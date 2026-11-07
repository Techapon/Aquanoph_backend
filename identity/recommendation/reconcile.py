"""Recommendation reconcile (Phase 5 §2)."""
from datetime import datetime

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import changedOnly
from identity.analysis.helpers import localDate
from identity.analysis.ids import recId
from identity.analysis.models import (
    ApplyMode,
    Notification,
    RecStatus,
    SignalSource,
    TriggerKind,
    Urgency,
)
from identity.analysis.severity_view import severityRank
from identity.recommendation.catalog import buildDrafts, existingOpenFor
from identity.recommendation.types import RecDraft, ReconcileResult, Renderer
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType


def sourceClosed(ref, signalsById) -> bool:
    """Detector sources never close; missing signal means unknown (keep)."""
    if ref.sourceType == SignalSource.detector:
        return False
    sig = signalsById.get(ref.sourceId)
    if sig is None:
        return False
    return not sig.active


def _allSourcesClosed(rec, signalsById) -> bool:
    return bool(rec.sources) and all(sourceClosed(ref, signalsById) for ref in rec.sources)


def blocked(key, draft, snapshot, now) -> bool:
    """Return True when creation is blocked by dismissed or applied history."""
    for rec in getattr(snapshot, "recommendations", ()):
        if getattr(rec, "dedupeKey", None) != key:
            continue
        if getattr(rec, "status", None) == RecStatus.dismissed and now < getattr(rec, "validUntil", now):
            if getattr(draft, "urgency", None) == Urgency.urgent:
                for param in (getattr(draft.facts, "get", lambda *a: ())("parameters") or ()):
                    for v in getattr(snapshot, "severityReports", ()):
                        if v.parameter == param and v.severity == SeverityLevelType.Critical and v.time > rec.updatedAt:
                            return False
            return True
        if getattr(rec, "status", None) == RecStatus.applied:
            pendingOrDone = [
                a for a in getattr(snapshot, "activities", ())
                if getattr(a, "sourceRecId", None) == rec.id and getattr(a, "status", None) in ("pending", "done")
            ]
            doneUnexpired = [
                a for a in getattr(snapshot, "activities", ())
                if getattr(a, "sourceRecId", None) == rec.id and getattr(a, "status", None) == "done" and now <= rec.validUntil
            ]
            pending = [a for a in pendingOrDone if getattr(a, "status", None) == "pending"]
            if pending or doneUnexpired:
                return True
    return False


