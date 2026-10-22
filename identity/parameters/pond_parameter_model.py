from __future__ import annotations

from typing import TYPE_CHECKING

from identity.parameters.parameter import ParameterModel
from identity.parameters.pond_parameter_enum import PondParameters

if TYPE_CHECKING:
    from identity.animals.animal_model import AquaticAnimal

class PondParametersModel:
    do:ParameterModel
    pH:ParameterModel
    tem:ParameterModel
    nh3:ParameterModel
    no2_n:ParameterModel
    salinity:ParameterModel

    def __init__(
            self,
            *,
            species: AquaticAnimal,
        ):
        self.species:AquaticAnimal = species

        # DO
        self.do = ParameterModel(
            identity = PondParameters.DO,
            valueNow = species.parameterNow.do,
            threshold = self.species.DOThreshold()
        )
        # pH
        self.pH = ParameterModel(
            identity = PondParameters.pH,
            valueNow = species.parameterNow.pH,
            threshold = self.species.pHThreshold()
        )
        # Tem
        self.tem = ParameterModel(
            identity = PondParameters.tem,
            valueNow = species.parameterNow.tem,
            threshold = self.species.temThreshold()
        )
        # NH3
        self.nh3 = ParameterModel(
            identity = PondParameters.NH3,
            valueNow = species.parameterNow.nh3,
            threshold = self.species.NH3Threshold()
        )
        # NO2-N
        self.no2_n = ParameterModel(
            identity = PondParameters.NO2_N,
            valueNow = species.parameterNow.no2_n,
            threshold = self.species.NO2_2Threshold()
        )
        # Salinity
        self.salinity = ParameterModel(
            identity = PondParameters.salinity,
            valueNow = species.parameterNow.salinity,
            threshold = self.species.salinityThreshold()
        )


class PondParametersDeliveryModel:
    def __init__(
            self,
            *,
            do: float,
            pH: float,
            tem: float,
            nh3: float,
            no2_n: float,
            salinity: float
        ):
        self.do = do
        self.pH = pH
        self.tem = tem     
        self.nh3 = nh3
        self.no2_n = no2_n   
        self.salinity = salinity   
