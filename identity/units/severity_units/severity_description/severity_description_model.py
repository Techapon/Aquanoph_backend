import copy


class SeverityDescriptionModel:
    description : str # เช่น ปลากำลังเครียดสูง / เสี่ยงตาย
    detail : str # อาการของปลา เช่น DO ตํ่ามากนานเกินไป อาจส่งผลต่อการเจริญเติบโต บลาๆ
    appendDes : str | None # สาเหตุเชิงเวลา
    guidance : str # best practice

    def __init__(
        self,
        *,
        des: str,
        detail : str,
        guid: str,

        append : str | None = None
    ):
        self.description = des
        self.guidance = guid
        self.detail = detail
        self.appendDes = append

    def withAppend(self, text: str) -> "SeverityDescriptionModel":
        """
        คืนสำเนาที่ต่อ appendDes แล้ว โดยไม่แก้ object ต้นฉบับ
        (evaluator ไม่ควร mutate description set ที่ใช้ร่วมกัน)
        """
        clone = copy.copy(self)
        clone.appendDes = f"{self.appendDes} {text}" if self.appendDes else text
        return clone

    def fullDescription(self) -> str:
        return f"description : {self.description} {self.detail} {self.appendDes or ''} \n guidance : {self.guidance}"