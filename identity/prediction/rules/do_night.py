"""PRED_DO_NIGHT prediction rule (Phase 4 §2)."""
from datetime import datetime, timedelta

from identity.analysis.helpers import doneActivities, localTime, mealPct, nightWindowFor, plannedActivities
from identity.analysis.models import Activity, ActivityType
from identity.prediction.rules._common import (
    PredictionContext,
    RuleResult,
    aerationHoursIn,
    anchor,
    metFrom,
    tempHighRecent,
)

RULE_ID = "PRED_DO_NIGHT"


def evaluate(ctx: PredictionContext) -> RuleResult:
    """Evaluate PRED_DO_NIGHT. Never skips (needs no sensor data)."""
    tz = ctx.pond.timezone
    cfg = ctx.cfg
    now = ctx.now

    doneMeals = doneActivities(
        ctx.activities, ActivityType.feeding,
        now - timedelta(hours=cfg.feedLookbackPredHours),
        now + timedelta(microseconds=1),
    )
    pendingMeals = plannedActivities(
        ctx.activities, ActivityType.feeding,
        now,
        now + timedelta(hours=cfg.feedLookaheadPredHours) + timedelta(microseconds=1),
        now,
    )

    def qualifies(act: Activity) -> bool:
        if act.type != ActivityType.feeding or act.quantityKg is None:
            return False
        loc = localTime(act.startTime, tz)
        if loc.hour * 60 + loc.minute < cfg.eveningFromHour * 60:
            return False
        return mealPct(act, ctx.pond) >= cfg.heavyMealPct

    candidates = tuple(
        a for a in (*sorted(doneMeals, key=lambda a: a.startTime), *sorted(pendingMeals, key=lambda a: a.startTime))
        if qualifies(a)
    )
    unknownQtyCount = sum(
        1 for a in ctx.activities
        if a.type == ActivityType.feeding
        and a.status.value in ("done", "pending")
        and a.quantityKg is None
    )
    c1 = bool(candidates)
    firstMeal = candidates[0] if candidates else None

    tempRecent = tempHighRecent(ctx.views, now, cfg.tempHighLookbackPredHours, cfg)
    c2 = bool(tempRecent)
    latestTemp = max(tempRecent, key=lambda v: v.time) if tempRecent else None

    anc = anchor(ctx)
    if firstMeal is not None:
        riskStartBase = firstMeal.startTime + timedelta(hours=cfg.riskStartAfterMealHours)
        riskStart = max(anc, riskStartBase)
    else:
        riskStart = anc

    nw = nightWindowFor(riskStart, tz, cfg)
    riskEnd = nw.end
    scope = nw.nightDate.isoformat()

    aeration = aerationHoursIn(ctx.activities, riskStart, riskEnd)
    c3 = aeration < cfg.minAerationHours

    conditions = {"C1": c1, "C2": c2, "C3": c3}
    met = metFrom(conditions)

    if c1 and c3:
        fire, reason = True, None
    elif c1 and not c3:
        fire, reason = False, "mitigated"
    else:
        fire, reason = False, "conditions_gone"

    evidence: dict[str, object] = {
        "firstMealTime": firstMeal.startTime if firstMeal else None,
        "firstMealKg": firstMeal.quantityKg if firstMeal else None,
        "firstMealPct": mealPct(firstMeal, ctx.pond) if firstMeal else None,
        "mealTime": firstMeal.startTime if firstMeal else None,
        "mealKg": firstMeal.quantityKg if firstMeal else None,
        "mealPct": mealPct(firstMeal, ctx.pond) if firstMeal else None,
        "mealIsPlanned": bool(firstMeal and firstMeal.startTime > ctx.now),
        "mealCount": len(candidates),
        "aerationHours": aeration,
        "unknownQtyCount": unknownQtyCount,
        "conditions": conditions,
    }
    if latestTemp is not None:
        evidence["tempValue"] = latestTemp.value
        evidence["tempZone"] = latestTemp.zone
        evidence["tempTime"] = latestTemp.time

    return RuleResult(
        skip=False,
        fire=fire,
        reason=reason,
        met=met,
        scope=scope,
        riskStart=riskStart,
        riskEnd=riskEnd,
        evidence=evidence,
    )
