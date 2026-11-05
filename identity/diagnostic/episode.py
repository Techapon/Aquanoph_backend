"""Episode construction from severity report views (Phase 2 contract §3.1)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from config.constants import AnalysisConfig
from identity.analysis.models import DiagStatus
from identity.analysis.severity_view import SeverityReportView, severityRank, zoneRank
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


@dataclass(frozen=True)
class Episode:
    parameter: PondParameters
    direction: ThresholdDirection | None
    onsetAt: datetime
    endAt: datetime | None
    status: DiagStatus
    peakSeverity: SeverityLevelType
    lastSeverity: SeverityLevelType
    peakZone: ThresholdLevelType
    readingCount: int
    lastReadingAt: datetime


def _episodeFrom(
    views: list[SeverityReportView],
    endAt: datetime | None = None,
) -> Episode:
    """Build an Episode from at least one non-Optimal view."""
    first = views[0]
    last = views[-1]
    peakSev = max(views, key=severityRank).severity
    peakZone = max(views, key=zoneRank).zone
    return Episode(
        parameter=first.parameter,
        direction=first.direction,
        onsetAt=first.time,
        endAt=endAt,
        status=DiagStatus.closed if endAt is not None else DiagStatus.open,
        peakSeverity=peakSev,
        lastSeverity=last.severity,
        peakZone=peakZone,
        readingCount=len(views),
        lastReadingAt=last.time,
    )


def buildEpisodes(
    views: Iterable[SeverityReportView],
    parameter: PondParameters,
) -> tuple[Episode, ...]:
    """Build parameter-specific episodes, ordered by onsetAt (Phase 2 §1)."""
    targetViews = sorted((v for v in views if v.parameter == parameter), key=lambda v: v.time)
    episodes: list[Episode] = []
    current: list[SeverityReportView] = []

    for view in targetViews:
        if view.zone == ThresholdLevelType.Optimal:
            if current:
                episodes.append(_episodeFrom(current, endAt=view.time))
                current = []
            continue

        if current and current[-1].direction != view.direction:
            # A range-side flip closes previous episode and starts next at this view time.
            episodes.append(_episodeFrom(current, endAt=view.time))
            current = [view]
            continue

        current.append(view)

    if current:
        episodes.append(_episodeFrom(current))

    return tuple(episodes)


def qualifies(ep: Episode, cfg: AnalysisConfig) -> bool:
    """Return whether an episode qualifies for a diagnostic report (Phase 2 §1.7)."""
    return (
        ep.readingCount >= cfg.minEpisodeReadings
        or zoneRank(ep.peakZone) >= zoneRank(ThresholdLevelType.HighRisk)
    )
