"""Pure orchestrator: run_analysis(snapshot, trigger, now) -> ChangeSet."""
from dataclasses import replace
from datetime import datetime

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import Notification, PondSnapshot, Trigger, TriggerKind
from identity.diagnostic.detectors.ph_swing import detectPhSwing
from identity.diagnostic.runner import runDiagnostic, diagnosticSignals
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.runner import runPredictions, predictionSignals
from identity.recommendation.reconcile import reconcile
from identity.text.render import renderRecommendation


def run_analysis(snapshot, trigger, now, cfg=DEFAULT_CONFIG, renderer=renderRecommendation) -> "ChangeSet":
    """Run the full analysis pipeline and return a ChangeSet (Phase 7 §1)."""
    from identity.analysis.changeset import ChangeSet

    if trigger.kind == TriggerKind.activityEvent and trigger.tFrom is None:
        raise ValueError("activityEvent trigger requires tFrom")

    diag = runDiagnostic(snapshot, trigger, now, cfg)

    detector_signal = None
    if trigger.kind == TriggerKind.reading:
        detector_signal = detectPhSwing(snapshot.severityReports, snapshot.pond, now, cfg)

    do_episodes = tuple(e for e in diag.episodes if e.parameter == PondParameters.DO)
    pred_changes = runPredictions(snapshot, now, cfg, doEpisodes=do_episodes)

    # Overlay predChanges onto snapshot predictions by id.
    predMap = {p.id: p for p in snapshot.predictions}
    for p in pred_changes:
        predMap[p.id] = p
    all_predictions = tuple(predMap.values())

    signals = list(diagnosticSignals(diag.allDiagnostics))
    signals.extend(predictionSignals(all_predictions))
    if detector_signal is not None:
        signals.append(detector_signal)

    rec = reconcile(snapshot, tuple(signals), now, trigger, renderer, cfg)

    notifications = list(rec.notifications)
    # predictionEnded notifications for ended predictions.
    for p in pred_changes:
        if p.status.value == "ended":
            notifications.append(Notification(
                kind="predictionEnded",
                targetType="prediction",
                targetId=p.id,
                reasonKey=f"prediction.ended.{p.endReason}",
                facts={"predictionId": p.id, "ruleId": p.ruleId, "endReason": p.endReason},
            ))

    # Fill activityType in rec.changed.activity_edit notifications (rebuild with a real dict).
    if trigger.kind == TriggerKind.activityEvent and trigger.tFrom is not None:
        matching = [a for a in snapshot.activities if a.startTime == trigger.tFrom]
        if len(matching) == 1:
            filled: list[Notification] = []
            for n in notifications:
                if n.kind == "recChanged" and n.reasonKey == "rec.changed.activity_edit" and n.facts.get("activityType") is None:
                    facts = dict(n.facts)
                    facts["activityType"] = matching[0].type.value
                    filled.append(Notification(kind=n.kind, targetType=n.targetType,
                                              targetId=n.targetId, reasonKey=n.reasonKey, facts=facts))
                else:
                    filled.append(n)
            notifications = filled

    return ChangeSet(
        diagnostics=diag.diagnostics,
        predictions=pred_changes,
        recommendations=rec.recommendations,
        activityOps=(),
        notifications=tuple(notifications),
    )


runAnalysis = run_analysis
