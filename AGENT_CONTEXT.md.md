# AGENT_CONTEXT — Aquanoph Analysis Backend (logic only)

Read this file fully at the start of EVERY phase. Then read the phase file. (If using Claude Code: copy this file to repo-root `CLAUDE.md`.)

## 1. Mission
Build the pure-logic core of a fish-pond analysis backend (Nile tilapia). Input: sensor-derived severity reports + farmer activity logs. Output: Diagnostic reports, Predictions, Recommendations.
Severity engine already exists and is **not** to be changed (except Bug 1 in Phase 0).

## 2. Scope
- IN: pure Python logic, dataclasses, config, English text templates, tests.
- OUT (do not build): database, ORM, queue/worker, HTTP, push notifications, Thai text, kNN, severity engine changes.
- Python 3.11, stdlib + pytest only. No new dependencies.

## 3. Architecture contract
```
run_analysis(snapshot: PondSnapshot, trigger: Trigger, now: datetime) -> ChangeSet
```
- `snapshot` = everything needed (immutable). `ChangeSet` = what should change. The engine never writes anything.
- A future DB adapter will: load snapshot -> call -> persist ChangeSet. Keep logic free of that.
- Pipeline order is fixed: Diagnostic (episodes + detector) -> Prediction -> Recommendation reconcile.
- Tests simulate a DB with `tests/support/store_sim.py` (`apply(changeset)`).

## 4. Target layout
```
config/constants.py            AnalysisConfig (all tunable numbers)
identity/analysis/             severity_view.py, models.py, helpers.py, ids.py, changeset.py
identity/diagnostic/           episode.py, cause_rules.py, detectors/ph_swing.py, runner.py
identity/prediction/           rules/*.py, runner.py
identity/recommendation/       catalog/*.py, reconcile.py, apply_plan.py
identity/text/                 templates_en.py, render.py
services/run_analysis.py       orchestrator
tests/                         test_<area>.py, scenarios/, support/{factories,store_sim}.py
docs/                          spec copies, CODE_FINDINGS.md, BACKLOG.md, PROGRESS.md
```
Existing code under `identity/units`, `identity/parameters`, `identity/animals` stays untouched.

## 5. Source documents and precedence
1. This file, section 8 (Overrides)
2. The phase file
3. `docs/part2_minimal_logic_flow_v0_3.md` (Thai; rules, numbers, test cases; read only the section a phase file points to, or when a rule is ambiguous)
4. `docs/special_part_retroactive_edits_v0_2.md`, `docs/09_system_logic_summary.md`, `docs/app_spec_v0_4.md`, `docs/ANALYSIS_BACKEND_SUMMARY.md`

Phase files are meant to be self-sufficient; do not read Thai docs unless needed.

## 6. Glossary
- Parameters: DO, NH3, NO2_N, pH, Temperature, Salinity. pH and Temperature are Range thresholds (direction low/high); others are Level thresholds.
- Zone order: Optimal < Stress < HighRisk < Critical (threshold zone).
- Severity order: Optimal < Stress < ElevatedRisk < Critical (engine output). Recovery Hold = zone Optimal but severity Stress.
- Activity types: feeding(point, kg), aeration(start..end), alkalinity/lime/probiotic(point, kg), water_change(point, fraction of pond), other. Status: pending/done/skipped. Source: user/recommendation.
- Episode: continuous stretch where a parameter's (direction-aware) zone is not Optimal. Unit of Diagnostic.
- Signal: normalized input to Recommendation, from episode / prediction / detector.
- Recommendation status: pending, snoozed, applied, dismissed, expired. Urgency: urgent (fixed time on apply) / non_urgent (user picks time in window).
- `dedupe_key` identifies "the same recommendation" across runs.