def reconcile(snapshot, signals, now, trigger, renderer, cfg=DEFAULT_CONFIG) -> ReconcileResult:
    """Reconcile drafts with open recommendations (Phase 5 §2, deterministic key order)."""
    drafts = buildDrafts(signals, snapshot, now, cfg)
    draftsByKey = {d.dedupeKey: d for d in drafts}
    signalsById = {s.sourceId: s for s in signals}

    updated: list = []
    notifications: list[Notification] = []

    for rec in list(getattr(snapshot, "recommendations", ())):
        if getattr(rec, "status", None) == RecStatus.snoozed and getattr(rec, "snoozeUntil", None) is not None and rec.snoozeUntil <= now:
            newRec = _replace(rec, status=RecStatus.pending, snoozeUntil=None, updatedAt=now)
            updated.append(newRec)
            notifications.append(Notification(kind="recUnsnoozed", targetType="recommendation", targetId=rec.id,
                                               reasonKey="rec.unsnoozed.snooze_over", facts={}))
            rec = newRec

    byId = {r.id: r for r in list(getattr(snapshot, "recommendations", ())) + updated}
    openRecs = [r for r in byId.values() if getattr(r, "status", None) in ("pending", "snoozed")]

    for key in sorted(draftsByKey):
        draft = draftsByKey[key]
        current = next((r for r in openRecs if r.dedupeKey == key), None)
        if current is None:
            continue
        raised = draft.urgency == Urgency.urgent and current.urgency != Urgency.urgent
        # Urgency never lowered while the rec is open.
        mergedUrgency = Urgency.urgent if (current.urgency == Urgency.urgent or draft.urgency == Urgency.urgent) else Urgency.nonUrgent
        mergedApplyMode = ApplyMode.fixed if mergedUrgency == Urgency.urgent else draft.applyMode
        candidate = _replace(
            current,
            urgency=mergedUrgency,
            validFrom=draft.validFrom,
            validUntil=draft.validUntil,
            applyMode=mergedApplyMode,
            proposedActivities=draft.proposedActivities,
            sources=tuple(dict.fromkeys([*current.sources, *draft.sources])),
            status=RecStatus.pending if raised else current.status,
            snoozeUntil=None if raised else current.snoozeUntil,
        )
        text = renderer(draft, snapshot.pond)
        candidate = _replace(candidate, title=text.title, reason=text.reason, basedOn=text.basedOn, guidance=text.guidance)
        if candidate == _withText(current, renderer, draft, snapshot):
            continue
        candidate = _replace(candidate, updatedAt=now)
        updated.append(candidate)
        openRecs = [candidate if r.id == current.id else r for r in openRecs]
        byId[candidate.id] = candidate
        if raised:
            notifications.append(Notification(kind="recChanged", targetType="recommendation", targetId=current.id,
                                               reasonKey="rec.changed.urgency_raised",
                                               facts={"recId": current.id, "entryId": current.entryId,
                                                      "fromUrgency": current.urgency.value, "toUrgency": draft.urgency.value}))
            if current.status == RecStatus.snoozed:
                notifications.append(Notification(kind="recUnsnoozed", targetType="recommendation", targetId=current.id,
                                                   reasonKey="rec.unsnoozed.urgency_raised",
                                                   facts={"recId": current.id, "entryId": current.entryId}))
        if getattr(trigger, "kind", None) == TriggerKind.activityEvent:
            notifications.append(Notification(kind="recChanged", targetType="recommendation", targetId=current.id,
                                               reasonKey="rec.changed.activity_edit",
                                               facts={"recId": current.id, "entryId": current.entryId,
                                                      "tFrom": getattr(trigger, "tFrom", None), "activityType": None}))

    for rec in [r for r in openRecs if r.dedupeKey not in draftsByKey]:
        if rec.id in [u.id for u in updated]:
            continue
        if _allSourcesClosed(rec, signalsById):
            endReasons: list[str] = []
            ruleIds: list[str] = []
            for ref in rec.sources:
                sig = signalsById.get(ref.sourceId)
                if sig is not None:
                    ruleIds.append(getattr(sig, "code", ref.sourceId))
                    endReasons.append("closed")
            updated.append(_replace(rec, status=RecStatus.expired, expireReason="no_longer_applies", updatedAt=now))
            notifications.append(Notification(kind="recExpired", targetType="recommendation", targetId=rec.id,
                                               reasonKey="rec.expired.no_longer_applies",
                                               facts={"recId": rec.id, "entryId": rec.entryId,
                                                      "sourceRuleIds": tuple(ruleIds), "sourceEndReasons": tuple(endReasons),
                                                      "afterActivityEdit": getattr(trigger, "kind", None) == TriggerKind.activityEvent}))
        elif now > rec.validUntil:
            updated.append(_replace(rec, status=RecStatus.expired, expireReason="time_window_over", updatedAt=now))
            notifications.append(Notification(kind="recExpired", targetType="recommendation", targetId=rec.id,
                                               reasonKey="rec.expired.time_window_over",
                                               facts={"recId": rec.id, "entryId": rec.entryId}))

    for key in sorted(draftsByKey):
        draft = draftsByKey[key]
        if any(r.dedupeKey == key and getattr(r, "status", None) in ("pending", "snoozed") for r in byId.values()):
            continue
        if blocked(key, draft, snapshot, now):
            continue
        text = renderer(draft, snapshot.pond)
        newRec = _newRec(snapshot, draft, now, text)
        updated.append(newRec)
        byId[newRec.id] = newRec  # type: ignore[index]
        if draft.urgency == Urgency.urgent:
            notifications.append(Notification(kind="urgentRecCreated", targetType="recommendation", targetId=newRec.id,
                                               reasonKey="rec.created.urgent",
                                               facts={"recId": newRec.id, "entryId": newRec.entryId,
                                                      "dedupeKey": newRec.dedupeKey, "parameters": draft.facts.get("parameters")}))

    existingById = {r.id: r for r in getattr(snapshot, "recommendations", ())}
    changed = changedOnly(tuple(updated), existingById)
    notifications.sort(key=lambda n: (n.kind, n.reasonKey, n.targetId))
    return ReconcileResult(recommendations=changed, notifications=tuple(notifications))


def _replace(rec, **kw):
    from dataclasses import replace
    return replace(rec, **kw)


def _withText(rec, renderer, draft, snapshot):
    text = renderer(draft, snapshot.pond)
    return _replace(rec, title=text.title, reason=text.reason, basedOn=text.basedOn, guidance=text.guidance,
                    urgency=draft.urgency, validFrom=draft.validFrom, validUntil=draft.validUntil,
                    applyMode=draft.applyMode, proposedActivities=draft.proposedActivities,
                    sources=tuple(dict.fromkeys([*rec.sources, *draft.sources])))


def _newRec(snapshot, draft, now, text):
    from identity.analysis.ids import recId
    return type(snapshot.recommendations[0] if getattr(snapshot, "recommendations", ()) else _templateRec())(
        id=recId(snapshot.pond.pondId, draft.dedupeKey, now),
        pondId=snapshot.pond.pondId,
        entryId=draft.entryId,
        dedupeKey=draft.dedupeKey,
        urgency=draft.urgency,
        validFrom=draft.validFrom,
        validUntil=draft.validUntil,
        title=text.title,
        reason=text.reason,
        basedOn=text.basedOn,
        guidance=text.guidance,
        proposedActivities=draft.proposedActivities,
        applyMode=draft.applyMode,
        status=RecStatus.pending,
        expireReason=None,
        sources=draft.sources,
        snoozeUntil=None,
        createdAt=now,
        updatedAt=now,
    )


def _templateRec():
    from tests.support.rec_builders import makeRecommendation
    return makeRecommendation()
