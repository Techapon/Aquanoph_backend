# PHASE 5 — Recommendation (catalog, reconcile, apply plan)

Read `AGENT_CONTEXT.md`, `PHASE_2_3_4_CONTRACTS.md`, `PHASE_5_6_7_CONTRACTS.md` first. Phases 0–4 are done.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §5 and test cases T2, T3, T4, T5, T7, T8, T10, T11, T12, T13, T14 (see contracts §4), T15, T16, T18 at recommendation level.

**Goal:** turn Signals into recommendations (create / update / expire), and turn "Apply" into a set of activity changes. Pure logic. No text (use the injected `Renderer`), no orchestration.

## Files
```
identity/recommendation/__init__.py
identity/recommendation/types.py              (RecDraft, RenderedText, Renderer, ReconcileResult, ApplyResult)
identity/recommendation/catalog/__init__.py   (CATALOG tuple, buildDrafts)
identity/recommendation/catalog/aerate.py
identity/recommendation/catalog/water_change.py
identity/recommendation/catalog/add_alkalinity.py
identity/recommendation/reconcile.py          (reconcile, blocked)
identity/recommendation/apply_plan.py         (buildApplyPlan, snoozeRec, dismissRec)
tests/support/rec_builders.py
tests/test_catalog.py, test_reconcile.py, test_apply_plan.py
```

## 0. Prerequisite check (do first)
Verify the real names of the evidence keys that Phase 4 writes into `Prediction.evidence` and the facts Phase 2 writes (`firstMealTime`, `firstMealKg`, `firstMealPct`, `aerationHours`, `tempValue`, `tempZone`, `hitNights`, `nightsChecked`, `totalMealPct`, `nh3Zone`, `nh3Value`, and `totalKg` for NH3). Contracts §3.2 lists what drafts need. If a key is missing, add it additively to the Phase 4 rule (new key only, with a test) and list it in Deviations. Adjust names, not semantics.

## 1. Catalog → drafts

`buildDrafts(signals, snapshot, now, cfg) -> tuple[RecDraft, ...]` calls each entry. Only **active** signals produce drafts. Result sorted by `dedupeKey`.

Common helpers (in `catalog/__init__.py`):
- `existingOpenFor(snapshot, entryId, sources)` = a `pending`/`snoozed` rec of the same entry that shares at least one `SourceRef` with the draft's sources.
- **Key and anchor reuse:** if such a rec exists, the draft **adopts its `dedupeKey`** (this stops a duplicate when the local date rolls over at midnight) and uses `anchor = rec.createdAt`. Otherwise `anchor = now`. If the new urgency is **higher** than the existing rec's urgency, `anchor = now` (the urgent deadline starts fresh).
- All windows are computed from `anchor`, never from `now`, so repeated runs produce identical drafts (Rule 7).

### `AERATE` (`aerate.py`) — urgent always, `applyMode=fixed`, key `AERATE:{nightDate}`
Sources:
- (a) active prediction signals with `code in (PRED_DO_NIGHT, PRED_DO_REPEAT)`; `nightDate = signal.scope`.
- (b) active episode signals with `parameter == DO` and `severityRank(lastSeverity) >= severityRank(ElevatedRisk)`; `nightDate = nightWindowFor(anchor).nightDate.isoformat()`.
Group by `nightDate`. Per group:

| | (a) only | (b) only | both |
|---|---|---|---|
| plan start | `max(anchor, riskStart − aerateLeadHours)` | `anchor` | `anchor` |
| plan end | `riskEnd` | `start + aerateDiagDurationHours` | later of (a) end and (b) end |
| `validFrom` | `anchor` | `anchor` | `anchor` |
| `validUntil` (deadline) | `riskStart + aerateDeadlineAfterRiskStartHours` | `anchor + aerateDiagDeadlineHours` | the **earlier** of the two |
| textKey | `AERATE.prediction` | `AERATE.diagnostic` | `AERATE.both` |

