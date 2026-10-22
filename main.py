from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
from identity.parameters.parameter import ParameterModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.parameters.pond_parameter_model import PondParametersDeliveryModel, PondParametersModel

# Input value

weight = 800 # g
density = (800/1000)*5 # kg/m3

parameters = PondParametersModel(
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


print(f"{parameters.do.identity.label} : ",parameters.do.checkParameterThreshold().level.value , "\n",parameters.do.threshold.getThreshold() , "\n")
print(f"{parameters.pH.identity.label} : ",parameters.pH.checkParameterThreshold().level.value , "\n",parameters.pH.threshold.getThreshold() , "\n")
print(f"{parameters.tem.identity.label} : ",parameters.tem.checkParameterThreshold().level.value , "\n",parameters.tem.threshold.getThreshold() , "\n")  
print(f"{parameters.no2_n.identity.label} : ",parameters.no2_n.checkParameterThreshold().level.value , "\n",parameters.no2_n.threshold.getThreshold() , "\n")
print(f"{parameters.nh3.identity.label} : ",parameters.nh3.checkParameterThreshold().level.value , "\n",parameters.nh3.threshold.getThreshold() , "\n")
print(f"{parameters.salinity.identity.label} : ",parameters.salinity.checkParameterThreshold().level.value , "\n",parameters.salinity.threshold.getThreshold() , "\n")



