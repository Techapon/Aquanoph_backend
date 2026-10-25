from identity.animals.animal_model import AquaticAnimal
from identity.animals.nile_tilapia.nile_parameter_severity.DO.nile_DO_severity import DO_EscalationPolicy, DO_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_severity.NH3.nile_NH3_severity import NH3_EscalationPolicy, NH3_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_severity.NO2_N.nile_NO2_N_severity import NO2_N_EscalationPolicy, NO2_N_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_severity.pH.nile_pH_severity import pH_EscalationPolicy, pH_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_severity.salinity.nile_salinity_severity import salinity_EscalationPolicy, salinity_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_severity.tempearture.nile_tem_severity import temperature_EscalationPolicy, temperature_SeverityDesSet
from identity.animals.nile_tilapia.nile_parameter_threshold.DO.nile_DO_threshold import DO_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.NO2_N.nile_NO2_N_threshold import NO2_N_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.NH3.nile_NH3_threshold import NH3_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.pH.nile_pH_threshold import pH_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.salinity.nile_salinity_threshold import salinity_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.tempearture.nile_tem_threshold import tem_threshold
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold.threshold_type_level_enum import LevelType
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, RangeThreshold, Threshold
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    EscalationPolicy, RangeEscalationPolicy,
)
from identity.units.severity_units.severity_description.severity_des_set_model import (
    SeverityDesSetModel, RangeSeverityDesSet,
)

class NileTilapiaModel(AquaticAnimal):
    label:str = "Nile Tilapia"

    # ----------
    # Threshold
    # ----------

    # DO
    def DOThreshold(self) -> LevelThreshold:
        return DO_threshold(self,self.parameterNow)

    # pH
    def pHThreshold(self) -> RangeThreshold:
        return pH_threshold(self)
    
    # Temerapure
    def temThreshold(self) -> RangeThreshold:
        return tem_threshold(self)

    # NH3
    def NH3Threshold(self) -> LevelThreshold:
        return NH3_threshold(self)

    # NO2_2
    def NO2_2Threshold(self) -> LevelThreshold:
        return NO2_N_threshold(self)

    # salinity
    def salinityThreshold(self) -> LevelThreshold:
        return salinity_threshold(self,self.parameterNow)

    # ----------
    # Escalation Policy
    # ----------
    
    # DO
    def DOEscalationPolicy(self) -> EscalationPolicy:
        return DO_EscalationPolicy()

    # pH
    def pHEscalationPolicy(self) -> RangeEscalationPolicy:
        return pH_EscalationPolicy()
    
    # Temerapure
    def temEscalationPolicy(self) -> RangeEscalationPolicy:
        return temperature_EscalationPolicy()

    # NH3
    def NH3EscalationPolicy(self) -> EscalationPolicy:
        return NH3_EscalationPolicy()

    # NO2_2
    def NO2_2EscalationPolicy(self) -> EscalationPolicy:
        return NO2_N_EscalationPolicy()

    # salinity
    def salinityEscalationPolicy(self) -> EscalationPolicy:
        return salinity_EscalationPolicy()

    # ----------
    # Severity Description Sets
    # ----------

    def DOSeverityDesSet(self) -> SeverityDesSetModel:
        return DO_SeverityDesSet()

    def pHSeverityDesSet(self) -> RangeSeverityDesSet:
        return pH_SeverityDesSet()

    def temSeverityDesSet(self) -> RangeSeverityDesSet:
        return temperature_SeverityDesSet()

    def NH3SeverityDesSet(self) -> SeverityDesSetModel:
        return NH3_SeverityDesSet()

    def NO2_2SeverityDesSet(self) -> SeverityDesSetModel:
        return NO2_N_SeverityDesSet()

    def salinitySeverityDesSet(self) -> SeverityDesSetModel:
        return salinity_SeverityDesSet()