"""Raw readings → local-day 30-minute slot series (kNN forecast input)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from config.constants import AnalysisConfig
from identity.analysis.helpers import localDayBounds, localTime
from identity.parameters.pond_parameter_enum import PondParameters


@dataclass(frozen=True)
class Reading:
    """1 แถว sensor_readings (naive UTC). ค่า None = sensor ไม่ได้ส่งค่านั้น."""
    time: datetime
    values: dict[PondParameters, float | None]


@dataclass(frozen=True)
class DaySeries:
    """ค่าของ 1 parameter ใน 1 local day แบ่งเป็น slot ตาม forecastStepMinutes."""
    day: date
    values: tuple[float | None, ...]

    @property
    def coverage(self) -> float:
        if not self.values:
            return 0.0
        return sum(1 for v in self.values if v is not None) / len(self.values)


def slotsPerDay(cfg: AnalysisConfig) -> int:
    return (24 * 60) // cfg.forecastStepMinutes


def slotIndex(t: datetime, tz: str, cfg: AnalysisConfig) -> int:
    """slot ของเวลาท้องถิ่น (นาทีของวัน // step) — ใช้ทั้ง known window และจุดอนาคต."""
    loc = localTime(t, tz)
    return (loc.hour * 60 + loc.minute) // cfg.forecastStepMinutes


def parameterSamples(
    readings: Sequence[Reading], parameter: PondParameters
) -> tuple[tuple[datetime, float], ...]:
    """(time, value) ของ parameter เดียว จาก readings ที่ค่านั้นไม่ None."""
    return tuple(
        (r.time, v)
        for r in readings
        if (v := r.values.get(parameter)) is not None
    )


def buildDaySeries(
    samples: Sequence[tuple[datetime, float]],
    day: date,
    tz: str,
    cfg: AnalysisConfig,
) -> DaySeries:
    """bucket samples ของ local day → slots; เฉลี่ยค่าที่ตก slot เดียวกัน.

    ช่องว่าง 1 slot ที่มีค่าคร่อมทั้งสองข้างถูก interpolate (ช่องว่างใหญ่กว่านั้นคง None
    → จุด forecast ที่อ้างวันนั้นจะตัดสิทธิ์เฉพาะ slot ไม่ใช่ตัดทั้งวัน).
    """
    n = slotsPerDay(cfg)
    buckets: list[list[float]] = [[] for _ in range(n)]
    start, end = localDayBounds(day, tz)
    for t, v in samples:
        if not (start <= t < end):
            continue
        idx = slotIndex(t, tz, cfg)
        if 0 <= idx < n:
            buckets[idx].append(v)

    values: list[float | None] = [(sum(b) / len(b)) if b else None for b in buckets]
    for i in range(1, n - 1):
        left, right = values[i - 1], values[i + 1]
        if values[i] is None and left is not None and right is not None:
            values[i] = (left + right) / 2.0
    return DaySeries(day=day, values=tuple(values))
