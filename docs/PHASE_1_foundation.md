# PHASE 1 — Foundation (config, models, helpers, ChangeSet, test simulator)

Read `AGENT_CONTEXT.md` first. Phase 0 must be done (needs `SeverityReportView`).

**Goal:** everything cross-cutting, so Phases 2–7 only add logic. No analysis rules here.

## Files
```
config/constants.py
identity/analysis/models.py
identity/analysis/ids.py
identity/analysis/changeset.py
identity/analysis/helpers.py
tests/support/factories.py
tests/support/store_sim.py
tests/test_config.py, test_helpers.py, test_changeset.py, test_store_sim.py
```
Follow the repo's convention on `__init__.py`; make sure `pytest` from repo root imports everything.

## 1. `config/constants.py` — `AnalysisConfig`
Frozen dataclass + `DEFAULT_CONFIG`. Fields and defaults (use exactly; all are tunable placeholders):
```python
# time
nightStartHour=18; nightEndHour=6
expectedIntervalMinutes=30; staleFactor=3
retroWindowDays=4; historyHorizonDays=8; tickMinutes=30
# diagnostic
minEpisodeReadings=2; maxCauses=2
heavyMealPct=1.0
feedLookbackDoHours=6; feedLookbackNh3Hours=12
tempLookbackHours=3; nh3ChainLookbackHours=24; salWaterChangeLookbackHours=6
tempHighWindow=(11,16); tempLowWindow=(22,6); phHighWindow=(12,18); phLowWindow=(2,7)   # local hours [from,to), may wrap midnight
# detector PH_SWING
phSwingMin=1.0; phSwingHitDays=2; phSwingWindowDays=3; phSwingCoverage=0.70
# prediction
eveningFromHour=16; feedLookbackPredHours=6; feedLookaheadPredHours=8
riskStartAfterMealHours=1; minAerationHours=3.0; tempHighLookbackPredHours=6
repeatMinNights=2; repeatWindowNights=3; repeatSeverity="ElevatedRisk"; predictFromHour=12
dailyHeavyPct=3.0; nh3RiseHorizonHours=12; wcLookbackHours=48; wcLookaheadHours=24
# recommendation
aerateLeadHours=1; aerateDeadlineAfterRiskStartHours=1
aerateDiagDeadlineHours=1; aerateDiagDurationHours=4
wcUrgentDeadlineHours=3; wcUrgentFraction=0.5; wcNonUrgentFraction=0.25
alkalinityWindowDays=3; minAerationSegmentMinutes=15
```
`validate()` raises `ValueError` on nonsense (negative values, hours outside 0–24, coverage outside 0–1, unknown severity name). Call it in `__post_init__`. Severity names are strings; use `severityRank` (Phase 0) to compare.

## 2. `models.py` (all frozen dataclasses; tuples not lists)
Enums: `ActivityType{feeding,aeration,alkalinity,lime,probiotic,waterChange,other}`, `ActivityStatus{pending,done,skipped}`, `ActivitySource{user,recommendation}`, `Urgency{urgent,nonUrgent}`, `RecStatus{pending,snoozed,applied,dismissed,expired}`, `ApplyMode{fixed,pickWindow}`, `PredStatus{active,ended}`, `DiagStatus{open,closed}`, `SignalSource{episode,prediction,detector}`, `TriggerKind{reading,activityEvent,pondEdit,tick}`.

```python
Activity(id, pondId, type, status, startTime, endTime|None, quantityKg|None, fraction|None,
         source=user, sourceRecId|None=None, createdAt, updatedAt)        # endTime required iff aeration
PondInfo(pondId, timezone, biomassKg, avgWeightG, fishCount)
Cause(ruleId, facts: Mapping[str, Any])
DiagnosticReport(id, pondId, parameter, direction|None, onsetAt, endAt|None, status, peakSeverity,
                 lastSeverity, causes: tuple[Cause,...], noClearCause: bool, pondSnapshot: PondInfo, revisedAt|None)
Prediction(id, pondId, ruleId, scope|None, parameter, expectedZone, riskStart, riskEnd, met: tuple[str,...],
           status, endReason|None, evidence: Mapping, pondSnapshot: PondInfo, createdAt, revisedAt|None)
SourceRef(sourceType: SignalSource, sourceId: str)
ProposedActivity(type, startTime, endTime|None, quantityKg|None, fraction|None)
Recommendation(id, pondId, entryId, dedupeKey, urgency, validFrom, validUntil, title, reason, basedOn,
               guidance: tuple[str,...], proposedActivities: tuple[ProposedActivity,...], applyMode, status,
               expireReason|None, sources: tuple[SourceRef,...], snoozeUntil|None, createdAt, updatedAt)
Signal(sourceType, sourceId, code, parameter|None, active: bool, riskStart|None, riskEnd|None,
       peakSeverity|None, lastSeverity|None, scope|None, facts: Mapping)
Trigger(kind, tFrom|None)
PondSnapshot(pond, severityReports: tuple[SeverityReportView,...], activities, diagnostics, predictions, recommendations)
```
`Activity.__post_init__` validates (aeration needs `endTime > startTime`; other types must not have `endTime`; `quantityKg>=0`; `fraction` in (0,1] and only for waterChange). `PondSnapshot` helper: `withActivities(...)` etc. returning copies (use `dataclasses.replace`). Fields shown are the contract; add nothing else without noting it in the report.

