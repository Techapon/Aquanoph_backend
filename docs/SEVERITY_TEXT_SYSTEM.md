# SEVERITY TEXT SYSTEM — ปัจจุบัน (Severity Description)

> สรุปโครงสร้างข้อความ severity ที่ engine เดิมใช้แสดงสถานการณ์บ่อ (ภาษาไทย)
> จุดประสงค์: เอกสารอ้างอิงสำหรับ refactor หรือแปลภาษาในอนาคต
> ทุกคำอ้างอิงชี้ไปที่ source จริง ณ commit ปัจจุบัน

---

## 1. ภาพรวม (Big Picture)

```
SeverityDescriptionModel  ──┐  (11 ชิ้น/ชุด)
                            ├──> SeverityDesSetModel  ──┐
SeverityDesSetModel(low)   ──┤                           ├──> RangeSeverityDesSet (Range: pH, Temp)
SeverityDesSetModel(high)  ──┘                           │
                                                          ▼
                                        evaluator (SeverityEvaluator) เลือกชิ้น + .withAppend(ข้อความเชิงเวลา)
                                                          ▼
                                        SeverityModel { severityLevel, severityDescription }
                                                          ▼
                                        AnalysisReportModel.severity  (เก็บใน report)
```

**ชั้นโมเดล:**

| Class | หน้าที่ | ไฟล์ |
|---|---|---|
| `SeverityDescriptionModel` | ข้อความ 1 สถานการณ์: description / detail / appendDes / guidance | `identity/units/severity_units/severity_description/severity_description_model.py` |
| `SeverityDesSetModel` | ชุด 11 ชิ้น + abnormalLabel สำหรับ Level parameter | `identity/units/severity_units/severity_description/severity_des_set_model.py` |
| `RangeSeverityDesSet` | คู่ low/high (subclass ของ `DirectionalPair`) | `severity_des_set_model.py` |
| `SeverityModel` | ผลลัพธ์: severityLevel + severityDescription | `identity/units/severity_units/severity/severity_model.py` |

---

## 2. `SeverityDescriptionModel` — 1 ข้อความ

ทั้ง 4 field เป็นภาษาไทย (engine เดิม; O7: Thai text อยู่นอก scope ของ analysis backend):

```python
# identity/units/severity_units/severity_description/severity_description_model.py:4-22
class SeverityDescriptionModel:
    description : str   # เช่น ปลากำลังเครียดสูง / เสี่ยงตาย
    detail : str        # อาการ/ผลต่อปลา เช่น "อาจส่งผลเสียต่อสุขภาพ..."
    appendDes : str | None  # สาเหตุเชิงเวลา (เติมทีหลังโดย evaluator)
    guidance : str      # best practice

    def __init__(self, *, des: str, detail: str, guid: str, append: str | None = None):
        self.description = des
        self.guidance = guid
        self.detail = detail
        self.appendDes = append
```

**การเติมข้อความเชิงเวลา** (`withAppend`) — คืน copy ไม่ mutate ชุดต้นฉบับ:

```python
# severity_description_model.py:24-31
def withAppend(self, text: str) -> "SeverityDescriptionModel":
    clone = copy.copy(self)
    clone.appendDes = f"{self.appendDes} {text}" if self.appendDes else text
    return clone
```

**ผลรวมทั้ง 4 field** (มี method แต่ไม่มี caller ใน prod — เก็บไว้ให้ UI เรียก):

```python
# severity_description_model.py:33-34
def fullDescription(self) -> str:
    return f"description : {self.description} {self.detail} {self.appendDes or ''} \n guidance : {self.guidance}"
```

---

## 3. `SeverityDesSetModel` — ชุด 11 ชิ้น

แต่ละ parameter มีชุด 11 `SeverityDescriptionModel` แบ่งตาม zone:

