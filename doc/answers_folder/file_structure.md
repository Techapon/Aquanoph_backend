# Aquanoph Backend — File Structure

## Overview

ระบบ backend สำหรับวิเคราะห์คุณภาพน้ำในบ่อเลี้ยงสัตว์น้ำ โดยรับค่าพารามิเตอร์น้ำ (DO, pH, Temperature, NH3, NO2-N, Salinity) แล้วประเมิน **Threshold** และ **Severity** ของแต่ละพารามิเตอร์ พร้อมบริบทจากประวัติข้อมูลก่อนหน้า

---

## Directory Tree

```
Aquanoph_backend/
├── main.py                          # Entry point (ปัจจุบันว่างอยู่)
│
├── identity/                        # Domain core — โมเดล, กฎ, และข้อมูล identity
│   │
│   ├── animals/                     # สัตว์น้ำแต่ละชนิด
│   │   ├── animal_model.py          # Abstract base class `AquaticAnimal`
│   │   │                            #   กำหนด interface: Threshold, EscalationPolicy,
│   │   │                            #   SeverityDesSet สำหรับทุกพารามิเตอร์
│   │   │
│   │   ├── nile_tilapia/            # ปลานิล (Nile Tilapia)
│   │   │   ├── nile_model.py        # `NileTilapiaModel(AquaticAnimal)` — implement
│   │   │   │                        #   ทุก abstract method โดย delegate ไปที่ไฟล์ย่อย
│   │   │   │
│   │   │   ├── nile_parameter_severity/     # Severity config แยกรายพารามิเตอร์
│   │   │   │   ├── DO/
│   │   │   │   │   └── nile_DO_severity.py     # DO_EscalationPolicy, DO_SeverityDesSet
│   │   │   │   ├── NH3/
│   │   │   │   │   └── nile_NH3_severity.py    # NH3_EscalationPolicy, NH3_SeverityDesSet
│   │   │   │   ├── NO2_N/
│   │   │   │   │   └── nile_NO2_N_severity.py  # NO2_N_EscalationPolicy, NO2_N_SeverityDesSet
│   │   │   │   ├── pH/
│   │   │   │   │   └── nile_pH_severity.py     # pH_EscalationPolicy, pH_SeverityDesSet
│   │   │   │   ├── salinity/
│   │   │   │   │   └── nile_salinity_severity.py  # salinity_EscalationPolicy, salinity_SeverityDesSet
│   │   │   │   └── tempearture/
│   │   │   │       └── nile_tem_severity.py    # temperature_EscalationPolicy, temperature_SeverityDesSet
│   │   │   │
│   │   │   └── nile_parameter_threshold/    # Threshold config แยกรายพารามิเตอร์
│   │   │       ├── DO/
│   │   │       │   └── nile_DO_threshold.py    # DO_threshold()
│   │   │       ├── NH3/
│   │   │       │   └── nile_NH3_threshold.py   # NH3_threshold()
│   │   │       ├── NO2_N/
│   │   │       │   └── nile_NO2_N_threshold.py # NO2_N_threshold()
│   │   │       ├── pH/
│   │   │       │   └── nile_pH_threshold.py    # pH_threshold()
│   │   │       ├── salinity/
│   │   │       │   └── nile_salinity_threshold.py  # salinity_threshold()
│   │   │       └── tempearture/
│   │   │           └── nile_tem_threshold.py   # tem_threshold()
│   │   │
│   │   └── whiteleg_shrimp/         # กุ้งขาว (Whiteleg Shrimp) — โฟลเดอร์สำรองสำหรับอนาคต
│   │
│   ├── formats/                     # รูปแบบ output / report
│   │   └── analysis_report/
│   │       └── analysis_report_model.py     # `AnalysisReportModel`
│   │                                        #   เก็บ: dateTime, parameter, thresholdStatus,
│   │                                        #   thresholdDirection, severity (SeverityModel)
│   │
│   ├── parameters/                  # โมเดลและ enum ของพารามิเตอร์น้ำ
│   │   ├── pond_parameter_enum.py   # `PondParameters(Enum)`: DO, pH, tem, NH3, NO2_N, salinity
│   │   ├── pond_parameter_model.py  # `PondParametersModel` — orchestrate ทุกพารามิเตอร์พร้อมกัน
│   │   │                            # `PondParametersDeliveryModel` — DTO รับค่าปัจจุบันของทุก param
│   │   ├── pond_parameter_history_model.py  # `PondParametersHistoryModel` — เก็บ history list
│   │   │                                   #   ของ AnalysisReportModel แยกตามพารามิเตอร์
│   │   └── parameter_model.py       # `ParameterModel` — logic หลักของพารามิเตอร์เดี่ยว:
│   │                                #   checkParameterThreshold(), getCurrentSeverityLevel(),
│   │                                #   buildAnalysisReport()
│   │
│   └── units/                       # หน่วยและกฎพื้นฐาน (reusable)
│       │
│       ├── severity_units/          # ระบบประเมิน Severity
│       │   ├── severity/
│       │   │   └── severity_model.py            # `SeverityModel`: severityLevel + severityDescription
│       │   │
│       │   ├── severity_level/
│       │   │   └── severity_level_enum.py       # `SeverityLevelType(Enum)`:
│       │   │                                    #   Optimal | Stress | ElevatedRisk | Critical
│       │   │
│       │   ├── severity_description/
│       │   │   ├── severity_description_model.py    # `SeverityDescriptionModel`: description + guidance
│       │   │   └── severity_des_set_model.py        # `SeverityDesSetModel`, `RangeSeverityDesSet`,
│       │   │                                        #   `AnySeverityDesSet` — ชุด description ตาม
│       │   │                                        #   สถานการณ์ (pureOptimal, pureStress, ฯลฯ)
│       │   │
│       │   └── severity_elavuator/  # Engine ประเมิน Severity
│       │       ├── severity_evaluator.py        # `SeverityEvaluator()` — ฟังก์ชันหลัก:
│       │       │                                #   ตัดสิน Severity จาก threshold level + history
│       │       │                                #   รองรับทั้ง Level (direction=None) และ Range
│       │       ├── severity_escalation_policy.py # `EscalationPolicy` (dataclass): กำหนดเกณฑ์
│       │       │                                #   เวลาต่อเนื่อง / สะสม / recovery hold (นาที)
│       │       │                                #   `RangeEscalationPolicy`: policy แยก Low/High
│       │       │                                #   `AnyEscalationPolicy` (type alias)
│       │       └── severity_helper.py           # ฟังก์ชันคำนวณ timeline, metrics, episodes:
│       │                                        #   buildTimeline(), calZoneMetrics(),
│       │                                        #   countEpisodes(), findPendingRecovery()
│       │
│       └── threshold_units/         # ระบบ Threshold
│           ├── threshold/
│           │   ├── threshold_model.py           # `Threshold` (ABC), `LevelThreshold`,
│           │   │                                #   `RangeThreshold` — ตรวจค่าและคืน ThresholdLevelModel
│           │   ├── threshold_type_level_enum.py # `LevelType(Enum)`: eqaMoreThan | eqaLessThan
│           │   └── value_range.py               # `Range`, `RangeType` — นิยามช่วงค่า (min, max)
│           │
│           └── threshold_level/
│               ├── threshold_level.py           # `ThresholdLevelType(Enum)`:
│               │                                #   Optimal | Stress | HighRisk | Critical
│               ├── threshold_level_model.py     # `ThresholdLevelModel`: level + direction (optional)
│               └── threshold_direction.py       # `ThresholdDirection(Enum)`: Low | High
│                                                # `DirectionalPair[T]` — Generic pair (low/high)
│
├── services/                        # Utility / helper services
│   ├── dif_minute.py                # `calDiffMinute(date1, date2)` — คำนวณผลต่างเวลาเป็นนาที
│   └── minute_to_hours.py           # `MinuteToHours(minute)` — แปลงนาทีเป็น string ชั่วโมง
│
└── tests/                           # Unit tests
    └── test_range_severity.py       # ทดสอบ severity assessment สำหรับ Range parameter
```

