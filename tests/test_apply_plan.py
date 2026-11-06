"""Apply plan / snooze / dismiss tests (Phase 5 §4)."""
from datetime import datetime, timedelta

import pytest

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    ActivitySource,
    ActivityStatus,
    ActivityType,
    ApplyMode,
    RecStatus,
    Signal,
    SignalSource,
    SourceRef,
    Urgency,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.recommendation.apply_plan import buildApplyPlan, dismissRec, snoozeRec
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeSnapshot, t
from tests.support.pred_builders import makePrediction
from tests.support.rec_builders import makeRecommendation
from tests.support.store_sim import StoreSim


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)


def aerateRec(**kw):
    kw.setdefault("entryId", "AERATE")
    kw.setdefault("dedupeKey", "AERATE:2026-10-25")
    kw.setdefault("urgency", Urgency.urgent)
    kw.setdefault("applyMode", ApplyMode.fixed)
    kw.setdefault("validFrom", NOW)
    kw.setdefault("validUntil", NOW + timedelta(hours=3))
    kw.setdefault("proposedActivities", (__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
        ActivityType.aeration, t("2026-10-25 19:00", TZ), t("2026-10-26 06:00", TZ), None, None),))
    kw.setdefault("sources", (SourceRef(SignalSource.prediction, "pred:1"),))
    kw.setdefault("createdAt", NOW)
    kw.setdefault("updatedAt", NOW)
    return makeRecommendation(**kw)


def predInSnapshot(riskStart, riskEnd):
    return makePrediction(
        predId="pred:1", ruleId="PRED_DO_NIGHT", scope="2026-10-25",
        parameter=PondParameters.DO, riskStart=riskStart, riskEnd=riskEnd,
        createdAt=NOW,
    )


