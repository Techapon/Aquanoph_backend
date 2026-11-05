"""Test factories for generating analysis domain models.

Strictly follows PHASE_1_foundation.md §6:
  makePond(...) (default tz "Asia/Bangkok", biomass 400 kg)
  makeActivity(...)
  makeView(...)
  makeSnapshot(...)
  t(local="2025-06-01 19:00", tz="Asia/Bangkok") -> naive UTC
"""
from datetime import datetime, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from identity.analysis.models import (
    Activity,
    ActivitySource,
    ActivityStatus,
    ActivityType,
    DiagnosticReport,
    PondInfo,
    PondSnapshot,
    Prediction,
    Recommendation,
)
from identity.analysis.severity_view import SeverityReportView
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


def t(local: str | datetime = "2025-06-01 19:00", tz: str = "Asia/Bangkok") -> datetime:
    """Convert a local time (str or datetime) to naive UTC datetime."""
    if isinstance(local, str):
        localDt = datetime.fromisoformat(local)
    else:
        localDt = local
    awareLocal = localDt.replace(tzinfo=ZoneInfo(tz))
    utcDt = awareLocal.astimezone(timezone.utc)
    return utcDt.replace(tzinfo=None)


def makePond(
    pondId: str = "pond_1",
    timezone: str = "Asia/Bangkok",
    biomassKg: float = 400.0,
    avgWeightG: float = 400.0,
    fishCount: int = 1000,
) -> PondInfo:
    return PondInfo(
        pondId=pondId,
        timezone=timezone,
        biomassKg=biomassKg,
        avgWeightG=avgWeightG,
        fishCount=fishCount,
    )


# Alias
makePondProfile = makePond


def makeView(
    parameter: PondParameters = PondParameters.DO,
    time: datetime | None = None,
    value: float = 5.5,
    zone: ThresholdLevelType = ThresholdLevelType.Optimal,
    direction: ThresholdDirection | None = None,
    severity: SeverityLevelType = SeverityLevelType.Optimal,
) -> SeverityReportView:
    return SeverityReportView(
        parameter=parameter,
        time=time or datetime(2026, 10, 25, 12, 0),
        value=value,
        zone=zone,
        direction=direction,
        severity=severity,
    )


def makeReport(
    parameter: PondParameters,
    dateTime: datetime,
    thresholdStatus: ThresholdLevelType = ThresholdLevelType.Optimal,
    thresholdDirection: ThresholdDirection | None = None,
    severityLevel: SeverityLevelType = SeverityLevelType.Optimal,
    value: float = 5.5,
    description: str = "Normal",
    guidance: str = "Keep monitoring",
) -> AnalysisReportModel:
    sevDes = SeverityDescriptionModel(des=description, detail="-", guid=guidance)
    sev = SeverityModel(severityLevel=severityLevel, severityDes=sevDes)
    return AnalysisReportModel(
        dateTime=dateTime,
        parameter=parameter,
        thresholdStatus=thresholdStatus,
        thresholdDirection=thresholdDirection,
        severity=sev,
        value=value,
    )


def makeActivity(
    activityId: str = "act_1",
    pondId: str = "pond_1",
    activityType: ActivityType = ActivityType.feeding,
    status: ActivityStatus = ActivityStatus.done,
    startTime: datetime | None = None,
    endTime: datetime | None = None,
    quantityKg: float | None = 6.0,
    fraction: float | None = None,
    source: ActivitySource = ActivitySource.user,
    sourceRecId: str | None = None,
    createdAt: datetime | None = None,
    updatedAt: datetime | None = None,
) -> Activity:
    st = startTime or datetime(2026, 10, 25, 12, 0)
    if activityType == ActivityType.waterChange:
        quantityKg = None
        endTime = None
        fraction = fraction if fraction is not None else 0.25
    elif activityType == ActivityType.aeration:
        fraction = None
        quantityKg = None
        endTime = endTime or (st + (datetime(2026, 1, 1, 2) - datetime(2026, 1, 1)))  # default 2 hours
    else:
        fraction = None
        endTime = None

    return Activity(
        id=activityId,
        pondId=pondId,
        type=activityType,
        status=status,
        startTime=st,
        endTime=endTime,
        quantityKg=quantityKg,
        fraction=fraction,
        source=source,
        sourceRecId=sourceRecId,
        createdAt=createdAt or st,
        updatedAt=updatedAt or st,
    )


def makeSnapshot(
    pond: PondInfo | None = None,
    severityReports: Sequence[SeverityReportView] | None = None,
    activities: Sequence[Activity] | None = None,
    diagnostics: Sequence[DiagnosticReport] | None = None,
    predictions: Sequence[Prediction] | None = None,
    recommendations: Sequence[Recommendation] | None = None,
) -> PondSnapshot:
    return PondSnapshot(
        pond=pond or makePond(),
        severityReports=tuple(severityReports or ()),
        activities=tuple(activities or ()),
        diagnostics=tuple(diagnostics or ()),
        predictions=tuple(predictions or ()),
        recommendations=tuple(recommendations or ()),
    )
