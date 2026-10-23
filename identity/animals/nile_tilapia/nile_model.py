from identity.animals.animal_model import AquaticAnimal
from identity.animals.nile_tilapia.nile_parameter_threshold.DO.nile_DO_threshold import DO_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.NO2_N.nile_NO2_N_threshold import NO2_N_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.NH3.nile_NO3_threshold import NH3_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.pH.nile_pH_threshold import pH_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.salinity.nile_salinity_threshold import salinity_threshold
from identity.animals.nile_tilapia.nile_parameter_threshold.tempearture.nile_tem_threshold import tem_threshold
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold.t_levels import LevelType
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, RangeThreshold, Threshold

class NileTilapiaModel(AquaticAnimal):
    label:str = "Nile Tilapia"

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