def test_t3_urgent_apply_times_and_deadline():
    snap = makeSnapshot(
        pond=makePond(),
        predictions=[predInSnapshot(t("2026-10-25 20:00", TZ), t("2026-10-26 06:00", TZ))],
    )
    rec = aerateRec()
    applyAt = t("2026-10-25 19:10", TZ)
    plan = buildApplyPlan(rec, snap, applyAt, cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    act = plan.changeSet.activityOps[0].activity
    assert act.startTime == applyAt
    assert act.endTime == t("2026-10-26 06:00", TZ)
    assert act.status == ActivityStatus.pending
    assert act.source == ActivitySource.recommendation
    assert act.sourceRecId == rec.id
    assert plan.changeSet.recommendations[0].status == RecStatus.applied

    earlier = t("2026-10-25 18:00", TZ)
    plan2 = buildApplyPlan(rec, snap, earlier, cfg=DEFAULT_CONFIG)
    act2 = plan2.changeSet.activityOps[0].activity
    assert act2.startTime == t("2026-10-25 19:00", TZ)  # riskStart - 1h

    late = t("2026-10-25 21:30", TZ)
    plan3 = buildApplyPlan(rec, snap, late, cfg=DEFAULT_CONFIG)
    assert plan3.status == "rejected" and plan3.reason == "expired"


def test_apply_after_already_applied_is_rejected():
    snap = makeSnapshot(pond=makePond())
    applied = aerateRec(status=RecStatus.applied)
    plan = buildApplyPlan(applied, snap, NOW, cfg=DEFAULT_CONFIG)
    assert plan.status == "rejected" and plan.reason == "not_pending"


def test_d15_user_pending_overlap():
    userAct = makeActivity("u1", activityType=ActivityType.aeration, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 21:00", TZ), endTime=t("2026-10-25 23:00", TZ))
    userAct = __import__("dataclasses", fromlist=["replace"]).replace(userAct, source=ActivitySource.user)
    snap = makeSnapshot(pond=makePond(), activities=[userAct])
    rec = aerateRec(
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.aeration, t("2026-10-25 22:00", TZ), t("2026-10-26 03:00", TZ), None, None),),
    )
    applyAt = t("2026-10-25 17:00", TZ)
    plan = buildApplyPlan(rec, snap, applyAt, cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    creates = [op for op in plan.changeSet.activityOps if op.op == "create"]
    updates = [op for op in plan.changeSet.activityOps if op.op == "update"]
    # R = 22:00-03:00, user 21:00-23:00 overlaps 22:00-23:00 -> user becomes 21:00-22:00, R created whole
    assert len(updates) == 1
    assert updates[0].activity.startTime == t("2026-10-25 21:00", TZ)
    assert updates[0].activity.endTime == t("2026-10-25 22:00", TZ)
    assert len(creates) >= 1
    assert any(n.kind == "activityReplaced" for n in plan.changeSet.notifications)


def test_t14_done_aeration_pieces_and_coverage():
    doneAct = makeActivity("d1", activityType=ActivityType.aeration, status=ActivityStatus.done,
                           startTime=t("2026-10-25 22:00", TZ), endTime=t("2026-10-26 02:00", TZ))
    snap = makeSnapshot(pond=makePond(), activities=[doneAct])
    rec = aerateRec(
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.aeration, t("2026-10-25 19:00", TZ), t("2026-10-26 06:00", TZ), None, None),),
    )
    plan = buildApplyPlan(rec, snap, NOW, cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    creates = [op.activity for op in plan.changeSet.activityOps if op.op == "create"]
    assert len(creates) == 2
    assert (creates[0].startTime, creates[0].endTime) == (t("2026-10-25 19:00", TZ), t("2026-10-25 22:00", TZ))
    assert (creates[1].startTime, creates[1].endTime) == (t("2026-10-26 02:00", TZ), t("2026-10-26 06:00", TZ))
    assert plan.summary["kept"] == ((t("2026-10-25 22:00", TZ), t("2026-10-26 02:00", TZ)),)

    # done covers all R
    fullDone = makeActivity("d2", activityType=ActivityType.aeration, status=ActivityStatus.done,
                            startTime=t("2026-10-25 19:00", TZ), endTime=t("2026-10-26 06:00", TZ))
    snap2 = makeSnapshot(pond=makePond(), activities=[fullDone])
    plan2 = buildApplyPlan(rec, snap2, NOW, cfg=DEFAULT_CONFIG)
    assert plan2.status == "applied"
    assert plan2.changeSet.activityOps == ()
    assert plan2.summary["coveredByDone"] is True


def test_short_pieces_dropped():
    doneAct = makeActivity("d1", activityType=ActivityType.aeration, status=ActivityStatus.done,
                           startTime=t("2026-10-25 22:00", TZ), endTime=t("2026-10-26 02:00", TZ))
    snap = makeSnapshot(pond=makePond(), activities=[doneAct])
    # R 21:50-02:10 -> left piece 21:50-22:00 (10 min) dropped; right 02:00-02:10 (10 min) dropped
    rec = aerateRec(
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.aeration, t("2026-10-25 21:50", TZ), t("2026-10-26 02:10", TZ), None, None),),
    )
    plan = buildApplyPlan(rec, snap, NOW, cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    assert plan.changeSet.activityOps == ()
    assert plan.summary["coveredByDone"] is True


def test_snapshot_untouched_and_invalid_window():
    snap = makeSnapshot(pond=makePond())
    rec = aerateRec(
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.aeration, t("2026-10-25 06:00", TZ), t("2026-10-25 05:00", TZ), None, None),),
    )
    plan = buildApplyPlan(rec, snap, NOW, cfg=DEFAULT_CONFIG)
    assert plan.status == "rejected"
    assert snap.activities == ()


