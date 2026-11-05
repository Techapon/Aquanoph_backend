"""Core domain models for the analysis pipeline (pure logic).

All models are frozen dataclasses (immutable). Times are naive UTC datetimes.
Strictly follows PHASE_1_foundation.md §2.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from identity.analysis.severity_view import SeverityReportView
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


# Enums per spec §2
class ActivityType(str, Enum):
    feeding = "feeding"
    aeration = "aeration"
    alkalinity = "alkalinity"
    lime = "lime"
    probiotic = "probiotic"
    waterChange = "waterChange"
    other = "other"


class ActivityStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"


class ActivitySource(str, Enum):
    user = "user"
    recommendation = "recommendation"


class Urgency(str, Enum):
    urgent = "urgent"
    nonUrgent = "nonUrgent"


# Alias
RecommendationUrgency = Urgency


class RecStatus(str, Enum):
    pending = "pending"
    snoozed = "snoozed"
    applied = "applied"
    dismissed = "dismissed"
    expired = "expired"


# Alias
RecommendationStatus = RecStatus


class ApplyMode(str, Enum):
    fixed = "fixed"
    pickWindow = "pickWindow"


class PredStatus(str, Enum):
    active = "active"
    ended = "ended"


class DiagStatus(str, Enum):
    open = "open"
    closed = "closed"


class SignalSource(str, Enum):
    episode = "episode"
    prediction = "prediction"
    detector = "detector"


# Alias
SourceKind = SignalSource


class TriggerKind(str, Enum):
    reading = "reading"
    activityEvent = "activityEvent"
    pondEdit = "pondEdit"
    tick = "tick"


# Alias
TriggerType = TriggerKind


@dataclass(frozen=True)
class Activity:
    id: str
    pondId: str
    type: ActivityType
    status: ActivityStatus
    startTime: datetime
    endTime: datetime | None = None
    quantityKg: float | None = None
    fraction: float | None = None
    source: ActivitySource = ActivitySource.user
    sourceRecId: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None

    def __post_init__(self) -> None:
        if self.type == ActivityType.aeration:
            if self.endTime is None or self.endTime <= self.startTime:
                raise ValueError("aeration needs endTime > startTime")
        else:
            if self.endTime is not None:
                raise ValueError(f"other types must not have endTime, got {self.type}")

        if self.type == ActivityType.waterChange:
            if self.fraction is None or not (0.0 < self.fraction <= 1.0):
                raise ValueError(f"fraction must be in (0,1] for waterChange, got {self.fraction}")
        else:
            if self.fraction is not None:
                raise ValueError(f"fraction is only allowed for waterChange, got {self.type}")

        if self.quantityKg is not None and self.quantityKg < 0:
            raise ValueError(f"quantityKg must be >= 0, got {self.quantityKg}")


@dataclass(frozen=True)
class PondInfo:
    pondId: str
    timezone: str = "Asia/Bangkok"
    biomassKg: float = 400.0
    avgWeightG: float = 400.0
    fishCount: int = 1000


# Alias
PondProfile = PondInfo


@dataclass(frozen=True)
class Cause:
    ruleId: str
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagnosticReport:
    id: str
    pondId: str
    parameter: PondParameters
    direction: ThresholdDirection | None
    onsetAt: datetime
    endAt: datetime | None
    status: DiagStatus
    peakSeverity: SeverityLevelType
    lastSeverity: SeverityLevelType
    causes: tuple[Cause, ...]
    noClearCause: bool
    pondSnapshot: PondInfo
    revisedAt: datetime | None = None


@dataclass(frozen=True)
class Prediction:
    id: str
    pondId: str
    ruleId: str
    scope: str | None
    parameter: PondParameters
    expectedZone: ThresholdLevelType
    riskStart: datetime
    riskEnd: datetime
    met: tuple[str, ...]
    status: PredStatus
    endReason: str | None
    evidence: Mapping[str, Any]
    pondSnapshot: PondInfo
    createdAt: datetime
    revisedAt: datetime | None = None


@dataclass(frozen=True)
class SourceRef:
    sourceType: SignalSource
    sourceId: str


@dataclass(frozen=True)
class ProposedActivity:
    type: ActivityType
    startTime: datetime
    endTime: datetime | None = None
    quantityKg: float | None = None
    fraction: float | None = None


@dataclass(frozen=True)
class Recommendation:
    id: str
    pondId: str
    entryId: str
    dedupeKey: str
    urgency: Urgency
    validFrom: datetime
    validUntil: datetime
    title: str
    reason: str
    basedOn: str
    guidance: tuple[str, ...]
    proposedActivities: tuple[ProposedActivity, ...]
    applyMode: ApplyMode
    status: RecStatus
    expireReason: str | None
    sources: tuple[SourceRef, ...]
    snoozeUntil: datetime | None
    createdAt: datetime
    updatedAt: datetime


@dataclass(frozen=True)
class Signal:
    sourceType: SignalSource
    sourceId: str
    code: str
    parameter: PondParameters | None
    active: bool
    riskStart: datetime | None
    riskEnd: datetime | None
    peakSeverity: SeverityLevelType | None
    lastSeverity: SeverityLevelType | None
    scope: str | None
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trigger:
    kind: TriggerKind
    tFrom: datetime | None = None


@dataclass(frozen=True)
class Notification:
    kind: str
    targetType: str
    targetId: str
    reasonKey: str
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PondSnapshot:
    pond: PondInfo
    severityReports: tuple[SeverityReportView, ...]
    activities: tuple[Activity, ...]
    diagnostics: tuple[DiagnosticReport, ...] = ()
    predictions: tuple[Prediction, ...] = ()
    recommendations: tuple[Recommendation, ...] = ()

    def withActivities(self, activities: tuple[Activity, ...]) -> "PondSnapshot":
        return replace(self, activities=activities)

    def withDiagnostics(self, diagnostics: tuple[DiagnosticReport, ...]) -> "PondSnapshot":
        return replace(self, diagnostics=diagnostics)

    def withPredictions(self, predictions: tuple[Prediction, ...]) -> "PondSnapshot":
        return replace(self, predictions=predictions)

    def withRecommendations(self, recommendations: tuple[Recommendation, ...]) -> "PondSnapshot":
        return replace(self, recommendations=recommendations)

    def withSeverityReports(self, severityReports: tuple[SeverityReportView, ...]) -> "PondSnapshot":
        return replace(self, severityReports=severityReports)
