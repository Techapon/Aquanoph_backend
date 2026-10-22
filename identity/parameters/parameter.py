
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold import Threshold
from identity.units.threshold_units.threshold_level_model import ThresholdLevelModel

class ParameterModel:
    def __init__(
            self,
            *,
            identity: PondParameters,
            valueNow: float,
            threshold: Threshold,
        ):
        self.identity = identity
        self.valueNow = valueNow
        self.threshold = threshold

        # self.thresholdLevel = 

    def checkParameterThreshold(self) -> ThresholdLevelModel:
        return self.threshold.checkThreshold(parameterValueNow = self.valueNow)