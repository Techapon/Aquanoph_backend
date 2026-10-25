import math
from abc import ABC, abstractmethod
from typing import NamedTuple

from identity.units.threshold_units.threshold.threshold_type_level_enum import LevelType
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold.value_range import Range, RangeType
from ....parameters.pond_parameter_enum import PondParameters

# Mother Class
class Threshold(ABC):
    def __init__(self,
                 *,
                 parameter: PondParameters,
                 optimal: Range | float,
                 stress: Range | float,
                 highRisk: Range | float,
                 critical: Range | float
                ):
        self.parameter = parameter
        self.optimal = optimal
        self.stress = stress
        self.highRisk = highRisk
        self.critical = critical

    @abstractmethod
    def getThreshold(self) -> str:
        pass

    @abstractmethod
    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:
        pass

class _RangeBounds(NamedTuple):
    """ขอบของแต่ละโซนที่ตรวจแล้วว่าเป็นตัวเลขจริง (ไม่ใช่ RangeType)"""
    optimalMin: float
    optimalMax: float
    stressMin: float
    stressMax: float
    highRiskMin: float
    highRiskMax: float


def _asNumber(label: str, name: str, value: float | RangeType) -> float:
    # isinstance ตรงนี้ทำให้ type checker รู้ว่าค่าที่คืนเป็น float
    if isinstance(value, RangeType):
        raise ValueError(f"{label}: {name} ต้องระบุเป็นตัวเลข ไม่ใช่ {value}")
    return float(value)


# Child Class
class RangeThreshold(Threshold):
    # Narrow the union types from Threshold for range-specific formatting.
    optimal: Range
    stress: Range
    highRisk: Range
    critical: Range

    def __init__(self,
                 *,
                 parameter: PondParameters,
                 optimal: Range,
                 stress: Range,
                 highRisk: Range,
                 critical: Range
                ):
        super().__init__(parameter=parameter, optimal=optimal, stress=stress,highRisk=highRisk, critical=critical)
        self._bounds: _RangeBounds = self._validate()

    def _validate(self) -> _RangeBounds:
        # optimal / stress / highRisk ต้องเป็นตัวเลขจริงทั้งสองขอบ
        # (critical คือ "ทุกอย่างที่เลย highRisk ออกไป" จึงใช้ noMin/noMax ได้)
        lb = self.parameter.label
        b = _RangeBounds(
            optimalMin=_asNumber(lb, "optimal.min", self.optimal.min),
            optimalMax=_asNumber(lb, "optimal.max", self.optimal.max),
            stressMin=_asNumber(lb, "stress.min", self.stress.min),
            stressMax=_asNumber(lb, "stress.max", self.stress.max),
            highRiskMin=_asNumber(lb, "highRisk.min", self.highRisk.min),
            highRiskMax=_asNumber(lb, "highRisk.max", self.highRisk.max),
        )
        # low_critical < low_high_risk < low_stress < optimal_low <= optimal_high
        #   < high_stress < high_high_risk < high_critical
        if not (b.highRiskMin < b.stressMin < b.optimalMin <= b.optimalMax < b.stressMax < b.highRiskMax):
            raise ValueError(
                f"{lb}: ลำดับ threshold ไม่ถูกต้อง "
                f"ต้องเป็น highRisk.min < stress.min < optimal.min <= optimal.max < stress.max < highRisk.max"
            )
        return b

    def getThreshold(self) -> str:
        return (
            f"{self.parameter.label} --> "
            f"optimal : {self.optimal.min} - {self.optimal.max}, "
            f"stress : {self.stress.min} - {self.optimal.min} , {self.optimal.max} - {self.stress.max}, "
            f"high risk : {self.highRisk.min} - {self.stress.min} , {self.stress.max} - {self.highRisk.max} "
            f"critical : < {self.highRisk.min} , > {self.highRisk.max} "
        )

    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:
        cv = parameterValueNow # current value
        if math.isnan(cv):
            raise ValueError(f"{self.parameter.label}: ค่าที่อ่านได้เป็น NaN")

        b = self._bounds

        # Optimal (รวมขอบทั้งสองข้าง) -> ไม่มี direction
        if b.optimalMin <= cv <= b.optimalMax:
            return ThresholdLevelModel(level=ThresholdLevelType.Optimal)

        # ต่ำกว่า optimal band
        if cv < b.optimalMin:
            direction = ThresholdDirection.Low
            if cv >= b.stressMin:
                level = ThresholdLevelType.Stress
            elif cv >= b.highRiskMin:
                level = ThresholdLevelType.HighRisk
            else:
                level = ThresholdLevelType.Critical
        # สูงกว่า optimal band
        else:
            direction = ThresholdDirection.High
            if cv <= b.stressMax:
                level = ThresholdLevelType.Stress
            elif cv <= b.highRiskMax:
                level = ThresholdLevelType.HighRisk
            else:
                level = ThresholdLevelType.Critical

        return ThresholdLevelModel(level=level, direction=direction)

class LevelThreshold(Threshold):
    # Narrow the union types from Threshold for level-specific formatting.
    optimal: float
    stress: float
    highRisk: float
    critical: float

    def __init__(self,
                 *,
                 parameter: PondParameters,
                 levelType: LevelType,
                 optimal: float,
                 stress: float,
                 highRisk: float,
                 critical: float,
                ):
        self.levelType = levelType
        super().__init__(parameter=parameter, optimal=optimal, stress=stress,highRisk=highRisk, critical=critical)

    def getThreshold(self) -> str:
        match self.levelType:
            case LevelType.eqaMoreThan:
                return (
                    f"{self.parameter.label} --> "
                    f"optimal : >= {self.optimal}, "
                    f"stress : < {self.optimal} and >= {self.stress}, "
                    f"high risk : < {self.stress} and >= {self.highRisk}, "
                    f"critical : < {self.highRisk}"
                )
            case LevelType.eqaLessThan:
                return (
                    f"{self.parameter.label} --> "
                    f"optimal : <= {self.optimal}, "
                    f"stress : > {self.optimal} and <= {self.stress}, "
                    f"high risk : > {self.stress} and <= {self.highRisk}, "
                    f"critical : > {self.highRisk}"
                )

    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:

        level:ThresholdLevelType

        cv = parameterValueNow # current value
        optimal = self.optimal
        stress = self.stress
        highRisk = self.highRisk

        match self.levelType:
            case LevelType.eqaMoreThan:
                if cv >= optimal :
                    level = ThresholdLevelType.Optimal
                elif cv >= stress :
                    level = ThresholdLevelType.Stress
                elif cv >= highRisk :
                    level = ThresholdLevelType.HighRisk
                else : 
                    level = ThresholdLevelType.Critical
                
            case LevelType.eqaLessThan:
                if cv <= optimal :
                    level = ThresholdLevelType.Optimal
                elif cv <= stress :
                    level = ThresholdLevelType.Stress
                elif cv <= highRisk :
                    level = ThresholdLevelType.HighRisk
                else : 
                    level = ThresholdLevelType.Critical

            case _:
                raise ValueError(f"ไม่รู้จัก levelType: {self.levelType}")

        # Level parameter ทางเดียว -> direction = None เสมอ
        return ThresholdLevelModel(level = level)