# ADAPTER NOTES — future DB adapter (≤ 1 page)

The adapter loads a `PondSnapshot` with at least `historyHorizonDays` of readings and all non-final objects, calls `run_analysis(snapshot, trigger, now)`, then persists the returned `ChangeSet` in one transaction.

## Load
- Readings: at least 8 days of severity reports sorted by time, one stream per parameter.
- Activities: all `done`/`pending`/`skipped` records in the retro window, plus any open recommendation-linked activities.
- Diagnostics, predictions, recommendations: all `open`/`active`/`pending`/`snoozed` objects plus recently closed/ended ones needed for idempotency.
- Pond info: current `PondInfo` with timezone. Times are naive UTC; convert local display via `helpers.localTime`.

## Persist
- Upsert diagnostics, predictions, recommendations by id.
- Apply `activityOps` create/update/delete in the same transaction.
- Append notifications to an outbox table; nothing is sent by the engine.
- For user actions: call `validateActivityEdit` + `triggerForEdit(s)` for activity edits; `buildApplyPlan`/`snoozeRec`/`dismissRec` for recommendations; `pondEditTrigger` for pond profile changes.
- Serialize work per pond. Merge overlapping triggers, keeping the lowest `tFrom`.
