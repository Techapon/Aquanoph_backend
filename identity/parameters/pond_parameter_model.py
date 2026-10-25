from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime
from identity.parameters.parameter_model import ParameterModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel

if TYPE_CHECKING:
    from identity.animals.animal_model import AquaticAnimal

class PondParametersModel:
    do:ParameterModel
    pH:ParameterModel
    tem:ParameterModel
    nh3:ParameterModel
    no2_n:ParameterModel
    salinity:ParameterModel
    dateTime:datetime

    def __init__(
            self,
            *,
            species: AquaticAnimal,
            analysisHis: list[AnalysisReportModel],
            dateTime: datetime
        ):
        self.species:AquaticAnimal = species
        self.analysisHis:list[AnalysisReportModel] = analysisHis
        self.dateTime = dateTime

        # DO
        self.do = ParameterModel(
            identity = PondParameters.DO,
            valueNow = species.parameterNow.do,
            threshold = self.species.DOThreshold(),
            escalationPolicy = self.species.DOEscalationPolicy(),
            severityDesSetModel = self.species.DOSeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
        )
        # pH
        self.pH = ParameterModel(
            identity = PondParameters.pH,
            valueNow = species.parameterNow.pH,
            threshold = self.species.pHThreshold(),
            escalationPolicy = self.species.pHEscalationPolicy(),
            severityDesSetModel = self.species.pHSeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
        )
        # Tem
        self.tem = ParameterModel(
            identity = PondParameters.tem,
            valueNow = species.parameterNow.tem,
            threshold = self.species.temThreshold(),
            escalationPolicy = self.species.temEscalationPolicy(),
            severityDesSetModel = self.species.temSeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
        )
        # NH3
        self.nh3 = ParameterModel(
            identity = PondParameters.NH3,
            valueNow = species.parameterNow.nh3,
            threshold = self.species.NH3Threshold(),
            escalationPolicy = self.species.NH3EscalationPolicy(),
            severityDesSetModel = self.species.NH3SeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
        )
        # NO2-N
        self.no2_n = ParameterModel(
            identity = PondParameters.NO2_N,
            valueNow = species.parameterNow.no2_n,
            threshold = self.species.NO2_2Threshold(),
            escalationPolicy = self.species.NO2_2EscalationPolicy(),
            severityDesSetModel = self.species.NO2_2SeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
        )
        # Salinity
        self.salinity = ParameterModel(
            identity = PondParameters.salinity,
            valueNow = species.parameterNow.salinity,
            threshold = self.species.salinityThreshold(),
            escalationPolicy = self.species.salinityEscalationPolicy(),
            severityDesSetModel = self.species.salinitySeverityDesSet(),
            analysisHis = self.analysisHis,
            dateTime = self.dateTime
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