With several (a) predictions in one group take the earliest `riskStart` and the latest `riskEnd`. `proposedActivities = (ProposedActivity(aeration, planStart, planEnd, None, None),)`. Never list a fixed apply time as a user choice. Time values in `facts`: see contracts §3.2.

### `WATER_CHANGE` (`water_change.py`) — key `WATER_CHANGE:{localDate(anchor)}`
Sources:
- (a) active episode signals with `parameter in (NH3, NO2_N)` and `severityRank(lastSeverity) >= severityRank(ElevatedRisk)`. `lastSeverity == Critical` → urgent; `ElevatedRisk` → non_urgent.
- (b) active `PRED_NH3_RISE` prediction signal → non_urgent.
One draft (single key). Several sources: highest urgency wins; `validFrom` = min, `validUntil` = min over the drafts of the **winning** urgency; sources = union.
- **urgent:** `applyMode=fixed`; `validFrom=anchor`, `validUntil=anchor + wcUrgentDeadlineHours`; proposed water_change at `anchor`, `fraction=wcUrgentFraction`.
- **non_urgent:** `applyMode=pickWindow`; `validFrom=anchor`, `validUntil` = end of the **next** local day after `localDate(anchor)` (use `localDayBounds`, naive UTC); proposed water_change at `anchor`, `fraction=wcNonUrgentFraction`.
- textKey `WATER_CHANGE.episode` / `.prediction` / `.both`.

### `ADD_ALKALINITY` (`add_alkalinity.py`) — non_urgent, `pickWindow`, key `ADD_ALKALINITY`
Source: the detector signal `PH_SWING`. `validFrom=anchor`, `validUntil=anchor + alkalinityWindowDays`. `proposedActivities = (ProposedActivity(alkalinity, anchor, None, None, None),)` (**no quantity**). textKey `ADD_ALKALINITY.detector`.

## 2. `reconcile(snapshot, signals, now, trigger, renderer, cfg)`

```
drafts   = buildDrafts(...)              # desired, one per dedupeKey
open     = recs with status pending or snoozed
```
Process **in this order**, results deterministic (sort by key):

1. **Unsnooze by time:** `snoozed` with `snoozeUntil <= now` → `pending`, `snoozeUntil=None`; notification `recUnsnoozed / rec.unsnoozed.snooze_over`.
2. **Existing open rec whose `dedupeKey` is desired** → update in place:
   - Keep `id`, `createdAt`, `status`, `snoozeUntil` (snooze is kept).
   - Replace `urgency` (never lowered while the rec is open: **urgency only goes up**), `validFrom`, `validUntil`, `applyMode`, `proposedActivities`, `textKey`-based text via `renderer(draft, pond)`, `sources = existing.sources + new refs not already present` (union, existing order first).
   - If urgency rose to urgent: `status=pending`, `snoozeUntil=None` (un-snooze), `applyMode=fixed`; notifications `recChanged / rec.changed.urgency_raised`, plus `recUnsnoozed / rec.unsnoozed.urgency_raised` if it was snoozed, plus `urgentRecCreated` is **not** emitted (it is not new).
   - Build the candidate with the old `updatedAt`. If equal to the stored object → emit nothing. Otherwise emit with `updatedAt=now`; and if `trigger.kind == activityEvent`, add `recChanged / rec.changed.activity_edit` (facts `tFrom=trigger.tFrom`, `activityType=None` for now; Phase 7 may fill it).
3. **Existing open rec whose key is not desired:**
   - if **all** its sources are closed → `expired`, `expireReason="no_longer_applies"`, notification `recExpired / rec.expired.no_longer_applies` (`afterActivityEdit = trigger.kind == activityEvent`);
   - elif `now > validUntil` → `expired`, `expireReason="time_window_over"`;
   - else keep unchanged (source still open, or data is missing). **Never expire because data is missing** (Rule 11).
