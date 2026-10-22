from abc import ABC, abstractmethod

from identity.parameters.pond_parameter_model import PondParametersDeliveryModel
from identity.units.threshold_units.threshold import LevelThreshold, RangeThreshold

class AquaticAnimal(ABC):
    label:str = "Not yet determined"

    def __init__(
            self,
            *,
            weight:float,
            density:float,
            parameterNow:PondParametersDeliveryModel
        ):
        self.weight = weight # g
        self.density = density # km/m^3
        self.parameterNow = parameterNow

    @abstractmethod
    def DOThreshold(self) -> LevelThreshold:
            pass

    @abstractmethod
    def pHThreshold(self) -> RangeThreshold:
            pass

    @abstractmethod
    def temThreshold(self) -> RangeThreshold:
            pass

    @abstractmethod
    def NH3Threshold(self) -> LevelThreshold:
        pass

    @abstractmethod
    def NO2_2Threshold(self) -> LevelThreshold:
        pass

    @abstractmethod
    def salinityThreshold(self) -> LevelThreshold:
        pass
