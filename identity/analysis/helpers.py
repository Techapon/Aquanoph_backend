"""Time and data helpers for analysis pipeline.

All timestamps are stored as naive UTC.
Clock-based decisions (local hour, date, night window) MUST use these helpers with pond.timezone.
Strictly follows PHASE_1_foundation.md §5:
  toUtcNaive(aware) -> naive UTC datetime
  localTime(t, tz) -> aware local datetime
  inLocalWindow(t, tz, fromHour, toHour) -> bool    # [from,to), supports wrap (22,6)
  isNight(t, tz, cfg) -> bool                       # nightStartHour <= local < nightEndHour (wrap)
  nightWindowFor(t, tz, cfg) -> NightWindow(nightDate: date, start: datetime, end: datetime)
  localDate(t, tz) -> date
  doneActivities(acts, type, fromT, toT) -> tuple
  plannedActivities(acts, type, fromT, toT, now) -> tuple
  mealPct(activity, pond) -> float
  aerationHours(acts, fromT, toT) -> float
  zoneAt(views, parameter, t, cfg) -> SeverityReportView|None
  isStale(lastTime, now, cfg) -> bool
  overlap(aStart, aEnd, bStart, bEnd) -> timedelta
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, NamedTuple, Sequence
from zoneinfo import ZoneInfo

from config.constants import AnalysisConfig, cfg as default_cfg
from identity.analysis.models import Activity, ActivityStatus, ActivityType, PondInfo
from identity.analysis.severity_view import SeverityReportView
from identity.parameters.pond_parameter_enum import PondParameters


class NightWindow(NamedTuple):
    nightDate: date
    start: datetime  # naive UTC
    end: datetime    # naive UTC


def toUtcNaive(aware: datetime) -> datetime:
    """Convert an aware datetime into naive UTC datetime."""
    utcDt = aware.astimezone(timezone.utc)
    return utcDt.replace(tzinfo=None)


def localTime(t: datetime, tz: str) -> datetime:
    """Convert naive UTC datetime t to aware local datetime."""
    utcDt = t.replace(tzinfo=timezone.utc)
    return utcDt.astimezone(ZoneInfo(tz))


def localDate(t: datetime, tz: str) -> date:
    """Return local date for naive UTC datetime t."""
    return localTime(t, tz).date()


def toUtc(localDt: datetime, tzName: str) -> datetime:
    """Convert naive local datetime to naive UTC datetime (helper)."""
    awareLocal = localDt.replace(tzinfo=ZoneInfo(tzName))
    return toUtcNaive(awareLocal)


def inLocalWindow(t: datetime, tz: str, fromHour: int, toHour: int) -> bool:
    """Check if local hour of t falls in [fromHour, toHour), supporting midnight wrap (e.g. 22 to 6)."""
    loc = localTime(t, tz)
    h = loc.hour
    m = loc.minute
    totalMinutes = h * 60 + m
    fromMin = fromHour * 60
    toMin = toHour * 60

    if fromMin < toMin:
        return fromMin <= totalMinutes < toMin
    else:  # wraps midnight
        return totalMinutes >= fromMin or totalMinutes < toMin


def isNight(t: datetime, tz: str, cfg: AnalysisConfig = default_cfg) -> bool:
    """Check if t is within night window: nightStartHour <= local < nightEndHour (wrap)."""
    return inLocalWindow(t, tz, cfg.nightStartHour, cfg.nightEndHour)


def nightWindowFor(
    t: datetime,
    tz: str,
    cfg: AnalysisConfig = default_cfg
) -> NightWindow:
    """Calculate the night window encompassing time t per AGENT_CONTEXT O2.

    If localTime(t).hour < nightEndHour: night started on previous local date.
    Else: night started on the same local date.
    Window = nightDate nightStartHour:00 -> (nightDate + 1) nightEndHour:00 local time.
    Returns NightWindow(nightDate, start, end) as naive UTC datetimes.
    """
    loc = localTime(t, tz)
    if loc.hour < cfg.nightEndHour:
        nightD = loc.date() - timedelta(days=1)
    else:
        nightD = loc.date()

    localStart = datetime.combine(nightD, time(hour=cfg.nightStartHour, minute=0))
    localEnd = datetime.combine(nightD + timedelta(days=1), time(hour=cfg.nightEndHour, minute=0))

    startUtc = toUtc(localStart, tz)
    endUtc = toUtc(localEnd, tz)
    return NightWindow(nightDate=nightD, start=startUtc, end=endUtc)


def isStale(
    lastTime: datetime,
    now: datetime,
    cfg: AnalysisConfig = default_cfg
) -> bool:
    """Check if reading timestamp is strictly older than staleFactor × expectedIntervalMinutes."""
    maxAgeMinutes = cfg.staleFactor * cfg.expectedIntervalMinutes
    return (now - lastTime) > timedelta(minutes=maxAgeMinutes)


def zoneAt(
    views: Sequence[SeverityReportView],
    parameter: PondParameters,
    t: datetime,
    cfg: AnalysisConfig = default_cfg
) -> SeverityReportView | None:
    """Return the latest view with time <= t and t - time <= staleFactor*interval, else None."""
    candidates = [v for v in views if v.parameter == parameter and v.time <= t]
    if not candidates:
        return None
    latest = max(candidates, key=lambda v: v.time)
    if isStale(latest.time, t, cfg):
        return None
    return latest


def overlap(
    aStart: datetime,
    aEnd: datetime,
    bStart: datetime,
    bEnd: datetime
) -> timedelta:
    """Return the overlap duration as timedelta (0 if no overlap)."""
    delta = min(aEnd, bEnd) - max(aStart, bStart)
    return max(timedelta(0), delta)


def doneActivities(
    acts: Sequence[Activity],
    type: ActivityType | None = None,
    fromT: datetime | None = None,
    toT: datetime | None = None,
) -> tuple[Activity, ...]:
    """Return activities with status done, startTime in [fromT, toT)."""
    res: list[Activity] = []
    for a in acts:
        if a.status != ActivityStatus.done:
            continue
        if type is not None and a.type != type:
            continue
        if fromT is not None and a.startTime < fromT:
            continue
        if toT is not None and a.startTime >= toT:
            continue
        res.append(a)
    return tuple(res)


def plannedActivities(
    acts: Sequence[Activity],
    type: ActivityType | None = None,
    fromT: datetime | None = None,
    toT: datetime | None = None,
    now: datetime | None = None,
) -> tuple[Activity, ...]:
    """Return activities with status pending, startTime in [fromT, toT) and startTime >= now."""
    res: list[Activity] = []
    for a in acts:
        if a.status != ActivityStatus.pending:
            continue
        if type is not None and a.type != type:
            continue
        if fromT is not None and a.startTime < fromT:
            continue
        if toT is not None and a.startTime >= toT:
            continue
        if now is not None and a.startTime < now:
            continue
        res.append(a)
    return tuple(res)


def mealPct(activity: Activity, pond: PondInfo) -> float:
    """Return (quantityKg / pond.biomassKg) * 100.

    Raises ValueError if activity is not feeding or quantityKg is None, or biomassKg <= 0.
    """
    if activity.type != ActivityType.feeding or activity.quantityKg is None:
        raise ValueError("activity must be feeding with quantityKg specified")
    if pond.biomassKg <= 0:
        raise ValueError("pond.biomassKg must be positive")
    return (activity.quantityKg / pond.biomassKg) * 100.0


def aerationHours(
    acts: Sequence[Activity],
    fromT: datetime | None = None,
    toT: datetime | None = None,
) -> float:
    """Calculate total effective aeration hours from activities in [fromT, toT).

    Done and pending aeration overlap hours, merged (no double count), skipped excluded.
    """
    intervals: list[tuple[datetime, datetime]] = []
    for act in acts:
        if act.type != ActivityType.aeration:
            continue
        if act.status == ActivityStatus.skipped:
            continue
        if not act.startTime or not act.endTime:
            continue
        if act.startTime >= act.endTime:
            continue

        start = act.startTime
        end = act.endTime

        if fromT is not None:
            start = max(start, fromT)
        if toT is not None:
            end = min(end, toT)

        if start < end:
            intervals.append((start, end))

    if not intervals:
        return 0.0

    intervals.sort(key=lambda iv: iv[0])
    merged: list[tuple[datetime, datetime]] = [intervals[0]]
    for curStart, curEnd in intervals[1:]:
        lastStart, lastEnd = merged[-1]
        if curStart <= lastEnd:
            merged[-1] = (lastStart, max(lastEnd, curEnd))
        else:
            merged.append((curStart, curEnd))

    totalSeconds = sum((end - start).total_seconds() for start, end in merged)
    return totalSeconds / 3600.0


def dailyMealPct(
    acts: Sequence[Activity],
    pond: PondInfo,
    targetDate: date,
    tz: str,
) -> float:
    """Calculate total percentage of daily feed delivered on targetDate (local time).

    Rules:
    - Only ActivityStatus.done counts; pending and skipped ignored (Rule 6).
    - Uses localDate(act.startTime, tz) to match targetDate (Rule 3).
    - Skips feeding activities where quantityKg is None without assuming 0 (Rule 5).
    - Delegates to mealPct per activity and sums the results.
    """
    totalPct = 0.0
    for act in acts:
        if act.type != ActivityType.feeding or act.status != ActivityStatus.done:
            continue
        if act.quantityKg is None:
            continue
        if localDate(act.startTime, tz) == targetDate:
            totalPct += mealPct(act, pond)
    return totalPct


def localDayBounds(d: date, tz: str) -> tuple[datetime, datetime]:
    """Return local day [00:00, next 00:00) as naive UTC datetimes."""
    zone = ZoneInfo(tz)
    localStart = datetime.combine(d, time.min, tzinfo=zone)
    localEnd = datetime.combine(d + timedelta(days=1), time.min, tzinfo=zone)
    return toUtcNaive(localStart), toUtcNaive(localEnd)

