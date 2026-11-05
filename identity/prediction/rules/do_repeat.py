"""PRED_DO_REPEAT prediction rule (Phase 4 §3)."""
from datetime import datetime, timedelta

from identity.analysis.helpers import localTime
from identity.analysis.models import ActivityType
from identity.diagnostic.episode import qualifies
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.rules._common import (
    PredictionContext,
    RuleResult,
    aerationHoursIn,
    metFrom,
    nightWindowForDate,
    tempHighNow,
)
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.analysis.severity_view import severityRank
from identity.analysis.helpers import nightWindowFor

RULE_ID = "PRED_DO_REPEAT"


def evaluate(ctx: PredictionContext) -> RuleResult:
    """Evaluate PRED_DO_REPEAT using historical DO episodes."""
    cfg = ctx.cfg
    tz = ctx.pond.timezone
    now = ctx.now

    tonight = nightWindowFor(now, tz, cfg)
    pastNights = [nightWindowForDate(tonight.nightDate - timedelta(days=d), tz, cfg) for d in (3, 2, 1)]

    thresholdRank = severityRank(SeverityLevelType[cfg.repeatSeverity])
    hitNights: list = []
    offsets: list[float] = []

    for night in pastNights:
        nightEps = [
            e for e in ctx.doEpisodes
            if e.parameter == PondParameters.DO
            and qualifies(e, cfg)
            and severityRank(e.peakSeverity) >= thresholdRank
            and night.start <= e.onsetAt < night.end
        ]
        if nightEps:
            hitNights.append(night.nightDate.isoformat())
            offsets.append(min((e.onsetAt - night.start).total_seconds() / 60 for e in nightEps))

    c1 = len(hitNights) >= cfg.repeatMinNights

    riskStart = tonight.start + timedelta(minutes=min(offsets)) if offsets else tonight.start
    riskEnd = tonight.end
    scope = tonight.nightDate.isoformat()

    locHour = localTime(now, tz).hour + localTime(now, tz).minute / 60
    c2 = locHour >= cfg.predictFromHour and now < riskStart

    aeration = aerationHoursIn(ctx.activities, riskStart, riskEnd)
    c3 = aeration < cfg.minAerationHours

    temp = tempHighNow(ctx.views, now, cfg)
    c4 = temp is not None

    conditions = {"C1": c1, "C2": c2, "C3": c3, "C4": c4}
    met = metFrom(conditions)

    if c1 and not c2:
        return RuleResult(skip=True, fire=False, reason=None, met=met, scope=scope,
                          riskStart=riskStart, riskEnd=riskEnd,
                          evidence={"hitNights": hitNights, "nightsChecked": len(pastNights),
                                    "earliestOffsetMinutes": min(offsets) if offsets else None,
                                    "aerationHours": aeration, "conditions": conditions})

    if c1 and c2 and c3:
        fire, reason = True, None
    elif c1 and c2 and not c3:
        fire, reason = False, "mitigated"
    else:
        fire, reason = False, "conditions_gone"

    evidence: dict[str, object] = {
        "hitNights": hitNights,
        "nightsChecked": len(pastNights),
        "earliestOffsetMinutes": min(offsets) if offsets else None,
        "aerationHours": aeration,
        "conditions": conditions,
    }
    if temp is not None:
        evidence["tempValue"] = temp.value
        evidence["tempZone"] = temp.zone
        evidence["tempTime"] = temp.time

    return RuleResult(skip=False, fire=fire, reason=reason, met=met, scope=scope,
                      riskStart=riskStart, riskEnd=riskEnd, evidence=evidence)
