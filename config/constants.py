"""AnalysisConfig — all tunable numbers for the analysis pipeline.

Rules read from cfg; never use magic numbers in logic files.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    # Severity escalation (minutes)
    stressCountMinute: int = 480          # Stress → ElevatedRisk (continuous)
    highRiskCountMinute: int = 150        # HighRisk → Critical (continuous)
    stressCumIn24Hs: int = 480           # Stress → ElevatedRisk (cumulative 24 h)
    highRiskCumIn24Hs: int = 240         # HighRisk → Critical (cumulative 24 h)
    recurrenceEpisode24H: int = 2        # HighRisk → Critical (episode count)
    episodeSeparationMinute: int = 60    # boundary between episodes

    # Recovery hold (minutes)
    elevatedRecoveryHoldMinute: int = 120
    criticalRecoveryHoldMinute: int = 240

    # History / stale reading
    historyHorizonDays: int = 8          # snapshot must carry at least this many days
    staleFactor: float = 3.0             # stale = staleFactor × expectedIntervalMinutes
    expectedIntervalMinutes: int = 30    # nominal sensor interval

    # Retroactive edit window
    retroWindowDays: int = 4

    # Night window (local time hours)
    nightStartHour: int = 21
    nightEndHour: int = 6


# Singleton — import and use directly.
cfg = AnalysisConfig()
