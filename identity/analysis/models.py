"""Core domain models for the analysis pipeline (pure logic).

All models are frozen dataclasses (immutable). Times are naive UTC datetimes.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


class TriggerType(str, Enum):
    reading = "reading"
    activity = "activity"
    edit = "edit"
    tick = "tick"


@dataclass(frozen=True)
class Trigger:
    triggerType: TriggerType
    triggeredAt: datetime
    details: dict[str, Any] = field(default_factory=dict)


class ActivityType(str, Enum):
    feeding = "feeding"
    aeration = "aeration"
    alkalinity = "alkalinity"
    lime = "lime"
    probiotic = "probiotic"
    water_change = "water_change"
    other = "other"


class ActivityStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"


class ActivitySource(str, Enum):
    user = "user"
    recommendation = "recommendation"


@dataclass(frozen=True)
class Activity:
    id: str
    pondId: str
    activityType: ActivityType
    status: ActivityStatus
    source: ActivitySource
    scheduledAt: datetime
    startedAt: datetime | None = None
    completedAt: datetime | None = None
    amount: float | None = None          # kg for feed/chemicals; fraction (0..1) for water_change
    note: str | None = None
    recommendationId: str | None = None
    revisedAt: datetime | None = None


class RecommendationUrgency(str, Enum):
    urgent = "urgent"
    non_urgent = "non_urgent"


class RecommendationStatus(str, Enum):
    pending = "pending"
    snoozed = "snoozed"
    applied = "applied"
    dismissed = "dismissed"
    expired = "expired"


class SourceKind(str, Enum):
    episode = "episode"
    prediction = "prediction"
    detector = "detector"


@dataclass(frozen=True)
class SourceRef:
    kind: SourceKind
    sourceId: str


@dataclass(frozen=True)
class Recommendation:
    id: str
    pondId: str
    dedupeKey: str
    actionType: str                      # "AERATE", "WATER_CHANGE", "ADD_ALKALINITY", etc.
    urgency: RecommendationUrgency
    status: RecommendationStatus
    sources: tuple[SourceRef, ...]
    createdAt: datetime
    deadline: datetime | None = None
    windowStart: datetime | None = None
    windowEnd: datetime | None = None
    snoozedUntil: datetime | None = None
    appliedAt: datetime | None = None
    dismissedAt: datetime | None = None
    expiredAt: datetime | None = None
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Notification:
    id: str
    pondId: str
    createdAt: datetime
    titleKey: str
    bodyKey: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PondProfile:
    id: str
    name: str
    species: str                         # "nile_tilapia"
    areaM2: float
    depthM: float
    targetDensityKgM3: float
    fishCount: int
    avgWeightG: float
    timezone: str = "Asia/Bangkok"       # IANA timezone string

    @property
    def volumeM3(self) -> float:
        return self.areaM2 * self.depthM

    @property
    def totalBiomassKg(self) -> float:
        return (self.fishCount * self.avgWeightG) / 1000.0


@dataclass(frozen=True)
class PondSnapshot:
    pond: PondProfile
    latestReadings: dict[PondParameters, Any]         # PondParameters -> AnalysisReportModel
    readingHistory: tuple[Any, ...]                   # tuple of AnalysisReportModel
    activities: tuple[Activity, ...]                  # history of activities
    activeEpisodes: tuple[Any, ...] = ()              # open Episode models
    closedEpisodes: tuple[Any, ...] = ()
    activePredictions: tuple[Any, ...] = ()
    activeDetectors: tuple[Any, ...] = ()
    recommendations: tuple[Recommendation, ...] = ()
