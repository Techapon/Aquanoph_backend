# Application Spec v0.4 (Prototype)

ครอบคลุมเฉพาะ Part 1 (Application) รวมคำตอบ Q1–Q10, N1–N4 และ Special Part
Part 1 ปิดแล้ว (รายละเอียดการแก้ข้อมูลย้อนหลังอยู่ใน `special_part_retroactive_edits_v0.2.md`)

---

## 0. สิ่งที่เปลี่ยนจาก v0.1 (รวมการปรับใน v0.3)

| หัวข้อ | v0.1 | v0.2 |
|---|---|---|
| หน้ารายการบ่อ | ไม่มี | **มี Card list** (ต้นแบบมี 1 การ์ด) |
| การติ๊ก checklist | dialog ยืนยันทุกครั้ง | ติ๊กได้หลายรายการก่อน (ยังไม่บันทึก) แล้วกด **Save** และมี **dialog ยืนยัน** ก่อนบันทึกลง database |
| Timezone | ค่าคงที่ Asia/Bangkok | เก็บเวลาเป็น UTC, บ่อมี timezone ของตัวเองไว้ให้ Analysis ใช้, App แสดงเวลาตาม timezone ปัจจุบันของ user |
| แก้ข้อมูลบ่อ | ทุกฟิลด์ | เฉพาะ **ชื่อบ่อ, น้ำหนักปลา, จำนวนปลา** (Device ID และ timezone แก้ไม่ได้) |
| Device ID | optional | **บังคับกรอก** ตอนสร้างบ่อ |
| ชนิด activity | 5 ชนิด (alkalinity รวม lime, probiotic ไป other) | **7 ชนิด** แยก alkalinity / lime / probiotic |
| ภาษา | UI ไทย + severity อังกฤษ | **อังกฤษล้วน** |
| พิกัดบ่อ (lat/long) | เสนอให้เพิ่ม | **ไม่เก็บ** เก็บ timezone แทน |
| จำนวนปลา | ข้อจำกัด: ไม่ลดตามการตาย | user แก้จำนวนเองได้ (แค่ไม่มีระบบ mortality) |
| จุดเริ่มข้อมูลที่ Analysis ใช้ | `stocking_date` | `max(stocking_date, เวลาสร้างบ่อ)` เพราะไม่มีรอบเลี้ยงและ `stocking_date` แก้ไม่ได้ (Device ID บังคับกรอกตอนสร้าง จึงไม่ต้องมี `device_linked_at` แยก) |
| สถานะ Recommendation | 6 สถานะ | 5 สถานะ (ตัด `superseded` ใช้ `expired` + `reason`) |
| แก้ข้อมูลย้อนหลัง | ยังไม่กำหนด | แก้/ลบ activity ย้อนหลังได้ **4 วัน** ย้อนสถานะหลัง Save ไม่ได้ |

---

## 1. ขอบเขตต้นแบบ

- Flutter, Supabase, ออนไลน์เท่านั้น
- ภาษาอังกฤษล้วนทั้งโปรเจกต์ (UI, ชื่อระดับ severity, ข้อความอธิบาย/guidance/recommendation, disclaimer) หน่วย SI
- 1 account สร้างได้ 1 บ่อ (schema รองรับหลายบ่อ แต่ UI จำกัด)
- ยังไม่มีทุ่นจริง ข้อมูลเซนเซอร์มาจาก simulator/free dataset ฝั่ง dev ไม่มีหน้ากรอกค่าด้วยมือ
- ปลานิลเท่านั้น, 6 parameter: DO, NH₃, NO₂, Temperature, pH, Salinity
- ยังไม่มีระบบรอบการเลี้ยง

---

## 2. แผนผังหน้าจอ

