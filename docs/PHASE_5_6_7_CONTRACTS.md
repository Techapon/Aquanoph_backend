# PHASES 5 · 6 · 7 — Run order and shared contracts

Every agent reads: `AGENT_CONTEXT.md` → `PHASE_2_3_4_CONTRACTS.md` (signals, runners) → this file → its own phase file.
Phase 5 = Recommendation (catalog, reconcile, apply plan) · Phase 6 = English text · Phase 7 = Orchestrator, edit rules, scenarios.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §5, §6, §9, §11. Decisions D15/D17 (urgent aeration apply) are in section 4 below because the Thai spec is outdated on them.

## 1. Run order (one phase at a time)

**Phase 5 → Phase 6 → Phase 7.** Same working tree. Before starting a phase, `pytest -q` is fully green and the previous phase is committed.
Phase 5 must not import Phase 6. It receives a `Renderer` function (stub in tests). Phase 6 supplies the real one. Phase 7 wires them.

## 2. Scope

- Touch only the files your phase file lists. Same "do not edit" list as before (`config/constants.py`, `models.py`, `ids.py`, `changeset.py`, `severity_view.py`, `factories.py`, `store_sim.py`, severity engine, old tests). If a needed field/config value is missing, STOP and ask.
- Append your row to `docs/PROGRESS.md` and backlog items to `docs/BACKLOG.md`.
- **Additive-only exception:** if a fact needed by text or recommendation is missing from a Phase 2 or Phase 4 output (a new key in `Cause.facts` or `Prediction.evidence`), the phase that needs it may add that key, additively (no change to existing keys or behavior), with a test, and list it under Deviations.

## 3. Shared contracts

### 3.1 Draft and text (defined in `identity/recommendation/types.py`, Phase 5)
```python
@dataclass(frozen=True)
class RecDraft:
    entryId: str                      # "AERATE" | "WATER_CHANGE" | "ADD_ALKALINITY"
    dedupeKey: str
    urgency: Urgency
    validFrom: datetime
    validUntil: datetime
    sources: tuple[SourceRef, ...]
    proposedActivities: tuple[ProposedActivity, ...]   # plan as of draft time (display); apply recomputes urgent times
    applyMode: ApplyMode              # urgent -> fixed ; non_urgent -> pickWindow
    textKey: str                      # see table 3.2
    facts: Mapping[str, Any]          # see table 3.2; naive-UTC datetimes, numbers, bools, tuples only

@dataclass(frozen=True)
class RenderedText:
    title: str; reason: str; basedOn: str; guidance: tuple[str, ...]

Renderer = Callable[[RecDraft, PondInfo], RenderedText]    # pure; Phase 6: renderRecommendation(draft, pond, cfg=DEFAULT_CONFIG)
```

### 3.2 `textKey` and `facts` (Phase 5 writes them, Phase 6 reads them)

| textKey | when | required facts |
|---|---|---|
| `AERATE.prediction` | only prediction source(s) | `ruleIds` (tuple), `riskStart`, `riskEnd`, `mealTime`, `mealKg`, `mealPct`, `mealIsPlanned` (bool, `mealTime > now`), `aerationHours`, `tempValue`/`tempZone` (or None), `hitNights` (tuple of date strings, or None), `nightsChecked`, `planStart`, `planEnd`, `deadline`, `parameters` |
| `AERATE.diagnostic` | only DO episode source | `doLastSeverity`, `doOnsetAt`, `planStart`, `planEnd`, `deadline`, `parameters` |
| `AERATE.both` | both | union of the two sets |
| `WATER_CHANGE.episode` | NH3/NO2_N episode only | `parameter`, `lastSeverity`, `onsetAt`, `fraction`, `parameters` |
| `WATER_CHANGE.prediction` | `PRED_NH3_RISE` only | `totalMealPct`, `totalKg`, `nh3Zone`, `nh3Value`, `horizonHours`, `fraction`, `windowEnd`, `parameters` |
| `WATER_CHANGE.both` | both | union |
| `ADD_ALKALINITY.detector` | detector | `hitDays`, `windowDays`, `maxSwing`, `windowEnd`, `parameters` |

`parameters` = tuple of `PondParameters` members involved (used by `blocked()` for the Critical-escalation exception).

### 3.3 Reconcile and apply (Phase 5)
```python
reconcile(snapshot, signals, now, trigger, renderer, cfg=DEFAULT_CONFIG) -> ReconcileResult
ReconcileResult(recommendations: tuple[Recommendation, ...],   # changed/new only (changedOnly)
                notifications: tuple[Notification, ...])

buildApplyPlan(rec, snapshot, now, chosenTime=None, confirmed=False, cfg=DEFAULT_CONFIG) -> ApplyResult
ApplyResult(status: "applied" | "rejected" | "needsDecision", reason: str | None,
            changeSet: ChangeSet, summary: Mapping[str, Any])
snoozeRec(rec, until, now, cfg) -> ChangeSet | raises ValueError      # non_urgent only, until <= validUntil
dismissRec(rec, now) -> ChangeSet
```
`buildApplyPlan` is pure. The UI may call it to preview (shortening shown before Apply) and call again to commit; nothing is persisted by the function.

