"""Prediction-only test builders (Phase 4)."""
from datetime import datetime, timedelta

from identity.analysis.models import (
    ApplyMode,
    DiagStatus,
    DiagnosticReport,
    PondInfo,
    Prediction,
    PredStatus,
    Recommendation,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


def makePrediction(
    predId: str = "pred:pond_1:PRED_DO_NIGHT:2026-10-25T16:30:00",
    pondId: str = "pond_1",
    ruleId: str = "PRED_DO_NIGHT",
    scope: str | None = "2026-10-25",
    parameter: PondParameters = PondParameters.DO,
    expectedZone: ThresholdLevelType = ThresholdLevelType.HighRisk,
    riskStart: datetime = datetime(2026, 10, 25, 13, 0),
    riskEnd: datetime = datetime(2026, 10, 26, 6, 0),
    met: tuple[str, ...] = ("C1", "C3"),
    status: PredStatus = PredStatus.active,
    endReason: str | None = None,
    evidence: dict | None = None,
    pond: PondInfo | None = None,
    createdAt: datetime = datetime(2026, 10, 25, 9, 30),
    revisedAt: datetime | None = None,
) -> Prediction:
    return Prediction(
        id=predId,
        pondId=pondId,
        ruleId=ruleId,
        scope=scope,
        parameter=parameter,
        expectedZone=expectedZone,
        riskStart=riskStart,
        riskEnd=riskEnd,
        met=met,
        status=status,
        endReason=endReason,
        evidence=evidence or {},
        pondSnapshot=pond or PondInfo(pondId=pondId),
        createdAt=createdAt,
        revisedAt=revisedAt,
    )
