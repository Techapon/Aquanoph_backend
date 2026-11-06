"""Shared recommendation draft/result types (Phase 5, contracts §3.1)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping

from identity.analysis.models import Notification, PondInfo, Recommendation, SourceRef, ProposedActivity, Urgency, ApplyMode


@dataclass(frozen=True)
class RecDraft:
    entryId: str
    dedupeKey: str
    urgency: Urgency
    validFrom: datetime
    validUntil: datetime
    sources: tuple[SourceRef, ...]
    proposedActivities: tuple[ProposedActivity, ...]
    applyMode: ApplyMode
    textKey: str
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderedText:
    title: str
    reason: str
    basedOn: str
    guidance: tuple[str, ...]


Renderer = Callable[[RecDraft, PondInfo], RenderedText]


@dataclass(frozen=True)
class ReconcileResult:
    recommendations: tuple[Recommendation, ...]
    notifications: tuple[Notification, ...]


@dataclass(frozen=True)
class ApplyResult:
    status: str
    reason: str | None
    changeSet: Any
    summary: Mapping[str, Any] = field(default_factory=dict)
