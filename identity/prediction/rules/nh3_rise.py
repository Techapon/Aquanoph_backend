"""PRED_NH3_RISE prediction rule (Phase 4 §4)."""
from datetime import datetime, timedelta

from identity.analysis.helpers import doneActivities, plannedActivities, totalMealPctDetail, zoneAt
from identity.analysis.models import ActivityType
from identity.prediction.rules._common import (
    PredictionContext,
    RuleResult,
    anchor,
    metFrom,
    tempHighNow,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType

RULE_ID = "PRED_NH3_RISE"


def evaluate(ctx: PredictionContext) -> RuleResult:
    """Evaluate PRED_NH3_RISE; skips when NH3 latest view is missing or stale."""
    cfg = ctx.cfg
    now = ctx.now

    latestNh3 = zoneAt(ctx.views, PondParameters.NH3, now, cfg)
    if latestNh3 is None:
        return RuleResult(skip=True, fire=False, reason=None, met=(), scope=None,
                          riskStart=None, riskEnd=None, evidence={})

    pct, unknownCount = totalMealPctDetail(ctx.activities, ctx.pond, now - timedelta(hours=24), now)
    c1 = pct >= cfg.dailyHeavyPct

    c2 = latestNh3.zone != ThresholdLevelType.Optimal

    toInclusive = now + timedelta(microseconds=1)
    doneWc = doneActivities(ctx.activities, ActivityType.waterChange, now - timedelta(hours=cfg.wcLookbackHours), toInclusive)
    plannedWc = plannedActivities(ctx.activities, ActivityType.waterChange, now, now + timedelta(hours=cfg.wcLookaheadHours) + timedelta(microseconds=1), now)
    c3 = not doneWc and not plannedWc

    temp = tempHighNow(ctx.views, now, cfg)
    c4 = temp is not None

    conditions = {"C1": c1, "C2": c2, "C3": c3, "C4": c4}
    met = metFrom(conditions)

    if c1 and c2 and c3:
        fire, reason = True, None
    elif c1 and c2 and not c3:
        fire, reason = False, "mitigated"
    else:
        fire, reason = False, "conditions_gone"

    riskStart = anchor(ctx)
    riskEnd = now + timedelta(hours=cfg.nh3RiseHorizonHours)

    evidence: dict[str, object] = {
        "totalMealPct": pct,
        "unknownQtyCount": unknownCount,
        "nh3Zone": latestNh3.zone,
        "nh3Value": latestNh3.value,
        "nh3Time": latestNh3.time,
        "lastWaterChangeTime": doneWc[-1].startTime if doneWc else None,
        "plannedWaterChangeTime": plannedWc[0].startTime if plannedWc else None,
        "conditions": conditions,
    }
    if temp is not None:
        evidence["tempValue"] = temp.value
        evidence["tempZone"] = temp.zone
        evidence["tempTime"] = temp.time

    return RuleResult(
        skip=False,
        fire=fire,
        reason=reason,
        met=met,
        scope=None,
        riskStart=riskStart,
        riskEnd=riskEnd,
        evidence=evidence,
    )
