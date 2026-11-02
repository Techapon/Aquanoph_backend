# ANALYSIS_BACKEND_SUMMARY.md

## 1. Overview
- **Language:** Python 3.11
- **Framework:** Pure Python (no web framework)
- **Deployment:** Library called from an external orchestrator (sensor‑buoy simulator or message queue listener)
- **Data flow:**
```
Sensor reading → PondParametersDeliveryModel
  → NileTilapiaModel (species config)
    → PondParametersModel (creates one ParameterModel per parameter)
      → ParameterModel.buildAnalysisReport()
          ├─ Threshold.checkThreshold() → ThresholdLevelModel
          └─ SeverityEvaluator() → SeverityModel
              └─ AnalysisReportModel ← stored in PondParametersHistoryModel
```

---

## 2. Structure (depth 3)
```
Aquanoph_backend/
├─ main.py                           # Empty (stub)
├─ identity/
│   ├─ animals/
│   │   ├─ animal_model.py           # AquaticAnimal ABC (interface)
│   │   └─ nile_tilapia/
│   │       ├─ nile_model.py         # NileTilapiaModel (concrete species)
│   │       ├─ nile_parameter_threshold/
│   │       │   ├─ DO/nile_DO_threshold.py  ← dynamic, biomass-adjusted
│   │       │   ├─ NH3/nile_NH3_threshold.py
│   │       │   ├─ NO2_N/nile_NO2_N_threshold.py
│   │       │   ├─ pH/nile_pH_threshold.py  ← RangeThreshold
│   │       │   ├─ salinity/nile_salinity_threshold.py  ← interaction-adjusted
│   │       │   └─ tempearture/nile_tem_threshold.py  ← RangeThreshold
│   │       └─ nile_parameter_severity/
│   │           ├─ DO/nile_DO_severity.py
│   │           ├─ NH3/nile_NH3_severity.py
│   │           ├─ NO2_N/nile_NO2_N_severity.py
│   │           ├─ pH/nile_pH_severity.py    ← RangeSeverityDesSet + factory
│   │           ├─ salinity/nile_salinity_severity.py
│   │           └─ tempearture/nile_tem_severity.py
│   ├─ formats/
│   │   └─ analysis_report/
│   │       └─ analysis_report_model.py      # AnalysisReportModel (snapshot)
│   ├─ parameters/
│   │   ├─ parameter_model.py               # ParameterModel (core analysis logic)
│   │   ├─ pond_parameter_enum.py           # PondParameters enum
│   │   ├─ pond_parameter_history_model.py  # PondParametersHistoryModel
│   │   └─ pond_parameter_model.py          # PondParametersModel orchestrator
│   └─ units/
│       ├─ severity_units/
│       │   ├─ severity/severity_model.py
│       │   ├─ severity_description/
│       │   │   ├─ severity_description_model.py
│       │   │   └─ severity_des_set_model.py
│       │   ├─ severity_elavuator/
│       │   │   ├─ severity_evaluator.py     # SeverityEvaluator (engine)
│       │   │   ├─ severity_escalation_policy.py
│       │   │   └─ severity_helper.py        # timeline / metrics helpers
│       │   └─ severity_level/
│       │       └─ severity_level_enum.py
│       └─ threshold_units/
│           ├─ threshold/
│           │   ├─ threshold_model.py        # Threshold ABC, LevelThreshold, RangeThreshold
│           │   ├─ threshold_type_level_enum.py
│           │   └─ value_range.py
│           └─ threshold_level/
│               ├─ threshold_level.py
│               ├─ threshold_level_model.py
│               └─ threshold_direction.py
├─ services/
│   ├─ dif_minute.py                # calDiffMinute()
│   └─ minute_to_hours.py           # MinuteToHours()
└─ tests/
    └─ test_range_severity.py       # 15+ unit tests
```

---

## 3. Run & Test
| Item | Detail | Verified? |
|------|--------|-----------|
| Setup | `pip install pytest` (stdlib only; no `requirements.txt` found) | unverified |
| Run analysis | Instantiate `NileTilapiaModel` + `PondParametersModel`, call `buildAnalysisReport()` | unverified (code review only) |
| Tests | `pytest tests/test_range_severity.py -v` (from repo root) | unverified (sandbox blocked) |
| Env vars needed | None in this repo | confirmed |

