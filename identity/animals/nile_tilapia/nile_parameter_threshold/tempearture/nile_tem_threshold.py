from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.t_levels import LevelType
from identity.units.threshold_units.threshold import LevelThreshold, Threshold,RangeThreshold
from identity.units.threshold_units.value_range import Range,RangeType

def tem_threshold(nile:NileTilapiaModel) -> RangeThreshold:

    tem_final_threshold = RangeThreshold(
        parameter = PondParameters.tem,
        optimal = Range( min = 26, max = 30),
        stress = Range( min = 22, max = 32),
        highRisk = Range( min = 16, max = 35),
        critical = Range( min = RangeType.noMin, max = RangeType.noMax),
    )

    return tem_final_threshold