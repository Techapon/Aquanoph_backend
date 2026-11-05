"""Unit tests for ids.py and changeset.py per PHASE_1_foundation.md."""
from datetime import datetime
import pytest

from identity.analysis.changeset import ActivityOp, ChangeSet, changedOnly
from identity.analysis.ids import actId, diagId, predId, recId
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    ApplyMode,
    DiagnosticReport,
    DiagStatus,
    Notification,
    PondInfo,
    Prediction,
    PredStatus,
    Recommendation,
    RecStatus,
    SourceKind,
    SourceRef,
    Urgency,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity


# ---------- ids: deterministic and distinct for different createdAt ----------
def test_diag_id_format_and_determinism():
    onset = datetime(2026, 10, 25, 12, 0)
    did1 = diagId("p1", PondParameters.DO, None, onset)
    did2 = diagId("p1", PondParameters.DO, None, onset)
    assert did1 == did2
    assert did1 == "diag:p1:DO:-:2026-10-25T12:00:00"

    did_dir = diagId("p1", PondParameters.pH, ThresholdDirection.Low, onset)
    assert did_dir == "diag:p1:pH:low:2026-10-25T12:00:00"


def test_pred_id_format_and_distinct_createdAt():
    t1 = datetime(2026, 10, 25, 12, 0)
    t2 = datetime(2026, 10, 25, 12, 1)
    p1 = predId("p1", "RULE_A", "scope1", t1)
    p2 = predId("p1", "RULE_A", "scope1", t2)
    assert p1 == "pred:p1:RULE_A:scope1:2026-10-25T12:00:00"
    assert p1 != p2


def test_rec_id_format_and_distinct_createdAt():
    t1 = datetime(2026, 10, 25, 12, 0)
    t2 = datetime(2026, 10, 25, 12, 5)
    r1 = recId("p1", "AERATE", t1)
    r2 = recId("p1", "AERATE", t2)
    assert r1 == "rec:p1:AERATE:2026-10-25T12:00:00"
    assert r1 != r2


def test_act_id_format():
    aid = actId("rec:p1:AERATE:2026-10-25T12:00:00", 0)
    assert aid == "act:rec:p1:AERATE:2026-10-25T12:00:00:0"


# ---------- changeset: isEmpty, changedOnly, merge ----------
def test_changeset_is_empty():
    cs = ChangeSet()
    assert cs.isEmpty() is True

    notEmpty = ChangeSet(notifications=(Notification(
        kind="urgentRecCreated", targetType="rec", targetId="r1", reasonKey="k",
    ),))
    assert notEmpty.isEmpty() is False


def test_changed_only_drops_equal_objects():
    now = datetime(2026, 10, 25, 12, 0)
    rec1 = Recommendation(
        id="r1", pondId="p1", entryId="e1", dedupeKey="AERATE",
        urgency=Urgency.urgent, validFrom=now, validUntil=now,
        title="t", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.fixed, status=RecStatus.pending, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )
    rec2 = Recommendation(
        id="r2", pondId="p1", entryId="e2", dedupeKey="WC",
        urgency=Urgency.nonUrgent, validFrom=now, validUntil=now,
        title="t", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.pickWindow, status=RecStatus.pending, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )

    existing = {"r1": rec1}
    filtered = changedOnly((rec1, rec2), existing)
    assert len(filtered) == 1
    assert filtered[0].id == "r2"


def test_merge_later_wins():
    now = datetime(2026, 10, 25, 12, 0)
    rec1 = Recommendation(
        id="r1", pondId="p1", entryId="e1", dedupeKey="AERATE",
        urgency=Urgency.urgent, validFrom=now, validUntil=now,
        title="Early", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.fixed, status=RecStatus.pending, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )
    rec2 = Recommendation(
        id="r1", pondId="p1", entryId="e1", dedupeKey="AERATE",
        urgency=Urgency.urgent, validFrom=now, validUntil=now,
        title="Later", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.fixed, status=RecStatus.applied, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )

    cs1 = ChangeSet(recommendations=(rec1,))
    cs2 = ChangeSet(recommendations=(rec2,))

    merged = cs1.merge(cs2)
    assert len(merged.recommendations) == 1
    assert merged.recommendations[0].title == "Later"
    assert merged.recommendations[0].status == RecStatus.applied
