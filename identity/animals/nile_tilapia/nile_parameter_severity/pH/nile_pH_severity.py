from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    EscalationPolicy,
    RangeEscalationPolicy,
)
from identity.units.severity_units.severity_description.severity_des_set_model import (
    RangeSeverityDesSet,
    SeverityDesSetModel,
)
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel


def pH_EscalationPolicy() -> RangeEscalationPolicy:
    return RangeEscalationPolicy(
        low = EscalationPolicy(),
        high = EscalationPolicy(),
    )


def _pHSideSet(*, label: str, detail: str, care: str) -> SeverityDesSetModel:
    """
    สร้างชุดข้อความ 1 ฝั่ง ใช้ factory เพื่อไม่ต้องเขียนซ้ำ 11 รายการต่อฝั่ง
    - label  : วลีที่ evaluator ใช้ต่อท้ายข้อความเชิงเวลา เช่น "อุณหภูมิต่ำ"
    - detail : ผลต่อปลาของฝั่งนั้น
    - care   : คำแนะนำเฉพาะฝั่ง
    ข้อความทั้งหมดเป็นร่าง ให้ผู้เชี่ยวชาญตรวจก่อนใช้งานจริง
    """
    return SeverityDesSetModel(
        abnormalLabel = label,

        # Optimal (ควรเหมือนกันทั้งสองฝั่ง เพราะ RangeSeverityDesSet ใช้ของฝั่ง low)
        pureOptimal = SeverityDescriptionModel(
            des = "อุณหภูมิน้ำอยู่ในช่วงเหมาะสม",
            detail = "เอื้อต่อการกินอาหารและการเจริญเติบโต",
            guid = "ดูแลตามปกติ",
        ),
        needRocoveryEleveted = SeverityDescriptionModel(
            des = f"ปลากำลังฟื้นตัวจากเหตุการณ์{label}ระดับเสี่ยงสูง",
            detail = "ยังเสี่ยงหากเกิดเหตุการณ์ซ้ำในช่วงนี้",
            guid = f"รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่อง {care}",
        ),
        needRocoveryCritical = SeverityDescriptionModel(
            des = f"ปลากำลังฟื้นตัวจากเหตุการณ์{label}ระดับวิกฤต",
            detail = "ยังเสี่ยงสูงมากหากเกิดเหตุการณ์ซ้ำในช่วงนี้",
            guid = f"รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่องอย่างเคร่งครัด {care}",
        ),

        # Stress
        pureStress = SeverityDescriptionModel(
            des = f"{label}กว่าช่วงเหมาะสมเล็กน้อย ปลาเริ่มเครียด",
            detail = detail,
            guid = care,
        ),
        continuousStressExceeded = SeverityDescriptionModel(
            des = f"{label}ต่อเนื่องนาน ปลาเครียดสูง",
            detail = detail,
            guid = f"ควรเริ่มแก้ไขโดยเร็ว {care}",
        ),
        cumStressExceeded = SeverityDescriptionModel(
            des = f"{label}สะสมหลายช่วงใน 24 ชม. ปลาเครียดสูง",
            detail = detail,
            guid = f"ควรเริ่มแก้ไขโดยเร็ว {care}",
        ),

        # High Risk
        pureHighRisk = SeverityDescriptionModel(
            des = f"{label}ถึงระดับเสี่ยงสูง",
            detail = detail,
            guid = f"ควรดำเนินการทันที {care}",
        ),
        continuousHighRiskExceeded = SeverityDescriptionModel(
            des = f"{label}ระดับเสี่ยงสูงต่อเนื่องนาน เสี่ยงต่อชีวิตปลา",
            detail = detail,
            guid = f"ดำเนินการทันที {care}",
        ),
        cumHighRiskExceeded = SeverityDescriptionModel(
            des = f"{label}ระดับเสี่ยงสูงสะสมใน 24 ชม. เสี่ยงต่อชีวิตปลา",
            detail = detail,
            guid = f"ดำเนินการทันที {care}",
        ),

        # Critical
        pureCritical = SeverityDescriptionModel(
            des = f"{label}ถึงระดับวิกฤต เสี่ยงต่อชีวิตปลา",
            detail = detail,
            guid = f"ดำเนินการทันที {care}",
        ),

        # Episode
        episodeExceeded = SeverityDescriptionModel(
            des = f"{label}ระดับเสี่ยงสูงเกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา",
            detail = detail,
            guid = f"ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ {care}",
        ),
    )


def pH_SeverityDesSet() -> RangeSeverityDesSet:
    return RangeSeverityDesSet(
        low = _pHSideSet(
            label = "pH ต่ำ",
            detail = "pH ต่ำกว่าช่วงเหมาะสม",            # TODO: ให้ผู้เชี่ยวชาญเติมผลต่อปลา
            care = "ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา",
        ),
        high = _pHSideSet(
            label = "pH สูง",
            detail = "pH สูงกว่าช่วงเหมาะสม",
            care = "ควรเฝ้าระวัง NH₃ ที่อาจเป็นพิษมากขึ้น",
        ),
    )