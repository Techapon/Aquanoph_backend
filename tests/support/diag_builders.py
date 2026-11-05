"""Diagnostic-only test builders for Phase 2."""
from datetime import datetime

from identity.analysis.models import (
    Cause,
    DiagStatus,
    DiagnosticReport,
    PondInfo,
)
from identity.diagnostic.episode import Episode
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


def makeEpisode(
    parameter: PondParameters = PondParameters.DO,
    direction: ThresholdDirection | None = None,
    onsetAt: datetime = datetime(2026, 10, 25, 13, 0),
    endAt: datetime | None = None,
    status: DiagStatus = DiagStatus.open,
    peakSeverity: SeverityLevelType = SeverityLevelType.Stress,
    lastSeverity: SeverityLevelType = SeverityLevelType.Stress,
    peakZone: ThresholdLevelType = ThresholdLevelType.Stress,
    readingCount: int = 2,
    lastReadingAt: datetime | None = None,
) -> Episode:
    return Episode(
        parameter=parameter,
        direction=direction,
        onsetAt=onsetAt,
        endAt=endAt,
        status=status,
        peakSeverity=peakSeverity,
        lastSeverity=lastSeverity,
        peakZone=peakZone,
        readingCount=readingCount,
        lastReadingAt=lastReadingAt or onsetAt,
    )


def makeDiagnosticReport(
    reportId: str = "diag:pond_1:DO:-:2026-10-25T13:00:00",
    pondId: str = "pond_1",
    parameter: PondParameters = PondParameters.DO,
    direction: ThresholdDirection | None = None,
    onsetAt: datetime = datetime(2026, 10, 25, 13, 0),
    endAt: datetime | None = None,
    status: DiagStatus = DiagStatus.open,
    peakSeverity: SeverityLevelType = SeverityLevelType.Stress,
    lastSeverity: SeverityLevelType = SeverityLevelType.Stress,
    causes: tuple[Cause, ...] = (),
    noClearCause: bool = True,
    pond: PondInfo | None = None,
    revisedAt: datetime | None = None,
) -> DiagnosticReport:
    return DiagnosticReport(
        id=reportId,
        pondId=pondId,
        parameter=parameter,
        direction=direction,
        onsetAt=onsetAt,
        endAt=endAt,
        status=status,
        peakSeverity=peakSeverity,
        lastSeverity=lastSeverity,
        causes=causes,
        noClearCause=noClearCause,
        pondSnapshot=pond or PondInfo(pondId=pondId),
        revisedAt=revisedAt,
    )
