"""Prediction runner tests (Phase 4 §6)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import ActivityStatus, ActivityType, PredStatus, Trigger, TriggerKind
from identity.diagnostic.episode import buildEpisodes
from identity.diagnostic.runner import runDiagnostic
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.runner import predictionSignals, runPredictions
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t
from tests.support.pred_builders import makePrediction
from tests.support.store_sim import StoreSim
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType


TZ = "Asia/Bangkok"


def feedAt(when: str, kg: float):
    return makeActivity("f", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t(when, TZ), quantityKg=kg)


def test_window_over_ends_and_never_reopens():
    now = t("2026-10-26 07:00", TZ)
    pred = makePrediction(riskEnd=t("2026-10-26 06:00", TZ))
    snap = makeSnapshot(pond=makePond(), predictions=[pred])
    out = runPredictions(snap, now)
    assert len(out) == 1
    assert out[0].status == PredStatus.ended
    assert out[0].endReason == "window_over"

    snap2 = makeSnapshot(pond=makePond(), predictions=list(out))
    assert runPredictions(snap2, now + timedelta(minutes=30)) == ()


def test_scope_change_ends_old_and_creates_new():
    now = t("2026-10-25 16:30", TZ)
    old = makePrediction(scope="2026-10-24")
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    snap = makeSnapshot(pond=makePond(), activities=[pending], predictions=[old])
    out = runPredictions(snap, now)
    assert any(p.status == PredStatus.ended and p.id == old.id for p in out)
    assert any(p.status == PredStatus.active and p.scope == "2026-10-25" for p in out)


def test_store_sim_idempotency_and_next_tick_nh3_only():
    now = t("2026-10-25 16:30", TZ)
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    heavy = [
        makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=now - timedelta(hours=2), quantityKg=7.2),
        makeActivity("b", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=now - timedelta(hours=4), quantityKg=7.2),
    ]
    nh3 = makeView(PondParameters.NH3, now, value=0.1, zone=ThresholdLevelType.Stress)
    snap = makeSnapshot(pond=makePond(), severityReports=[nh3], activities=[pending, *heavy])
    sim = StoreSim(snap)

    first = runPredictions(snap, now)
    assert first
    sim.apply(ChangeSet(predictions=first))
    assert runPredictions(sim.snapshot(), now) == ()

    later = now + timedelta(minutes=30)
    moved = runPredictions(sim.snapshot(), later)
    assert all(p.ruleId == "PRED_NH3_RISE" for p in moved)


def test_rules_independent_and_episode_equivalence_and_signals():
    now = t("2026-10-25 16:30", TZ)
    doView = makeView(PondParameters.DO, now, value=4.0, zone=ThresholdLevelType.Stress)
    snap = makeSnapshot(pond=makePond(), severityReports=[doView])
    explicit = buildEpisodes(snap.severityReports, PondParameters.DO)
    assert runPredictions(snap, now, doEpisodes=explicit) == runPredictions(snap, now, doEpisodes=None)

    active = makePrediction()
    ended = makePrediction(predId="pred:pond_1:RULE:old", status=PredStatus.ended, endReason="window_over")
    signals = predictionSignals([active, ended])
    assert signals[0].active is True
    assert signals[1].active is False
    assert signals[0].sourceId == active.id
    assert signals[0].code == active.ruleId


def test_snapshot_immutable_output_order_and_same_scope_update():
    now = t("2026-10-25 16:30", TZ)
    pending = makeActivity("p", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    heavy = [
        makeActivity("a", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=now - timedelta(hours=1), quantityKg=7.2),
        makeActivity("b", activityType=ActivityType.feeding, status=ActivityStatus.done,
                     startTime=now - timedelta(hours=2), quantityKg=7.2),
    ]
    nh3 = makeView(PondParameters.NH3, now, value=0.1, zone=ThresholdLevelType.Stress)
    snap = makeSnapshot(pond=makePond(), severityReports=[nh3], activities=[pending, *heavy])

    first = runPredictions(snap, now)
    assert [p.ruleId for p in first] == ["PRED_DO_NIGHT", "PRED_NH3_RISE"]
    assert snap.predictions == ()

    sim = StoreSim(snap)
    sim.apply(ChangeSet(predictions=first))
    stored = list(sim.snapshot().predictions)
    unchanged = runPredictions(sim.snapshot(), now)
    assert all(p.ruleId == "PRED_NH3_RISE" for p in unchanged)
