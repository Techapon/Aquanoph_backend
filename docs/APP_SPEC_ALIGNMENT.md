# APP_SPEC_ALIGNMENT — app_spec_v0.4 vs backend ปัจจุบัน

> เอกสารนี้อธิบาย **ความหมายของ table/column ทุกตัว + ความสัมพันธ์ + contract ที่แอปใช้ + backend flow**
> เพื่อให้แอปอ่าน/เขียนถูกโดยไม่ต้องอ่านโค้ด backend ทั้งหมด
> อ้างอิง source จริง (migrations `001`–`010`, Python `identity/`, `services/`, `db/`) ณ commit ปัจจุบัน
> ไม่ได้แก้โค้ดใดๆ — แค่สรุป facts

---

## 1. แผนผังความสัมพันธ์ตาราง (Relationships)

```
profiles (1 user = auth user)
  │
  ├─< ponds ──────────────────────────── 1 บ่อต่อ user (UI จำกัด, schema รองรับหลายบ่อ)
  │   │  ผูกอุปกรณ์ผ่าน device_id ──> devices (ตรวจสอบว่ามีอยู่จริง)
  │   │
  │   ├─< sensor_readings        readings จาก buoy/simulator ผูก device_id
  │   ├─< severity_reports       1 reading สร้าง 1 report (insert-only, ไม่แก้ไขได้)
  │   ├─< pond_states            snapshot ของบ่อเมื่อ weight/count เปลี่ยน (insert-only)
  │   ├─< pond_analysis_state    cursor ของ backend (1:1 ต่อบ่อ) ว่าอ่านถึงเมื่อไร
  │   ├─< diagnostic_reports     บทวิเคราะห์สาเหตุ (episodes + causes)
  │   │       ↑
  │   │   recommendation_sources โยง rec ไปยัง diagnostic/prediction/detector
  │   ├─< predictions            การคาดการณ์ (1 active ต่อ rule ต่อบ่อ)
  │   ├─< recommendations        คำแนะนำ (dedupe ป้องกันซ้ำ)
  │   │       ↑
  │   │   activity created by apply โยงผ่าน source_rec_id
  │   ├─< activities              กิจกรรมบ่อ (checklist) ──< activity_series (repeat 7 วัน)
  │   ├─< notifications           outbox แจ้งเตือน (push/feed)
  │   ├─< parameter_forecasts    พยากรณ์ค่า kNN ล่วงหน้า (1 แถวต่อ parameter, เขียนทับทุก run)
  │   └─< analysis_jobs/runs      งานวิเคราะห์ที่ trigger สร้าง (backend worker ทำ)
  └─< push_tokens                 device tokens สำหรับ push
```

**อ่านตาม flow:**
reading เข้า `sensor_readings` → enqueue job → backend โหลด snapshot → คำนวณ → สร้าง `severity_reports` + `diagnostic_reports` + `predictions` + `recommendations` + `notifications` + `parameter_forecasts` ลง DB ผ่าน ChangeSet/adapter → app subscribe realtime อ่านผล

---

## 2. ตารางและคอลัมน์ (ความหมาย + หน้าที่)

### 2.1 `profiles` — ข้อมูลผู้ใช้

มาจาก Supabase Auth (`auth.users`) สร้างผ่าน trigger ตอนสมัคร

| column | ความหมาย / หน้าที่ |
|---|---|
| `user_id` | PK, อ้าง auth.users — ระบุตัวตน |
| `username` | ชื่อแสดง (ห้ามซ้ำ, ไม่แยกตัวพิมพ์) |
| `created_at` | เวลาสมัคร |

**ความสัมพันธ์:** `ponds.user_id` → 1 user มีหลายบ่อ (RLS ให้เห็นเฉพาะของตัวเอง)

---

### 2.2 `devices` — ทะเบียนอุปกรณ์ทุ่น

| column | ความหมาย / หน้าที่ |
|---|---|
| `device_id` | PK (text) — รหัสทุ่น sensor ที่ user กรอกตอนสร้างบ่อ (บังคับ, ห้ามซ้ำข้ามบ่อ) |
| `created_at` | เวลาลงทะเบียน |

**ความสัมพันธ์:** `ponds.device_id` → ตรวจว่าทุ่นที่กรอกมีอยู่จริง; `sensor_readings.device_id` → readings ผูกอุปกรณ์ไม่ใช่ผูกบ่อโดยตรง

---

