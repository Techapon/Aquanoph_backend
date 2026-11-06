"""Recommendation catalog tests (Phase 5 §4)."""
from datetime import datetime, timedelta

import pytest

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import (
    ActivityStatus,
    ActivityType,
    ApplyMode,
    DiagStatus,
    ProposedActivity,
    Signal,
    SignalSource,
    SourceRef,
    Urgency,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.recommendation.catalog import buildDrafts
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.diag_builders import makeDiagnosticReport
from tests.support.factories import makePond, makeSnapshot, makeView, t


TZ = "Asia/Bangkok"
NOW = t("2026-10-25 16:30", TZ)


def predSig(code="PRED_DO_NIGHT", riskStart=None, riskEnd=None, scope="2026-10-25", srcId="pred:1", facts=None):
    return Signal(
        sourceType=SignalSource.prediction, sourceId=srcId, code=code,
        parameter=PondParameters.DO, active=True,
        riskStart=riskStart or t("2026-10-25 20:00", TZ),
        riskEnd=riskEnd or t("2026-10-26 06:00", TZ),
        peakSeverity=None, lastSeverity=None, scope=scope,
        facts=facts or {"firstMealTime": t("2026-10-25 19:00", TZ), "firstMealKg": 8.0,
                        "firstMealPct": 2.0, "aerationHours": 0.0},
    )


def epSig(param, lastSeverity, srcId="ep:1", scope=None, onset=None):
    return Signal(
        sourceType=SignalSource.episode, sourceId=srcId, code="DIAG_EPISODE",
        parameter=param, active=True, riskStart=None, riskEnd=None,
        peakSeverity=lastSeverity, lastSeverity=lastSeverity, scope=scope,
        facts={"onsetAt": onset or t("2026-10-25 20:00", TZ), "direction": None},
    )


def wcSig(param=PondParameters.NH3, severity=SeverityLevelType.Critical, srcId="ep:2"):
    return epSig(param, severity, srcId=srcId)


def detSig():
    return Signal(
        sourceType=SignalSource.detector, sourceId="PH_SWING:pond_1", code="PH_SWING",
        parameter=PondParameters.pH, active=True,
        riskStart=None, riskEnd=None, peakSeverity=None, lastSeverity=None, scope=None,
        facts={"hitDays": 2, "windowDays": 3, "days": ({"date": datetime(2026, 10, 2).date(), "swing": 1.2, "coverage": 0.75, "readingCount": 36, "hit": True},)},
    )


def snap(**kw):
    kw.setdefault("pond", makePond())
    return makeSnapshot(**kw)


def test_t2_prediction_aerate_draft():
    drafts = buildDrafts((predSig(),), snap(), NOW)
    assert len(drafts) == 1
    d = drafts[0]
    assert d.entryId == "AERATE"
    assert d.urgency == Urgency.urgent
    assert d.applyMode == ApplyMode.fixed
    assert d.dedupeKey == "AERATE:2026-10-25"
    assert d.validFrom == NOW
    assert d.validUntil == t("2026-10-25 21:00", TZ)
    assert d.textKey == "AERATE.prediction"
    assert d.proposedActivities[0].startTime == t("2026-10-25 19:00", TZ)
    assert d.proposedActivities[0].endTime == t("2026-10-26 06:00", TZ)

    drafts2 = buildDrafts((predSig(code="PRED_DO_REPEAT", srcId="pred:2"),), snap(), NOW)
    assert drafts2[0].textKey == "AERATE.prediction"


def test_diagnostic_only_aerate_draft():
    openEp = epSig(PondParameters.DO, SeverityLevelType.ElevatedRisk)
    drafts = buildDrafts((openEp,), snap(), NOW)
    assert drafts[0].textKey == "AERATE.diagnostic"
    assert drafts[0].proposedActivities[0].startTime == NOW
    assert drafts[0].proposedActivities[0].endTime == NOW + timedelta(hours=4)
    assert drafts[0].validUntil == NOW + timedelta(hours=1)

    assert buildDrafts((epSig(PondParameters.DO, SeverityLevelType.Stress),), snap(), NOW) == ()
    closedEp = Signal(
        sourceType=SignalSource.episode, sourceId="ep:c", code="DIAG_EPISODE",
        parameter=PondParameters.DO, active=False, riskStart=None, riskEnd=None,
        peakSeverity=SeverityLevelType.ElevatedRisk, lastSeverity=SeverityLevelType.ElevatedRisk,
        scope=None, facts={},
    )
    assert buildDrafts((closedEp,), snap(), NOW) == ()


def test_both_sources_aerate():
    both = (predSig(), epSig(PondParameters.DO, SeverityLevelType.ElevatedRisk))
    drafts = buildDrafts(both, snap(), NOW)
    assert drafts[0].textKey == "AERATE.both"
    a = drafts[0].proposedActivities[0]
    assert a.startTime == NOW
    assert a.endTime == t("2026-10-26 06:00", TZ)
    assert drafts[0].validUntil == t("2026-10-25 17:30", TZ)
    assert len(drafts[0].sources) == 2


def test_water_change_urgency_and_windows():
    critical = buildDrafts((wcSig(severity=SeverityLevelType.Critical),), snap(), NOW)
    assert critical[0].urgency == Urgency.urgent
    assert critical[0].applyMode == ApplyMode.fixed
    assert critical[0].validUntil == NOW + timedelta(hours=3)
    assert critical[0].proposedActivities[0].fraction == 0.5
    assert critical[0].dedupeKey == "WATER_CHANGE:2026-10-25"

    elevated = buildDrafts((wcSig(severity=SeverityLevelType.ElevatedRisk),), snap(), NOW)
    assert elevated[0].urgency == Urgency.nonUrgent
    assert elevated[0].applyMode == ApplyMode.pickWindow
    assert elevated[0].proposedActivities[0].fraction == 0.25
    _, endNext = __import__("identity.analysis.helpers", fromlist=["localDayBounds"]).localDayBounds(
        __import__("identity.analysis.helpers", fromlist=["localDate"]).localDate(NOW, TZ) + timedelta(days=1), TZ)
    assert elevated[0].validUntil == endNext

    no2 = buildDrafts((wcSig(param=PondParameters.NO2_N),), snap(), NOW)
    assert no2[0].entryId == "WATER_CHANGE"

    predRise = Signal(
        sourceType=SignalSource.prediction, sourceId="pred:r", code="PRED_NH3_RISE",
        parameter=PondParameters.NH3, active=True,
        riskStart=NOW, riskEnd=NOW + timedelta(hours=12),
        peakSeverity=None, lastSeverity=None, scope=None,
        facts={"totalMealPct": 3.6, "nh3Zone": ThresholdLevelType.Stress, "nh3Value": 0.1},
    )
    assert buildDrafts((predRise,), snap(), NOW)[0].textKey == "WATER_CHANGE.prediction"

    both = buildDrafts((wcSig(severity=SeverityLevelType.Critical), predRise), snap(), NOW)
    assert both[0].urgency == Urgency.urgent
    assert len(both[0].sources) == 2


def test_alkalinity_draft_and_closed_signals():
    drafts = buildDrafts((detSig(),), snap(), NOW)
    assert drafts[0].entryId == "ADD_ALKALINITY"
    assert drafts[0].urgency == Urgency.nonUrgent
    assert drafts[0].applyMode == ApplyMode.pickWindow
    assert drafts[0].validUntil == NOW + timedelta(days=3)
    assert drafts[0].proposedActivities[0].quantityKg is None

    inactive = Signal(
        sourceType=SignalSource.detector, sourceId="PH_SWING:pond_1", code="PH_SWING",
        parameter=PondParameters.pH, active=False,
        riskStart=None, riskEnd=None, peakSeverity=None, lastSeverity=None, scope=None, facts={},
    )
    assert buildDrafts((inactive,), snap(), NOW) == ()


def test_anchor_stability_and_key_reuse_midnight():
    existing = makeSnapshot(
        pond=makePond(),
        recommendations=[__import__("tests.support.rec_builders", fromlist=["makeRecommendation"]).makeRecommendation(
            entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
            urgency=Urgency.urgent,
            sources=(SourceRef(SignalSource.episode, "ep:2"),),
            createdAt=t("2026-10-25 10:00", TZ), updatedAt=t("2026-10-25 10:00", TZ),
        )],
    )
    later = NOW + timedelta(minutes=30)
    drafts1 = buildDrafts((wcSig(),), existing, NOW)
    drafts2 = buildDrafts((wcSig(),), existing, later)
    assert drafts1[0].validFrom == drafts2[0].validFrom == t("2026-10-25 10:00", TZ)
    assert drafts1[0].proposedActivities == drafts2[0].proposedActivities

    midnight = t("2026-10-26 00:10", TZ)
    drafts3 = buildDrafts((wcSig(),), existing, midnight)
    assert drafts3[0].dedupeKey == "WATER_CHANGE:2026-10-25"


def test_urgency_raised_resets_anchor():
    existing = makeSnapshot(
        pond=makePond(),
        recommendations=[__import__("tests.support.rec_builders", fromlist=["makeRecommendation"]).makeRecommendation(
            entryId="WATER_CHANGE", dedupeKey="WATER_CHANGE:2026-10-25",
            urgency=Urgency.nonUrgent,
            sources=(SourceRef(SignalSource.episode, "ep:2"),),
            createdAt=t("2026-10-25 10:00", TZ), updatedAt=t("2026-10-25 10:00", TZ),
        )],
    )
    drafts = buildDrafts((wcSig(severity=SeverityLevelType.Critical),), existing, NOW)
    assert drafts[0].urgency == Urgency.urgent
    assert drafts[0].validFrom == NOW
