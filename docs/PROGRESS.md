# PROGRESS

| Phase | Status | Tests | Notes |
|---|---|---|---|
| Phase 0 | Done | 33 passed | Severity engine baseline + Bug 1 fix (severityStatus) |
| Phase 1 | Done | 84 passed | Aligned to spec: config (49), severity_view (12), helpers (13), changeset (7), store_sim (3) |
| Fix Phase 0-1 | Done | 117 total | Resolved blocker F-01, aligned code to spec, added dailyMealPct and viewsFor with tests |
| Phase 2 | Done | 33 added; 152 passed | Diagnostic episodes, eight cause rules, runner, signals, stale gate, idempotency; pytest.ini added for pytest launcher imports |
| Phase 3 | Done | 8 added; 160 passed | PH_SWING detector, local complete days, coverage and DST-aware expected reading count; review test gaps closed |
| Phase 4 | Done | 23 added; 185 passed | Prediction: 3 rules (DO_NIGHT, DO_REPEAT, NH3_RISE), lifecycle runner, predictionSignals, totalMealPct helper |
| Phase 5 | Done | 29 added; 214 passed | Recommendation: catalog (AERATE/WATER_CHANGE/ADD_ALKALINITY), reconcile+blocked, buildApplyPlan (D15/D17), snooze/dismiss |

## Decisions made by agent & owner
- **F-01 Approved:** Added `value: float | None = None` to `AnalysisReportModel` and passed `self.valueNow` from `ParameterModel.buildAnalysisReport()`. Removed unneeded `description` and `guidance` properties from `AnalysisReportModel`.
- **Engine names (R2):** Retained existing engine names with typos (`tem`, `NO2_N`, `"hight risk"`, `HightRiskCountMinute`, `needRocoveryEleveted`, `NO2_2Threshold`) without changing engine files.
- **Activity & Helpers:** `Activity` strictly matches spec `(id, pondId, type, status, startTime, endTime, quantityKg, fraction, source, sourceRecId, createdAt, updatedAt)` with `__post_init__` validation. Added `dailyMealPct` (done feedings only, local date window via `localDate`, skip feeding if quantityKg is None).
- **Severity Views:** `viewsFor(views, parameter)` filters views per parameter while preserving chronological order.
- **Deterministic IDs:** Switched from sha256 hex strings to spec-defined readable format (`diag:{pond}:{param}:{dir|-}:{onset}`, `pred:...`, `rec:...`, `act:...`).
- **Tests split:** Replaced `test_analysis_core.py` with 5 targeted files (`test_config.py`, `test_severity_view.py`, `test_helpers.py`, `test_changeset.py`, `test_store_sim.py`).

## Open questions
- None. Phase 0 and Phase 1 are verified, aligned with spec, and clean. Ready for Phase 2 (Diagnostic).
