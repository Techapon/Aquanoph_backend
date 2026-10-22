from abc import ABC, abstractmethod

from identity.units.threshold_units.t_levels import LevelType
from identity.units.threshold_units.threshold_level_model import ThresholdLevelModel
from identity.units.threshold_units.threshold_level import ThresholdLevelType
from identity.units.threshold_units.value_range import Range, RangeType
from ...parameters.pond_parameter_enum import PondParameters



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
    def getThreshold(self):
        pass

    @abstractmethod
    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:
        pass

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

    def getThreshold(self):
        return (
            f"{self.parameter.label} --> "
            f"optimal : {self.optimal.min} - {self.optimal.max}, "
            f"stress : {self.stress.min} - {self.optimal.min} , {self.optimal.max} - {self.stress.max}, "
            f"hight risk : {self.highRisk.min} - {self.stress.min} , {self.stress.max} - {self.highRisk.max} "
            f"critical : {self.critical.min} - {self.highRisk.min} , {self.highRisk.max} - {self.critical.max} "
        )

    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:

        level:ThresholdLevelType
        
        cv = parameterValueNow # current value
        optimal = self.optimal
        stress = self.stress
        highRisk = self.highRisk
        critical = self.critical

        if (
            # Optimal Type check
            not isinstance(optimal.min,RangeType) and 
            not isinstance(optimal.max,RangeType) and
            # Stress Type check
            not isinstance(stress.min,RangeType) and 
            not isinstance(stress.max,RangeType) and
            # Hight Type Risk check
            not isinstance(highRisk.min,RangeType) and 
            not isinstance(highRisk.max,RangeType)
        ):
            # Optimal
            if cv >= optimal.min and cv <= optimal.max :
                level = ThresholdLevelType.Optimal
            # Stress
            elif cv >= stress.min and cv < optimal.min :
                level = ThresholdLevelType.Stress
            elif cv <= stress.max and cv > optimal.max :
                level = ThresholdLevelType.Stress
            # Hight Risk
            elif cv >= highRisk.min and cv < stress.min :
                level = ThresholdLevelType.HighRisk
            elif cv <= highRisk.max and cv > stress.max :
                level = ThresholdLevelType.HighRisk
            # Critical
            elif cv > highRisk.max:
                level = ThresholdLevelType.Critical
            elif cv < highRisk.min:
                level = ThresholdLevelType.Critical
            
        return ThresholdLevelModel(
            level = level
        )

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

    def getThreshold(self):
        match self.levelType:
            case LevelType.eqaMoreThan:
                return (
                    f"{self.parameter.label} --> "
                    f"optimal : >= {self.optimal}, "
                    f"stress : < {self.optimal} and >= {self.stress}, "
                    f"hight risk : < {self.stress} and >= {self.highRisk}, "
                    f"critical : < {self.highRisk} and > {self.critical}"
                )
            case LevelType.eqaLessThan:
                return (
                    f"{self.parameter.label} --> "
                    f"optimal : <= {self.optimal}, "
                    f"warn : > {self.optimal} and <= {self.stress}, "
                    f"hight risk : > {self.stress} and <= {self.highRisk}, "
                    f"critical : > {self.stress} and < {self.critical}"
                )

    def checkThreshold(self,*,parameterValueNow:float) -> ThresholdLevelModel:

        level:ThresholdLevelType

        cv = parameterValueNow # current value
        optimal = self.optimal
        stress = self.stress
        highRisk = self.highRisk
        critical = self.critical

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

        return ThresholdLevelModel(
            level = level
        )