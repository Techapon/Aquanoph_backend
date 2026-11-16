# Verification Report: Phase 0 and Phase 1

**STATUS: BLOCKER**
(Blocker triggered by Check A2: `AnalysisReportModel` does NOT store the measured sensor reading value).

---

## A. BLOCKER CHECKS

| Check | Result | Evidence |
|---|---|---|
| **A1. Does an analysis report keep threshold ZONE separate from SEVERITY?** | **YES** | Real engine evaluation produces separate attributes. Zone is in `report.thresholdStatus` (`ThresholdLevelType.Optimal`), and Severity is in `report.severity.severityLevel` / `report.severityStatus` (`SeverityLevelType.Stress`). In Recovery Hold (`test_range_severity.py:152-158`), reading at T-30 has zone `optimal` while severity remains `stress`. |
| **A2. Does the report keep the measured VALUE? Give attribute name.** | **NO** | Attribute name: **None (MISSING)**. `identity/formats/analysis_report/analysis_report_model.py:9-35` defines `dateTime`, `parameter`, `thresholdStatus`, `thresholdDirection`, `severity`. In `identity/parameters/parameter_model.py:51-59`, `buildAnalysisReport()` passes `self.valueNow` to threshold check but drops it when instantiating `AnalysisReportModel`. |
| **A3. Do Range-threshold reports keep direction low/high? What does Level-threshold report carry?** | **YES** | Range thresholds (pH, Temperature) store `ThresholdDirection.Low` or `ThresholdDirection.High` when non-optimal, and `None` when optimal (`identity/units/threshold_units/threshold/threshold_model.py:110-132`). Level thresholds (DO, NH3, NO2_N, Salinity) carry `None` (`identity/units/threshold_units/threshold_level/threshold_level_model.py:13`, `tests/test_range_severity.py:101-103`). |
| **A4. Is every reading's zone in history in time order? Real type? Cases with no report?** | **YES** | Real type: `PondParametersHistoryModel` (`identity/parameters/pond_parameter_history_model.py:7-13`) holding `list[AnalysisReportModel]`. Sorted defensively by `dateTime` in `SeverityEvaluator` (`identity/units/severity_units/severity_elavuator/severity_evaluator.py:37-40`). No report produced if reading is `NaN` (`ValueError` raised at `threshold_model.py:105`) or if caller omits appending report to history. |

---

## B. REAL NAMES

### Enums and Models
| Enum / Model | Real Name | Members / Attributes (in order) | Notes |
|---|---|---|---|
| `ThresholdLevelType` | `ThresholdLevelType` | `Optimal = "optimal"`, `Stress = "stress"`, `HighRisk = "hight risk"`, `Critical = "critical"` | Value has typo `"hight risk"` |
| `SeverityLevelType` | `SeverityLevelType` | `Optimal = "optimal"`, `Stress = "stress"`, `ElevatedRisk = "elevated risk"`, `Critical = "critical"` | Exact match with spec |
| `ThresholdDirection` | `ThresholdDirection` | `Low = "low"`, `High = "high"` | Direction for Range thresholds |
| `PondParameters` | `PondParameters` | `DO = ("DO","mg/L")`, `pH = ("pH","")`, `tem = ("Temperature","C")`, `NH3 = ("NH3","mg/L")`, `NO2_N = ("NO2-_N","mg/L")`, `salinity = ("salinity","ppt")` | Name is `tem`, not `temperature`; `NO2_N` with label `NO2-_N` |
| `AnalysisReportModel` | `AnalysisReportModel` | `dateTime`, `parameter`, `thresholdStatus`, `thresholdDirection`, `severity` (properties: `severityStatus`, `description`, `guidance`) | Missing measured reading `value` |

### Exact Name Comparison: Severity vs Zone
- **Severity names:** Exactly `Optimal`, `Stress`, `ElevatedRisk`, `Critical`. Enum string values: `"optimal"`, `"stress"`, `"elevated risk"`, `"critical"`.
- **Zone names:** Member names are `Optimal`, `Stress`, `HighRisk`, `Critical`. Enum string values: `"optimal"`, `"stress"`, `"hight risk"` (typo in string value), `"critical"`.

