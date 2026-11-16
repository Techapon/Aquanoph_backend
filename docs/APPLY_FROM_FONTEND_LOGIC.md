สรุป logic ระบบ Activity ที่ใช้จริงตอนนี้ (อ่านจากโค้ดทั้งหมดแล้ว) — เรียงตามชั้น:

---

## 1. ข้อมูล (Entity / DB)

**`ActivityEntity`** — ชนิด, สถานะ, เวลา, ที่มา:
- **Type 8 ค่า**: `feeding`, `aeration`, `waterChange`, `alkalinity`, `lime`, `probiotic`, `other`, `unknown` (map จาก `feeding/water_change/...` — ค่าที่ไม่รู้จัก → `unknown`)
- **Status 3 ค่า**: `pending | done | skipped` (default `pending` ถ้าอ่านค่าแปลก)
- **เวลา**: `startTime` (UTC, จำเป็น), `endTime` (เฉพาะ aeration = ช่วงเริ่ม–จบ), `fraction` (water change 1/4,1/2,3/4), `quantityKg` (feeding/alkalinity/lime/probiotic)
- **`missed`**: คอลัมน์ computed จาก view `v_activities` (pending ที่เลยเวลา) — โหลดมาแล้ว **แต่ไม่แสดงที่ไหน**
- **`originRecId`**: มีค่าก็ต่อเมื่อ `source='recommendation'` — เอาจาก `source_rec_id` ก่อน ไม่มี则 parse จาก id รูป `act:{recId}:{index}` (id ฝั่ง backend กำหนดแบบ deterministic) ; `source='user'` → null เสมอ

**DB บังคับ (guard trigger + constraint — แอปไม่ทำ ปล่อยให้ DB โยน error กลับมา):**
- aeration ห้ามซ้อนกัน (exclude GiST) — **ชนิดอื่นไม่มี constraint นี้**
- retro window 4 วัน: `startTime` เกิน `now−4วัน` → แก้/ลบไม่ได้
- ย้อน status `done/skipped → pending` ไม่ได้ (`status_rollback`); `done ↔ skipped` ได้
- คอลัมน์ id/pond/source/createdAt แก้ไม่ได้ (`immutable_field`)
- ลบ activity ที่มาจาก Recommendation ไม่ได้

---

## 2. การอ่าน (Read)

**`getDay(pondId, from, to)`** → query `v_activities` เรียง `start_time`:
- กรอง `start_time >= from AND < to` (caller เป็นคนคำนวณ boundary เป็น UTC แล้ว — datasource ไม่รู้ timezone)
- ** bekan limit**: กรองเฉพาะ `start_time` — aeration ที่เริ่มก่อนเที่ยงคืนจะหายจากวันถัดไป (มี ponytail note ไว้)
- สองที่ใช้:
  1. **PondHomeProvider.load()** — วันปัจจุบันของบ่อ (`pondDayUtc`) → การ์ด 3 ใบ + realtime refetch
  2. **ActivityProvider** (instance ต่อ checklist sheet) — วันเดียวกัน + `fetchDay()` แบบ read-only สำหรับ pre-flight เช็ค conflict ตอน apply

---

## 3. การเขียน (Write) — 3 RPC ทั้งหมด

| RPC | ใช้ตอน | พฤติกรรม |
|---|---|---|
| `save_checklist(pond_id, changes[])` | ติ๊ก Save / Edit Schedule | batch **all-or-nothing** 1 transaction; changes = `{op: create/update/delete, activity/id}` |
| `upsert_activity(pond_id, activity)` | Add Activity / Apply-to-other-day | คืน id (ใหม่หรือของเดิม) — **ไม่ส่ง id = สร้างใหม่เสมอ** |
| `delete_activity(id)` | Delete Activities | ลบทีละรายการ |

ทุก error → `CoreFailure.databaseError` → โชว์ "Save failed" dialog. **ทุก write สำเร็จ → `load()` ซ้ำทันที** (refresh ทั้ง home ผ่าน onSaved callback → PondHomeProvider.load → realtime channel อยู่แล้วไม่ resubscribe)

---

## 4. Flows ฝั่ง UI (checklist_sheet.dart 1706 บรรทัด)

### 4.1 Checklist หลัก (เปิดจากการ์ด Feeding/Aeration/Other บน pond home)
- **กรองตาม type**: feeding → `type==feeding` / aeration → `type==aeration` / **other → ทุกชนิดที่ไม่ใช่ feeding+aeration**
- ติ๊ก = **toggle done↔pending เฉพาะบนจอ** (ยังไม่เขียน DB), นับ `_changed` โชว์ "Save (N)"
- **Save**: confirm dialog สรุปจำนวน → `save_checklist` (เปลี่ยนเฉพาะ `status`) → success dialog → `onSaved()` → home reload
- **Pop ออกมี unsaved** → PopScope ถาม "Discard changes?"
- rec-origin row: tint + AppliedBadge ซ้อนขอบบน (อ่าน urgency จาก `recUrgencyById[originRecId]`)
- **ไม่มีปุ่ม skip** — ติ๊กได้แค่ done/pending (gap vs spec §146 ที่บอก "ติ๊ก + กด skip")

