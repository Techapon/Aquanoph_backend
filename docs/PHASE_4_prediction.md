# PHASE 4 — Prediction (3 rules + lifecycle runner)

Read `AGENT_CONTEXT.md` and `PHASE_2_3_4_CONTRACTS.md` first. Phases 0–3 are done.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §4 (rules, lifecycle), test cases T4, T9, T11, T12, T15, T16 (prediction parts) and Case 2/3 numbers in §9.
`PRED_DO_REPEAT` uses `Episode`, `buildEpisodes`, `qualifies` from `identity/diagnostic/episode.py` (Phase 2). Import them; do not copy them. Suggested order inside this phase: `PRED_DO_NIGHT`, `PRED_NH3_RISE`, `PRED_DO_REPEAT`, then the runner.

**Goal:** from a snapshot and `now`, decide which predictions are active, updated or ended. Pure logic, no recommendation.

## Files
```
identity/prediction/__init__.py
identity/prediction/rules/__init__.py, _common.py, do_night.py, do_repeat.py, nh3_rise.py
identity/prediction/runner.py
identity/analysis/helpers.py          (append-only: totalMealPct)
tests/support/pred_builders.py
tests/test_helpers.py            (append tests for totalMealPct)
tests/test_pred_do_night.py, test_pred_do_repeat.py, test_pred_nh3_rise.py, test_prediction_runner.py
```

## 0. Helper to add to `helpers.py` (append only)
`totalMealPct(acts, pond, fromT, toT) -> float`: sum of `mealPct` over `done` feedings with `startTime` in `[fromT, toT)`; feedings with `quantityKg=None` are skipped (unknown, Rule 5). Also return the count of skipped ones via a second function or a tuple-returning variant `totalMealPctDetail(...) -> (pct, unknownCount)`. Add its tests to `tests/test_helpers.py` (append only).
(Note: `NH3` C1 is a **rolling 24 h** sum, not a local-calendar-day sum.)

## 1. Shared pieces

```python
@dataclass(frozen=True)
class PredictionContext:
    pond: PondInfo; views: tuple[SeverityReportView, ...]; activities: tuple[Activity, ...]
    doEpisodes: tuple[Episode, ...]; active: Prediction | None   # active prediction of THIS rule, if any
    now: datetime; cfg: AnalysisConfig

@dataclass(frozen=True)
class RuleResult:
    skip: bool            # not enough data: change nothing
    fire: bool
    reason: str | None    # when not fire: "mitigated" | "conditions_gone"
    met: tuple[str, ...]  # condition ids that are true, e.g. ("C1","C2","C3"), in order
    scope: str | None
    riskStart: datetime | None; riskEnd: datetime | None
    evidence: Mapping[str, Any]   # structured facts; must include "conditions": {"C1": bool, ...} for ALL conditions, incl. optional
```
Each rule module exposes `RULE_ID` and `evaluate(ctx) -> RuleResult`. `_common.py` holds private helpers: "temperature High and zone ≠ Optimal within window" lookup, `nightWindowForDate(nightDate, tz, cfg)` (use `nightWindowFor` on local noon of that date), evening test, etc.

Boundary convention: see CONTRACTS §4 (prediction lookbacks inclusive of `now`). Lookback/lookahead lengths come from `cfg`. Time-of-day tests go through `localTime`/`inLocalWindow`/`nightWindowFor`.

Common field values: `parameter` = DO for the two DO rules, NH3 for `PRED_NH3_RISE`; `expectedZone = ThresholdLevelType.HighRisk`.

## 2. `PRED_DO_NIGHT` (`do_night.py`)

