"""Time and data helpers for analysis pipeline.

All timestamps are stored as naive UTC.
Clock-based decisions (local hour, date, night window) MUST use these helpers with pond.timezone.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from config.constants import AnalysisConfig, cfg as default_cfg


def localTime(dt: datetime, tzName: str) -> datetime:
    """Convert a naive UTC datetime to naive pond-local datetime."""
    utcDt = dt.replace(tzinfo=timezone.utc)
    localDt = utcDt.astimezone(ZoneInfo(tzName))
    return localDt.replace(tzinfo=None)


def toUtc(localDt: datetime, tzName: str) -> datetime:
    """Convert a naive pond-local datetime to naive UTC datetime."""
    awareLocal = localDt.replace(tzinfo=ZoneInfo(tzName))
    utcDt = awareLocal.astimezone(timezone.utc)
    return utcDt.replace(tzinfo=None)


def nightWindowFor(
    t: datetime,
    tzName: str,
    cfg: AnalysisConfig = default_cfg
) -> tuple[datetime, datetime]:
    """Calculate the night window encompassing time `t`.

    Per Override O2:
    - If localTime(t).hour < nightEndHour: night started on previous local date.
    - Else: night started on the same local date.
    - Window = nightDate nightStartHour:00 -> (nightDate + 1) nightEndHour:00 local time.
    Returns (start_utc, end_utc) as naive UTC datetimes.
    """
    local = localTime(t, tzName)
    if local.hour < cfg.nightEndHour:
        nightDate = local.date() - timedelta(days=1)
    else:
        nightDate = local.date()

    localStart = datetime.combine(nightDate, time(hour=cfg.nightStartHour, minute=0))
    localEnd = datetime.combine(nightDate + timedelta(days=1), time(hour=cfg.nightEndHour, minute=0))

    return toUtc(localStart, tzName), toUtc(localEnd, tzName)


def isNight(
    t: datetime,
    tzName: str,
    cfg: AnalysisConfig = default_cfg
) -> bool:
    """Check if `t` falls within the night window."""
    startUtc, endUtc = nightWindowFor(t, tzName, cfg)
    return startUtc <= t < endUtc


def isStale(
    readingDt: datetime,
    now: datetime,
    cfg: AnalysisConfig = default_cfg
) -> bool:
    """Check if reading timestamp is older than staleFactor × expectedIntervalMinutes."""
    maxAgeMinutes = cfg.staleFactor * cfg.expectedIntervalMinutes
    return (now - readingDt) > timedelta(minutes=maxAgeMinutes)
