"""Scenario driver for Phase 7 end-to-end tests."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    Activity,
    ActivityStatus,
    ActivityType,
    PondInfo,
    PondSnapshot,
    Trigger,
    TriggerKind,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.recommendation.apply_plan import buildApplyPlan, dismissRec, snoozeRec
from identity.text.render import renderRecommendation
from services.activity_edit import pondEditTrigger, triggerForEdit, validateActivityEdit
from services.run_analysis import run_analysis
from tests.support.factories import makeActivity, makePond, makeSnapshot, makeView, t
from tests.support.store_sim import StoreSim
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection


class ScenarioDriver:
    """Drive StoreSim + run_analysis with idempotency checks."""

    def __init__(self, pond: PondInfo | None = None, tz: str = "Asia/Bangkok", activities=(), severityReports=()):
        self.tz = tz
        self.sim = StoreSim(makeSnapshot(pond=pond or makePond(timezone=tz), severityReports=severityReports, activities=activities))

    def snapshot(self) -> PondSnapshot:
        return self.sim.snapshot()

    def addReadings(self, parameter: PondParameters, rows: list[tuple[str, float, ThresholdLevelType, SeverityLevelType, ThresholdDirection | None]]):
        views = list(self.sim.snapshot().severityReports)
        for local, value, zone, severity, direction in rows:
            views.append(makeView(parameter, t(local, self.tz), value=value, zone=zone, severity=severity, direction=direction))  # type: ignore[arg-type]
        from dataclasses import replace
        self.sim = StoreSim(replace(self.sim.snapshot(), severityReports=tuple(views)))
        # rebuild sim internal state while preserving snapshot
        newSim = StoreSim(self.sim.snapshot())
        newSim.notifications = list(self.sim.notifications)
        self.sim = newSim

    def addActivity(self, **kw) -> Activity:
        if "id" in kw:
            kw = dict(kw)
            kw["activityId"] = kw.pop("id")
        act = makeActivity(**kw)
        from dataclasses import replace
        self.sim = StoreSim(replace(self.sim.snapshot(), activities=self.sim.snapshot().activities + (act,)))
        return act

    def editActivity(self, actId: str, now: datetime, **changes):
        from dataclasses import replace
        acts = list(self.sim.snapshot().activities)
        before = next(a for a in acts if a.id == actId)
        after = replace(before, **changes, updatedAt=now)
        check = validateActivityEdit(before, after, now)
        assert check.ok, check.reason
        acts = tuple(after if a.id == actId else a for a in acts)
        self.sim = StoreSim(replace(self.sim.snapshot(), activities=acts))
        return self.run(Trigger(TriggerKind.activityEvent, tFrom=min(before.startTime, after.startTime)), now)

    def deleteActivity(self, actId: str, now: datetime):
        from dataclasses import replace
        acts = list(self.sim.snapshot().activities)
        before = next(a for a in acts if a.id == actId)
        check = validateActivityEdit(before, None, now)
        assert check.ok, check.reason
        acts = tuple(a for a in acts if a.id != actId)
        self.sim = StoreSim(replace(self.sim.snapshot(), activities=acts))
        return self.run(Trigger(TriggerKind.activityEvent, tFrom=before.startTime), now)

    def run(self, trigger: Trigger, now: datetime) -> ChangeSet:
        snap = self.sim.snapshot()
        first = run_analysis(snap, trigger, now)
        beforeN = len(self.sim.notifications)
        self.sim.apply(first)
        again = run_analysis(self.sim.snapshot(), trigger, now)
        assert again.isEmpty() if hasattr(again, "isEmpty") else again.diagnostics == () and again.predictions == () and again.recommendations == () and again.notifications == (), f"not idempotent: {again}"
        return first

    def applyRec(self, recId: str, now: datetime, chosenTime=None, confirmed=False):
        from dataclasses import replace
        rec = next(r for r in self.sim.snapshot().recommendations if r.id == recId)
        result = buildApplyPlan(rec, self.sim.snapshot(), now, chosenTime=chosenTime, confirmed=confirmed)
        assert result.status == "applied", result.reason
        self.sim.apply(result.changeSet)
        # follow-up analysis on the created activity's start
        created = [op.activity for op in result.changeSet.activityOps if op.op == "create"]
        if created:
            return self.run(Trigger(TriggerKind.activityEvent, tFrom=created[0].startTime), now)
        return result.changeSet

    def skipActivity(self, actId: str, now: datetime):
        return self.editActivity(actId, now, status=ActivityStatus.skipped)

    def dismiss(self, recId: str, now: datetime):
        rec = next(r for r in self.sim.snapshot().recommendations if r.id == recId)
        self.sim.apply(dismissRec(rec, now))

    def snooze(self, recId: str, until: datetime, now: datetime):
        from identity.analysis.models import Urgency
        rec = next(r for r in self.sim.snapshot().recommendations if r.id == recId)
        self.sim.apply(snoozeRec(rec, until, now))
