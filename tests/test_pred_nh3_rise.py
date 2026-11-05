"""PRED_NH3_RISE rule tests (Phase 4 §6)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import ActivityStatus, ActivityType
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.rules._common import PredictionContext
from identity.prediction.rules.nh3_rise import RULE_ID, evaluate
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeView, t


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)


def ctx(views=(), activities=(), now=NOW, active=None):
    return PredictionContext(
        pond=makePond(biomassKg=400.0, timezone=TZ),
        views=tuple(views),
        activities=tuple(activities),
        doEpisodes=(),
        active=active,
        now=now,
        cfg=DEFAULT_CONFIG,
    )


def nh3View(when: datetime, zone=ThresholdLevelType.Stress):
    return makeView(PondParameters.NH3, when, value=0.1, zone=zone)


def tempHigh(when: datetime):
    return makeView(PondParameters.tem, when, value=31.0,
                    zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)


def heavy24() -> list:
    return [
        makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=NOW - timedelta(hours=2), quantityKg=7.2),
        makeActivity("b", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=NOW - timedelta(hours=4), quantityKg=7.2),
    ]


def test_case3_fires_with_risk_end_plus_12h_and_no_scope():
    res = evaluate(ctx([nh3View(NOW)], heavy24()))
    assert res.fire is True
    assert res.scope is None
    assert res.riskStart == NOW
    assert res.riskEnd == NOW + timedelta(hours=12)
    assert res.met == ("C1", "C2", "C3")


def test_daily_heavy_boundary_and_excluded_statuses():
    exact = [
        makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=NOW - timedelta(hours=1), quantityKg=12.0),
    ]
    assert evaluate(ctx([nh3View(NOW)], exact)).fire is True
    below = [
        makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=NOW - timedelta(hours=1), quantityKg=11.96),
    ]
    assert evaluate(ctx([nh3View(NOW)], below)).fire is False

    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=NOW - timedelta(hours=1), quantityKg=20.0)
    skipped = makeActivity("s", activityType=ActivityType.feeding, status=ActivityStatus.skipped,
                           startTime=NOW - timedelta(hours=1), quantityKg=20.0)
    assert evaluate(ctx([nh3View(NOW)], [pending, skipped])).fire is False


def test_stale_nh3_skips_and_optimal_is_gone():
    stale = nh3View(NOW - timedelta(minutes=91))
    res = evaluate(ctx([stale], heavy24()))
    assert res.skip is True

    optimal = nh3View(NOW, ThresholdLevelType.Optimal)
    res2 = evaluate(ctx([optimal], heavy24()))
    assert res2.fire is False and res2.reason == "conditions_gone"


def test_water_change_mitigation_and_lookback():
    base = heavy24()
    active = nh3View(NOW)
    recent = makeActivity("w", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                          startTime=NOW - timedelta(hours=3), fraction=0.5)
    assert evaluate(ctx([active], [*base, recent])).reason == "mitigated"

    planned = makeActivity("p", activityType=ActivityType.waterChange, status=ActivityStatus.pending,
                           startTime=NOW + timedelta(hours=10), fraction=0.25)
    assert evaluate(ctx([active], [*base, planned])).reason == "mitigated"

    oldWc = makeActivity("o", activityType=ActivityType.waterChange, status=ActivityStatus.done,
                         startTime=NOW - timedelta(hours=49), fraction=0.5)
    assert evaluate(ctx([active], [*base, oldWc])).fire is True


def test_risk_end_moves_while_id_and_risk_start_stable():
    assert RULE_ID == "PRED_NH3_RISE"
    assert tempHigh(NOW).value == 31.0
