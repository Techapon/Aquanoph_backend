"""PH_SWING detector over recent complete local days."""
from datetime import datetime, timedelta
from typing import Iterable

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.helpers import isStale, localDate, localDayBounds
from identity.analysis.models import PondInfo, Signal, SignalSource
from identity.analysis.severity_view import SeverityReportView
from identity.parameters.pond_parameter_enum import PondParameters


def detectPhSwing(
    views: Iterable[SeverityReportView],
    pond: PondInfo,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> Signal | None:
    """Return PH_SWING Signal when sufficient complete days exceed swing and coverage thresholds."""
    phViews = tuple(sorted(
        (v for v in views if v.parameter == PondParameters.pH),
        key=lambda v: v.time,
    ))
    if not phViews or isStale(phViews[-1].time, now, cfg):
        return None

    today = localDate(now, pond.timezone)
    days: list[dict[str, object]] = []
    hitDays = 0

    for offset in range(cfg.phSwingWindowDays, 0, -1):
        day = today - timedelta(days=offset)
        start, end = localDayBounds(day, pond.timezone)
        dayValues = [v.value for v in phViews if start <= v.time < end]
        readingCount = len(dayValues)
        swing = max(dayValues) - min(dayValues) if readingCount >= 2 else 0.0
        expectedReadings = (end - start).total_seconds() / 60 / cfg.expectedIntervalMinutes
        coverage = readingCount / expectedReadings if expectedReadings else 0.0
        roundedSwing = round(swing, 6)
        roundedCoverage = round(coverage, 6)
        hit = (
            roundedSwing >= cfg.phSwingMin
            and roundedCoverage >= cfg.phSwingCoverage
        )
        if hit:
            hitDays += 1
        days.append({
            "date": day,
            "swing": roundedSwing,
            "coverage": roundedCoverage,
            "readingCount": readingCount,
            "hit": hit,
        })

    if hitDays < cfg.phSwingHitDays:
        return None

    return Signal(
        sourceType=SignalSource.detector,
        sourceId=f"PH_SWING:{pond.pondId}",
        code="PH_SWING",
        parameter=PondParameters.pH,
        active=True,
        riskStart=None,
        riskEnd=None,
        peakSeverity=None,
        lastSeverity=None,
        scope=None,
        facts={
            "hitDays": hitDays,
            "windowDays": cfg.phSwingWindowDays,
            "days": tuple(days),
        },
    )
