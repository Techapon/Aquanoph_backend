from __future__ import annotations

from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
    from identity.parameters.pond_parameter_model import PondParametersDeliveryModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold.t_levels import LevelType
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, Threshold

def NO2_N_threshold(nile:NileTilapiaModel) -> LevelThreshold:

    # Final Threshold
    NO2_N_final_threshold = LevelThreshold(
        parameter = PondParameters.NO2_N,
        levelType = LevelType.eqaLessThan,
        optimal = .1,
        stress = .5,
        highRisk = 1,
        critical = 1000 
    )

    return NO2_N_final_threshold