| slot | ใช้เมื่อ |
|---|---|
| `pureOptimal` | zone Optimal ปกติ (ไม่มี Recovery Hold) |
| `needRocoveryEleveted` | Recovery Hold หลังเหตุการณ์ ElevatedRisk |
| `needRocoveryCritical` | Recovery Hold หลังเหตุการณ์ Critical |
| `pureStress` | zone Stress ปกติ |
| `continuousStressExceeded` | Stress ต่อเนื่องเกินเกณฑ์ |
| `cumStressExceeded` | Stress สะสม 24 ชม. เกินเกณฑ์ |
| `pureHighRisk` | zone HighRisk ปกติ |
| `continuousHighRiskExceeded` | HighRisk ต่อเนื่องเกินเกณฑ์ → Critical |
| `cumHighRiskExceeded` | HighRisk สะสม 24 ชม. เกินเกณฑ์ → Critical |
| `pureCritical` | zone Critical ทันที |
| `episodeExceeded` | เข้า HighRisk ซ้ำ ≥ recurrenceEpisode24H |

**+ `abnormalLabel`** — วลีสำหรับ evaluator ต่อท้ายข้อความเชิงเวลา (default `"ค่าผิดปกติ"`):

```python
# severity_des_set_model.py:33-35
# วลีที่ใช้ประกอบข้อความเชิงเวลาที่ evaluator สร้าง เช่น "DO ต่ำ", "NH₃ สูง", "pH สูง"
# (แทนคำว่า "ต่ำ" ที่เคย hardcode ไว้ใน evaluator ซึ่งผิดสำหรับ NH3 และฝั่ง high)
abnormalLabel: str = "ค่าผิดปกติ"
```

**`forDirection()`**: Level parameter คืนตัวเองไม่ว่า direction เป็นอะไร:

```python
# severity_des_set_model.py:55-57
def forDirection(self, direction: ThresholdDirection | None = None) -> "SeverityDesSetModel":
    """Level parameter มีชุดเดียว -> คืนตัวเองไม่ว่า direction จะเป็นอะไร"""
    return self
```

**`RangeSeverityDesSet`** — คู่ low/high ของ `SeverityDesSetModel`:

```python
# severity_des_set_model.py:60-67
class RangeSeverityDesSet(DirectionalPair[SeverityDesSetModel]):
    """Range parameter (pH, Temperature): ชุดข้อความแยกฝั่ง low / high"""

    @property
    def pureOptimal(self) -> SeverityDescriptionModel:
        # Optimal ไม่มีทิศทาง จึงใช้ pureOptimal ของฝั่ง low เป็นตัวแทน
        # (ควรเขียนข้อความ pureOptimal ของสองฝั่งให้เหมือนกัน)
        return self.low.pureOptimal
```

`forDirection()` รับมาจาก `DirectionalPair` (ที่ `threshold_direction.py:23-32`):

```python
def forDirection(self, direction: ThresholdDirection | None) -> T:
    match direction:
        case ThresholdDirection.Low:
            return self.low
        case ThresholdDirection.High:
            return self.high
        case _:
            raise ValueError("Range parameter ต้องระบุ direction (Low/High) แต่ได้รับ None ...")
```

---

## 4. ผู้สร้างข้อความ — 6 provider files

| Parameter | Type | ไฟล์ | โครงสร้าง | abnormalLabel |
|---|---|---|---|---|
| DO | Level | `nile_parameter_severity/DO/nile_DO_severity.py` | duplicate 11 entries inline | `"DO ต่ำ"` (ตั้งเอง) |
| NH3 | Level | `.../NH3/nile_NH3_severity.py` | duplicate (copy จาก DO) | ไม่ได้ตั้ง (default) |
| NO2_N | Level | `.../NO2_N/nile_NO2_N_severity.py` | duplicate (copy จาก DO) | ไม่ได้ตั้ง |
| salinity | Level | `.../salinity/nile_salinity_severity.py` | duplicate (copy จาก DO) | ไม่ได้ตั้ง |
| pH | Range | `.../pH/nile_pH_severity.py` | factory `_pHSideSet(label, detail, care)` ×2 | per-side = label |
| Temperature | Range | `.../tempearture/nile_tem_severity.py` | factory `_temperatureSideSet(...)` ×2 | per-side = label |

### Level (DO) — ตัวอย่าง duplicate ทั้งชุด