| # | หน้าจอ | หน้าที่ |
|---|---|---|
| 1 | Sign up / Login | สมัครด้วย email + username, ล็อกอินด้วย email + password |
| 2 | **Pond list (Card list)** | การ์ดของแต่ละบ่อ: ชื่อบ่อ, parameter ตัวแทน + ระดับ, เวลาอัปเดตล่าสุด / ปุ่มเพิ่มบ่อซ่อนเมื่อมีครบ 1 บ่อ |
| 3 | Create Pond / Edit Pond | กรอกข้อมูลบ่อ / แก้ได้เฉพาะ 3 ค่า |
| 4 | Pond status | แสดง parameter ที่สำคัญที่สุด 1 ตัวแบบละเอียด |
| 4.1 | All parameters | แถวสรุปทุกตัว (ค่า, ระดับ) |
| 4.2 | Parameter detail | รายละเอียดของแต่ละ parameter |
| 5 | Checklist (รายวัน) | เลือกวัน ติ๊ก/ข้าม แล้ว Save, แก้/เพิ่ม activity |
| 5.1 | Add / Edit activity | ฟอร์มตามชนิด activity |
| 6 | Recommendations | แท็บ Today / Upcoming / History, รายละเอียด, apply |
| 7 | Analysis | Retrospective (กราฟ) และ Predictive (placeholder) |

---

## 3. โมดูลและกฎ

### 3.1 Account
- สมัครด้วย email + username (ห้ามซ้ำ ไม่แยกตัวพิมพ์เล็ก/ใหญ่)
- ยืนยันอีเมลก่อนใช้งาน และมี reset password (ฟีเจอร์ของ Supabase Auth)

### 3.2 Pond
- **ตอนสร้าง user กรอก:** ชื่อบ่อ, พื้นที่ (m²), ความลึกเฉลี่ย (m), สปีชีส์ (dropdown), จำนวนปลา, น้ำหนักเฉลี่ย, วันที่ปล่อย, Device ID (**บังคับ**), timezone ของบ่อ (ค่าเริ่มต้น = timezone ของเครื่อง แก้ได้ตอนสร้างเท่านั้น)
- **ระบบคำนวณ:** ปริมาตร, biomass, density (kg/m³)
- **แก้ภายหลังได้:** ชื่อบ่อ, น้ำหนักเฉลี่ย (user สุ่มชั่งแล้วกรอก), จำนวนปลา (ใช้ปรับเมื่อมีปลาตาย) ค่าที่แก้ถูกใช้เป็น "ค่าปัจจุบัน" ตั้งแต่เวลาที่แก้เป็นต้นไป
- **แก้ไม่ได้:** พื้นที่, ความลึก, สปีชีส์, วันที่ปล่อย, Device ID, timezone (ถ้ากรอกผิดให้ dev แก้ใน DB ในช่วงต้นแบบ)
- Device ID ต้องไม่ซ้ำกับบ่ออื่น และต้องมีอยู่จริงในตารางอุปกรณ์
- ไม่มีหน้าลบ/เก็บถาวรบ่อ และไม่มีแนวคิดรอบเลี้ยง (เริ่มรอบใหม่ = สร้างบ่อใหม่ในต้นแบบ)

### 3.3 Status (Assess Severity)
- 4 ระดับ: Optimal / Stress / ElevatedRisk / Critical และมีป้าย "Recovering" (Recovery Hold) พร้อมเวลาที่เหลือ
- **Pond status** แสดง parameter ตัวแทน 1 ตัวแบบละเอียด
  - ทุกตัว Optimal → แสดง DO
  - มีตัวที่ไม่ใช่ Optimal → ตัวที่ severity สูงสุด ถ้าเท่ากันใช้ลำดับ parameter (ค่าเริ่มต้น DO > NH₃ > NO₂ > Temperature > pH > Salinity เป็น config)
- กดดูเพิ่ม → แถวสรุปทุกตัว (ค่า, ระดับ) → กดแต่ละตัวเพื่อดูรายละเอียด
- การ์ด parameter แสดง: ค่า+หน่วย+เวลาที่วัด, ระดับ, อาการของสัตว์, เหตุผลเชิงเงื่อนไข, guidance, diagnostic reason (ซ่อนถ้าไม่มี)
- `guidance` เป็นข้อความคงที่ ไม่มีปุ่ม สิ่งที่ลง checklist ได้มาจาก Recommendation เท่านั้น
- แสดงเวลา "Last updated" อย่างเดียว ไม่มีสถานะ Fresh/Stale/Offline, อัปเดตแบบ realtime

