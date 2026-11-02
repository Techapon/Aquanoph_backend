"""StoreSimulator — simulates the database applying a ChangeSet to a PondSnapshot.

Used in integration and scenario tests (Contract §3).
"""
from dataclasses import replace
from typing import Any

from identity.analysis.changeset import ChangeSet
from identity.analysis.models import Notification, PondSnapshot, Recommendation


class StoreSimulator:
    def __init__(self, initialSnapshot: PondSnapshot):
        self.snapshot = initialSnapshot
        self.notificationLog: list[Notification] = []

    def apply(self, changeset: ChangeSet) -> PondSnapshot:
        """Apply a ChangeSet to produce a new immutable PondSnapshot."""
        # 1. Recommendations: update or append by id
        recMap = {r.id: r for r in self.snapshot.recommendations}
        for r in changeset.upsertRecommendations:
            recMap[r.id] = r

        # 2. Episodes: update or append
        epMap = {getattr(e, "id", str(i)): e for i, e in enumerate(self.snapshot.activeEpisodes)}
        for e in changeset.upsertEpisodes:
            epId = getattr(e, "id", None)
            if epId:
                epMap[epId] = e

        # 3. Detectors: update or append
        detMap = {getattr(d, "id", str(i)): d for i, d in enumerate(self.snapshot.activeDetectors)}
        for d in changeset.upsertDetectors:
            detId = getattr(d, "id", None)
            if detId:
                detMap[detId] = d

        # 4. Predictions: update or append
        predMap = {getattr(p, "id", str(i)): p for i, p in enumerate(self.snapshot.activePredictions)}
        for p in changeset.upsertPredictions:
            predId = getattr(p, "id", None)
            if predId:
                predMap[predId] = p

        # 5. Notifications
        self.notificationLog.extend(changeset.notifications)

        self.snapshot = replace(
            self.snapshot,
            recommendations=tuple(recMap.values()),
            activeEpisodes=tuple(epMap.values()),
            activeDetectors=tuple(detMap.values()),
            activePredictions=tuple(predMap.values()),
        )
        return self.snapshot
