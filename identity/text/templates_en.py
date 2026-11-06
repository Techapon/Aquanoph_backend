"""English text templates keyed by id (Phase 6). Data only; no logic here.

Rendered with str.format_map. Missing facts raise KeyError.
"""
DIAGNOSTIC_TITLE = "Why this may have happened"

DIAGNOSTIC_FOOTER = "Based on your logged activities and sensor data. If something is missing from your log, this explanation may be incomplete."

DIAGNOSTIC_FALLBACK = "We could not find a clear cause from the data available. Check your aeration and feeding records and look at the pond."

DIAGNOSTIC_REVISED_LABEL = "Updated after activity change"

DISCLAIMER_TEXT = "Automated estimate based on your logs and sensor data. Not a guarantee."

#: (ruleId) -> (heading, body)
CAUSE_TEMPLATES: dict[str, tuple[str, str]] = {
    "DO_C_FEED": (
        "Feeding raised oxygen demand.",
        "You fed {kg} kg at {time} (about {pct}% of the fish weight). Fish and bacteria use more oxygen while digesting and breaking down feed.",
    ),
    "DO_C_FEED_UNKNOWN": (
        "Feeding raised oxygen demand.",
        "Feeding was logged at {time}. Fish and bacteria use more oxygen while digesting and breaking down feed.",
    ),
    "DO_C_NIGHT": (
        "It is night.",
        "Plants and algae stop making oxygen after sunset.",
    ),
    "DO_C_NIGHT_NO_AERATION": (
        "It is night.",
        "Plants and algae stop making oxygen after sunset. No aeration was logged tonight.",
    ),
    "DO_C_TEMP": (
        "Warm water holds less oxygen.",
        "Water temperature was above the optimal range ({tempValue} °C at {tempTime}). Warmer water holds less oxygen, and fish use more of it.",
    ),
    "NH3_C_FEED": (
        "Feeding added to the ammonia load.",
        "You fed {kg} kg at {time} (about {pct}% of the fish weight). Uneaten feed and fish waste break down into ammonia.",
    ),
    "NH3_C_FEED_UNKNOWN": (
        "Feeding added to the ammonia load.",
        "Feeding was logged at {time}. Uneaten feed and fish waste break down into ammonia.",
    ),
    "NO2_C_NH3": (
        "Ammonia was above the optimal range recently.",
        "Bacteria turn ammonia into nitrite, so nitrite can rise after an ammonia peak.",
    ),
    "TEMP_C_TIME_HIGH": (
        "It is the warm part of the day.",
        "Water temperature usually peaks in the afternoon ({window}).",
    ),
    "TEMP_C_TIME_LOW": (
        "It is the cold part of the day.",
        "Water temperature usually drops late at night and early in the morning ({window}).",
    ),
    "PH_C_TIME_HIGH": (
        "pH usually rises in the afternoon.",
        "Algae and plants use carbon dioxide during the day, which raises pH, mostly {window}.",
    ),
    "PH_C_TIME_LOW": (
        "pH usually falls before sunrise.",
        "Fish and bacteria release carbon dioxide overnight, which lowers pH, mostly {window}.",
    ),
    "SAL_C_WATERCHG": (
        "A recent water change may have changed salinity.",
        "A water change of {fraction} of the pond was logged at {time}. New water with a different salinity can shift the pond's salinity.",
    ),
}

#: (ruleId, condition) -> label
PREDICTION_CONDITION_LABELS: dict[str, dict[str, str]] = {
    "PRED_DO_NIGHT": {
        "C1": "Heavy meal in the evening",
        "C2": "Hot water",
        "C3": "Less than {minAerationHours} hours of aeration logged or planned",
    },
    "PRED_DO_REPEAT": {
        "C1": "Low DO on {repeatMinNights} of the last {repeatWindowNights} nights",
        "C2": "Not yet in the usual risk period",
        "C3": "Less than {minAerationHours} hours of aeration logged or planned",
        "C4": "Hot water",
    },
    "PRED_NH3_RISE": {
        "C1": "Heavy feeding in the last 24 hours",
        "C2": "Ammonia above the optimal range",
        "C3": "No water change in the last {wcLookbackHours} h or planned",
        "C4": "Hot water",
    },
}

PREDICTION_HEADLINES: dict[str, str] = {
    "PRED_DO_NIGHT": "DO may fall into the High Risk range tonight ({start}–{end}).",
    "PRED_DO_REPEAT": "DO may fall into the High Risk range tonight ({start}–{end}).",
    "PRED_NH3_RISE": "Ammonia may reach the High Risk range in the next {hours} hours.",
}