### 3.4 Checklist และ Activity

**หลักการ:** 1 activity = 1 รายการที่เป็นทั้งแผนและบันทึก เพิ่มผ่านฟอร์ม Add activity ที่ user เลือกเวลาเอง เมื่อติ๊กจะใช้เวลาและรายละเอียดที่บันทึกในรายการ (ถ้าทำจริงต่างจากแผน user แก้รายการก่อนหรือหลังติ๊กได้)

| ชนิด | เวลา | รายละเอียด |
|---|---|---|
| feeding | จุดเวลา | ปริมาณ (kg) |
| aeration | ช่วงเวลา (เริ่ม–สิ้นสุด) | ไม่มี |
| alkalinity | จุดเวลา | ปริมาณ (kg) |
| lime | จุดเวลา | ปริมาณ (kg) |
| probiotic | จุดเวลา | ปริมาณ (kg) |
| water_change | จุดเวลา | ตัวเลือก 1/4, 1/2, 3/4 ของบ่อ หรือกรอก % โดยประมาณ |
| other | จุดเวลา | ชื่อเอง (ไม่ถูกใช้ใน Analysis) |

- alkalinity / lime / probiotic ใช้โครงฟอร์มเดียวกัน (ปริมาณ + เวลา) ต่างกันแค่ชนิด/ชื่อ จึงไม่เพิ่มงานมาก (หน่วย kg ตามที่ระบุ แต่ probiotic จริงๆ มักเป็น g หรือ L เปลี่ยนได้ภายหลัง)
- feeding และ aeration คือสองชนิดที่ต้องติดตามทุกวัน
- Repeat: สวิตช์ "ทำซ้ำทุกวันตั้งแต่วันนี้" ระบบสร้างรายการล่วงหน้า 7 วัน และเก็บรหัสชุด (`series_id`) เพื่อแก้ "ตั้งแต่วันนี้เป็นต้นไป" ได้
- **การติ๊ก (batch):** user ติ๊ก 1 หรือหลายรายการ (และกด skip) ในหน้าก่อน ยังไม่บันทึกอะไร แล้วกด **Save** จะมี **dialog ให้ยืนยัน** (สรุปจำนวนรายการ) ก่อน เมื่อยืนยันระบบจึงเขียนลง database ในครั้งเดียว (all-or-nothing) ออกจากหน้าโดยยังไม่ Save → เตือนว่าจะทิ้งการเปลี่ยนแปลง ติ๊กวันอนาคตไม่ได้ วันนี้ติ๊กได้ทุกรายการ เวลาของ `done` คือเวลาที่บันทึกในรายการ ไม่ใช่เวลาที่กด Save
- **สถานะ:** `pending` / `done` / `skipped` ส่วน `missed` คำนวณจาก pending ที่เลยเวลาแล้ว (ไม่เก็บ)
- วันที่ไม่มีรายการ = **ไม่ทราบ (unknown)** ไม่ใช่ "ไม่ได้ทำ"
- **Conflict:** ในต้นแบบมีเฉพาะ **aeration ที่ช่วงเวลาซ้อนกัน ซึ่งบล็อกเด็ดขาดและไม่รวมให้อัตโนมัติ** ส่วนเกณฑ์เตือนเชิงตัวเลข (ระยะห่างมื้อ, เพดานปริมาณ ฯลฯ) เลื่อนไปภายหลัง จึงไม่ต้องใช้ผลวิจัยจาก prompt
- ไม่มี validation ปริมาณ
- รายการที่มาจาก Recommendation **ลบไม่ได้** (ถ้าไม่ทำให้กด skipped)
- รายการจาก Recommendation ไม่เร่งด่วนที่ missed: ย้ายมาวันนี้ด้วยการแก้เวลาตามปกติ
- แก้/ลบ activity ย้อนหลังได้ภายใน 4 วัน (ลบรายการ done ได้ แต่รายการจาก Recommendation ลบไม่ได้) ย้อนสถานะ done/skipped กลับเป็น pending ไม่ได้ แต่แก้เวลา/รายละเอียดได้ ผลต่อการวิเคราะห์ดู `special_part_retroactive_edits_v0.2.md`

