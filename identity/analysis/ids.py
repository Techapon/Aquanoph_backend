"""Deterministic ID generation for pipeline artifacts.

Ensures idempotency across analysis runs (Rule 7).
"""
import hashlib
from datetime import datetime
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection


def _digest(raw: str) -> str:
    """Return a compact, deterministic 12-char hex digest."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def episodeId(
    pondId: str,
    parameter: PondParameters,
    direction: ThresholdDirection | None,
    startedAt: datetime,
) -> str:
    dirStr = direction.value if direction else "none"
    ts = startedAt.isoformat()
    slug = f"{pondId}:{parameter.value}:{dirStr}:{ts}"
    return f"ep_{parameter.value}_{_digest(slug)}"


def detectorId(
    pondId: str,
    detectorName: str,
    startedAt: datetime,
) -> str:
    ts = startedAt.isoformat()
    slug = f"{pondId}:{detectorName}:{ts}"
    return f"det_{detectorName.lower()}_{_digest(slug)}"


def predictionId(
    pondId: str,
    ruleName: str,
    predictedFor: datetime,
) -> str:
    ts = predictedFor.isoformat()
    slug = f"{pondId}:{ruleName}:{ts}"
    return f"pred_{ruleName.lower()}_{_digest(slug)}"


def recommendationId(
    pondId: str,
    dedupeKey: str,
    createdAt: datetime,
) -> str:
    ts = createdAt.isoformat()
    slug = f"{pondId}:{dedupeKey}:{ts}"
    return f"rec_{_digest(slug)}"


def notificationId(
    pondId: str,
    titleKey: str,
    createdAt: datetime,
) -> str:
    ts = createdAt.isoformat()
    slug = f"{pondId}:{titleKey}:{ts}"
    return f"notif_{_digest(slug)}"
