"""Phase 2 diagnostic runner tests."""
from datetime import datetime, timedelta
from dataclasses import replace

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    Cause,
    DiagStatus,
    PondSnapshot,
    Trigger,
    TriggerKind,
)
from identity.diagnostic.runner import diagnosticSignals, runDiagnostic
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.diag_builders import makeDiagnosticReport
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t
from tests.support.store_sim import StoreSim


TZ = "Asia/Bangkok"


def test_new_qualifying_episode_report_fields_and_deterministic_id():
    views = (
        makeView(PondParameters.DO, t("2026-10-25 19:00", TZ), value=4.0, zone=ThresholdLevelType.Stress),
        makeView(PondParameters.DO, t("2026-10-25 19:30", TZ), value=3.5, zone=ThresholdLevelType.Stress),
    )
    snap = makeSnapshot(pond=makePond(), severityReports=views)
    result = runDiagnostic(snap, Trigger(TriggerKind.reading), t("2026-10-25 19:30", TZ))
    assert len(result.diagnostics) == 1
    report = result.diagnostics[0]
    assert report.id.startswith("diag:pond_1:DO:-:")
    assert report.status == DiagStatus.open
    assert report.peakSeverity == SeverityLevelType.Optimal  # supplied test views default severity
    assert report.revisedAt is None


def test_report_waits_for_qualifying_stress_episode():
    v1 = makeView(PondParameters.DO, t("2026-10-25 19:00", TZ), zone=ThresholdLevelType.Stress)
    snap1 = makeSnapshot(pond=makePond(), severityReports=(v1,))
    assert runDiagnostic(snap1, Trigger(TriggerKind.reading), v1.time).diagnostics == ()
    v2 = makeView(PondParameters.DO, t("2026-10-25 19:30", TZ), zone=ThresholdLevelType.Stress)
    snap2 = makeSnapshot(pond=makePond(), severityReports=(v1, v2))
    assert len(runDiagnostic(snap2, Trigger(TriggerKind.reading), v2.time).diagnostics) == 1


def test_open_to_closed_updates_without_reading_trigger_cause_revision():
    onset, close = t("2026-10-25 19:00", TZ), t("2026-10-25 19:30", TZ)
    stress1 = makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress)
    stress2 = makeView(PondParameters.DO, t("2026-10-25 19:15", TZ), zone=ThresholdLevelType.Stress)
    report = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + onset.isoformat(), onsetAt=onset,
        causes=(Cause("old", {}),), noClearCause=False,
    )
    optimal = makeView(PondParameters.DO, close, zone=ThresholdLevelType.Optimal)
    snap = makeSnapshot(pond=makePond(), severityReports=(stress1, stress2, optimal))
    snap = replace(snap, diagnostics=(report,))

    result = runDiagnostic(snap, Trigger(TriggerKind.reading), close)
    updated = result.diagnostics[0]
    assert updated.endAt == close
    assert updated.status == DiagStatus.closed
    assert updated.causes == report.causes
    assert updated.revisedAt == report.revisedAt