### 2.3 `ponds` — ข้อมูลบ่อ (ตารางหลักของ app)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK (uuid) — รหัสบ่อ ใช้อ้างทุกตารางอื่น |
| `user_id` | FK profiles — เจ้าของ; RLS ใช้กรองข้อมูล |
| `name` | ชื่อบ่อ (แก้ได้จาก app) |
| `area_m2` | พื้นที่ผิวน้ำ ตร.ม. (แก้ไม่ได้; คำนวณ volume/density) |
| `avg_depth_m` | ความลึกเฉลี่ย ม. (แก้ไม่ได้; คำนวณ volume/density) |
| `species` | ชนิดปลา (enum, default `nile_tilapia`) — engine ใช้เลือก threshold ของสปีชีส์ |
| `stocking_count` | จำนวนปลา (แก้ได้; แก้แล้ว trigger `pondEdit` → คำนวณ biomass ใหม่ + รันวิเคราะห์ใหม่) |
| `avg_weight_g` | น้ำหนักเฉลี่ย g (แก้ได้; แก้แล้ว trigger `pondEdit` — DO threshold คำนวณจาก biomass จึงต้องวิเคราะห์ใหม่) |
| `stocking_date` | วันปล่อย (แก้ไม่ได้; ใช้คำนวณ `analysis_start_at`) |
| `device_id` | FK devices — ผูกทุ่น (แก้ไม่ได้) |
| `timezone` | IANA timezone ของบ่อ (แก้ไม่ได้) — **backend ใช้ timezone นี้ใน logic ช่วงเวลาทั้งหมด** (night window, local date) |
| `volume_m3` | generated: `area_m2 × avg_depth_m` — ปริมาตร คิวบิกเมตร |
| `biomass_kg` | generated: `stocking_count × avg_weight_g / 1000` — มวลปลา kg; **engine ใช้คำนวณ mealPct (%) และ DO threshold** |
| `density_kg_m3` | generated: `biomass / volume` — ความหนาแน่น kg/m³ (ส่งเข้า engine) |
| `analysis_start_at` | trigger ตั้ง = max(midnight local ของ stocking_date, created_at) — readings ก่อนเวลานี้ถูกข้าม (N2) |
| `created_at` / `updated_at` | เวลาสร้าง/แก้ไขล่าสุด (auto) |

**ความสัมพันธ์:** เป็น hub — ทุกตาราง analysis อ้าง `ponds.id` (FK); app แก้ได้เฉพาะ `name`, `avg_weight_g`, `stocking_count` (column grant + guard trigger บล็อกคอลัมน์อื่น)

---

### 2.4 `pond_states` — snapshot ของบ่อเมื่อค่าเปลี่ยน (insert-only)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK uuid (auto) |
| `pond_id` | FK ponds — บ่อที่เกี่ยวข้อง |
| `effective_from` | เวลาที่ค่าชุดนี้เริ่มมีผล |
| `avg_weight_g`, `fish_count` | ค่า weight/count ณ เวลานั้น (เก่าแก้ไม่ได้; ค่าปัจจุบันอยู่ใน `ponds`) |
| `biomass_kg`, `density_kg_m3`, `volume_m3` | ค่าที่คำนวณแล้ว ณ เวลานั้น |
| `timezone` | timezone ของบ่อ ณ เวลานั้น |

**ความหมาย:** บันทึกประวัติค่าบ่อแบบ insert-only (ห้าม update/delete) เพื่อให้ `severity_reports` อ้าง FK ได้ว่า report นั้นถูกสร้างจากค่าบ่อชุดไหน (snapshot ตาม spec §3.9)

**ความสัมพันธ์:** `severity_reports.pond_state_id` FK → ตารางนี้ (1 บ่อ มีหลาย state; 1 state มีหลาย report)

---

### 2.5 `pond_analysis_state` — cursor ของ backend (1:1 ต่อบ่อ)

| column | ความหมาย / หน้าที่ |
|---|---|
| `pond_id` | PK — 1 บ่อ = 1 แถว |
| `last_reading_at` | เวลา reading ล่าสุดที่ backend อ่าน/ประมวลผลแล้ว — ใช้**ทำเครื่องหมาย `late`** ให้ reading ที่เข้ามาผิดลำดับ (measured_at <= ค่านี้) |
| `last_run_at` | เวลารัน analysis ล่าสุด |
| `engine_version` | เวอร์ชัน engine ที่ใช้รันล่าสุด (debug/migration) |

**ความสัมพันธ์:** ไม่มี FK ออก — เป็น internal cursor ให้ backend กันอ่านซ้ำ/ข้าม reading

---

### 2.6 `sensor_readings` — raw readings จากทุ่น

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK bigint (auto) |
| `device_id` | FK devices — อุปกรณ์ที่ส่ง (ไม่ใช่บ่อ) |
| `measured_at` | เวลาวัด (UTC) — ใช้เรียงลำดับและทำ window |
| `received_at` | เวลารับเข้าระบบ (default now) — ใช้วัด latency ย้อนหลัง |
| `late` | boolean — true เมื่อ measured_at เก่ากว่า `last_reading_at` (ผิดลำดับ); **backend ข้าม reading พวกนี้** (`WHERE late = false`) |
| `"DO"`, `"pH"`, `"NH3"`, `"NO2"`, `"temperature"`, `"salinity"` | ค่า 6 parameter หน่วย SI; NaN ห้ามเข้า (constraint) |

**ความหมาย:** แถว = 1 ครั้งการวัดจากทุ่น 1 ตัว; ไม่ผูกบ่อโดยตรง แต่ผูกผ่าน `device_id` → `ponds.device_id`

