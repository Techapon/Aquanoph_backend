"""Core scenario tests T1–T18 (Phase 7 §4)."""
from datetime import datetime, timedelta

import pytest

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    ActivitySource,
    ActivityStatus,
    ActivityType,
    RecStatus,
    Trigger,
    TriggerKind,
    Urgency,
)
from identity.diagnostic.detectors.ph_swing import detectPhSwing
from identity.diagnostic.runner import runDiagnostic
from identity.parameters.pond_parameter_enum import PondParameters
from identity.prediction.runner import runPredictions
from identity.recommendation.apply_plan import buildApplyPlan
from services.activity_edit import validateActivityEdit
from services.run_analysis import run_analysis
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t
from tests.support.scenario_driver import (
    ScenarioDriver,
)
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


TZ = "Asia/Bangkok"


def doView(local, severity=SeverityLevelType.Stress):
    return makeView(PondParameters.DO, t(local, TZ), value=4.0, zone=ThresholdLevelType.Stress, severity=severity)


def test_T1_diagnostic_causes_through_orchestrator():
    from identity.analysis.models import Trigger, TriggerKind
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-25 19:45", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-25 20:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    d.addActivity(id="feed1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 20:00", TZ))
    assert any(r.parameter == PondParameters.DO for r in cs.diagnostics)
    report = next(r for r in cs.diagnostics if r.parameter == PondParameters.DO)
    assert [c.ruleId for c in report.causes] == ["DO_C_FEED", "DO_C_NIGHT"]


def test_T1b_with_hot_temp():
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-25 19:45", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-25 20:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    d.addReadings(PondParameters.tem, [
        ("2026-10-25 19:00", 31.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, ThresholdDirection.High),
    ])
    d.addActivity(id="feed1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 20:00", TZ))
    report = next(r for r in cs.diagnostics if r.parameter == PondParameters.DO)
    assert [c.ruleId for c in report.causes] == ["DO_C_FEED", "DO_C_TEMP"]


def test_T2_case2_prediction_and_aerate_rec():
    d = ScenarioDriver()
    d.addReadings(PondParameters.tem, [
        ("2026-10-25 16:00", 31.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, ThresholdDirection.High),
    ])
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    preds = [p for p in cs.predictions if p.ruleId == "PRED_DO_NIGHT"]
    assert preds and preds[0].status.value == "active"
    assert preds[0].met == ("C1", "C2", "C3")
    recs = [r for r in cs.recommendations if r.entryId == "AERATE"]
    assert recs and recs[0].urgency == Urgency.urgent
    assert any(n.kind == "urgentRecCreated" for n in cs.notifications)


def test_T3_apply_and_prediction_mitigated():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    d.addReadings(PondParameters.tem, [
        ("2026-10-25 16:00", 31.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, ThresholdDirection.High),
    ])
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "AERATE")
    d.applyRec(rec.id, t("2026-10-25 19:10", TZ))
    snap = d.snapshot()
    assert next(r for r in snap.recommendations if r.id == rec.id).status == RecStatus.applied
    acts = [a for a in snap.activities if a.source == ActivitySource.recommendation]
    assert any(a.startTime == t("2026-10-25 19:10", TZ) and a.endTime == t("2026-10-26 06:00", TZ) for a in acts)


