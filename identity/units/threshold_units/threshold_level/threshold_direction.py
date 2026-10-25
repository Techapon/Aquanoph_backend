from enum import Enum
from typing import Generic, TypeVar


class ThresholdDirection(Enum):
    Low = "low"
    High = "high"


T = TypeVar("T")


class DirectionalPair(Generic[T]):
    """
    คู่ของ config ฝั่งต่ำ/ฝั่งสูง (เช่น EscalationPolicy 2 ชุด หรือ SeverityDesSetModel 2 ชุด)
    มี forDirection() ให้ evaluator เรียกใช้เหมือนกับ config แบบ Level
    """

    def __init__(self, *, low: T, high: T):
        self.low = low
        self.high = high

    def forDirection(self, direction: ThresholdDirection | None) -> T:
        match direction:
            case ThresholdDirection.Low:
                return self.low
            case ThresholdDirection.High:
                return self.high
            case _:
                raise ValueError(
                    "Range parameter ต้องระบุ direction (Low/High) แต่ได้รับ None "
                    "- ตรวจว่า RangeThreshold ส่ง direction มาแล้ว และประวัติเก่าถูก backfill direction แล้ว"
                )