### Name Discrepancies with AGENT_CONTEXT / Specs
| Spec / AGENT_CONTEXT Name | Real Code Name | File : Line | Detail |
|---|---|---|---|
| `Temperature` / `temperature` | `tem` | `identity/parameters/pond_parameter_enum.py:6` | Enum identifier is `tem` |
| `NO2` / `no2` | `NO2_N` | `identity/parameters/pond_parameter_enum.py:8` | Identifier is `NO2_N` |
| `value` / `measuredValue` | *Missing* | `identity/formats/analysis_report/analysis_report_model.py:10` | Measured numeric reading is not retained |
| `severityStatus` | `severity` + property `severityStatus` | `identity/formats/analysis_report/analysis_report_model.py:17, 32` | Added property alias in Phase 0 |
| `highRisk` | `HighRisk` (value: `"hight risk"`) | `identity/units/threshold_units/threshold_level/threshold_level.py:6` | Enum string value contains extra 't' |
| `HightRiskCountMinute` | `HightRiskCountMinute` | `identity/units/severity_units/severity_elavuator/severity_escalation_policy.py:8` | Typo with 't' in escalation policy field |
| `needRocoveryEleveted` | `needRocoveryEleveted` | `identity/units/severity_units/severity_description/severity_des_set_model.py:11` | Typo in description set |
| `NO2_2Threshold` | `NO2_2Threshold` | `identity/animals/animal_model.py:46` | Typo `NO2_2` instead of `NO2_N` in ABC |

---

## C. TESTS AND HYGIENE

- **C1. Test Count:**
  - Old tests (`tests/test_range_severity.py`): 21 test functions (33 test cases with parametrize).
  - New tests (`tests/test_analysis_core.py`): 14 test functions.
  - Total test cases: 47.
  - *CLI Execution Status:* **UNVERIFIED** (Automated runner safety classifier `antigravity-free-tier[1m]` timed out during bash execution). Static analysis confirms all imports, mock signatures, and assertion branches match codebase types.
- **C2. Git Status and Diff:**
  - Modified files in Phase 0/1:
    - `identity/formats/analysis_report/analysis_report_model.py` (Phase 0: `severityStatus`, `description`, `guidance` properties)
    - `identity/units/severity_units/severity/severity_model.py` (Phase 0: `severityStatus` property alias)
    - `identity/analysis/helpers.py` (Phase 0/1: time helpers + `aerationHours`)
    - `identity/analysis/severity_view.py` (Phase 1: `isOptimalZone`, `severityRank`, `toViews`)
    - `docs/PROGRESS.md` (Progress tracking)
    - `tests/test_analysis_core.py` (Phase 1 unit tests)
  - Pre-existing / out-of-phase changes:
    - `identity/animals/nile_tilapia/nile_parameter_severity/DO/nile_DO_severity.py` (User typo fix before session)
    - `main.py` (User cleared scratchpad before session)
    - `AGENT_CONTEXT.md.md` (Spec documentation)
    - `doc/` (Prompts and summary directory)
- **C3. New Dependencies:** **None**. Only Python 3.11+ standard library (`dataclasses`, `datetime`, `enum`, `hashlib`, `typing`, `zoneinfo`) and `pytest`.
- **C4. Python Version:** Python **3.14.4** (verified via `python --version`).
- **C5. Import Check:**
  `python -c "import config.constants, identity.analysis.models, identity.analysis.helpers, identity.analysis.changeset, identity.analysis.ids, identity.analysis.severity_view"`
  All modules import clean from repo root with zero `sys.path` hacks.

---

## D. SPOT CHECKS

### D1. `nightWindowFor` (Timezone: `Asia/Bangkok`, UTC+07:00)
Reference date: `2026-10-25`. Rules: `nightEndHour = 6`, `nightStartHour = 21`.
- **Local 03:00** (`2026-10-25 03:00` local / `2026-10-24 20:00` UTC):
  - `nightDate`: `2026-10-24`
  - Local Window: `2026-10-24 21:00` to `2026-10-25 06:00`
  - Naive UTC Window: `2026-10-24 14:00` to `2026-10-24 23:00`
- **Local 06:00** (`2026-10-25 06:00` local / `2026-10-24 23:00` UTC):
  - `nightDate`: `2026-10-25`
  - Local Window: `2026-10-25 21:00` to `2026-10-26 06:00`
  - Naive UTC Window: `2026-10-25 14:00` to `2026-10-25 23:00`
- **Local 15:00** (`2026-10-25 15:00` local / `2026-10-25 08:00` UTC):
  - `nightDate`: `2026-10-25`
  - Local Window: `2026-10-25 21:00` to `2026-10-26 06:00`
  - Naive UTC Window: `2026-10-25 14:00` to `2026-10-25 23:00`
- **Local 23:00** (`2026-10-25 23:00` local / `2026-10-25 16:00` UTC):
  - `nightDate`: `2026-10-25`
  - Local Window: `2026-10-25 21:00` to `2026-10-26 06:00`
  - Naive UTC Window: `2026-10-25 14:00` to `2026-10-25 23:00`

### D2. `isStale`
- Threshold: `cfg.staleFactor * cfg.expectedIntervalMinutes = 3.0 * 30 = 90.0 min`.
- At **90 min 00 s**: `(now - readingDt) > timedelta(minutes=90)` is `False` -> **`isStale = False`**.
- At **90 min 01 s**: `(now - readingDt) > timedelta(minutes=90)` is `True` -> **`isStale = True`**.

