# SEVERITY TEXT REFACTOR SPEC

## เป้าหมาย

Refactor ระบบข้อความ Severity ให้แยกชัดระหว่าง:

1. **Template / structure** — ต้องถูกต้องและ reusable
2. **Parameter-specific content** — `detail`, `guidance` ยังใช้ mockup ได้ชั่วคราว
3. **Runtime-generated time text** — `appendDes` ต้องสร้างโดย `SeverityEvaluator`

ห้ามใช้ข้อความ mockup เป็นตัวกำหนดโครงสร้าง และห้าม copy ข้อความ DO ไปใช้กับ NH3, NO2_N, salinity

## หลักการแยกข้อความ

| Field | ควรเป็นอะไร | ใครสร้าง | Mockup ได้หรือไม่ |
|---|---|---|---|
| `description` | Template ที่รวม `parameter_label`, `direction`, `severity_state` | Provider + shared template | ไม่ควร ต้องใช้ template |
| `detail` | ผลต่อปลา/อาการที่คาดหวังในระดับนั้น | Provider ของ parameter แต่ละตัว | ได้ชั่วคราว |
| `guidance` | การกระทำที่เกษตรกรควรทำ | Provider ของ parameter แต่ละตัว | ได้ชั่วคราว |
| `appendDes` | ข้อความเชิงเวลา เช่น ต่อเนื่อง, สะสม, เกิดซ้ำ, recovery | `SeverityEvaluator` | ไม่ควร ต้องเป็น template |

## โครงสร้างเป้าหมาย

```text
SeverityTextTemplate
        │
        ├── buildDescription(parameterLabel, directionLabel, severityState)
        │
SeverityContent
        ├── detail
        └── guidance
        │
        ├──> SeverityDescriptionModel
        │
SeverityEvaluator
        └── withAppend(timeText)
```

### 1. SeverityTextTemplate

ใช้สร้าง `description` จากข้อมูลที่ระบบรู้จริง

```python
class SeverityTextTemplate:
    @staticmethod
    def build_description(
        *,
        parameter_label: str,
        direction_label: str | None,
        severity_state: str,
    ) -> str:
        if direction_label:
            return f"{parameter_label}{direction_label} {severity_state}"
        return f"{parameter_label} {severity_state}"
```

ตัวอย่าง:

```text
DO + ต่ำ + ต่ำกว่าช่วงเหมาะสมเล็กน้อย
→ "DO ต่ำกว่าช่วงเหมาะสมเล็กน้อย"

NH3 + None + สูงกว่าช่วงเหมาะสม
→ "NH3 สูงกว่าช่วงเหมาะสม"

Temperature + สูง + สูงกว่าช่วงเหมาะสมเล็กน้อย
→ "อุณหภูมิน้ำสูงกว่าช่วงเหมาะสมเล็กน้อย"
```

### 2. SeverityContent

ใช้เก็บข้อความที่ยังเป็น mockup

```python
@dataclass(frozen=True)
class SeverityContent:
    detail: str
    guidance: str
```

ตัวอย่าง:

```python
DO_CONTENT = {
    "pureOptimal": SeverityContent(
        detail="[MOCKUP] ปลาอยู่ในสภาพแวดล้อมที่เหมาะสม",
        guidance="[MOCKUP] ดูแลตามปกติ",
    ),
    "pureStress": SeverityContent(
        detail="[MOCKUP] ปลาอาจเริ่มเครียด",
        guidance="[MOCKUP] ตรวจสอบ aerator และติดตาม DO",
    ),
}
```

## โครงสร้าง slot ที่ต้องมี

ทุก parameter ต้องมี 11 slots:

| Slot | ความหมาย |
|---|---|
| `pureOptimal` | ค่าปกติ ไม่มี recovery hold |
| `needRecoveryElevated` | กลับ Optimal หลัง ElevatedRisk แต่ยังต้อง recovery |
| `needRecoveryCritical` | กลับ Optimal หลัง Critical แต่ยังต้อง recovery |
| `pureStress` | Stress ปกติ |
| `continuousStressExceeded` | Stress ต่อเนื่องเกินเกณฑ์ |
| `cumulativeStressExceeded` | Stress สะสม 24 ชม. เกินเกณฑ์ |
| `pureHighRisk` | HighRisk ปกติ |
| `continuousHighRiskExceeded` | HighRisk ต่อเนื่องเกินเกณฑ์ |
| `cumulativeHighRiskExceeded` | HighRisk สะสม 24 ชม. เกินเกณฑ์ |
| `pureCritical` | Critical ทันที |
| `episodeExceeded` | HighRisk เกิดซ้ำเกินเกณฑ์ |

