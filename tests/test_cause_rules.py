"""Phase 2 diagnostic cause-rule tests."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import ActivityStatus, ActivityType
from identity.diagnostic.cause_rules import CauseContext, evaluateCauses
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeView, t


TZ = "Asia/Bangkok"


def ctx(views=(), activities=(), timezone=TZ):
    return CauseContext(makePond(timezone=timezone, biomassKg=400), tuple(views), tuple(activities), DEFAULT_CONFIG)


def ids(causes):
    return [cause.ruleId for cause in causes]


def test_t1_do_feed_then_night():
    onset = t("2026-10-25 20:00", TZ)
    feed = makeActivity("feed", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    causes, noClear = evaluateCauses(PondParameters.DO, None, onset, ctx(activities=[feed]))
    assert ids(causes) == ["DO_C_FEED", "DO_C_NIGHT"]
    facts = causes[0].facts
    assert facts["kg"] == 6.0
    assert facts["mealPct"] == 1.5
    assert facts["isHeavy"] is True
    assert causes[1].facts["aerationLogged"] is False
    assert noClear is False


def test_t1b_max_causes_drops_night_after_feed_and_temp():
    onset = t("2026-10-25 20:00", TZ)
    feed = makeActivity("feed", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    temp = makeView(PondParameters.tem, t("2026-10-25 19:00", TZ), value=31.0,
                    zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)
    causes, _ = evaluateCauses(PondParameters.DO, None, onset, ctx([temp], [feed]))
    assert ids(causes) == ["DO_C_FEED", "DO_C_TEMP"]


def test_every_rule_has_positive_and_negative_case():
    onset = t("2026-10-25 20:00", TZ)
    feed = makeActivity("f", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=onset - timedelta(hours=1), quantityKg=4.0)
    wc = makeActivity("wc", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                      startTime=onset - timedelta(hours=1), fraction=0.25)
    highTemp = makeView(PondParameters.tem, onset, value=31.0,
                        zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)
    badNh3 = makeView(PondParameters.NH3, onset, value=0.1, zone=ThresholdLevelType.Stress)

    assert "DO_C_FEED" in ids(evaluateCauses(PondParameters.DO, None, onset, ctx(activities=[feed]))[0])
    assert "NH3_C_FEED" in ids(evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[feed]))[0])
    assert "DO_C_TEMP" in ids(evaluateCauses(PondParameters.DO, None, onset, ctx([highTemp]))[0])
    assert "NO2_C_NH3" in ids(evaluateCauses(PondParameters.NO2_N, None, onset, ctx([badNh3]))[0])
    assert "TEMP_C_TIME" in ids(evaluateCauses(PondParameters.tem, ThresholdDirection.High, t("2026-10-25 12:00", TZ), ctx())[0])
    assert "PH_C_TIME" in ids(evaluateCauses(PondParameters.pH, ThresholdDirection.Low, t("2026-10-26 03:00", TZ), ctx())[0])
    assert "SAL_C_WATERCHG" in ids(evaluateCauses(PondParameters.salinity, None, onset, ctx(activities=[wc]))[0])

    noon = t("2026-10-25 12:00", TZ)
    assert evaluateCauses(PondParameters.NH3, None, noon, ctx())[1] is True
    assert evaluateCauses(PondParameters.tem, ThresholdDirection.Low, noon, ctx())[1] is True
    assert evaluateCauses(PondParameters.pH, None, noon, ctx())[1] is True


def test_activity_and_view_boundaries():
    onset = datetime(2026, 10, 25, 20, 0)
    inFeed = makeActivity("in", activityType=ActivityType.feeding, status=ActivityStatus.done,
                          startTime=onset - timedelta(hours=6), quantityKg=6.0)
    atOnset = makeActivity("at", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=onset, quantityKg=6.0)
    outside = makeActivity("out", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=onset - timedelta(hours=6, seconds=1), quantityKg=6.0)
    causes, _ = evaluateCauses(PondParameters.DO, None, onset, ctx(activities=[inFeed, atOnset, outside]))
    assert causes[0].facts["feedCount"] == 1

    nh3AtOnset = makeView(PondParameters.NH3, onset, zone=ThresholdLevelType.Stress)
    assert "NO2_C_NH3" in ids(evaluateCauses(PondParameters.NO2_N, None, onset, ctx([nh3AtOnset]))[0])

    nh3Old = makeView(PondParameters.NH3, onset - timedelta(hours=2), zone=ThresholdLevelType.Stress)
    nh3Recent = makeView(PondParameters.NH3, onset - timedelta(hours=1), zone=ThresholdLevelType.HighRisk)
    cause = evaluateCauses(PondParameters.NO2_N, None, onset, ctx([nh3Recent, nh3Old]))[0][0]
    assert cause.facts["nh3FirstTime"] == nh3Old.time
    assert cause.facts["nh3LastTime"] == nh3Recent.time
    assert cause.facts["nh3PeakZone"] == ThresholdLevelType.HighRisk


def test_no2_nh3_boundary_lookback_is_inclusive():
    onset = datetime(2026, 10, 25, 20, 0)
    exact = makeView(PondParameters.NH3, onset - timedelta(hours=24), zone=ThresholdLevelType.Stress)
    outside = makeView(PondParameters.NH3, onset - timedelta(hours=24, seconds=1), zone=ThresholdLevelType.Stress)
    assert "NO2_C_NH3" in ids(evaluateCauses(PondParameters.NO2_N, None, onset, ctx([exact]))[0])
    assert evaluateCauses(PondParameters.NO2_N, None, onset, ctx([outside]))[1] is True


def test_temp_and_salinity_lookback_boundaries():
    onset = datetime(2026, 10, 25, 20, 0)
    exactTemp = makeView(PondParameters.tem, onset - timedelta(hours=3), value=31, zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)
    outsideTemp = makeView(PondParameters.tem, onset - timedelta(hours=3, seconds=1), value=31, zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)
    assert "DO_C_TEMP" in ids(evaluateCauses(PondParameters.DO, None, onset, ctx([exactTemp]))[0])
    assert "DO_C_TEMP" not in ids(evaluateCauses(PondParameters.DO, None, onset, ctx([outsideTemp]))[0])

    exactWater = makeActivity("w1", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                              startTime=onset - timedelta(hours=6), fraction=0.25)
    atOnset = makeActivity("w2", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                           startTime=onset, fraction=0.25)
    outsideWater = makeActivity("w3", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                                startTime=onset - timedelta(hours=6, seconds=1), fraction=0.25)
    causes, _ = evaluateCauses(PondParameters.salinity, None, onset, ctx(activities=[exactWater, atOnset, outsideWater]))
    assert causes[0].facts["waterChangeTime"] == exactWater.startTime


def test_time_rules_wrong_direction_and_new_york():
    bangkokNoon = t("2026-10-25 12:00", TZ)
    assert evaluateCauses(PondParameters.tem, ThresholdDirection.Low, bangkokNoon, ctx())[1] is True
    assert evaluateCauses(PondParameters.pH, ThresholdDirection.Low, bangkokNoon, ctx())[1] is True

    instant = datetime(2026, 10, 25, 12, 0)
    assert "DO_C_NIGHT" in ids(evaluateCauses(PondParameters.DO, None, instant, ctx())[0])
    assert "DO_C_NIGHT" not in ids(evaluateCauses(PondParameters.DO, None, instant, ctx(timezone="America/New_York"))[0])


def test_heavy_threshold_and_same_pct_tie_uses_latest_feed():
    onset = datetime(2026, 10, 25, 20, 0)
    early = makeActivity("e", activityType=ActivityType.feeding, status=ActivityStatus.done,
                         startTime=onset - timedelta(hours=2), quantityKg=4.0)
    latest = makeActivity("l", activityType=ActivityType.feeding, status=ActivityStatus.done,
                          startTime=onset - timedelta(hours=1), quantityKg=4.0)
    cause = evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[early, latest]))[0][0]
    assert cause.facts["mealPct"] == 1.0
    assert cause.facts["isHeavy"] is True
    assert cause.facts["feedTime"] == latest.startTime


def test_no_activities_only_night_positive_evidence():
    onset = t("2026-10-25 20:00", TZ)
    causes, noClear = evaluateCauses(PondParameters.DO, None, onset, ctx())
    assert ids(causes) == ["DO_C_NIGHT"]
    assert noClear is False


def test_all_unknown_feeds_match_without_headline():
    onset = datetime(2026, 10, 25, 20, 0)
    f1 = makeActivity("f1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                      startTime=onset - timedelta(hours=2), quantityKg=None)
    f2 = makeActivity("f2", activityType=ActivityType.feeding, status=ActivityStatus.done,
                      startTime=onset - timedelta(hours=1), quantityKg=None)
    cause = evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[f1, f2]))[0][0]
    assert cause.facts["feedTime"] is None
    assert cause.facts["totalKg"] == 0
    assert cause.facts["unknownQtyCount"] == 2
    assert cause.facts["hoursBeforeOnset"] == 1.0


def test_pending_skipped_and_unknown_feed_quantity():
    onset = datetime(2026, 10, 25, 20, 0)
    pending = makeActivity("pending", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=onset - timedelta(hours=1), quantityKg=6.0)
    skipped = makeActivity("skip", activityType=ActivityType.feeding, status=ActivityStatus.skipped,
                           startTime=onset - timedelta(hours=1), quantityKg=6.0)
    assert evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[pending, skipped]))[1] is True

    unknown = makeActivity("unknown", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=onset - timedelta(hours=1), quantityKg=None)
    causes, _ = evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[unknown]))
    facts = causes[0].facts
    assert facts["kg"] is None
    assert facts["mealPct"] is None
    assert facts["isHeavy"] is False
    assert facts["unknownQtyCount"] == 1
    assert facts["totalKg"] == 0

    known = makeActivity("known", activityType=ActivityType.feeding, status=ActivityStatus.done,
                         startTime=onset - timedelta(hours=2), quantityKg=4.0)
    mixedFacts = evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[known, unknown]))[0][0].facts
    assert mixedFacts["totalKg"] == 4.0
    assert mixedFacts["unknownQtyCount"] == 1


def test_do_night_and_aeration_logged_boundaries():
    assert "DO_C_NIGHT" not in ids(evaluateCauses(PondParameters.DO, None, t("2026-10-25 17:59", TZ), ctx())[0])
    assert "DO_C_NIGHT" in ids(evaluateCauses(PondParameters.DO, None, t("2026-10-25 18:00", TZ), ctx())[0])
    assert "DO_C_NIGHT" in ids(evaluateCauses(PondParameters.DO, None, t("2026-10-26 05:59", TZ), ctx())[0])
    assert "DO_C_NIGHT" not in ids(evaluateCauses(PondParameters.DO, None, t("2026-10-26 06:00", TZ), ctx())[0])

    onset = t("2026-10-25 20:00", TZ)
    pendingAeration = makeActivity("a", activityType=ActivityType.aeration, status=ActivityStatus.pending,
                                   startTime=onset - timedelta(hours=1), endTime=onset + timedelta(hours=1))
    skippedAeration = makeActivity("b", activityType=ActivityType.aeration, status=ActivityStatus.skipped,
                                   startTime=onset - timedelta(hours=1), endTime=onset + timedelta(hours=1))
    assert evaluateCauses(PondParameters.DO, None, onset, ctx(activities=[pendingAeration]))[0][0].facts["aerationLogged"] is True
    assert evaluateCauses(PondParameters.DO, None, onset, ctx(activities=[skippedAeration]))[0][0].facts["aerationLogged"] is False


def test_headline_meal_priority_and_no_match():
    onset = datetime(2026, 10, 25, 20, 0)
    smaller = makeActivity("small", activityType=ActivityType.feeding, status=ActivityStatus.done,
                           startTime=onset - timedelta(hours=2), quantityKg=4.0)
    larger = makeActivity("large", activityType=ActivityType.feeding, status=ActivityStatus.done,
                          startTime=onset - timedelta(hours=3), quantityKg=6.0)
    causes, _ = evaluateCauses(PondParameters.NH3, None, onset, ctx(activities=[smaller, larger]))
    assert causes[0].facts["feedTime"] == larger.startTime
    assert causes[0].facts["totalKg"] == 10.0
    assert causes[0].facts["isHeavy"] is True

    assert evaluateCauses(PondParameters.salinity, None, onset, ctx())[1] is True