---

## Architecture Flow

```
Input (PondParametersDeliveryModel)
    │
    ▼
AquaticAnimal (e.g. NileTilapiaModel)
    │  กำหนด Threshold, EscalationPolicy, SeverityDesSet ต่อ species
    │
    ▼
PondParametersModel
    │  สร้าง ParameterModel ทุกตัว (DO, pH, tem, NH3, NO2-N, Salinity)
    │
    ▼
ParameterModel.buildAnalysisReport()
    │
    ├──► Threshold.checkThreshold()
    │        └── คืน ThresholdLevelModel (level + direction)
    │
    └──► SeverityEvaluator()
             ├── รับ ThresholdLevelModel + History (list[AnalysisReportModel])
             ├── ใช้ EscalationPolicy (เวลาต่อเนื่อง/สะสม/recovery)
             └── คืน SeverityModel (severityLevel + severityDescription)
    │
    ▼
AnalysisReportModel  ←  บันทึกเป็น History รอบถัดไป
```

---

## Key Concepts

| Concept | Class/File | ความหมาย |
|---|---|---|
| **Threshold** | `threshold_model.py` | แบ่งโซน: Optimal / Stress / HighRisk / Critical |
| **LevelThreshold** | `threshold_model.py` | พารามิเตอร์ทางเดียว (DO, NH3, NO2-N, Salinity) — ไม่มี direction |
| **RangeThreshold** | `threshold_model.py` | พารามิเตอร์สองทาง (pH, Temperature) — มี direction Low/High |
| **SeverityLevelType** | `severity_level_enum.py` | Optimal → Stress → ElevatedRisk → Critical |
| **EscalationPolicy** | `severity_escalation_policy.py` | เกณฑ์เวลาเพื่อ escalate severity ขึ้น |
| **SeverityEvaluator** | `severity_evaluator.py` | engine ตัดสิน severity จาก threshold + history |
| **AnalysisReportModel** | `analysis_report_model.py` | snapshot ผลวิเคราะห์ 1 ครั้ง สำหรับบันทึกเป็นประวัติ |
| **PondParametersHistoryModel** | `pond_parameter_history_model.py` | รวม history ทุกพารามิเตอร์ใน pond |

---

## Parameters Supported

| Parameter | ชื่อ | หน่วย | Threshold Type |
|---|---|---|---|
| `DO` | Dissolved Oxygen | mg/L | Level (≥ optimal) |
| `pH` | pH | — | Range (low/high) |
| `tem` | Temperature | °C | Range (low/high) |
| `NH3` | Ammonia | mg/L | Level (≤ optimal) |
| `NO2_N` | Nitrite-Nitrogen | mg/L | Level (≤ optimal) |
| `salinity` | Salinity | ppt | Level |
