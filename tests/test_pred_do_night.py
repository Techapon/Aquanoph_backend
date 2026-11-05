"""PRED_DO_NIGHT rule tests (Phase 4 §6)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import ActivityStatus, ActivityType
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.rules._common import PredictionContext
from identity.prediction.rules.do_night import RULE_ID, evaluate
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeView, t


TZ = "Asia/Bangkok"


def ctx(views=(), activities=(), now=None, active=None):
    n = now or t("2026-10-25 16:30", TZ)
    return PredictionContext(
        pond=makePond(biomassKg=400.0, timezone=TZ),
        views=tuple(views),
        activities=tuple(activities),
        doEpisodes=(),
        active=active,
        now=n,
        cfg=DEFAULT_CONFIG,
    )


def feed(startLocal: str, kg: float | None, status=ActivityStatus.done, aid: str = "f"):
    return makeActivity(aid, activityType=ActivityType.feeding, status=status,
                        startTime=t(startLocal, TZ), quantityKg=kg)


def tempAt(when: str, zone=ThresholdLevelType.Stress, value: float = 31.0):
    return makeView(PondParameters.tem, t(when, TZ), value=value,
                    zone=zone, direction=ThresholdDirection.High)


def test_case2_fires_with_all_three_conditions():
    now = t("2026-10-25 16:30", TZ)
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    temp = tempAt("2026-10-25 16:00")
    res = evaluate(ctx([temp], [pending], now))
    assert res.fire is True
    assert res.met == ("C1", "C2", "C3")
    assert res.riskStart == t("2026-10-25 20:00", TZ)
    assert res.riskEnd == t("2026-10-26 06:00", TZ)
    assert res.scope == "2026-10-25"


def test_fires_without_hot_weather():
    now = t("2026-10-25 16:30", TZ)
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    res = evaluate(ctx([], [pending], now))
    assert res.fire is True
    assert res.met == ("C1", "C3")
    assert res.evidence["conditions"]["C2"] is False


def test_light_meal_does_not_fire():
    now = t("2026-10-25 16:30", TZ)
    light = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                         startTime=t("2026-10-25 19:00", TZ), quantityKg=3.0)
    res = evaluate(ctx([], [light], now))
    assert res.fire is False
    assert res.reason == "conditions_gone"


def test_heavy_boundary_and_evening_boundary():
    boundaryCfg = DEFAULT_CONFIG
    now = t("2026-10-25 16:30", TZ)
    exact = makeActivity("e1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                         startTime=t("2026-10-25 19:00", TZ), quantityKg=4.0)
    assert evaluate(ctx([], [exact], now)).fire is True
    below = makeActivity("e2", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                         startTime=t("2026-10-25 19:00", TZ), quantityKg=3.96)
    assert evaluate(ctx([], [below], now)).fire is False

    tooEarly = makeActivity("e", activityType=ActivityType.feeding, status=ActivityStatus.done,
                            startTime=t("2026-10-25 15:59", TZ), quantityKg=8.0)
    assert evaluate(ctx([], [tooEarly], now)).fire is False
    onTime = makeActivity("e", activityType=ActivityType.feeding, status=ActivityStatus.done,
                          startTime=t("2026-10-25 16:00", TZ), quantityKg=8.0)
    assert evaluate(ctx([], [onTime], now)).fire is True
    assert boundaryCfg.heavyMealPct == 1.0


def test_aeration_mitigation_boundaries():
    now = t("2026-10-25 16:30", TZ)
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)

    def aer(start: str, end: str, status=ActivityStatus.pending):
        return makeActivity("a", activityType=ActivityType.aeration, status=status,
                            startTime=t(start, TZ), endTime=t(end, TZ))

    res = evaluate(ctx([], [pending, aer("2026-10-25 18:30", "2026-10-26 06:00")], now))
    assert res.fire is False and res.reason == "mitigated"

    exact3 = evaluate(ctx([], [pending, aer("2026-10-25 20:00", "2026-10-25 23:00")], now))
    assert exact3.evidence["aerationHours"] == 3.0
    assert exact3.fire is False

    short = evaluate(ctx([], [pending, aer("2026-10-25 20:00", "2026-10-25 22:54")], now))
    assert short.evidence["aerationHours"] == 2.9
    assert short.fire is True

    skipAer = evaluate(ctx([], [pending, aer("2026-10-25 18:30", "2026-10-26 06:00", ActivityStatus.skipped)], now))
    assert skipAer.fire is True


def test_lookback_boundaries_and_unknown_quantity():
    now = t("2026-10-25 16:30", TZ)
    exact6h = makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=now - timedelta(hours=6), quantityKg=8.0)
    # 10:30 local is before the evening cutoff, so still not qualifying.
    assert evaluate(ctx([], [exact6h], now)).fire is False

    evening6h = makeActivity("b", activityType=ActivityType.feeding, status=ActivityStatus.done,
                             startTime=t("2026-10-25 16:00", TZ), quantityKg=8.0)
    beyond6h = makeActivity("c", activityType=ActivityType.feeding, status=ActivityStatus.done,
                            startTime=t("2026-10-25 16:00", TZ) - timedelta(seconds=1), quantityKg=8.0)
    assert evaluate(ctx([], [evening6h], now)).fire is True
    assert beyond6h.startTime == t("2026-10-25 16:00", TZ) - timedelta(seconds=1)

    morningNow = t("2026-10-25 09:30", TZ)
    future = makeActivity("f", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                          startTime=t("2026-10-25 17:30", TZ), quantityKg=8.0)
    assert evaluate(ctx([], [future], morningNow)).fire is True
    tooFar = makeActivity("g", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                          startTime=t("2026-10-25 17:30", TZ) + timedelta(seconds=1), quantityKg=8.0)
    assert evaluate(ctx([], [tooFar], morningNow)).fire is False

    unknown = makeActivity("u", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=t("2026-10-25 18:00", TZ), quantityKg=None)
    res = evaluate(ctx([], [unknown], now))
    assert res.fire is False and res.reason == "conditions_gone"
    assert res.evidence["unknownQtyCount"] == 1


def test_anchor_stability_and_post_midnight_scope():
    now = t("2026-10-25 21:00", TZ)
    done = makeActivity("d", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 18:30", TZ), quantityKg=8.0)
    res = evaluate(ctx([], [done], now))
    assert res.riskStart == now

    after = t("2026-10-26 02:00", TZ)
    lateMeal = makeActivity("d", activityType=ActivityType.feeding, status=ActivityStatus.done,
                            startTime=t("2026-10-25 21:00", TZ), quantityKg=8.0)
    res2 = evaluate(ctx([], [lateMeal], after))
    assert res2.scope == "2026-10-25"


def test_second_timezone_differs():
    utcInstant = datetime(2026, 10, 25, 11, 0)
    mealUtc = makeActivity("m", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=utcInstant, quantityKg=8.0)
    bkk = PredictionContext(makePond(timezone="Asia/Bangkok"), (), (mealUtc,), (), None, utcInstant, DEFAULT_CONFIG)
    ny = PredictionContext(makePond(timezone="America/New_York"), (), (mealUtc,), (), None, utcInstant, DEFAULT_CONFIG)
    assert evaluate(bkk).fire is True
    assert evaluate(ny).fire is False