**ความสัมพันธ์:** trigger AFTER INSERT → `enqueue_analysis(pond_id, 'reading')` เมื่อไม่ late และ >= `analysis_start_at`

---

### 2.7 `severity_reports` — ผลประเมิน severity ต่อ parameter ต่อครั้ง (insert-only)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK bigint (auto) |
| `pond_id` | FK ponds |
| `pond_state_id` | FK pond_states — ชี้ snapshot บ่อที่ใช้ตอนคำนวณ |
| `parameter` | enum (DO/pH/NH3/NO2/temperature/salinity) — parameter ตัวนี้ |
| `measured_at` | เวลาวัด (UTC) — unique คู่กับ pond+parameter (idempotency) |
| `value` | ค่าที่อ่านได้ (F-01: report เก็บ measured value) |
| `zone` | enum optimal/stress/high_risk/critical — โซน threshold ที่ค่าตกอยู่ |
| `direction` | enum low/high/null — ทิศทางที่ผิด (Range เท่านั้น; Level = null) |
| `severity` | enum optimal/stress/elevated_risk/critical — ระดับความรุนแรง (engine ตัดสินจาก zone + ระยะเวลา/การสะสม) |
| `recovering` | generated boolean: zone=optimal AND severity=stress — ป้าย "Recovering" (Recovery Hold: ค่าปกติแล้วแต่ยังกักไว้เพราะเหตุการณ์ก่อนหน้า) |
| `description` | ข้อความสั้น "สถานการณ์ตอนนี้" (English, จาก template): เช่น "DO is slightly outside the suitable range" |
| `detail` | อาการ/ผลต่อปลา (English, parameter-specific): เช่น "Nile tilapia may begin to experience stress..." |
| `append_des` | ข้อความเชิงเวลา (English, สร้างตอน runtime): เช่น "low DO has been continuous beyond 8 h. Now 8.5 h." |
| `guidance` | คำแนะนำเกษตรกร (English): เช่น "Check aeration equipment..." |
| `engine_version` | engine ที่สร้างแถว |
| `reading_id` | FK sensor_readings — ชี้ raw reading ต้นทาง (nullable) |
| `threshold` | **jsonb — threshold ที่ใช้ตัดสินแถวนี้** (เพิ่มใน migration 012): Level = `{kind:"level", levelType:"eqaMoreThan"|"eqaLessThan", optimal, stress, highRisk, critical}` เช่น DO `optimal:5.8` แปลว่า "Optimal ≥ 5.8 mg/L ตอนนั้น"; Range = `{kind:"range", optimal:{min,max}, stress:{...}, highRisk:{...}, critical:{...}}` (null ใน min/max = ขอบเปิด เช่น temperature critical) · **null** = แถวก่อน migration 012 |

**ความหมาย:** 1 แถว = 1 การประเมิน severity ของ 1 parameter ณ เวลาหนึ่ง. 4 คอลัมน์ text (`description/detail/append_des/guidance`) คือ **สิ่งที่ app แสดงบนการ์ด parameter**

**ความสัมพันธ์:** มี trigger AFTER INSERT → ถ้าเปลี่ยนเป็น critical ครั้งแรก (ไม่ค้าง) สร้าง `notifications` แถว kind=`severityCritical` ให้ app แสดง/push

---

### 2.8 `diagnostic_reports` — บทวิเคราะห์ "เพราะอะไร" (episodes + causes)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK (text) — deterministic: `diag:{pond}:{param}:{dir|-}:{onset iso}` (รันซ้ำไม่สร้างซ้ำ) |
| `pond_id` | FK ponds |
| `parameter` | parameter ที่มี episode |
| `direction` | ทิศทางของ episode (Range) / null (Level) |
| `onset_at` | เวลาเริ่ม episode — ครั้งแรกที่ zone ไม่ใช่ Optimal |
| `end_at` | เวลาจบ episode (Optimal reading แรก); null = ยัง open |
| `status` | open/closed — ยังดำเนินอยู่หรือปิดแล้ว |
| `peak_severity` | severity สูงสุดระหว่าง episode |
| `last_severity` | severity ของ reading สุดท้ายใน episode |
| `causes` | jsonb `[{ruleId, facts}]` — สาเหตุที่ rule engine สรุป เช่น `DO_C_FEED` + ข้อเท็จจริง (feed time, kg, mealPct) |
| `no_clear_cause` | bool — true ถ้าไม่พบสาเหตุชัด (app แสดง fallback text) |
| `pond_snapshot` | jsonb — ข้อมูลบ่อ ณ ตอนสร้าง report (น้ำหนัก, count, biomass, timezone) เผื่อคำนวณซ้ำ |
| `revised_at` | เวลาที่ causes ถูกคำนวณใหม่ (activity edit); null = ไม่เคยแก้ |
| `text` | jsonb cache จาก `renderDiagnostic` (title, causes[], footer, revisedLabel) — app อ่านได้เลยไม่ต้อง render เอง |

**ความหมาย:** 1 แถว = 1 episode ของ 1 parameter. ใช้แสดงในหน้า Analysis/parameter detail: "Why this may have happened" + รายการ cause

