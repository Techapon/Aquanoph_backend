"""Mockup parameter-specific content (detail / guidance) for severity descriptions.

Per SEVERITY_TEXT_REFACTOR_SPEC: these may stay mockup temporarily and are owned
by each parameter. They must never contain another parameter's name
(no "DO" in NH3/NO2_N/salinity, no "อุณหภูมิ" in pH).

Slot keys match the real SeverityDesSetModel field names (no renames).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeverityContent:
    detail: str
    guidance: str


# ---- DO (Level) ----
DO_CONTENT = {
    "pureOptimal": SeverityContent(
        detail="ดีต่อการเจริญเติบโตมาก",
        guidance="ระวังและดูแลตามปกติ",
    ),
    "needRocoveryEleveted": SeverityContent(
        detail="เสี่ยงอันตรายขึ้นหากเกิดเหตุการณ์ขึ้นอีก ปลาอาจ...",
        guidance="ระวังและดูแลให้ DO อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "needRocoveryCritical": SeverityContent(
        detail="เสี่ยงอันตรายขึ้นหากเกิดเหตุการณ์ขึ้นอีก ปลาอาจ...",
        guidance="ระวังและดูแลให้ DO อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "pureStress": SeverityContent(
        detail="อาจส่งผลเสียต่อสุขภาพหากอยู่นานกว่านี้",
        guidance="ระวังและดูแลให้ DO กลับมาอยู่ในระดับที่เหมาะสม",
    ),
    "continuousStressExceeded": SeverityContent(
        detail="เสี่ยงส่งผลต่อสุขภาพระยะยาวหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "cumStressExceeded": SeverityContent(
        detail="เสี่ยงส่งผลต่อสุขภาพระยะยาวหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "pureHighRisk": SeverityContent(
        detail="อาจเสี่ยงส่งผลเสียต่อปลาอย่างร้ายแรงหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ควรดำเนินการทันที ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "continuousHighRiskExceeded": SeverityContent(
        detail="อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ดำเนินการทันที ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "cumHighRiskExceeded": SeverityContent(
        detail="อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ดำเนินการทันที ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "pureCritical": SeverityContent(
        detail="อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ดำเนินการทันที ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
    "episodeExceeded": SeverityContent(
        detail="อาจเสี่ยงตายหากอยู่นานกว่านี้ ปลาอาจ...",
        guidance="ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ระวังและดูแลให้ DO อยู่ในระดับดี",
    ),
}

# ---- NH3 (Level) ----
NH3_CONTENT = {
    "pureOptimal": SeverityContent(
        detail="[MOCKUP] ไม่เป็นพิษต่อปลา",
        guidance="[MOCKUP] ดูแลตามปกติ",
    ),
    "needRocoveryEleveted": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ NH3 อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "needRocoveryCritical": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงสูงมากหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ NH3 อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "pureStress": SeverityContent(
        detail="[MOCKUP] NH3 เริ่มส่งผลต่อปลา",
        guidance="[MOCKUP] ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "continuousStressExceeded": SeverityContent(
        detail="[MOCKUP] NH3 สูงต่อเนื่อง ปลาเสี่ยงต่อเนื้อเยื่อ",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "cumStressExceeded": SeverityContent(
        detail="[MOCKUP] NH3 สะสมสูง ปลาเสี่ยงต่อเนื้อเยื่อ",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "pureHighRisk": SeverityContent(
        detail="[MOCKUP] NH3 ระดับเสี่ยงสูง ปลาหายใจลำบาก",
        guidance="[MOCKUP] ควรดำเนินการทันที ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "continuousHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] NH3 สูงต่อเนื่อง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "cumHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] NH3 สะสมสูง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "pureCritical": SeverityContent(
        detail="[MOCKUP] NH3 วิกฤต เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
    "episodeExceeded": SeverityContent(
        detail="[MOCKUP] NH3 เกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ระวังและดูแลให้ NH3 อยู่ในระดับดี",
    ),
}

# ---- NO2_N (Level) ----
NO2_N_CONTENT = {
    "pureOptimal": SeverityContent(
        detail="[MOCKUP] ไม่เป็นพิษต่อปลา",
        guidance="[MOCKUP] ดูแลตามปกติ",
    ),
    "needRocoveryEleveted": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ NO2 อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "needRocoveryCritical": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงสูงมากหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ NO2 อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "pureStress": SeverityContent(
        detail="[MOCKUP] NO2 เริ่มส่งผลต่อปลา",
        guidance="[MOCKUP] ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "continuousStressExceeded": SeverityContent(
        detail="[MOCKUP] NO2 สูงต่อเนื่อง ปลาหายใจลำบาก",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "cumStressExceeded": SeverityContent(
        detail="[MOCKUP] NO2 สะสมสูง ปลาหายใจลำบาก",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "pureHighRisk": SeverityContent(
        detail="[MOCKUP] NO2 ระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ",
        guidance="[MOCKUP] ควรดำเนินการทันที ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "continuousHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] NO2 สูงต่อเนื่อง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "cumHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] NO2 สะสมสูง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "pureCritical": SeverityContent(
        detail="[MOCKUP] NO2 วิกฤต เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
    "episodeExceeded": SeverityContent(
        detail="[MOCKUP] NO2 เกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ระวังและดูแลให้ NO2 อยู่ในระดับดี",
    ),
}

# ---- salinity (Level) ----
SALINITY_CONTENT = {
    "pureOptimal": SeverityContent(
        detail="[MOCKUP] เอื้อต่อการเจริญเติบโตของปลา",
        guidance="[MOCKUP] ดูแลตามปกติ",
    ),
    "needRocoveryEleveted": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ salinity อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "needRocoveryCritical": SeverityContent(
        detail="[MOCKUP] ยังเสี่ยงสูงมากหากเกิดเหตุการณ์ซ้ำ",
        guidance="[MOCKUP] ระวังและดูแลให้ salinity อยู่ในระดับดี อย่างเคร่งครัด",
    ),
    "pureStress": SeverityContent(
        detail="[MOCKUP] salinity ผิดปกติ ปลาเครียดจากการเปลี่ยนแปลงเกลือ",
        guidance="[MOCKUP] ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "continuousStressExceeded": SeverityContent(
        detail="[MOCKUP] salinity ผิดปกติต่อเนื่อง ปลาเครียดจากการเปลี่ยนแปลงเกลือ",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "cumStressExceeded": SeverityContent(
        detail="[MOCKUP] salinity สะสมผิดปกติ ปลาเครียดจากการเปลี่ยนแปลงเกลือ",
        guidance="[MOCKUP] ควรเริ่มแก้ไขโดยเร็ว ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "pureHighRisk": SeverityContent(
        detail="[MOCKUP] salinity ระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ",
        guidance="[MOCKUP] ควรดำเนินการทันที ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "continuousHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] salinity ผิดปกติต่อเนื่อง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "cumHighRiskExceeded": SeverityContent(
        detail="[MOCKUP] salinity สะสมผิดปกติ เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "pureCritical": SeverityContent(
        detail="[MOCKUP] salinity วิกฤต เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันที ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
    "episodeExceeded": SeverityContent(
        detail="[MOCKUP] salinity เกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา",
        guidance="[MOCKUP] ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ระวังและดูแลให้ salinity อยู่ในระดับดี",
    ),
}

_OPTIMAL_DETAIL = "เอื้อต่อการกินอาหารและการเจริญเติบโต"
_OPTIMAL_GUIDANCE = "ดูแลตามปกติ"
_RECOVERY_DETAIL_HIGH = "ยังเสี่ยงหากเกิดเหตุการณ์ซ้ำในช่วงนี้"
_RECOVERY_DETAIL_CRITICAL = "ยังเสี่ยงสูงมากหากเกิดเหตุการณ์ซ้ำในช่วงนี้"

# ---- pH (Range) ----
PH_LOW_CONTENT = {
    "pureOptimal": SeverityContent(detail=_OPTIMAL_DETAIL, guidance=_OPTIMAL_GUIDANCE),
    "needRocoveryEleveted": SeverityContent(detail=_RECOVERY_DETAIL_HIGH, guidance="รักษา pH ให้อยู่ในช่วงเหมาะสมต่อเนื่อง ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "needRocoveryCritical": SeverityContent(detail=_RECOVERY_DETAIL_CRITICAL, guidance="รักษา pH ให้อยู่ในช่วงเหมาะสมต่อเนื่องอย่างเคร่งครัด ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "pureStress": SeverityContent(detail="pH ต่ำกว่าช่วงเหมาะสม ทำให้ปลาเครียดจากการเปลี่ยนแปลงสภาพน้ำ", guidance="ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "continuousStressExceeded": SeverityContent(detail="pH ต่ำต่อเนื่อง ปลาเครียดจากการเปลี่ยนแปลงสภาพน้ำ", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "cumStressExceeded": SeverityContent(detail="pH ต่ำสะสม ปลาเครียดจากการเปลี่ยนแปลงสภาพน้ำ", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "pureHighRisk": SeverityContent(detail="pH ต่ำระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ", guidance="ควรดำเนินการทันที ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "continuousHighRiskExceeded": SeverityContent(detail="pH ต่ำต่อเนื่อง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "cumHighRiskExceeded": SeverityContent(detail="pH ต่ำสะสม เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "pureCritical": SeverityContent(detail="pH ต่ำวิกฤต เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
    "episodeExceeded": SeverityContent(detail="pH ต่ำเกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา"),
}

PH_HIGH_CONTENT = {
    "pureOptimal": SeverityContent(detail=_OPTIMAL_DETAIL, guidance=_OPTIMAL_GUIDANCE),
    "needRocoveryEleveted": SeverityContent(detail=_RECOVERY_DETAIL_HIGH, guidance="รักษา pH ให้อยู่ในช่วงเหมาะสมต่อเนื่อง ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "needRocoveryCritical": SeverityContent(detail=_RECOVERY_DETAIL_CRITICAL, guidance="รักษา pH ให้อยู่ในช่วงเหมาะสมต่อเนื่องอย่างเคร่งครัด ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "pureStress": SeverityContent(detail="pH สูงกว่าช่วงเหมาะสม ทำให้ NH3 มีสัดส่วนที่เป็นพิษมากขึ้น", guidance="ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "continuousStressExceeded": SeverityContent(detail="pH สูงต่อเนื่อง NH3 เป็นพิษมากขึ้น", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "cumStressExceeded": SeverityContent(detail="pH สูงสะสม NH3 เป็นพิษมากขึ้น", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "pureHighRisk": SeverityContent(detail="pH สูงระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ", guidance="ควรดำเนินการทันที ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "continuousHighRiskExceeded": SeverityContent(detail="pH สูงต่อเนื่อง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "cumHighRiskExceeded": SeverityContent(detail="pH สูงสะสม เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "pureCritical": SeverityContent(detail="pH สูงวิกฤต เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
    "episodeExceeded": SeverityContent(detail="pH สูงเกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ควรเฝ้าระวัง NH3 ที่อาจเป็นพิษมากขึ้น"),
}

# ---- Temperature (Range) ----
TEMP_LOW_CONTENT = {
    "pureOptimal": SeverityContent(detail=_OPTIMAL_DETAIL, guidance=_OPTIMAL_GUIDANCE),
    "needRocoveryEleveted": SeverityContent(detail=_RECOVERY_DETAIL_HIGH, guidance="รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่อง ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "needRocoveryCritical": SeverityContent(detail=_RECOVERY_DETAIL_CRITICAL, guidance="รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่องอย่างเคร่งครัด ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "pureStress": SeverityContent(detail="น้ำเย็นกว่าช่วงเหมาะสม ปลากินอาหารลดลง", guidance="ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "continuousStressExceeded": SeverityContent(detail="น้ำเย็นต่อเนื่อง ปลากินอาหารลดลง", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "cumStressExceeded": SeverityContent(detail="น้ำเย็นสะสม ปลากินอาหารลดลง", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "pureHighRisk": SeverityContent(detail="น้ำเย็นระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ", guidance="ควรดำเนินการทันที ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "continuousHighRiskExceeded": SeverityContent(detail="น้ำเย็นต่อเนื่อง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "cumHighRiskExceeded": SeverityContent(detail="น้ำเย็นสะสม เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "pureCritical": SeverityContent(detail="น้ำเย็นวิกฤต เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรลดการให้อาหารและเฝ้าระวัง DO"),
    "episodeExceeded": SeverityContent(detail="น้ำเย็นเกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ควรลดการให้อาหารและเฝ้าระวัง DO"),
}

TEMP_HIGH_CONTENT = {
    "pureOptimal": SeverityContent(detail=_OPTIMAL_DETAIL, guidance=_OPTIMAL_GUIDANCE),
    "needRocoveryEleveted": SeverityContent(detail=_RECOVERY_DETAIL_HIGH, guidance="รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่อง ควรเฝ้าระวัง DO และ NH3"),
    "needRocoveryCritical": SeverityContent(detail=_RECOVERY_DETAIL_CRITICAL, guidance="รักษาอุณหภูมิให้อยู่ในช่วงเหมาะสมต่อเนื่องอย่างเคร่งครัด ควรเฝ้าระวัง DO และ NH3"),
    "pureStress": SeverityContent(detail="น้ำร้อนกว่าช่วงเหมาะสม ปลาใช้ออกซิเจนมากขึ้น และ NH3 มีสัดส่วนที่เป็นพิษมากขึ้น", guidance="ควรเฝ้าระวัง DO และ NH3"),
    "continuousStressExceeded": SeverityContent(detail="น้ำร้อนต่อเนื่อง ปลาใช้ออกซิเจนมากขึ้น", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวัง DO และ NH3"),
    "cumStressExceeded": SeverityContent(detail="น้ำร้อนสะสม ปลาใช้ออกซิเจนมากขึ้น", guidance="ควรเริ่มแก้ไขโดยเร็ว ควรเฝ้าระวัง DO และ NH3"),
    "pureHighRisk": SeverityContent(detail="น้ำร้อนระดับเสี่ยงสูง ปลาเสี่ยงต่อเนื้อเยื่อ", guidance="ควรดำเนินการทันที ควรเฝ้าระวัง DO และ NH3"),
    "continuousHighRiskExceeded": SeverityContent(detail="น้ำร้อนต่อเนื่อง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง DO และ NH3"),
    "cumHighRiskExceeded": SeverityContent(detail="น้ำร้อนสะสม เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง DO และ NH3"),
    "pureCritical": SeverityContent(detail="น้ำร้อนวิกฤต เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันที ควรเฝ้าระวัง DO และ NH3"),
    "episodeExceeded": SeverityContent(detail="น้ำร้อนเกิดซ้ำหลายครั้ง เสี่ยงต่อชีวิตปลา", guidance="ดำเนินการทันทีและหาสาเหตุที่ทำให้เกิดซ้ำ ควรเฝ้าระวัง DO และ NH3"),
}
