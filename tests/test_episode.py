"""Phase 2 episode tests."""
from datetime import datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.models import DiagStatus
from identity.diagnostic.episode import buildEpisodes, qualifies
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeView


T0 = datetime(2026, 10, 25, 12, 0)


def test_episode_qualification_rules():
    stress = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress)
    highRisk = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.HighRisk)
    critical = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Critical)
    twoStress = [
        makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress),
        makeView(PondParameters.DO, T0 + timedelta(minutes=30), zone=ThresholdLevelType.Stress),
    ]

    assert qualifies(buildEpisodes([stress], PondParameters.DO)[0], DEFAULT_CONFIG) is False
    assert qualifies(buildEpisodes([highRisk], PondParameters.DO)[0], DEFAULT_CONFIG) is True
    assert qualifies(buildEpisodes([critical], PondParameters.DO)[0], DEFAULT_CONFIG) is True
    assert qualifies(buildEpisodes(twoStress, PondParameters.DO)[0], DEFAULT_CONFIG) is True


def test_recovery_hold_optimal_zone_closes_episode():
    inEpisode = makeView(
        PondParameters.DO, T0, zone=ThresholdLevelType.Stress,
        severity=SeverityLevelType.Stress,
    )
    recoveryHold = makeView(
        PondParameters.DO, T0 + timedelta(minutes=30), zone=ThresholdLevelType.Optimal,
        severity=SeverityLevelType.Stress,
    )

    episodes = buildEpisodes([inEpisode, recoveryHold], PondParameters.DO)

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.endAt == recoveryHold.time
    assert ep.status == DiagStatus.closed
    assert ep.readingCount == 1
    assert ep.lastSeverity == SeverityLevelType.Stress


def test_range_direction_flip_splits_but_level_does_not():
    low = makeView(PondParameters.pH, T0, value=6.5, zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low)
    high = makeView(PondParameters.pH, T0 + timedelta(minutes=30), value=9.0, zone=ThresholdLevelType.Stress, direction=ThresholdDirection.High)
    episodes = buildEpisodes([low, high], PondParameters.pH)
    assert len(episodes) == 2
    assert episodes[0].direction == ThresholdDirection.Low
    assert episodes[0].endAt == high.time
    assert episodes[0].status == DiagStatus.closed
    assert episodes[1].direction == ThresholdDirection.High
    assert episodes[1].onsetAt == high.time
    assert episodes[1].status == DiagStatus.open

    do1 = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress)
    do2 = makeView(PondParameters.DO, T0 + timedelta(minutes=30), zone=ThresholdLevelType.HighRisk)
    assert len(buildEpisodes([do1, do2], PondParameters.DO)) == 1


def test_open_episode_has_no_end_time():
    episode = buildEpisodes([makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress)], PondParameters.DO)[0]
    assert episode.endAt is None
    assert episode.status == DiagStatus.open


def test_mixed_parameter_input_is_filtered():
    doView = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress)
    phView = makeView(PondParameters.pH, T0 + timedelta(minutes=5), zone=ThresholdLevelType.Stress, direction=ThresholdDirection.Low)
    episodes = buildEpisodes([phView, doView], PondParameters.DO)
    assert len(episodes) == 1
    assert episodes[0].parameter == PondParameters.DO


def test_unsorted_input_is_sorted_stably_for_equal_timestamps():
    late = makeView(PondParameters.DO, T0 + timedelta(hours=1), zone=ThresholdLevelType.Stress)
    first = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress, severity=SeverityLevelType.Stress)
    equal = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.HighRisk, severity=SeverityLevelType.ElevatedRisk)
    ep = buildEpisodes([late, first, equal], PondParameters.DO)[0]
    assert ep.onsetAt == T0
    assert ep.lastReadingAt == late.time
    assert ep.peakZone == ThresholdLevelType.HighRisk


def test_gap_does_not_close_episode_and_empty_returns_empty_tuple():
    a = makeView(PondParameters.DO, T0, zone=ThresholdLevelType.Stress)
    b = makeView(PondParameters.DO, T0 + timedelta(hours=3), zone=ThresholdLevelType.Stress)
    assert len(buildEpisodes([a, b], PondParameters.DO)) == 1
    assert buildEpisodes([], PondParameters.DO) == ()


def test_peak_values_are_max_not_last():
    first = makeView(
        PondParameters.DO, T0, zone=ThresholdLevelType.HighRisk,
        severity=SeverityLevelType.ElevatedRisk,
    )
    last = makeView(
        PondParameters.DO, T0 + timedelta(minutes=30), zone=ThresholdLevelType.Stress,
        severity=SeverityLevelType.Stress,
    )
    ep = buildEpisodes([first, last], PondParameters.DO)[0]
    assert ep.peakSeverity == SeverityLevelType.ElevatedRisk
    assert ep.peakZone == ThresholdLevelType.HighRisk
    assert ep.lastSeverity == SeverityLevelType.Stress
