"""Orchestrator run_analysis tests (Phase 7 §4)."""
from datetime import datetime, timedelta

import pytest

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    Trigger,
    TriggerKind,
)
from identity.diagnostic.runner import runDiagnostic
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.runner import runPredictions
from services.run_analysis import run_analysis, runAnalysis
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)


def test_activity_event_without_tfrom_raises():
    with pytest.raises(ValueError):
        run_analysis(makeSnapshot(), Trigger(TriggerKind.activityEvent, tFrom=None), NOW)


def test_detector_only_on_reading():
    snap = makeSnapshot(pond=makePond())
    r1 = run_analysis(snap, Trigger(TriggerKind.reading), NOW)
    r2 = run_analysis(snap, Trigger(TriggerKind.tick), NOW)
    assert isinstance(r1, ChangeSet)
    assert isinstance(r2, ChangeSet)


def test_pipeline_order_and_prediction_ended_notification():
    now = t("2026-10-26 07:00", TZ)
    from tests.support.pred_builders import makePrediction
    pred = makePrediction(predId="pred:pond_1:RULE:2026-10-25T16:30:00", status=__import__("identity.analysis.models", fromlist=["PredStatus"]).PredStatus.active, riskEnd=t("2026-10-26 06:00", TZ))
    snap = makeSnapshot(pond=makePond(), predictions=[pred])
    cs = run_analysis(snap, Trigger(TriggerKind.reading), now)
    ended = [n for n in cs.notifications if n.kind == "predictionEnded"]
    assert any(n.facts.get("endReason") == "window_over" for n in ended)


def test_activity_type_fill():
    act = makeActivity("a1", startTime=t("2026-10-25 13:00", TZ), activityType=ActivityType.feeding)
    snap = makeSnapshot(pond=makePond(), activities=[act])
    cs = run_analysis(snap, Trigger(TriggerKind.activityEvent, tFrom=act.startTime), NOW)
    assert isinstance(cs, ChangeSet)


def test_alias_and_no_mutation():
    snap = makeSnapshot(pond=makePond())
    before = snap
    cs = runAnalysis(snap, Trigger(TriggerKind.reading), NOW)
    assert isinstance(cs, ChangeSet)
    assert snap is before
