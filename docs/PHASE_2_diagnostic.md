# PHASE 2 — Diagnostic (episodes, cause rules, runner)

Read `AGENT_CONTEXT.md` and `PHASE_2_3_4_CONTRACTS.md` first (run order, contracts, conventions). Phases 0 and 1 are done.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §3.1, §3.2, §3.4 and test cases T1, T1b, T6 (diagnostic part only).

**Goal:** turn severity history + activities into `DiagnosticReport`s with causes. Pure logic, no recommendation, no prediction.

Start with `episode.py` + `tests/test_episode.py` (the rest builds on it; Phase 4 will use it later).

## Files
```
identity/diagnostic/__init__.py
identity/diagnostic/episode.py
identity/diagnostic/cause_rules.py
identity/diagnostic/runner.py
tests/support/diag_builders.py
tests/test_episode.py, tests/test_cause_rules.py, tests/test_diagnostic_runner.py
```
Do not create `detectors/` (Phase 3).

## 1. `episode.py` (contract in PHASE_2_3_4_CONTRACTS.md §3.1)

`buildEpisodes(views, parameter)`:
1. Keep only `parameter`'s views, sort ascending by time (stable).
2. An episode is a continuous run of readings whose **zone** is not Optimal. Use `zone`, never `severity`, so Recovery Hold (zone Optimal, severity Stress) closes the episode and does not open a new one.
3. It **closes** at the first reading whose zone is Optimal: `endAt` = that reading's time, `status = closed`. It is open (`endAt=None`) if no such reading exists.
4. **Range thresholds (pH, Temperature):** a direction change between two consecutive non-Optimal readings (Low→High or High→Low) closes the old episode and opens a new one, both at that reading's time. Level thresholds have `direction=None` and never flip.
5. `peakSeverity` = max by `severityRank` over in-episode readings; `lastSeverity` = severity of the last in-episode reading (the closing Optimal-zone reading is **not** in-episode); `peakZone` = max by `zoneRank`; `readingCount` counts in-episode readings.
6. **A gap in the data does not close an episode.** Only an Optimal-zone reading closes it (Rule 5).
7. `qualifies(ep, cfg)`: `readingCount >= cfg.minEpisodeReadings` or `zoneRank(peakZone) >= zoneRank(HighRisk)`.

## 2. `cause_rules.py`

```python
@dataclass(frozen=True)
class CauseContext:
    pond: PondInfo; views: tuple[SeverityReportView, ...]; activities: tuple[Activity, ...]; cfg: AnalysisConfig

def evaluateCauses(parameter, direction, onsetAt, ctx) -> tuple[tuple[Cause, ...], bool]   # (causes, noClearCause)
```
- Use only data before or at `onsetAt` (`t0`), with the boundary convention in CONTRACTS §4: activities `[t0−X, t0)`, views `[t0−X, t0]`.
- Evaluate every rule that applies to `(parameter, direction)`, sort by priority ascending (ties: rule table order), keep the first `cfg.maxCauses`. If none match: `causes=()` and `noClearCause=True`.
- Each match is `Cause(ruleId, facts)`. Facts are structured (naive-UTC datetimes, numbers, bools). No prose.

| ruleId | applies to | condition at t0 | prio | facts |
|---|---|---|---|---|
| `DO_C_FEED` | DO | a `done` feeding in `[t0 − feedLookbackDoHours, t0)` | 1 | `feedTime, kg, mealPct, isHeavy, feedCount, totalKg, unknownQtyCount, hoursBeforeOnset` |
| `DO_C_TEMP` | DO | any Temperature view with zone ≠ Optimal and direction High in `[t0 − tempLookbackHours, t0]` | 2 | `tempValue, tempZone, tempTime, hoursBeforeOnset` (0 if at t0) |
| `DO_C_NIGHT` | DO | `isNight(t0)` | 3 | `nightDate, aerationLogged` |
| `NH3_C_FEED` | NH3 | a `done` feeding in `[t0 − feedLookbackNh3Hours, t0)` | 1 | same as `DO_C_FEED` |
| `NO2_C_NH3` | NO2_N | any NH3 view with zone ≠ Optimal in `[t0 − nh3ChainLookbackHours, t0]` | 1 | `nh3PeakZone, nh3FirstTime, nh3LastTime` |
| `TEMP_C_TIME` | Temperature | direction High and `inLocalWindow(t0, tz, *tempHighWindow)`, or direction Low and `inLocalWindow(t0, tz, *tempLowWindow)` | 1 | `direction, onsetLocal` |
| `PH_C_TIME` | pH | direction High and `phHighWindow`, or Low and `phLowWindow` | 1 | `direction, onsetLocal` |
| `SAL_C_WATERCHG` | salinity | a `done` water_change in `[t0 − salWaterChangeLookbackHours, t0)` | 1 | `waterChangeTime, fraction, hoursBeforeOnset` |

