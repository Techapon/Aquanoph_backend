"""WATER_CHANGE catalog entry."""
from datetime import timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.helpers import localDate, localDayBounds
from identity.analysis.models import (
    ActivityType,
    ApplyMode,
    ProposedActivity,
    SignalSource,
    SourceRef,
    Urgency,
)
from identity.analysis.severity_view import severityRank
from identity.parameters.pond_parameter_enum import PondParameters
from identity.recommendation.types import RecDraft
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType

ENTRY_ID = "WATER_CHANGE"


def build(signals, snapshot, now, cfg=DEFAULT_CONFIG):
    episodes = [
        s for s in signals
        if s.active and s.sourceType == SignalSource.episode
        and s.parameter in (PondParameters.NH3, PondParameters.NO2_N)
        and s.lastSeverity is not None
        and severityRank(s.lastSeverity) >= severityRank(SeverityLevelType.ElevatedRisk)
    ]
    preds = [s for s in signals if s.active and s.sourceType == SignalSource.prediction and s.code == "PRED_NH3_RISE"]
    if not episodes and not preds:
        return ()

    from identity.recommendation.catalog import existingOpenFor
    refsAll = tuple(SourceRef(s.sourceType, s.sourceId) for s in (*episodes, *preds))
    existing = existingOpenFor(snapshot, ENTRY_ID, refsAll)
    anchor = existing.createdAt if existing else now
    urgentEps = [s for s in episodes if s.lastSeverity == SeverityLevelType.Critical]
    urgent = bool(urgentEps)
    if existing is not None and urgent and existing.urgency != Urgency.urgent:
        anchor = now
    keyDate = localDate(anchor, snapshot.pond.timezone).isoformat()
    dedupeKey = existing.dedupeKey if existing else f"WATER_CHANGE:{keyDate}"

    refsUrgent = tuple(SourceRef(s.sourceType, s.sourceId) for s in (*urgentEps,)) if urgent else ()
    if urgent:
        sources = tuple(dict.fromkeys([*refsUrgent, *[SourceRef(s.sourceType, s.sourceId) for s in preds]]))
        validFrom = anchor
        validUntil = anchor + timedelta(hours=cfg.wcUrgentDeadlineHours)
        applyMode = ApplyMode.fixed
        textKey = "WATER_CHANGE.episode" if not preds else ("WATER_CHANGE.prediction" if not episodes else "WATER_CHANGE.both")
        fraction = cfg.wcUrgentFraction
    else:
        sources = refsAll
        validFrom = anchor
        nextDay = localDate(anchor, snapshot.pond.timezone) + timedelta(days=2)
        _, validUntil = localDayBounds(localDate(anchor, snapshot.pond.timezone) + timedelta(days=1), snapshot.pond.timezone)
        validUntil = localDayBounds(localDate(anchor, snapshot.pond.timezone) + timedelta(days=1), snapshot.pond.timezone)[1]
        applyMode = ApplyMode.pickWindow
        textKey = "WATER_CHANGE.episode" if episodes and not preds else ("WATER_CHANGE.prediction" if preds and not episodes else "WATER_CHANGE.both")
        fraction = cfg.wcNonUrgentFraction

    predFacts = preds[0].facts if preds else {}
    param = next((s.parameter for s in episodes), PondParameters.NH3)

    facts = {
        "parameter": param,
        "lastSeverity": max((s.lastSeverity for s in episodes), key=lambda v: severityRank(v)) if episodes else None,
        "onsetAt": min((s.facts.get("onsetAt") for s in episodes if s.facts and s.facts.get("onsetAt")), default=None),
        "fraction": fraction,
        "parameters": tuple(sorted({*(s.parameter for s in episodes), *(s.parameter for s in preds if s.parameter)}, key=lambda p: p.name)) or (PondParameters.NH3,),
        "totalMealPct": predFacts.get("totalMealPct"),
        "totalKg": predFacts.get("totalKg"),
        "nh3Zone": predFacts.get("nh3Zone"),
        "nh3Value": predFacts.get("nh3Value"),
        "horizonHours": cfg.nh3RiseHorizonHours if preds else None,
        "windowEnd": validUntil,
    }

    return (RecDraft(
        entryId=ENTRY_ID,
        dedupeKey=dedupeKey,
        urgency=Urgency.urgent if urgent else Urgency.nonUrgent,
        validFrom=validFrom,
        validUntil=validUntil,
        sources=sources,
        proposedActivities=(ProposedActivity(ActivityType.waterChange, anchor, None, None, fraction),),
        applyMode=applyMode,
        textKey=textKey,
        facts=facts,
    ),)