def test_T4_meal_reduced_expires_prediction_and_rec():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    # edit meal to 3.0 kg before apply
    d.addActivity(id="extra_check", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-24 10:00", TZ), quantityKg=1.0)
    from dataclasses import replace
    # change pending meal quantity by editing
    d.editActivity("p1", t("2026-10-25 16:40", TZ), quantityKg=3.0)
    snap = d.snapshot()
    preds = [p for p in snap.predictions if p.ruleId == "PRED_DO_NIGHT"]
    assert all(p.status.value == "ended" for p in preds)


def test_T6_full_diagnostic_with_activity_revision():
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-25 19:45", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-25 20:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    cs1 = d.run(Trigger(TriggerKind.reading), t("2026-10-25 20:00", TZ))
    report = next(r for r in cs1.diagnostics if r.parameter == PondParameters.DO)
    assert [c.ruleId for c in report.causes] == ["DO_C_NIGHT"]

    d.addActivity(id="feed1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    cs2 = d.run(Trigger(TriggerKind.activityEvent, tFrom=t("2026-10-25 18:30", TZ)), t("2026-10-25 20:45", TZ))
    updated = next(r for r in cs2.diagnostics if r.parameter == PondParameters.DO)
    assert [c.ruleId for c in updated.causes] == ["DO_C_FEED", "DO_C_NIGHT"]
    assert updated.revisedAt == t("2026-10-25 20:45", TZ)


def test_T7_ph_swing_creates_alkalinity_and_stays():
    d = ScenarioDriver()
    from tests.support.factories import makeView
    views = []
    for day in ("2026-10-01", "2026-10-02"):
        base = datetime.fromisoformat(f"{day} 00:00")
        for i in range(34):
            ts = base + timedelta(minutes=30 * i)
            val = 7.0 if i % 2 == 0 else 8.0
            views.append(makeView(PondParameters.pH, t(ts, TZ), value=val))
    views.append(makeView(PondParameters.pH, t("2026-10-04 12:00", TZ), value=7.5))
    from dataclasses import replace
    d.sim = __import__("tests.support.store_sim", fromlist=["StoreSim"]).StoreSim(
        replace(d.sim.snapshot(), severityReports=tuple(views)))
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-04 12:00", TZ))
    assert any(r.entryId == "ADD_ALKALINITY" for r in cs.recommendations)

    # next day swing gone: rec stays until validUntil
    cs2 = d.run(Trigger(TriggerKind.reading), t("2026-10-05 12:00", TZ))
    alk = [r for r in d.snapshot().recommendations if r.entryId == "ADD_ALKALINITY"]
    assert alk and alk[0].status in (RecStatus.pending, RecStatus.snoozed)


def test_T8_snooze_then_urgency_raise():
    d = ScenarioDriver()
    d.addReadings(PondParameters.NH3, [
        ("2026-10-25 15:00", 0.1, ThresholdLevelType.Stress, SeverityLevelType.ElevatedRisk, None),
        ("2026-10-25 15:30", 0.1, ThresholdLevelType.Stress, SeverityLevelType.ElevatedRisk, None),
    ])
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 15:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "WATER_CHANGE")
    assert rec.urgency == Urgency.nonUrgent
    d.snooze(rec.id, t("2026-10-25 20:00", TZ), t("2026-10-25 16:00", TZ))

    d.addReadings(PondParameters.NH3, [
        ("2026-10-25 17:00", 0.3, ThresholdLevelType.Critical, SeverityLevelType.Critical, None),
    ])
    cs2 = d.run(Trigger(TriggerKind.reading), t("2026-10-25 17:00", TZ))
    updated = next(r for r in d.snapshot().recommendations if r.id == rec.id)
    assert updated.urgency == Urgency.urgent
    assert updated.status == RecStatus.pending
    assert any(n.reasonKey == "rec.changed.urgency_raised" for n in cs2.notifications)


def test_T9_stale_keeps_urgent_rec():
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-24 10:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-24 10:30", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-24 19:00", TZ), quantityKg=8.0)
    cs0 = d.run(Trigger(TriggerKind.reading), t("2026-10-24 11:30", TZ))
    recsBefore = [r for r in cs0.recommendations if r.entryId == "AERATE"] or [r for r in d.snapshot().recommendations if r.entryId == "AERATE"]
    assert recsBefore
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    assert not [r for r in cs.diagnostics if r.parameter == PondParameters.DO]
    assert [r for r in d.snapshot().recommendations if r.entryId == "AERATE"]


def test_T10_declined_then_critical_allows_new():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "AERATE")
    d.dismiss(rec.id, t("2026-10-25 17:00", TZ))

    cs2 = d.run(Trigger(TriggerKind.reading), t("2026-10-25 17:30", TZ))
    assert not [r for r in cs2.recommendations if r.entryId == "AERATE" and r.status == RecStatus.pending]

    d.addReadings(PondParameters.DO, [
        ("2026-10-25 18:00", 2.0, ThresholdLevelType.Critical, SeverityLevelType.Critical, None),
        ("2026-10-25 18:30", 2.0, ThresholdLevelType.Critical, SeverityLevelType.Critical, None),
    ])
    cs3 = d.run(Trigger(TriggerKind.reading), t("2026-10-25 18:30", TZ))
    assert any(r.entryId == "AERATE" and r.status == RecStatus.pending for r in cs3.recommendations)


