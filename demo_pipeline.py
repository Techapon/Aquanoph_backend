# -*- coding: utf-8 -*-
"""Simulate a DB snapshot -> run_analysis -> pretty print all 4 stages."""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.helpers import localTime
from identity.analysis.models import Activity, ActivitySource, ActivityStatus, ActivityType, PondInfo, PondSnapshot, Trigger, TriggerKind
from identity.analysis.severity_view import toViews, SeverityReportView
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from services.run_analysis import run_analysis
from identity.text.render import (
    renderDiagnostic, renderPrediction, renderRecommendation, renderPlan, renderNotification,
)
from tests.support.factories import makeView, t

TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)

# ---------- 1) Severity: simulate DB readings (AnalysisReportModel -> view) ----------
# Build a tiny temperature history + current DO readings via SeverityReportView (F-01 value present).
views = []
# temperature: hot in the afternoon (High risk)
for i in range(6):
    ts = t(f"2026-10-25 {14+i}:00", TZ)
    views.append(makeView(PondParameters.tem, ts, value=31.0 + i*0.1,
                         zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High,
                         severity=SeverityLevelType.Stress))
# DO: two stress readings to qualify an episode
views.append(makeView(PondParameters.DO, t("2026-10-25 19:45", TZ), value=4.2,
                     zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress))
views.append(makeView(PondParameters.DO, t("2026-10-25 20:00", TZ), value=4.0,
                     zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress))
# pending heavy feeding at 19:00 (for PRED_DO_NIGHT)
act = Activity(
    id="act:feed:1", pondId="pond_1", type=ActivityType.feeding, status=ActivityStatus.pending,
    startTime=t("2026-10-25 19:00", TZ), quantityKg=8.0, source=ActivitySource.user,
)
pond = PondInfo(pondId="pond_1", timezone=TZ, biomassKg=400.0)
snap = PondSnapshot(pond=pond, severityReports=tuple(views), activities=(act,))

print("=" * 70)
print("INPUT SNAPSHOT")
print("  pond:", pond.pondId, pond.timezone, "biomass", pond.biomassKg, "kg")
print("  severityReports:", len(views))
print("  activities:", len(snap.activities))
print()

# ---------- 2) Run pipeline ----------
cs = run_analysis(snap, Trigger(TriggerKind.reading), NOW, cfg=DEFAULT_CONFIG)
print("=" * 70)
print("CHANGESET")
print("  diagnostics:", len(cs.diagnostics))
print("  predictions:", len(cs.predictions))
print("  recommendations:", len(cs.recommendations))
print("  notifications:", len(cs.notifications))
print("  isEmpty:", cs.isEmpty())
print()

# ---------- Severity (current readings) ----------
print("=" * 70)
print("1) SEVERITY (current readings, via severity engine already stored)")
for v in views[-3:]:
    print(f"   {v.parameter.value}: value={v.value} zone={v.zone.value} severity={v.severity.value} @ {localTime(v.time, TZ)}")

# ---------- 2) Diagnostic ----------
print()
print("=" * 70)
print("2) DIAGNOSTIC")
for d in cs.diagnostics:
    print(f"   id={d.id}")
    print(f"   param={d.parameter.value} dir={d.direction} onset={localTime(d.onsetAt, TZ)} end={localTime(d.endAt, TZ) if d.endAt else 'OPEN'} status={d.status.value}")
    print(f"   peakSeverity={d.peakSeverity.value} lastSeverity={d.lastSeverity.value}")
    print(f"   causes={[c.ruleId for c in d.causes]}  noClearCause={d.noClearCause}")
    rd = renderDiagnostic(d, DEFAULT_CONFIG)
    print(f"   title: {rd.title}")
    for c in rd.causes:
        print(f"     - [{c.heading}] {c.body}")
    if rd.fallback:
        print(f"     fallback: {rd.fallback}")

# ---------- 3) Prediction ----------
print()
print("=" * 70)
print("3) PREDICTION")
for p in cs.predictions:
    print(f"   id={p.id}")
    print(f"   rule={p.ruleId} status={p.status.value} scope={p.scope}")
    print(f"   riskStart={localTime(p.riskStart, TZ)} riskEnd={localTime(p.riskEnd, TZ)} met={p.met}")
    rp = renderPrediction(p, DEFAULT_CONFIG)
    print(f"   headline: {rp.headline}")
    for label, met in rp.conditions:
        print(f"     - [{'x' if met else ' '}] {label}")

# ---------- 4) Recommendation ----------
print()
print("=" * 70)
print("4) RECOMMENDATION")
for r in cs.recommendations:
    print(f"   id={r.id}")
    print(f"   entry={r.entryId} urgency={r.urgency.value} status={r.status.value}")
    print(f"   validFrom={localTime(r.validFrom, TZ)} validUntil={localTime(r.validUntil, TZ)}")
    print(f"   applyMode={r.applyMode.value} sources={[s.sourceType.value+':'+s.sourceId for s in r.sources]}")
    rt = renderRecommendation(r, snap.pond, DEFAULT_CONFIG)
    print(f"   title: {rt.title}")
    print(f"   reason: {rt.reason}")
    print(f"   basedOn: {rt.basedOn}")
    print(f"   guidance: {list(rt.guidance)}")
    plan = renderPlan(r, snap.pond, DEFAULT_CONFIG)
    print(f"   plan: {plan}")

print()
print("=" * 70)
print("NOTIFICATIONS")
for n in cs.notifications:
    print(f"   [{n.kind}] {n.reasonKey} -> {renderNotification(n, TZ)}")
print()
print("DISCLAIMER:", "Automated estimate based on your logs and sensor data. Not a guarantee.")
