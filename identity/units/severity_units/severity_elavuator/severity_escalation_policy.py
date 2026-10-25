from dataclasses import dataclass

from identity.units.threshold_units.threshold_level.threshold_direction import (
    DirectionalPair,
    ThresholdDirection,
)


@dataclass
class EscalationPolicy:
    # NOTE: ต้องมี type annotation (: int) dataclass จึงจะนับเป็น field จริง
    # และเรียก EscalationPolicy(stressCountMinute=300) เพื่อปรับต่อ parameter ได้

    # ---------------------
    # Continuous type
    # ---------------------
    stressCountMinute: int = 480
    HightRiskCountMinute: int = 150

    # ---------------------
    # Cumulative type
    # ---------------------
    stressCumIn24Hs: int = 480
    HightRiskCumIn24Hs: int = 240

    # ---------------------
    # Other
    # ---------------------
    recurrenceEpisode24H: int = 2
    EpisodeSeparationMinute: int = 60

    ElevatedRecoveryHoldMinute: int = 120
    CriticalRecoveryHoldMinute: int = 240

    def forDirection(self, direction: ThresholdDirection | None = None) -> "EscalationPolicy":
        """Level parameter มีชุดเดียว -> คืนตัวเองไม่ว่า direction จะเป็นอะไร"""
        return self


class RangeEscalationPolicy(DirectionalPair[EscalationPolicy]):
    """Range parameter (pH, Temperature): policy แยกฝั่ง low / high"""


AnyEscalationPolicy = EscalationPolicy | RangeEscalationPolicy