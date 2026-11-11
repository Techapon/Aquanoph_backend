from identity.parameters.pond_parameter_model import PondParametersDeliveryModel
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, RangeThreshold
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    EscalationPolicy, RangeEscalationPolicy,
)
from identity.units.severity_units.severity_description.severity_des_set_model import (
    SeverityDesSetModel, RangeSeverityDesSet,
)

from abc import ABC, abstractmethod 

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

    # Threshold
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


    # Policy
    @abstractmethod
    def DOEscalationPolicy(self) -> EscalationPolicy:
        pass

    @abstractmethod
    def pHEscalationPolicy(self) -> RangeEscalationPolicy:
        pass

    @abstractmethod
    def temEscalationPolicy(self) -> RangeEscalationPolicy:
        pass

    @abstractmethod
    def NH3EscalationPolicy(self) -> EscalationPolicy:
        pass

    @abstractmethod
    def NO2_2EscalationPolicy(self) -> EscalationPolicy:
        pass

    @abstractmethod
    def salinityEscalationPolicy(self) -> EscalationPolicy:
        pass

    # Severity Description Sets
    @abstractmethod
    def DOSeverityDesSet(self) -> SeverityDesSetModel:
        pass

    @abstractmethod
    def pHSeverityDesSet(self) -> RangeSeverityDesSet:
        pass

    @abstractmethod
    def temSeverityDesSet(self) -> RangeSeverityDesSet:
        pass

    @abstractmethod
    def NH3SeverityDesSet(self) -> SeverityDesSetModel:
        pass

    @abstractmethod
    def NO2_2SeverityDesSet(self) -> SeverityDesSetModel:
        pass

    @abstractmethod
    def salinitySeverityDesSet(self) -> SeverityDesSetModel:
        pass
