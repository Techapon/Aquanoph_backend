# PHASE 7 — Orchestrator, activity-edit rules, scenarios

Read `AGENT_CONTEXT.md`, `PHASE_2_3_4_CONTRACTS.md`, `PHASE_5_6_7_CONTRACTS.md` first. Phases 0–6 are done.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §6, §11 (T1–T18), `docs/special_part_retroactive_edits_v0_2.md` §2, §3.6, §4, §5.

**Goal:** wire everything into `run_analysis(snapshot, trigger, now) -> ChangeSet`, add the activity-edit validation (T17), and prove the whole system with end-to-end scenarios and idempotency checks. After this phase the logic-only backend is complete.

## Files
```
services/__init__.py                (follow repo convention)
services/run_analysis.py
services/activity_edit.py
tests/support/scenario_driver.py
tests/test_activity_edit.py
tests/test_run_analysis.py
tests/scenarios/test_scenarios_core.py        (T1–T18)
tests/scenarios/test_scenarios_text.py        (Cases 1–3 end to end)
tests/scenarios/test_scenarios_invariants.py  (idempotency, determinism, long run, timezones, stale data)
docs/TEST_MAP.md                              (T1…T18 -> test function names)
docs/ADAPTER_NOTES.md                         (what a future DB adapter must do; short)
```
Do not change logic in Phases 2–6. If a scenario exposes a bug there, STOP, report it with a failing test, and ask.

## 1. `run_analysis` (`services/run_analysis.py`)

```python
def run_analysis(snapshot, trigger, now, cfg=DEFAULT_CONFIG, renderer=renderRecommendation) -> ChangeSet
runAnalysis = run_analysis
```
Fixed order, no I/O, nothing written:
1. `ValueError` if `trigger.kind == activityEvent` and `trigger.tFrom is None`.
2. `diag = runDiagnostic(snapshot, trigger, now, cfg)` for **every** trigger kind. (Phase 2 already limits cause re-evaluation by trigger kind; the episodes are needed by the DO prediction anyway.)
3. `detectorSignal = detectPhSwing(views, pond, now, cfg)` **only when `trigger.kind == reading`**. (The detector never closes; a recommendation lives until `validUntil`.)
4. `doEpisodes = tuple(e for e in diag.episodes if e.parameter == PondParameters.DO)`; `predChanges = runPredictions(snapshot, now, cfg, doEpisodes)`.
5. Signals = `diagnosticSignals(diag.allDiagnostics)` + `predictionSignals(all predictions)` + detector signal if any, where "all predictions" = snapshot predictions overlaid with `predChanges` by id.
6. `rec = reconcile(snapshot, signals, now, trigger, renderer, cfg)`.
7. `predictionEnded` notifications: for each prediction in `predChanges` that is `ended` and was `active` (or absent) in the snapshot: kind `predictionEnded`, `targetType="prediction"`, `reasonKey="prediction."+"ended."+endReason`, facts `predictionId, ruleId, endReason`.
8. Fill `activityType` in `recChanged / rec.changed.activity_edit` notifications: if exactly one activity in the snapshot has `startTime == trigger.tFrom`, use its type; otherwise leave `None` (a deleted activity is no longer in the snapshot; accepted limitation, text falls back to "an activity").
9. Return `ChangeSet(diagnostics=diag.diagnostics, predictions=predChanges, recommendations=rec.recommendations, activityOps=(), notifications=prediction notifications + rec.notifications)`. Everything is already "changed only"; assert in a test that no object equals its snapshot version.

Stale data (Rule 11, T9): no special-casing in the orchestrator; Phases 2–5 already skip. Test it end to end (§4).
Empty history: no early return (activity-based predictions need no readings).

## 2. Activity edit rules (`services/activity_edit.py`), O8 and special part §3.6

