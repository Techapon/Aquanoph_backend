from dataclasses import dataclass

@dataclass
class EscalationPolicy:

    # ---------------------
    # Continuous  type
    # ---------------------
    
    stressCountMinute = 480
    HightRiskCountMinute = 150

    # ---------------------
    # Cumulative type
    # ---------------------
    
    stressCumIn24Hs = 480
    HightRiskCumIn24Hs = 240

    # ---------------------
    # Other
    # ---------------------

    recurrenceEpisode24H = 2
    EpisodeSeparationMinute = 60

    HightRiskRecoveryHoldMinute = 120
    CriticalRecoveryHoldMinute = 240

