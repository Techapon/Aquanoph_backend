from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from identity.units.threshold_units.threshold_level.threshold_direction import (
    DirectionalPair,
    ThresholdDirection,
)

class SeverityDesSetModel:

    def __init__(
        self,
        *,
        # Optimal
        pureOptimal: SeverityDescriptionModel,
        needRocoveryEleveted:SeverityDescriptionModel,
        needRocoveryCritical:SeverityDescriptionModel,

        # Stress
        pureStress: SeverityDescriptionModel,
        continuousStressExceeded: SeverityDescriptionModel,
        cumStressExceeded: SeverityDescriptionModel,

        # High Risk
        pureHighRisk: SeverityDescriptionModel,
        continuousHighRiskExceeded: SeverityDescriptionModel,
        cumHighRiskExceeded: SeverityDescriptionModel,

        # Critical
        pureCritical: SeverityDescriptionModel,

        # Episode
        episodeExceeded: SeverityDescriptionModel,

        # วลีที่ใช้ประกอบข้อความเชิงเวลาที่ evaluator สร้าง เช่น "DO ต่ำ", "NH₃ สูง", "pH สูง"
        # (แทนคำว่า "ต่ำ" ที่เคย hardcode ไว้ใน evaluator ซึ่งผิดสำหรับ NH3 และฝั่ง high)
        abnormalLabel: str = "ค่าผิดปกติ"
    ):
        self.pureOptimal = pureOptimal
        self.needRocoveryEleveted = needRocoveryEleveted
        self.needRocoveryCritical = needRocoveryCritical

        self.pureStress = pureStress
        self.continuousStressExceeded = continuousStressExceeded
        self.cumStressExceeded = cumStressExceeded

        self.pureHighRisk = pureHighRisk
        self.continuousHighRiskExceeded = continuousHighRiskExceeded
        self.cumHighRiskExceeded = cumHighRiskExceeded

        self.pureCritical = pureCritical

        self.episodeExceeded = episodeExceeded

        self.abnormalLabel = abnormalLabel

    def forDirection(self, direction: ThresholdDirection | None = None) -> "SeverityDesSetModel":
        """Level parameter มีชุดเดียว -> คืนตัวเองไม่ว่า direction จะเป็นอะไร"""
        return self


class RangeSeverityDesSet(DirectionalPair[SeverityDesSetModel]):
    """Range parameter (pH, Temperature): ชุดข้อความแยกฝั่ง low / high"""

    @property
    def pureOptimal(self) -> SeverityDescriptionModel:
        # Optimal ไม่มีทิศทาง จึงใช้ pureOptimal ของฝั่ง low เป็นตัวแทน
        # (ควรเขียนข้อความ pureOptimal ของสองฝั่งให้เหมือนกัน)
        return self.low.pureOptimal


AnySeverityDesSet = SeverityDesSetModel | RangeSeverityDesSet