**ความสัมพันธ์:** `recommendation_sources.diagnostic_id` → ชี้ rec ที่มาจาก episode นี้ (Phase 5 ใช้ปิด rec เมื่อ episode ปิด)

---

### 2.9 `predictions` — การคาดการณ์ล่วงหน้า

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK (text) — deterministic: `pred:{pond}:{rule}:{scope|-}:{createdAt iso}` |
| `pond_id` | FK ponds |
| `rule_id` | กฎที่ยิง: `PRED_DO_NIGHT` / `PRED_DO_REPEAT` / `PRED_NH3_RISE` |
| `scope` | ขอบเขต เช่น nightDate `2026-10-25` (คืนนี้) / null (NH3 ไม่มี scope) |
| `parameter` | DO หรือ NH3 |
| `expected_zone` | โซนที่คาดว่าจะตก (high_risk) |
| `risk_start` / `risk_end` | ช่วงเวลาเสี่ยง (UTC) |
| `met` | text[] — condition ids ที่เป็นจริง เช่น `{C1,C2,C3}` (ใช้แสดง "2/3 conditions") |
| `status` | active/ended — ยังคาดการณ์อยู่หรือจบแล้ว |
| `end_reason` | mitigated (มีการแก้แล้ว) / conditions_gone (เงื่อนไขหาย) / window_over (หมดช่วงเวลา) |
| `evidence` | jsonb หลักฐานทั้งหมด รวม `conditions: {C1: true, C2: false, ...}` สำหรับแสดงว่าเงื่อนไขไหนผ่าน |
| `pond_snapshot` | jsonb snapshot ตอนสร้าง |
| `revised_at` | เวลาปรับปรุงล่าสุด |
| `text` | jsonb cache จาก `renderPrediction` (headline, conditions[], footer) |

**ความหมาย:** 1 แถว = 1 การคาดการณ์. unique index `(pond_id, rule_id) WHERE status='active'` — **มีได้แค่ 1 active ต่อ rule ต่อบ่อ**

**ความสัมพันธ์:** `recommendation_sources.prediction_id` → โยง rec ที่มาจาก prediction (ปิด rec เมื่อ prediction ended); `notifications` kind=`predictionEnded` target_id = แถวนี้

---

### 2.10 `recommendations` — คำแนะนำ (AERATE / WATER_CHANGE / ADD_ALKALINITY)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK (text) — deterministic: `rec:{pond}:{dedupeKey}:{createdAt iso}` |
| `pond_id` | FK ponds |
| `entry_id` | ประเภทคำแนะนำ: `AERATE` (เปิดเครื่องตีน้ำ) / `WATER_CHANGE` (เปลี่ยนน้ำ) / `ADD_ALKALINITY` (เติมด่าง) |
| `dedupe_key` | กุญแจกันซ้ำ เช่น `AERATE:2026-10-25` — ไม่สร้าง rec ใหม่ถ้ามี pending/snoozed ที่ key เดียวกัน |
| `urgency` | urgent (มีเวลาต้องทำ ห้าม snooze) / non_urgent (เลือกเวลาเอง, snooze ได้) |
| `apply_mode` | fixed (เวลากำหนดตายตัว) / pick_window (user เลือกในช่วง) — คู่กับ urgency |
| `valid_from` | เริ่มใช้ได้ตั้งแต่เมื่อไร (มัก = เวลาสร้าง) |
| `valid_until` | หมดอายุเมื่อไร — app แสดงนับถอยหลัง; เกินนี้ = expired |
| `title` | หัวข้อที่ app แสดง เช่น "Run aeration tonight: DO may drop too low" (render เก็บใน DB) |
| `reason` | เหตุผล/ความเสี่ยงที่อธิบายให้เกษตรกร (อ้างค่าปัจจุบัน) |
| `based_on` | ข้อมูลที่อ้างอิง เช่น "Planned feeding 19:00 · no aeration planned 20:00–06:00" |
| `guidance` | text[] คำแนะนำขั้นตอน (3-4 ข้อ) |
| `proposed_activities` | jsonb กิจกรรมที่เสนอ `{type, startTime, endTime, quantityKg, fraction}` — app preview ก่อน apply |
| `plan_text` | บรรทัด "Plan:" จาก `renderPlan` (cache) |
| `status` | pending → applied / snoozed / dismissed / expired (state machine §4.2) |
| `expire_reason` | `no_longer_applies` (เงื่อนไขหาย) / `time_window_over` (หมดเวลา) — มีค่า ⇔ status=expired |
| `snooze_until` | เลื่อนถึงเมื่อไร — มีค่า ⇔ status=snoozed; urgent ห้าม snooze |
| `dismissed_at` / `dismiss_note` | เวลา/เหตุผลที่ user ปฏิเสธ (เฉพาะ dismissed; เขียนผ่าน Python API เท่านั้น ไม่ผ่าน ChangeSet) |
| `created_at` / `updated_at` | เวลาสร้าง/แก้ไข (auto trigger) |

