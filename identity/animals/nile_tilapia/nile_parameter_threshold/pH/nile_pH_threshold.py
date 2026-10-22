from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity.animals.nile_tilapia.nile_model import NileTilapiaModel

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.t_levels import LevelType
from identity.units.threshold_units.threshold import LevelThreshold, Threshold,RangeThreshold
from identity.units.threshold_units.value_range import Range,RangeType

def pH_threshold(nile:NileTilapiaModel) -> RangeThreshold:

    pH_final_threshold = RangeThreshold(
        parameter = PondParameters.pH,
        optimal = Range( min = 7, max = 8.5),
        stress = Range( min = 6.5, max = 9),
        highRisk = Range( min = 6, max = 10),
        critical = Range( min = 0, max = 14),
    )

    return pH_final_threshold