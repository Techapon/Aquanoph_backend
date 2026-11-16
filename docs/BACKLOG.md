# BACKLOG

Out-of-scope items tracked for future passes (per AGENT_CONTEXT.md.md section 8 Override O7).

## Thai text issues in severity engine (Phases 1-5)
- **Bug 2**: `NH3`, `NO2_N`, and `salinity` severity description files (`identity/animals/nile_tilapia/nile_parameter_severity/`) contain text referencing "DO" from earlier copy-paste. Update templates to reference their own parameter names once Thai text review is scheduled.
- **Bug 3**: `NH3_EscalationPolicy`, `NO2_N_EscalationPolicy`, and `salinity_EscalationPolicy` default `abnormalLabel` to `"ค่าผิดปกติ"` instead of parameter-specific labels like `"NH3"`, `"NO2-N"`, `"Salinity"`.

## Technical Debt & Architecture Items
- **Dead code `dif_minute.py`**: Function `calDiffMinute` is unused throughout the codebase.
- **Duplicated description factories**: Severity description factories for DO, NH3, NO2-N, and Salinity repeat identical boilerplate; should be consolidated into a shared factory helper (similar to pH and Temperature).
- **Unbounded history scan**: History scans in `SeverityEvaluator` and `findPendingRecovery` are O(N) over all historical reports without a time horizon cap. Needs bounding to `historyHorizonDays` (8 days).
- **Episode onset left-censoring**: If the history horizon begins inside an episode, `Episode.onsetAt` is the first retained non-Optimal reading. Its deterministic ID changes when the horizon slides. Resolve in Phase 7 with persisted episode continuity or a stable onset reference.
- **Decline reason not stored**: `dismissRec` has no reason field; the model has no slot. Phase 7 may add storage.
- **Urgency never lowered**: Reconcile only raises urgency while a rec is open; never lowers it. Phase 7 may revisit with owner.
- **Blocked ★ rules**: `blocked()` uses dismissed rec inside validUntil (Critical-escalation exception) and applied rec with pending/done activity (T5/T18). Phase 7 may refine.
- **Expert review of drafted cause texts and guidance (spec §10)**: Only Case 1/2/3 texts are golden; the remaining cause headings/bodies and guidance lines in `templates_en.py` are author drafts awaiting expert review.
- **Duplicated temperature-High lookup**: Phase 2 `_doTempCause` and Phase 4 `_common.tempHighNow` repeat the same lookup; consolidate in Phase 7 (not refactored yet).
- **Thai severity descriptions from engine file 09** remain out of scope (O7); Phase 7 is the last phase, so they stay in BACKLOG.
- **`services/run_analysis.py` notification fill**: `activityType` is filled only when exactly one activity matches `trigger.tFrom`; deleted activities leave it `None` (accepted limitation, text falls back to "an activity").
- **`render.py` derived fragments**: several fragment defaults assume facts exist; missing keys are guarded by `setdefault`, but the assembly is brittle and should be refactored in a later pass.
- **`activity_replaced` split notification**: `after` tuple uses `tuple(keeps)`; if the second part is dropped it may have fewer than two entries. Handled in `renderNotification` via `len(after)` checks.
- **Skipped deletable (★ default)**: user `skipped` activities are deletable; owner may reverse this.
- **Batch Save all-or-nothing (★ default)**: any single invalid edit aborts the whole batch.
- **`done ↔ skipped` allowed (★ default)**: status can move between `done` and `skipped` but never to `pending`.
- **Detector only on `reading` trigger (★ default)**: `detectPhSwing` runs only on `reading` triggers; other trigger kinds skip the detector.
