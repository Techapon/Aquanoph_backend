"""Append text templates for SeverityEvaluator (SEVERITY_TEXT_REFACTOR_SPEC).

`appendDes` is runtime-generated time text. Only the evaluator formats these;
providers must never write appendDes themselves.
"""

# abnormal_label ที่ evaluator ส่งมา (เช่น "DO ต่ำ", "pH สูง")
CONTINUOUS = "{label}ต่อเนื่องเกิน {limit_hours} ชม. แล้ว ปัจจุบัน {current_hours} ชม."

CUMULATIVE = "{label}รวม {current_hours} ชม. ใน 24 ชม. เกินเกณฑ์ {limit_hours} ชม."

EPISODE = "{label}เกิดซ้ำ {episode_count} ครั้งใน 24 ชม. เกินเกณฑ์ {limit_count} ครั้ง"

RECOVERY = "เกิดเวลาประมาณ {event_time} เหลืออีก {remaining_hours} ชม."

PENDING_STRESS = (
    "{label}มาแล้ว {current_hours} ชม. "
    "หากต่อเนื่องจนครบ {limit_hours} ชม. จะอันตรายขึ้น"
)

PENDING_HIGH_RISK = (
    "{label}มาแล้ว {current_hours} ชม. "
    "หากต่อเนื่องจนครบ {limit_hours} ชม. จะอันตรายขึ้นมากกว่าเดิม"
)