4. **New recs:** for each draft key with no open rec and not `blocked(...)`: create `pending`: `id=recId(pondId, dedupeKey, now)`, `createdAt=updatedAt=now`, text from `renderer`. If urgent → notification `urgentRecCreated / rec.created.urgent`.
5. `applied`, `dismissed`, `expired` recs are never touched here.

**`sourceClosed(ref, signalsById)`:** detector → always `False` (a detector source ends only through `validUntil`; O3). A source with a signal that is not active → `True`. A source with **no** signal in this run → `False` (unknown; keep).

**`blocked(key, draft, snapshot, now)`** (author decisions marked ★):
- A rec with the same `dedupeKey` that is `dismissed` and `now < validUntil` blocks. **Exception (urgent only):** if any view of one of `draft.facts["parameters"]` has `severity == Critical` and `time > dismissed.updatedAt`, it does not block (T10).
- ★ A rec that is `applied` blocks while any activity with `sourceRecId == rec.id` is `pending`, or is `done` and `now <= rec.validUntil`. If every such activity is `skipped` or deleted, it does not block (T5). (The `validUntil` bound for `done` stops the constant key `ADD_ALKALINITY` from being blocked forever.)
- `expired` never blocks. Shortening an applied pending aeration still blocks (T18).

## 3. `buildApplyPlan`

Order of checks, each returns `ApplyResult(status="rejected", reason=...)` with an **empty** ChangeSet:
1. `rec.status` not in `(pending, snoozed)` → `not_pending`.
2. `now > rec.validUntil` → `expired`. (Do not mutate the rec here; reconcile expires it.)
3. **non_urgent:** `chosenTime` required (`missing_time`) and must satisfy `validFrom <= chosenTime <= validUntil` else `time_outside_window` (T13). The activity may end after `validUntil`.
4. **urgent:** times are fixed at `now`; `chosenTime` is ignored.

Activity to create, by entry:
- **AERATE (urgent):** recompute at `now` from `rec.sources` (do not trust the stored plan): look up each prediction source in `snapshot.predictions` → `riskStart/riskEnd`; episode source → duration `aerateDiagDurationHours`. `start = now` when an episode source exists (also in "both"); else `max(now, riskStart − aerateLeadHours)`; `end` per the table in §1 (using `start`). If a source is missing from the snapshot, fall back to the stored `proposedActivities[0]` (`start = max(now, stored.start)`, `end = stored.end`). If `start >= end` → `invalid_window`. Result **R = [start, end)**.
- **WATER_CHANGE:** one `waterChange` activity at `now` (urgent, `fraction=wcUrgentFraction`) or at `chosenTime` (non_urgent, `fraction=` proposed).
- **ADD_ALKALINITY:** one `alkalinity` activity at `chosenTime`, no quantity.
New activities: `status=pending`, `source=recommendation`, `sourceRecId=rec.id`, `createdAt=updatedAt=now`, ids `actId(rec.id, index)`. Then `rec.status = applied`, `updatedAt = now`.