Decisions (author; keep unless a test proves them wrong):
- **Which feeding is the headline** when several are in the window: the one with the highest `mealPct` (tie: the latest). `isHeavy = mealPct >= cfg.heavyMealPct`. `totalKg` sums feedings with a known quantity. A feeding with `quantityKg=None` still counts as positive evidence (it matches the rule) but is excluded from the headline, from `totalKg`, and counted in `unknownQtyCount`. If **all** feedings in the window have unknown quantity: match, with `kg=None, mealPct=None, isHeavy=False`.
- `aerationLogged` (DO_C_NIGHT) = there is a non-skipped (`done` or `pending`) aeration with `start <= t0 < end`. It is evidence of "logged", never "not aerated".
- `onsetLocal` = `localTime(t0, tz).isoformat()` (deterministic string); this is the only string-typed time in facts.
- A direction-less episode never matches `TEMP_C_TIME` / `PH_C_TIME`.
- Rule 11 for causes: a view is evidence only if it exists; do not apply staleness inside cause rules (the history is already a fact).

## 3. `runner.py`

```python
runDiagnostic(snapshot, trigger, now, cfg=DEFAULT_CONFIG) -> DiagnosticResult
diagnosticSignals(reports) -> tuple[Signal, ...]        # contract CONTRACTS §3.2
```
For each parameter: `buildEpisodes` → for each qualifying episode (`qualifies`):
1. `id = diagId(pondId, parameter, direction, onsetAt)`. Look up the existing report in `snapshot.diagnostics` by id.
2. **New** report: `pondSnapshot = snapshot.pond` info, causes evaluated at `onsetAt` with the current pond, `revisedAt=None`, `status/peak/last/endAt` from the episode.
3. **Existing** report: update `endAt, status, peakSeverity, lastSeverity` from the episode. Re-evaluate causes only when `trigger.kind == activityEvent` and `trigger.tFrom is not None` and `ep.onsetAt >= trigger.tFrom` (an activity at time t can only affect what happens at or after t). Re-evaluation uses the report's **own stored `pondSnapshot`** (old diagnostics are not touched by pond edits). If the new causes or `noClearCause` differ from the stored ones: replace them and set `revisedAt = now`. If they are equal: leave `revisedAt` unchanged.
4. Trigger kinds `reading`, `tick`, `pondEdit`: never re-evaluate causes of existing reports.
5. **Stale gate (Rule 11, T9):** if the parameter's newest view is stale at `now` (`isStale`), do **not create new reports** for it. Existing reports still update from the episode facts and may still get cause revisions (step 3), because those use past facts.
6. Result: `allDiagnostics` = the resulting report for every qualifying episode found; `diagnostics = changedOnly(allDiagnostics, existingById)`; `episodes` = all episodes of all parameters (qualifying or not), ascending by onsetAt then parameter order.
7. Output must be deterministic (stable ordering of reports and of causes). Running again on a snapshot that already holds the result must return `diagnostics == ()`.

`diagnosticSignals`: one Signal per report as in the contract; no filtering (Phase 5 decides what it needs).

## 4. Tests (write first)

**test_episode.py**
1. Single non-Optimal reading (Stress) → episode exists but `qualifies` False; single HighRisk or Critical reading → `qualifies` True; two Stress readings → True.
2. Recovery Hold: readings Stress-zone, then Optimal-zone with Stress severity → episode closes at the Optimal reading; `lastSeverity` is the last in-episode one; no new episode opens.
3. pH direction flip Low→High on consecutive readings → two episodes, first closed at the flip time, second open from that time. Level threshold (DO) never flips.
4. Open episode: `endAt None`, `status open`.
5. Two parameters interleaved in the input → `buildEpisodes(views, DO)` ignores the other.
6. Unsorted input and equal timestamps → ascending, stable.
7. Gap: two readings 3 h apart both non-Optimal → still one episode.
8. Empty input → `()`.
9. `peakSeverity` / `peakZone` take the max, not the last.