---

## 4. Triggers & Orchestration
- **Trigger:** New sensor reading (supplied externally as `PondParametersDeliveryModel`); no webhook, queue, or cron exists inside this repo.
- **Orchestration:** `PondParametersModel.__init__` creates one `ParameterModel` per parameter and calls it immediately.
- **Ordering:** Threshold check → severity evaluation → report build, per parameter.
- **Idempotency:** Evaluator filters history by `r.dateTime < parameterDateTime` (strict less‑than), so re‑running with the same timestamp is safe.
- **Concurrency / locking:** None implemented; assumed handled by the caller.
- **Retry / failure:** Raises `ValueError` on invalid input (NaN values, illegal direction, bad threshold order); caller must catch.

---

## 5. Modules

### Severity stage

| File | Responsibility | Main function / class | Inputs | Outputs |
|------|----------------|-----------------------|--------|---------|
| `parameter_model.py` | Orchestrates threshold + severity | `buildAnalysisReport()` | valueNow, history, datetime | `AnalysisReportModel` |
| `severity_evaluator.py` | Engine — decides severity level | `SeverityEvaluator()` | `ThresholdLevelModel`, history, `EscalationPolicy`, description set | `SeverityModel` |
| `severity_helper.py` | Timeline, metrics, recovery state | `buildTimeline`, `calZoneMetrics`, `countEpisodes`, `findPendingRecovery` | history list, `ThresholdLevelType`, direction, now | `TimelinePoint`, `ZoneMetrics`, `RecoveryState` |
| `severity_escalation_policy.py` | Policy data class (time thresholds) | `EscalationPolicy` (dataclass) | – (constructor defaults) | Policy instance |
| `threshold_model.py` | Threshold classification | `LevelThreshold.checkThreshold`, `RangeThreshold.checkThreshold` | float value | `ThresholdLevelModel` |

**Severity decision order (per evaluator):**
1. **Critical → immediate** `SeverityLevelType.Critical`
2. **Optimal → check Recovery Hold** (may return `SeverityLevelType.Stress` while hold active)
3. **Stress → check continuous / cumulative** → escalate to `ElevatedRisk`
4. **HighRisk → check continuous / cumulative / episode recurrence** → escalate to `Critical`

**Recovery Hold logic** (`_evaluateOptimal`, `findPendingRecovery`):
- `ElevatedRisk` event → hold = `ElevatedRecoveryHoldMinute` (default 120 min)
- `Critical` event → hold = `CriticalRecoveryHoldMinute` (default 240 min)
- Hold resets when optimal streak breaks.
- Stronger event (`Critical > ElevatedRisk`) wins if two compete.

### Diagnostic, Prediction, Recommendation stages
**Not implemented** in this codebase. No files exist for these stages.

---

## 6. Data Access

| Data | Model | How loaded | How written |
|------|-------|------------|-------------|
| Current reading | `PondParametersDeliveryModel` | Supplied by caller | N/A (input) |
| Parameter history | `list[AnalysisReportModel]` inside `PondParametersHistoryModel` | Supplied by caller | Caller appends the returned `AnalysisReportModel` |
| Species config | `NileTilapiaModel` attributes | Instantiated with `weight`, `density`, `parameterNow` | Immutable during a run |

No ORM, no DB client, no Supabase SDK inside this repo.

---

## 7. Time Handling

| Concern | Implementation |
|---------|----------------|
| Timestamp type | `datetime` (naive; timezone unspecified — assumed UTC by convention) |
| Timezone conversion | **Not done** in this repo; caller responsibility |
| Time arithmetic | `timedelta` in `calZoneMetrics` and `countEpisodes` |
| Recovery hold remaining | `(now - optimalSince).total_seconds() / 60` |
| Stale readings | **Not handled** — gaps in history appear as "parameter was Optimal" |
| Night window / sunrise | **Not implemented** |

---

## 8. Configuration & Constants

