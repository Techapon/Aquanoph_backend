from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel

def DO_EscalationPolicy() -> EscalationPolicy:
    return EscalationPolicy(
        
    )

def DO_SeverityDesSet() -> SeverityDesSetModel:
    return SeverityDesSetModel(
        abnormalLabel = "DO ต่ำ",
        # Optimal
        pureOptimal = SeverityDescriptionModel(
            des = "ปลาดูในระดับ DO ในเหมาะสม",
            detail= "ดีต่อการเจริญเติบโตมาก",
            guid = "ระวังและดูแลตามปกติ",
            append= None
        ),
        needRocoveryEleveted =  SeverityDescriptionModel(
            des = "ปลาค้องการการพักฟื้น จาก DO ตํ่าในระดับ เครียดสูง ",
            detail= "เสี่ยงอันตรายขึ้นหากเกิดเหตุการณ์ขึ้นอีก ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดี อย่างเคร่งครัด",
            append= None
        ),
        needRocoveryCritical = SeverityDescriptionModel(
            des = "ปลาค้องการการพักฟื้น จาก DO ตํ่าในระดับ เสี่ยงตาย ",
            detail= "เสี่ยงอันตรายขึ้นหากเกิดเหตุการณ์ขึ้นอีก ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดี อย่างเคร่งครัด",
            append= None
        ),

        # Stress
        pureStress = SeverityDescriptionModel(
            des = "ปลาสะบายเครียดเล็กน้อย",
            detail= "อาจเป็นส่งผลเสียต่อสุขภาพหากอยู่นานกว่านี้",
            guid = "ระวังและดูแลให้ DO กลับมาอยู่ในระดับที่เหมาะสม",
            append= None
        ),
        continuousStressExceeded = SeverityDescriptionModel(
            des = "ปลาสะบายเครียดสูง",
            detail= "เสี่ยงส่งผลต่อสุขภาพระยะยาวหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน",
            append= None
        ),
        cumStressExceeded = SeverityDescriptionModel(
            des = "ปลาสะบายเครียดสูง",
            detail= "เสี่ยงส่งผลต่อสุขภาพระยะยาวหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน",
            append= None
        ),

        # High Risk
        pureHighRisk = SeverityDescriptionModel(
            des = "ปลาสะบายเครียดสูง",
            detail= "อาจเสี่ยงส่งผลเสียต่อปลาอย่างร้ายแรงหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วนที่สุด",
            append= None
        ),
        continuousHighRiskExceeded = SeverityDescriptionModel(
            des = "ปลากำลังเสี่ยงตาย",
            detail= "อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน!!!",
            append= None
        ),
        cumHighRiskExceeded = SeverityDescriptionModel(
            des = "ปลากำลังเสี่ยงตาย",
            detail= "อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน!!!",
            append= None
        ),

        # Critical
        pureCritical = SeverityDescriptionModel(
            des = "ปลากำลังเสี่ยงตาย",
            detail= "อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน!!!",
            append= None
        ),

        # Episode
        episodeExceeded = SeverityDescriptionModel(
            des = "ปลากำลังเสี่ยงตาย",
            detail= "อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
            guid = "ระวังและดูแลให้ DO อยู่ในระดับดีโดยด่วน!!!",
            append= None
        ),
    )
