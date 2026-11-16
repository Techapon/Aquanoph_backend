# CODE FINDINGS

Tracking technical findings, discrepancies, typos, and architecture blockers discovered during code reviews and phase verification.

## Resolved Blockers
- **F-01: `AnalysisReportModel` drops measured sensor reading (`valueNow`)**
  - **Location:** `identity/formats/analysis_report/analysis_report_model.py:10-35`, `identity/parameters/parameter_model.py:51-59`
  - **Resolution:** Approved and resolved in FIX Phase 0-1 (Task 1). Added `value: float | None = None` to `AnalysisReportModel` and passed `self.valueNow` from `ParameterModel.buildAnalysisReport()`. `toView` enforces `value is not None` with `ValueError`.
  - **Phase 0 Question f Answer:** The report now reliably stores the measured numerical value.

- **F-00: `severityStatus` missing on `AnalysisReportModel` / `SeverityModel` (Bug 1)**
  - **Location:** `identity/formats/analysis_report/analysis_report_model.py`, `identity/units/severity_units/severity/severity_model.py`
  - **Fixed in:** Phase 0. Added property alias delegating to `severity.severityLevel`. Extra unneeded properties `description` and `guidance` removed in FIX Phase 0-1.

## Enum & Naming Discrepancies (Rule R2 - Keep Real Engine Names)
- **F-02: `ThresholdLevelType.HighRisk` string value contains typo**
  - **Location:** `identity/units/threshold_units/threshold_level/threshold_level.py:6`
  - **Detail:** `HighRisk = "hight risk"` (extra 't').
  - **Fix/Rule (R2):** Keep `"hight risk"` to prevent breaking existing tests and serialization.
- **F-03: Parameter identifier for Temperature is `tem`**
  - **Location:** `identity/parameters/pond_parameter_enum.py:6`
  - **Detail:** Spec uses `temperature`/`Temperature`, real code uses `tem` with label `"Temperature"`.
  - **Fix/Rule (R2):** Standardize on `PondParameters.tem`.
- **F-04: Parameter identifier for NO2 is `NO2_N` with label `NO2-_N`**
  - **Location:** `identity/parameters/pond_parameter_enum.py:8`
  - **Fix/Rule (R2):** Standardize on `PondParameters.NO2_N`.
- **F-05: `HightRiskCountMinute` in EscalationPolicy**
  - **Location:** `identity/units/severity_units/severity_elavuator/severity_escalation_policy.py:8`
  - **Detail:** Field spelled with 't' (`HightRiskCountMinute`).
  - **Fix/Rule (R2):** Keep real engine attribute name in severity policy.
- **F-06: `needRocoveryEleveted` in SeverityDesSetModel**
  - **Location:** `identity/units/severity_units/severity_description/severity_des_set_model.py:11`
  - **Detail:** Typo in field name (`needRocoveryEleveted`).
  - **Fix/Rule (R2):** Keep real engine attribute name in severity description sets.
- **F-07: `NO2_2Threshold` in AquaticAnimal ABC**
  - **Location:** `identity/animals/animal_model.py:46`
  - **Detail:** Spelled `NO2_2Threshold` instead of `NO2_N_Threshold`.
  - **Fix/Rule (R2):** Keep real engine method name in ABC and concrete classes.

## Phase 2 Review Fixes
- **F-08: NO2/NH3 first and last evidence time depended on input order**
  - **Location:** `identity/diagnostic/cause_rules.py`
  - **Resolution:** Sorted abnormal NH3 views chronologically before deriving `nh3FirstTime` and `nh3LastTime`. Added an unsorted-input regression assertion in `tests/test_cause_rules.py`.
- **F-09: Missing regression coverage for activity-trigger idempotency and activity-deletion revision**
  - **Location:** `tests/test_diagnostic_runner.py`
  - **Resolution:** Added tests for StoreSim-applied activity revisions followed by identical rerun, and deleted feeding recomputation retaining only positive evidence.

## Phase 2 Test Infrastructure
- **F-10: `pytest -q` did not add repository root to Python import path**
  - **Resolution:** Added root `pytest.ini` with `pythonpath = .`. `pytest -q` now completes successfully from repository root.
