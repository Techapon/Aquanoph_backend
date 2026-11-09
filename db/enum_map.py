"""Python <-> Postgres enum name mapping. Single source of truth (CONFIG ข้อ 1).

DB enum values use clean snake_case names; the Python side keeps the
engine's historical names (incl. the "hight risk" typo and `tem`).

Activity kinds: 6 only (no `other`, CONFIG ข้อ 4).
"""
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    ApplyMode,
    DiagStatus,
    PredStatus,
    RecStatus,
    SignalSource,
    TriggerKind,
    Urgency,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


def _pairs(py_items, db_names):
    """zip python members with db names (same order)."""
    names = [db_names] if isinstance(db_names, str) else db_names
    if len(names) != len(py_items):
        raise ValueError(f"expected {len(py_items)} names, got {len(names)}")
    to_db = {py: db for py, db in zip(py_items, names)}
    to_py = {db: py for py, db in zip(py_items, names)}
    return to_db, to_py


PARAMETER_TO_DB, PARAMETER_FROM_DB = _pairs(
    [PondParameters.DO, PondParameters.NH3, PondParameters.NO2_N, PondParameters.pH,
     PondParameters.tem, PondParameters.salinity],
    ["DO", "NH3", "NO2_N", "pH", "Temperature", "Salinity"],
)

ZONE_TO_DB, ZONE_FROM_DB = _pairs(
    [ThresholdLevelType.Optimal, ThresholdLevelType.Stress,
     ThresholdLevelType.HighRisk, ThresholdLevelType.Critical],
    ["optimal", "stress", "high_risk", "critical"],
)

SEVERITY_TO_DB, SEVERITY_FROM_DB = _pairs(
    [SeverityLevelType.Optimal, SeverityLevelType.Stress,
     SeverityLevelType.ElevatedRisk, SeverityLevelType.Critical],
    ["optimal", "stress", "elevated_risk", "critical"],
)

DIRECTION_TO_DB, DIRECTION_FROM_DB = _pairs(
    [ThresholdDirection.Low, ThresholdDirection.High],
    ["low", "high"],
)

ACTIVITY_TYPE_TO_DB, ACTIVITY_TYPE_FROM_DB = _pairs(
    [ActivityType.feeding, ActivityType.aeration, ActivityType.alkalinity,
     ActivityType.lime, ActivityType.probiotic, ActivityType.waterChange],
    ["feeding", "aeration", "alkalinity", "lime", "probiotic", "water_change"],
)

ACTIVITY_STATUS_TO_DB, ACTIVITY_STATUS_FROM_DB = _pairs(
    [ActivityStatus.pending, ActivityStatus.done, ActivityStatus.skipped],
    ["pending", "done", "skipped"],
)

URGENCY_TO_DB, URGENCY_FROM_DB = _pairs(
    [Urgency.urgent, Urgency.nonUrgent],
    ["urgent", "non_urgent"],
)

REC_STATUS_TO_DB, REC_STATUS_FROM_DB = _pairs(
    [RecStatus.pending, RecStatus.snoozed, RecStatus.applied,
     RecStatus.dismissed, RecStatus.expired],
    ["pending", "snoozed", "applied", "dismissed", "expired"],
)

APPLY_MODE_TO_DB, APPLY_MODE_FROM_DB = _pairs(
    [ApplyMode.fixed, ApplyMode.pickWindow],
    ["fixed", "pick_window"],
)

PRED_STATUS_TO_DB, PRED_STATUS_FROM_DB = _pairs(
    [PredStatus.active, PredStatus.ended],
    ["active", "ended"],
)

DIAG_STATUS_TO_DB, DIAG_STATUS_FROM_DB = _pairs(
    [DiagStatus.open, DiagStatus.closed],
    ["open", "closed"],
)

SIGNAL_SOURCE_TO_DB, SIGNAL_SOURCE_FROM_DB = _pairs(
    [SignalSource.episode, SignalSource.prediction, SignalSource.detector],
    ["episode", "prediction", "detector"],
)

# ponytail: TriggerKind has no DB enum (kinds live in analysis_jobs.kinds text[]).