**ความหมาย:** 1 แถว = 1 คำแนะนำที่แอปแสดงในแท็บ Today/Upcoming/History. ตัวแปรสำคัญต่อ app: `dedupe_key` (กันซ้ำ), `urgency+apply_mode` (รูปแบบการใช้งาน), `valid_until` (หมดอายุ), `status+reason` (state machine)

**ความสัมพันธ์:** มี unique index `(pond_id, dedupe_key) WHERE status IN (pending, snoozed)` — ระบบบังคับไม่สร้างซ้ำ; `recommendation_sources` (1:N) ชี้แหล่งที่มา; `activities.source_rec_id` → โยงกิจกรรมที่สร้างจากการ apply; `notifications` อ้าง `id` เมื่อ rec เปลี่ยนสถานะ

---

### 2.11 `recommendation_sources` — โยง rec กลับไปที่แหล่งที่มา

| column | ความหมาย / หน้าที่ |
|---|---|
| `rec_id` | FK recommendations — คำแนะนำ |
| `source_type` | `episode` / `prediction` / `detector` — แหล่งชนิดใด |
| `diagnostic_id` | FK diagnostic_reports (เมื่อ source_type=episode) |
| `prediction_id` | FK predictions (เมื่อ source_type=prediction) |
| `detector_code` | โค้ด detector เช่น `PH_SWING` (เมื่อ source_type=detector) |

**ความหมาย:** กติกา O3: rec ปิด (`no_longer_applies`) เมื่อ **ทุก** source ปิด; detector source ไม่เคยปิด (หมดด้วย valid_until เท่านั้น). App ไม่เขียนตารางนี้ — backend เท่านั้น

---

### 2.12 `activities` — กิจกรรมบ่อ (checklist)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK (text) — user สร้าง: uuid; backend สร้างตอน apply: `act:{recId}:{i}` |
| `pond_id` | FK ponds |
| `type` | feeding / aeration / alkalinity / lime / probiotic / water_change / other |
| `status` | pending (แผน) → done (ทำแล้ว) / skipped (ข้าม); `missed` คำนวณไม่เก็บ |
| `start_time` | เวลาเริ่ม (จุดเวลา หรือ ต้นช่วง aeration) (UTC) |
| `end_time` | หมดช่วง (บังคับเฉพาะ aeration, ต้อง > start_time) |
| `quantity_kg` | ปริมาณ kg (feeding/alkalinity/lime/probiotic) — ห้ามน้อยกว่า 0 |
| `fraction` | สัดส่วนน้ำที่เปลี่ยน 0–1 (บังคับเฉพาะ water_change: 1/4=0.25) |
| `source` | `user` (user สร้าง) / `recommendation` (apply สร้าง) |
| `source_rec_id` | FK recommendations — ชี้ rec ต้นทางเมื่อ source=recommendation (**ลบไม่ได้ ต้อง skip**) |
| `series_id` | FK activity_series — รายการจากชุด repeat รายวัน |
| `created_at` / `updated_at` | เวลาสร้าง/แก้ไข (auto) |

**ความหมาย:** 1 แถว = 1 งาน/แผน. ใช้ทั้งเป็นแผนและเป็นบันทึก (checklist). **Constraint สำคัญ:** aeration ห้ามซ้อนกัน (exclude GiST) และ guard trigger บังคับ retro window 4 วัน + ห้าย้อน status + คอลัมน์ immutable

**ความสัมพันธ์:** `source_rec_id` → recommendations; `series_id` → activity_series; trigger AFTER INSERT/UPDATE/DELETE → `enqueue_analysis('activityEvent', tFrom=min(startTime))` ให้ backend วิเคราะห์ใหม่

---

### 2.13 `activity_series` — ชุด repeat รายวัน

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK uuid |
| `pond_id` | FK ponds |
| `type` | ชนิดกิจกรรมที่ทำซ้ำ |
| `local_start_time` | เวลา (ใน timezone บ่อ) ที่ทำทุกวัน |
| `duration_minutes` | ระยะเวลา (aeration เท่านั้น) |
| `quantity_kg` / `fraction` | รายละเอียดที่ทำซ้ำ |
| `first_local_date` | เริ่มจากวันไหน |
| `ended_at` | จบชุดเมื่อไร (null = ยังทำซ้ำอยู่) |
| `generated_through` | สร้างรายการถึงวันไหนแล้ว (cron ต่ออายุถึง +7 วัน) |

**ความหมาย:** app สร้างผ่านสวิตช์ "ทำซ้ำทุกวัน" — ตารางนี้เก็บแบบแผน ส่วน `activities` คือรายการจริงที่ generate ล่วงหน้า 7 วัน (ชน aeration เดิมจะข้ามวันนั้น)

---

### 2.14 `notifications` — outbox แจ้งเตือน (feed + push)