def test_activity_event_revises_existing_causes_using_stored_pond_snapshot():
    onset = t("2026-10-25 20:00", TZ)
    views = (
        makeView(PondParameters.DO, t("2026-10-25 19:30", TZ), zone=ThresholdLevelType.Stress),
        makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress),
    )
    storedPond = makePond(biomassKg=800.0)
    existing = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + views[0].time.isoformat(),
        onsetAt=views[0].time,
        pond=storedPond,
        causes=(Cause("DO_C_NIGHT", {"old": True}),),
        noClearCause=False,
    )
    feed = makeActivity("f", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    snap = replace(makeSnapshot(pond=makePond(biomassKg=100), severityReports=views, activities=(feed,)), diagnostics=(existing,))
    now = t("2026-10-25 20:45", TZ)
    result = runDiagnostic(snap, Trigger(TriggerKind.activityEvent, tFrom=feed.startTime), now)
    changed = next(r for r in result.diagnostics if r.id == existing.id)
    assert changed.revisedAt == now
    feedCause = next(c for c in changed.causes if c.ruleId == "DO_C_FEED")
    assert feedCause.facts["mealPct"] == 0.75


def test_earlier_onset_and_non_activity_triggers_do_not_recompute_causes():
    onset = t("2026-10-25 19:00", TZ)
    views = (
        makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, t("2026-10-25 19:30", TZ), zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
    )
    existing = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + onset.isoformat(), onsetAt=onset,
        causes=(Cause("old", {}),), noClearCause=False,
    )
    laterChange = Trigger(TriggerKind.activityEvent, tFrom=onset + timedelta(minutes=1))
    snap = replace(makeSnapshot(pond=makePond(), severityReports=views), diagnostics=(existing,))
    assert runDiagnostic(snap, laterChange, onset + timedelta(minutes=45)).diagnostics == ()
    for kind in (TriggerKind.reading, TriggerKind.tick, TriggerKind.pondEdit):
        assert runDiagnostic(snap, Trigger(kind, tFrom=onset - timedelta(minutes=1)), onset + timedelta(minutes=45)).diagnostics == ()


def test_stale_gate_blocks_new_reports_but_processes_other_parameter():
    now = t("2026-10-25 20:00", TZ)
    oldDo = makeView(PondParameters.DO, now - timedelta(minutes=91), zone=ThresholdLevelType.Stress)
    do2 = makeView(PondParameters.DO, now - timedelta(minutes=120), zone=ThresholdLevelType.Stress)
    ph1 = makeView(PondParameters.pH, now - timedelta(minutes=20), zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low)
    ph2 = makeView(PondParameters.pH, now - timedelta(minutes=10), zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low)
    snap = makeSnapshot(pond=makePond(), severityReports=(do2, oldDo, ph1, ph2))
    reports = runDiagnostic(snap, Trigger(TriggerKind.reading), now).diagnostics
    assert all(r.parameter != PondParameters.DO for r in reports)
    assert any(r.parameter == PondParameters.pH for r in reports)