### 4.2 Edit Schedule (เฉพาะ feeding/aeration)
- แก้เวลา (start/end) + kg ของ feeding → รวมเป็น changes ชุดเดียว → `save_checklist`
- ปุ่ม "Feed the shrimp" = label ผิด species (โลโก้ inspect ไว้ — ปลานิล)

### 4.3 Add Activity
- กรอกเวลา (เครื่อง当地时间 → convert UTC ด้วย `_localToUtc` fixed offset), kg, fraction, aeration มี start–end
- `source: 'user'`, `status: 'pending'` เสมอ → `upsert_activity`
- **ไม่เช็ค overlap/ซ้ำเวลาเลย** (ปล่อย DB constraint — aeration เท่านั้นที่ชน)

### 4.4 Apply to other day (1 / 7 / 30 วัน)
1. double-tap guard (`beginApply`)
2. เอา activity ของวันนี้ตาม type เดียวกับ sheet
3. **Pre-flight**: วนวันเป้าหมาย → `fetchDay` → ถ้าวันนั้นมี activity **ชนิดเดียวกันอยู่แล้ว** → ใส่ `conflictDays` (ที่เหลือ = `freeOffsets`)
4. มี conflict → dialog "Schedule already exists" → user เลือก Apply to free days ต่อ / cancel
5. สร้างทีละวัน×ทีละรายการ (shift ตาม pond-local day, `source:'user'`) → สรุป "Created N, skipped M"
- **known soft spots**: `fetchDay` error → คืน `[]` เงียบ (วันดูว่าง); ไม่เช็คเวลาชนข้ามชนิด; aeration ชนซ้อนจะชน DB constraint แล้ว fail กลางคัน (ข้อความ error ไม่สวย)

### 4.5 Delete Activities
- ลบทุกแถวใน type นั้น **ไม่กรอง originRecId** → แถว rec-origin จะโดน DB ปฏิเสธ → fail กลาง loop (UI ไม่ได้บอกว่า "ลบไม่ได้ ให้ใช้ skip")

---

## 5. Activity ที่เกิดจาก Recommendation (เส้นทาง backend)

- Rec Apply (HTTP API `preview`/`apply` ไม่ใช่ Supabase) → backend สร้าง activity `source='recommendation'` + `source_rec_id` (หรือ id รูป `act:{recId}:{n}`)
- แอป **preview ก่อน** (`previewRec`) → ถ้า summary มีการแก้ activity ของ user → `formatPreApplyWarning` เตือนก่อน ("This will shorten your planned aeration...") → apply → `formatApplySummary` เล่าผล (เพิ่ม/ตัด/แยก/coveredByDone) เป็นเวลาบ่อ
- แถว rec-origin ในแอป: ** tint + AppliedBadge**, dot urgency บนการ์ด home, **ลบไม่ได้** (DB) — แก้เวลา/สถานะได้ตามกฎปกติ
- ตอน Apply urgent aeration: backend ทับ aeration `pending` ของ user (§6.4) — ฝั่งแอปแค่ reload

---

## 6. การแสดงผลบน Pond Home

- การ์ด 3 ใบ: **Feeding** (จุดเวลา + kg), **Aeration** (ช่วงเวลา), **Other** (จุดเวลา + type name) — chip ติ๊ก ✓ ถ้า `done`, "Nothing logged today" ถ้าว่าง
- **Dot urgency**: 1 ตัวต่อ origin rec ที่ distinct (ไม่ใช่ต่อ row) — 8×8px, อ่านจาก `recUrgencyById`
- **`missed` ไม่ได้ใช้**, skipped ไม่ได้แสดงผลต่างจาก pending

---

## 7. Realtime

PondHomeProvider subscribe `activities` (filter pond_id) → event → debounce 2s → `load()` ใหม่ ทั้งบ้าน refresh — แต่ **ActivityProvider ใน sheet ไม่มี realtime** (sheet เปิดสั้นๆ, onSaved ยิง load เอง)

---

## 8. Gap ที่ยังค้าง (เทียบ spec — ยังไม่ได้ทำ)

| เรื่อง | สถานะ |
|---|---|
| ปุ่ม Skip ก่อน Save (§146) | ❌ ไม่มี |
| Repeat ทุกวัน + `series_id` (§145) | ❌ ไม่แตะ |
| Retro window validate ในแอป | ⚠️ ปล่อย DB error ดิบ |
| ลบ rec-origin → ควรบอก "ใช้ skip แทน" | ⚠️ ปล่อย error กลาง loop |
| Add/Edit เช็ค overlap ฝั่ง UI | ⚠️ เฉพาะ aeration ที่ DB กัน |
| การ์ด Other → Edit Schedule | ❌ filter `a.type==other` ตรงๆ → ได้รายการว่างเสมอ (bug) |
| แสดง `missed` | ⚠️ โหลดมาไม่ใช้ |