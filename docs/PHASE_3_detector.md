# PHASE 3 — Detector `PH_SWING`

Read `AGENT_CONTEXT.md` and `PHASE_2_3_4_CONTRACTS.md` first. Phases 0, 1 and 2 are done. This phase does not use Phase 2 code.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §3.3, T7 (detector part only), T9 (detector part).

**Goal:** a pure function that looks at the last complete local days of pH readings and returns a `Signal` when pH swings too much on enough days. The detector stores nothing; it is recomputed every run.

## Files
```
identity/diagnostic/detectors/__init__.py
identity/diagnostic/detectors/ph_swing.py
identity/analysis/helpers.py      (append-only: localDayBounds)
tests/test_helpers.py            (append tests for localDayBounds)
tests/test_ph_swing.py
```
Needs the measured `value` on `SeverityReportView` (F-01, already fixed). Do not touch any other file.

## Rule
```
for the phSwingWindowDays (3) most recent COMPLETE local days:
    day "hits" if (max(pH) - min(pH)) >= phSwingMin (1.0)  and  coverage >= phSwingCoverage (0.70)
    coverage = readingCount / expectedReadings
if number of hit days >= phSwingHitDays (2): return Signal, else None
```

## Interface
```python
def detectPhSwing(views: Iterable[SeverityReportView], pond: PondInfo, now: datetime,
                  cfg: AnalysisConfig = DEFAULT_CONFIG) -> Signal | None
```
Signal: `sourceType=detector`, `sourceId=f"PH_SWING:{pond.pondId}"` (stable, so Phase 5 can merge sources across runs), `code="PH_SWING"`, `parameter=PondParameters.pH`, `active=True`, `riskStart=None`, `riskEnd=None`, `peakSeverity=None`, `lastSeverity=None`, `scope=None`.
`facts` (structured, deterministic): `{"hitDays": int, "windowDays": int, "days": tuple[{"date": date, "swing": float, "coverage": float, "readingCount": int, "hit": bool}, ...]}` ordered oldest → newest.

## Details (decisions by the author)
1. Use only pH views (`parameter == pH`); ignore all others. Sort ascending; input order must not matter.
2. **Complete local day** = a local date strictly before `localDate(now, pond.timezone)`. Today is never included, even if it already has a large swing. The window is the 3 dates `today−1, today−2, today−3`.
3. A reading belongs to a day by **local date** (`pond.timezone`), not UTC date. Day bounds are `[local 00:00, next local 00:00)` converted to naive UTC. Add `localDayBounds(d: date, tz) -> (start, end)` to `helpers.py` (append-only; it may use `zoneinfo` inside that one function and must convert through `toUtcNaive`). Add its tests to `tests/test_helpers.py`: Bangkok 24 h day, a DST day in `America/New_York` (23 h and 25 h), result is naive UTC.
4. `expectedReadings = dayLengthMinutes / cfg.expectedIntervalMinutes` where `dayLengthMinutes` is the **actual** length of that local day (so a DST day of 23 or 25 h is handled; Bangkok is always 24 h = 48 readings). `coverage = readingCount / expectedReadings` (not capped).
5. Compare with a small tolerance so floating-point does not decide: `round(max - min, 6) >= cfg.phSwingMin` and `round(coverage, 6) >= cfg.phSwingCoverage`. A day with 0 readings: swing 0, coverage 0, not a hit. A day with 1 reading: swing 0.
6. **Stale gate (Rule 11, T9):** if there are no pH views, or the newest pH view is stale at `now` (`isStale`), return `None`. No new signal from stale data.
7. Return `None` when `hitDays < cfg.phSwingHitDays`. (Whether an existing `ADD_ALKALINITY` recommendation survives is Phase 5's job; here a "swing gone" simply gives `None`.)
8. Pure, deterministic, no mutation of inputs, no `datetime.now()`.

## Tests (write first; build views with `makeView`, read times in local time with `t(...)`)
1. 2 of 3 days hit → Signal with `hitDays=2`; 3 of 3 → Signal; 1 of 3 → `None`; 0 → `None`.
2. Which two days hit does not matter (oldest+middle, oldest+newest, middle+newest).
3. Swing boundary: 1.0 hits, 0.99 does not; also a float case like 8.3 − 7.3 that is mathematically 1.0.
4. Coverage boundary at 48 expected readings: 34 readings (70.8 %) hit, 33 readings (68.75 %) do not.
5. Today's (incomplete) day with a large swing is ignored; a swing only in today's day → `None`.
6. Window slides: the same data evaluated at `now` one day later (the oldest hit day drops out) → `None`.
7. Timezone: a reading at 17:30 UTC counts for the **next** Bangkok date. Same UTC readings with `America/New_York` fall on different days.
8. DST day in `America/New_York` (23 h or 25 h) uses the actual expected count (e.g. 46 or 50) and does not mis-compute coverage.
9. Stale newest pH view → `None`; no pH views → `None`; other parameters' views are ignored.
10. Unsorted input and duplicate timestamps give the same result as sorted input.
11. `facts` content: dates, swing, coverage, hit flags, oldest → newest; Signal fields exactly as specified.
12. Determinism: same inputs twice → equal Signals. Input not mutated.

## Definition of Done
- [ ] All tests pass; all old tests still pass
- [ ] Only the files listed above were changed; `helpers.py` only appended to
- [ ] No `datetime.now()`, no raw `.hour/.date()` outside `helpers.py`
- [ ] `docs/PROGRESS.md` row added

## Out of scope
`ADD_ALKALINITY` recommendation, `valid_until`, reconcile, text, any other detector.
