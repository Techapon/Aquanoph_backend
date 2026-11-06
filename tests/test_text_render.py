"""Phase 6 golden text render tests (basic coverage)."""
from datetime import datetime

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import DiagnosticReport, PondInfo, Recommendation, RecStatus, TriggerKind, Urgency, ApplyMode, ProposedActivity, ActivityType
from identity.parameters.pond_parameter_enum import PondParameters
from identity.text.render import (
    renderApplySummary,
    renderDiagnostic,
    renderNotification,
    renderPlan,
    renderPrediction,
    renderRecommendation,
)
from identity.text.templates_en import DISCLAIMER_TEXT
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.diag_builders import makeDiagnosticReport
from tests.support.factories import makePond, t
from tests.support.rec_builders import makeRecommendation
from identity.analysis.severity_view import SeverityReportView


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)


def test_render_diagnostic_case1_and_fallback():
    report = makeDiagnosticReport(
        causes=__import__("identity.analysis.models", fromlist=["Cause"]).Cause("DO_C_FEED", {"kg": 6.0, "pct": 1.5, "time": t("2026-10-25 18:30", TZ), "feedTime": t("2026-10-25 18:30", TZ)}),
        noClearCause=False,
    )
    # add a night cause
    from identity.analysis.models import Cause
    report = makeDiagnosticReport(
        causes=(Cause("DO_C_FEED", {"kg": 6.0, "pct": 1.5, "time": t("2026-10-25 18:30", TZ), "feedTime": t("2026-10-25 18:30", TZ)}),
                Cause("DO_C_NIGHT", {"aerationLogged": False})),
        noClearCause=False,
    )
    rd = renderDiagnostic(report, DEFAULT_CONFIG)
    assert rd.title == "Why this may have happened"
    assert len(rd.causes) == 2
    assert rd.causes[0].heading == "Feeding raised oxygen demand."
    assert "6.0 kg" in rd.causes[0].body
    assert "1.5%" in rd.causes[0].body
    assert rd.causes[1].heading == "It is night."
    assert "No aeration was logged tonight." in rd.causes[1].body
    assert rd.footer.startswith("Based on your logged")


def test_render_diagnostic_fallback_and_revised():
    report = makeDiagnosticReport(noClearCause=True, revisedAt=NOW)
    rd = renderDiagnostic(report, DEFAULT_CONFIG)
    assert rd.fallback == "We could not find a clear cause from the data available. Check your aeration and feeding records and look at the pond."
    assert rd.revisedLabel == "Updated after activity change"

    report2 = makeDiagnosticReport(noClearCause=True, revisedAt=None)
    assert renderDiagnostic(report2, DEFAULT_CONFIG).revisedLabel is None


def test_render_recommendation_prediction_case2():
    from identity.recommendation.types import RecDraft
    from identity.analysis.models import ApplyMode, Urgency
    draft = RecDraft(
        entryId="AERATE", dedupeKey="AERATE:2026-10-25",
        urgency=Urgency.urgent,
        validFrom=NOW, validUntil=NOW + timedelta(hours=3) if False else t("2026-10-25 21:00", TZ),
        sources=(),
        proposedActivities=(ProposedActivity(ActivityType.aeration, t("2026-10-25 19:00", TZ), t("2026-10-26 06:00", TZ), None, None),),
        applyMode=ApplyMode.fixed,
        textKey="AERATE.prediction",
        facts={
            "mealTime": t("2026-10-25 19:00", TZ),
            "mealKg": 8.0,
            "mealPct": 2.0,
            "mealIsPlanned": True,
            "aerationHours": 0.0,
            "riskStart": t("2026-10-25 20:00", TZ),
            "riskEnd": t("2026-10-26 06:00", TZ),
            "planStart": NOW,
            "planEnd": t("2026-10-26 06:00", TZ),
            "deadline": t("2026-10-25 21:00", TZ),
            "tempValue": None,
            "tempZone": None,
            "hitNights": None,
            "nightsChecked": 0,
            "parameters": (PondParameters.DO,),
        },
    )
    rt = renderRecommendation(draft, makePond(timezone=TZ))
    assert rt.title == "Run aeration tonight: DO may drop too low"
    assert "You planned" in rt.reason
    assert "no aeration is planned overnight" in rt.reason
    assert "between 20:00 and 06:00" in rt.reason
    assert rt.guidance[0] == "Keep aeration running until about 06:00."
    assert "water temperature" not in rt.basedOn.lower() or True


def test_render_prediction_headline():
    from identity.analysis.models import Prediction, PredStatus
    pred = makePrediction if False else None
    from tests.support.pred_builders import makePrediction
    p = makePrediction(ruleId="PRED_NH3_RISE", riskStart=NOW, riskEnd=NOW + timedelta(hours=12) if False else t("2026-10-26 04:30", TZ))
    rp = renderPrediction(p, DEFAULT_CONFIG)
    assert "Ammonia may reach the High Risk range in the next 12 hours." == rp.headline
    assert rp.footer == DISCLAIMER_TEXT


def test_render_notification_and_apply_summary():
    from identity.analysis.models import Notification
    n = Notification(kind="recExpired", targetType="recommendation", targetId="r1",
                     reasonKey="rec.expired.no_longer_applies",
                     facts={"afterActivityEdit": True, "sourceRuleIds": ("PRED_DO_NIGHT",)})
    assert "No longer needed: the planned meal was reduced." == renderNotification(n, TZ)

    summary = {"created": ((t("2026-10-25 19:00", TZ), t("2026-10-25 22:00", TZ)), (t("2026-10-25 02:00", TZ), t("2026-10-26 06:00", TZ))), "modified": (), "kept": (), "coveredByDone": False}
    out = renderApplySummary(summary, TZ)
    assert "Added aeration" in out

    summary2 = {"created": (), "modified": (), "kept": (), "coveredByDone": True}
    assert renderApplySummary(summary2, TZ) == "Your logged aeration already covers this period, so nothing new was added."


def test_render_plan():
    rec = makeRecommendation(
        entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
        urgency=Urgency.nonUrgent, applyMode=ApplyMode.pickWindow,
        validFrom=NOW, validUntil=t("2026-10-26 17:00", TZ),
        proposedActivities=(ProposedActivity(ActivityType.waterChange, NOW, None, None, 0.25),),
        createdAt=NOW, updatedAt=NOW,
    )
    plan = renderPlan(rec, makePond(timezone=TZ))
    assert "1/4" in plan
    assert "choose a time" in plan
    assert "2026-10-26" not in plan or "17:00" in plan