```python
@dataclass(frozen=True)
class EditCheck:
    ok: bool
    reason: str | None        # machine id

validateActivityEdit(before: Activity | None, after: Activity | None, now, cfg=DEFAULT_CONFIG) -> EditCheck
triggerForEdit(before, after) -> Trigger                     # Trigger(activityEvent, tFrom)
triggerForEdits(edits: Sequence[tuple[Activity|None, Activity|None]], now, cfg) -> Trigger | None
pondEditTrigger(before: PondInfo, after: PondInfo, now) -> Trigger | None
```
- `floor = now − retroWindowDays days`. Any involved `startTime` (before and/or after) `< floor` → `outside_retro_window` (T17: add, edit and delete). Times in the future are always allowed.
- Create (`before is None`): `after.source` must be `user` (`invalid_source`); any status allowed (retro add, may be `done`).
- Delete (`after is None`): recommendation-origin → `recommendation_activity_not_deletable` (the user skips it instead); user `done` and user `pending` → ok; user `skipped` → ok (★ default, flagged).
- Update: `done → pending` or `skipped → pending` → `status_rollback`; `done ↔ skipped` is allowed (★ default); changing `id`, `pondId`, `source`, `sourceRecId` or `createdAt` → `immutable_field`; time/detail/type edits are ok (editing a recommendation-origin activity's time/details is allowed).
- `tFrom`: create = `after.startTime`; delete = `before.startTime`; update = `min(before.startTime, after.startTime)`; status save = the activity's `startTime`.
- **Batch Save is one event:** `triggerForEdits` validates every edit; if any fails → `None` (all-or-nothing, ★ default); otherwise one `Trigger(activityEvent, tFrom=min)`.
- `pondEditTrigger`: `Trigger(pondEdit, tFrom=now)` if `avgWeightG`, `fishCount` or `biomassKg` changed, else `None`. Other fields (timezone, name) do not trigger.
These functions are pure and never touch the snapshot.

## 3. Scenario driver (`tests/support/scenario_driver.py`)
A small class around `StoreSim` + `run_analysis`:
- `addReadings(parameter, rows)` rows like `("2025-06-01 20:00", value, zone, severity, direction)` in local time (uses `makeView`, `t(...)`).
- `addActivity(...)`, `editActivity(id, **changes, now)` (runs `validateActivityEdit`, applies, builds the trigger, runs analysis), `deleteActivity(id, now)`.
- `run(trigger, now)` runs `run_analysis`, applies the ChangeSet with `StoreSim`, **then runs the same trigger and `now` again and asserts the second ChangeSet is empty** (idempotency on every step). Returns the first ChangeSet.
- `applyRec(recId, now, chosenTime=None, confirmed=False)` calls `buildApplyPlan`, applies its ChangeSet, then runs a `Trigger(activityEvent, tFrom=<the created activity's start>)` analysis. `skipActivity(id, now)`, `dismiss(recId, now)`, `snooze(...)`.
- Uses the real renderer from Phase 6. Keep it under ~150 lines.

## 4. Scenario tests (write first; Asia/Bangkok, biomass 400 kg unless stated)

**test_scenarios_core.py** — one test per case, each named `test_T<n>_...`; the T-numbers map to the spec table, with the updates in contracts §4:
- **T1/T1b** (`Diagnostic` end to end, through the orchestrator): causes `[DO_C_FEED, DO_C_NIGHT]` and, with 31 °C, `[DO_C_FEED, DO_C_TEMP]`.
- **T2** Case 2: now 16:30, planned feeding 8.0 kg 19:00, Temperature 31 °C: prediction active (3 of 3), `AERATE` urgent, plan 19:00→06:00, `validFrom 16:30`, `validUntil 21:00`; one `urgentRecCreated` notification. (The spec's T2 line says "18:00–21:00"; Case 2 and the config give 19:00–21:00; keep Case 2 and note it in Deviations.)
- **T3** apply at 19:10: activity 19:10→06:00, rec `applied`, prediction ended `mitigated` after the follow-up run, `predictionEnded` notification.
- **T4** meal edited to 3.0 kg before apply: prediction ended `conditions_gone`, rec `expired / no_longer_applies`; notifications `predictionEnded` and `recExpired` with `afterActivityEdit=True`.
- **T5** apply, then `skipped` the aeration: prediction returns, `blocked()` false, a **new** AERATE rec (new id) is created.
- **T6** full: DO episode onset 20:00 with causes `[DO_C_NIGHT]`; at 20:45 a done feeding 18:30 is added: causes become `[DO_C_FEED, DO_C_NIGHT]`, `revisedAt` set; an episode with onset before 18:30 is untouched; a prediction/rec that depended on the missing feeding is reconciled.
- **T7** pH swing ≥ 1.0 on 2 of 3 complete days (reading trigger): `ADD_ALKALINITY` non_urgent, 3-day window, no quantity; next day the swing is gone: rec stays until `validUntil`, then `expired / time_window_over`.
- **T8** NH3 ElevatedRisk → non_urgent `WATER_CHANGE`; user snoozes; NH3 reaches Critical: same id, urgent, un-snoozed, notifications `recChanged(urgency_raised)` + `recUnsnoozed`; deadline `now + 3 h`.
- **T9** readings stop (newest > 3×Δ old): no new diagnostic, no detector signal, existing urgent rec kept; a rec past `validUntil` still expires; a prediction window past `riskEnd` still ends.
- **T10** urgent AERATE declined: same night, no new rec; then a Critical DO reading after the decline: a new rec is allowed.
- **T11** `PRED_DO_REPEAT` (2 of last 3 nights with DO episodes ≥ ElevatedRisk, now 15:00, no aeration) → urgent AERATE fixed time.
- **T12** Case 3: `PRED_NH3_RISE` → non_urgent `WATER_CHANGE`, user picks a time in the window; a time outside the window is rejected.
- **T13** non_urgent apply with a time after `validUntil` → rejected; exactly at `validUntil` → accepted.
- **T14 (updated)**: urgent aeration apply with an existing user `pending` 22:00–02:00 inside R → user activity deleted, R created whole, `activityReplaced` notification, and the summary text; with an existing user **done** 22:00–02:00 → two created pieces and the done activity untouched. Plus the D15 example (user pending 21:00–23:00, R 22:00–03:00 → 21:00–22:00).
- **T15** add a done water_change 3 h ago while `PRED_NH3_RISE` is active → prediction ended `mitigated`.
- **T16** delete that water_change (inside 4 days and inside 48 h): prediction fires again as a **new** prediction (new id) if C1 and C2 still hold; the related recommendation logic follows.
- **T17** add/edit/delete an activity older than 4 days → rejected by `validateActivityEdit`; exactly at the 4-day floor → ok; future activities always ok.
- **T18** shorten an applied pending aeration: no new rec (still blocked), but the prediction (C3 true again) comes back and shows the risk.

**test_scenarios_text.py**: Cases 1, 2, 3 from raw readings/activities through `run_analysis` to the final rendered text (`renderDiagnostic`, `renderPrediction`, `renderRecommendation`, `renderPlan`), compared with the golden text of §9.

**test_scenarios_invariants.py**
1. **Idempotency:** every `driver.run` already asserts it. Add an explicit test: take the Case 2 snapshot, `run`, apply, `run` again with the same arguments → `ChangeSet.isEmpty()`. Also after each user action (apply, skip, dismiss, snooze).
2. **Determinism:** the same snapshot/trigger/now twice → equal ChangeSets (same order, same ids). Inputs are not mutated (deep-compare the snapshot before and after).
3. **Long run:** 8 days of synthetic 30-minute readings and ticks with a few activity edits, a feeding pattern that causes DO episodes, one NH3 episode, a pH swing, two user actions. Invariants after every step: ids unique per object type; at most one open (`pending`/`snoozed`) rec per `dedupeKey`; `applied`/`dismissed`/`expired` recs never change again; no ChangeSet object equals its snapshot version; no exception; `ChangeSet` empty when nothing changed between two consecutive ticks with no new data **except** time-driven updates (e.g. `PRED_NH3_RISE.riskEnd` moving while it fires).
4. **Timezones:** the same story in `Asia/Bangkok` and `America/New_York` (shift the UTC instants so local clock times match): same structural outcome (causes, rules fired, rec entries/urgencies, local plan times), different UTC instants. One scenario runs at local 02:00 to cover the night that started on the previous date.
5. **Rule 5:** DO episode at night with **no activities at all** → only `DO_C_NIGHT`, text says "No aeration was logged tonight."; no prediction/recommendation concludes "not fed"/"not aerated" from absence.
6. **Retro honesty:** severity views are never changed by any ChangeSet; an applied rec's activities are never modified by reconcile (only by `buildApplyPlan` D15 rules).
7. **O3:** a rec with prediction + episode sources: closing one source keeps it; closing both expires it; a detector-only rec is never closed by source.
8. `pondEdit` trigger: changing `avgWeightG` re-evaluates predictions (meal % changes) and does **not** touch old diagnostics (`revisedAt` unchanged).

**test_run_analysis.py / test_activity_edit.py:** unit tests for pipeline order (mock-free: assert on results), `activityEvent` without `tFrom` → `ValueError`, detector runs only on `reading`, `predictionEnded` notifications only for newly ended predictions, `activityType` fill (one match / no match / two matches), and every `validateActivityEdit` branch including boundaries (`floor` exactly, `floor − 1 s`), batch all-or-nothing, `pondEditTrigger` for each field.

## 5. Docs
- `docs/TEST_MAP.md`: a table T1…T18 + Cases 1–3 → test function names.
- `docs/ADAPTER_NOTES.md` (≤ 1 page): the adapter loads a `PondSnapshot` with ≥ `historyHorizonDays` of readings and all non-final objects, calls `run_analysis`, then persists the ChangeSet in one transaction (upserts by id; `activityOps` create/update/delete; notifications to an outbox), and for user actions calls `validateActivityEdit` + `triggerForEdit(s)` (activities), `buildApplyPlan`/`snoozeRec`/`dismissRec` (recommendations), `pondEditTrigger` (pond). The adapter serializes work per pond and merges overlapping triggers with the lowest `tFrom`.
- `docs/BACKLOG.md`: add the items from contracts §6 and the ★ defaults of this phase.

## 6. Definition of Done
- [ ] All new tests pass; **all** tests from Phases 0–6 still pass; `pytest -q` total reported
- [ ] T1–T18 and Cases 1–3 each map to a passing test in `docs/TEST_MAP.md`
- [ ] Every `driver.run` step proves idempotency
- [ ] Long-run invariants hold
- [ ] No `datetime.now()` anywhere in `config/`, `identity/analysis|diagnostic|prediction|recommendation|text/`, `services/`
- [ ] No new dependency; Python 3.11-compatible syntax only
- [ ] `docs/PROGRESS.md` final row; `docs/BACKLOG.md` and `docs/ADAPTER_NOTES.md` written
- [ ] A short "Spec vs implementation" list in the final message: every place where the code differs from the Thai spec (T2 window, T14, `blocked` ★, urgency never lowered, detector only on `reading`, etc.)

## Out of scope
Database, ORM, queue, HTTP, real push, Thai text, kNN, severity-engine changes, new catalog entries, UI.

## Questions to raise if hit
A scenario that cannot pass without changing a Phase 2–6 rule; any ★ default the owner may want reversed (skipped deletable, `done ↔ skipped`, batch all-or-nothing, detector only on `reading`).
