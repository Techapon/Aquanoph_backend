"""AnalysisConfig — all tunable numbers for the analysis pipeline.

Rules read from cfg; never use magic numbers in logic files.
Frozen dataclass with validate() called in __post_init__.
Strictly follows PHASE_1_foundation.md §1.
"""
from dataclasses import dataclass
from typing import Tuple

VALID_SEVERITY_NAMES = {"Optimal", "Stress", "ElevatedRisk", "Critical"}


@dataclass(frozen=True)
class AnalysisConfig:
    # time
    nightStartHour: int = 18
    nightEndHour: int = 6
    expectedIntervalMinutes: int = 30
    staleFactor: float = 3.0
    retroWindowDays: int = 4
    historyHorizonDays: int = 8
    tickMinutes: int = 30

    # diagnostic
    minEpisodeReadings: int = 2
    maxCauses: int = 2
    heavyMealPct: float = 1.0
    feedLookbackDoHours: int = 6
    feedLookbackNh3Hours: int = 12
    tempLookbackHours: int = 3
    nh3ChainLookbackHours: int = 24
    salWaterChangeLookbackHours: int = 6
    tempHighWindow: Tuple[int, int] = (11, 16)
    tempLowWindow: Tuple[int, int] = (22, 6)
    phHighWindow: Tuple[int, int] = (12, 18)
    phLowWindow: Tuple[int, int] = (2, 7)

    # detector PH_SWING
    phSwingMin: float = 1.0
    phSwingHitDays: int = 2
    phSwingWindowDays: int = 3
    phSwingCoverage: float = 0.70

    # prediction
    eveningFromHour: int = 16
    feedLookbackPredHours: int = 6
    feedLookaheadPredHours: int = 8
    riskStartAfterMealHours: int = 1
    minAerationHours: float = 3.0
    tempHighLookbackPredHours: int = 6
    repeatMinNights: int = 2
    repeatWindowNights: int = 3
    repeatSeverity: str = "ElevatedRisk"
    predictFromHour: int = 12
    dailyHeavyPct: float = 3.0
    nh3RiseHorizonHours: int = 12
    wcLookbackHours: int = 48
    wcLookaheadHours: int = 24

    # recommendation
    aerateLeadHours: int = 1
    aerateDeadlineAfterRiskStartHours: int = 1
    aerateDiagDeadlineHours: int = 1
    aerateDiagDurationHours: int = 4
    wcUrgentDeadlineHours: int = 3
    wcUrgentFraction: float = 0.5
    wcNonUrgentFraction: float = 0.25
    alkalinityWindowDays: int = 3
    minAerationSegmentMinutes: int = 15

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        # hour checks (0-23)
        for name in ("nightStartHour", "nightEndHour", "eveningFromHour", "predictFromHour"):
            val = getattr(self, name)
            if not (0 <= val <= 23):
                raise ValueError(f"{name} must be in 0..23, got {val}")

        # window pairs
        for name in ("tempHighWindow", "tempLowWindow", "phHighWindow", "phLowWindow"):
            w = getattr(self, name)
            if not (len(w) == 2 and 0 <= w[0] <= 23 and 0 <= w[1] <= 23):
                raise ValueError(f"{name} must be a pair of hours in 0..23, got {w}")

        # positive durations and intervals
        for name in (
            "expectedIntervalMinutes", "retroWindowDays", "historyHorizonDays",
            "tickMinutes", "minEpisodeReadings", "maxCauses", "feedLookbackDoHours",
            "feedLookbackNh3Hours", "tempLookbackHours", "nh3ChainLookbackHours",
            "salWaterChangeLookbackHours", "phSwingHitDays", "phSwingWindowDays",
            "feedLookbackPredHours", "feedLookaheadPredHours", "riskStartAfterMealHours",
            "tempHighLookbackPredHours", "repeatMinNights", "repeatWindowNights",
            "nh3RiseHorizonHours", "wcLookbackHours", "wcLookaheadHours",
            "aerateLeadHours", "aerateDeadlineAfterRiskStartHours",
            "aerateDiagDeadlineHours", "aerateDiagDurationHours", "wcUrgentDeadlineHours",
            "alkalinityWindowDays", "minAerationSegmentMinutes"
        ):
            val = getattr(self, name)
            if val <= 0:
                raise ValueError(f"{name} must be positive, got {val}")

        # positive floats
        for name in ("heavyMealPct", "phSwingMin", "minAerationHours", "dailyHeavyPct"):
            val = getattr(self, name)
            if val <= 0.0:
                raise ValueError(f"{name} must be positive, got {val}")

        if self.staleFactor < 1.0:
            raise ValueError(f"staleFactor must be >= 1.0, got {self.staleFactor}")

        if not (0.0 <= self.phSwingCoverage <= 1.0):
            raise ValueError(f"phSwingCoverage must be in 0..1, got {self.phSwingCoverage}")

        for name in ("wcUrgentFraction", "wcNonUrgentFraction"):
            val = getattr(self, name)
            if not (0.0 < val <= 1.0):
                raise ValueError(f"{name} must be in (0, 1], got {val}")

        if self.repeatSeverity not in VALID_SEVERITY_NAMES:
            raise ValueError(f"Unknown repeatSeverity: {self.repeatSeverity}")


# Defaults
DEFAULT_CONFIG = AnalysisConfig()
cfg = DEFAULT_CONFIG
