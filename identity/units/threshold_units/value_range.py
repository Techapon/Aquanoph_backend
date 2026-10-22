from enum import Enum

class RangeType(Enum):
    noMax = 1
    noMin = 2

    def __str__(self):
        return "heightest" if self == RangeType.noMax else "lowest"

class Range:
    def __init__(self,*, min: float | RangeType , max: float | RangeType ):
        self.min = min 
        self.max = max