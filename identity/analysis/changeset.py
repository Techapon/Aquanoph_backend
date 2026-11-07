"""ChangeSet model representing the pure output of an analysis run.

The analysis engine produces only a ChangeSet. It never mutates inputs or writes to DB (Contract §3).
Strictly follows PHASE_1_foundation.md §4:
  ActivityOp(op: "create"|"update"|"delete", activity: Activity|None, activityId: str|None, reason: str|None)
  Notification(kind: str, targetType: str, targetId: str, reasonKey: str, facts: Mapping)
  ChangeSet(diagnostics: tuple, predictions: tuple, recommendations: tuple, activityOps: tuple, notifications: tuple)
     .isEmpty()  .merge(other) -> ChangeSet   (later object with same id wins)
  def changedOnly(newObjs, existingById) -> tuple
"""
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from identity.analysis.models import (
    Activity,
    DiagnosticReport,
    Notification,
    Prediction,
    Recommendation,
)


@dataclass(frozen=True)
class ActivityOp:
    op: Literal["create", "update", "delete"]
    activity: Activity | None = None
    activityId: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.op in ("create", "update") and self.activity is None:
            raise ValueError(f"activity is required for op '{self.op}'")
        if self.op == "delete" and self.activityId is None and self.activity is None:
            raise ValueError("activityId or activity is required for op 'delete'")


def changedOnly(newObjs: tuple[Any, ...], existingById: Mapping[str, Any]) -> tuple[Any, ...]:
    """Keep only objects that do not exist or are not equal to the existing version."""
    result: list[Any] = []
    for obj in newObjs:
        objId = getattr(obj, "id", None)
        if objId is None:
            result.append(obj)
            continue
        if objId not in existingById or existingById[objId] != obj:  # type: ignore[index]
            result.append(obj)
    return tuple(result)


@dataclass(frozen=True)
class ChangeSet:
    diagnostics: tuple[DiagnosticReport, ...] = ()
    predictions: tuple[Prediction, ...] = ()
    recommendations: tuple[Recommendation, ...] = ()
    activityOps: tuple[ActivityOp, ...] = ()
    notifications: tuple[Notification, ...] = ()

    # Backward compatibility properties
    @property
    def upsertEpisodes(self) -> tuple[DiagnosticReport, ...]:
        return self.diagnostics

    @property
    def upsertDetectors(self) -> tuple:
        return ()

    @property
    def upsertPredictions(self) -> tuple[Prediction, ...]:
        return self.predictions

    @property
    def upsertRecommendations(self) -> tuple[Recommendation, ...]:
        return self.recommendations

    def isEmpty(self) -> bool:
        return (
            len(self.diagnostics) == 0
            and len(self.predictions) == 0
            and len(self.recommendations) == 0
            and len(self.activityOps) == 0
            and len(self.notifications) == 0
        )

    def merge(self, other: "ChangeSet") -> "ChangeSet":
        """Merge two ChangeSets; later (other) wins on id collision."""
        def _mergeById(a: tuple, b: tuple) -> tuple:
            combined: dict[Any, Any] = {}
            for obj in (*a, *b):
                objId = getattr(obj, "id", None)
                key: Any = objId if objId is not None else id(obj)
                combined[key] = obj
            return tuple(combined.values())

        return ChangeSet(
            diagnostics=_mergeById(self.diagnostics, other.diagnostics),
            predictions=_mergeById(self.predictions, other.predictions),
            recommendations=_mergeById(self.recommendations, other.recommendations),
            activityOps=self.activityOps + other.activityOps,
            notifications=self.notifications + other.notifications,
        )