**test_cause_rules.py** (Asia/Bangkok, biomass 400 kg)
1. **T1:** feeding 6.0 kg done 18:30, DO onset 20:00, Temperature 29 °C Optimal, no aeration → causes `[DO_C_FEED, DO_C_NIGHT]`; facts `kg=6.0, mealPct=1.5, isHeavy=True`, `aerationLogged=False`; `noClearCause=False`.
2. **T1b:** same but Temperature 31 °C (Stress, High) in the 3 h before → all three match, result `[DO_C_FEED, DO_C_TEMP]` (`DO_C_NIGHT` dropped by `maxCauses=2`).
3. Each of the 8 rules: one positive case and one negative case.
4. Boundaries: feeding exactly `t0 − 6 h` matches; exactly `t0` does not; `t0 − 6 h − 1 s` does not. Same style for NH3 12 h, NO2 24 h (views inclusive at `t0`), temp 3 h, salinity 6 h.
5. `pending` and `skipped` feedings do not match; a feeding with `quantityKg=None` matches with `isHeavy=False`.
6. `DO_C_NIGHT` boundaries: local 17:59 no, 18:00 yes, 05:59 yes, 06:00 no. Second timezone (`America/New_York`) gives a different answer for the same UTC instant.
7. `aerationLogged` True when a pending aeration covers `t0`; skipped aeration does not count.
8. `TEMP_C_TIME`/`PH_C_TIME` windows incl. the wrapping Low window (22,6); wrong direction does not match.
9. Headline-meal choice with several feedings; heavy vs not heavy at exactly 1.0 %.
10. No match → `causes=()`, `noClearCause=True`.
11. Absence of any activity record never produces a cause (Rule 5): DO episode at night with no activities → only `DO_C_NIGHT`.

**test_diagnostic_runner.py**
1. New qualifying episode → report created with correct fields, deterministic id, `revisedAt=None`.
2. Report not created while the episode is still 1 Stress reading; created when the second arrives.
3. Open → closed update changes `endAt/status`, leaves causes untouched on `reading` trigger.
4. **T6 (diagnostic part):** snapshot holds a report for a DO episode with onset 20:00 and `causes=[DO_C_NIGHT]`; now = 20:45; a `done` feeding 18:30 is added; `Trigger(activityEvent, tFrom=18:30)` → causes become `[DO_C_FEED, DO_C_NIGHT]`, `revisedAt=now`.
5. Episode with `onsetAt < tFrom` is not re-evaluated; `reading`/`tick`/`pondEdit` triggers never re-evaluate.
6. Deleting that feeding (trigger with `tFrom` = its time) → causes revert, `revisedAt=now`. Missing activity is "unknown", so only positive-evidence rules remain.
7. Re-evaluation uses the stored `pondSnapshot`: change the pond biomass in the snapshot, `activityEvent` → `mealPct` still computed with the old biomass.
8. **Idempotency:** apply `diagnostics` with `StoreSim`, run again with the same trigger and `now` → `diagnostics == ()`. Same with `Trigger(activityEvent)`.
9. **Stale gate (T9):** newest DO view older than `staleFactor × expectedIntervalMinutes` → no new report for DO; existing report unchanged. Other parameters still processed.
10. Direction in the id: pH Low and pH High episodes get different ids; a Level parameter uses `-`.
11. `allDiagnostics` includes unchanged reports; `episodes` includes non-qualifying ones.
12. `diagnosticSignals`: open → `active=True`, closed → `active=False`; fields as in the contract.
13. Input snapshot is not mutated.

## 5. Definition of Done
- [ ] All tests above pass; all old tests still pass
- [ ] Every rule in the table implemented with the stated facts; no prose, no `datetime.now()`, no raw `.hour/.date()`
- [ ] `runDiagnostic` returns only changed reports and is idempotent (verified with `StoreSim`)
- [ ] `docs/PROGRESS.md` row added; `docs/BACKLOG.md`: append "episode onset is left-censored when the history horizon starts inside an episode (id would change as the horizon slides)"

## Out of scope
Detector (Phase 3), predictions (Phase 4), recommendations, text rendering, orchestrator, retro-window rejection (T17, Phase 7).

## Questions to raise if hit (do not guess beyond the defaults above)
Anything in the spec that contradicts a decision in this file; any rule whose fact cannot be derived from `PondSnapshot`.
