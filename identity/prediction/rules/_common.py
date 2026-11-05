"""Shared prediction rule helpers (Phase 4 §1)."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from config.constants import AnalysisConfig
from identity.analysis.helpers import (
    aerationHours,
    doneActivities,
    inLocalWindow,
    localTime,
    mealPct,
    nightWindowFor,
    plannedActivities,
    zoneAt,
)
from identity.analysis.models import (
    Activity,
    ActivityType,
    PondInfo,
    Prediction,
)
from identity.analysis.severity_view import SeverityReportView
from identity.diagnostic.episode import Episode
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


@dataclass(frozen=True)
class PredictionContext:
    pond: PondInfo
    views: tuple[SeverityReportView, ...]
    activities: tuple[Activity, ...]
    doEpisodes: tuple[Episode, ...]
    active: Prediction | None
    now: datetime
    cfg: AnalysisConfig


@dataclass(frozen=True)
class RuleResult:
    skip: bool
    fire: bool
    reason: str | None
    met: tuple[str, ...]
    scope: str | None
    riskStart: datetime | None
    riskEnd: datetime | None
    evidence: Mapping[str, Any] = field(default_factory=dict)


def anchor(ctx: PredictionContext) -> datetime:
    """Stable anchor: active.createdAt if an active prediction exists, else now."""
    return ctx.active.createdAt if ctx.active else ctx.now


def metFrom(conditions: Mapping[str, bool]) -> tuple[str, ...]:
    """Return true condition ids in deterministic C-order."""
    return tuple(k for k in sorted(conditions.keys()) if conditions[k])


def nightWindowForDate(nightDate: date, tz: str, cfg: AnalysisConfig):
    """Build the night window for a given night date via noon of that date."""
    noonLocal = datetime(nightDate.year, nightDate.month, nightDate.day, 12, 0)
    from identity.analysis.helpers import toUtc
    noonUtc = toUtc(noonLocal, tz)
    return nightWindowFor(noonUtc, tz, cfg)


def eveningQualifyingMeal(act: Activity, pond: PondInfo, tz: str, cfg: AnalysisConfig) -> bool:
    """Return True when a feeding qualifies as an evening heavy meal candidate."""
    if act.type != ActivityType.feeding or act.quantityKg is None:
        return False
    loc = localTime(act.startTime, tz)
    if loc.hour * 60 + loc.minute < cfg.eveningFromHour * 60:
        return False
    return mealPct(act, pond) >= cfg.heavyMealPct


def localEveningHourOk(startTime: datetime, tz: str, cfg: AnalysisConfig) -> bool:
    """Return True when local start hour is at or after eveningFromHour."""
    loc = localTime(startTime, tz)
    return loc.hour * 60 + loc.minute >= cfg.eveningFromHour * 60


def tempHighNow(views: Sequence[SeverityReportView], now: datetime, cfg: AnalysisConfig) -> SeverityReportView | None:
    """Return the current fresh Temperature High-abnormal view, if any."""
    view = zoneAt(views, PondParameters.tem, now, cfg)
    if view is None or view.zone == ThresholdLevelType.Optimal:
        return None
    from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
    if view.direction != ThresholdDirection.High:
        return None
    return view


def tempHighRecent(views: Sequence[SeverityReportView], now: datetime, hours: int, cfg: AnalysisConfig) -> tuple[SeverityReportView, ...]:
    """Return Temperature High-abnormal views within [now - hours, now] (spec §2 C2)."""
    from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
    fromT = now - timedelta(hours=hours)
    inclusive = now + timedelta(microseconds=1)
    return tuple(
        v for v in views
        if v.parameter == PondParameters.tem
        and fromT <= v.time <= inclusive
        and v.zone != ThresholdLevelType.Optimal
        and v.direction == ThresholdDirection.High
    )


def aerationHoursIn(activities: tuple[Activity, ...], fromT: datetime, toT: datetime) -> float:
    """Return merged aeration hours in [fromT, toT)."""
    return aerationHours(activities, fromT, toT)


INCLUSIVE_EPSILON = timedelta(microseconds=1)
