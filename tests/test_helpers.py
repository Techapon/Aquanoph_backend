"""Unit tests for helpers per PHASE_1_foundation.md."""
from datetime import date, datetime, timedelta
import pytest

from config.constants import cfg
from identity.analysis.helpers import (
    NightWindow,
    aerationHours,
    dailyMealPct,
    doneActivities,
    inLocalWindow,
    isNight,
    isStale,
    localDate,
    localTime,
    mealPct,
    nightWindowFor,
    overlap,
    plannedActivities,
    toUtc,
    toUtcNaive,
    zoneAt,
)
from identity.analysis.models import Activity, ActivityStatus, ActivityType, PondInfo
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeView, t


TZ = "Asia/Bangkok"


# ---------- Time (Asia/Bangkok = UTC+7) ----------
def test_utc_to_local_and_is_night():
    # 13:00 UTC -> local 20:00 -> isNight True
    t20 = datetime(2026, 10, 25, 13, 0)
    assert localTime(t20, TZ).hour == 20
    assert isNight(t20, TZ, cfg) is True

    # 06:00 UTC -> 13:00 local -> False
    t13 = datetime(2026, 10, 25, 6, 0)
    assert localTime(t13, TZ).hour == 13
    assert isNight(t13, TZ, cfg) is False


def test_is_night_boundaries():
    # local 17:59 False, 18:00 True, 05:59 True, 06:00 False
    assert isNight(t("2026-10-25 17:59", TZ), TZ, cfg) is False
    assert isNight(t("2026-10-25 18:00", TZ), TZ, cfg) is True
    assert isNight(t("2026-10-26 05:59", TZ), TZ, cfg) is True
    assert isNight(t("2026-10-26 06:00", TZ), TZ, cfg) is False


def test_in_local_window_with_wrap():
    # inLocalWindow with wrap (22, 6): 23:00 True, 03:00 True, 12:00 False
    assert inLocalWindow(t("2026-10-25 23:00", TZ), TZ, 22, 6) is True
    assert inLocalWindow(t("2026-10-26 03:00", TZ), TZ, 22, 6) is True
    assert inLocalWindow(t("2026-10-25 12:00", TZ), TZ, 22, 6) is False


def test_night_window_for():
    # local 15:00 -> tonight (starts today 18:00, ends tomorrow 06:00)
    w15 = nightWindowFor(t("2026-10-25 15:00", TZ), TZ, cfg)
    assert w15.nightDate == date(2026, 10, 25)
    assert w15.start == t("2026-10-25 18:00", TZ)
    assert w15.end == t("2026-10-26 06:00", TZ)

    # 23:00 -> same night
    w23 = nightWindowFor(t("2026-10-25 23:00", TZ), TZ, cfg)
    assert w23.nightDate == date(2026, 10, 25)
    assert w23.start == t("2026-10-25 18:00", TZ)
    assert w23.end == t("2026-10-26 06:00", TZ)

    # 03:00 -> night that started yesterday, ends today 06:00
    w03 = nightWindowFor(t("2026-10-26 03:00", TZ), TZ, cfg)
    assert w03.nightDate == date(2026, 10, 25)
    assert w03.start == t("2026-10-25 18:00", TZ)
    assert w03.end == t("2026-10-26 06:00", TZ)

    # 06:00 exactly -> tonight (starts today 18:00)
    w06 = nightWindowFor(t("2026-10-26 06:00", TZ), TZ, cfg)
    assert w06.nightDate == date(2026, 10, 26)
    assert w06.start == t("2026-10-26 18:00", TZ)
    assert w06.end == t("2026-10-27 06:00", TZ)


def test_second_timezone_differs():
    # Same UTC instant gives different night classification in New York (UTC-5 / UTC-4)
    instantUtc = datetime(2026, 10, 25, 12, 0)
    # In Bangkok (+7) -> 19:00 -> night
    assert isNight(instantUtc, "Asia/Bangkok", cfg) is True
    # In New York (-4 EDT) -> 08:00 -> daytime
    assert isNight(instantUtc, "America/New_York", cfg) is False