## กฎการสร้าง description

`description` ต้องไม่ hardcode ชื่อพารามิเตอร์ใน body ของ factory

ให้แยกข้อมูล:

```python
@dataclass(frozen=True)
class SeverityTextContext:
    parameter_label: str       # "DO", "NH3", "NO2-N", "Salinity", "pH", "อุณหภูมิน้ำ"
    direction_label: str | None # "ต่ำ", "สูง", None
    abnormal_label: str        # "DO ต่ำ", "NH3 สูง", "pH สูง"
```

แล้วให้ factory สร้าง description จาก context เสมอ

```python
def build_description(
    context: SeverityTextContext,
    severity_state: str,
) -> str:
    if context.direction_label:
        return (
            f"{context.parameter_label}"
            f"{context.direction_label}"
            f"{severity_state}"
        )
    return f"{context.parameter_label}{severity_state}"
```

## กฎการสร้าง appendDes

`appendDes` ต้องสร้างโดย evaluator เท่านั้น

ตัวอย่าง template:

```text
continuous:
"{abnormal_label}ต่อเนื่องเกิน {limit_hours} ชม. แล้ว ปัจจุบัน {current_hours} ชม."

cumulative:
"{abnormal_label}รวม {current_hours} ชม. ใน 24 ชม. เกินเกณฑ์ {limit_hours} ชม."

episode:
"{abnormal_label}เกิดซ้ำ {episode_count} ครั้งใน 24 ชม. เกินเกณฑ์ {limit_count} ครั้ง"

recovery:
"เกิดเวลาประมาณ {event_time} เหลืออีก {remaining_hours} ชม."
```

## โครงสร้าง provider ใหม่

แต่ละ parameter ควรมีไฟล์แบบนี้:

```python
def DO_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="DO",
        direction_label=None,
        abnormal_label="DO ต่ำ",
    )

    return build_level_severity_des_set(
        context=context,
        contents=DO_CONTENT,
    )
```

ตัวอย่าง NH3:

```python
def NH3_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="NH3",
        direction_label=None,
        abnormal_label="NH3 สูง",
    )

    return build_level_severity_des_set(
        context=context,
        contents=NH3_CONTENT,
    )
```

ตัวอย่าง pH:

```python
def pH_SeverityDesSet() -> RangeSeverityDesSet:
    low_context = SeverityTextContext(
        parameter_label="pH",
        direction_label="ต่ำ",
        abnormal_label="pH ต่ำ",
    )

    high_context = SeverityTextContext(
        parameter_label="pH",
        direction_label="สูง",
        abnormal_label="pH สูง",
    )

    return RangeSeverityDesSet(
        low=build_range_side_severity_des_set(
            context=low_context,
            contents=PH_LOW_CONTENT,
        ),
        high=build_range_side_severity_des_set(
            context=high_context,
            contents=PH_HIGH_CONTENT,
        ),
    )
```

## สิ่งที่ต้องแก้ทันที

1. ลบข้อความ hardcode เกี่ยวกับ DO ใน NH3, NO2_N, salinity
2. ตั้ง `abnormalLabel` ให้ครบทุก parameter
3. เปลี่ยน `description` ให้สร้างจาก template
4. เปลี่ยน `appendDes` ให้ evaluator สร้างจาก template
5. แยก `detail` และ `guidance` ออกจาก template
6. แก้ pH ที่ hardcode คำว่า “อุณหภูมิ”
7. แก้ typo ชื่อ field:
   - `needRocoveryEleveted` → `needRecoveryElevated`
   - `needRocoveryCritical` → `needRecoveryCritical`
   - `HightRiskCountMinute` → `HighRiskCountMinute`

## ข้อห้าม

- ห้ามใส่คำว่า “DO” ใน NH3, NO2_N, salinity
- ห้ามใส่คำว่า “อุณหภูมิ” ใน pH
- ห้าม hardcode “ต่ำ” ใน evaluator เพราะ NH3, NO2, salinity และฝั่ง high ของ Range ใช้คำว่า “สูง”
- ห้ามให้ provider เขียน `appendDes` เอง
- ห้ามให้ `description` อ้างอิง severity ที่ evaluator ยังไม่ได้ตัดสิน