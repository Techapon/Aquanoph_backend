# PHASES 2 · 3 · 4 — Run order and shared contracts

Every agent reads: `AGENT_CONTEXT.md` → this file → its own phase file.
Phase 2 = Diagnostic (episodes, causes, runner) · Phase 3 = Detector `PH_SWING` · Phase 4 = Prediction (3 rules + runner).
Spec source for rules and numbers: `docs/part2_minimal_logic_flow_v0_3.md` §3 (Phase 2, 3) and §4 (Phase 4). Phase files are self-sufficient; read the Thai spec only if a rule is ambiguous.

## 1. Run order (one phase at a time)

**Phase 2 → Phase 3 → Phase 4**, each in the same working tree, each finished and committed before the next starts.
Before starting a phase: `pytest -q` must be fully green on the previous phase's result. Do not start the next phase if it is not.
Phase 4 uses `Episode`, `buildEpisodes`, `qualifies` from Phase 2 (contract in §3), so Phase 2 must be done first.

## 2. Scope per phase

- Touch only the files your phase file lists. Do not edit the severity engine, existing tests, `config/constants.py` (every needed field already exists; if one seems missing, STOP and ask), `models.py`, `ids.py`, `changeset.py`, `severity_view.py`, `tests/support/factories.py`, `tests/support/store_sim.py`.
- Phase files may say "append to `helpers.py`". That is the only allowed edit to Phase 1 files, append-only, with its own tests added to `tests/test_helpers.py`.
- Append your own row to `docs/PROGRESS.md` and any backlog items to `docs/BACKLOG.md`.

## 3. Shared contracts (implement exactly; names match the repo's real engine names)

### 3.1 Episode (owner: Phase 2, consumer: Phase 4)
```python
# identity/diagnostic/episode.py
@dataclass(frozen=True)
class Episode:
    parameter: PondParameters
    direction: ThresholdDirection | None   # None for Level thresholds
    onsetAt: datetime                      # time of first non-Optimal-zone reading (naive UTC)
    endAt: datetime | None                 # time of the Optimal-zone reading that closed it; None if open
    status: DiagStatus                     # open | closed
    peakSeverity: SeverityLevelType        # max severity over in-episode readings
    lastSeverity: SeverityLevelType        # severity of the last in-episode reading
    peakZone: ThresholdLevelType
    readingCount: int                      # in-episode readings only
    lastReadingAt: datetime

def buildEpisodes(views: Iterable[SeverityReportView], parameter: PondParameters) -> tuple[Episode, ...]  # ascending by onsetAt
def qualifies(ep: Episode, cfg: AnalysisConfig) -> bool   # readingCount >= minEpisodeReadings OR zoneRank(peakZone) >= zoneRank(HighRisk)
```
`buildEpisodes` filters by `parameter` itself. Never build episodes from a mixed-parameter stream.

### 3.2 Signals (Signal dataclass is in `models.py`; these constructors are the contract)
- Diagnostic (Phase 2): `diagnosticSignals(reports: Iterable[DiagnosticReport]) -> tuple[Signal, ...]`
  `sourceType=episode, sourceId=report.id, code="DIAG_EPISODE", parameter=report.parameter, active=(report.status == open), peakSeverity, lastSeverity, riskStart=None, riskEnd=None, scope=None, facts={"direction": report.direction, "onsetAt": report.onsetAt}`.
- Detector (Phase 3): `detectPhSwing(...) -> Signal | None`. `sourceType=detector, sourceId=f"PH_SWING:{pondId}"` (stable across runs), `code="PH_SWING"`, `parameter=pH`, `active=True`.
- Prediction (Phase 4): `predictionSignals(predictions: Iterable[Prediction]) -> tuple[Signal, ...]`
  `sourceType=prediction, sourceId=p.id, code=p.ruleId, parameter=p.parameter, active=(p.status == active), riskStart=p.riskStart, riskEnd=p.riskEnd, scope=p.scope, facts=p.evidence`.

Phase 5 (recommendation) will consume these. Do not add recommendation logic.

### 3.3 Runner entry points (the Phase 7 orchestrator will call these)
```python
# Phase 2
runDiagnostic(snapshot: PondSnapshot, trigger: Trigger, now: datetime, cfg: AnalysisConfig = DEFAULT_CONFIG) -> DiagnosticResult
DiagnosticResult(diagnostics: tuple[DiagnosticReport, ...],      # only new/changed vs snapshot (use changedOnly)
                 allDiagnostics: tuple[DiagnosticReport, ...],   # resulting report for every qualifying episode in the supplied history
                 episodes: tuple[Episode, ...])                  # all episodes, all parameters (qualifying or not)
# Phase 3
detectPhSwing(views, pond: PondInfo, now: datetime, cfg: AnalysisConfig = DEFAULT_CONFIG) -> Signal | None
# Phase 4
runPredictions(snapshot: PondSnapshot, now: datetime, cfg: AnalysisConfig = DEFAULT_CONFIG,
               doEpisodes: tuple[Episode, ...] | None = None) -> tuple[Prediction, ...]   # only new/changed (changedOnly); ended ones included
```
Each runner is pure, returns data only, never calls another phase's runner (Phase 4 may call `buildEpisodes` when `doEpisodes` is None).

## 4. Conventions for all three phases

- **Names:** use the repo's real engine names (`PondParameters.tem`, `PondParameters.NO2_N`, `PondParameters.salinity`, `ThresholdLevelType.HighRisk`, `ThresholdDirection.High/Low`). Verify before use (AGENT_CONTEXT §9.2).
- **Window boundary convention** (apply everywhere, test it):
  - Diagnostic lookback for **activities**: `[t0 − X, t0)` (an activity exactly at `t0` is not a cause; one exactly at `t0 − X` is).
  - Diagnostic lookback for **sensor views**: `[t0 − X, t0]` (the reading at `t0` is known).
  - Prediction lookback for activities: `[now − X, now]`; lookahead for pending activities: `[now, now + X]`. `doneActivities`/`plannedActivities` are half-open `[from, to)`, so for "inclusive of now" pass `to = now + timedelta(microseconds=1)` or an equivalent, and test the boundary.
- **Rule 5 (unknown ≠ not done):** a rule may only use positive evidence. A missing activity never counts as "not done". Facts record `aerationLogged: bool`, never `notAerated`.
- **Rule 6:** only `done` activities count as past events. `pending` counts as plan only where the rule says so. `skipped` counts as nothing.
- **Rules return facts, not prose.** No English strings except fixed machine ids (rule ids, end reasons).
- Time facts are naive-UTC datetimes. Any local-clock logic goes through `helpers.py`.
- Tests first. Read tests in local time via `t("2025-06-01 19:00")` from `tests/support/factories.py`.
- Run the **full** `pytest -q` before reporting. All old tests must still pass.
- Final message: AGENT_CONTEXT §9.7 format.

## 5. After each phase

1. `pytest -q` fully green (old tests included). Commit.
2. Import check from repo root with no `sys.path` hacks.
3. After Phase 4 only: a short end-to-end smoke check (not a new phase): Case 2 snapshot -> `runDiagnostic` + `runPredictions` -> `StoreSim.apply` -> run again -> both results empty. List any duplicated private helpers in `docs/BACKLOG.md` for Phase 7.
