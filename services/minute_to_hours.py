from datetime import datetime,timedelta

def MinuteToHours(minute) -> float:
    """ใช้เฉพาะ text (appendDes) — ปัด 1 ตำแหน่ง กัน "3.916348691944444 h"
    ponytail: ถ้าเอาไปใช้คำนวณต่อ ให้แยก function d ปื่นแทนการปัดที่นี่"""
    return round(minute / 60, 1)