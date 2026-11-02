"""SeverityView — unified read-only querying over sensor and severity history.

Adapts AnalysisReportModel entries produced by the severity engine for Diagnostic and Prediction.
"""
from datetime import datetime, timedelta
from typing import Sequence

from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


ZONE_ORDER: dict[ThresholdLevelType, int] = {
    ThresholdLevelType.Optimal: 0,
    ThresholdLevelType.Stress: 1,
    ThresholdLevelType.HighRisk: 2,
    ThresholdLevelType.Critical: 3,
}

SEVERITY_ORDER: dict[SeverityLevelType, int] = {
    SeverityLevelType.Optimal: 0,
    SeverityLevelType.Stress: 1,
    SeverityLevelType.ElevatedRisk: 2,
    SeverityLevelType.Critical: 3,
}


def zoneOrder(zone: ThresholdLevelType) -> int:
    """Return numeric order for threshold zone: Optimal < Stress < HighRisk < Critical."""
    return ZONE_ORDER.get(zone, -1)


def severityOrder(severity: SeverityLevelType) -> int:
    """Return numeric order for severity: Optimal < Stress < ElevatedRisk < Critical."""
    return SEVERITY_ORDER.get(severity, -1)


def isNonOptimal(report: AnalysisReportModel) -> bool:
    """Check if report threshold zone is non-optimal (trigger for an episode)."""
    return report.thresholdStatus != ThresholdLevelType.Optimal


def isRecoveryHold(report: AnalysisReportModel) -> bool:
    """Check if report is in Recovery Hold (zone is Optimal, but severity is still Stress)."""
    return (
        report.thresholdStatus == ThresholdLevelType.Optimal
        and report.severityStatus == SeverityLevelType.Stress
    )


class ParameterTimelineView:
    """Read-only view over a single parameter's history, sorted chronologically."""

    def __init__(self, parameter: PondParameters, history: Sequence[AnalysisReportModel]):
        self.parameter = parameter
        # Sort chronologically, strictly filtering for this parameter
        self.reports: tuple[AnalysisReportModel, ...] = tuple(
            sorted(
                (r for r in history if r.parameter == parameter),
                key=lambda r: r.dateTime,
            )
        )

    @property
    def latest(self) -> AnalysisReportModel | None:
        return self.reports[-1] if self.reports else None

    def window(self, fromTime: datetime, toTime: datetime) -> tuple[AnalysisReportModel, ...]:
        """Return readings in [fromTime, toTime]."""
        return tuple(r for r in self.reports if fromTime <= r.dateTime <= toTime)

    def pastMinutes(self, now: datetime, minutes: int) -> tuple[AnalysisReportModel, ...]:
        """Return readings in [now - minutes, now]."""
        start = now - timedelta(minutes=minutes)
        return self.window(start, now)