### 3.4 Notification catalog (O5: entries in ChangeSet only; nothing is sent)

| kind | reasonKey | facts | produced by |
|---|---|---|---|
| `urgentRecCreated` | `rec.created.urgent` | `recId, entryId, dedupeKey, parameters` | reconcile (new urgent rec) |
| `recChanged` | `rec.changed.activity_edit` | `recId, entryId, tFrom, activityType` (type may be None) | reconcile, only when `trigger.kind == activityEvent` and content changed |
| `recChanged` | `rec.changed.urgency_raised` | `recId, entryId, fromUrgency, toUrgency` | reconcile |
| `recExpired` | `rec.expired.no_longer_applies` | `recId, entryId, sourceRuleIds, sourceEndReasons, afterActivityEdit` | reconcile |
| `recExpired` | `rec.expired.time_window_over` | `recId, entryId` | reconcile |
| `recUnsnoozed` | `rec.unsnoozed.snooze_over` / `rec.unsnoozed.urgency_raised` | `recId, entryId` | reconcile |
| `predictionEnded` | `prediction.ended.mitigated` / `.conditions_gone` / `.window_over` | `predictionId, ruleId, endReason` | Phase 7 (from the prediction diff) |
| `activityReplaced` | `activity.replaced.by_recommendation` | `activityId, recId, before=(start,end), after=tuple[(start,end)]` (empty = deleted) | `buildApplyPlan` |

`targetType` is `"recommendation"`, `"prediction"` or `"activity"`; `targetId` is that object's id.

### 3.5 Text API (Phase 6, in `identity/text/render.py`)
```python
renderRecommendation(draft, pond, cfg=DEFAULT_CONFIG) -> RenderedText
renderDiagnostic(report, cfg=DEFAULT_CONFIG) -> RenderedDiagnostic       # title, causes=(CauseText(heading, body),...), fallback|None, footer, revisedLabel|None
renderPrediction(pred, cfg=DEFAULT_CONFIG) -> RenderedPrediction          # headline, conditions=((label, met),...), footer
renderNotification(n: Notification, pondTz: str, cfg=DEFAULT_CONFIG) -> str
renderApplySummary(summary, pondTz: str) -> str
renderPlan(rec: Recommendation, pond: PondInfo, cfg=DEFAULT_CONFIG) -> str   # the "Plan:" line (the model has no plan field)
DISCLAIMER_TEXT: str                                                         # "Automated estimate based on your logs and sensor data. Not a guarantee."
```

### 3.6 Orchestrator (Phase 7, `services/run_analysis.py`)
```python
run_analysis(snapshot, trigger, now, cfg=DEFAULT_CONFIG, renderer=renderRecommendation) -> ChangeSet
runAnalysis = run_analysis        # repo style alias
```

## 4. Rules that override the Thai spec (author decisions; keep unless the owner changes them)

- **D15 (urgent aeration apply):** the recommendation's range R always wins over the user's `pending` aeration. Parts of that activity outside R are kept. Example: user pending 21:00–23:00 + R 22:00–03:00 → the user activity becomes 21:00–22:00; R is created in full.
- **D17 sub-rules:** `done` aeration is never modified (the rec then creates only the remaining pieces); recommendation-origin `pending` aeration is never modified (same: the rec fills around it); `skipped` is ignored; leftover pieces shorter than `minAerationSegmentMinutes` are dropped; everything is one ChangeSet (one transaction); if `done` covers all of R, the rec becomes `applied` with no new activity and the summary says so.
- **T14 in the spec is outdated** (it describes gap-fill around a pending user aeration). Under D15 a pending 22:00–02:00 inside R is removed, and R is created whole. Gap-fill around the existing activity only happens when that activity is `done` or recommendation-origin.
- User-form aeration overlaps, and any non_urgent aeration apply, still block (O6, D16).
- Urgent apply with a same-type conflict for a non-aeration activity: `needsDecision` ("Apply anyway" = call again with `confirmed=True`).

## 5. Conventions (same as before)

Real engine names; Rule 5 (unknown ≠ not done); Rule 6; Rule 7 idempotency; rules return facts, text only in `identity/text`; no `datetime.now()`; time-of-day only through `helpers.py`; tests first; full `pytest -q` before reporting; final message in AGENT_CONTEXT §9.7 format.

## 6. After each phase

`pytest -q` fully green, commit, import check from repo root. After Phase 7: update `docs/BACKLOG.md` (Thai text bugs O7, left-censored episodes, duplicated helpers, decline-reason storage) and stop. Do not start a DB adapter.
