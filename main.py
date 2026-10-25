from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.parameter_model import ParameterModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.parameters.pond_parameter_model import PondParametersDeliveryModel, PondParametersModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from datetime import datetime

# Input value

weight = 450 # g
density = (450/1000)*5 # kg/m3

analysisHistoryReport: list[AnalysisReportModel] = []

parameters = PondParametersModel(
    analysisHis = analysisHistoryReport,
    dateTime = datetime(2026,10,24,11,1,50),
    species = NileTilapiaModel(
        weight = weight,
        density = density,
        parameterNow = PondParametersDeliveryModel(
            do = 5.7,
            pH =7,
            tem = 30,
            nh3 = 0.55,
            no2_n = 0.1,
            salinity = 0.1
        )
    ),
)

# print(f"{parameters.do.identity.label} : ",parameters.do.checkParameterThreshold().level.value , "\n",parameters.do.threshold.getThreshold() , "\n")
# print(f"{parameters.pH.identity.label} : ",parameters.pH.checkParameterThreshold().level.value , "\n",parameters.pH.threshold.getThreshold() , "\n")
# print(f"{parameters.tem.identity.label} : ",parameters.tem.checkParameterThreshold().level.value , "\n",parameters.tem.threshold.getThreshold() , "\n")  
# print(f"{parameters.no2_n.identity.label} : ",parameters.no2_n.checkParameterThreshold().level.value , "\n",parameters.no2_n.threshold.getThreshold() , "\n")
# print(f"{parameters.nh3.identity.label} : ",parameters.nh3.checkParameterThreshold().level.value , "\n",parameters.nh3.threshold.getThreshold() , "\n")
# print(f"{parameters.salinity.identity.label} : ",parameters.salinity.checkParameterThreshold().level.value , "\n",parameters.salinity.threshold.getThreshold() , "\n")


print(f"{parameters.do.identity.label} : ",parameters.do.getCurrentSeverityLevel().severityLevel.value , "\n")
print(f"{parameters.pH.identity.label} : ",parameters.pH.getCurrentSeverityLevel().severityLevel.value , "\n")
print(f"{parameters.tem.identity.label} : ",parameters.tem.getCurrentSeverityLevel().severityLevel.value , "\n")  
print(f"{parameters.no2_n.identity.label} : ",parameters.no2_n.getCurrentSeverityLevel().severityLevel.value , "\n")
print(f"{parameters.nh3.identity.label} : ",parameters.nh3.getCurrentSeverityLevel().severityLevel.value , "\n")
print(f"{parameters.salinity.identity.label} : ",parameters.salinity.getCurrentSeverityLevel().severityLevel.value , "\n")

