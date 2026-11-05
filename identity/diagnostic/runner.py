"""Pure Phase 2 diagnostic runner."""
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.changeset import changedOnly
from identity.analysis.helpers import isStale
from identity.analysis.ids import diagId
from identity.analysis.models import (
    DiagnosticReport,
    DiagStatus,
    PondSnapshot,
    Signal,
    SignalSource,
    Trigger,
    TriggerKind,
)
from identity.diagnostic.cause_rules import CauseContext, evaluateCauses
from identity.diagnostic.episode import Episode, buildEpisodes, qualifies
from identity.parameters.pond_parameter_enum import PondParameters


@dataclass(frozen=True)
class DiagnosticResult:
    diagnostics: tuple[DiagnosticReport, ...]
    allDiagnostics: tuple[DiagnosticReport, ...]
    episodes: tuple[Episode, ...]


def _reportFrom(
    episode: Episode,
    pondId: str,
    pond,
    ctx: CauseContext,
) -> DiagnosticReport:
    causes, noClearCause = evaluateCauses(episode.parameter, episode.direction, episode.onsetAt, ctx)
    return DiagnosticReport(
        id=diagId(pondId, episode.parameter, episode.direction, episode.onsetAt),
        pondId=pondId,
        parameter=episode.parameter,
        direction=episode.direction,
        onsetAt=episode.onsetAt,
        endAt=episode.endAt,
        status=episode.status,
        peakSeverity=episode.peakSeverity,
        lastSeverity=episode.lastSeverity,
        causes=causes,
        noClearCause=noClearCause,
        pondSnapshot=pond,
        revisedAt=None,
    )


def runDiagnostic(
    snapshot: PondSnapshot,
    trigger: Trigger,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> DiagnosticResult:
    """Build/update qualifying diagnostics without mutating snapshot (Phase 2 §3)."""
    allEpisodes = tuple(
        sorted(
            (ep for parameter in PondParameters for ep in buildEpisodes(snapshot.severityReports, parameter)),
            key=lambda ep: (ep.onsetAt, list(PondParameters).index(ep.parameter)),
        )
    )
    existingById = {report.id: report for report in snapshot.diagnostics}
    allReports: list[DiagnosticReport] = []

    for episode in allEpisodes:
        if not qualifies(episode, cfg):
            continue
        reportId = diagId(snapshot.pond.pondId, episode.parameter, episode.direction, episode.onsetAt)
        existing = existingById.get(reportId)
        parameterViews = tuple(v for v in snapshot.severityReports if v.parameter == episode.parameter)
        newest = max(parameterViews, key=lambda v: v.time) if parameterViews else None
        stale = newest is not None and isStale(newest.time, now, cfg)

        if existing is None:
            if stale:
                continue
            ctx = CauseContext(snapshot.pond, snapshot.severityReports, snapshot.activities, cfg)
            allReports.append(_reportFrom(episode, snapshot.pond.pondId, snapshot.pond, ctx))
            continue

        updated = replace(
            existing,
            endAt=episode.endAt,
            status=episode.status,
            peakSeverity=episode.peakSeverity,
            lastSeverity=episode.lastSeverity,
        )
        shouldReevaluate = (
            trigger.kind == TriggerKind.activityEvent
            and trigger.tFrom is not None
            and episode.onsetAt >= trigger.tFrom
        )
        if shouldReevaluate:
            ctx = CauseContext(existing.pondSnapshot, snapshot.severityReports, snapshot.activities, cfg)
            causes, noClearCause = evaluateCauses(episode.parameter, episode.direction, episode.onsetAt, ctx)
            if causes != existing.causes or noClearCause != existing.noClearCause:
                updated = replace(updated, causes=causes, noClearCause=noClearCause, revisedAt=now)
        allReports.append(updated)

    allReportsTuple = tuple(sorted(allReports, key=lambda r: (r.onsetAt, list(PondParameters).index(r.parameter))))
    return DiagnosticResult(
        diagnostics=changedOnly(allReportsTuple, existingById),
        allDiagnostics=allReportsTuple,
        episodes=allEpisodes,
    )


def diagnosticSignals(reports: Iterable[DiagnosticReport]) -> tuple[Signal, ...]:
    """Normalize diagnostics as Phase 5 signals (shared contract §3.2)."""
    return tuple(
        Signal(
            sourceType=SignalSource.episode,
            sourceId=report.id,
            code="DIAG_EPISODE",
            parameter=report.parameter,
            active=report.status == DiagStatus.open,
            riskStart=None,
            riskEnd=None,
            peakSeverity=report.peakSeverity,
            lastSeverity=report.lastSeverity,
            scope=None,
            facts={"direction": report.direction, "onsetAt": report.onsetAt},
        )
        for report in reports
    )
