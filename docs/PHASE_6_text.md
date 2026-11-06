# PHASE 6 — English text (templates and renderers)

Read `AGENT_CONTEXT.md`, `PHASE_5_6_7_CONTRACTS.md` first. Phases 0–5 are done.
Spec: `docs/part2_minimal_logic_flow_v0_3.md` §9 (Cases 1–3 and the system messages). The sample text in §9 is **golden**: match it word for word.

**Goal:** turn structured facts into English text, only here (Rule 8). Templates are keyed by id. No Thai. No logic about *what* to recommend.

## Files
```
identity/text/__init__.py
identity/text/templates_en.py      (data only: id -> template string)
identity/text/render.py            (renderers, formatters)
tests/test_text_templates.py
tests/test_text_render.py          (golden Cases 1–3, system messages, formatting)
```
Small additive edits allowed (contracts §2): a missing fact key in Phase 2/4/5 output; `buildApplyPlan` `summary` keys `activityType` and `activityTime` for non-aeration applies. List any in Deviations.

## 1. API (contracts §3.5, plus one addition)
```python
renderRecommendation(draft, pond, cfg=DEFAULT_CONFIG) -> RenderedText          # same signature as Renderer
renderPlan(rec: Recommendation, pond, cfg=DEFAULT_CONFIG) -> str               # the "Plan:" line; built from proposedActivities, urgency, validFrom/validUntil
renderDiagnostic(report, cfg=DEFAULT_CONFIG) -> RenderedDiagnostic
renderPrediction(pred, cfg=DEFAULT_CONFIG) -> RenderedPrediction
renderNotification(n, pondTz, cfg=DEFAULT_CONFIG) -> str
renderApplySummary(summary, pondTz) -> str
DISCLAIMER_TEXT = "Automated estimate based on your logs and sensor data. Not a guarantee."   # exported constant; the app shows it on urgent recs
```
`renderPlan` is new (the Recommendation model has no plan field, and the plan line depends on fixed vs. pick-window). Add it to the contracts file under 3.5.

## 2. Formatting rules (tested)
- Times: pond-local `HH:MM` via `localTime(t, tz)`; ranges `20:00–06:00` (en dash); plan arrows ` → `. Never print UTC.
- kg: one decimal (`6.0 kg`). Percent of biomass: one decimal (`about 1.5%`). Temperature: `31 °C` (drop `.0`, otherwise one decimal). Fractions: `0.25 → 1/4`, `0.5 → 1/2`, other → percent (`30%`). Hours: integer if whole.
- "tonight" is used for the night-based predictions (`PRED_DO_*`) and for AERATE.
- Render with `str.format_map`. A missing fact raises `KeyError` (never print `None`, `{}` or an empty slot). Optional fragments (e.g. temperature in "Based on") are omitted cleanly when the fact is `None`.
- **Rule 5 wording:** say "logged" or "planned", never "not fed", "did not", "not aerated". Test this with a forbidden-phrase scan over all templates.
- English only: a test scans every template for Thai characters (`\u0E00–\u0E7F`).

## 3. Diagnostic (`renderDiagnostic`)
Returns `RenderedDiagnostic(title="Why this may have happened", causes=tuple[CauseText(heading, body)], fallback: str|None, footer, revisedLabel: str|None)`.
`revisedLabel = "Updated after activity change"` when `report.revisedAt` is not None. Footer: `Based on your logged activities and sensor data. If something is missing from your log, this explanation may be incomplete.`
`noClearCause` → `causes=()` and `fallback="We could not find a clear cause from the data available. Check your aeration and feeding records and look at the pond."`

Cause templates (headings and bodies). The first two are **golden** (Case 1); the rest are the author's drafts for expert review (spec §10) and may be reworded later, so keep them in `templates_en.py` only:

| ruleId | heading | body |
|---|---|---|
| `DO_C_FEED` | Feeding raised oxygen demand. | You fed {kg} kg at {time} (about {pct}% of the fish weight). Fish and bacteria use more oxygen while digesting and breaking down feed. *(if `kg` is None: "Feeding was logged at {time}." in place of the first sentence)* |
| `DO_C_NIGHT` | It is night. | Plants and algae stop making oxygen after sunset. *(if `aerationLogged` is False, append: "No aeration was logged tonight.")* |
| `DO_C_TEMP` | Warm water holds less oxygen. | Water temperature was above the optimal range ({tempValue} °C at {tempTime}). Warmer water holds less oxygen, and fish use more of it. |
| `NH3_C_FEED` | Feeding added to the ammonia load. | You fed {kg} kg at {time} (about {pct}% of the fish weight). Uneaten feed and fish waste break down into ammonia. *(same fallback for `kg` None)* |
| `NO2_C_NH3` | Ammonia was above the optimal range recently. | Bacteria turn ammonia into nitrite, so nitrite can rise after an ammonia peak. |
| `TEMP_C_TIME` (High / Low) | It is the warm / cold part of the day. | Water temperature usually peaks in the afternoon ({window}). / Water temperature usually drops late at night and early in the morning ({window}). |
| `PH_C_TIME` (High / Low) | pH usually rises in the afternoon. / pH usually falls before sunrise. | Algae and plants use carbon dioxide during the day, which raises pH, mostly {window}. / Fish and bacteria release carbon dioxide overnight, which lowers pH, mostly {window}. |
| `SAL_C_WATERCHG` | A recent water change may have changed salinity. | A water change of {fraction} of the pond was logged at {time}. New water with a different salinity can shift the pond's salinity. |

`{window}` comes from the `cfg` window for that direction, formatted `11:00–16:00`. Numbered display ("1.", "2.") is the app's job; `causes` carries no numbers.

## 4. Prediction (`renderPrediction`)
`RenderedPrediction(headline, conditions: tuple[(label, met: bool)], footer=DISCLAIMER_TEXT)`.
- `PRED_DO_NIGHT`, `PRED_DO_REPEAT`: `DO may fall into the High Risk range tonight ({start}–{end}).` (golden for Case 2: `20:00–06:00`)
- `PRED_NH3_RISE`: `Ammonia may reach the High Risk range in the next {hours} hours.` (golden: 12; hours from `cfg.nh3RiseHorizonHours`)
- `conditions` from `evidence["conditions"]` (all conditions, met and not met). Labels (cfg numbers inserted): DO_NIGHT: C1 "Heavy meal in the evening", C2 "Hot water", C3 "Less than {minAerationHours} hours of aeration logged or planned". DO_REPEAT: C1 "Low DO on {repeatMinNights} of the last {repeatWindowNights} nights", C2 "Not yet in the usual risk period", C3 same as above, C4 "Hot water". NH3_RISE: C1 "Heavy feeding in the last 24 hours", C2 "Ammonia above the optimal range", C3 "No water change in the last {wcLookbackHours} h or planned", C4 "Hot water".

## 5. Recommendation (`renderRecommendation`, `renderPlan`)
Golden text is in spec §9 Cases 2 and 3. Texts per `textKey` (drafts by the author where the spec has no sample; expert review pending):

**`AERATE.prediction`** (Case 2 golden)
- title: `Run aeration tonight: DO may drop too low`
- reason: `{You planned|You fed} {mealKg} kg of feed at {mealTime} (about {mealPct}% of the fish weight) and {aerationClause}. Oxygen use rises after feeding, and plants stop making oxygen after sunset. DO may fall into the High Risk range between {riskStart} and {riskEnd}.`
  `You planned` when `mealIsPlanned`, else `You fed`. `aerationClause`: `no aeration is planned overnight` when `aerationHours == 0`, else `only {h} hours of aeration are planned overnight`.
  For a source with `hitNights` (`PRED_DO_REPEAT`) use: `DO fell into the High Risk range on {n} of the last {nightsChecked} nights around this time, and less than {minAerationHours} hours of aeration is planned tonight. Oxygen use rises after feeding, and plants stop making oxygen after sunset.`
- basedOn: `{Planned|Logged} feeding {mealTime} · no aeration planned {riskStart}–{riskEnd} · water temperature {tempValue} °C` (omit the feeding part for REPEAT; omit temperature when None)
- guidance (three items, golden): `Keep aeration running until about {planEnd}.` · `Consider a smaller meal tonight to reduce oxygen demand.` · `Check the DO reading in the app around midnight.`

