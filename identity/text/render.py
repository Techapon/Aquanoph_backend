"""English rendering (Phase 6). All wording lives in templates_en.py; no sentences here."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.helpers import localTime
from identity.analysis.models import DiagnosticReport, Notification, Recommendation
from identity.parameters.pond_parameter_enum import PondParameters
from identity.text import templates_en as T
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection


# Dataclasses for rendered text outputs
from identity.recommendation.types import RenderedText  # Renderer return type (contracts §3.1)


@dataclass(frozen=True)
class CauseText:
    heading: str
    body: str


@dataclass(frozen=True)
class RenderedDiagnostic:
    title: str
    causes: tuple[CauseText, ...]
    fallback: str | None
    footer: str
    revisedLabel: str | None


@dataclass(frozen=True)
class RenderedPrediction:
    headline: str
    conditions: tuple[tuple[str, bool], ...]
    footer: str


def _local(t: datetime | None, tz: str) -> str:
    if t is None:
        return ""
    return localTime(t, tz).strftime("%H:%M")


def _fmt_temp(v) -> str | None:
    if v is None:
        return None
    r = round(float(v), 1)
    return f"{int(r)} °C" if r == int(r) else f"{r} °C"


def _fmt_tempNoUnit(v) -> str | None:
    if v is None:
        return None
    r = round(float(v), 1)
    return str(int(r)) if r == int(r) else str(r)


def _fmt_kg(v) -> str | None:
    return None if v is None else f"{float(v):.1f}"


def _fmt_percent(v) -> str | None:
    return None if v is None else f"{float(v):.1f}"


def _fmt_fraction(v) -> str | None:
    if v is None:
        return None
    if v == 0.25:
        return "1/4"
    if v == 0.5:
        return "1/2"
    return f"{int(v * 100)}%"


def _fmt_hours(v) -> str | None:
    return None if v is None else str(int(v)) if float(v).is_integer() else str(v)


def _zoneName(z) -> str | None:
    if z is None:
        return None
    mapping = {
        ThresholdLevelType.Optimal: "Optimal",
        ThresholdLevelType.Stress: "Stress",
        ThresholdLevelType.HighRisk: "High Risk",
        ThresholdLevelType.Critical: "Critical",
        SeverityLevelType.Optimal: "Optimal",
        SeverityLevelType.Stress: "Stress",
        SeverityLevelType.ElevatedRisk: "Elevated Risk",
        SeverityLevelType.Critical: "Critical",
    }
    return mapping.get(z, str(z).split(".")[-1].replace("_", " "))


def renderDiagnostic(report: DiagnosticReport, cfg=DEFAULT_CONFIG):
    causes: list[CauseText] = []
    tz = report.pondSnapshot.timezone
    for c in report.causes:
        ruleId = c.ruleId
        facts = dict(c.facts)
        if ruleId == "DO_C_FEED":
            if facts.get("kg") is None:
                ruleId = "DO_C_FEED_UNKNOWN"
            else:
                facts["kg"] = _fmt_kg(facts["kg"])
                facts["pct"] = _fmt_percent(facts.get("pct"))
        if ruleId == "DO_C_NIGHT" and not facts.get("aerationLogged", False):
            ruleId = "DO_C_NIGHT_NO_AERATION"
        if ruleId == "NH3_C_FEED":
            if facts.get("kg") is None:
                ruleId = "NH3_C_FEED_UNKNOWN"
            else:
                facts["kg"] = _fmt_kg(facts["kg"])
                facts["pct"] = _fmt_percent(facts.get("pct"))
        if ruleId in ("TEMP_C_TIME", "PH_C_TIME"):
            suffix = "HIGH" if facts.get("direction") == ThresholdDirection.High else "LOW"
            ruleId = f"{ruleId}_{suffix}"
            win = (cfg.tempHighWindow if (ruleId.startswith("TEMP") and suffix == "HIGH") else
                   cfg.tempLowWindow if ruleId.startswith("TEMP") else
                   cfg.phHighWindow if suffix == "HIGH" else cfg.phLowWindow)
            facts["window"] = f"{win[0]:02d}:00–{win[1]:02d}:00"
        if ruleId == "DO_C_TEMP":
            facts["tempValue"] = _fmt_tempNoUnit(facts.get("tempValue"))
        if ruleId == "SAL_C_WATERCHG":
            facts["fraction"] = _fmt_fraction(facts.get("fraction"))
        heading, body = T.CAUSE_TEMPLATES[ruleId]
        # times in facts are naive-UTC datetimes; render pond-local
        for key in ("feedTime", "waterChangeTime", "tempTime", "onsetAt", "time"):
            if key in facts and isinstance(facts[key], datetime):
                facts[key] = _local(facts[key], tz)
        causes.append(CauseText(heading=heading, body=body.format_map(facts)))

    fallback = T.DIAGNOSTIC_FALLBACK if report.noClearCause else None
    revisedLabel = T.DIAGNOSTIC_REVISED_LABEL if report.revisedAt is not None else None
    return RenderedDiagnostic(
        title=T.DIAGNOSTIC_TITLE,
        causes=tuple(causes),
        fallback=fallback,
        footer=T.DIAGNOSTIC_FOOTER,
        revisedLabel=revisedLabel,
    )


def renderRecommendation(draft, pond, cfg=DEFAULT_CONFIG) -> RenderedText:
    tz = pond.timezone
    facts = dict(draft.facts)
    # times to local strings
    for key in ("mealTime", "riskStart", "riskEnd", "planStart", "planEnd",
                "doOnsetAt", "onsetAt", "deadline", "validUntil", "windowEnd"):
        if key in facts and isinstance(facts[key], datetime):
            facts[key] = _local(facts[key], tz)
    facts["mealKg"] = _fmt_kg(facts.get("mealKg"))
    facts["mealPct"] = _fmt_percent(facts.get("mealPct"))
    facts["totalMealPct"] = _fmt_percent(facts.get("totalMealPct"))
    facts["totalKg"] = _fmt_kg(facts.get("totalKg"))
    facts["tempValue"] = _fmt_tempNoUnit(facts.get("tempValue"))
    facts["fraction"] = _fmt_fraction(facts.get("fraction"))
    facts["maxSwing"] = _fmt_percent(facts.get("maxSwing"))
    facts["nh3Zone"] = _zoneName(facts.get("nh3Zone"))
    facts["doLastSeverity"] = _zoneName(facts.get("doLastSeverity"))
    facts["lastSeverity"] = _zoneName(facts.get("lastSeverity"))
    facts["aerationHours"] = _fmt_hours(facts.get("aerationHours"))
    facts["horizonHours"] = _fmt_hours(facts.get("horizonHours"))
    facts["hitNights"] = ", ".join(str(x) for x in facts["hitNights"]) if facts.get("hitNights") is not None else None
    facts["nightsChecked"] = str(facts["nightsChecked"]) if facts.get("nightsChecked") is not None else None
    facts["diagHours"] = str(cfg.aerateDiagDurationHours)
    facts["speciesNoun"] = "Ammonia" if (facts.get("parameter") in (PondParameters.NH3, None)) else "Nitrite"
    facts["paramName"] = "NH3" if facts["speciesNoun"] == "Ammonia" else "NO2-N"
    facts["hitDays"] = str(facts["hitDays"]) if facts.get("hitDays") is not None else None
    facts["windowDays"] = str(facts["windowDays"]) if facts.get("windowDays") is not None else None

    # Derived fragments (Rule 5 wording kept in templates_en below)
    if "mealSentence" not in facts:
        if facts.get("mealTime") and facts.get("mealKg") is not None:
            planned = "You planned" if facts.get("mealIsPlanned") else "You fed"
            facts["mealSentence"] = f"{planned} {facts['mealKg']} kg of feed at {facts['mealTime']} (about {facts['mealPct']}% of the fish weight)"
        else:
            facts["mealSentence"] = T.REASON_SENTENCES.get("noMeal", "")
    if "aerationClause" not in facts:
        if facts.get("aerationHours") in (0, "0"):
            facts["aerationClause"] = T.REASON_SENTENCES.get("noAeration", "")
        else:
            facts["aerationClause"] = T.REASON_SENTENCES.get("lowAeration", "").format(h=facts.get("aerationHours"))
    if "feedingFragment" not in facts:
        facts["feedingFragment"] = (
            f"{T.BASED_ON_FRAGMENTS['plannedFeeding'].format(mealTime=facts.get('mealTime'))} · "
            if facts.get("mealTime") else ""
        )
    if "aerationFragment" not in facts:
        facts["aerationFragment"] = (
            f"{T.BASED_ON_FRAGMENTS['noAerationPlanned'].format(riskStart=facts.get('riskStart'), riskEnd=facts.get('riskEnd'))} · "
            if facts.get("riskStart") else ""
        )
    if "tempFragment" not in facts:
        tempFrag = T.BASED_ON_FRAGMENTS.get("tempValue", "")
        facts["tempFragment"] = (f"{tempFrag.format(tempValue=facts.get('tempValue'))} · " if facts.get("tempValue") is not None else "")
    if "episodeReason" not in facts:
        facts["episodeReason"] = T.REASON_SENTENCES.get("wcEpisode", "").format(**facts) if facts.get("lastSeverity") else ""
    if "predictionReason" not in facts:
        facts["predictionReason"] = T.REASON_SENTENCES.get("wcPrediction", "").format(**facts) if facts.get("totalMealPct") is not None else ""
    if "episodeBasedOn" not in facts:
        facts["episodeBasedOn"] = T.BASED_ON_FRAGMENTS.get("wcEpisode", "").format(**facts) if facts.get("lastSeverity") else ""
    if "predictionBasedOn" not in facts:
        facts["predictionBasedOn"] = T.BASED_ON_FRAGMENTS.get("wcPrediction", "").format(**facts) if facts.get("totalMealPct") is not None else ""
    if "diagFragment" not in facts:
        facts["diagFragment"] = T.BASED_ON_FRAGMENTS.get("doLow", "").format(**facts)
    if "predFragment" not in facts:
        facts["predFragment"] = T.BASED_ON_FRAGMENTS.get("doRisk", "").format(**facts)

    template = T.RECOMMENDATION_TEMPLATES[draft.textKey]
    title = template[0].format_map(facts)
    reason = template[1].format_map(facts)
    basedOn = template[2].format_map(facts)
    guidance = tuple(g.format_map(facts) for g in template[3])
    return RenderedText(title=title, reason=reason, basedOn=basedOn, guidance=guidance)


def renderPlan(rec: Recommendation, pond, cfg=DEFAULT_CONFIG) -> str:
    tz = pond.timezone
    if rec.entryId == "AERATE" and rec.urgency.value == "urgent":
        pa = rec.proposedActivities[0]
        start = _local(pa.startTime, tz)
        end = _local(pa.endTime, tz)
        return T.PLAN_LINES["aerate.urgent"].format(start=start, end=end)
    if rec.entryId == "WATER_CHANGE" and rec.urgency.value == "urgent":
        frac = _fmt_fraction(rec.proposedActivities[0].fraction)
        return T.PLAN_LINES["wc.urgent"].format(fraction=frac)
    if rec.entryId == "WATER_CHANGE" and rec.urgency.value != "urgent":
        frac = _fmt_fraction(rec.proposedActivities[0].fraction)
        until = _local(rec.validUntil, tz)
        return T.PLAN_LINES["wc.nonUrgent"].format(fraction=frac, until=until)
    if rec.entryId == "ADD_ALKALINITY":
        until = _local(rec.validUntil, tz)
        return T.PLAN_LINES["alkalinity"].format(until=until)
    return ""


def renderNotification(n: Notification, pondTz: str, cfg=DEFAULT_CONFIG) -> str:
    facts = dict(n.facts)
    for key in ("time", "tFrom"):
        if key in facts and isinstance(facts[key], datetime):
            facts[key] = _local(facts[key], pondTz)
    key = T.notificationTemplateKey(n.kind, n.reasonKey, facts)
    if key is None:
        return ""
    return T.NOTIFICATION_TEMPLATES[key].format_map(facts)


def renderPrediction(pred, cfg=DEFAULT_CONFIG):
    from identity.text.templates_en import PREDICTION_HEADLINES, PREDICTION_CONDITION_LABELS
    ruleId = pred.ruleId
    headline_tpl = PREDICTION_HEADLINES.get(ruleId, "")
    conds = pred.evidence.get("conditions", {}) if pred.evidence else {}
    labels = PREDICTION_CONDITION_LABELS.get(ruleId, {})
    if ruleId == "PRED_NH3_RISE":
        headline = headline_tpl.format(hours=cfg.nh3RiseHorizonHours)
    elif ruleId in ("PRED_DO_NIGHT", "PRED_DO_REPEAT"):
        start = _local(pred.riskStart, "UTC") if pred.riskStart else ""
        end = _local(pred.riskEnd, "UTC") if pred.riskEnd else ""
        headline = headline_tpl.format(start=start, end=end)
    else:
        headline = headline_tpl
    conditions = []
    for key in sorted(conds.keys()):
        label: str = labels.get(key, key) or key
        label = label.format(minAerationHours=cfg.minAerationHours, repeatMinNights=cfg.repeatMinNights,
                             repeatWindowNights=cfg.repeatWindowNights, wcLookbackHours=cfg.wcLookbackHours)
        conditions.append((label, bool(conds[key])))
    return RenderedPrediction(headline=headline, conditions=tuple(conditions), footer=T.DISCLAIMER_TEXT)


def renderApplySummary(summary, pondTz: str) -> str:
    covered = summary.get("created") and not summary.get("modified") and not summary.get("kept") and summary.get("coveredByDone", False)
    tz = pondTz
    parts: list[str] = []

    created = summary.get("created", ())
    modified = summary.get("modified", ())
    kept = summary.get("kept", ())

    if summary.get("coveredByDone") and not created:
        return T.SUMMARY_TEMPLATES["coveredByDone"]

    if created:
        intervals = " and ".join(
            f"{_local(iv[0], tz)}–{_local(iv[1], tz)}" for iv in created if iv[1] is not None
        )
        if intervals:
            parts.append(T.SUMMARY_TEMPLATES["aerateAdded"].format(intervals=intervals))
        else:
            # non-aeration single activity at time
            entry = summary.get("entry", "activity")
            at = _local(created[0][0], tz) if created else ""
            frac = _fmt_fraction(summary.get("fraction"))
            parts.append(T.SUMMARY_TEMPLATES["nonAerateAdded"].format(entry=entry, fraction=frac, time=at))

    for m in modified:
        before = f"{_local(m['before'][0], tz)}–{_local(m['before'][1], tz)}"
        after = m.get("after", ())
        if not after:
            parts.append(T.SUMMARY_TEMPLATES["aerateReplaced"].format(before=before))
        elif len(after) == 1:
            afterStr = f"{_local(after[0][0], tz)}–{_local(after[0][1], tz)}"
            parts.append(T.SUMMARY_TEMPLATES["aerateShortened"].format(before=before, after=afterStr))
        else:
            a1 = f"{_local(after[0][0], tz)}–{_local(after[0][1], tz)}"
            a2 = f"{_local(after[1][0], tz)}–{_local(after[1][1], tz)}"
            parts.append(T.SUMMARY_TEMPLATES["aerateSplit"].format(before=before, afterFirst=a1, afterSecond=a2))

    if kept:
        keptStr = " and ".join(
            f"{_local(iv[0], tz)}–{_local(iv[1], tz)}" for iv in kept if iv[1] is not None
        )
        parts.append(T.SUMMARY_TEMPLATES["existingKept"].format(kept=keptStr))

    return " ".join(parts)
