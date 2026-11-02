"""Unit tests for Phase 1: Core analysis models, helpers, ids, changeset, store simulation, and severity view."""
from datetime import datetime, timedelta

import pytest

from config.constants import cfg
from identity.analysis.changeset import ChangeSet
from identity.analysis.helpers import isNight, isStale, localTime, nightWindowFor, toUtc
from identity.analysis.ids import (
    detectorId,
    episodeId,
    notificationId,
    predictionId,
    recommendationId,
)
from identity.analysis.models import (
    Notification,
    Recommendation,
    RecommendationStatus,
    RecommendationUrgency,
    SourceKind,
    SourceRef,
)
from identity.analysis.severity_view import (
    ParameterTimelineView,
    isNonOptimal,
    isRecoveryHold,
    severityOrder,
    zoneOrder,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import (
    makeActivity,
    makePondProfile,
    makeReport,
    makeSnapshot,
)
from tests.support.store_sim import StoreSimulator


TZ = "Asia/Bangkok"


# ---------- Time helpers & Night window (O2, Rule 3) ----------
def test_local_time_and_to_utc_roundtrip():
    # 2026-10-25 05:00 UTC -> 12:00 Bangkok (+7)
    utc = datetime(2026, 10, 25, 5, 0)
    local = localTime(utc, TZ)
    assert local == datetime(2026, 10, 25, 12, 0)

    backUtc = toUtc(local, TZ)
    assert backUtc == utc


def test_night_window_for_evening():
    # 22:00 local on 2026-10-25 -> 15:00 UTC
    tUtc = datetime(2026, 10, 25, 15, 0)
    startUtc, endUtc = nightWindowFor(tUtc, TZ, cfg)

    # Night starts 21:00 local (14:00 UTC) on 2026-10-25
    # Ends 06:00 local (23:00 UTC) on 2026-10-26
    assert startUtc == datetime(2026, 10, 25, 14, 0)
    assert endUtc == datetime(2026, 10, 25, 23, 0)
    assert isNight(tUtc, TZ, cfg) is True


def test_night_window_for_early_morning():
    # 03:00 local on 2026-10-26 -> 20:00 UTC on 2026-10-25
    tUtc = datetime(2026, 10, 25, 20, 0)
    startUtc, endUtc = nightWindowFor(tUtc, TZ, cfg)

    # Night started 21:00 local (14:00 UTC) on previous day (2026-10-25)
    # Ends 06:00 local (23:00 UTC) on current day (2026-10-26)
    assert startUtc == datetime(2026, 10, 25, 14, 0)
    assert endUtc == datetime(2026, 10, 25, 23, 0)
    assert isNight(tUtc, TZ, cfg) is True


def test_is_night_false_at_daytime():
    # 12:00 local (05:00 UTC) is daytime
    tUtc = datetime(2026, 10, 25, 5, 0)
    assert isNight(tUtc, TZ, cfg) is False


def test_is_stale_reading():
    # staleFactor = 3.0, expectedInterval = 30 min -> max age = 90 min
    now = datetime(2026, 10, 25, 12, 0)
    fresh = now - timedelta(minutes=80)
    stale = now - timedelta(minutes=91)

    assert isStale(fresh, now, cfg) is False
    assert isStale(stale, now, cfg) is True


# ---------- Deterministic IDs (Rule 7) ----------
def test_deterministic_ids_are_reproducible():
    ts = datetime(2026, 10, 25, 12, 0)
    ep1 = episodeId("pond_1", PondParameters.DO, None, ts)
    ep2 = episodeId("pond_1", PondParameters.DO, None, ts)
    assert ep1 == ep2
    assert ep1.startswith("ep_DO_")

    rec1 = recommendationId("pond_1", "AERATE:night", ts)
    rec2 = recommendationId("pond_1", "AERATE:night", ts)
    assert rec1 == rec2
    assert rec1.startswith("rec_")


def test_ids_differ_for_different_inputs():
    ts = datetime(2026, 10, 25, 12, 0)
    epDo = episodeId("pond_1", PondParameters.DO, None, ts)
    epPh = episodeId("pond_1", PondParameters.pH, ThresholdDirection.Low, ts)
    assert epDo != epPh


# ---------- ChangeSet & StoreSimulator (Contract §3, Rule 7) ----------
def test_changeset_empty_check():
    cs = ChangeSet()
    assert cs.isEmpty is True

    notEmpty = ChangeSet(notifications=(Notification(
        id="notif_1", pondId="pond_1", createdAt=datetime(2026, 10, 25, 12, 0),
        titleKey="title", bodyKey="body",
    ),))
    assert notEmpty.isEmpty is False


def test_changeset_diff_only_idempotent():
    now = datetime(2026, 10, 25, 12, 0)
    rec = Recommendation(
        id="rec_1", pondId="pond_1", dedupeKey="AERATE",
        actionType="AERATE", urgency=RecommendationUrgency.urgent,
        status=RecommendationStatus.pending,
        sources=(SourceRef(kind=SourceKind.episode, sourceId="ep_1"),),
        createdAt=now,
    )
    snapshot = makeSnapshot(recommendations=[rec])

    # Applying the same recommendation produces empty diff
    cs = ChangeSet(upsertRecommendations=(rec,))
    diff = cs.diffOnly(snapshot)
    assert len(diff.upsertRecommendations) == 0

    # Modified recommendation is included in diff
    recModified = Recommendation(
        id="rec_1", pondId="pond_1", dedupeKey="AERATE",
        actionType="AERATE", urgency=RecommendationUrgency.urgent,
        status=RecommendationStatus.applied,
        sources=(SourceRef(kind=SourceKind.episode, sourceId="ep_1"),),
        createdAt=now, appliedAt=now,
    )
    cs2 = ChangeSet(upsertRecommendations=(recModified,))
    diff2 = cs2.diffOnly(snapshot)
    assert len(diff2.upsertRecommendations) == 1


def test_store_simulator_apply():
    now = datetime(2026, 10, 25, 12, 0)
    snapshot = makeSnapshot()
    sim = StoreSimulator(snapshot)

    rec = Recommendation(
        id="rec_1", pondId="pond_1", dedupeKey="AERATE",
        actionType="AERATE", urgency=RecommendationUrgency.urgent,
        status=RecommendationStatus.pending,
        sources=(), createdAt=now,
    )
    notif = Notification(
        id="notif_1", pondId="pond_1", createdAt=now,
        titleKey="title", bodyKey="body",
    )
    cs = ChangeSet(upsertRecommendations=(rec,), notifications=(notif,))

    newSnap = sim.apply(cs)
    # Original snapshot unchanged
    assert len(snapshot.recommendations) == 0
    # New snapshot has recommendation
    assert len(newSnap.recommendations) == 1
    assert newSnap.recommendations[0].id == "rec_1"
    # Notification recorded in log
    assert len(sim.notificationLog) == 1


# ---------- SeverityView tests ----------
def test_zone_and_severity_orders():
    assert zoneOrder(ThresholdLevelType.Optimal) < zoneOrder(ThresholdLevelType.Stress)
    assert zoneOrder(ThresholdLevelType.Stress) < zoneOrder(ThresholdLevelType.HighRisk)
    assert zoneOrder(ThresholdLevelType.HighRisk) < zoneOrder(ThresholdLevelType.Critical)

    assert severityOrder(SeverityLevelType.Optimal) < severityOrder(SeverityLevelType.Stress)
    assert severityOrder(SeverityLevelType.Stress) < severityOrder(SeverityLevelType.ElevatedRisk)
    assert severityOrder(SeverityLevelType.ElevatedRisk) < severityOrder(SeverityLevelType.Critical)


def test_parameter_timeline_view():
    now = datetime(2026, 10, 25, 12, 0)
    r1 = makeReport(PondParameters.DO, now - timedelta(minutes=60), ThresholdLevelType.Stress)
    r2 = makeReport(PondParameters.pH, now - timedelta(minutes=45), ThresholdLevelType.Stress)
    r3 = makeReport(PondParameters.DO, now - timedelta(minutes=30), ThresholdLevelType.HighRisk)

    view = ParameterTimelineView(PondParameters.DO, [r1, r2, r3])
    assert len(view.reports) == 2
    assert view.latest == r3
    assert isNonOptimal(r3) is True

    recHold = makeReport(
        PondParameters.DO, now,
        thresholdStatus=ThresholdLevelType.Optimal,
        severityLevel=SeverityLevelType.Stress,
    )
    assert isRecoveryHold(recHold) is True
