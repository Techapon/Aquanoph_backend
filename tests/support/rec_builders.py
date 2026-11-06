"""Recommendation-only test builders (Phase 5)."""
from datetime import datetime, timedelta
from typing import Mapping

from identity.analysis.models import (
    PondInfo,
    Recommendation,
    RecStatus,
    SourceRef,
    SignalSource,
    Urgency,
    ApplyMode,
    ProposedActivity,
    ActivityType,
)
from identity.parameters.pond_parameter_enum import PondParameters


def makeRecDraft(
    entryId: str = "AERATE",
    dedupeKey: str = "AERATE:2026-10-25",
    urgency: Urgency = Urgency.urgent,
    validFrom: datetime = datetime(2026, 10, 25, 16, 30),
    validUntil: datetime = datetime(2026, 10, 25, 21, 0),
    sources: tuple[SourceRef, ...] = (),
    proposedActivities: tuple[ProposedActivity, ...] = (),
    applyMode: ApplyMode = ApplyMode.fixed,
    textKey: str = "AERATE.prediction",
    facts: Mapping | None = None,
):
    from identity.recommendation.types import RecDraft

    return RecDraft(
        entryId=entryId,
        dedupeKey=dedupeKey,
        urgency=urgency,
        validFrom=validFrom,
        validUntil=validUntil,
        sources=sources,
        proposedActivities=proposedActivities,
        applyMode=applyMode,
        textKey=textKey,
        facts=facts or {},
    )


def makeRecommendation(
    recId: str = "rec:pond_1:AERATE:2026-10-25T16:30:00",
    pondId: str = "pond_1",
    entryId: str = "AERATE",
    dedupeKey: str = "AERATE:2026-10-25",
    urgency: Urgency = Urgency.urgent,
    validFrom: datetime = datetime(2026, 10, 25, 16, 30),
    validUntil: datetime = datetime(2026, 10, 25, 21, 0),
    title: str = "title",
    reason: str = "reason",
    basedOn: str = "basedOn",
    guidance: tuple[str, ...] = ("g1",),
    proposedActivities: tuple[ProposedActivity, ...] = (),
    applyMode: ApplyMode = ApplyMode.fixed,
    status: RecStatus = RecStatus.pending,
    expireReason: str | None = None,
    sources: tuple[SourceRef, ...] = (),
    snoozeUntil: datetime | None = None,
    createdAt: datetime = datetime(2026, 10, 25, 16, 30),
    updatedAt: datetime = datetime(2026, 10, 25, 16, 30),
) -> Recommendation:
    return Recommendation(
        id=recId,
        pondId=pondId,
        entryId=entryId,
        dedupeKey=dedupeKey,
        urgency=urgency,
        validFrom=validFrom,
        validUntil=validUntil,
        title=title,
        reason=reason,
        basedOn=basedOn,
        guidance=guidance,
        proposedActivities=proposedActivities,
        applyMode=applyMode,
        status=status,
        expireReason=expireReason,
        sources=sources,
        snoozeUntil=snoozeUntil,
        createdAt=createdAt,
        updatedAt=updatedAt,
    )