| Constant | Value | File | Used by |
|----------|-------|------|---------|
| `stressCountMinute` | 480 min | `severity_escalation_policy.py` | Stress → ElevatedRisk (continuous) |
| `HightRiskCountMinute` | 150 min | same | HighRisk → Critical (continuous) |
| `stressCumIn24Hs` | 480 min | same | Stress → ElevatedRisk (cumulative) |
| `HightRiskCumIn24Hs` | 240 min | same | HighRisk → Critical (cumulative) |
| `recurrenceEpisode24H` | 2 episodes | same | HighRisk → Critical (episode count) |
| `EpisodeSeparationMinute` | 60 min | same | Episode boundary |
| `ElevatedRecoveryHoldMinute` | 120 min | same | Recovery hold after ElevatedRisk |
| `CriticalRecoveryHoldMinute` | 240 min | same | Recovery hold after Critical |
| DO optimal base | 5.0 – 7.0 mg/L (biomass‑dependent) | `nile_DO_threshold.py` | DO threshold |
| DO oxygen‑demand formula | `q = 10^(0.492 − 0.243·log10(w) + 1.68·log10(T))` | `nile_DO_threshold.py` | Biomass adjustment |
| NH3 Optimal / Stress / HighRisk / Critical | 0.02 / 0.05 / 0.2 / 1000 mg/L | `nile_NH3_threshold.py` | NH3 threshold |
| NO2-N Optimal / Stress / HighRisk | 0.1 / 0.5 / 1.0 mg/L | `nile_NO2_N_threshold.py` | NO2-N threshold |
| pH Optimal / Stress / HighRisk | 7–8.5 / 6.5–9 / 6–10 | `nile_pH_threshold.py` | pH threshold |
| Temp Optimal / Stress / HighRisk | 26–30 / 22–32 / 16–35 °C | `nile_tem_threshold.py` | Temp threshold |
| Salinity base Optimal / Stress / HighRisk | 5 / 15 / 25 ppt | `nile_salinity_threshold.py` | Salinity threshold |
| Salinity adjustment (NH3 warn) | −2.5 ppt | `nile_salinity_threshold.py` | Interaction shift |
| Salinity adjustment (NH3 severe) | −5.0 ppt | same | Interaction shift |
| Salinity adjustment (DO low) | −2.5 ppt | same | Interaction shift |
| NH3 warn / severe thresholds | 0.1 / 0.5 mg/L | `nile_salinity_threshold.py` (hardcoded) | Salinity interaction |
| DO low threshold | 3.0 mg/L | same (hardcoded) | Salinity interaction |

**Flag:** All numeric values in threshold files are hard‑coded, not read from a config file.

---

## 9. Retroactive Edits
Not implemented. No mechanism for replaying, overwriting, or invalidating past `AnalysisReportModel` entries.

---

## 10. User‑Facing Text

| Concern | Detail |
|---------|--------|
| Storage location | Inside `SeverityDesSetModel` / `SeverityDescriptionModel` instances in each `nile_parameter_severity/*.py` |
| Language | Thai (ภาษาไทย) — with placeholder notes like "ปลาอาจ..." indicating incomplete drafts |
| Construction | Templates interpolated at factory‑creation time using f-strings with `label`, `detail`, `care` parameters |
| Runtime appended text | Evaluator calls `.withAppend(text)` to add time‑based clauses (duration, remaining hold); returns a **copy** to avoid mutating shared description sets |
| Pending expert review | pH and temperature descriptions are explicitly marked "ให้ผู้เชี่ยวชาญตรวจก่อนใช้งานจริง" |

---

## 11. Spec Coverage (No docs/ folder found; partial spec check)

| Spec item | Status | Evidence |
|-----------|--------|----------|
| DO threshold (dynamic biomass‑adjusted) | ✅ done | `nile_DO_threshold.py` |
| NH3 threshold | ✅ done | `nile_NH3_threshold.py` |
| NO2-N threshold | ✅ done | `nile_NO2_N_threshold.py` |
| pH threshold (RangeThreshold) | ✅ done | `nile_pH_threshold.py` |
| Temperature threshold (RangeThreshold) | ✅ done | `nile_tem_threshold.py` |
| Salinity threshold (interaction-adjusted) | ✅ done | `nile_salinity_threshold.py` |
| Severity zones (Optimal/Stress/ElevatedRisk/Critical) | ✅ done | `severity_evaluator.py` |
| Recovery Hold (Elevated=120 min, Critical=240 min) | ✅ done | `severity_escalation_policy.py`, `severity_evaluator.py` |
| Episode recurrence counting | ✅ done | `severity_helper.py:countEpisodes` |
| Diagnostic cause rules (DO_C_FEED, DO_C_TEMP, DO_C_NIGHT, etc.) | ❌ missing | – |
| Detector PH_SWING | ❌ missing | – |
| Prediction rules (PRED_DO_NIGHT, PRED_DO_REPEAT, PRED_NH3_RISE) | ❌ missing | – |
| Recommendations (AERATE, WATER_CHANGE, ADD_ALKALINITY) | ❌ missing | – |
| Reconcile, blocked(), source-closed expiry | ❌ missing | – |
| Retroactive edit handling (4-day window, revised_at) | ❌ missing | – |
| Stale reading detection (3× expected interval) | ❌ missing | – |

