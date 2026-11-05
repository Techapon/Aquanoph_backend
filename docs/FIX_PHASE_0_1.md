# FIX PHASE 0–1 — Resolve blocker, verify tests, align code to spec

Read `AGENT_CONTEXT.md`, `PHASE_0_prep.md`, `PHASE_1_foundation.md`, then `REPORT_PHASE_0_1.md` and `docs/CODE_FINDINGS.md`.

**Principle: the spec wins.** Where the Phase 0–1 code differs from the spec, change the code, not the spec.
**One exception:** existing severity-engine code (`identity/units`, `identity/parameters`, `identity/animals`, `identity/formats`) keeps its real names. See Task 3, rule R2.

Do the tasks in order. Do not start Phase 2.

---

## Task 1 — Approve and fix F-01 (the BLOCKER)

**Decision (approved by the owner):** a minimal, additive change to the severity engine is allowed so the report keeps the measured value. This is the only engine change allowed beyond Bug 1.

1. Write a failing test first: a report built through `ParameterModel.buildAnalysisReport()` must expose the measured value.
2. In `identity/formats/analysis_report/analysis_report_model.py` add a field `value: float | None = None` (default keeps all existing constructor calls and tests working). Do not rename or reorder existing attributes.
3. In `identity/parameters/parameter_model.py` (`buildAnalysisReport`) pass `self.valueNow` into the report. Change nothing else there.
4. Severity/threshold/recovery-hold logic must not change at all. Existing severity tests must still pass unmodified.
5. `SeverityReportView.value` is filled from `report.value`. `toView` raises `ValueError` if `value` is `None` (never silently skip).
6. Update `docs/CODE_FINDINGS.md`: move F-01 to "Resolved", and answer question f) from Phase 0 properly (the report now stores the value).
7. In `docs/PROGRESS.md` remove the open question about F-01 and log the decision.
8. Also review the extra properties added to `AnalysisReportModel` in Phase 0 (`description`, `guidance`, `severityStatus`). Keep only what Bug 1 needs (`severityStatus` alias). If `description` and `guidance` are not needed by anything else, remove them and say so in the report.

## Task 2 — Get a verified test baseline

The earlier report says pytest could not run (timeout), so no test count is verified. Fix that.

1. Run `pytest -q` from repo root. If it hangs, run per file (`pytest -q tests/test_range_severity.py`, then each new file) with a timeout, and find what hangs.
2. Report exact numbers: passed / failed / errors, per file, and total. Explain the earlier mismatch (PROGRESS.md says 15 + 11, REPORT says 47).
3. Report `python --version`. The spec says Python 3.11; the machine has 3.14. You cannot change the machine, so make sure no code uses features newer than 3.11 (no `type X = ...` statements, no PEP 695 generics, no 3.12+ only stdlib). Fix any you find.
4. Do not move on until `pytest -q` runs to completion in one command.

## Task 3 — Align code with the spec

Rules for deciding:
- **R1.** For anything the spec names in Phase 0–1 (config fields, models, helpers, ids, ChangeSet, test-support, test files): the code must match the spec exactly. Rename and refactor the code. Update all call sites and tests.
- **R2.** For existing engine names with typos or different spelling (`PondParameters.tem`, `PondParameters.NO2_N`, `ThresholdLevelType.HighRisk = "hight risk"`, `HightRiskCountMinute`, `needRocoveryEleveted`, `NO2_2Threshold`): do NOT rename them. AGENT_CONTEXT §9.2 says adjust names, not semantics. Use the real names in new code, and list the mapping in `docs/CODE_FINDINGS.md`.
- **R3.** If following the spec would break an existing test or needs a change in the engine other than Task 1: STOP and ask.

Check and fix each item below (all are R1 unless stated):