## 3. `ids.py` — deterministic ids (idempotency)
```
diagId(pondId, parameter, direction, onsetAt)        -> "diag:{pond}:{param}:{dir|-}:{onset iso}"
predId(pondId, ruleId, scope, createdAt)             -> "pred:{pond}:{rule}:{scope|-}:{createdAt iso}"
recId(pondId, dedupeKey, createdAt)                  -> "rec:{pond}:{dedupeKey}:{createdAt iso}"
actId(recId, index)                                  -> "act:{recId}:{index}"
```
A new prediction/rec for the same key after the old one ended/expired gets a different id (different `createdAt`).

## 4. `changeset.py`
```python
ActivityOp(op: "create"|"update"|"delete", activity: Activity|None, activityId: str|None, reason: str|None)
Notification(kind: str, targetType: str, targetId: str, reasonKey: str, facts: Mapping)
ChangeSet(diagnostics: tuple, predictions: tuple, recommendations: tuple, activityOps: tuple, notifications: tuple)
   .isEmpty()  .merge(other) -> ChangeSet   (later object with same id wins)
def changedOnly(newObjs, existingById) -> tuple   # keep only objects not equal to the existing version
```
Notification kinds (strings, fixed): `urgentRecCreated`, `recChanged`, `recExpired`, `recUnsnoozed`, `predictionEnded`, `activityReplaced`.
Diagnostic/prediction/recommendation entries are **full-object upserts by id**.

## 5. `helpers.py` (pure; take `cfg` and tz explicitly)
```python
toUtcNaive(aware) -> naive UTC datetime
localTime(t, tz) -> aware local datetime            # naive t means UTC
inLocalWindow(t, tz, fromHour, toHour) -> bool    # [from,to), supports wrap (22,6)
isNight(t, tz, cfg) -> bool                       # nightStartHour <= local < nightEndHour (wrap)
nightWindowFor(t, tz, cfg) -> NightWindow(nightDate: date, start: datetime, end: datetime)   # AGENT_CONTEXT O2
localDate(t, tz) -> date
doneActivities(acts, type, fromT, toT) -> tuple    # status done, startTime in [fromT,toT)
plannedActivities(acts, type, fromT, toT, now) -> tuple   # status pending, startTime in [fromT,toT) and startTime >= now
mealPct(activity, pond) -> float                   # quantityKg / pond.biomassKg * 100
aerationHours(acts, fromT, toT) -> float           # done+pending aeration overlap hours, merged (no double count), skipped excluded
zoneAt(views, parameter, t, cfg) -> SeverityReportView|None   # latest view with time<=t and t-time <= staleFactor*interval, else None (unknown)
isStale(lastTime, now, cfg) -> bool                # now-lastTime > staleFactor*interval (strictly greater)
overlap(aStart,aEnd,bStart,bEnd) -> timedelta
```
`mealPct`: raise `ValueError` if activity is not feeding or `quantityKg` is None; `biomassKg<=0` -> `ValueError`.
Never use `datetime.now()`.

## 6. Test support
`factories.py`: `makePond(...)` (default tz `Asia/Bangkok`, biomass 400 kg), `makeActivity(...)`, `makeView(...)`, `makeSnapshot(...)`, `t(local="2025-06-01 19:00", tz="Asia/Bangkok")` -> naive UTC (so tests read in local time).
`store_sim.py`: `StoreSim(snapshot)` with `.apply(changeset)` (upsert diagnostics/predictions/recommendations by id; apply activityOps; record notifications in `.notifications`) and `.snapshot()`. It must handle every ChangeSet field now so later phases can use it.

## Tests (must pass)
**config:** defaults load; frozen; `validate()` rejects bad values (one case per rule).
**time (Asia/Bangkok = UTC+7):**
- 13:00 UTC -> local 20:00 -> `isNight` True; 06:00 UTC -> 13:00 local -> False.
- `isNight` boundaries: local 17:59 False, 18:00 True, 05:59 True, 06:00 False.
- `inLocalWindow` with wrap (22,6): 23:00 True, 03:00 True, 12:00 False.
- `nightWindowFor`: local 15:00 -> tonight (starts today 18:00, ends tomorrow 06:00); 23:00 -> same night; **03:00 -> night that started yesterday, ends today 06:00**; 06:00 exactly -> tonight (starts today 18:00); all returned as naive UTC.
- A second timezone (e.g. `America/New_York`) gives different results for the same UTC instant.
**activities:**
- `mealPct` 6.0 kg / 400 kg = 1.5; non-feeding or missing kg -> `ValueError`.
- `aerationHours`: partial overlap; two overlapping aerations merged (no double count); `skipped` excluded; `pending` and `done` included; no overlap -> 0.
- `doneActivities` ignores pending/skipped; `plannedActivities` ignores past-start pending and non-pending.
- `Activity` validation cases.
**data freshness:** `isStale` at exactly 90 min False, 90 min + 1 s True; `zoneAt` returns None when the latest view is stale or newer than `t`.
**ids/changeset:** ids deterministic and distinct for different `createdAt`; `changedOnly` drops equal objects; `merge` later-wins; `isEmpty`.
**store_sim:** apply each op type; apply(changeset) twice == once (idempotent apply); notifications recorded; snapshot immutable (original not mutated).

## Definition of Done
- [ ] All new tests pass; all old tests still pass
- [ ] `AnalysisConfig` has every field above, validated, frozen
- [ ] Every model/enum/helper/id/ChangeSet item above exists with the stated names (or deviations listed in the report)
- [ ] No rule logic, no `datetime.now()`, no clock reads from raw datetimes outside `helpers.py`
- [ ] `StoreSim` handles all ChangeSet fields
- [ ] `docs/PROGRESS.md` updated

## Out of scope
Episodes, causes, detectors, predictions, recommendations, text.