**Aeration apply under D15/D17 (urgent AERATE):** let `fixed` = aeration activities that are `done` or recommendation-origin `pending`, and `userPending` = user-origin `pending` aeration. `skipped` is ignored.
1. Pieces to create = R minus the union of `fixed` intervals; drop pieces shorter than `minAerationSegmentMinutes`. If nothing is left (done covers all of R) → status `applied`, no creates, `summary["coveredByDone"]=True`.
2. For every `userPending` overlapping R: remove the overlap from it. Outside parts are kept. Result per activity: unchanged (no overlap), **update** (one part kept, shortened), **split** (two parts: update the original to the first part, create a new `source=user` activity for the second with the next `actId(rec.id, k)`; new activity keeps the original's `createdAt`), or **delete** (nothing left). Parts shorter than `minAerationSegmentMinutes` are dropped (the activity shrinks or is deleted).
3. All of this goes into one ChangeSet: `activityOps` + the updated rec + one `activityReplaced` notification per modified or deleted user activity (contracts §3.4).
4. `summary` = `{"created": ((start,end),...), "modified": ({"activityId","before","after"},...), "kept": ((start,end),...) for done/rec-origin that were respected, "coveredByDone": bool}` so the UI can show the shortening before and after Apply.

**Other conflict rules:**
- **non_urgent aeration** (not in the v1 catalog, keep the path generic): any overlap with an existing non-skipped aeration → `rejected / aeration_overlap`.
- **Same-type conflict** for non-aeration activities (a non-skipped activity of the same type with `startTime` in `[validFrom, validUntil]`): `needsDecision` with `summary["conflicts"]` unless `confirmed=True`. Applies to urgent and non_urgent.
- Idempotency: applying the result twice is rejected the second time (`not_pending`).

**`snoozeRec(rec, until, now, cfg)`:** only `pending` non_urgent; `now < until <= validUntil`, else `ValueError`. Returns ChangeSet with `status=snoozed, snoozeUntil=until, updatedAt=now`.
**`dismissRec(rec, now)`:** from `pending`/`snoozed` → `dismissed`, `updatedAt=now`. (A decline reason is not stored: the model has no field; add it to BACKLOG.)

## 4. Tests (write first; `Asia/Bangkok`, biomass 400 kg; use a stub renderer that returns `RenderedText(f"title:{textKey}", f"reason:{textKey}", "basedOn", ("g1",))`)

**test_catalog.py**
1. **T2 / T11 level:** active `PRED_DO_NIGHT` signal (riskStart 20:00, riskEnd 06:00, scope tonight), now 16:30 → one `AERATE` draft: urgent, `fixed`, plan 19:00→06:00, `validFrom=16:30`, `validUntil=21:00`, key `AERATE:{tonight}`, textKey `AERATE.prediction`. Same with `PRED_DO_REPEAT`.
2. Diagnostic only: open DO episode with `lastSeverity=ElevatedRisk` → plan `anchor → anchor+4h`, deadline `anchor+1h`, `AERATE.diagnostic`. `Stress` → no draft; closed episode → no draft.
3. Both sources: start = anchor, end = later of the two, deadline = earlier of the two, `AERATE.both`, sources contain both refs.
4. `WATER_CHANGE`: episode NH3 `Critical` → urgent fixed, deadline `anchor+3h`, fraction 1/2; `ElevatedRisk` → non_urgent, fraction 1/4, window `anchor → end of next local day`; NO2_N works the same; `PRED_NH3_RISE` → non_urgent; urgent + non_urgent sources → urgent wins, sources union.
5. `ADD_ALKALINITY`: window 3 days, no quantity.
6. Anchor stability: running `buildDrafts` again 30 min later with the existing rec in the snapshot gives the same `validFrom/validUntil/proposedActivities` (only `now`-independent output).
7. Key reuse across local midnight: existing `WATER_CHANGE:2025-06-01` rec, now 2025-06-02 00:10, source still active → draft key stays `WATER_CHANGE:2025-06-01`.
8. Urgency raised → anchor resets to `now`.
9. Closed/inactive signals produce no drafts.

**test_reconcile.py**
1. Create: draft with no open rec and not blocked → `pending` rec, deterministic id; urgent → `urgentRecCreated` notification.
2. Same key, nothing changed → empty result (idempotent). Apply the result with `StoreSim` and rerun → empty.
3. **T4:** prediction signal becomes inactive (`conditions_gone`) → rec `expired / no_longer_applies` + notification with `sourceEndReasons`; `applied` rec untouched.
4. Multi-source (O3): sources {prediction (closed), episode (open)} → not expired; both closed → expired; detector source → never closed, rec lives until `validUntil` then `time_window_over` (**T7**: swing gone next day, rec stays).
5. Source signal missing (no data) → rec kept; `now > validUntil` still expires it (time-based expiry runs).
6. **T8:** non_urgent snoozed `WATER_CHANGE`; episode becomes `Critical` → same id, `urgent`, `fixed`, `pending`, `snoozeUntil=None`, notifications `recChanged(urgency_raised)` + `recUnsnoozed(urgency_raised)`; deadline = `now + 3h`.
7. Urgency never lowered: urgent rec, source drops to `ElevatedRisk` → stays urgent.
8. Snooze kept when content changes but urgency is unchanged. `snoozeUntil <= now` → pending + `recUnsnoozed(snooze_over)`.
9. `blocked`: dismissed + inside `validUntil` blocks; **T10:** urgent dismissed, later a Critical DO view after the dismissal → not blocked; Critical view **before** the dismissal → still blocked; after `validUntil` → not blocked.
10. **T5:** applied rec whose activity is `skipped` → not blocked → new rec created (new id). Deleted activity → not blocked. **T18:** activity shortened but still `pending` → blocked. Applied with `done` activity blocks until `validUntil`, then not (alkalinity case).
11. `trigger.kind == activityEvent` + content change → `recChanged(activity_edit)` with `tFrom`; on `reading` trigger the same change gives **no** notification. `afterActivityEdit` flag on expiry.
12. Urgent rec is never expired by an activity edit unless all sources are closed.
13. Determinism: same inputs → same output order; inputs not mutated.

**test_apply_plan.py**
1. **T3:** urgent AERATE apply at 19:10 → activity 19:10→06:00 (`pending`, `source=recommendation`, `sourceRecId`), rec `applied`. Apply at 18:00 → start 19:00 (`riskStart − 1h`). Apply after the deadline → `rejected/expired`.
2. Both-source start = apply time; end = later end.
3. **D15:** user pending 21:00–23:00 + R 22:00–03:00 → user activity updated to 21:00–22:00; R created whole; `activityReplaced` notification. User pending fully inside R → deleted. R strictly inside a user pending (20:00–06:00 vs 22:00–03:00) → split: 20:00–22:00 updated, 03:00–06:00 created (`source=user`).
4. **T14 (updated):** user `done` 22:00–02:00 inside R 19:00–06:00 → rec creates 19:00–22:00 and 02:00–06:00; the done activity is untouched. Rec-origin pending inside R is respected the same way. `skipped` ignored.
5. Pieces shorter than 15 min are dropped (both rec pieces and user remainders); exactly 15 min is kept.
6. `done` covers all of R → rec `applied`, no created activities, `coveredByDone`.
7. Everything in one ChangeSet; the input snapshot is untouched; applying again → `not_pending`.
8. **T13:** non_urgent `chosenTime` before `validFrom` or after `validUntil` → `time_outside_window`; at exactly the bounds → accepted; missing → `missing_time`. Activity may end after `validUntil` (alkalinity has no end).
9. Same-type conflict (existing pending water_change inside the window): `needsDecision`; `confirmed=True` → applied. Skipped one does not conflict.
10. Non_urgent aeration overlap (synthetic rec) → `rejected/aeration_overlap`.
11. Water change fraction: urgent 1/2, non_urgent default 1/4; `Activity` validation passes (fraction only on `waterChange`).
12. `snoozeRec`: ok within `validUntil`; urgent → `ValueError`; `until > validUntil` → `ValueError`. `dismissRec` from pending/snoozed only.
13. Missing prediction source in the snapshot → falls back to the stored plan.

## 5. Definition of Done
- [ ] All tests above pass; all old tests still pass
- [ ] Catalog (3 entries), `reconcile`, `blocked`, `buildApplyPlan`, `snoozeRec`, `dismissRec` implemented; no text strings other than ids and keys
- [ ] Idempotent with `StoreSim` (apply result, rerun → empty)
- [ ] No `datetime.now()`, no raw `.hour/.date()`, no magic numbers (all from `cfg`)
- [ ] Phase 4/2 additive evidence keys (if any) listed in Deviations
- [ ] `docs/PROGRESS.md` row; `docs/BACKLOG.md`: decline reason not stored; urgency-never-lowered decision; `blocked` ★ rule

## Out of scope
Text rendering (Phase 6), orchestrator, activity-edit validation (T17, Phase 7), push sending, DB.