### 3.5 Recommendation

| | ไม่เร่งด่วน | เร่งด่วน |
|---|---|---|
| ตัวอย่าง | ใช้ alkalinity | DO อาจต่ำอันตรายคืนนี้ |
| เวลาที่ทำ | เลือกวันได้ภายในช่วงที่ยังใช้ได้ | มี **ช่วงเวลาที่ต้องทำ** (เช่น 10:00–11:00) user เลือกเวลาในช่วงนั้น |
| เลื่อน (snooze) | ได้ (พรุ่งนี้/เลือกวัน ภายในช่วงที่ยังใช้ได้) | ไม่ได้ |
| ปฏิเสธ | dismiss ได้ | ได้แต่ต้องยืนยัน (แสดงเหตุผลและความเสี่ยงซ้ำ) และบันทึกการปฏิเสธ |
| หมดอายุ | เมื่อเลยช่วงที่ยังใช้ได้ | เมื่อเลยช่วงเวลาที่ต้องทำ |

- ข้อมูล: title, reason (จะเกิดอะไร + อ้างอิงข้อมูลอะไร), full action detail, ประเภท, `valid_from`–`valid_until`, parameter ที่เกี่ยวข้อง, `dedupe_key`, สถานะ, เวลาที่สร้าง, รายการ activity ที่เสนอ (0 ถึง n)
- **Apply:** เลือกเวลา → ตรวจ conflict → สร้างรายการ `pending` (source = recommendation)
- **เมื่อชน:** ตอนนี้เกิดเฉพาะ aeration ซ้อนกัน → "Adjust time" / "Don't apply" (ไม่มี replace/combine) การตรวจชนแบบอื่นรอผลของ Special Part
- Recommendation ที่ไม่มี activity ใช้ปุ่ม "Acknowledge" แทน Apply
- ไม่สร้างซ้ำถ้ามี pending ที่ `dedupe_key` เดียวกัน
- UI: แท็บ Today / Upcoming / History เร่งด่วนอยู่บนสุดเสมอ แสดงเร่งด่วนทั้งหมด + ไม่เร่งด่วนสูงสุด 3 อัน ที่เหลือใน "See more" และมี disclaimer สั้นๆ ที่ Recommendation เร่งด่วน

### 3.6 Analysis (Full Analysis Result)
- ช่วงเวลา: 24 ชม. / 7 วัน / 30 วัน / กำหนดเอง
- **Retrospective:** กราฟต่อ parameter พร้อมแถบสีโซน, min/max/avg (คำนวณตอนเปิดหน้า), marker ของ activity บนแกนเวลาเดียวกัน, diagnostic ที่ backend เก็บไว้ (เมื่อมี)
- **Predictive:** placeholder (กราฟอดีต + พื้นที่อนาคต + "Not enough data") ไม่ผูกรูปแบบข้อมูลจนกว่าจะจบ Part 2

### 3.7 Notifications
- Push เฉพาะ 2 กรณี: severity เป็น Critical และมี Recommendation เร่งด่วนใหม่ ทำเป็น phase ท้ายของต้นแบบ

### 3.8 เวลาและ timezone
- ทุก timestamp เก็บเป็น **UTC**
- **Analysis Backend** ใช้ timezone ของบ่อ ในทุก logic ที่ช่วงเวลาของวันมีผล (เช่น 02:00–05:00 DO ต่ำเป็นพิเศษ, กลางวัน/กลางคืน)
- **App** แสดงเวลา (Last updated, แกนเวลากราฟ, ประวัติ) ตาม timezone ปัจจุบันของ user
- วัน (day) ของ checklist และเวลาที่ตั้งในฟอร์มใช้ **timezone ของบ่อ** และแสดงแบนเนอร์ "Pond time (UTC+x)" เมื่อต่างจากเครื่อง user
- ไม่เก็บพิกัดบ่อ เก็บเฉพาะ timezone แบบ IANA id (เช่น `Asia/Bangkok`) ซึ่งรองรับ daylight saving ต่างจากการเก็บ UTC offset ตรงๆ

