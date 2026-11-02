ROLE
You are a senior engineer onboarding onto an existing codebase. Your job is to READ and SUMMARIZE ONLY the Analysis Backend so a planner can decide what to build next. Ignore the Flutter app and anything unrelated to analysis, except where the backend reads or writes it. Do not modify any file except creating ANALYSIS_BACKEND_SUMMARY.md at the repo root.

PROJECT CONTEXT
Prototype of an aquaculture water-quality system for Nile tilapia ponds. A sensor buoy (not built yet; data comes from [simulator / dataset - fill in]) sends 6 parameters about every 30 minutes: DO, NH3, NO2, Temperature, pH, Salinity. Supabase stores data. The Analysis Backend ([language/framework - fill in or "unknown"]) does, per pond:
1. Severity: classifies each reading into a threshold zone (Optimal / Stress / HighRisk / Critical) and a severity (Optimal / Stress / ElevatedRisk / Critical, with Recovery Hold).
2. Diagnostic: groups non-Optimal readings into episodes and evaluates cause rules at the episode onset.
3. Prediction: rule-based forecasts that use sensor data and farmer activities.
4. Recommendation: turns signals into recommendations, de-duplicates and reconciles them with existing ones.
Repo location: [path]
Specs, if present in docs/: part2_minimal_logic_flow_v0.3.md, special_part_retroactive_edits_v0.2.md, 09_system_logic_summary.md

RULES
- Read-only, except writing ANALYSIS_BACKEND_SUMMARY.md.
- NEVER print secrets (keys, tokens, passwords, .env values, service-role keys). Mention only that a file or variable exists.
- Base every statement on files you actually read. Cite file paths with function/class names. If you did not verify something, write "unverified". Do not guess.
- No large code blocks. Short signatures or 3-5 line snippets only when essential.
- Keep the whole summary under about 500 lines. Prefer tables and short bullets.

WHAT TO PRODUCE (sections in this order)

1. Overview
   - Language, framework, versions, how it is deployed or run, and a simple text diagram: trigger -> stages -> database writes.

2. Structure
   - Directory tree (depth 3) of the backend only, one line of purpose per important folder/file. Mark generated/vendor folders as ignorable.

3. Run and test
   - Setup, env var NAMES (not values), commands to run, test and migrate, and which of these you were able to verify.

4. Triggers and orchestration
   - What starts an analysis run (new reading, activity change, pond edit, scheduled tick) and how each is wired (webhook, listener, cron, queue).
   - Ordering of stages, one-run-at-a-time per pond (locks/queues), idempotency (upserts/keys), coalescing of events, retry/failure handling.

5. Modules (one table per stage: file | responsibility | main functions | inputs | outputs)
   - Severity (zone/direction/severity, Recovery Hold, episode handling if any)
   - Diagnostic (episode building, cause rules, detectors)
   - Prediction (each rule, its conditions, mitigation check, lifecycle)
   - Recommendation (catalog, drafting, dedupe_key, merge, reconcile, blocked() logic, expiry, urgency handling, window/time logic)

6. Data access
   - Tables and columns read and written by the backend, which client/role it uses, and how results are read back by the app.
   - How activities, pond profile, readings and existing recommendations are loaded; how "not logged" versus "not done" is treated.

7. Time handling
   - UTC storage versus pond timezone, how local time-of-day is computed (night window, time-based rules), how sunrise/sunset or night is defined, and how stale or missing readings (data gaps, expected interval) are handled.

8. Configuration and constants
   - Table: constant | value | file | used by. Include every threshold, window, lookback, percentage and default. Flag hard-coded numbers that are not in a config file.

9. Retroactive edits
   - How the backend reacts to adding, editing, deleting and status-saving activities in the past (t_from, which episodes/predictions are recomputed, overwrite with revised_at, the 4-day window, what happens to existing recommendations).

10. User-facing text
   - Where message templates live (titles, reasons, guidance, diagnostic text), the language used, and whether text is built from facts/templates or hard-coded.

11. Spec coverage (only if specs are in docs/)
   - Table: spec item | status (done / partial / missing / diverges) | evidence (file path) | notes. Cover at least:
     - cause rules: DO_C_FEED, DO_C_TEMP, DO_C_NIGHT, NH3_C_FEED, NO2_C_NH3, TEMP_C_TIME, PH_C_TIME, SAL_C_WATERCHG and the fallback NO_CLEAR_CAUSE
     - detector PH_SWING
     - predictions PRED_DO_NIGHT, PRED_DO_REPEAT, PRED_NH3_RISE and their mitigation checks
     - recommendations AERATE, WATER_CHANGE, ADD_ALKALINITY (urgency, dedupe_key, fixed time for urgent vs picked time for non_urgent, deadlines)
     - reconcile, blocked(), source-closed expiry, urgent safety rule, un-snooze on urgency upgrade
     - retroactive-edit handling, 3x expected-interval stale rule, English messages

12. Quality and risks
   - Tests (what exists, what is covered, how to run), error handling, logging, duplicated logic, dead code, TODO/FIXME list, race conditions, performance concerns, security concerns.

13. Where to add the next code
   - Exact files/folders and the pattern to copy for: a new cause rule, a new detector, a new prediction rule, a new recommendation entry, a new config constant, a new test, a new message template.

14. Open questions
   - What you could not determine and which file or person would answer it.

OUTPUT
Write everything to ANALYSIS_BACKEND_SUMMARY.md at the repo root. In your final chat message reply only with: the file path, its line count, and the 5 most important findings.
```
