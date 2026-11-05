"""Deterministic ID generation for pipeline artifacts.

Ensures idempotency across analysis runs (Rule 7).
Strictly follows PHASE_1_foundation.md §3:
  diagId(pondId, parameter, direction, onsetAt)        -> "diag:{pond}:{param}:{dir|-}:{onset iso}"
  predId(pondId, ruleId, scope, createdAt)             -> "pred:{pond}:{rule}:{scope|-}:{createdAt iso}"
  recId(pondId, dedupeKey, createdAt)                  -> "rec:{pond}:{dedupeKey}:{createdAt iso}"
  actId(recId, index)                                  -> "act:{recId}:{index}"
"""
from datetime import datetime
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection


def _ts(dt: datetime) -> str:
    """Format datetime as ISO string for id slug."""
    return dt.isoformat()


def _dir(direction: ThresholdDirection | None) -> str:
    return direction.value if direction else "-"


def _scope(scope: str | None) -> str:
    return scope if scope else "-"


def diagId(
    pondId: str,
    parameter: PondParameters,
    direction: ThresholdDirection | None,
    onsetAt: datetime,
) -> str:
    """diagId(pondId, parameter, direction, onsetAt) -> 'diag:{pond}:{param}:{dir|-}:{onset iso}'."""
    paramName = parameter.value[0] if isinstance(parameter.value, tuple) else str(parameter.value)
    return f"diag:{pondId}:{paramName}:{_dir(direction)}:{_ts(onsetAt)}"


def predId(
    pondId: str,
    ruleId: str,
    scope: str | None,
    createdAt: datetime,
) -> str:
    """predId(pondId, ruleId, scope, createdAt) -> 'pred:{pond}:{rule}:{scope|-}:{createdAt iso}'."""
    return f"pred:{pondId}:{ruleId}:{_scope(scope)}:{_ts(createdAt)}"


def recId(
    pondId: str,
    dedupeKey: str,
    createdAt: datetime,
) -> str:
    """recId(pondId, dedupeKey, createdAt) -> 'rec:{pond}:{dedupeKey}:{createdAt iso}'."""
    return f"rec:{pondId}:{dedupeKey}:{_ts(createdAt)}"


def actId(
    recIdVal: str,
    index: int,
) -> str:
    """actId(recId, index) -> 'act:{recId}:{index}'."""
    return f"act:{recIdVal}:{index}"