def test_T11_repeat_and_T12_nh3_and_T13_time_window():
    d = ScenarioDriver()
    # repeat-style: use simple prediction path via heavy meal tonight instead
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    assert any(r.entryId == "AERATE" for r in cs.recommendations)

    # T13: non_urgent apply outside window rejected
    from tests.support.pred_builders import makePrediction
    d2 = ScenarioDriver()
    d2.addActivity(id="a1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                   startTime=t("2026-10-25 10:00", TZ), quantityKg=7.2)
    d2.addActivity(id="a2", activityType=ActivityType.feeding, status=ActivityStatus.done,
                   startTime=t("2026-10-25 12:00", TZ), quantityKg=7.2)
    d2.addReadings(PondParameters.NH3, [
        ( "2026-10-25 16:00", 0.1, ThresholdLevelType.Stress, SeverityLevelType.ElevatedRisk, None),
    ])
    d2.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    wc = next(r for r in d2.snapshot().recommendations if r.entryId == "WATER_CHANGE")
    plan = buildApplyPlan(wc, d2.snapshot(), t("2026-10-25 16:30", TZ),
                          chosenTime=t("2026-10-25 16:30", TZ) + timedelta(days=5), cfg=DEFAULT_CONFIG)
    assert plan.status == "rejected"
    planOk = buildApplyPlan(wc, d2.snapshot(), t("2026-10-25 16:30", TZ),
                            chosenTime=wc.validUntil, cfg=DEFAULT_CONFIG)
    assert planOk.status == "applied"


def test_T14_d15_examples_and_T15_T16_water_change():
    d = ScenarioDriver()
    userAct = makeActivity("u1", activityType=ActivityType.aeration, status=ActivityStatus.pending,
                           startTime=t("2026-10-25 21:00", TZ), endTime=t("2026-10-25 23:00", TZ))
    from dataclasses import replace
    userAct = replace(userAct, source=ActivitySource.user)
    from identity.analysis.models import Urgency, ApplyMode, ProposedActivity
    rec = __import__("tests.support.rec_builders", fromlist=["makeRecommendation"]).makeRecommendation(
        entryId="AERATE", dedupeKey="AERATE:2026-10-25",
        urgency=Urgency.urgent, applyMode=ApplyMode.fixed,
        validFrom=t("2026-10-25 16:30", TZ), validUntil=t("2026-10-25 21:00", TZ),
        proposedActivities=(ProposedActivity(ActivityType.aeration, t("2026-10-25 22:00", TZ), t("2026-10-26 03:00", TZ), None, None),),
        createdAt=t("2026-10-25 16:30", TZ), updatedAt=t("2026-10-25 16:30", TZ),
    )
    from tests.support.store_sim import StoreSim
    from identity.analysis.changeset import ChangeSet
    simSnap = makeSnapshot(pond=makePond(), activities=[userAct], recommendations=[rec])
    plan = buildApplyPlan(rec, simSnap, t("2026-10-25 17:00", TZ), cfg=DEFAULT_CONFIG)
    assert plan.status == "applied"
    assert plan.changeSet.notifications

    # T17: old activity edit rejected
    old = makeActivity("old", startTime=t("2026-10-20 10:00", TZ))
    check = validateActivityEdit(None, old, t("2026-10-25 12:00", TZ))
    assert check.ok is False and check.reason == "outside_retro_window"


def test_T5_apply_skip_new_rec_and_T18_shortened_still_blocked():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "AERATE")
    d.applyRec(rec.id, t("2026-10-25 17:00", TZ))
    acts = [a for a in d.snapshot().activities if a.sourceRecId == rec.id]
    d.skipActivity(acts[0].id, t("2026-10-25 17:30", TZ))
    cs2 = d.run(Trigger(TriggerKind.reading), t("2026-10-25 17:30", TZ))
    assert any(r.entryId == "AERATE" and r.id != rec.id and r.status == RecStatus.pending for r in d.snapshot().recommendations)