def test_direction_specific_ids_all_diagnostics_and_nonqualifying_episodes():
    now = t("2026-10-25 20:00", TZ)
    views = (
        makeView(PondParameters.pH, now, zone=ThresholdLevelType.HighRisk, direction=ThresholdDirection.High, severity=SeverityLevelType.ElevatedRisk),
        makeView(PondParameters.pH, now + timedelta(minutes=1), zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low, severity=SeverityLevelType.Stress),
        makeView(PondParameters.pH, now + timedelta(minutes=2), zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, now, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
    )
    snap = makeSnapshot(pond=makePond(), severityReports=views)
    result = runDiagnostic(snap, Trigger(TriggerKind.reading), now)
    assert len(result.episodes) == 3
    phIds = [r.id for r in result.allDiagnostics if r.parameter == PondParameters.pH]
    assert len(phIds) == 2 and phIds[0] != phIds[1]
    assert any(ep.parameter == PondParameters.DO and not (ep.readingCount >= DEFAULT_CONFIG.minEpisodeReadings or ep.peakZone == ThresholdLevelType.HighRisk) for ep in result.episodes)


def test_diagnostic_signals_contract():
    openReport = makeDiagnosticReport()
    closedReport = replace(openReport, status=DiagStatus.closed)
    signals = diagnosticSignals((openReport, closedReport))
    assert len(signals) == 2
    assert signals[0].active is True
    assert signals[1].active is False
    assert signals[0].sourceId == openReport.id
    assert signals[0].code == "DIAG_EPISODE"
    assert signals[0].facts == {"direction": openReport.direction, "onsetAt": openReport.onsetAt}


def test_runner_does_not_mutate_snapshot_and_store_sim_is_idempotent():
    now = t("2026-10-25 20:00", TZ)
    views = (
        makeView(PondParameters.DO, now - timedelta(minutes=30), zone=ThresholdLevelType.Stress),
        makeView(PondParameters.DO, now, zone=ThresholdLevelType.Stress),
    )
    snapshot = makeSnapshot(pond=makePond(), severityReports=views)
    original = snapshot
    sim = StoreSim(snapshot)
    first = runDiagnostic(snapshot, Trigger(TriggerKind.reading), now)
    assert snapshot is original
    sim.apply(ChangeSet(diagnostics=first.diagnostics))
    second = runDiagnostic(sim.snapshot(), Trigger(TriggerKind.reading), now)
    assert second.diagnostics == ()


def test_activity_trigger_revisions_are_idempotent_after_store_apply():
    onset = t("2026-10-25 20:00", TZ)
    views = (
        makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, onset + timedelta(minutes=30), zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
    )
    oldReport = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + onset.isoformat(), onsetAt=onset,
        causes=(Cause("DO_C_NIGHT", {}),), noClearCause=False,
    )
    feed = makeActivity("f", activityType=ActivityType.feeding, status=ActivityStatus.done,
                        startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    snap = replace(makeSnapshot(pond=makePond(), severityReports=views, activities=(feed,)), diagnostics=(oldReport,))
    trigger = Trigger(TriggerKind.activityEvent, tFrom=feed.startTime)
    now = onset + timedelta(minutes=45)

    sim = StoreSim(snap)
    first = runDiagnostic(snap, trigger, now)
    assert [c.ruleId for c in first.diagnostics[0].causes] == ["DO_C_FEED", "DO_C_NIGHT"]
    sim.apply(ChangeSet(diagnostics=first.diagnostics))
    second = runDiagnostic(sim.snapshot(), trigger, now)
    assert second.diagnostics == ()


def test_activity_deletion_reverts_causes_to_positive_evidence_remaining():
    onset = t("2026-10-25 20:00", TZ)
    views = (
        makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, onset + timedelta(minutes=30), zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
    )
    feedTime = t("2026-10-25 18:30", TZ)
    oldReport = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + onset.isoformat(), onsetAt=onset,
        causes=(Cause("DO_C_FEED", {}), Cause("DO_C_NIGHT", {})), noClearCause=False,
    )
    # Feed was deleted before recomputation: missing activity is unknown, not a negative fact.
    snap = replace(makeSnapshot(pond=makePond(), severityReports=views, activities=()), diagnostics=(oldReport,))
    now = onset + timedelta(minutes=45)
    result = runDiagnostic(snap, Trigger(TriggerKind.activityEvent, tFrom=feedTime), now)
    updated = result.diagnostics[0]
    assert [c.ruleId for c in updated.causes] == ["DO_C_NIGHT"]
    assert updated.revisedAt == now
    assert updated.noClearCause is False
    assert oldReport.causes == (Cause("DO_C_FEED", {}), Cause("DO_C_NIGHT", {}))



def test_stale_existing_report_still_updates_episode_facts():
    now = t("2026-10-25 20:00", TZ)
    onset = now - timedelta(minutes=120)
    views = (
        makeView(PondParameters.DO, onset, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, now - timedelta(minutes=91), zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress),
        makeView(PondParameters.DO, now - timedelta(minutes=90), zone=ThresholdLevelType.Optimal, severity=SeverityLevelType.Optimal),
    )
    existing = makeDiagnosticReport(
        reportId="diag:pond_1:DO:-:" + onset.isoformat(), onsetAt=onset,
        causes=(Cause("DO_C_NIGHT", {}),), noClearCause=False,
    )
    snap = replace(makeSnapshot(pond=makePond(), severityReports=views), diagnostics=(existing,))
    result = runDiagnostic(snap, Trigger(TriggerKind.reading), now)
    assert result.allDiagnostics[0].status == DiagStatus.closed
    assert result.allDiagnostics[0].endAt == now - timedelta(minutes=90)
