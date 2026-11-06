"""AERATE catalog entry."""
from datetime import datetime, timedelta

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.helpers import nightWindowFor
from identity.analysis.models import (
    ApplyMode,
    PondInfo,
    ProposedActivity,
    SignalSource,
    SourceRef,
    Urgency,
    ActivityType,
)
from identity.analysis.severity_view import severityRank
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.recommendation.types import RecDraft

ENTRY_ID = "AERATE"


def build(signals, snapshot, now, cfg=DEFAULT_CONFIG):
    preds = [s for s in signals if s.active and s.sourceType == SignalSource.prediction and s.code in ("PRED_DO_NIGHT", "PRED_DO_REPEAT")]
    episodes = [
        s for s in signals
        if s.active and s.sourceType == SignalSource.episode and s.parameter == PondParameters.DO
        and severityRank(s.lastSeverity) >= severityRank(SeverityLevelType.ElevatedRisk)
    ]
    if not preds and not episodes:
        return ()

    nightKeyOf = lambda sig: sig.scope if sig in preds else nightWindowFor(now, snapshot.pond.timezone, cfg).nightDate.isoformat()
    groups: dict[str, dict[str, list]] = {}
    for sig in preds:
        groups.setdefault(sig.scope or "", {"preds": [], "eps": []})["preds"].append(sig)
    for sig in episodes:
        nightDate = nightWindowFor(now, snapshot.pond.timezone, cfg).nightDate.isoformat()
        groups.setdefault(nightDate, {"preds": [], "eps": []})["eps"].append(sig)

    drafts: list[RecDraft] = []
    for nightDate in sorted(groups):
        group = groups[nightDate]
        predsG, epsG = group["preds"], group["eps"]
        aRiskStart = min((s.riskStart for s in predsG), default=None)
        aRiskEnd = max((s.riskEnd for s in predsG), default=None)

        from identity.recommendation.catalog import existingOpenFor
        refs = tuple(SourceRef(s.sourceType, s.sourceId) for s in (*predsG, *epsG))
        existing = existingOpenFor(snapshot, ENTRY_ID, refs)
        dedupeKey = existing.dedupeKey if existing else f"AERATE:{nightDate}"
        anchor = existing.createdAt if existing else now
        raised = existing is not None and existing.urgency != Urgency.urgent
        if raised:
            anchor = now

        if predsG and not epsG:
            assert aRiskStart is not None and aRiskEnd is not None
            planStart = max(anchor, aRiskStart - timedelta(hours=cfg.aerateLeadHours))
            planEnd = aRiskEnd
            validFrom = anchor
            validUntil = min(s.riskStart for s in predsG) + timedelta(hours=cfg.aerateDeadlineAfterRiskStartHours)
            textKey = "AERATE.prediction"
        elif epsG and not predsG:
            planStart = anchor
            planEnd = anchor + timedelta(hours=cfg.aerateDiagDurationHours)
            validFrom = anchor
            validUntil = anchor + timedelta(hours=cfg.aerateDiagDeadlineHours)
            textKey = "AERATE.diagnostic"
        else:
            bPlanEnd = anchor + timedelta(hours=cfg.aerateDiagDurationHours)
            bDeadline = anchor + timedelta(hours=cfg.aerateDiagDeadlineHours)
            planStart = anchor
            planEnd = max(aRiskEnd, bPlanEnd) if aRiskEnd else bPlanEnd
            validFrom = anchor
            validUntil = min(min(s.riskStart for s in predsG) + timedelta(hours=cfg.aerateDeadlineAfterRiskStartHours), bDeadline)
            textKey = "AERATE.both"

        earliestRisk = min((s.riskStart for s in predsG), default=None)
        ruleIds = tuple(sorted({s.code for s in predsG}))
        hitNights = tuple(sorted({s.scope for s in predsG if s.scope})) or None
        nightsChecked = max((len(s.facts.get("hitNights", [])) if s.facts else 0) for s in predsG) if predsG else 0
        facts = {
            "ruleIds": ruleIds or None,
            "riskStart": earliestRisk,
            "riskEnd": aRiskEnd,
            "mealTime": next((s.facts.get("firstMealTime") for s in predsG if s.facts and s.facts.get("firstMealTime")), None),
            "mealKg": next((s.facts.get("firstMealKg") for s in predsG if s.facts and s.facts.get("firstMealKg") is not None), None),
            "mealPct": next((s.facts.get("firstMealPct") for s in predsG if s.facts and s.facts.get("firstMealPct") is not None), None),
            "mealIsPlanned": any(bool(s.facts.get("firstMealTime") and s.facts["firstMealTime"] > now) for s in predsG if s.facts),
            "aerationHours": next((s.facts.get("aerationHours") for s in predsG if s.facts and s.facts.get("aerationHours") is not None), 0.0),
            "tempValue": next((s.facts.get("tempValue") for s in predsG if s.facts and s.facts.get("tempValue") is not None), None),
            "tempZone": next((s.facts.get("tempZone") for s in predsG if s.facts and s.facts.get("tempZone") is not None), None),
            "hitNights": hitNights,
            "nightsChecked": nightsChecked,
            "planStart": planStart,
            "planEnd": planEnd,
            "deadline": validUntil,
            "parameters": (PondParameters.DO,),
            "doLastSeverity": max((s.lastSeverity for s in epsG), key=lambda v: severityRank(v)) if epsG else None,
            "doOnsetAt": min((s.facts.get("onsetAt") for s in epsG if s.facts and s.facts.get("onsetAt")), default=None),
        }

        drafts.append(RecDraft(
            entryId=ENTRY_ID,
            dedupeKey=dedupeKey,
            urgency=Urgency.urgent,
            validFrom=validFrom,
            validUntil=validUntil,
            sources=refs,
            proposedActivities=(ProposedActivity(ActivityType.aeration, planStart, planEnd, None, None),),
            applyMode=ApplyMode.fixed,
            textKey=textKey,
            facts=facts,
        ))
    return tuple(drafts)