**`AERATE.diagnostic`**: title `Run aeration now: dissolved oxygen is low`; reason `Dissolved oxygen is already low and may keep falling. Fish are under stress when oxygen is low.`; basedOn `DO at {doLastSeverity} level since {doOnsetAt}`; guidance: `Start aeration now and keep it running for about 4 hours.` · `Do not feed until DO is back in the optimal range.` · `Check the DO reading again in an hour.` (use `cfg.aerateDiagDurationHours` for "4").
**`AERATE.both`**: reason = `Dissolved oxygen is already low.` + the `AERATE.prediction` reason; basedOn = both fragments joined with ` · `; guidance from `.prediction`.

**`WATER_CHANGE.prediction`** (Case 3 golden)
- title: `Plan a partial water change: ammonia may keep rising`
- reason: `You fed about {totalMealPct}% of the fish weight in the last 24 hours, ammonia is already above the optimal range, and no water change is planned. Ammonia may reach the High Risk range within about {horizonHours} hours.`
- basedOn: `Feeding in the last 24 h: {totalKg} kg · NH3 at {nh3Zone} level · no water change in the last 48 h or planned` (zone name rendered `Stress`, `High Risk`, `Critical`)
- guidance: `Replace about {fraction} of the pond water. Use water with a similar temperature and salinity.` · `Consider smaller meals while ammonia is high.`
**`WATER_CHANGE.episode`**: title `Do a partial water change now: {Ammonia|Nitrite} is high` (urgent) / `Plan a partial water change: {Ammonia|Nitrite} is above the optimal range` (non_urgent); reason `{Ammonia|Nitrite} is at {lastSeverity} level. Both are harmful to fish, and a partial water change dilutes them.`; basedOn `{NH3|NO2-N} at {lastSeverity} level since {onsetAt}`; guidance as above.
**`WATER_CHANGE.both`**: episode reason + prediction reason; basedOn joined.
**`ADD_ALKALINITY.detector`**: title `Plan alkalinity support: pH is swinging`; reason `pH moved by about {maxSwing} or more on {hitDays} of the last {windowDays} days. Large daily pH swings stress fish.`; basedOn `pH swing on {hitDays} of the last {windowDays} days`; guidance: `Check alkalinity with a test kit before adding anything.` · `Add alkalinity material in small amounts and record how much you use.` · `Check pH again a few hours later.` (no quantity is ever proposed).

**`renderPlan(rec, pond, cfg)`**
- urgent AERATE (golden): `Aeration {start} → {end} (if you apply after {start}, it starts when you apply)`
- urgent WATER_CHANGE: `Water change {fraction} of the pond, started when you apply`
- non_urgent WATER_CHANGE: `Water change {fraction} of the pond — choose a time before {validUntil local, "DD Mon HH:MM"}`
- ADD_ALKALINITY: `Add alkalinity — choose a time before {validUntil local}; enter the amount yourself`

## 6. Notifications and apply summary
`renderNotification` by `reasonKey` (facts per contracts §3.4):
- `rec.changed.activity_edit` → `Updated after you changed {Feeding|an activity} at {time}.` (type name capitalised from `activityType`, else "an activity"; time = local `tFrom`) (**golden** for the Feeding case)
- `rec.changed.urgency_raised` → `This recommendation is now urgent.`
- `rec.expired.no_longer_applies` → if `afterActivityEdit` and `PRED_DO_NIGHT` in `sourceRuleIds` and its end reason is `conditions_gone`: `No longer needed: the planned meal was reduced.` (**golden**); else `No longer needed: the conditions behind this recommendation have changed.`
- `rec.expired.time_window_over` → `Expired: the time window for this recommendation has ended.`
- `rec.created.urgent` → `A new urgent recommendation is available.`
- `rec.unsnoozed.snooze_over` → `Reminder: this recommendation is available again.` / `rec.unsnoozed.urgency_raised` → `This recommendation was snoozed but is now urgent.`
- `prediction.ended.mitigated` → DO rules: `Resolved: aeration is now planned for tonight.` (**golden**); NH3: `Resolved: a water change is now planned.`
- `prediction.ended.conditions_gone` → `No longer expected: conditions have changed.`; `.window_over` → `This prediction period has ended.`
- `activity.replaced.by_recommendation` → `Your aeration {before} was shortened to {after}.` / `... was replaced by the recommended plan.` (when `after` is empty)