#: textKey -> (title, reason, basedOn, guidance tuple)
RECOMMENDATION_TEMPLATES: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "AERATE.prediction": (
        "Run aeration tonight: DO may drop too low",
        "{mealSentence} and {aerationClause}. Oxygen use rises after feeding, and plants stop making oxygen after sunset. DO may fall into the High Risk range between {riskStart} and {riskEnd}.",
        "{feedingFragment}{aerationFragment}{tempFragment}",
        (
            "Keep aeration running until about {planEnd}.",
            "Consider a smaller meal tonight to reduce oxygen demand.",
            "Check the DO reading in the app around midnight.",
        ),
    ),
    "AERATE.diagnostic": (
        "Run aeration now: dissolved oxygen is low",
        "Dissolved oxygen is already low and may keep falling. Fish are under stress when oxygen is low.",
        "DO at {doLastSeverity} level since {doOnsetAt}",
        (
            "Start aeration now and keep it running for about {diagHours} hours.",
            "Do not feed until DO is back in the optimal range.",
            "Check the DO reading again in an hour.",
        ),
    ),
    "AERATE.both": (
        "Run aeration now: dissolved oxygen is low",
        "Dissolved oxygen is already low. {mealSentence} and {aerationClause}. Oxygen use rises after feeding, and plants stop making oxygen after sunset. DO may fall into the High Risk range between {riskStart} and {riskEnd}.",
        "{diagFragment} · {predFragment}",
        (
            "Keep aeration running until about {planEnd}.",
            "Consider a smaller meal tonight to reduce oxygen demand.",
            "Check the DO reading in the app around midnight.",
        ),
    ),
    "WATER_CHANGE.prediction": (
        "Plan a partial water change: ammonia may keep rising",
        "You fed about {totalMealPct}% of the fish weight in the last 24 hours, ammonia is already above the optimal range, and no water change is planned. Ammonia may reach the High Risk range within about {horizonHours} hours.",
        "Feeding in the last 24 h: {totalKg} kg · NH3 at {nh3Zone} level · no water change in the last 48 h or planned",
        (
            "Replace about {fraction} of the pond water. Use water with a similar temperature and salinity.",
            "Consider smaller meals while ammonia is high.",
        ),
    ),
    "WATER_CHANGE.episode.urgent": (
        "Do a partial water change now: {speciesNoun} is high",
        "{speciesNoun} is at {lastSeverity} level. Both are harmful to fish, and a partial water change dilutes them.",
        "{paramName} at {lastSeverity} level since {onsetAt}",
        (
            "Replace about {fraction} of the pond water. Use water with a similar temperature and salinity.",
            "Consider smaller meals while ammonia is high.",
        ),
    ),
    "WATER_CHANGE.episode.nonUrgent": (
        "Plan a partial water change: {speciesNoun} is above the optimal range",
        "{speciesNoun} is at {lastSeverity} level. Both are harmful to fish, and a partial water change dilutes them.",
        "{paramName} at {lastSeverity} level since {onsetAt}",
        (
            "Replace about {fraction} of the pond water. Use water with a similar temperature and salinity.",
            "Consider smaller meals while ammonia is high.",
        ),
    ),
    "WATER_CHANGE.both": (
        "Plan a partial water change: ammonia may keep rising",
        "{episodeReason} {predictionReason}",
        "{episodeBasedOn} · {predictionBasedOn}",
        (
            "Replace about {fraction} of the pond water. Use water with a similar temperature and salinity.",
            "Consider smaller meals while ammonia is high.",
        ),
    ),
    "ADD_ALKALINITY.detector": (
        "Plan alkalinity support: pH is swinging",
        "pH moved by about {maxSwing} or more on {hitDays} of the last {windowDays} days. Large daily pH swings stress fish.",
        "pH swing on {hitDays} of the last {windowDays} days",
        (
            "Check alkalinity with a test kit before adding anything.",
            "Add alkalinity material in small amounts and record how much you use.",
            "Check pH again a few hours later.",
        ),
    ),
}

REASON_SENTENCES: dict[str, str] = {
    "noMeal": "",
    "noAeration": "no aeration is planned overnight",
    "lowAeration": "only {h} hours of aeration are planned overnight",
    "wcEpisode": "{speciesNoun} is at {lastSeverity} level. Both are harmful to fish, and a partial water change dilutes them.",
    "wcPrediction": "You fed about {totalMealPct}% of the fish weight in the last 24 hours, ammonia is already above the optimal range, and no water change is planned. Ammonia may reach the High Risk range within about {horizonHours} hours.",
}

BASED_ON_FRAGMENTS: dict[str, str] = {
    "plannedFeeding": "Planned feeding {mealTime}",
    "noAerationPlanned": "no aeration planned {riskStart}–{riskEnd}",
    "tempValue": "water temperature {tempValue} °C",
    "doLow": "Dissolved oxygen is already low.",
    "doRisk": "DO may fall into the High Risk range tonight.",
    "wcEpisode": "{paramName} at {lastSeverity} level since {onsetAt}",
    "wcPrediction": "Feeding in the last 24 h: {totalKg} kg · NH3 at {nh3Zone} level · no water change in the last 48 h or planned",
}

