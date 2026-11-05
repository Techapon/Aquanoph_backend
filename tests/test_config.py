"""Unit tests for AnalysisConfig per PHASE_1_foundation.md."""
from dataclasses import replace
import pytest

from config.constants import DEFAULT_CONFIG, AnalysisConfig, cfg


def test_defaults_load():
    assert cfg.nightStartHour == 18
    assert cfg.nightEndHour == 6
    assert cfg.expectedIntervalMinutes == 30
    assert cfg.staleFactor == 3.0
    assert cfg.retroWindowDays == 4
    assert cfg.historyHorizonDays == 8
    assert cfg.tickMinutes == 30
    assert cfg.minEpisodeReadings == 2
    assert cfg.heavyMealPct == 1.0
    assert cfg.repeatSeverity == "ElevatedRisk"


def test_config_is_frozen():
    with pytest.raises((AttributeError, TypeError)):
        cfg.nightStartHour = 20  # type: ignore


@pytest.mark.parametrize("invalidField, value", [
    ("nightStartHour", -1),
    ("nightStartHour", 24),
    ("nightEndHour", -1),
    ("nightEndHour", 24),
    ("eveningFromHour", 25),
    ("predictFromHour", -1),
    ("tempHighWindow", (11, 25)),
    ("tempLowWindow", (-1, 6)),
    ("expectedIntervalMinutes", 0),
    ("staleFactor", 0.5),
    ("retroWindowDays", 0),
    ("historyHorizonDays", 0),
    ("tickMinutes", 0),
    ("minEpisodeReadings", 0),
    ("maxCauses", 0),
    ("heavyMealPct", 0.0),
    ("feedLookbackDoHours", 0),
    ("feedLookbackNh3Hours", 0),
    ("tempLookbackHours", 0),
    ("nh3ChainLookbackHours", 0),
    ("salWaterChangeLookbackHours", 0),
    ("phSwingMin", 0.0),
    ("phSwingHitDays", 0),
    ("phSwingWindowDays", 0),
    ("phSwingCoverage", 1.5),
    ("phSwingCoverage", -0.1),
    ("feedLookbackPredHours", 0),
    ("feedLookaheadPredHours", 0),
    ("riskStartAfterMealHours", 0),
    ("minAerationHours", 0.0),
    ("tempHighLookbackPredHours", 0),
    ("repeatMinNights", 0),
    ("repeatWindowNights", 0),
    ("repeatSeverity", "NonExistentSeverity"),
    ("dailyHeavyPct", 0.0),
    ("nh3RiseHorizonHours", 0),
    ("wcLookbackHours", 0),
    ("wcLookaheadHours", 0),
    ("aerateLeadHours", 0),
    ("aerateDeadlineAfterRiskStartHours", 0),
    ("aerateDiagDeadlineHours", 0),
    ("aerateDiagDurationHours", 0),
    ("wcUrgentDeadlineHours", 0),
    ("wcUrgentFraction", 0.0),
    ("wcUrgentFraction", 1.5),
    ("wcNonUrgentFraction", 0.0),
    ("wcNonUrgentFraction", 1.5),
    ("alkalinityWindowDays", 0),
    ("minAerationSegmentMinutes", 0),
])
def test_config_validation_rejects_bad_values(invalidField, value):
    with pytest.raises(ValueError):
        replace(cfg, **{invalidField: value})