| | definition | type |
|---|---|---|
| C1 heavy evening meal | a feeding that is `done` in `[now − feedLookbackPredHours, now]` **or** `pending` in `[now, now + feedLookaheadPredHours]`, with local start time hour ≥ `eveningFromHour`, and `mealPct ≥ heavyMealPct` | must |
| C2 hot weather | Temperature view with zone ≠ Optimal and direction High at the latest fresh reading or within `tempHighLookbackPredHours` before `now` | optional |
| C3 not enough aeration | `aerationHours(riskStart, riskEnd) < minAerationHours` | must |

- `firstMeal` = the earliest qualifying C1 meal. `anchor = ctx.active.createdAt if ctx.active else now`.
- `riskStart = max(anchor, firstMeal.startTime + riskStartAfterMealHours)`; `nw = nightWindowFor(riskStart)`; `riskEnd = nw.end`; `scope = nw.nightDate.isoformat()`.
  (Decision: the anchor keeps `riskStart` stable across ticks, so the prediction is not rewritten every 30 minutes and Phase 5 deadlines do not drift. For a new prediction this equals the spec's `max(now, …)`.)
- `fire = C1 and C3`. `C1 and not C3` → `reason="mitigated"`. `not C1` → `reason="conditions_gone"` (covers T4: meal reduced below 1.0 %).
- Evidence: `firstMealTime, firstMealKg, firstMealPct, mealCount, aerationHours, tempValue/tempZone if C2`, plus `conditions`.
- Never skip (needs no sensor data).

## 3. `PRED_DO_REPEAT` (`do_repeat.py`)

| | definition | type |
|---|---|---|
| C1 repeated | among the `repeatWindowNights` (3) most recent **completed** nights before tonight, at least `repeatMinNights` (2) have a DO episode with `qualifies`, `severityRank(peakSeverity) ≥ severityRank(SeverityLevelType[cfg.repeatSeverity])` and `onsetAt` inside that night window. Several episodes in one night count once. | must |
| C2 not yet risk time | `localTime(now).hour ≥ predictFromHour` and `now < riskStart` | must |
| C3 not enough aeration | `aerationHours(riskStart, riskEnd) < minAerationHours` | must |
| C4 hot weather | Temperature zone ≠ Optimal High now | optional |

- Tonight = `nightWindowFor(now)` (valid because C2 needs local hour ≥ 12). "Completed nights" = nights with `nightDate` = tonight − 1, −2, −3 days, built with `nightWindowForDate`.
- `riskStart = tonight.start + min(offset)` where `offset = onsetAt − thatNight.start` for the earliest hit episode of each hit night (take the smallest across hit nights). `riskEnd = tonight.end`; `scope = tonight.nightDate.isoformat()`.
- `fire = C1 and C2 and C3`.
  - `C1 and C2 and not C3` → `reason="mitigated"`.
  - `not C1` → `reason="conditions_gone"`.
  - **`C1 and not C2` → `skip=True`** (decision: once the risk time has begun, the Diagnostic takes over; an already-active prediction is left to run to `window_over`; a new one is not created).
- Evidence: `hitNights` (list of nightDates), `nightsChecked`, `earliestOffsetMinutes`, `aerationHours`, plus `conditions`.
- Input `ctx.doEpisodes` is already computed (see runner).

## 4. `PRED_NH3_RISE` (`nh3_rise.py`)

| | definition | type |
|---|---|---|
| C1 heavy feeding | `totalMealPct(done feedings, [now − 24 h, now]) ≥ dailyHeavyPct` | must |
| C2 NH₃ abnormal | the latest NH3 view is fresh (`zoneAt`) and its zone ≠ Optimal | must |
| C3 no water change | no `done` water_change in `[now − wcLookbackHours, now]` **and** no `pending` water_change in `[now, now + wcLookaheadHours]` | must |
| C4 hot weather | Temperature zone ≠ Optimal High now | optional |

- If the latest NH3 view is missing or stale (`zoneAt` returns None) → `skip=True` (keep state).
- `riskStart = anchor` (same anchor rule as DO_NIGHT); `riskEnd = now + nh3RiseHorizonHours` (moves forward every run while firing); `scope=None`; only one active at a time.
- `fire = C1 and C2 and C3`. `C1 and C2 and not C3` → `"mitigated"`. `not C2` or `not C1` → `"conditions_gone"`.
- Evidence: `totalMealPct, unknownQtyCount, nh3Zone, nh3Value, nh3Time, lastWaterChange*, plannedWaterChange*`, plus `conditions`.

## 5. `runner.py`

```python
runPredictions(snapshot, now, cfg=DEFAULT_CONFIG, doEpisodes=None) -> tuple[Prediction, ...]   # changed only
predictionSignals(predictions) -> tuple[Signal, ...]                                           # contract CONTRACTS §3.2
```
`doEpisodes=None` → `buildEpisodes(DO views, DO)`; the orchestrator will pass Phase 2's list instead.

Algorithm (deterministic order: `PRED_DO_NIGHT`, `PRED_DO_REPEAT`, `PRED_NH3_RISE`):
1. `window_over` first: every active prediction with `now > riskEnd` → ended, `endReason="window_over"`, `revisedAt=now`. (Decision: done before the rules, so a stale old window cannot be "refreshed" by a rule.)
2. For each rule, `active` = the active prediction of that rule (after step 1). Evaluate.
   - `skip` → nothing for that rule.
   - `fire`:
     - no active → create: `createdAt=now`, `id=predId(pondId, ruleId, scope, now)`, `status=active`, `revisedAt=None`.
     - active with the same `scope` → update `riskStart, riskEnd, met, evidence, pondSnapshot` (pondSnapshot = current pond info). Build the candidate with the old `revisedAt`; if it equals the stored object, it is unchanged and **not** emitted; otherwise emit it with `revisedAt=now`. Keep `id` and `createdAt`.
     - active with a different `scope` → end the old one (`"conditions_gone"`) and create the new one.
   - not `fire` and an active exists → end it with `result.reason`, `revisedAt=now`.
   - not `fire` and no active → nothing.
3. Ended predictions are never re-evaluated or reopened later. A condition that returns later creates a **new** prediction (new `createdAt` → new id), as in T5/T16.
4. Result = `changedOnly(...)` against `snapshot.predictions`, so a snapshot that already holds the result gives `()` (Rule 7).
5. Stale data (Rule 11): handled per rule through `skip`. Missing readings never end a prediction by themselves, except `window_over` by time.

`met` for display = the true condition ids; the full true/false map is in `evidence["conditions"]` (needed for "2/3" style display later).

## 6. Tests (write first; Asia/Bangkok, biomass 400 kg, use `t("...")`)

**test_pred_do_night.py**
1. **Case 2 (T2 prediction part):** now 16:30, pending feeding 8.0 kg at 19:00 (2.0 %), no aeration, Temperature 31 °C High → fires, `met == ("C1","C2","C3")`, `riskStart=20:00`, `riskEnd=06:00` next day, `scope` = tonight's date, `expectedZone=HighRisk`.
2. Same without hot weather → fires with `met == ("C1","C3")`, C2 false in evidence.
3. Meal 3.0 kg (0.75 %) → C1 false → not fire; with an active prediction → `conditions_gone` (**T4**).
4. Meal exactly 1.0 % fires; 0.99 % does not. Meal at local 15:59 does not count; 16:00 counts.
5. Aeration planned 18:30–06:00 → C3 false → active prediction ends `mitigated`; aeration of exactly 3.0 h inside the window is "enough"; 2.9 h is not. A `skipped` aeration does not count; `pending` and `done` do.
6. Done meal 6 h ago counts, 6 h + 1 s does not. Pending meal 8 h ahead counts, beyond does not. A feeding with `quantityKg=None` cannot be heavy (unknown) and is reported in evidence, not treated as zero-risk proof.
7. `riskStart` after meal + 1 h: now 21:00, done meal 18:30 → `riskStart = 21:00` for a new prediction; for an existing active one `riskStart` stays at the stored value on a later tick.
8. After midnight (now 02:00, done meal 21:00) → `scope` is the night that started yesterday.
9. Second timezone gives a different local-time result for the same UTC instant.

**test_pred_do_repeat.py**
1. **T11:** DO episodes with peak ≥ ElevatedRisk and onset at night on 2 of the last 3 nights; now 15:00; no aeration → fires; `riskStart` = tonight 18:00 + the smallest onset offset; `riskEnd` 06:00.
2. Only 1 of 3 nights → C1 false. Peak only Stress → does not count. Onset at 17:59 (not night) does not count. Two episodes in one night count once.
3. now 11:59 → C2 false (`skip`-or-not-fire per rule, no creation). now ≥ `riskStart` with C1 true → `skip`: an existing active prediction is **unchanged**.
4. Aeration planned for the whole night → `mitigated` when active.
5. Night-by-date works over a month boundary and with a second timezone.

**test_pred_nh3_rise.py**
1. **T12 (Case 3):** 14.4 kg fed within 24 h (3.6 %), NH3 zone Stress at a fresh reading, no water change → fires; `riskEnd = now + 12 h`, `scope None`.
2. 3.0 % exactly fires, 2.99 % does not. Feedings that are `pending` or `skipped` do not count toward C1.
3. Stale NH3 reading (older than 3 × 30 min) → `skip`, active prediction unchanged (**T9 prediction part**). NH3 zone Optimal → `conditions_gone`.
4. **T15:** a `done` water_change 3 h ago added while active → `mitigated`. A `pending` water_change within the next 24 h also mitigates. Done water_change 49 h ago does not.
5. **T16:** after the done water_change is removed (and it was inside 48 h), the next run creates a **new** prediction (different `createdAt`/id) if C1 and C2 still hold.
6. On each tick while firing `riskEnd` moves to `now + 12 h` and `revisedAt` is set; `riskStart` and `id` stay.

**test_prediction_runner.py**
1. Window over: `now > riskEnd` → ended `window_over`; an ended prediction is not touched again.
2. Different `scope` for the same rule → old ended, new created.
3. **Idempotency:** apply result with `StoreSim`, rerun with the same `now` → `()`. Rerun on the next tick (+30 min) changes only what should change (NH3 `riskEnd`).
4. Rules are independent: one firing does not affect another's state.
5. `doEpisodes=None` computes episodes from DO views and gives the same result as passing `buildEpisodes(...)` output.
6. `predictionSignals`: active → `active=True`, ended → `False`; fields as in the contract.
7. Input snapshot not mutated; output order deterministic.
8. (in `tests/test_helpers.py`) `totalMealPct`: sums done feedings only, half-open window, skips unknown quantity and reports the count.

## 7. Definition of Done
- [ ] All tests above pass; all old tests still pass
- [ ] Three rules + runner + `predictionSignals` implemented; `helpers.py` only appended to
- [ ] No magic numbers (everything from `cfg`), no `datetime.now()`, no raw `.hour/.date()`
- [ ] `PRED_DO_REPEAT` imports the real Phase 2 `episode.py` (no copy)
- [ ] Idempotent with `StoreSim`
- [ ] `docs/PROGRESS.md` row added; `docs/BACKLOG.md`: note duplicated "temperature High lookup" helper with Phase 2

## Out of scope
Recommendations (`AERATE`/`WATER_CHANGE` signals handling, reconcile, apply), text rendering, kNN, orchestrator, notifications for `predictionEnded` (Phase 7 decides from the ChangeSet).

## Accepted limitations (do not "fix")
- `PRED_DO_NIGHT` can end as `conditions_gone` after midnight when the meal leaves the 6 h lookback; the Diagnostic takes over from there.
- Shortening an applied aeration brings the prediction back (C3 true again) but creates no new recommendation (Phase 5, T18).