# ---------- Activities ----------
def test_meal_pct():
    pond = makePond(biomassKg=400.0)
    act = makeActivity(activityType=ActivityType.feeding, quantityKg=6.0)
    assert mealPct(act, pond) == 1.5

    # non-feeding or missing kg -> ValueError
    nonFeed = makeActivity(activityType=ActivityType.aeration)
    with pytest.raises(ValueError):
        mealPct(nonFeed, pond)

    # biomassKg <= 0 -> ValueError
    zeroPond = makePond(biomassKg=0.0)
    with pytest.raises(ValueError):
        mealPct(act, zeroPond)


def test_daily_meal_pct():
    pond = makePond(biomassKg=400.0)
    targetD = date(2026, 10, 25)

    # 1. Done feeding on target date: 6 kg / 400 kg = 1.5%
    act1 = makeActivity("a1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 08:00", TZ), quantityKg=6.0)

    # 2. Second done feeding on target date: 4 kg / 400 kg = 1.0%
    act2 = makeActivity("a2", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 14:00", TZ), quantityKg=4.0)

    # 3. Pending feeding on target date (Rule 6: not counted)
    actPending = makeActivity("a3", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                              startTime=t("2026-10-25 17:00", TZ), quantityKg=5.0)

    # 4. Skipped feeding on target date (Rule 6: not counted)
    actSkipped = makeActivity("a4", activityType=ActivityType.feeding, status=ActivityStatus.skipped,
                              startTime=t("2026-10-25 12:00", TZ), quantityKg=3.0)

    # 5. Done feeding on different local date (2026-10-26 01:00 local time -> Oct 26)
    actOtherDay = makeActivity("a5", activityType=ActivityType.feeding, status=ActivityStatus.done,
                               startTime=t("2026-10-26 01:00", TZ), quantityKg=6.0)

    # 6. Feeding with quantityKg=None (Rule 5: unknown != 0, skipped from sum)
    actNoQty = makeActivity("a6", activityType=ActivityType.feeding, status=ActivityStatus.done,
                            startTime=t("2026-10-25 10:00", TZ), quantityKg=None)

    allActs = [act1, act2, actPending, actSkipped, actOtherDay, actNoQty]
    resultPct = dailyMealPct(allActs, pond, targetD, TZ)
    # Expected: act1 (1.5%) + act2 (1.0%) = 2.5%
    assert resultPct == 2.5



def test_aeration_hours():
    # partial overlap, two overlapping merged, skipped excluded, pending and done included
    t1 = datetime(2026, 10, 25, 10, 0)
    t2 = datetime(2026, 10, 25, 12, 0)
    t3 = datetime(2026, 10, 25, 11, 0)
    t4 = datetime(2026, 10, 25, 13, 0)

    actDone = makeActivity("a1", activityType=ActivityType.aeration, status=ActivityStatus.done,
                           startTime=t1, endTime=t2)
    actPending = makeActivity("a2", activityType=ActivityType.aeration, status=ActivityStatus.pending,
                              startTime=t3, endTime=t4)
    actSkipped = makeActivity("a3", activityType=ActivityType.aeration, status=ActivityStatus.skipped,
                              startTime=datetime(2026, 10, 25, 10, 30),
                              endTime=datetime(2026, 10, 25, 11, 30))

    hours = aerationHours([actDone, actPending, actSkipped], t1, t4)
    assert hours == 3.0  # union is 10:00 to 13:00 = 3h

    # no overlap -> 0
    emptyHours = aerationHours([actDone], datetime(2026, 10, 25, 14, 0), datetime(2026, 10, 25, 16, 0))
    assert emptyHours == 0.0


def test_done_and_planned_activities():
    now = datetime(2026, 10, 25, 12, 0)
    pastDone = makeActivity("a1", status=ActivityStatus.done, startTime=now - timedelta(hours=2))
    pastPending = makeActivity("a2", status=ActivityStatus.pending, startTime=now - timedelta(hours=1))
    futurePending = makeActivity("a3", status=ActivityStatus.pending, startTime=now + timedelta(hours=1))
    futureSkipped = makeActivity("a4", status=ActivityStatus.skipped, startTime=now + timedelta(hours=2))

    acts = [pastDone, pastPending, futurePending, futureSkipped]

    done = doneActivities(acts)
    assert len(done) == 1
    assert done[0].id == "a1"

    # plannedActivities ignores past-start pending and non-pending
    planned = plannedActivities(acts, now=now)
    assert len(planned) == 1
    assert planned[0].id == "a3"


def test_activity_validation_cases():
    now = datetime(2026, 10, 25, 12, 0)

    # aeration needs endTime > startTime
    with pytest.raises(ValueError):
        Activity(id="1", pondId="p", type=ActivityType.aeration, status=ActivityStatus.pending,
                 startTime=now, endTime=now)
    with pytest.raises(ValueError):
        Activity(id="1", pondId="p", type=ActivityType.aeration, status=ActivityStatus.pending,
                 startTime=now, endTime=now - timedelta(hours=1))

    # other types must not have endTime
    with pytest.raises(ValueError):
        Activity(id="2", pondId="p", type=ActivityType.feeding, status=ActivityStatus.pending,
                 startTime=now, endTime=now + timedelta(hours=1), quantityKg=10.0)

    # quantityKg >= 0
    with pytest.raises(ValueError):
        Activity(id="3", pondId="p", type=ActivityType.feeding, status=ActivityStatus.pending,
                 startTime=now, quantityKg=-1.0)

    # fraction in (0, 1] and only for waterChange
    with pytest.raises(ValueError):
        Activity(id="4", pondId="p", type=ActivityType.waterChange, status=ActivityStatus.pending,
                 startTime=now, fraction=0.0)
    with pytest.raises(ValueError):
        Activity(id="5", pondId="p", type=ActivityType.waterChange, status=ActivityStatus.pending,
                 startTime=now, fraction=1.5)
    with pytest.raises(ValueError):
        Activity(id="6", pondId="p", type=ActivityType.feeding, status=ActivityStatus.pending,
                 startTime=now, quantityKg=10.0, fraction=0.5)


# ---------- Data Freshness ----------
def test_is_stale_exact_boundaries():
    now = datetime(2026, 10, 25, 12, 0)
    # max age = 3.0 * 30 min = 90 min
    # at exactly 90 min: False (strictly greater)
    assert isStale(now - timedelta(minutes=90), now, cfg) is False
    # at 90 min + 1 s: True
    assert isStale(now - timedelta(minutes=90, seconds=1), now, cfg) is True


def test_zone_at():
    tRef = datetime(2026, 10, 25, 12, 0)
    vOld = makeView(PondParameters.DO, time=tRef - timedelta(minutes=100))
    vFresh = makeView(PondParameters.DO, time=tRef - timedelta(minutes=30), zone=ThresholdLevelType.Stress)
    vFuture = makeView(PondParameters.DO, time=tRef + timedelta(minutes=10))

    # returns latest with time <= t and not stale
    res = zoneAt([vOld, vFresh, vFuture], PondParameters.DO, tRef, cfg)
    assert res == vFresh

    # returns None when latest is stale (>90 min)
    resStale = zoneAt([vOld], PondParameters.DO, tRef, cfg)
    assert resStale is None

    # returns None when view is newer than t
    resFuture = zoneAt([vFuture], PondParameters.DO, tRef, cfg)
    assert resFuture is None


# ---------- Overlap ----------
def test_overlap_returns_timedelta():
    t1 = datetime(2026, 10, 25, 10, 0)
    t2 = datetime(2026, 10, 25, 12, 0)
    t3 = datetime(2026, 10, 25, 11, 0)
    t4 = datetime(2026, 10, 25, 13, 0)

    delta = overlap(t1, t2, t3, t4)
    assert delta == timedelta(hours=1)

    noDelta = overlap(t1, t2, t2, t4)
    assert noDelta == timedelta(0)