```python
# nile_DO_severity.py:10-88 (ตัดบางส่วน)
def DO_SeverityDesSet() -> SeverityDesSetModel:
    return SeverityDesSetModel(
        abnormalLabel = "DO ต่ำ",
        pureOptimal = SeverityDescriptionModel(
            des = "ปลาดูในระดับ DO ในเหมาะสม",
            detail= "ดีต่อการเจริญเติบโตมาก",
            guid = "ระวังและดูแลตามปกติ",
            append= None
        ),
        pureStress = SeverityDescriptionModel(
            des = "ปลเครียดเล็กน้อย",          # typo: ขาด "า"
            detail= "อาจเป็นส่งผลเสียต่อสุขภาพหากอยู่นานกว่านี้",
            guid = "ระวังและดูแลให้ DO กลับมาอยู่ในระดับที่เหมาะสม",
        ),
        # ... ต่อครบ 11 entries
    )
```

### Range (pH) — factory 3 params ต่อฝั่ง

```python
# nile_pH_severity.py:19-27
def _pHSideSet(*, label: str, detail: str, care: str) -> SeverityDesSetModel:
    """
    สร้างชุดข้อความ 1 ฝั่ง ใช้ factory เพื่อไม่ต้องเขียนซ้ำ 11 รายการต่อฝั่ง
    - label  : วลีที่ evaluator ใช้ต่อท้ายข้อความเชิงเวลา เช่น "อุณหภูมิต่ำ"
    - detail : ผลต่อปลาของฝั่งนั้น
    - care   : คำแนะนำเฉพาะฝั่ง
    """
    return SeverityDesSetModel(
        abnormalLabel = label,
        pureOptimal = SeverityDescriptionModel( des = "อุณหภูมิน้ำอยู่ในช่วงเหมาะสม", ... ),
        pureStress = SeverityDescriptionModel(
            des = f"{label}กว่าช่วงเหมาะสมเล็กน้อย ปลาเริ่มเครียด",
            detail = detail,
            guid = care,
        ),
        # ... ต่อครบ 11 entries
    )

# nile_pH_severity.py:97-109
def pH_SeverityDesSet() -> RangeSeverityDesSet:
    return RangeSeverityDesSet(
        low = _pHSideSet(
            label = "pH ต่ำ",
            detail = "pH ต่ำกว่าช่วงเหมาะสม",   # TODO: ให้ผู้เชี่ยวชาญเติมผลต่อปลา
            care = "ควรเฝ้าระวังเสถียรภาพของน้ำและสุขภาพปลา",
        ),
        high = _pHSideSet(
            label = "pH สูง",
            detail = "pH สูงกว่าช่วงเหมาะสม",
            care = "ควรเฝ้าระวัง NH₃ ที่อาจเป็นพิษมากขึ้น",
        ),
    )
```

**หมายเหตุ Range:** `detail`/`care` คนละค่าตามฝั่งอยู่แล้ว แต่ `des` ของ recovery/pureOptimal ยัง hardcode "อุณหภูมิ" ในฝั่ง pH (factory body copy จาก temperature) — ดู section 6

---

## 5. ผู้ใช้ข้อความ — `SeverityEvaluator`

Evaluator เลือก slot ตามสถานการณ์ แล้ว `withAppend()` ข้อความเชิงเวลา (ยังเป็น Thai):

```python
# severity_evaluator.py:135-153 (ส่วน Stress)
continuousText = (
    f"{label}ต่อเนื่องเกิน {MinuteToHours(limitContinuous)} ชม. แล้ว "
    f"ปัจจุบัน {MinuteToHours(metrics.continuousMinute)} ชม."
)
...
return SeverityModel(
    severityLevel=SeverityLevelType.Stress,
    severityDes=des.pureStress.withAppend(
        f"{label}มาแล้ว {MinuteToHours(metrics.continuousMinute)} ชม. "
        f"หากต่อเนื่องจนครบ {MinuteToHours(limitContinuous)} ชม. จะอันตรายขึ้น"
    ),
)
```

Recovery Hold (severity_evaluator.py:95-100):

```python
return SeverityModel(
    severityLevel=SeverityLevelType.Stress,   # แสดงเป็น Stress (Recovery Hold)
    severityDes=base.withAppend(
        f"เกิดเวลาประมาณ {event.dateTime:%d/%m/%Y %H:%M} เหลืออีก {MinuteToHours(remainingMinute)} ชม."
    ),
)
```