### D3. `aerationHours` Overlap and Skip Check
- **Inputs:**
  1. `Activity(type=aeration, status=pending, scheduledAt=10:00, amount=2.0)` -> [10:00, 12:00]
  2. `Activity(type=aeration, status=pending, scheduledAt=11:00, amount=2.0)` -> [11:00, 13:00]
  3. `Activity(type=aeration, status=skipped, scheduledAt=10:30, amount=1.0)` -> [10:30, 11:30]
- **Calculation:** Skipped activity is ignored (Rule 6). Pending intervals merge into [10:00, 13:00].
- **Result:** **`3.0` hours**.

### D4. StoreSimulator Idempotency
- Applying the same `ChangeSet` twice:
  `snap1 = sim.apply(changeset)`
  `snap2 = sim.apply(changeset)`
  Both snapshots contain identical dictionary states: **`snap1 == snap2`**.

### D5. Recovery Hold & Severity Rank Check
- Evaluated history with real engine:
  - Reading T-60 min: Temperature 16.0 C -> HighRisk, ElevatedRisk.
  - Reading T-30 min: Temperature 28.0 C -> Optimal threshold zone, Stress severity (Recovery Hold).
- View conversion (`toViews`):
  - `isOptimalZone(report)` -> **`True`** (`thresholdStatus == ThresholdLevelType.Optimal`).
  - `severityRank(report)` -> **`1`** (rank of `SeverityLevelType.Stress`).
  - `severityRank(SeverityLevelType.Stress)` -> **`1`**.
  - Rank equality holds: `severityRank(report) == severityRank(SeverityLevelType.Stress)`.

### D6. Deterministic IDs
- Evaluated twice with identical arguments:
  `episodeId("pond_1", PondParameters.DO, None, ts)` -> `"ep_DO_85b4c1aa32aa"`
  Both calls produce exact identical strings: **Identical**.

---

## E. MISMATCHES

1. **Problem:** `AnalysisReportModel` does not retain the measured float value (`valueNow`).
   - *Evidence:* `identity/formats/analysis_report/analysis_report_model.py:10-18`.
   - *Fix:* Add `value: float` to `AnalysisReportModel` and pass `self.valueNow` inside `ParameterModel.buildAnalysisReport()`.
2. **Problem:** `ThresholdLevelType.HighRisk` enum value has typo (`"hight risk"` with 't').
   - *Evidence:* `identity/units/threshold_units/threshold_level/threshold_level.py:6`.
   - *Fix:* Retain `"hight risk"` as canonical internal string value to preserve backward compatibility.
3. **Problem:** Parameter name for Temperature is `tem` (lowercase 3 letters), not `temperature`.
   - *Evidence:* `identity/parameters/pond_parameter_enum.py:6`.
   - *Fix:* Use `PondParameters.tem` throughout all analysis, diagnostic, and recommendation code.
4. **Problem:** Typos in escalation policy and description set attribute names (`HightRiskCountMinute`, `needRocoveryEleveted`, `NO2_2Threshold`).
   - *Evidence:* `identity/units/severity_units/severity_elavuator/severity_escalation_policy.py:8`, `identity/animals/animal_model.py:46`.
   - *Fix:* Map these transparently in `config/constants.py` and diagnostic code without altering existing severity files.
5. **Problem:** `PondParametersHistoryModel` stores raw Python lists without enforcing chronological order on append.
   - *Evidence:* `identity/parameters/pond_parameter_history_model.py:6-14`.
   - *Fix:* Ensure `ParameterTimelineView` explicitly sorts by `dateTime` on construction.

---

## F. QUESTIONS

1. **Question:** Should `AnalysisReportModel` be updated to include `value: float` in Phase 2 so detectors (e.g. `PH_SWING`) have access to exact numeric delta?
   - *Proposed default:* Add `value: float` to `AnalysisReportModel` in Phase 2.
2. **Question:** Should `ThresholdLevelType.HighRisk` string value `"hight risk"` be preserved or corrected to `"high risk"`?
   - *Proposed default:* Preserve `"hight risk"` to ensure zero disruption to existing tests.
3. **Question:** When an aeration activity has `status == pending` and no `completedAt` timestamp, how should duration be inferred if `amount` is missing?
   - *Proposed default:* Assume 1.0 hour nominal duration.
4. **Question:** When `run_analysis` receives an empty reading history, should it return an empty `ChangeSet`?
   - *Proposed default:* Return empty `ChangeSet` (no episodes, no predictions).
5. **Question:** If the latest reading is stale (>90 min), should existing open recommendations remain open?
   - *Proposed default:* Per Rule 11, do not expire existing recommendations when data is stale; return empty ChangeSet.
