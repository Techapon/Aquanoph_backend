"""Weighted kNN aggregation: past days' same time-of-day → forecast points."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from config.constants import AnalysisConfig
from identity.forecast.series import DaySeries, slotIndex
from identity.forecast.similarity import Neighbor


@dataclass(frozen=True)
class ForecastPoint:
    time: datetime  # naive UTC
    value: float | None
    low: float | None
    high: float | None
    count: int


def _weightedQuantile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= q * total:
            return v
    return pairs[-1][0]


def buildForecast(
    now: datetime,
    tz: str,
    neighborSeries: Sequence[tuple[Neighbor, DaySeries]],
    cfg: AnalysisConfig,
) -> tuple[ForecastPoint, ...]:
    """จุดอนาคตทุก step จนครบ horizon — ค่ามัธยฐานถ่วงน้ำหนัก 1/distance + P25/P75.

    slot ที่เพื่อนบ้านมีข้อมูลน้อยกว่า forecastMinNeighbors → จุดนั้น value = None
    (แอปวาดขาดช่วง แต่ไม่ทำให้ทั้งเส้นหาย).
    """
    points: list[ForecastPoint] = []
    steps = (cfg.forecastHorizonHours * 60) // cfg.forecastStepMinutes

    for i in range(1, steps + 1):
        t = now + timedelta(minutes=cfg.forecastStepMinutes * i)
        slot = slotIndex(t, tz, cfg)

        values: list[float] = []
        weights: list[float] = []
        for nb, series in neighborSeries:
            v = series.values[slot] if slot < len(series.values) else None
            if v is None:
                continue
            values.append(v)
            weights.append(1.0 / (nb.distance + 1e-6))

        n = len(values)
        if n < cfg.forecastMinNeighbors:
            points.append(ForecastPoint(time=t, value=None, low=None, high=None, count=n))
            continue

        points.append(
            ForecastPoint(
                time=t,
                value=_weightedQuantile(values, weights, 0.5),
                low=_weightedQuantile(values, weights, 0.25),
                high=_weightedQuantile(values, weights, 0.75),
                count=n,
            )
        )

    return tuple(points)