def test_t13_chosen_time_and_conflicts():
    urgentRec = makeRecommendation(
        entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
        urgency=Urgency.urgent, applyMode=ApplyMode.fixed,
        validFrom=NOW, validUntil=NOW + timedelta(hours=3),
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.waterChange, NOW, None, None, 0.5),),
        createdAt=NOW, updatedAt=NOW,
    )
    snap = makeSnapshot(pond=makePond())
    plan = buildApplyPlan(urgentRec, snap, NOW, cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    act = plan.changeSet.activityOps[0].activity
    assert act.fraction == 0.5

    nonUrgent = makeRecommendation(
        entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
        urgency=Urgency.nonUrgent, applyMode=ApplyMode.pickWindow,
        validFrom=NOW, validUntil=NOW + timedelta(days=1),
        proposedActivities=(__import__("identity.analysis.models", fromlist=["ProposedActivity"]).ProposedActivity(
            ActivityType.waterChange, NOW, None, None, 0.25),),
        createdAt=NOW, updatedAt=NOW,
    )
    assert buildApplyPlan(nonUrgent, snap, NOW, cfg=DEFAULT_CONFIG).reason == "missing_time"
    early = buildApplyPlan(nonUrgent, snap, NOW, chosenTime=NOW - timedelta(minutes=1), cfg=DEFAULT_CONFIG)
    assert early.reason == "time_outside_window"
    ok = buildApplyPlan(nonUrgent, snap, NOW, chosenTime=NOW + timedelta(hours=5), cfg=DEFAULT_CONFIG)
    assert ok.status == "applied"
    assert ok.changeSet.activityOps[0].activity.fraction == 0.25

    pendingWc = makeActivity("w", activityType=ActivityType.waterChange, status=ActivityStatus.pending,
                             startTime=NOW + timedelta(hours=1))
    snapConf = makeSnapshot(pond=makePond(), activities=[pendingWc])
    conflicted = buildApplyPlan(nonUrgent, snapConf, NOW, chosenTime=NOW + timedelta(hours=5), cfg=DEFAULT_CONFIG)
    assert conflicted.status == "needsDecision"
    confirmed = buildApplyPlan(nonUrgent, snapConf, NOW, chosenTime=NOW + timedelta(hours=5), confirmed=True, cfg=DEFAULT_CONFIG)
    assert confirmed.status == "applied"

    skippedWc = makeActivity("w", activityType=ActivityType.waterChange, status=ActivityStatus.skipped,
                             startTime=NOW + timedelta(hours=1))
    snapSkipped = makeSnapshot(pond=makePond(), activities=[skippedWc])
    assert buildApplyPlan(nonUrgent, snapSkipped, NOW, chosenTime=NOW + timedelta(hours=5), cfg=DEFAULT_CONFIG).status == "applied"


def test_missing_prediction_source_falls_back_to_stored_plan():
    snap = makeSnapshot(pond=makePond())
    rec = aerateRec()  # sources reference pred:1 but snapshot has no predictions
    plan = buildApplyPlan(rec, snap, t("2026-10-25 19:10", TZ), cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    act = plan.changeSet.activityOps[0].activity
    assert act.startTime == t("2026-10-25 19:10", TZ)
    assert act.endTime == t("2026-10-26 06:00", TZ)


def test_snooze_and_dismiss():
    nonUrgent = makeRecommendation(
        entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
        urgency=Urgency.nonUrgent, applyMode=ApplyMode.pickWindow,
        validFrom=NOW, validUntil=NOW + timedelta(days=1),
        createdAt=NOW, updatedAt=NOW,
    )
    until = NOW + timedelta(hours=5)
    cs = snoozeRec(nonUrgent, until, NOW)
    assert cs.recommendations[0].status == RecStatus.snoozed
    assert cs.recommendations[0].snoozeUntil == until

    urgent = aerateRec()
    with pytest.raises(ValueError):
        snoozeRec(urgent, until, NOW)
    with pytest.raises(ValueError):
        snoozeRec(nonUrgent, NOW + timedelta(days=2), NOW)

    ds = dismissRec(nonUrgent, NOW)
    assert ds.recommendations[0].status == RecStatus.dismissed
    with pytest.raises(ValueError):
        dismissRec(makeRecommendation(status=RecStatus.applied), NOW)
