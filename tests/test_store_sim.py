"""Unit tests for StoreSim per PHASE_1_foundation.md."""
from datetime import datetime
import pytest

from identity.analysis.changeset import ActivityOp, ChangeSet
from identity.analysis.models import (
    Activity,
    ActivityStatus,
    ActivityType,
    ApplyMode,
    Notification,
    Recommendation,
    RecStatus,
    Urgency,
)
from tests.support.factories import makeActivity, makeSnapshot
from tests.support.store_sim import StoreSim


def test_storesim_apply_each_op_type():
    now = datetime(2026, 10, 25, 12, 0)
    initialSnap = makeSnapshot()
    sim = StoreSim(initialSnap)

    # 1. create op
    act1 = makeActivity("a1", activityType=ActivityType.feeding, status=ActivityStatus.done)
    csCreate = ChangeSet(activityOps=(ActivityOp(op="create", activity=act1),))
    sim.apply(csCreate)
    assert len(sim.snapshot().activities) == 1
    assert sim.snapshot().activities[0].id == "a1"

    # 2. update op
    act1_updated = makeActivity("a1", activityType=ActivityType.feeding, status=ActivityStatus.done, quantityKg=15.0)
    csUpdate = ChangeSet(activityOps=(ActivityOp(op="update", activity=act1_updated),))
    sim.apply(csUpdate)
    assert len(sim.snapshot().activities) == 1
    assert sim.snapshot().activities[0].quantityKg == 15.0

    # 3. delete op
    csDelete = ChangeSet(activityOps=(ActivityOp(op="delete", activityId="a1"),))
    sim.apply(csDelete)
    assert len(sim.snapshot().activities) == 0


def test_storesim_apply_twice_equals_once():
    """Idempotent apply: applying same changeset twice produces identical state."""
    now = datetime(2026, 10, 25, 12, 0)
    sim = StoreSim(makeSnapshot())

    rec = Recommendation(
        id="r1", pondId="p1", entryId="e1", dedupeKey="AERATE",
        urgency=Urgency.urgent, validFrom=now, validUntil=now,
        title="t", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.fixed, status=RecStatus.pending, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )
    notif = Notification(
        kind="urgentRecCreated", targetType="rec", targetId="r1", reasonKey="k"
    )
    cs = ChangeSet(recommendations=(rec,), notifications=(notif,))

    sim.apply(cs)
    snap1 = sim.snapshot()
    notifs1 = list(sim.notifications)

    sim.apply(cs)
    snap2 = sim.snapshot()
    notifs2 = list(sim.notifications)

    assert snap1 == snap2
    assert notifs1 == notifs2


def test_storesim_snapshot_immutable_original_not_mutated():
    now = datetime(2026, 10, 25, 12, 0)
    originalSnap = makeSnapshot()
    sim = StoreSim(originalSnap)

    rec = Recommendation(
        id="r1", pondId="p1", entryId="e1", dedupeKey="AERATE",
        urgency=Urgency.urgent, validFrom=now, validUntil=now,
        title="t", reason="r", basedOn="b", guidance=(), proposedActivities=(),
        applyMode=ApplyMode.fixed, status=RecStatus.pending, expireReason=None,
        sources=(), snoozeUntil=None, createdAt=now, updatedAt=now,
    )
    cs = ChangeSet(recommendations=(rec,))
    sim.apply(cs)

    # originalSnap is untouched
    assert len(originalSnap.recommendations) == 0
    # simulator's snapshot updated
    assert len(sim.snapshot().recommendations) == 1