---

## 12. Quality & Risks

| Category | Detail |
|----------|--------|
| Tests | `tests/test_range_severity.py` — 15 tests covering threshold classification, direction separation, severity escalation, recovery hold, episode counting, history immutability, and model validation |
| Code quality | Well‑structured; uses ABCs, generics, NamedTuples |
| **Bug 1** | `SeverityModel` stores `severityStatus` property alias but `analysis_report_model.py` uses `event.severityStatus` which is not defined — may `AttributeError` at recovery‑hold check |
| **Bug 2** | NH3 / NO2-N / Salinity severity description files contain text referencing "DO" (copy‑paste from DO template) — wrong user‑facing messages |
| **Bug 3** | `NH3_EscalationPolicy`, `NO2_N_EscalationPolicy`, `salinity_EscalationPolicy` are returned with empty constructors; the `abnormalLabel` field defaults to `"ค่าผิดปกติ"` (generic) rather than parameter-specific |
| TODO | pH and temperature descriptions marked for expert review |
| Dead code | `dif_minute.py` (`calDiffMinute`) — imported nowhere (unverified) |
| Duplicate logic | Severity description factories for DO / NH3 / NO2-N / Salinity are near‑identical; should use factory helper like pH / Temperature do |
| Performance | O(N) history scan; no cap on history length — may slow with long‑running ponds |
| Security | No external I/O; no risk |

---

## 13. Where to Add the Next Code

| Task | File / folder to create | Pattern to copy |
|------|------------------------|-----------------|
| New parameter threshold | `identity/animals/nile_tilapia/nile_parameter_threshold/<PARAM>/nile_<PARAM>_threshold.py` | Copy `nile_pH_threshold.py` (Range) or `nile_NH3_threshold.py` (Level) |
| New severity description set | `identity/animals/nile_tilapia/nile_parameter_severity/<PARAM>/nile_<PARAM>_severity.py` | Copy `nile_tem_severity.py` (uses factory helper `_temperatureSideSet`) |
| New cause rule / detector | `identity/animals/nile_tilapia/<PARAM>_diagnostic/` (new folder) | Define a function `def detect_X(history, ...) -> bool` |
| New prediction rule | `identity/prediction/<rule_name>.py` (new folder) | TBD; no pattern yet |
| New recommendation entry | `identity/recommendation/<name>.py` (new folder) | TBD; no pattern yet |
| New config constant | `config/constants.py` (new file) | Plain module with typed constants |
| New test | `tests/test_<feature>.py` | Copy `test_range_severity.py` helper style |
| New message template | Add a `SeverityDescriptionModel(des=…, detail=…, guid=…)` to the relevant `_…SideSet()` factory | See `_pHSideSet()` in `nile_pH_severity.py` |

---

## 14. Open Questions

| Question | Where to look for answer |
|----------|--------------------------|
| What are the intended non‑default values for `EscalationPolicy` fields per parameter? | Spec docs / domain expert |
| How are `PondParametersDeliveryModel` objects created (Supabase listener, FastAPI, or simulator)? | Outer service layer (not in repo) |
| When will Diagnostic / Prediction / Recommendation stages be added? | Project roadmap |
| Does the system need to handle data gaps (readings missing for >1.5 h)? | Spec docs |
| Should timestamps be stored in pond‑local time or UTC? | System design decision |
| Is `SeverityModel.severityStatus` a real property or a typo for `severityLevel`? | `severity_model.py` (line 6) — attribute is `severityLevel` not `severityStatus`; evaluator and tests reference `severityStatus` — potential runtime error |