### 3.9 ส่วนที่ใช้ร่วมกัน
- Empty state: บ่อใหม่ยังไม่มีข้อมูล / ยังไม่มี activity / วันแรก / ข้อมูลไม่พอพยากรณ์
- Loading ใช้ skeleton (ยังไม่ทำการแสดงข้อมูลแคช)
- RLS: user เห็นเฉพาะบ่อของตน (บ่อมี `user_id`) simulator/Analysis backend เขียนผ่าน service role
- Hard delete ไม่มี soft delete และไม่เก็บประวัติการแก้ไข (กลับมาคุยใน Special Part) แต่ฐานข้อมูลเก็บ `created_at`/`updated_at` อัตโนมัติ
- report เก็บ snapshot ของ threshold และข้อมูลบ่อ (น้ำหนัก, จำนวน, density, timezone) ที่ใช้ตอนวิเคราะห์

---

## 4. State machine

### 4.1 Activity

```
pending ──Save (done)──▶ done
   └─────Save (skip)───▶ skipped
(missed = pending ที่เลยเวลาแล้ว ไม่ใช่สถานะที่เก็บ)
```

ก่อน Save การสลับติ๊ก/ยกเลิกเป็นแค่สถานะบนหน้าจอ **หลัง Save ย้อนสถานะไม่ได้** (done/skipped → pending ไม่อนุญาต) แต่แก้เวลา/รายละเอียดได้ภายใน 4 วัน

### 4.2 Recommendation

```
pending ──apply──────▶ applied
   │──dismiss/decline─▶ dismissed   (เร่งด่วนต้องยืนยัน)
   │──snooze──────────▶ snoozed ──ถึงเวลา──▶ pending   (เฉพาะไม่เร่งด่วน)
   └──หมดช่วงเวลา / ไม่เข้าเงื่อนไขหลังวิเคราะห์ใหม่──▶ expired (มี reason)
```

- สถานะของ Recommendation = การตัดสินใจเรื่อง "คำแนะนำ" / สถานะของ Activity = การทำ "งานจริง" หลัง apply
- `expired` เกิดโดยระบบและมี `reason` (เช่น หมดช่วงเวลา, ไม่เข้าเงื่อนไขหลังวิเคราะห์ใหม่) เกิดได้เฉพาะจาก `pending` หรือ `snoozed` ส่วน `applied`/`dismissed` แล้วระบบไม่เปลี่ยนอีก

---

## 5. พจนานุกรมข้อมูล (ระดับ business)

**Pond:** user_id, name, area_m2, avg_depth_m, species, stocking_count, avg_weight, stocking_date, device_id (บังคับ, unique, แก้ไม่ได้), timezone (IANA id, แก้ไม่ได้), created_at / คำนวณ: volume, biomass, density

**Activity:** pond, type, เวลาของ activity (จุดเวลาหรือเริ่ม–สิ้นสุด), detail (ตามชนิด), title (เฉพาะ other), status, source (self / recommendation) + อ้างอิง recommendation, series_id (กรณี repeat), created_at, updated_at

**Recommendation:** ตามหัวข้อ 3.5

**Severity report ที่ App แสดง:** parameter, ค่า, เวลาที่วัด, level, recovering หรือไม่, อาการ, เหตุผลเชิงเงื่อนไข, guidance, diagnostic (ถ้ามี), snapshot

**ตารางที่มีอยู่แล้วใน Database (จาก Q10):** (1) ตาราง devices (device_id + รายละเอียดอุปกรณ์) (2) ตารางค่า parameter ทั้งชุด 1 แถวต่อ 1 การวัด: device_id | DO | pH | … (ต้องมีคอลัมน์เวลาที่วัดเป็น UTC ด้วย) ใช้ตรวจว่า Device ID ที่ user กรอกมีอยู่จริง

**คำศัพท์**