ลำดับตัดสิน: Critical → Optimal(+Recovery Hold) → Stress/HighRisk (ตาม documented ลำดับ)

---

## 6. ปัญหาที่รู้แล้ว (Known Issues)

| # | ปัญหา | ที่ |
|---|---|---|
| 1 | **Thai ทั้งหมด** — engine เดิมยังไม่ได้แปล English (O7: out of scope) | ทุก provider |
| 2 | **Copy-paste bug** — NH3/NO2_N/salinity text อ้าง "DO" ทุก field (เช่น `"ปลาดูในระดับ DO ในเหมาะสม"`) | `nile_NH3_severity.py`, `nile_NO2_N_severity.py`, `nile_salinity_severity.py` |
| 3 | **`abnormalLabel` ไม่ได้ตั้ง** — NH3/NO2/salinity ใช้ default `"ค่าผิดปกติ"` | เดิม |
| 4 | **Typos ในข้อความ** — `"ปลเครียดเล็กน้อย"` (ขาด า), `"ปลาสะบาย"` (สะบาย), `"ค้องการ"` (ต้องการ), `"ตํ่า"` (ต่ำ), `"DO ในเหมาะสม"` | DO/NH3/NO2/salinity |
| 5 | **Typos ในชื่อ field** — `needRocoveryEleveted` (Rocovery/Eleveted), `HightRiskCountMinute` | `severity_des_set_model.py`, `severity_escalation_policy.py` |
| 6 | **pH factory body ยัง hardcode "อุณหภูมิ"** — `pureOptimal.des = "อุณหภูมิน้ำอยู่ในช่วงเหมาะสม"`, recovery guid `"รักษาอุณหภูมิ..."` | `nile_pH_severity.py:31-44` |
| 7 | **ข้อความซ้ำกัน** — 4 entries (contHigh/cumHigh/pureCritical/episode) ใช้ text เดียวกันทั้งหมด | ทุก Level provider |
| 8 | **ไม่มี consumer ใน prod** — `fullDescription()` ไม่มี caller; `SeverityReportView` ไม่ carrying text; Phase 6 สร้าง English จาก scratch | — |

---

## 7. สถานะใน pipeline ปัจจุบัน

```
SeverityEvaluator ──> SeverityModel.severityDescription  ──> AnalysisReportModel.severity
                                                                        │
                                                          ┌─────────────┴──────────────┐
                                                          ▼                            ▼
                                            toView() ตัดทิ้ง (severity_view.py)    ไม่มีใน ChangeSet
                                            แสดงแค่ zone/severity/value            ไม่ส่งออกไปไหน
```

- **เขียน:** เฉพาะ evaluator + 6 providers
- **อ่าน:** ไม่มีใน production โค้ด (มีแค่ `test_range_severity.py` assert `.description`/`.appendDes`)
- **ส่งออก:** ไม่ได้ — `SeverityReportView` (6 fields) ไม่รวม text; `ChangeSet` ไม่ carry text
- **English:** `identity/text/` (Phase 6) สร้างจาก Cause/Prediction/Recommendation เท่านั้น ไม่ mapping ไป severity descriptions

---

## 8. ถ้าจะ refactor ต่อ (ยังไม่ทำ)

- **แปล English:** ต้องเลือกว่าจะแทน field เดิม หรือเพิ่ม field ใหม่; ต้องแก้ 6 providers + tests
- **แก้ copy-paste:** ให้ NH3/NO2/salinity พูดถึง parameter ตัวเอง + ตั้ง `abnormalLabel`
- **Range per-side:** pH ควรแยก `pureOptimal`/recovery ตามฝั่ง (ตอนนี้ใช้ของ low เป็นตัวแทน)
- **Deduplicate:** Level providers ใช้ factory เดียวกับ Range (เหลือ `label/detail/care` ต่อ parameter)
- **เชื่อม text กับ UI:** เพิ่ม field ใน `SeverityReportView` หรือให้ adapter persist `fullDescription()`
