"""SeverityView — unified read-only querying over sensor and severity history.

Adapts AnalysisReportModel entries produced by the severity engine for Diagnostic and Prediction.
Follows PHASE_0_prep.md §0.4:
SeverityReportView carries (parameter, time, value, zone, direction, severity).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Sequence

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


@dataclass(frozen=True)
class SeverityReportView:
    parameter: PondParameters
    time: datetime                       # naive UTC
    value: float
    zone: ThresholdLevelType
    direction: ThresholdDirection | None # None for Level thresholds
    severity: SeverityLevelType


def toView(report: AnalysisReportModel) -> SeverityReportView:
    """Convert an AnalysisReportModel into an immutable SeverityReportView.

    Raises ValueError if report.value is None or any required field is missing.
    """
    if report.value is None:
        raise ValueError(
            f"Report for {report.parameter.label} at {report.dateTime} has no measured value. "
            f"Every stored report must carry value."
        )
    return SeverityReportView(
        parameter=report.parameter,
        time=report.dateTime,
        value=report.value,
        zone=report.thresholdStatus,
        direction=report.thresholdDirection,
        severity=report.severityStatus,
    )


def toViews(history: Iterable[Any]) -> tuple[SeverityReportView, ...]:
    """Convert an iterable of AnalysisReportModel or SeverityReportView into a tuple of SeverityReportView sorted by time ascending (stable)."""
    views: list[SeverityReportView] = []
    for item in history:
        if isinstance(item, SeverityReportView):
            views.append(item)
        elif isinstance(item, AnalysisReportModel):
            views.append(toView(item))
        else:
            raise TypeError(f"Expected AnalysisReportModel or SeverityReportView, got {type(item)}")
    views.sort(key=lambda v: v.time)
    return tuple(views)


def zoneRank(val: Any) -> int:
    """Return numeric rank of zone: Optimal 0, Stress 1, HighRisk 2, Critical 3."""
    zone = getattr(val, "zone", val)
    return ZONE_ORDER.get(zone, -1)


def severityRank(val: Any) -> int:
    """Return numeric rank of severity: Optimal 0, Stress 1, ElevatedRisk 2, Critical 3."""
    sev = getattr(val, "severity", val)
    return SEVERITY_ORDER.get(sev, -1)


def isOptimalZone(v: SeverityReportView) -> bool:
    """Check if report view has zone == Optimal."""
    return v.zone == ThresholdLevelType.Optimal


def viewsFor(
    views: Sequence[SeverityReportView],
    parameter: PondParameters,
) -> tuple[SeverityReportView, ...]:
    """Filter a sequence of SeverityReportView for a specific parameter, preserving chronological order."""
    return tuple(v for v in views if v.parameter == parameter)

