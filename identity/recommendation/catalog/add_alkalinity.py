"""ADD_ALKALINITY catalog entry."""
from datetime import timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import (
    ActivityType,
    ApplyMode,
    ProposedActivity,
    SignalSource,
    SourceRef,
    Urgency,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.recommendation.types import RecDraft

ENTRY_ID = "ADD_ALKALINITY"


def build(signals, snapshot, now, cfg=DEFAULT_CONFIG):
    det = [s for s in signals if s.active and s.sourceType == SignalSource.detector and s.code == "PH_SWING"]
    if not det:
        return ()

    sig = det[0]
    from identity.recommendation.catalog import existingOpenFor
    refs = (SourceRef(sig.sourceType, sig.sourceId),)
    existing = existingOpenFor(snapshot, ENTRY_ID, refs)
    anchor = existing.createdAt if existing else now
    dedupeKey = existing.dedupeKey if existing else ENTRY_ID
    raised = existing is not None and existing.urgency != Urgency.nonUrgent
    if raised:
        anchor = now

    validFrom = anchor
    validUntil = anchor + timedelta(days=cfg.alkalinityWindowDays)

    facts = {
        "hitDays": sig.facts.get("hitDays"),
        "windowDays": sig.facts.get("windowDays"),
        "maxSwing": max((d.get("swing", 0.0) for d in sig.facts.get("days", ())), default=0.0),
        "windowEnd": validUntil,
        "parameters": (PondParameters.pH,),
    }

    return (RecDraft(
        entryId=ENTRY_ID,
        dedupeKey=dedupeKey,
        urgency=Urgency.nonUrgent,
        validFrom=validFrom,
        validUntil=validUntil,
        sources=refs,
        proposedActivities=(ProposedActivity(ActivityType.alkalinity, anchor, None, None, None),),
        applyMode=ApplyMode.pickWindow,
        textKey="ADD_ALKALINITY.detector",
        facts=facts,
    ),)
