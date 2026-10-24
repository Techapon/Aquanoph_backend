from datetime import datetime, timedelta
from typing import NamedTuple

from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType

STRESS_OR_WORSE = {ThresholdLevelType.Stress, ThresholdLevelType.HighRisk, ThresholdLevelType.Critical}
ELEVATED_OR_WORSE = {ThresholdLevelType.HighRisk, ThresholdLevelType.Critical}

ZONE_BY_LEVEL = {
    ThresholdLevelType.Stress: STRESS_OR_WORSE,
    ThresholdLevelType.HighRisk: ELEVATED_OR_WORSE,
}

class ZoneMetrics(NamedTuple):
    continuousMinute: float   
    cumMinute: float          


def buildTimeline(analysisHis, currentLevel, now):
    points = [(r.dateTime, r.thresholdStatus) for r in reversed(analysisHis)]
    points.append((now, currentLevel))
    return points

def countEpisodes(
    timeline,
    now: datetime,
    separationHours: float,
    windowHours: int = 24,
) -> int:
    windowStart = now - timedelta(hours=windowHours)
    separation = timedelta(hours=separationHours)

    count = 0
    inZone = False
    exitTime: datetime | None = None 

    for t, level in timeline:
        if t < windowStart:
            continue

        if level in ELEVATED_OR_WORSE:
            if not inZone:
                if exitTime is None or (t - exitTime) >= separation:
                    count += 1
                inZone = True
                exitTime = None
        else:
            if inZone:
                inZone = False
                exitTime = t  

    return count

def calZoneMetrics(timeline, now: datetime, zone: set, windowHours: int = 24) -> ZoneMetrics:
    # continuous
    streakStart = now
    for t, level in reversed(timeline):
        if level not in zone:
            break
        streakStart = t
    continuousMinute = (now - streakStart).total_seconds() / 60

    # cumulative 
    windowStart = now - timedelta(hours=windowHours)
    cumMinute = 0.0
    for (t0, level0), (t1, _) in zip(timeline, timeline[1:]):
        if level0 not in zone:
            continue
        start = max(t0, windowStart)
        if t1 > start:
            cumMinute += (t1 - start).total_seconds() / 60

    return ZoneMetrics(continuousMinute, cumMinute)