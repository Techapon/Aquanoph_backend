from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection


class ThresholdLevelModel:
    level: ThresholdLevelType
    direction: ThresholdDirection | None

    def __init__(
        self,
        *,
        level: ThresholdLevelType,
        direction: ThresholdDirection | None = None
    ):
        if level == ThresholdLevelType.Optimal and direction is not None:
            raise ValueError("ค่า Optimal ต้องไม่มี direction")
        self.level = level
        self.direction = direction