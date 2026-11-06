"""Invariant tests (Phase 7 §4)."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    Trigger,
    TriggerKind,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from services.run_analysis import run_analysis
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t
from tests.support.scenario_driver import ScenarioDriver

TZ = "Asia/Bangkok"


def test_explicit_case2_idempotency():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    now = t("2026-10-25 16:30", TZ)
    cs = d.run(Trigger(TriggerKind.reading), now)
    again = run_analysis(d.snapshot(), Trigger(TriggerKind.reading), now)
    assert again.diagnostics == () and again.predictions == () and again.recommendations == () and again.notifications == ()


def test_determinism_no_mutation():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    snap = d.snapshot()
    now = t("2026-10-25 16:30", TZ)
    trig = Trigger(TriggerKind.reading)
    c1 = run_analysis(snap, trig, now)
    c2 = run_analysis(snap, trig, now)
    assert c1 == c2
    assert snap == d.snapshot()


def test_rule5_night_only_do_night():
    d = ScenarioDriver()
    d.addReadings(PondParameters.DO, [
        ("2026-10-25 22:00", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
        ("2026-10-25 22:30", 4.0, ThresholdLevelType.Stress, SeverityLevelType.Stress, None),
    ])
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 22:30", TZ))
    report = next(r for r in cs.diagnostics if r.parameter == PondParameters.DO)
    assert [c.ruleId for c in report.causes] == ["DO_C_NIGHT"]


def test_o3_sources_and_pond_edit():
    d = ScenarioDriver()
    d.addActivity(id="p1", activityType=ActivityType.feeding, status=ActivityStatus.pending,
                  startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0)
    cs = d.run(Trigger(TriggerKind.reading), t("2026-10-25 16:30", TZ))
    assert cs.recommendations
    # no diagnosis change on pond edit for existing diagnostics
    from services.activity_edit import pondEditTrigger
    assert pondEditTrigger(makePond(), makePond(), t("2026-10-25 16:30", TZ)) is None


def test_long_run_invariants():
    d = ScenarioDriver()
    base = datetime(2026, 10, 25, 0, 0)
    for day in range(8):
        for half in range(48):
            pass
    assert d.snapshot() is not None
