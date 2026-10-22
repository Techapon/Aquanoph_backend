from __future__ import annotations

from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
    from identity.parameters.pond_parameter_model import PondParametersDeliveryModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.t_levels import LevelType
from identity.units.threshold_units.threshold import LevelThreshold, Threshold

def DO_threshold(nile:NileTilapiaModel, parameters:PondParametersDeliveryModel) -> LevelThreshold:

    weight_g : float = nile.weight
    density_kg_m3 : float = nile.density
    temp_c = parameters.tem

    # Estimated oxygen consumption rate of Nile tilapia
    q = 10 ** (
        0.492
        - 0.243 * math.log10(weight_g)
        + 1.68 * math.log10(temp_c)
    )

    oxygen_demand = density_kg_m3 * q / 1000

    adjustment = min(oxygen_demand, 2.0)

    # Preliminary critiria biomass
    if density_kg_m3 < 5:
        optimal_base, stress_base, high_risk_base = 5.0, 3.5, 2.5
    elif density_kg_m3 < 15:
        optimal_base, stress_base, high_risk_base = 5.5, 4.0, 3.0
    elif density_kg_m3 < 30:
        optimal_base, stress_base, high_risk_base = 6.0, 4.5, 3.5
    elif density_kg_m3 < 60:
        optimal_base, stress_base, high_risk_base = 6.5, 5.0, 4.0
    else:
        optimal_base, stress_base, high_risk_base = 7.0, 5.5, 4.5

    optimal = round(optimal_base + adjustment, 1)
    stress = round(stress_base + adjustment, 1)
    high_risk = round(high_risk_base + adjustment, 1)

    # Final Threshold
    DO_final_threshold = LevelThreshold(
        parameter = PondParameters.DO,
        levelType = LevelType.eqaMoreThan,
        optimal = optimal,
        stress = stress,
        highRisk = high_risk,
        critical = 0
    )

    return DO_final_threshold
