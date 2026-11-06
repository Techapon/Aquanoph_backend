"""Activity-edit validation tests (Phase 7 §4)."""
from datetime import datetime, timedelta

import pytest

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import (
    ActivitySource,
    ActivityStatus,
    ActivityType,
    PondInfo,
    TriggerKind,
)
from services.activity_edit import (
    EditCheck,
    pondEditTrigger,
    triggerForEdit,
    triggerForEdits,
    validateActivityEdit,
)
from tests.support.factories import makeActivity, makePond, t


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 12:00", TZ)
FLOOR = NOW - timedelta(days=DEFAULT_CONFIG.retroWindowDays)


def make(*, startTime=None, status=ActivityStatus.done, source=ActivitySource.user, **kw):
    st = startTime or (NOW - timedelta(hours=1))
    return makeActivity(kw.pop("id", "a1"), activityType=kw.pop("activityType", ActivityType.feeding),
                        status=status, startTime=st, source=source, **kw)


def test_create_ok_and_source_check():
    future = make(startTime=NOW + timedelta(days=5))
    check = validateActivityEdit(None, future, NOW)
    assert check.ok is True

    past = make(startTime=FLOOR - timedelta(seconds=1))
    check2 = validateActivityEdit(None, past, NOW)
    assert check2.ok is False and check2.reason == "outside_retro_window"

    recOrigin = make(source=ActivitySource.recommendation)
    check3 = validateActivityEdit(None, recOrigin, NOW)
    assert check3.ok is False and check3.reason == "invalid_source"


def test_delete_rules():
    userDone = make()
    check = validateActivityEdit(userDone, None, NOW)
    assert check.ok is True

    recOrigin = make(source=ActivitySource.recommendation)
    check2 = validateActivityEdit(recOrigin, None, NOW)
    assert check2.ok is False and check2.reason == "recommendation_activity_not_deletable"

    skipped = make(status=ActivityStatus.skipped)
    assert validateActivityEdit(skipped, None, NOW).ok is True

    old = make(startTime=FLOOR - timedelta(seconds=1))
    check3 = validateActivityEdit(old, None, NOW)
    assert check3.ok is False and check3.reason == "outside_retro_window"


def test_update_status_rollback_and_immutable_fields():
    done = make()
    toPending = make(status=ActivityStatus.pending)
    check = validateActivityEdit(done, toPending, NOW)
    assert check.ok is False and check.reason == "status_rollback"

    skipped = make(status=ActivityStatus.skipped)
    checkSkipped = validateActivityEdit(skipped, toPending, NOW)
    assert checkSkipped.reason == "status_rollback"

    # done <-> skipped allowed
    toSkipped = make(status=ActivityStatus.skipped)
    assert validateActivityEdit(done, toSkipped, NOW).ok is True
    assert validateActivityEdit(toSkipped, done, NOW).ok is True

    # immutable field change
    changedId = make(id="other_id")
    check2 = validateActivityEdit(done, changedId, NOW)
    assert check2.ok is False and check2.reason == "immutable_field"


def test_retro_window_boundaries():
    # exactly at floor ok
    atFloor = make(startTime=FLOOR)
    assert validateActivityEdit(None, atFloor, NOW).ok is True
    # floor - 1 s rejected
    below = make(startTime=FLOOR - timedelta(seconds=1))
    assert validateActivityEdit(None, below, NOW).ok is False
    # future always allowed
    future = make(startTime=NOW + timedelta(days=10))
    assert validateActivityEdit(None, future, NOW).ok is True


def test_trigger_for_edit_and_batch():
    a = make()
    b = make(startTime=a.startTime + timedelta(hours=2))
    trig = triggerForEdit(a, b)
    assert trig.kind == TriggerKind.activityEvent
    assert trig.tFrom == min(a.startTime, b.startTime)

    # batch: all ok -> one trigger with min tFrom
    batch = triggerForEdits([(None, a), (None, b)], NOW)
    assert batch is not None
    assert batch.tFrom == min(a.startTime, b.startTime)

    # batch: any failure -> None
    bad = make(startTime=FLOOR - timedelta(days=1))
    assert triggerForEdits([(None, a), (None, bad)], NOW) is None

    # empty batch -> None
    assert triggerForEdits([], NOW) is None


def test_pond_edit_trigger():
    p1 = makePond(avgWeightG=400.0, fishCount=1000, biomassKg=400.0)
    p2 = makePond(avgWeightG=450.0, fishCount=1000, biomassKg=400.0)
    trig = pondEditTrigger(p1, p2, NOW)
    assert trig is not None and trig.kind == TriggerKind.pondEdit

    # timezone/name changes do not trigger
    p3 = makePond(avgWeightG=400.0, fishCount=1000, biomassKg=400.0, timezone="Asia/Bangkok")
    p4 = makePond(avgWeightG=400.0, fishCount=1000, biomassKg=400.0, timezone="America/New_York")
    assert pondEditTrigger(p3, p4, NOW) is None

    same = makePond(avgWeightG=400.0, fishCount=1000, biomassKg=400.0)
    assert pondEditTrigger(p1, same, NOW) is None
