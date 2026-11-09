"""Apply plan, snooze, dismiss (Phase 5 §3)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ActivityOp, ChangeSet
from identity.analysis.helpers import localDate
from identity.analysis.ids import actId
from identity.analysis.models import (
    Activity,
    ActivitySource,
    ActivityStatus,
    ActivityType,
    ApplyMode,
    Notification,
    RecStatus,
    Urgency,
)
from identity.recommendation.types import ApplyResult


def buildApplyPlan(rec, snapshot, now, chosenTime=None, confirmed=False, cfg=DEFAULT_CONFIG) -> ApplyResult:
    """Build activities/rec update for applying a recommendation (pure)."""
    if getattr(rec, "status", None) not in (RecStatus.pending, RecStatus.snoozed):
        return ApplyResult(status="rejected", reason="not_pending", changeSet=ChangeSet(), summary={})
    if now > rec.validUntil:
        return ApplyResult(status="rejected", reason="expired", changeSet=ChangeSet(), summary={})

    if rec.applyMode == ApplyMode.pickWindow:
        if chosenTime is None:
            return ApplyResult(status="rejected", reason="missing_time", changeSet=ChangeSet(), summary={})
        if not (rec.validFrom <= chosenTime <= rec.validUntil):
            return ApplyResult(status="rejected", reason="time_outside_window", changeSet=ChangeSet(), summary={})

    if rec.entryId == "AERATE":
        return _aerateApply(rec, snapshot, now, cfg)
    if rec.entryId == "WATER_CHANGE":
        return _waterChangeApply(rec, snapshot, now, chosenTime, confirmed, cfg)
    if rec.entryId == "ADD_ALKALINITY":
        return _alkalinityApply(rec, snapshot, now, chosenTime, confirmed, cfg)
    # Generic non-aeration path with same-type conflict handling.
    return _genericApply(rec, snapshot, now, chosenTime, confirmed, cfg)


def _newActivity(actIdVal, rec, start, end, actType, qty, frac, now):
    return Activity(
        id=actIdVal, pondId=rec.pondId, type=actType, status=ActivityStatus.pending,
        startTime=start, endTime=end, quantityKg=qty, fraction=frac,
        source=ActivitySource.recommendation, sourceRecId=rec.id, createdAt=now, updatedAt=now,
    )


def _aerateApply(rec, snapshot, now, cfg):
    riskStarts, riskEnds = [], []
    for ref in rec.sources:
        pred = next((p for p in snapshot.predictions if p.id == ref.sourceId), None)
        if pred is not None:
            riskStarts.append(pred.riskStart)
            riskEnds.append(pred.riskEnd)
    hasEpisode = any(str(getattr(ref, "sourceType", "")).endswith("episode") for ref in rec.sources)
    if riskStarts and not hasEpisode:
        start = max(now, min(riskStarts) - timedelta(hours=cfg.aerateLeadHours))
        end = max(riskEnds)
    elif hasEpisode and not riskStarts:
        start = now
        end = now + timedelta(hours=cfg.aerateDiagDurationHours)
    elif hasEpisode and riskStarts:
        start = now
        end = max(max(riskEnds), now + timedelta(hours=cfg.aerateDiagDurationHours))
    elif rec.proposedActivities:
        stored = rec.proposedActivities[0]
        start = max(now, stored.startTime)
        end = stored.endTime
    else:
        return ApplyResult(status="rejected", reason="invalid_window", changeSet=ChangeSet(), summary={})
    if start >= end:
        return ApplyResult(status="rejected", reason="invalid_window", changeSet=ChangeSet(), summary={})

    rStart, rEnd = start, end
    fixed = tuple(
        a for a in snapshot.activities
        if a.type == ActivityType.aeration and a.status != ActivityStatus.skipped and a.endTime is not None
        and (a.status == ActivityStatus.done or a.source == ActivitySource.recommendation)
    )
    userPending = tuple(
        a for a in snapshot.activities
        if a.type == ActivityType.aeration and a.status == ActivityStatus.pending and a.source == ActivitySource.user and a.endTime is not None
    )

    created, kept = [], []
    cursor = rStart
    # R minus fixed union.
    blocked = sorted([(max(a.startTime, rStart), min(a.endTime, rEnd)) for a in fixed if a.startTime < rEnd and a.endTime > rStart])
    for bStart, bEnd in blocked:
        if cursor < bStart:
            created.append((cursor, bStart))
        kept.append((max(cursor, bStart), bEnd))
        cursor = max(cursor, bEnd)
    if cursor < rEnd:
        created.append((cursor, rEnd))
    minSeg = timedelta(minutes=cfg.minAerationSegmentMinutes)
    created = [(s, e) for s, e in created if e - s >= minSeg]

    if not created:
        from dataclasses import replace
        updated = replace(rec, status=RecStatus.applied, updatedAt=now)
        return ApplyResult(status="applied", reason=None,
                           changeSet=ChangeSet(activityOps=(), recommendations=(updated,)),
                           summary={"created": (), "modified": (), "kept": tuple(kept), "coveredByDone": True})

    ops: list[ActivityOp] = []
    notifications: list[Notification] = []
    modified: list[dict] = []
    actIndex = 0
    for s, e in created:
        ops.append(ActivityOp(op="create", activity=_newActivity(actId(rec.id, actIndex), rec, s, e, ActivityType.aeration, None, None, now)))
        actIndex += 1

    for act in sorted(userPending, key=lambda a: a.startTime):
        if act.endTime <= rStart or act.startTime >= rEnd:
            continue
        keepBefore = (act.startTime, min(act.endTime, rStart)) if act.startTime < rStart else None
        keepAfter = (max(act.startTime, rEnd), act.endTime) if act.endTime > rEnd else None
        keeps = [k for k in (keepBefore, keepAfter) if k and k[1] - k[0] >= minSeg]
        before = (act.startTime, act.endTime)
        from dataclasses import replace
        if not keeps:
            ops.append(ActivityOp(op="delete", activityId=act.id))
            modified.append({"activityId": act.id, "before": before, "after": ()})
        elif len(keeps) == 1:
            ops.append(ActivityOp(op="update", activity=replace(act, startTime=keeps[0][0], endTime=keeps[0][1], updatedAt=now)))
            modified.append({"activityId": act.id, "before": before, "after": keeps[0]})
        else:
            ops.append(ActivityOp(op="update", activity=replace(act, startTime=keeps[0][0], endTime=keeps[0][1], updatedAt=now)))
            newAct = replace(act, id=actId(rec.id, actIndex), startTime=keeps[1][0], endTime=keeps[1][1])
            actIndex += 1
            ops.append(ActivityOp(op="create", activity=newAct))
            modified.append({"activityId": act.id, "before": before, "after": tuple(keeps)})
        notifications.append(Notification(kind="activityReplaced", targetType="activity", targetId=act.id,
                                           reasonKey="activity.replaced.by_recommendation",
                                           facts={"activityId": act.id, "recId": rec.id, "before": before,
                                                  "after": tuple(keeps) if keeps else ()}))

    from dataclasses import replace
    updated = replace(rec, status=RecStatus.applied, updatedAt=now)
    return ApplyResult(status="applied", reason=None,
                       changeSet=ChangeSet(activityOps=tuple(ops), recommendations=(updated,), notifications=tuple(notifications)),
                       summary={"created": tuple(created), "modified": tuple(modified), "kept": tuple(kept), "coveredByDone": False})


def _waterChangeApply(rec, snapshot, now, chosenTime, confirmed, cfg):
    fraction = rec.proposedActivities[0].fraction if rec.proposedActivities else cfg.wcNonUrgentFraction
    at = now if rec.urgency == Urgency.urgent else chosenTime
    return _singleActivityApply(rec, snapshot, now, at, ActivityType.waterChange, None, fraction, confirmed)


def _alkalinityApply(rec, snapshot, now, chosenTime, confirmed, cfg):
    return _singleActivityApply(rec, snapshot, now, chosenTime, ActivityType.alkalinity, None, None, confirmed)


def _genericApply(rec, snapshot, now, chosenTime, confirmed, cfg):
    at = now if rec.urgency == Urgency.urgent else chosenTime
    if not rec.proposedActivities:
        raise ValueError(f"rec {rec.id}: generic apply requires proposedActivities")
    stored = rec.proposedActivities[0]
    return _singleActivityApply(rec, snapshot, now, at, stored.type, stored.quantityKg, stored.fraction, confirmed)


def _singleActivityApply(rec, snapshot, now, at, actType, qty, frac, confirmed):
    conflicts = [
        a for a in snapshot.activities
        if a.type == actType and a.status != ActivityStatus.skipped
        and rec.validFrom <= a.startTime <= rec.validUntil
    ]
    if actType == ActivityType.aeration and conflicts:
        return ApplyResult(status="rejected", reason="aeration_overlap", changeSet=ChangeSet(),
                           summary={"conflicts": tuple(a.id for a in conflicts)})
    if conflicts and not confirmed:
        return ApplyResult(status="needsDecision", reason=None, changeSet=ChangeSet(),
                           summary={"conflicts": tuple(a.id for a in conflicts)})

    stored = rec.proposedActivities[0] if rec.proposedActivities else None
    end = stored.endTime if (actType == ActivityType.aeration and stored is not None) else None
    from dataclasses import replace
    newAct = _newActivity(actId(rec.id, 0), rec, at, end, actType, qty, frac, now)
    updated = replace(rec, status=RecStatus.applied, updatedAt=now)
    return ApplyResult(status="applied", reason=None,
                       changeSet=ChangeSet(activityOps=(ActivityOp(op="create", activity=newAct),),
                                           recommendations=(updated,)),
                       summary={"created": ((at, end),)})


def snoozeRec(rec, until, now, cfg=DEFAULT_CONFIG):
    """Snooze a pending non-urgent rec until `until`."""
    if rec.status != RecStatus.pending or rec.urgency != Urgency.nonUrgent:
        raise ValueError("only pending non-urgent recs can be snoozed")
    if not (now < until <= rec.validUntil):
        raise ValueError("snooze time must satisfy now < until <= validUntil")
    from dataclasses import replace
    updated = replace(rec, status=RecStatus.snoozed, snoozeUntil=until, updatedAt=now)
    return ChangeSet(recommendations=(updated,))


def dismissRec(rec, now):
    """Dismiss a pending or snoozed rec."""
    if rec.status not in (RecStatus.pending, RecStatus.snoozed):
        raise ValueError("only pending/snoozed recs can be dismissed")
    from dataclasses import replace
    return ChangeSet(recommendations=(replace(rec, status=RecStatus.dismissed, updatedAt=now),))
