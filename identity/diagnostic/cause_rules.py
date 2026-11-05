"""Diagnostic cause rules (Phase 2 §2)."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from config.constants import AnalysisConfig
from identity.analysis.helpers import doneActivities, inLocalWindow, isNight, localTime, mealPct, nightWindowFor
from identity.analysis.models import Activity, ActivityStatus, ActivityType, Cause, PondInfo
from identity.analysis.severity_view import SeverityReportView, zoneRank
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


@dataclass(frozen=True)
class CauseContext:
    pond: PondInfo
    views: tuple[SeverityReportView, ...]
    activities: tuple[Activity, ...]
    cfg: AnalysisConfig


def _viewsIn(
    views: tuple[SeverityReportView, ...],
    parameter: PondParameters,
    fromT: datetime,
    toT: datetime,
) -> tuple[SeverityReportView, ...]:
    return tuple(v for v in views if v.parameter == parameter and fromT <= v.time <= toT)


def _feedCause(
    ruleId: str,
    onsetAt: datetime,
    hours: int,
    ctx: CauseContext,
) -> Cause | None:
    fromT = onsetAt - timedelta(hours=hours)
    feeds = doneActivities(ctx.activities, ActivityType.feeding, fromT, onsetAt)
    if not feeds:
        return None

    known = tuple(a for a in feeds if a.quantityKg is not None)
    unknownQtyCount = len(feeds) - len(known)
    headline = None
    if known:
        # Largest meal percentage, then latest on ties.
        headline = max(known, key=lambda a: (mealPct(a, ctx.pond), a.startTime))
        headlinePct = mealPct(headline, ctx.pond)
        kg = headline.quantityKg
    else:
        headlinePct = None
        kg = None

    facts = {
        "feedTime": headline.startTime if headline else None,
        "kg": kg,
        "mealPct": headlinePct,
        "isHeavy": headlinePct is not None and headlinePct >= ctx.cfg.heavyMealPct,
        "feedCount": len(feeds),
        "totalKg": sum(a.quantityKg for a in feeds if a.quantityKg is not None),
        "unknownQtyCount": unknownQtyCount,
        "hoursBeforeOnset": (onsetAt - (headline.startTime if headline else max(a.startTime for a in feeds))).total_seconds() / 3600,
    }
    return Cause(ruleId=ruleId, facts=facts)


def _doTempCause(onsetAt: datetime, ctx: CauseContext) -> Cause | None:
    views = _viewsIn(
        ctx.views, PondParameters.tem,
        onsetAt - timedelta(hours=ctx.cfg.tempLookbackHours), onsetAt,
    )
    candidates = tuple(
        v for v in views
        if v.zone != ThresholdLevelType.Optimal and v.direction == ThresholdDirection.High
    )
    if not candidates:
        return None
    selected = max(candidates, key=lambda v: (zoneRank(v), v.time))
    return Cause(ruleId="DO_C_TEMP", facts={
        "tempValue": selected.value,
        "tempZone": selected.zone,
        "tempTime": selected.time,
        "hoursBeforeOnset": (onsetAt - selected.time).total_seconds() / 3600,
    })


def _doNightCause(onsetAt: datetime, ctx: CauseContext) -> Cause | None:
    if not isNight(onsetAt, ctx.pond.timezone, ctx.cfg):
        return None
    aerationLogged = any(
        a.type == ActivityType.aeration
        and a.status != ActivityStatus.skipped
        and a.endTime is not None
        and a.startTime <= onsetAt < a.endTime
        for a in ctx.activities
    )
    window = nightWindowFor(onsetAt, ctx.pond.timezone, ctx.cfg)
    return Cause(ruleId="DO_C_NIGHT", facts={
        "nightDate": window.nightDate,
        "aerationLogged": aerationLogged,
    })


def _no2Nh3Cause(onsetAt: datetime, ctx: CauseContext) -> Cause | None:
    views = _viewsIn(
        ctx.views, PondParameters.NH3,
        onsetAt - timedelta(hours=ctx.cfg.nh3ChainLookbackHours), onsetAt,
    )
    abnormal = tuple(sorted(
        (v for v in views if v.zone != ThresholdLevelType.Optimal),
        key=lambda v: v.time,
    ))
    if not abnormal:
        return None
    peak = max(abnormal, key=lambda v: (zoneRank(v), v.time))
    return Cause(ruleId="NO2_C_NH3", facts={
        "nh3PeakZone": peak.zone,
        "nh3FirstTime": abnormal[0].time,
        "nh3LastTime": abnormal[-1].time,
    })


def _timeCause(
    ruleId: str,
    direction: ThresholdDirection | None,
    onsetAt: datetime,
    highWindow: tuple[int, int],
    lowWindow: tuple[int, int],
    ctx: CauseContext,
) -> Cause | None:
    if direction == ThresholdDirection.High:
        matches = inLocalWindow(onsetAt, ctx.pond.timezone, *highWindow)
    elif direction == ThresholdDirection.Low:
        matches = inLocalWindow(onsetAt, ctx.pond.timezone, *lowWindow)
    else:
        matches = False
    if not matches:
        return None
    return Cause(ruleId=ruleId, facts={
        "direction": direction,
        "onsetLocal": localTime(onsetAt, ctx.pond.timezone).isoformat(),
    })


def _salinityWaterChangeCause(onsetAt: datetime, ctx: CauseContext) -> Cause | None:
    fromT = onsetAt - timedelta(hours=ctx.cfg.salWaterChangeLookbackHours)
    changes = doneActivities(ctx.activities, ActivityType.waterChange, fromT, onsetAt)
    if not changes:
        return None
    selected = max(changes, key=lambda a: a.startTime)
    return Cause(ruleId="SAL_C_WATERCHG", facts={
        "waterChangeTime": selected.startTime,
        "fraction": selected.fraction,
        "hoursBeforeOnset": (onsetAt - selected.startTime).total_seconds() / 3600,
    })


def evaluateCauses(
    parameter: PondParameters,
    direction: ThresholdDirection | None,
    onsetAt: datetime,
    ctx: CauseContext,
) -> tuple[tuple[Cause, ...], bool]:
    """Evaluate matching causes in deterministic priority/table order (Phase 2 §2)."""
    matches: list[tuple[int, int, Cause]] = []

    if parameter == PondParameters.DO:
        feed = _feedCause("DO_C_FEED", onsetAt, ctx.cfg.feedLookbackDoHours, ctx)
        if feed:
            matches.append((1, 0, feed))
        temp = _doTempCause(onsetAt, ctx)
        if temp:
            matches.append((2, 1, temp))
        night = _doNightCause(onsetAt, ctx)
        if night:
            matches.append((3, 2, night))

    elif parameter == PondParameters.NH3:
        feed = _feedCause("NH3_C_FEED", onsetAt, ctx.cfg.feedLookbackNh3Hours, ctx)
        if feed:
            matches.append((1, 3, feed))

    elif parameter == PondParameters.NO2_N:
        nh3 = _no2Nh3Cause(onsetAt, ctx)
        if nh3:
            matches.append((1, 4, nh3))

    elif parameter == PondParameters.tem:
        tempTime = _timeCause(
            "TEMP_C_TIME", direction, onsetAt,
            ctx.cfg.tempHighWindow, ctx.cfg.tempLowWindow, ctx,
        )
        if tempTime:
            matches.append((1, 5, tempTime))

    elif parameter == PondParameters.pH:
        phTime = _timeCause(
            "PH_C_TIME", direction, onsetAt,
            ctx.cfg.phHighWindow, ctx.cfg.phLowWindow, ctx,
        )
        if phTime:
            matches.append((1, 6, phTime))

    elif parameter == PondParameters.salinity:
        waterChange = _salinityWaterChangeCause(onsetAt, ctx)
        if waterChange:
            matches.append((1, 7, waterChange))

    matches.sort(key=lambda m: (m[0], m[1]))
    causes = tuple(m[2] for m in matches[:ctx.cfg.maxCauses])
    return causes, len(causes) == 0