`renderApplySummary(summary, tz)` (golden example from §9, D15 and D17 cases):
- done kept: `Added aeration 19:00–22:00 and 02:00–06:00. Your existing 22:00–02:00 was kept.`
- user pending shortened (D15): `Added aeration 22:00–03:00. Your pending aeration 21:00–23:00 was shortened to 21:00–22:00.`; split: `... was split into 20:00–22:00 and 03:00–06:00.`; deleted: `... was replaced.`
- `coveredByDone`: `Your logged aeration already covers this period, so nothing new was added.`
- non-aeration: `Added {water change ({fraction}) | alkalinity} at {time}.`
Join several pieces/changes with "and" / sentences as in the samples.

## 7. Tests (write first; compare golden text after `" ".join(text.split())`, because the spec wraps lines)
**test_text_templates.py:** every `ruleId` (8 causes), every prediction `ruleId` and condition label, every `textKey`, every notification `reasonKey`, and every summary shape has a template; no template is unused; no Thai characters; no empty strings; no forbidden Rule 5 phrases; every `{placeholder}` in a template is supplied by a documented fact.
**test_text_render.py:**
1. **Case 1 golden:** report with causes `[DO_C_FEED(kg 6.0, pct 1.5, 18:30), DO_C_NIGHT(aerationLogged False)]` → heading/body text, footer.
2. Fallback text for `noClearCause`; `revisedLabel` only when `revisedAt` is set.
3. All 8 cause templates render with realistic facts; High/Low variants of `TEMP_C_TIME` and `PH_C_TIME`; `kg=None` fallback; `aerationLogged=True` drops the "No aeration" sentence.
4. **Case 2 golden:** prediction headline `DO may fall into the High Risk range tonight (20:00–06:00).`; rec title, reason, basedOn, three guidance items, plan line; `You fed` vs `You planned`; no temperature → fragment omitted; partial aeration clause.
5. `AERATE.diagnostic`, `AERATE.both`, REPEAT variant, `WATER_CHANGE.episode` (urgent and non_urgent, NH3 and NO2_N), `ADD_ALKALINITY` (no quantity anywhere in the output).
6. **Case 3 golden:** prediction headline, title, reason, basedOn, guidance. `renderPlan` non_urgent contains `1/4 of the pond` and `choose a time`. (The spec sample says "within the next 24 hours" but the window rule gives up to 48 h; see Questions.)
7. Notifications: every golden message above; the missing-activity-type fallback.
8. Apply summaries: the done-kept sample (golden), D15 shorten / split / delete, `coveredByDone`.
9. Timezone: the same UTC instant renders different clock times for `Asia/Bangkok` and `America/New_York`.
10. Formatters: `31.0 → "31 °C"`, `31.5 → "31.5 °C"`; `0.25 → "1/4"`, `0.3 → "30%"`; `6 → "6.0"`; rounding at x.x5.
11. Missing fact → `KeyError` (not silent); inputs not mutated; same input → same output.

## 8. Definition of Done
- [ ] All tests pass; all old tests pass
- [ ] Case 1, 2, 3 and every system message match the spec word for word
- [ ] All wording lives in `templates_en.py`; `render.py` has no English sentences
- [ ] No Thai, no Rule 5 violations, no `datetime.now()`, no raw `.hour/.date()`
- [ ] `docs/PROGRESS.md` row; `docs/BACKLOG.md`: "expert review of drafted cause texts and guidance (spec §10)"

## Out of scope
Deciding what to recommend, Thai text (O7), UI layout, localization, the Thai severity descriptions from engine file 09.

## Questions to raise if hit
Case 3 plan window ("next 24 hours" vs the end-of-next-day rule); activity type missing from `Trigger` (Phase 7 fills it best-effort); any golden text that conflicts with Rule 5 (keep the golden text, report the conflict).
