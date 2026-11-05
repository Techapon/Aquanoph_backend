"""Pure Phase 4 prediction lifecycle runner."""
from dataclasses import replace
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.changeset import changedOnly
from identity.analysis.ids import predId
from identity.analysis.models import PondSnapshot, PredStatus, Prediction, Signal, SignalSource
from identity.diagnostic.episode import buildEpisodes
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.rules import do_night, do_repeat, nh3_rise
from identity.prediction.rules._common import PredictionContext
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType

RULE_MODULES = (do_night, do_repeat, nh3_rise)


def _moduleFor(ruleId: str):
    for mod in RULE_MODULES:
        if mod.RULE_ID == ruleId:
            return mod
    raise ValueError(f"Unknown prediction rule: {ruleId}")


def runPredictions(
    snapshot: PondSnapshot,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
    doEpisodes=None,
) -> tuple[Prediction, ...]:
    """Evaluate prediction rules and return changed predictions only."""
    episodes = doEpisodes if doEpisodes is not None else buildEpisodes(snapshot.severityReports, PondParameters.DO)

    activeByRule: dict[str, Prediction] = {}
    endedExpired: list[Prediction] = []
    # Step 1: window_over before rules
    for pred in snapshot.predictions:
        if pred.status == PredStatus.active and now > pred.riskEnd:
            endedExpired.append(replace(pred, status=PredStatus.ended, endReason="window_over", revisedAt=now))
        elif pred.status == PredStatus.active:
            if pred.ruleId in activeByRule:
                continue
            activeByRule[pred.ruleId] = pred

    results: list[Prediction] = []
    results.extend(endedExpired)
    candidateNew: list[Prediction] = []

    for mod in RULE_MODULES:
        ruleId = mod.RULE_ID
        active = activeByRule.get(ruleId)
        ruleCtx = PredictionContext(
            pond=snapshot.pond,
            views=snapshot.severityReports,
            activities=snapshot.activities,
            doEpisodes=episodes if ruleId == do_repeat.RULE_ID else (),
            active=active,
            now=now,
            cfg=cfg,
        )
        result = mod.evaluate(ruleCtx)

        if result.skip:
            continue

        if result.fire:
            if active is None:
                assert result.riskStart is not None and result.riskEnd is not None
                candidateNew.append(Prediction(
                    id=predId(snapshot.pond.pondId, ruleId, result.scope, now),
                    pondId=snapshot.pond.pondId,
                    ruleId=ruleId,
                    scope=result.scope,
                    parameter=PondParameters.DO if ruleId != nh3_rise.RULE_ID else PondParameters.NH3,
                    expectedZone=ThresholdLevelType.HighRisk,
                    riskStart=result.riskStart,
                    riskEnd=result.riskEnd,
                    met=result.met,
                    status=PredStatus.active,
                    endReason=None,
                    evidence=dict(result.evidence),
                    pondSnapshot=snapshot.pond,
                    createdAt=now,
                    revisedAt=None,
                ))
            elif active.scope != result.scope:
                results.append(replace(active, status=PredStatus.ended, endReason="conditions_gone", revisedAt=now))
                activeByRule.pop(ruleId, None)
                assert result.riskStart is not None and result.riskEnd is not None
                candidateNew.append(Prediction(
                    id=predId(snapshot.pond.pondId, ruleId, result.scope, now),
                    pondId=snapshot.pond.pondId,
                    ruleId=ruleId,
                    scope=result.scope,
                    parameter=active.parameter,
                    expectedZone=active.expectedZone,
                    riskStart=result.riskStart,
                    riskEnd=result.riskEnd,
                    met=result.met,
                    status=PredStatus.active,
                    endReason=None,
                    evidence=dict(result.evidence),
                    pondSnapshot=snapshot.pond,
                    createdAt=now,
                    revisedAt=None,
                ))
            else:
                assert result.riskStart is not None and result.riskEnd is not None
                candidate = replace(
                    active,
                    riskStart=result.riskStart,
                    riskEnd=result.riskEnd,
                    met=result.met,
                    evidence=dict(result.evidence),
                    pondSnapshot=snapshot.pond,
                )
                if candidate != active:
                    results.append(replace(candidate, revisedAt=now))
        else:
            if active is not None:
                assert result.reason in ("mitigated", "conditions_gone")
                results.append(replace(active, status=PredStatus.ended, endReason=result.reason, revisedAt=now))
                activeByRule.pop(ruleId, None)

    results.extend(candidateNew)
    orderIdx = {mod.RULE_ID: i for i, mod in enumerate(RULE_MODULES)}
    ordered = tuple(sorted(results, key=lambda p: (orderIdx.get(p.ruleId, 99), p.createdAt, p.id)))
    existingById = {p.id: p for p in snapshot.predictions}
    return changedOnly(ordered, existingById)


def predictionSignals(predictions: Iterable[Prediction]) -> tuple[Signal, ...]:
    """Normalize predictions as Phase 5 signals (shared contract §3.2)."""
    return tuple(
        Signal(
            sourceType=SignalSource.prediction,
            sourceId=p.id,
            code=p.ruleId,
            parameter=p.parameter,
            active=p.status == PredStatus.active,
            riskStart=p.riskStart,
            riskEnd=p.riskEnd,
            peakSeverity=None,
            lastSeverity=None,
            scope=p.scope,
            facts=dict(p.evidence),
        )
        for p in predictions
    )
