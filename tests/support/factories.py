"""Test factories for generating analysis domain models."""
from datetime import datetime, timedelta
from typing import Any

from identity.analysis.models import (
    Activity,
    ActivitySource,
    ActivityStatus,
    ActivityType,
    PondProfile,
    PondSnapshot,
    Recommendation,
    RecommendationStatus,
    RecommendationUrgency,
    SourceRef,
)
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


def makePondProfile(
    pondId: str = "pond_1",
    name: str = "Test Pond",
    species: str = "nile_tilapia",
    areaM2: float = 1600.0,
    depthM: float = 1.5,
    targetDensityKgM3: float = 2.0,
    fishCount: int = 5000,
    avgWeightG: float = 400.0,
    timezone: str = "Asia/Bangkok",
) -> PondProfile:
    return PondProfile(
        id=pondId,
        name=name,
        species=species,
        areaM2=areaM2,
        depthM=depthM,
        targetDensityKgM3=targetDensityKgM3,
        fishCount=fishCount,
        avgWeightG=avgWeightG,
        timezone=timezone,
    )


def makeReport(
    parameter: PondParameters,
    dateTime: datetime,
    thresholdStatus: ThresholdLevelType = ThresholdLevelType.Optimal,
    thresholdDirection: ThresholdDirection | None = None,
    severityLevel: SeverityLevelType = SeverityLevelType.Optimal,
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
    )


def makeActivity(
    activityId: str,
    pondId: str = "pond_1",
    activityType: ActivityType = ActivityType.feeding,
    status: ActivityStatus = ActivityStatus.done,
    source: ActivitySource = ActivitySource.user,
    scheduledAt: datetime | None = None,
    amount: float | None = 20.0,
    recommendationId: str | None = None,
) -> Activity:
    now = scheduledAt or datetime(2026, 10, 25, 12, 0)
    return Activity(
        id=activityId,
        pondId=pondId,
        activityType=activityType,
        status=status,
        source=source,
        scheduledAt=now,
        startedAt=now if status == ActivityStatus.done else None,
        completedAt=now if status == ActivityStatus.done else None,
        amount=amount,
        recommendationId=recommendationId,
    )


def makeSnapshot(
    pond: PondProfile | None = None,
    reports: list[AnalysisReportModel] | None = None,
    activities: list[Activity] | None = None,
    recommendations: list[Recommendation] | None = None,
) -> PondSnapshot:
    p = pond or makePondProfile()
    reps = tuple(reports or [])
    acts = tuple(activities or [])
    recs = tuple(recommendations or [])

    latest: dict[PondParameters, Any] = {}
    for r in reps:
        if r.parameter not in latest or r.dateTime > latest[r.parameter].dateTime:
            latest[r.parameter] = r

    return PondSnapshot(
        pond=p,
        latestReadings=latest,
        readingHistory=reps,
        activities=acts,
        recommendations=recs,
    )