| กลุ่ม | ค่า |
|---|---|
| Severity | Optimal, Stress, ElevatedRisk, Critical (+ป้าย Recovering) |
| Parameter | DO, NH₃, NO₂, Temperature, pH, Salinity |
| Activity type | feeding, aeration, alkalinity, lime, probiotic, water_change, other |
| Activity status | pending, done, skipped (missed คำนวณ) |
| Recommendation status | pending, snoozed, applied, dismissed, expired (+ reason) |

---

## 6. การคัดกรองส่วนที่บวม (ปรับตามคำตอบล่าสุด)

### 6.1 คงไว้ (แกนของระบบ)
Severity 4 ระดับ + Recovering / parameter ตัวแทน 1 ตัว / activity + checklist / Recommendation แยกเร่งด่วน + apply + ช่วงเวลาของ urgent / Retrospective (กราฟ + zone band + min/max/avg) / Auth (ใช้ Supabase Auth)

### 6.2 คงไว้ แต่ทำให้เล็ก

| ส่วน | วิธีทำให้เล็ก |
|---|---|
| Card list ของบ่อ | การ์ดเดียวในต้นแบบ ไม่มีปุ่มเพิ่มเมื่อครบ 1 บ่อ (schema รองรับหลายบ่อเพราะไม่เพิ่มต้นทุน) |
| 7 ชนิด activity | alkalinity/lime/probiotic ใช้ฟอร์มเดียวกัน ต่างแค่ชนิด จึงสื่อสารกับ user ชัดโดยไม่เพิ่มงานฟอร์ม |
| Batch tick + Save + dialog ยืนยัน | dialog ครั้งเดียวต่อการ Save (ไม่ใช่ต่อรายการ) แต่ต้องเก็บ state ที่ยังไม่ Save บนหน้าจอและบันทึกแบบ transaction เดียว |
| Repeat | สวิตช์เดียว (ทุกวัน) + `series_id` ไม่มี template |
| Conflict | มีเฉพาะ aeration ซ้อนบล็อก เกณฑ์เตือนเชิงตัวเลขเลื่อนไปภายหลัง ไม่มี replace/combine |
| Timezone | เก็บ IANA id ต่อบ่อ ค่าเริ่มต้นจากเครื่อง ไม่มีพิกัด |
| Tie-break parameter | เหลือ 2 ชั้น (severity → ลำดับ parameter) |
| Retrospective | เลื่อน timeline เหตุการณ์, จำนวนครั้ง HighRisk/Critical, เวลาในแต่ละโซน |
| Push | 2 กรณี และเป็น phase ท้าย |
| `superseded` | **ตัดออกแล้ว** ใช้ `expired` + `reason` แทน |

### 6.3 ตัดแล้ว
เกณฑ์เตือน conflict เชิงตัวเลข (prompt วิจัยพักไว้) / Crop cycle / mortality / ประมาณน้ำหนักอัตโนมัติ / validation ปริมาณ / สถานะ Fresh-Stale-Offline / หน้าลบหรือ archive บ่อ / ประวัติการแก้ pond และ soft delete / combine ใน conflict / พิกัดบ่อ / การแก้ไขฟิลด์โครงสร้างของบ่อ (พื้นที่, ความลึก, สปีชีส์, วันที่ปล่อย) / ลบบัญชี, เตือน checklist, ให้คะแนน Recommendation, ส่งออกรายงาน

### 6.4 เลื่อนไป Part 2
ข้อมูลเซนเซอร์มาช้า (L6), data gap (L9), และการตัดสินว่าการแก้น้ำหนัก/จำนวนปลาเป็น trigger ของการวิเคราะห์หรือไม่ (ขึ้นกับว่า analysis ใช้ค่านั้นจริงหรือไม่)

---

## 7. ข้อจำกัดที่รับไว้ในต้นแบบ

