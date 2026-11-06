"""Scenario text tests Cases 1-3 (Phase 7 §4)."""
from config.constants import DEFAULT_CONFIG
from identity.analysis.models import ActivityType, ActivityStatus, Trigger, TriggerKind
from identity.parameters.pond_parameter_enum import PondParameters
from identity.text.render import (
    renderDiagnostic,
    renderPlan,
    renderRecommendation,
)
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from tests.support.factories import t
from tests.support.scenario_driver import ScenarioDriver

TZ = "Asia/Bangkok"


def test_case1_golden_diagnostic_text():
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-25 19:45", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-25 20:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    d.addActivity(id="feed1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 18:30", TZ), quantityKg=6.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 20:00", TZ))
    report = next(r for r in cs.diagnostics if r.parameter == PondParameters.DO)
    rd = renderDiagnostic(report, DEFAULT_CONFIG)
    assert rd.title == "Why this may have happened"
    assert any(c.heading == "Feeding raised oxygen demand." for c in rd.causes)
    assert any("6.0 kg" in c.body for c in rd.causes)
    assert any("It is night." in c.heading for c in rd.causes)


def test_case2_golden_recommendation_text():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    d.addReadings(PondParameters.tem, [
        ("2026-10-25 16:00", 31.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, ThresholdDirection.High),
    ])
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "AERATE")
    # reconcile already rendered the text into the rec; verify stored fields instead
    assert rec.title == "Run aeration tonight: DO may drop too low"
    assert "You planned" in rec.reason
    assert "no aeration is planned overnight" in rec.reason
    assert "20:00" in rec.reason and "06:00" in rec.reason
    assert rec.guidance[0] == "Keep aeration running until about 06:00."
    plan = renderPlan(rec, d.snapshot().pond, DEFAULT_CONFIG)
    assert "19:00" in plan and "06:00" in plan


def test_case3_golden_water_change_text():
    d = ScenarioDriver()
    d.addActivity(id="a1", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 10:00", TZ), quantityKg=7.2)
    d.addActivity(id="a2", activityType=ActivityType.feeding, status=ActivityStatus.done,
                  startTime=t("2026-10-25 12:00", TZ), quantityKg=7.2)
    d.addReadings(PondParameters.NH3, [
        ("2026-10-25 16:00", 0.1, ThresholdLevelType.Stress, SeverityLevelType.ElevatedRisk, None),
    ])
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    rec = next(r for r in cs.recommendations if r.entryId == "WATER_CHANGE")
    assert rec.title.startswith("Plan a partial water change")
    assert "ammonia is already above the optimal range" in rec.reason
    plan = renderPlan(rec, d.snapshot().pond, DEFAULT_CONFIG)
    assert "1/4" in plan and "choose a time" in plan
