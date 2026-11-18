"""kNN forecast runner (pure): 6 parameters × forecastHorizonHours from similar past days."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Sequence

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.helpers import localDate, localTime
from identity.analysis.models import Activity, PondInfo
from identity.forecast.knn import ForecastPoint, buildForecast
from identity.forecast.series import (
    DaySeries,
    Reading,
    buildDaySeries,
    parameterSamples,
)
from identity.forecast.similarity import (
    featuresForDay,
    rankDays,
)
from identity.parameters.pond_parameter_enum import PondParameters

MODEL = "knn_v1"

FORECAST_PARAMETERS: tuple[PondParameters, ...] = (
    PondParameters.DO,
    PondParameters.pH,
    PondParameters.tem,
    PondParameters.NH3,
    PondParameters.NO2_N,
    PondParameters.salinity,
)


@dataclass(frozen=True)
class ForecastResult:
    parameter: PondParameters
    generatedAt: datetime
    horizonHours: int
    points: tuple[ForecastPoint, ...]
    neighbors: tuple[tuple[date, float], ...]
    model: str = MODEL


def forecastParameter(
    parameter: PondParameters,
    readings: Sequence[Reading],
    activities: Sequence[Activity],
    pond: PondInfo,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> ForecastResult | None:
    """None = ข้อมูลอดีตไม่ถึงเกณฑ์ (แอปแสดง 'Not enough data')."""
    tz = pond.timezone
    today = localDate(now, tz)
    nowLocal = localTime(now, tz)

    byDay: dict[date, list[tuple[datetime, float]]] = {}
    for t, v in parameterSamples(readings, parameter):
        byDay.setdefault(localDate(t, tz), []).append((t, v))

    todaySeries = buildDaySeries(byDay.get(today, ()), today, tz, cfg)
    candidates: list[DaySeries] = []
    for offset in range(1, cfg.forecastWindowDays + 1):
        day = today - timedelta(days=offset)
        series = buildDaySeries(byDay.get(day, ()), day, tz, cfg)
        if series.coverage >= cfg.forecastCoverage:
            candidates.append(series)

    if len(candidates) < cfg.forecastMinDays:
        return None

    todayFeatures = featuresForDay(today, todaySeries, activities, pond, nowLocal, cfg, nowUtc=now)
    candidateFeatures = [
        featuresForDay(s.day, s, activities, pond, nowLocal, cfg) for s in candidates
    ]
    ranked = rankDays(todayFeatures, candidateFeatures, today, cfg)[: cfg.forecastK]

    seriesByDay = {s.day: s for s in candidates}
    points = buildForecast(
        now, tz, [(nb, seriesByDay[nb.day]) for nb in ranked], cfg
    )

    return ForecastResult(
        parameter=parameter,
        generatedAt=now,
        horizonHours=cfg.forecastHorizonHours,
        points=points,
        neighbors=tuple((nb.day, nb.distance) for nb in ranked),
    )


def forecastAll(
    pond: PondInfo,
    readings: Sequence[Reading],
    activities: Sequence[Activity],
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> tuple[ForecastResult, ...]:
    """พยากรณ์ทุก parameter — ข้ามตัวที่ข้อมูลไม่พอ."""
    out: list[ForecastResult] = []
    for parameter in FORECAST_PARAMETERS:
        result = forecastParameter(parameter, readings, activities, pond, now, cfg)
        if result is not None:
            out.append(result)
    return tuple(out)