## 7. Global rules (always)
1. **Pure & deterministic.** No I/O, no `datetime.now()`, no randomness, no global mutable state. `now` is a parameter.
2. **Immutable data.** Frozen dataclasses; never mutate inputs; return new objects.
3. **Time.** Datetimes are naive and mean UTC. Every clock-based rule (night, evening, time windows, local date) MUST go through `localTime()`/helpers using `pond.timezone` (IANA, via `zoneinfo`). Never read `.hour`/`.date()` from a raw datetime.
4. **No magic numbers.** Every tunable number lives in `AnalysisConfig`. Rules read from `cfg`.
5. **Unknown != not done.** Missing activity record means "not logged". Never conclude "not fed/not aerated" from absence. Rules use positive evidence only; text says "not logged".
6. **Retroactive honesty.** Facts (readings, severity) never change; interpretations (diagnostic/prediction/recommendation) are recomputed. Only activities with status `done` count as past events; `pending` counts only as plan; `skipped` counts as nothing.
7. **Idempotent.** Same snapshot + trigger + now -> same ChangeSet. Running twice on a snapshot that already applied the first result -> empty ChangeSet. Ids are deterministic (`ids.py`). Include an object in the ChangeSet only if it differs from the snapshot's version.
8. **Rules return facts, not prose.** Rules output structured `facts`; text is rendered only in `identity/text` (Phase 6).
9. **Style.** Match existing repo: classes PascalCase, functions/methods/fields camelCase, files snake_case. Type hints everywhere. Small functions. Docstring = one line pointing to the spec rule id.
10. **User-facing text:** English, template-based, keyed by id. No Thai.
11. **Stale data.** Reading older than `staleFactor x expectedIntervalMinutes` is stale: do not create new analysis from it; keep existing results; never expire a recommendation just because data is missing.
12. **History horizon.** Snapshot holds >= `historyHorizonDays` (8) of history. Never assume more.

## 8. Overrides to v0.3 (decided; these win)
- **O1** Timezone handling as rule 3 above.
- **O2** Night window: `nightWindowFor(t)`: if `localTime(t).hour < nightEndHour` the night started on the previous local date; else it started on the same local date. Window = nightDate `nightStartHour:00` -> nightDate+1 `nightEndHour:00` (local), returned as naive UTC.
- **O3** A recommendation can have several sources (`SourceRef` list). It expires with `no_longer_applies` only when ALL its sources are closed. Detector sources never close (only `validUntil` ends them).
- **O4** AERATE with both sources (prediction a + diagnostic b): start = apply time (rule b), end = the later of the two ends, deadline = the earlier of the two deadlines.
- **O5** Push/notify = a `Notification` entry in the ChangeSet only. Nothing is sent.
- **O6** Urgent aeration apply uses "recommendation overwrites user's `pending` aeration" (full rule in Phase 5). User-form and non_urgent aeration overlaps still block. `done` and recommendation-origin activities are never modified.
- **O7** Thai text bugs (Bug 2, Bug 3 in ANALYSIS_BACKEND_SUMMARY) are out of scope -> `docs/BACKLOG.md`.
- **O8** All activity edits older than `retroWindowDays` (4) are rejected (read-only); status never moves done/skipped -> pending.

## 9. Working protocol
1. Read this file + the phase file. Read only the spec sections the phase lists.
2. Verify names against the real code before using them (the SUMMARY may be slightly off). Adjust names, not semantics; note it in the report.
3. **Test first**: write the phase's tests, see them fail, then implement.
4. Touch only files the phase lists. Do not refactor other phases' files or the severity engine.
5. Run the full test suite (`pytest -q`). All old tests must still pass.
6. Append a short entry to `docs/PROGRESS.md`.
7. Final message format:
   - **Done**: checklist from the phase's DoD, each item pass/fail
   - **Tests**: added N, total pass/fail
   - **Files**: added/changed
   - **Deviations**: anything differing from the phase file, and why
   - **Questions**: spec ambiguities found (max 5, each with your proposed default)

**STOP and ask (do not guess)** when: a rule is ambiguous and not covered by section 8; a test from the spec cannot pass without changing a spec rule; you need to change the severity engine beyond Bug 1; you need a new dependency; an existing test breaks and the cause isn't your change.

## 10. Test-case map (v0.3 §11) -> phase
T1,T1b,T6(diag part) -> Phase 2 | T7(detector part) -> Phase 3 | T4,T9,T11,T12,T15,T16 -> Phase 4 (prediction part) | T2,T3,T5,T7,T8,T10,T13,T14,T18 -> Phase 5 | Case 1-3 text -> Phase 6 | T6(full),T17, all scenarios, idempotency -> Phase 7.

## 11. `docs/PROGRESS.md` template (create in Phase 0)
```
# PROGRESS
| Phase | Status | Tests | Notes |
## Decisions made by agent
## Open questions
```