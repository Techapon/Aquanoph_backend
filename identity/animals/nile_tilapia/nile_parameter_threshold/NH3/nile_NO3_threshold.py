from __future__ import annotations

from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
    from identity.parameters.pond_parameter_model import PondParametersDeliveryModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold.t_levels import LevelType
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, Threshold

def NH3_threshold(nile:NileTilapiaModel) -> LevelThreshold:

    # Final Threshold
    NH3_final_threshold = LevelThreshold(
        parameter = PondParameters.NH3,
        levelType = LevelType.eqaLessThan,
        optimal = .02,
        stress = .05,
        highRisk = .2,
        critical = 1000 
    )

    return NH3_final_threshold