| column | ความหมาย / หน้าที่ |
|---|---|
| `id` | PK bigint (auto) |
| `pond_id` | FK ponds |
| `user_id` | FK profiles — denormalized เพื่อให้ RLS กรองเร็ว |
| `kind` | `urgentRecCreated` / `recChanged` / `recExpired` / `recUnsnoozed` / `predictionEnded` / `activityReplaced` / `severityCritical` |
| `target_type` | `recommendation` / `prediction` / `activity` / `diagnostic` / `severity` — object ที่เกี่ยวข้อง |
| `target_id` | id ของ object นั้น (ใช้ app สร้างลิงก์ไปหน้านั้น) |
| `reason_key` | เหตุผลละเอียด เช่น `rec.changed.urgency_raised`, `rec.expired.no_longer_applies` — app ใช้เลือกข้อความ |
| `facts` | jsonb ข้อมูลเสริม (recId, entryId, tFrom, activityType...) |
| `text` | ข้อความ English ที่แสดง (cache จาก renderNotification หรือ format ของ DB trigger) |
| `push_eligible` | true ได้เฉพาะ 3 กรณี: severityCritical, urgentRecCreated, recChanged+urgency_raised (constraint บังคับ) |
| `pushed_at` | เวลาที่ push ส่งแล้ว (null = ยังไม่ส่ง; cron ทุกนาที retry) |
| `read_at` | เวลาที่ user อ่านแล้ว (app mark-read) |
| `created_at` | เวลาสร้าง (app เรียงตามนี้) |

**ความหมาย:** 1 แถว = 1 แจ้งเตือน. App subscribe Realtime ตารางนี้ → แสดง badge/feed; ถ้า push_eligible → Edge Function push-dispatch ส่งถึง device

**ความสัมพันธ์:** `target_id` ชี้กลับไปที่ rec/prediction/activity/severity report ที่เกี่ยวข้อง

---

### 2.15 `analysis_jobs` / `analysis_runs` — คิวและประวัติงานวิเคราะห์ (backend เท่านั้น)

| table | ความหมาย |
|---|---|
| `analysis_jobs` | คิวงาน: trigger สร้างแถว (reading/activityEvent/pondEdit/tick) → worker poll ประมวลผล 1 งานต่อครั้ง |
| `analysis_runs` | ประวัติการรัน (เวลาเร็ว/จบ, ผล ChangeSet, error) |

**ความหมายต่อ app:** app **ไม่เขียน/ไม่อ่านตรง** — รู้แค่ว่าผลวิเคราะห์อัปเดตแบบ async หลัง trigger. Webhook ยิง `/wake` เพื่อปลุก worker

---

### 2.16 `push_tokens` — device tokens สำหรับ push

| column | ความหมาย |
|---|---|
| `user_id` | FK profiles |
| `token` | FCM/APNs token (unique) |
| `platform` | `fcm` / `apns` |
| `last_seen_at` | เวลารอบสุดท้ายที่ app ยืนยัน token |

**ความหมาย:** app สมัคร/รีเฟรช token เอง; Edge Function `push-dispatch` อ่านตารางนี้ส่ง push

---

### 2.17 `parameter_forecasts` — พยากรณ์ค่า parameter ล่วงหน้า (kNN)

| column | ความหมาย / หน้าที่ |
|---|---|
| `pond_id` + `parameter` | **PK** — 1 แถวต่อ parameter ต่อบ่อ (อัปเดตทับทุก analysis run) |
| `generated_at` | เวลาที่สร้างชุดพยากรณ์ล่าสุด — เก่ากว่า 90 นาที = กราฟเทา/ไม่สด |
| `model` | เวอร์ชันโมเดล (`knn_v1`) |
| `horizon_hours` | ล่วงหน้ากี่ชั่วโมง (ปัจจุบัน 12) |
| `points` | jsonb array เรียงเวลา: `[{t, v, p25, p75, n}]` — `t` = เวลา ISO (UTC), `v` = ค่ากลาง (median ถ่วงน้ำหนัก) หรือ **null** (เพื่อนบ้านมีข้อมูลไม่พอ), `p25`/`p75` = ช่วงความเชื่อมั่น, `n` = จำนวนเพื่อนบ้านที่มีข้อมูล ณ จุดนั้น · จุดทุก 30 นาที (24 จุด สำหรับ 12 ชม.) |
| `neighbors` | jsonb `[{date, distance}]` — วันที่ในอดีตที่ถูกใช้เป็นเพื่อนบ้าน (debug/อธิบายผล) |

**ความหมาย:** กราฟ **Predictive** ของหน้า Full Analysis — เอาวันในอดีตที่ "คล้ายวันนี้" (activity + สภาพน้ำช่วงที่ผ่านมา) มาเฉลี่ยค่าที่ **เวลาเดียวกันของวัน** เป็นเส้นอนาคต. ไม่มีแถว = ข้อมูลอดีตไม่ถึงเกณฑ์ (`< 5 วัน`) → app แสดง "Not enough data"

**ความสัมพันธ์:** `pond_id` FK ponds; app อ่านผ่าน RLS (เจ้าของบ่อ) — backend เป็นผู้เขียนเท่านั้น (upsert ทุก job)

---

