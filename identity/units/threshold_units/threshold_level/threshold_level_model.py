from identity.units.threshold_units.threshold_level import ThresholdLevelType


class ThresholdLevelModel:
    level: ThresholdLevelType

    def __init__(self,*,level:ThresholdLevelType):
        self.level = level