1. น้ำหนักปลาเท่ากับค่าที่ user กรอกล่าสุด ถ้าไม่อัปเดต threshold ของ DO จะใช้น้ำหนักเก่า
2. จำนวนปลาไม่ลดอัตโนมัติ user ต้องแก้เอง
3. ถ้าทุ่นหยุดส่งข้อมูล App แสดงค่าล่าสุดพร้อมเวลาเท่านั้น
4. ไม่มีประวัติการแก้ pond ดูได้เฉพาะ snapshot ใน report จึงต้องบันทึก snapshot ตั้งแต่ต้น
5. ไม่มีรอบเลี้ยง เริ่มรอบใหม่ = สร้างบ่อใหม่ และฟิลด์ที่แก้ไม่ได้ (รวม Device ID, timezone) ถ้ากรอกผิดต้องให้ dev แก้ใน DB
6. ไม่มีพิกัด เวลาดวงอาทิตย์ขึ้น-ตกต้องประมาณจาก timezone (เหมาะกับเขตร้อน ไม่แม่นที่ละติจูดสูง) ไปตัดสินใจใน Part 2
7. ค่าเซนเซอร์ผูกกับ device ไม่ใช่กับบ่อ จึงใช้เวลาสร้างบ่อเป็นตัวกั้นข้อมูลก่อนหน้า และเพราะ Device ID แก้ไม่ได้ จึงย้ายอุปกรณ์ข้ามบ่อไม่ได้ในต้นแบบ

---

## 8. คำตอบที่ปิดแล้ว (N1–N4)

| ข้อ | ข้อสรุป |
|---|---|
| N1 | Device ID บังคับกรอก จึง **Device ID และ timezone แก้ไม่ได้** ฟิลด์ที่แก้ได้มีแค่ ชื่อ, น้ำหนัก, จำนวนปลา |
| N2 | Analysis ใช้ข้อมูลตั้งแต่ `max(stocking_date, เวลาสร้างบ่อ)` |
| N3 | checklist (แบ่งวัน, ตั้งเวลา) ใช้ timezone ของบ่อ ส่วน timestamp อื่นแสดงตามเครื่อง user |
| N4 | ติ๊กได้ไม่จำกัดโดยยังไม่บันทึก จากนั้นกด Save และมี dialog ยืนยันก่อนบันทึก |

---

## 9. Special Part (ปิดแล้ว)

สรุปการตัดสินใจอยู่ใน `special_part_retroactive_edits_v0.2.md` ประเด็นหลัก: ช่วงย้อนหลัง 4 วัน, ย้อนสถานะหลัง Save ไม่ได้, ลบรายการ done ได้ภายใน window, ตัด `superseded`, ผลที่คำนวณใหม่เขียนทับพร้อม `revised_at`

---

## 10. โน้ตส่งต่อไป Part 2 และ Part 3

**Part 2 (Backend for Analysis)**
- ข้อความ symptom / reason / guidance / diagnostic / recommendation ต้องมีเป็นภาษาอังกฤษ (ถ้าไฟล์ 09 มีข้อความไทย ต้องแปลหรือเขียนใหม่)
- ประมาณเวลาดวงอาทิตย์ขึ้น-ตกจาก timezone
- เริ่มใช้ข้อมูลตั้งแต่ `max(stocking_date, เวลาสร้างบ่อ)` (N2)
- นโยบาย data gap (L9) ยังพักไว้
- ตัดสินว่าน้ำหนัก/จำนวนปลาเป็น trigger ของ Prediction/Recommendation หรือไม่ ตามที่ analysis ใช้ค่านั้นจริง (ทำเป็นรายการตั้งค่า)

**Part 3 (Database)**
- ตารางค่าเซนเซอร์ผูกกับ `device_id` ต้องมีเวลาที่วัด (UTC) และ flag `late` (L6)
- Pond → Device ผ่าน `device_id` (unique ระหว่างบ่อ) ตรวจกับตาราง devices
- Repeat 7 วันต้องมีกลไกต่ออายุรายการ (เช่น scheduled job รายวัน หรือสร้างเพิ่มเมื่อเปิดแอป)
- Batch Save = 1 transaction
- report เก็บ snapshot ตาม 3.9

---

## 11. ขั้นตอนถัดไป

1. ใช้ `research_prompt_diagnostic_knowledge.md` หาข้อมูลเชิงวิชาการ แล้วนำผลมาออกแบบ
2. Part 2 เริ่มจาก recommendation catalog และ Diagnostic cause catalog
3. จากนั้นไป Part 3 (Database)