## 3. Backend Flow (input/output ที่ app ควรรู้)

### 3.1 Input: PondSnapshot

Backend โหลด (ผ่าน `db/adapter.py`):
```
PondSnapshot(
  pond: PondInfo,                  # pondId, timezone, biomassKg, avgWeightG, fishCount
  severityReports: [...],          # SeverityReportView {parameter, time, value, zone, direction, severity} เรียงเวลา
  activities: [...],               # ทุก activity ของบ่อ
  diagnostics / predictions / recommendations: [...],  # ของเดิมที่มีอยู่แล้ว
)
```

### 3.2 Output: ChangeSet

```
ChangeSet(
  diagnostics: (DiagnosticReport, ...),      # ใหม่/เปลี่ยน เท่านั้น
  predictions: (Prediction, ...),            # ใหม่/เปลี่ยน เท่านั้น
  recommendations: (Recommendation, ...),    # ใหม่/เปลี่ยน เท่านั้น
  activityOps: (ActivityOp, ...),            # create/update/delete กิจกรรม (เช่น D15 ตัด aeration)
  notifications: (Notification, ...),        # outbox entries
)
```
Adapter persist ChangeSet ทั้งหมดใน 1 transaction (upsert by id; ไม่ insert แถวซ้ำ)

### 3.3 Trigger kinds (สำคัญต่อ app)

| kind | เกิดเมื่อ | ผลต่อ app |
|---|---|
| `reading` | sensor เข้าใหม่ | severity/diagnostic/prediction/rec อัปเดต; detector (PH_SWING) รันเฉพาะตอนนี้ |
| `activityEvent` | app เพิ่ม/แก้/ลบ activity | rec ถูก re-evaluate (causes, dedupe, expiry) |
| `pondEdit` | แก้ weight/count | predictions คำนวณใหม่ (meal% เปลี่ยน); diagnostics เก่า **ไม่แตะ** |
| `tick` | cron/cron-job.org | งานป้องกัน stale; rec time-based expiry |

### 3.4 Stale rule (Rule 11) — app แสดงอย่างไร

- Reading เก่ากว่า `3 × expectedIntervalMinutes` (3 × 30 = **90 นาที**) = stale
- Backend **ไม่สร้างผลใหม่** จากข้อมูล stale, ไม่ expire rec แค่เพราะขาดข้อมูล
- app แสดง "Last updated" ตาม `severity_reports.measured_at` — ไม่มีสถานะ Fresh/Stale/Offline (ตาม spec §3.3)

### 3.5 Dedupe key (กัน rec ซ้ำ)

| entry | key | หมายความว่า |
|---|---|---|
| AERATE | `AERATE:{nightDate}` | 1 rec ต่อคืน |
| WATER_CHANGE | `WATER_CHANGE:{localDate(anchor)}` | 1 rec ต่อวัน (local บ่อ) |
| ADD_ALKALINITY | `ADD_ALKALINITY` | คงที่ — มี pending แล้วไม่สร้างเพิ่ม |

- ถ้ามี open rec key เดิม → draft ใช้ key เดิม + anchor = createdAt เดิม (กันซ้ำตอนข้ามเที่ยงคืน)
- ถ้า urgency สูงขึ้น → anchor = now (deadline ใหม่เริ่มใหม่)

### 3.6 Idempotency

- ผลเดิม + trigger เดิม + now เดิม → ChangeSet เดิม
- รันซ้ำบน snapshot ที่ apply แล้ว → ChangeSet ว่าง
- `changedOnly(newObjs, existingById)` ตัดออกเฉพาะ object ที่เหมือนเป๊ะ
- แอปไม่ต้องทำอะไรพิเศษ — backend รับประกัน

### 3.7 Activity edit rules (retro window — app ต้อง validate ตรงกัน)

- Floor = `now − retroWindowDays` (4 วัน): startTime ก่อน floor → ปฏิเสธ `outside_retro_window`
- อนาคตแก้ได้เสมอ
- สร้าง: source ต้องเป็น `user` (`invalid_source`)
- ลบ: recommendation-origin → ลบไม่ได้ (ให้ skip แทน); user → ได้
- แก้ status: `done/skipped → pending` → `status_rollback`; `done ↔ skipped` → ได้
- แก้ id/pond/source/createdAt → `immutable_field`
- Batch Save = all-or-nothing
- **DB guard trigger บังคับกฎเดียวกับ `services/activity_edit.py`** — app จะพลาดก็เจอ error จาก DB

---

## 4. Contract ที่แอปใช้ (read/write)

### 4.1 อ่านตรงผ่าน Supabase (RLS)

