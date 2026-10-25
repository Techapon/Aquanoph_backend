from datetime import datetime, timedelta
from typing import Callable, NamedTuple

from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection

STRESS_OR_WORSE = {ThresholdLevelType.Stress, ThresholdLevelType.HighRisk, ThresholdLevelType.Critical}
ELEVATED_OR_WORSE = {ThresholdLevelType.HighRisk, ThresholdLevelType.Critical}

ZONE_BY_LEVEL = {
    ThresholdLevelType.Stress: STRESS_OR_WORSE,
    ThresholdLevelType.HighRisk: ELEVATED_OR_WORSE,
}

# severity ที่ต้องมี Recovery Hold หลังเกิดเหตุ
NEED_RECOVERY = (SeverityLevelType.ElevatedRisk, SeverityLevelType.Critical)


class TimelinePoint(NamedTuple):
    time: datetime
    level: ThresholdLevelType
    direction: ThresholdDirection | None


class ZoneMetrics(NamedTuple):
    continuousMinute: float
    cumMinute: float


class RecoveryState(NamedTuple):
    event: AnalysisReportModel | None   # เหตุการณ์ Elevated/Critical ที่ยังฟื้นไม่ครบ
    optimalSince: datetime | None       # เวลาที่ค่าเริ่มอยู่ Optimal ต่อเนื่องจนถึงปัจจุบัน


def _minutes(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60


def _inZone(point: TimelinePoint, zoneLevels: set, direction: ThresholdDirection | None) -> bool:
    # หัวใจของ Range model: ต้องอยู่ในโซนที่กำหนด *และ* ฝั่งเดียวกับค่าปัจจุบันเท่านั้น
    # Level model: direction เป็น None ทั้งคู่ จึงเทียบเท่าพฤติกรรมเดิม
    return point.level in zoneLevels and point.direction == direction


def buildTimeline(
    history: list[AnalysisReportModel],
    currentLevel: ThresholdLevelType,
    currentDirection: ThresholdDirection | None,
    now: datetime,
) -> list[TimelinePoint]:
    """history ต้องกรองเฉพาะ parameter นี้และเรียงเก่า -> ใหม่มาแล้ว (evaluator ทำให้)"""
    points = [TimelinePoint(r.dateTime, r.thresholdStatus, r.thresholdDirection) for r in history]
    points.append(TimelinePoint(now, currentLevel, currentDirection))
    return points


def calZoneMetrics(
    timeline: list[TimelinePoint],
    now: datetime,
    zoneLevels: set,
    direction: ThresholdDirection | None,
    windowHours: int = 24,
) -> ZoneMetrics:
    # continuous: ถอยหลังจากปัจจุบันตราบที่ยังอยู่ในโซนและฝั่งเดียวกัน
    streakStart = now
    for p in reversed(timeline):
        if not _inZone(p, zoneLevels, direction):
            break
        streakStart = p.time
    continuousMinute = _minutes(streakStart, now)

    # cumulative: รวมช่วงเวลาที่อยู่ในโซน+ฝั่งเดียวกัน ภายใน window
    windowStart = now - timedelta(hours=windowHours)
    cumMinute = 0.0
    for a, b in zip(timeline, timeline[1:]):
        if not _inZone(a, zoneLevels, direction):
            continue
        start = max(a.time, windowStart)
        if b.time > start:
            cumMinute += _minutes(start, b.time)

    return ZoneMetrics(continuousMinute, cumMinute)


def countEpisodes(
    timeline: list[TimelinePoint],
    now: datetime,
    direction: ThresholdDirection | None,
    separationHours: float,
    windowHours: int = 24,
) -> int:
    windowStart = now - timedelta(hours=windowHours)
    separation = timedelta(hours=separationHours)

    count = 0
    inZone = False
    exitTime: datetime | None = None

    for p in timeline:
        if p.time < windowStart:
            continue

        if _inZone(p, ELEVATED_OR_WORSE, direction):
            if not inZone:
                if exitTime is None or (p.time - exitTime) >= separation:
                    count += 1
                inZone = True
                exitTime = None
        else:
            if inZone:
                inZone = False
                exitTime = p.time

    return count


def findPendingRecovery(
    history: list[AnalysisReportModel],
    now: datetime,
    holdMinuteOf: Callable[[AnalysisReportModel], int],
) -> RecoveryState:
    """
    หาเหตุการณ์ Elevated/Critical ที่ "ยังฟื้นไม่ครบ" ณ ปัจจุบัน (ใช้เมื่อค่าปัจจุบันเป็น Optimal)

    ตามเอกสาร: Recovery Hold จบเมื่อค่าอยู่ Optimal *ต่อเนื่อง* ครบเวลา hold
    จึงเดินตาม history (เก่า -> ใหม่) แล้วจับว่า streak Optimal ยาวพอที่จะ "ล้าง" เหตุการณ์หรือยัง
    - เจอเหตุการณ์ใหม่ -> เริ่มค้างเหตุการณ์, streak Optimal เริ่มนับใหม่
    - ค่าหลุด Optimal -> streak Optimal ขาด
    - streak Optimal ยาว >= hold ของเหตุการณ์ที่ค้างอยู่ -> ล้างเหตุการณ์
    ปัจจุบัน (now) ถือเป็นตัวอย่าง Optimal สุดท้าย
    """
    pending: AnalysisReportModel | None = None
    optimalSince: datetime | None = None

    samples: list[tuple[datetime, AnalysisReportModel | None]] = [(r.dateTime, r) for r in history]
    samples.append((now, None))

    for t, r in samples:
        if r is not None and r.severityStatus in NEED_RECOVERY:
            pending = _stronger(pending, r)
            optimalSince = None
            continue

        isOptimal = r is None or r.thresholdStatus == ThresholdLevelType.Optimal
        if not isOptimal:
            optimalSince = None
            continue

        if optimalSince is None:
            optimalSince = t
        if pending is not None and _minutes(optimalSince, t) >= holdMinuteOf(pending):
            pending = None

    return RecoveryState(pending, optimalSince if pending is not None else None)


def _stronger(current: AnalysisReportModel | None, new: AnalysisReportModel) -> AnalysisReportModel:
    # Critical หนักกว่า Elevated; ถ้าเท่ากันใช้เหตุการณ์ที่ใหม่กว่า
    if current is None:
        return new
    if current.severityStatus == SeverityLevelType.Critical and new.severityStatus != SeverityLevelType.Critical:
        return current
    return new