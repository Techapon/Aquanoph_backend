"""Activity-edit validation (Phase 7 §2). Pure logic, never touches the snapshot."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.models import (
    Activity,
    ActivitySource,
    ActivityStatus,
    PondInfo,
    Trigger,
    TriggerKind,
)


@dataclass(frozen=True)
class EditCheck:
    ok: bool
    reason: str | None


def _floor(now: datetime, cfg: AnalysisConfig) -> datetime:
    return now - timedelta(days=cfg.retroWindowDays)


def validateActivityEdit(
    before: Activity | None,
    after: Activity | None,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> EditCheck:
    """Validate a single activity create/edit/delete against the retro window and field rules."""
    if before is None and after is None:
        return EditCheck(ok=False, reason="no_change")

    floor = _floor(now, cfg)

    if before is None and after is not None:
        # Create: any involved startTime before floor rejected; future always allowed.
        if after.startTime < floor:
            return EditCheck(ok=False, reason="outside_retro_window")
        if after.source != ActivitySource.user:
            return EditCheck(ok=False, reason="invalid_source")
        return EditCheck(ok=True, reason=None)

    if after is None and before is not None:
        # Delete: only user activities may be deleted; skipped deletable (default, flagged).
        if before.startTime < floor:
            return EditCheck(ok=False, reason="outside_retro_window")
        if before.source != ActivitySource.user:
            return EditCheck(ok=False, reason="recommendation_activity_not_deletable")
        return EditCheck(ok=True, reason=None)

    assert before is not None and after is not None
    if before.startTime < floor or after.startTime < floor:
        return EditCheck(ok=False, reason="outside_retro_window")

    if before.status == ActivityStatus.done and after.status == ActivityStatus.pending:
        return EditCheck(ok=False, reason="status_rollback")
    if before.status == ActivityStatus.skipped and after.status == ActivityStatus.pending:
        return EditCheck(ok=False, reason="status_rollback")

    # done <-> skipped allowed.
    if (before.id != after.id or before.pondId != after.pondId
            or before.source != after.source or before.sourceRecId != after.sourceRecId
            or before.createdAt != after.createdAt):
        return EditCheck(ok=False, reason="immutable_field")

    return EditCheck(ok=True, reason=None)


def triggerForEdit(before: Activity | None, after: Activity | None) -> Trigger:
    """Build Trigger(activityEvent, tFrom) for a single accepted edit."""
    if before is None and after is not None:
        return Trigger(TriggerKind.activityEvent, tFrom=after.startTime)
    if after is None and before is not None:
        return Trigger(TriggerKind.activityEvent, tFrom=before.startTime)
    assert before is not None and after is not None
    return Trigger(TriggerKind.activityEvent, tFrom=min(before.startTime, after.startTime))


def triggerForEdits(
    edits: Sequence[tuple[Activity | None, Activity | None]],
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> Trigger | None:
    """Batch save is one event: validate all, else None; otherwise Trigger with min tFrom."""
    if not edits:
        return None
    for before, after in edits:
        check = validateActivityEdit(before, after, now, cfg)
        if not check.ok:
            return None
    tFroms = []
    for before, after in edits:
        tFroms.append(triggerForEdit(before, after).tFrom)
    assert all(t is not None for t in tFroms)
    return Trigger(TriggerKind.activityEvent, tFrom=min(t for t in tFroms if t is not None))


def pondEditTrigger(before: PondInfo, after: PondInfo, now: datetime) -> Trigger | None:
    """Return Trigger(pondEdit, tFrom=now) when feed-relevant pond fields changed."""
    if (before.avgWeightG != after.avgWeightG or before.fishCount != after.fishCount
            or before.biomassKg != after.biomassKg):
        return Trigger(TriggerKind.pondEdit, tFrom=now)
    return None
