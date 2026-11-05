"""PRED_DO_REPEAT rule tests (Phase 4 §6)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import ActivityStatus, ActivityType
from identity.diagnostic.episode import Episode, qualifies
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.rules._common import PredictionContext
from identity.prediction.rules.do_repeat import RULE_ID, evaluate
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeView, t

RULE_ID_CHECK = RULE_ID
TZ = "Asia/Bangkok"


def ep(onsetLocal: str, peak=SeverityLevelType.ElevatedRisk):
    onset = t(onsetLocal, TZ)
    return Episode(
        parameter=PondParameters.DO,
        direction=None,
        onsetAt=onset,
        endAt=None,
        status=__import__("identity.analysis.models", fromlist=["DiagStatus"]).DiagStatus.open,
        peakSeverity=peak,
        lastSeverity=peak,
        peakZone=ThresholdLevelType.HighRisk if peak != SeverityLevelType.Stress else ThresholdLevelType.Stress,
        readingCount=2,
        lastReadingAt=onset,
    )


def ctx(episodes=(), activities=(), nowStr="2026-10-25 15:00", active=None):
    return PredictionContext(
        pond=makePond(biomassKg=400.0, timezone=TZ),
        views=(),
        activities=tuple(activities),
        doEpisodes=tuple(episodes),
        active=active,
        now=t(nowStr, TZ),
        cfg=DEFAULT_CONFIG,
    )


def test_t11_fires_with_earliest_offset():
    eps = [ep("2026-10-22 21:00"), ep("2026-10-23 19:00")]
    assert all(qualifies(e, DEFAULT_CONFIG) for e in eps)
    res = evaluate(ctx(eps))
    assert res.fire is True
    tonight = t("2026-10-25 18:00", TZ)
    assert res.riskStart == tonight + timedelta(hours=1)  # min offset 1h (Oct-23 19:00)
    assert res.riskEnd == t("2026-10-26 06:00", TZ)
    assert res.scope == "2026-10-25"


def test_single_night_or_stress_or_daytime_or_double_counts_once():
    assert evaluate(ctx([ep("2026-10-23 21:00")])).fire is False
    assert evaluate(ctx([ep("2026-10-22 21:00", SeverityLevelType.Stress), ep("2026-10-23 21:00", SeverityLevelType.Stress)])).fire is False
    assert evaluate(ctx([ep("2026-10-23 17:59"), ep("2026-10-24 21:00")])).fire is False

    sameNight = [ep("2026-10-23 21:00"), ep("2026-10-23 23:00"), ep("2026-10-24 21:00")]
    res = evaluate(ctx(sameNight))
    assert res.fire is True
    assert len(res.evidence["hitNights"]) == 2


def test_c2_gating_and_active_skip():
    eps = [ep("2026-10-22 21:00"), ep("2026-10-23 19:00")]
    res = evaluate(ctx(eps, nowStr="2026-10-25 11:59"))
    assert res.fire is False

    res2 = evaluate(ctx(eps, nowStr="2026-10-25 19:30"))
    assert res2.skip is True


def test_whole_night_aeration_mitigates():
    eps = [ep("2026-10-22 21:00"), ep("2026-10-23 19:00")]
    aer = makeActivity("a", activityType=ActivityType.aeration, status=ActivityStatus.pending,
                       startTime=t("2026-10-25 18:00", TZ), endTime=t("2026-10-26 06:00", TZ))
    res = evaluate(ctx(eps, [aer]))
    assert res.fire is False and res.reason == "mitigated"


def test_month_boundary_and_timezone():
    eps = [ep("2026-09-29 21:00"), ep("2026-09-30 21:00")]
    res = evaluate(ctx(eps, nowStr="2026-10-01 15:00"))
    assert res.fire is True
    assert res.scope == "2026-10-01"

    nowUtc = t("2026-10-25 15:00", TZ)  # 08:00 UTC; New York is 04:00 → predictFromHour false
    c = PredictionContext(makePond(timezone="America/New_York"), (), (), tuple(eps), None, nowUtc, DEFAULT_CONFIG)
    assert evaluate(c).fire is False