| # | Found in report | Spec requires | Action |
|---|---|---|---|
| 1 | `nightStartHour` tested with 21 | `nightStartHour = 18`, `nightEndHour = 6` | Fix config default and any hard-coded 21. Re-run all night/boundary tests from Phase 1 (17:59 False, 18:00 True, 05:59 True, 06:00 False). |
| 2 | `Activity(scheduledAt=..., amount=...)` | `Activity(id, pondId, type, status, startTime, endTime, quantityKg, fraction, source, sourceRecId, createdAt, updatedAt)`. `endTime` only for aeration. `fraction` only for waterChange. | Rewrite `Activity` and all helpers that use it (`aerationHours`, `doneActivities`, `plannedActivities`, `mealPct`). Aeration duration comes from `startTime`/`endTime`, never from an inferred `amount`. Remove the "assume 1.0 hour" idea (report question 3). |
| 3 | ids like `ep_DO_85b4c1aa32aa` via `episodeId` | `diagId`, `predId`, `recId`, `actId` with the exact string formats in Phase 1 §3 (e.g. `diag:{pond}:{param}:{dir\|-}:{onset iso}`) | Replace the hash-based ids. Remove `episodeId`. Ids must stay deterministic and differ for different `createdAt`. |
| 4 | `diffOnly` | `changedOnly(newObjs, existingById)` | Rename. Keep `merge` (later wins) and `isEmpty`. |
| 5 | Tests all in `tests/test_analysis_core.py` | Separate files: `test_severity_view.py`, `test_config.py`, `test_helpers.py`, `test_changeset.py`, `test_store_sim.py` | Split the tests into these files. Every test case listed in the Phase 0 and Phase 1 "Tests" sections must exist. Add the ones that are missing. |
| 6 | `tests/support/` | `factories.py` (`makePond`, `makeActivity`, `makeView`, `makeSnapshot`, `t(local, tz)`) and `store_sim.py` (`StoreSim.apply`, `.snapshot()`, `.notifications`) | Verify they exist with these names and signatures. Add what is missing. |
| 7 | `StoreSim` | Handles every ChangeSet field; `apply` twice == once; the original snapshot is never mutated | Check against `snap1 == snap2` claim. The report's D4 example looks like `apply` returns a snapshot. Make it match the spec (`apply(changeset)` then `.snapshot()`). Add the missing tests. |
| 8 | `AnalysisConfig` | Every field and default in Phase 1 §1, frozen, `validate()` called in `__post_init__` | Diff the dataclass against the spec list field by field. Add missing, fix wrong defaults, add one validation test per rule. |
| 9 | `models.py` | Every enum and dataclass in Phase 1 §2, with the stated fields and `Activity.__post_init__` validation | Diff field by field. Fields not in the spec must be removed or listed in the report as a deviation. |
| 10 | `helpers.py` | Every function in Phase 1 §5 with the stated names and semantics, including `nightWindowFor` (O2), `zoneAt`, `isStale` (strictly greater), `overlap` | Diff signature by signature. Re-check the nightWindowFor cases with 18:00 start: local 03:00 → night that started yesterday; local 06:00 exactly → tonight. |
| 11 | `severity_view.py` | `SeverityReportView` with the 6 fields; `toView`, `toViews`, `zoneRank`, `severityRank`, `isOptimalZone` | Check names. Note: `isOptimalZone(report)` in the report takes a report; the spec takes a `SeverityReportView`. Follow the spec. |
| 12 | Report question 4 and 5 (empty history, stale data) | Rule 11 in AGENT_CONTEXT: stale data creates no new analysis and never expires anything | No code needed now. Do not implement it in Phase 0–1. Just confirm in the report that nothing here contradicts it. |

Also check, and fix if needed:
- No `datetime.now()` anywhere in `config/` and `identity/analysis/`.
- No clock reads (`.hour`, `.date()`) on raw datetimes outside `helpers.py`.
- All new files use camelCase for functions/fields, PascalCase for classes.
- `pytest` from repo root imports everything with no `sys.path` hacks.
- `docs/BACKLOG.md` exists with: Bug 2, Bug 3, dead code `dif_minute.py`, duplicated description factories, unbounded history scan.

## Test-first

For every change in Task 3, write or update the test first, see it fail, then change the code. Do not weaken or delete an existing assertion to make a test pass.

## Definition of Done

- [ ] F-01 fixed with a regression test; severity engine behaviour unchanged
- [ ] `pytest -q` runs to completion; exact counts reported per file and total
- [ ] No Python > 3.11-only syntax
- [ ] Table items 1–11 each marked: already matched / fixed / STOP-and-ask
- [ ] Test files split as in item 5, and every test listed in Phase 0 and Phase 1 exists
- [ ] `docs/CODE_FINDINGS.md`, `docs/PROGRESS.md`, `docs/BACKLOG.md` updated
- [ ] No engine file changed except for Task 1 (and the Bug 1 alias)

## Final message format

Same as AGENT_CONTEXT §9.7: **Done** (checklist pass/fail) · **Tests** (per-file counts, total) · **Files** (added/changed) · **Deviations** · **Questions** (max 5, each with your proposed default).
Add one more section: **Mapping table** — spec name → real engine name, for every R2 case.
