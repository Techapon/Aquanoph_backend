# PHASE 0 — Prep & baseline

Read `AGENT_CONTEXT.md` first.

**Goal:** verified baseline, the known blocker fixed, real code facts documented, and a `SeverityReportView` adapter so all later phases never touch the severity engine's classes directly.

**Prereq:** spec docs copied into `docs/` (v0.3, special part, 09, app spec, SUMMARY). If missing, ask.

## Tasks

### 0.1 Baseline
Run `pytest -q` (existing: `tests/test_range_severity.py`). Record pass/fail counts in `docs/PROGRESS.md` (create it from the template in AGENT_CONTEXT §11). If tests fail or cannot run, report; do not fix unless related to Bug 1.

### 0.2 Code findings -> `docs/CODE_FINDINGS.md`
Inspect the real code and write concise facts (file:line). Answer exactly:
- a) `AnalysisReportModel`: attribute names/types for parameter, timestamp, measured value, threshold zone/level, direction, severity.
- b) Enums: members + order of `ThresholdLevelType`, `SeverityLevelType`, `ThresholdDirection`, `PondParameters`.
- c) **Does a report produced during Recovery Hold keep zone = Optimal while severity = Stress?** Prove with a tiny throwaway test using existing test helpers.
- d) What direction value do Level thresholds (DO, NH3, NO2_N, Salinity) carry in a report?
- e) Type/ordering of the history passed to the evaluator.
- f) Does the report store the measured value? (needed for pH swing, Phase 3)

**BLOCKER:** if (a) or (c) shows the zone is not stored separately from severity, or the value is not stored, STOP and report. Episodes (Phase 2) and detector (Phase 3) depend on it.

### 0.3 Bug 1
SUMMARY claims `AnalysisReportModel` uses `event.severityStatus` but `SeverityModel` defines `severityLevel`.
- Reproduce with a failing test first (Recovery Hold path). If not reproducible, document and skip.
- Minimal fix: add a read-only property alias on `SeverityModel` (do not rename existing attributes). Add a regression test.

### 0.4 `SeverityReportView` -> `identity/analysis/severity_view.py`
```python
@dataclass(frozen=True)
class SeverityReportView:
    parameter: PondParameters
    time: datetime                       # naive UTC
    value: float
    zone: ThresholdLevelType
    direction: ThresholdDirection | None # None for Level thresholds (confirm in 0.2d)
    severity: SeverityLevelType

def toView(report: AnalysisReportModel) -> SeverityReportView
def toViews(history: Iterable[AnalysisReportModel]) -> tuple[SeverityReportView, ...]   # sorted by time asc
def zoneRank(zone) -> int        # Optimal 0, Stress 1, HighRisk 2, Critical 3
def severityRank(sev) -> int     # Optimal 0, Stress 1, ElevatedRisk 2, Critical 3
def isOptimalZone(v: SeverityReportView) -> bool
```
Use the real names found in 0.2; keep the semantics. `toView` raises `ValueError` on missing fields (never silently skip).

### 0.5 `docs/BACKLOG.md`
Create with: Bug 2 (NH3/NO2_N/Salinity descriptions mention DO), Bug 3 (empty escalation-policy constructors), dead code `dif_minute.py`, duplicated description factories, unbounded history scan. Do not fix.

## Tests (`tests/test_severity_view.py`, plus the Bug 1 regression)
1. `toView` maps all fields correctly for one report per parameter.
2. Recovery Hold report -> `isOptimalZone` True while severity rank == Stress rank.
3. `zoneRank` / `severityRank` ordering for all members (and the zone/severity name mismatch HighRisk vs ElevatedRisk is handled).
4. `toViews` sorts ascending and is stable for equal times.
5. `toView` raises `ValueError` for an incomplete report.
6. Input history list is not mutated.

## Definition of Done
- [ ] Old tests still pass; baseline recorded
- [ ] `docs/CODE_FINDINGS.md` answers a–f (no BLOCKER, or BLOCKER reported)
- [ ] Bug 1 fixed with regression test, or documented as not reproducible
- [ ] `severity_view.py` + tests green
- [ ] `docs/BACKLOG.md` and `docs/PROGRESS.md` exist
- [ ] No other existing file modified (except the Bug 1 alias)

## Out of scope
Config, models, helpers (Phase 1); any diagnostic logic; Bugs 2–3.
