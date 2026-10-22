from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
    from identity.parameters.pond_parameter_model import PondParametersDeliveryModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.t_levels import LevelType
from identity.units.threshold_units.threshold import LevelThreshold, Threshold

NH3_WARN, NH3_SEVERE = 0.1, 0.5    
DO_LOW = 3.0                      
SHIFT_NH3_WARN, SHIFT_NH3_SEVERE  = 2.5, 5.0
SHIFT_DO_LOW = 2.5 

def salinity_threshold(
    nile: NileTilapiaModel,
    parameters: PondParametersDeliveryModel,
) -> LevelThreshold:

    do_mg_l = parameters.do
    nh3_mg_l = parameters.nh3

    optimal_base, stress_base, high_risk_base = 5.0, 15.0, 25.0

    # Interaction adjustment (stricter thresholds when other stressors present)
    shift = 0.0
    if nh3_mg_l is not None:

        if nh3_mg_l >= NH3_SEVERE:
            shift += SHIFT_NH3_SEVERE
        elif nh3_mg_l >= NH3_WARN:
            shift += SHIFT_NH3_WARN
            
    if do_mg_l is not None and do_mg_l < DO_LOW:
        shift += SHIFT_DO_LOW

    optimal = optimal_base
    stress = max(stress_base - shift, optimal)
    high_risk = max(high_risk_base - shift, stress)

    # Final Threshold
    salinity_final_threshold = LevelThreshold(
        parameter = PondParameters.salinity,
        levelType = LevelType.eqaLessThan,
        optimal = round(optimal, 1),
        stress = round(stress, 1),
        highRisk = round(high_risk, 1),
        critical = 35,
    )

    return salinity_final_threshold