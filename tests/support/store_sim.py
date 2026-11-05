"""StoreSim — simulates the database applying a ChangeSet to a PondSnapshot.

Used in integration and scenario tests (Contract §3).
Strictly follows PHASE_1_foundation.md §6:
  StoreSim(snapshot) with .apply(changeset), .snapshot(), .notifications.
  Upsert diagnostics/predictions/recommendations by id; apply activityOps; record notifications.
"""
from dataclasses import replace
from typing import Any

from identity.analysis.changeset import ActivityOp, ChangeSet
from identity.analysis.models import (
    Activity,
    DiagnosticReport,
    Notification,
    PondSnapshot,
    Prediction,
    Recommendation,
)


class StoreSim:
    def __init__(self, initialSnapshot: PondSnapshot):
        self._snapshot = initialSnapshot
        self.notifications: list[Notification] = []

    def snapshot(self) -> PondSnapshot:
        return self._snapshot

    def apply(self, changeset: ChangeSet) -> None:
        # 1. Diagnostics (upsert by id)
        diagMap = {d.id: d for d in self._snapshot.diagnostics}
        for d in changeset.diagnostics:
            diagMap[d.id] = d

        # 2. Predictions (upsert by id)
        predMap = {p.id: p for p in self._snapshot.predictions}
        for p in changeset.predictions:
            predMap[p.id] = p

        # 3. Recommendations (upsert by id)
        recMap = {r.id: r for r in self._snapshot.recommendations}
        for r in changeset.recommendations:
            recMap[r.id] = r

        # 4. ActivityOps (create, update, delete)
        actMap = {a.id: a for a in self._snapshot.activities}
        for op in changeset.activityOps:
            if op.op == "create" and op.activity:
                actMap[op.activity.id] = op.activity
            elif op.op == "update" and op.activity:
                actMap[op.activity.id] = op.activity
            elif op.op == "delete":
                targetId = op.activityId or (op.activity.id if op.activity else None)
                if targetId in actMap:
                    del actMap[targetId]

        # 5. Notifications
        for n in changeset.notifications:
            if n not in self.notifications:
                self.notifications.append(n)

        self._snapshot = replace(
            self._snapshot,
            diagnostics=tuple(diagMap.values()),
            predictions=tuple(predMap.values()),
            recommendations=tuple(recMap.values()),
            activities=tuple(actMap.values()),
        )


# Backward compatibility alias
StoreSimulator = StoreSim