PLAN_LINES: dict[str, str] = {
    "aerate.urgent": "Aeration {start} → {end} (if you apply after {start}, it starts when you apply)",
    "wc.urgent": "Water change {fraction} of the pond, started when you apply",
    "wc.nonUrgent": "Water change {fraction} of the pond — choose a time before {until}",
    "alkalinity": "Add alkalinity — choose a time before {until}; enter the amount yourself",
}

SUMMARY_TEMPLATES: dict[str, str] = {
    "coveredByDone": "Your logged aeration already covers this period, so nothing new was added.",
    "aerateAdded": "Added aeration {intervals}.",
    "nonAerateAdded": "Added {entry} at {time}.",
    "aerateReplaced": "Your aeration {before} was replaced.",
    "aerateShortened": "Your aeration {before} was shortened to {after}.",
    "aerateSplit": "Your aeration {before} was split into {afterFirst} and {afterSecond}.",
    "existingKept": "Your existing {kept} was kept.",
}


def notificationTemplateKey(kind: str, reasonKey: str, facts: dict) -> str | None:
    if kind == "recChanged" and reasonKey == "rec.changed.activity_edit":
        return "rec.changed.activity_edit.feeding" if facts.get("activityType") == "feeding" or facts.get("activityType") is None else "rec.changed.activity_edit.other"
    mapping = {
        ("recChanged", "rec.changed.urgency_raised"): "rec.changed.urgency_raised",
        ("recExpired", "rec.expired.no_longer_applies"): (
            "rec.expired.no_longer_applies.meal_reduced"
            if facts.get("afterActivityEdit") and "PRED_DO_NIGHT" in (facts.get("sourceRuleIds") or ())
            else "rec.expired.no_longer_applies.other"
        ),
        ("recExpired", "rec.expired.time_window_over"): "rec.expired.time_window_over",
        ("urgentRecCreated", "rec.created.urgent"): "rec.created.urgent",
        ("recUnsnoozed", "rec.unsnoozed.snooze_over"): "rec.unsnoozed.snooze_over",
        ("recUnsnoozed", "rec.unsnoozed.urgency_raised"): "rec.unsnoozed.urgency_raised",
        ("predictionEnded", "prediction.ended.mitigated"): (
            "prediction.ended.mitigated.nh3" if "NH3" in str(facts.get("ruleId", "")) else "prediction.ended.mitigated.do"
        ),
        ("predictionEnded", "prediction.ended.conditions_gone"): "prediction.ended.conditions_gone",
        ("predictionEnded", "prediction.ended.window_over"): "prediction.ended.window_over",
        ("activityReplaced", "activity.replaced.by_recommendation"): (
            "activity.replaced.by_recommendation.deleted" if not facts.get("after")
            else "activity.replaced.by_recommendation.shortened" if len(facts["after"]) == 1
            else "activity.replaced.by_recommendation.split"
        ),
    }
    return mapping.get((kind, reasonKey))


NOTIFICATION_TEMPLATES: dict[str, str] = {
    "rec.changed.activity_edit.feeding": "Updated after you changed Feeding at {time}.",
    "rec.changed.activity_edit.other": "Updated after you changed an activity at {time}.",
    "rec.changed.urgency_raised": "This recommendation is now urgent.",
    "rec.expired.no_longer_applies.meal_reduced": "No longer needed: the planned meal was reduced.",
    "rec.expired.no_longer_applies.other": "No longer needed: the conditions behind this recommendation have changed.",
    "rec.expired.time_window_over": "Expired: the time window for this recommendation has ended.",
    "rec.created.urgent": "A new urgent recommendation is available.",
    "rec.unsnoozed.snooze_over": "Reminder: this recommendation is available again.",
    "rec.unsnoozed.urgency_raised": "This recommendation was snoozed but is now urgent.",
    "prediction.ended.mitigated.do": "Resolved: aeration is now planned for tonight.",
    "prediction.ended.mitigated.nh3": "Resolved: a water change is now planned.",
    "prediction.ended.conditions_gone": "No longer expected: conditions have changed.",
    "prediction.ended.window_over": "This prediction period has ended.",
    "activity.replaced.by_recommendation.deleted": "Your aeration {before} was replaced.",
    "activity.replaced.by_recommendation.shortened": "Your aeration {before} was shortened to {after}.",
    "activity.replaced.by_recommendation.split": "Your aeration {before} was split into {afterFirst} and {afterSecond}.",
}