| ต้องการ | ตาราง | วิธี |
|---|---|---|
| การ์ด parameter + severity text | `severity_reports` (SELECT, เรียง measured_at DESC) | columns: value/zone/severity/recovering/description/detail/append_des/guidance |
| Full Analysis (กราฟ + threshold ณ เวลานั้น) | `severity_reports` (SELECT ตามช่วงเวลา) | เพิ่ม `threshold` jsonb = ค่า threshold ที่ใช้จริงตอนนั้น (ดู §2.7) — ใช้วาดเส้น Optimal/Stress สีโซนย้อนหลังได้ตรงกับที่ engine ตัดสิน |
| Full Analysis (กราฟอนาคต) | `parameter_forecasts` (SELECT + Realtime) | `points` jsonb = เส้นพยากรณ์ + band; ไม่มีแถว = "Not enough data" (ดู §2.17) |
| "Why" / diagnostic | `diagnostic_reports` (SELECT) | text cache `text` jsonb → render ไม่ต้องทำเอง |
| Prediction | `predictions` (SELECT) | `text` jsonb + status/evidence |
| Recommendation list | `recommendations` (SELECT) | เรียง urgency + valid_until; `recommendation_sources` ถ้าอยากรู้แหล่งที่มา |
| Checklist | `activities` (SELECT) + `activity_series` | |
| แจ้งเตือน | `notifications` (SELECT + Realtime) | mark-read: UPDATE read_at |
| บ่อ | `ponds` (SELECT) | generated: volume/biomass/density |

### 4.2 เขียนตรง (RLS หรือ RPC)

| การกระทำ | วิธี | หมายเหตุ |
|---|---|---|
| สร้างบ่อ | RPC `create_pond(...)` | trigger สร้าง pond_states/analysis_state + enqueue เอง |
| แก้บ่อ (name/weight/count) | UPDATE `ponds` | column grant อนุญาตแค่ 3 คอลัมน์; guard บล็อกคอลัมน์อื่น; weight/count → pond_states ใหม่ + `pondEdit` |
| Checklist save | RPC `save_checklist(pond_id, changes)` | changes = array of {op: create/update/delete}; all-or-nothing |
| เพิ่ม/แก้ activity เดี่ยว | RPC `upsert_activity` / `delete_activity` | guard trigger ตรวจ retro/status/immutable |
| Repeat | INSERT `activity_series` | cron ต่ออายุ generate ล่วงหน้า 7 วัน |

### 4.3 เขียนผ่าน Backend API (JWT + owner check)

| Endpoint | เรียก function | ผล |
|---|---|---|
| `POST /recommendations/{id}/preview` | `buildApplyPlan` (dry-run) | สร้าง summary (รวมถ้า aeration ชน → needsDecision) ไม่ persist |
| `POST /recommendations/{id}/apply` | `buildApplyPlan` | persist: activityOps + rec.status=applied; D15 ตัด/ลบ aeration ผู้ใช้ใน 1 transaction |
| `POST /recommendations/{id}/snooze` | `snoozeRec` | non_urgent เท่านั้น; until ≤ validUntil |
| `POST /recommendations/{id}/dismiss` | `dismissRec` | pending/snoozed → dismissed |
| `GET /health` | - | 200 ok (ไม่แตะ DB) |

### 4.4 Realtime

Subscribe: `notifications`, `severity_reports`, `recommendations` (changes ใหม่ → อัปเดต UI แบบ live)

### 4.5 Text rendering

ถ้า app ต้อง render เอง (ปกติอ่าน cache จาก DB แล้ว): `renderRecommendation`, `renderDiagnostic`, `renderPrediction`, `renderNotification`, `renderApplySummary`, `renderPlan`
- `DISCLAIMER_TEXT` = "Automated estimate based on your logs and sensor data. Not a guarantee." (แสดงบน urgent rec)

### 4.6 Severity text (English ที่ app แสดง)

app อ่าน 4 columns จาก `severity_reports`:
- `description`: "DO is slightly outside the suitable range" / "pH is low, slightly outside the suitable range"
- `detail`: อาการต่อปลา (parameter-specific)
- `append_des`: ข้อความเชิงเวลา เช่น "low DO has been continuous beyond 8 h. Now 8.5 h."
- `guidance`: คำแนะนำเกษตรกร

สถานะ: engine สร้างเป็น **English ทั้งหมดแล้ว** (refactor ล่าสุด), ไม่มี Thai, ไม่มี copy-paste bug, abnormalLabel ถูกต้องทุก parameter

---

## 5. สรุป 10 อย่างที่แอปต้องทำ

1. อ่านการ์ด parameter จาก `severity_reports` (value, severity, recovering, 4 text columns)
2. อ่าน diagnostic จาก `diagnostic_reports.text`
3. อ่าน prediction จาก `predictions.text` + status
4. อ่าน recommendation จาก `recommendations` (เรียง urgency, ตรวจ valid_until)
5. เขียน checklist ผ่าน `save_checklist` RPC (all-or-nothing)
6. Apply rec ผ่าน `POST /recommendations/{id}/apply` (+ preview ก่อน)
7. Snooze/dismiss ผ่าน backend API (ไม่เขียนตรง)
8. แก้บ่อได้เฉพาะ name/avg_weight_g/stocking_count
9. Subscribe Realtime: notifications, severity_reports, recommendations
10. แสดง push 2 กรณี: Critical severity + urgent rec ใหม่ (ผ่าน notifications.push_eligible)
