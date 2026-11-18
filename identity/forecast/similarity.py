"""Similarity between today's known window and past local days (activity + water state)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from config.constants import AnalysisConfig
from identity.analysis.helpers import aerationHours, localDayBounds, mealPct, toUtc
from identity.analysis.models import Activity, ActivityStatus, ActivityType, PondInfo
from identity.forecast.series import DaySeries

# feature weights ภายในกลุ่ม
_WATER_FEATURES = 3
_ACTIVITY_FEATURES = 7


@dataclass(frozen=True)
class DayFeatures:
    """feature ของ 1 วัน เฉพาะช่วง [local 00:00, now's local clock]."""
    day: date
    water: tuple[float, float, float] | None     # mean, min, max ของ parameter
    activities: tuple[float, ...]                # mealPct, feedCount, aerationHours, wc, alk, lime, probiotic


@dataclass(frozen=True)
class Neighbor:
    day: date
    distance: float


def windowForDay(
    day: date,
    tz: str,
    nowLocal: datetime,
    nowUtc: datetime | None = None,
) -> tuple[datetime, datetime]:
    """[local midnight ของ day, เวลาท้องถิ่นเดิมของ now] เป็น naive UTC."""
    start, _ = localDayBounds(day, tz)
    end = nowUtc if nowUtc is not None else toUtc(datetime.combine(day, nowLocal.time()), tz)
    return start, end


def _waterFeatures(series: DaySeries, nowLocal: datetime, cfg: AnalysisConfig) -> tuple[float, float, float] | None:
    limit = (nowLocal.hour * 60 + nowLocal.minute) // cfg.forecastStepMinutes
    values = [v for v in series.values[:limit] if v is not None]
    if len(values) < 2:
        return None
    return (sum(values) / len(values), min(values), max(values))


def _activityFeatures(acts: Sequence[Activity], pond: PondInfo) -> tuple[float, ...]:
    meals = [a for a in acts if a.type == ActivityType.feeding]
    mealPctSum = sum(mealPct(a, pond) for a in meals if a.quantityKg is not None)
    aeration = aerationHours(acts)

    def count(kind: ActivityType) -> float:
        return float(sum(1 for a in acts if a.type == kind))

    return (
        mealPctSum,
        float(len(meals)),
        aeration,
        count(ActivityType.waterChange),
        count(ActivityType.alkalinity),
        count(ActivityType.lime),
        count(ActivityType.probiotic),
    )


def featuresForDay(
    day: date,
    series: DaySeries,
    activities: Sequence[Activity],
    pond: PondInfo,
    nowLocal: datetime,
    cfg: AnalysisConfig,
    nowUtc: datetime | None = None,
) -> DayFeatures:
    start, end = windowForDay(day, pond.timezone, nowLocal, nowUtc)
    acts = tuple(
        a for a in activities
        if a.status == ActivityStatus.done and start <= a.startTime < end
    )
    return DayFeatures(
        day=day,
        water=_waterFeatures(series, nowLocal, cfg),
        activities=_activityFeatures(acts, pond),
    )


def _stats(vectors: Sequence[Sequence[float] | None], size: int) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for i in range(size):
        vals = [v[i] for v in vectors if v is not None]
        if not vals:
            out.append((0.0, 0.0))
            continue
        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((x - mean) ** 2 for x in vals) / len(vals))
        out.append((mean, std))
    return out


def _distance(
    a: DayFeatures,
    b: DayFeatures,
    waterStats: list[tuple[float, float]],
    activityStats: list[tuple[float, float]],
    cfg: AnalysisConfig,
) -> float:
    """weighted normalized Euclidean; feature ที่ไม่มีข้อมูลถูกข้าม (หารด้วยน้ำหนักที่ใช้จริง)."""
    sumSq = 0.0
    weightSum = 0.0

    if a.water is not None and b.water is not None:
        w = (1.0 - cfg.forecastWeightActivity) / _WATER_FEATURES
        for i in range(_WATER_FEATURES):
            _, std = waterStats[i]
            weightSum += w
            if std > 0.0:
                sumSq += w * (((a.water[i] - b.water[i]) / std) ** 2)

    w = cfg.forecastWeightActivity / _ACTIVITY_FEATURES
    for i in range(_ACTIVITY_FEATURES):
        _, std = activityStats[i]
        weightSum += w
        if std > 0.0:
            sumSq += w * (((a.activities[i] - b.activities[i]) / std) ** 2)

    return math.sqrt(sumSq / weightSum) if weightSum > 0.0 else 0.0


def rankDays(
    today: DayFeatures,
    candidates: Sequence[DayFeatures],
    todayDate: date,
    cfg: AnalysisConfig,
) -> tuple[Neighbor, ...]:
    """เรียงวันอดีตตามระยะทาง (ถ่วง recency penalty 2^(age/halfLife)), tie → วันที่เก่ากว่า."""
    allDays = [today, *candidates]
    waterStats = _stats([d.water for d in allDays], _WATER_FEATURES)
    activityStats = _stats([d.activities for d in allDays], _ACTIVITY_FEATURES)

    out: list[Neighbor] = []
    for cand in candidates:
        raw = _distance(today, cand, waterStats, activityStats, cfg)
        age = float((todayDate - cand.day).days)
        penalty = 2.0 ** (age / cfg.forecastRecencyHalfLifeDays)
        out.append(Neighbor(day=cand.day, distance=raw * penalty))

    out.sort(key=lambda n: (n.distance, n.day))
    return tuple(out)
