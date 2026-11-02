"""ChangeSet model representing the pure output of an analysis run.

The analysis engine produces only a ChangeSet. It never mutates inputs or writes to DB (Contract §3).
A ChangeSet is empty when no state change is needed (idempotency §7.7).
"""
from dataclasses import dataclass, field
from typing import Any

from identity.analysis.models import Notification, Recommendation


@dataclass(frozen=True)
class ChangeSet:
    upsertEpisodes: tuple[Any, ...] = ()
    upsertDetectors: tuple[Any, ...] = ()
    upsertPredictions: tuple[Any, ...] = ()
    upsertRecommendations: tuple[Recommendation, ...] = ()
    notifications: tuple[Notification, ...] = ()

    @property
    def isEmpty(self) -> bool:
        return (
            len(self.upsertEpisodes) == 0
            and len(self.upsertDetectors) == 0
            and len(self.upsertPredictions) == 0
            and len(self.upsertRecommendations) == 0
            and len(self.notifications) == 0
        )

    def diffOnly(self, existingSnapshot: Any) -> "ChangeSet":
        """Filter out records that already exist identically in snapshot (idempotency Rule 7)."""
        # Compares objects by id + equality to ensure only changed objects are in ChangeSet.
        existingRecMap = {r.id: r for r in getattr(existingSnapshot, "recommendations", ())}
        filteredRecs = tuple(
            r for r in self.upsertRecommendations
            if r.id not in existingRecMap or existingRecMap[r.id] != r
        )

        existingEpMap = {e.id: e for e in getattr(existingSnapshot, "activeEpisodes", ()) + getattr(existingSnapshot, "closedEpisodes", ())}
        filteredEps = tuple(
            e for e in self.upsertEpisodes
            if getattr(e, "id", None) not in existingEpMap or existingEpMap[e.id] != e
        )

        existingDetMap = {d.id: d for d in getattr(existingSnapshot, "activeDetectors", ())}
        filteredDets = tuple(
            d for d in self.upsertDetectors
            if getattr(d, "id", None) not in existingDetMap or existingDetMap[d.id] != d
        )

        existingPredMap = {p.id: p for p in getattr(existingSnapshot, "activePredictions", ())}
        filteredPreds = tuple(
            p for p in self.upsertPredictions
            if getattr(p, "id", None) not in existingPredMap or existingPredMap[p.id] != p
        )

        return ChangeSet(
            upsertEpisodes=filteredEps,
            upsertDetectors=filteredDets,
            upsertPredictions=filteredPreds,
            upsertRecommendations=filteredRecs,
            notifications=self.notifications,
        )
