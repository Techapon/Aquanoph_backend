# คู่มือ Backend สำหรับ Flutter Frontend

> อ่านจากโค้ดจริงทั้งหมด (migration 001–012, `db/adapter.py`, `identity/**`, `main.py`) — ใช้แทน
> `APPLY_FROM_FONTEND_LOGIC.md` ที่มีข้อผิดพลาดบางจุด (แก้ให้แล้วใน §1.1)

---

## 0. ภาพรวม — ใครเขียนอะไร

```
┌─────────────┐  Supabase (PostgREST + RPC + Realtime)   ┌──────────────┐
│   Flutter   │ ───────────────────────────────────────► │   Postgres   │
│   App       │  อ่าน: views/tables/realtime             │  (RLS+guard) │
│             │  เขียน activity: 3 RPC เท่านั้น          │              │
│             │                                           │  trigger     │
│             │  เขียน rec (apply/snooze/dismiss):        │  enqueue     │
│             │  HTTP → Render backend ──────────────┐    │  job         │
└─────────────┘                                      ▼    └──────┬───────┘
                                          ┌──────────────────┐   │
                                          │ Render (Python)  │◄──┘
                                          │ analysis engine  │  worker poll
                                          └──────────────────┘
```

| เรื่อง | ช่องทาง | ทำไม |
|---|---|---|
| อ่านข้อมูลทุกอย่าง | Supabase views/tables | RLS แยกบ่ออัตโนมัติ |
| สร้าง/แก้/ลบ **activity ของ user** | 3 RPC (§4) | guard trigger บังคับกติกา |
| **apply/snooze/dismiss rec** | HTTP Render `/recommendations/...` (§5) | logic คำนวณอยู่ใน Python engine ที่เดียว |
| ฟังข้อมูลเปลี่ยน | Realtime (§3.3) | 6 ตารางใน publication |

**กติกาเหล็ก:** แอป **ไม่เคย** update ตาราง `recommendations` ตรง (RLS มีแต่ `select`), ไม่เคย insert activity
`source='recommendation'` (guard บล็อก), ไม่เคยลบ activity ของ rec — ทุกอย่างนั้นผ่าน HTTP apply เท่านั้น

---

## 1. ค่า/Enum ที่ใช้จริงทั้งหมด

### 1.1 `activity_type` — **6 ค่า, ไม่มี `other`/`unknown`**

```
feeding | aeration | alkalinity | lime | probiotic | water_change
```

- มติ CONFIG ข้อ 4: **ลบ `other` ออกจากระบบทั้งหมดแล้ว** — ส่งค่าอื่นเข้า RPC = cast error
- ปุ่ม "Other" บนแอป = กลุ่ม **alkalinity + lime + probiotic + water_change** (กรอง `type != feeding && type != aeration`) ไม่ใช่ type ชื่อ `other`
- ชื่อ DB เป็น snake_case: `water_change` (ไม่ใช่ `waterChange`)

### 1.2 `activity_status` — 3 ค่า

```
pending | done | skipped        (default: pending)
```

- `skipped` ≠ `pending`: aeration ที่ skipped **ไม่นับในกฎห้ามซ้อน** และไม่ดึงกลับเป็น pending ได้
- `done ↔ skipped` สลับได้; `done/skipped → pending` **โดน `status_rollback`** (ทั้ง engine และ DB)

### 1.3 `activity_source` — 2 ค่า

```
user | recommendation
```

- check คู่: `(source = 'recommendation') = (source_rec_id is not null)` — rec-origin ต้องมี `source_rec_id` เสมอ, user-origin ห้ามมี

### 1.4 `rec_status` / `urgency` / `apply_mode`

```
rec_status : pending | snoozed | applied | dismissed | expired
urgency    : urgent | non_urgent          (ส่งกลับจาก API เป็น camelCase? ไม่ — DB/PostgREST = snake_case)
apply_mode : fixed | pick_window
```

คู่ constraint ที่แอปควรรู้ (DB บังคับเอง ไม่ต้องเช็คซ้ำ):
- `snoozed` ⇔ `snooze_until is not null`
- `expired` ⇔ `expire_reason is not null` (`no_longer_applies` | `time_window_over`)
- `dismissed` ⇔ `dismissed_at is not null`
- **`urgent` ห้ามเป็น `snoozed`**
- `valid_until >= valid_from`

### 1.5 Check constraints ของ `activities` (ส่งผิด = DB error กลับมาเป็น `CoreFailure.databaseError`)

| constraint | ความหมาย → ฝั่ง form ต้องทำอะไร |
|---|---|
| `(type='aeration') = (end_time is not null)` | **aeration ต้องมี end_time; ชนิดอื่นห้ามมี** (feeding/water_change ส่ง end_time = error) |
| `end_time > start_time` (เมื่อมีค่า) | ช่วงเวลาต้องกลับด้านไม่ได้ |
| `(type='water_change') = (fraction is not null)` | **water_change ต้องมี fraction; ชนิดอื่นห้ามมี** |
| `fraction in (0, 1]` | เช่น 0.25 / 0.5 / 0.75 |
| `quantity_kg >= 0` (nullable) | feeding/alkalinity/lime/probiotic |
| aeration ห้ามซ้อน | `exclude gist` ต่อ `pond + [start,end)` เฉพาะ `type='aeration' and status<>'skipped'`, **`deferrable initially deferred`** → ชนตอน **commit ของ batch** (RPC ทั้งชุด fail ทุกอย่าง — all-or-nothing) |
| retro window **4 วัน** | `start_time >= now()-4วัน` ทั้ง **insert และ update** — ย้อนหลังเกินนี้ = `outside_retro_window` |
| immutable | `id, pond_id, source, source_rec_id, created_at` แก้ไม่ได้ (`immutable_field`) |
| rec-origin ลบไม่ได้ | `source='recommendation'` + DELETE = `recommendation_activity_not_deletable` — **ใช้ skip แทน** |

> **ช่องว่างที่รู้อยู่:** ไม่มี check บังคับ `aeration → end_time` แถวที่ end เป็น null (ถ้าหลุดเข้ามา) จะทำให้ engine
> ไม่นับเป็น fixed + range เปิดทะลุ — แอปส่ง end เสมอจึงรอด, backend จะเพิ่ม check ทีหลัง

---

## 2. อ่านข้อมูล (Read)

### 2.1 Views ที่ให้ใช้

| view | คอลัมน์เพิ่มจากตาราง | ใช้ที่ไหน |
|---|---|---|
| `v_activities` | `missed` (computed: `pending and start_time < now()`) | การ์ด home + checklist — **โหลดมาแล้วแต่ยังไม่แสดง, จะแสดงเมื่อไหร่ก็แค่อ่าน field นี้** |
| `v_recommendations` | `parameters text[]` (รวม parameter จาก diagnostic/prediction sources) | การ์ด rec — ไม่ต้อง join เอง |
| `v_pond_status` | severity สูงสุดต่อ b่อ (tie-break ตาม param_priority ใน `app_config`) | banner สถานะบ่อ |
| `v_pond_cards` | การ์ด 3 ใบ (feeding/aeration/other) + สรุป | Pond Home |

กรอง/เรียง: caller จัดการเอง (เช่น `getDay` → `start_time >= from AND < to`, เรียง `start_time`) —
**boundary เป็น UTC แล้ว**, แปลง timezone ด้วย `ponds.timezone` (`Asia/Bangkok`) ก่อนส่ง

### 2.2 ตารางที่อ่านตรงได้ (RLS กรองเฉพาะบ่อที่เป็นเจ้าของเอง)

`ponds`, `activities`, `sensor_readings` (เฉพาะ rows ผ่าน `analysis_start_at`),
`severity_reports`, `diagnostic_reports`, `predictions`, `recommendations`,
`recommendation_sources`, `notifications`, `activity_series`, `profiles`

**`recommendations` อ่านอย่างเดียว** — ไม่มี grant insert/update ให้ `authenticated`

### 2.3 ตารางที่ app เขียนได้ (นอกเหนือจาก 3 RPC)

| ตาราง | เขียนอะไรได้ |
|---|---|
| `notifications` | **เฉพาะ `read_at`** (`grant update (read_at)`) — ทำเครื่องอ่านแล้ว |
| `push_tokens` | insert/update own (platform: `fcm`/`apns`) |
| ที่เหลือ | อ่านอย่างเดียว / ผ่าน RPC เท่านั้น |

### 2.4 ฟอร์แมตเวลา

- DB ทุก timestamp เป็น **UTC** (PostgREST คืน ISO แบบ `+00`)
- แปลง本地 ↔ UTC ในแอปเอง (fixed offset ของ timezone บ่อ)
- HTTP apply รับ `chosenTime`/`snoozeUntil` เป็น ISO string (มี `Z` หรือ offset ก็ได้) — ฟอร์แมตผิด = **400** ไม่ใช่ 500

---

## 3. Realtime

Publication มี 6 ตาราง:

```
severity_reports, recommendations, notifications,
activities, diagnostic_reports, predictions
```

- subscribe ด้วย filter `pond_id=eq.<id>` แบบเดียวกับ PostgREST
- **PondHomeProvider**: ตาราง `activities` → debounce 2s → `load()` ใหม่ (pattern ที่ใช้อยู่แล้ว ถูกแล้ว)
- **ActivityProvider ใน sheet**: ไม่ต้อง subscribe (เปิดสั้นๆ, `onSaved` ยิง load เอง) — ถูกแล้ว
- ตาราง rec/severity เปลี่ยนจาก worker ฝั่ง backend ทุก ~7-30 วิ → ถ้ามีหน้าจอ rec ให้ subscribe `recommendations` ด้วย (เดิม app อาจแค่ refetch — เพิ่ม channel ได้เลย)

---

## 4. เขียน Activity — 3 RPC (ทั้งหมด `security invoker` = RLS + guard ทำงาน)

### 4.1 `save_checklist(pond_id uuid, changes jsonb) → void`

Batch **all-or-nothing** (transaction เดียว, fail = ไม่มีอะไรถูกเขียน):

```jsonc
[
  { "op": "create", "activity": { "type":"feeding", "startTime":"...Z",
      "quantityKg": 3.5, "status":"pending" } },
  { "op": "update", "activity": { "id":"<uuid>", "status":"done" } },
  { "op": "delete", "activity": { "id":"<uuid>" } }   // หรือใช้ key "id" ระดับบนก็ได้ตามที่แอปส่ง
]
```

- `update` เปลี่ยนได้เฉพาะ: `status, startTime, endTime, quantityKg, fraction` (field อื่นส่งมาก็ถูก ignore)
- op ไม่รู้จัก → `unknown_op: ...`
- ไม่ใช่เจ้าของบ่อ → `not_pond_owner`
- สร้าง source บังคับเป็น `'user'` ใน RPC เอง (JSON ส่ง `source` อะไรมาไม่เกี่ยว)

### 4.2 `upsert_activity(pond_id uuid, activity jsonb) → text` (คืน id)

- **ไม่ส่ง `id` = สร้างใหม่เสมอ** (uuid ใหม่), ส่ง `id` + มีอยู่แล้ว = upsert (แก้ status/time/qty/fraction เท่านั้น)
- ใช้ตอน Add Activity / Apply-to-other-day
- คืน `id` ให้เก็บไว้ (หรือจะ refetch ก็ได้)

### 4.3 `delete_activity(activity_id text) → void`

- ลบทีละรายการ; RLS เช็คเจ้าของบ่อเอง
- rec-origin → โดน guard `recommendation_activity_not_deletable`
- **แนะนำให้ UI เช็ค `originRecId != null` ก่อนกดลบ** แล้วเปลี่ยนข้อความเป็น "ใช้ Skip แทน" (ตอนนี้ปล่อย error ดิบ — gap §8)

### 4.4 ทุก write สำเร็จ → `load()` ซ้ำทันที (ทำอยู่แล้ว ถูกต้อง)

---

## 5. Recommendation — HTTP API ทั้งหมด (Render)

Base: `https://aquanoph-backend.onrender.com`
Header ทุก endpoint: `Authorization: Bearer <supabase access_token>` (JWT จาก `auth.getSession`)

> ownership เช็คจาก token (`ponds.user_id = sub`) — **ไม่เชื่อ pond_id ใน body** ส่งมาก็ไร้ผล

### 5.1 Endpoint

| Method+Path | Body | คืน |
|---|---|---|
| `POST /recommendations/{id}/preview` | `{ chosenTime?: ISO }` | `{status, reason, summary}` — **ไม่เขียนอะไรเลย** |
| `POST /recommendations/{id}/apply` | `{ chosenTime?: ISO }` | `{status, reason, summary}` — เขียนจริง + enqueue |
| `POST /recommendations/{id}/snooze` | `{ snoozeUntil*: ISO }` | `{status:"snoozed"}` |
| `POST /recommendations/{id}/dismiss` | `{ note?: string }` | `{status:"dismissed"}` |
| `GET /health` | — | `{status:"ok"}` (ไม่ต้อง token) |

HTTP error: `400` bad ISO field · `401` ไม่มี/token ตาย · `403` ไม่ใช่เจ้าของ · `404` rec ไม่มี ·
**`409` stale snapshot** (apply ระหว่างที่ engine เขียน rec อยู่ → reload แล้วให้ user กดใหม่)

### 5.2 Gate ที่ทุก apply/preview ผ่านก่อน (เรียงลำดับ)

1. `status` ต้อง `pending` หรือ `snoozed` → ไม่งั้น `rejected / not_pending`
2. `now <= validUntil` → ไม่งั้น `rejected / expired`
3. `apply_mode = pick_window` ต้องส่ง `chosenTime` → ไม่งั้น `rejected / missing_time`
4. `chosenTime` ∈ `[validFrom, validUntil]` → ไม่งั้น `rejected / time_outside_window`

`snooze` เพิ่ม: ต้อง `pending` + `non_urgent` + `now < snoozeUntil <= validUntil` (ผิด = 400)
`dismiss`: ได้เฉพาะ `pending`/`snoozed` (ผิด = 400)

### 5.3 `status` ที่ apply/preview คืน — ทั้ง 3 ค่า

| status | ความหมาย | summary ที่มา |
|---|---|---|
| `applied` | สำเร็จ (ใน preview = "ถ้ากด apply จะสำเร็จ") | AERATE: `{created:[(s,e)...], modified:[{activityId,before,after}...], kept:[...], coveredByDone:bool}`<br>Single: `{created:[(at,end)]}` |
| `needsDecision` | มี activity ชน → **ต้องถาม user แล้วยิง apply อีกครั้ง** | `{conflicts: [activityId,...]}` |
| `rejected` | ติด gate → ดู `reason` | `{}` |

> **สำคัญ:** `preview` คืน status เหมือน `apply` เป๊ะ (รวม `applied`) — ต่างกันที่ **preview ไม่เขียนอะไร**;
> ความหมายของ `applied` ใน preview = "แผนผ่าน" ไม่ใช่ "เขียนแล้ว"

### 5.4 `reason` ที่ `rejected` คืน (7 ค่า — ควร map เป็นข้อความ user)

| reason | เกิดเมื่อ | ข้อความที่ควรโชว์ (ตัวอย่าง) |
|---|---|---|
| `not_pending` | rec ไป applied/dismissed/expired แล้ว | "คำแนะนำนี้ถูกจัดการไปแล้ว" |
| `expired` | เลย `validUntil` | "หมดเวลาดำเนินการแล้ว" |
| `missing_time` | pick_window ไม่ส่ง chosenTime | "กรุณาเลือกเวลา" |
| `time_outside_window` | เลือกเวลาผิดช่วง | "เวลาต้องอยู่ในช่วงที่กำหนด" |
| `invalid_window` | ช่วงเวลาคำนวณไม่ได้ (edge case) | "ลองใหม่อีกครั้ง" |
| `aeration_overlap` | มี aeration ซ้อนใน window (summary มี `conflicts`) | "มีงานเติมอากาศอยู่แล้ว" |
| — (`needsDecision`) | activity ชน (summary มี `conflicts`) | "มีงานเดิมอยู่ — ยืนยันการแทนที่?" |

### 5.5 พฤติกรรมแยกตาม `entry_id` (3 ตัว)

**AERATE (เติมอากาศ) — merge อัตโนมัติ, ไม่เคย `needsDecision`:**

1. คำนวณช่วงต้องเติม `R = [rStart, rEnd]`
   - มี prediction: `rStart = max(now, riskStart − lead)`, `rEnd = max(riskEnd)`
   - มีแค่ episode: `[now, now + diagDuration]`
2. `fixed` = aeration ที่ **done แล้ว** หรือ **rec อื่นจองไว้** → หักออกจาก R
3. สร้าง activity ใหม่ **เฉพาะช่องว่าง** (เศษ < 15 นาทีถูกตัดทิ้ง)
4. aeration **pending ของ user** ที่ทับ R → ถูก **ตัด/ย่อ/แยก** ออก (notification `activity.replaced.by_recommendation` พร้อม before/after ให้โชว์ diff)
5. ช่องว่าง = 0 → `applied` เปล่า + `coveredByDone: true` (ไม่สร้างอะไร — ถูกแล้ว)
6. **กฎลำดับสิทธิ์: `done` > `rec` > `user-pending`** (user-pending ไม่เคยชนะ)

**WATER_CHANGE / ADD_ALKALINITY / อื่นๆ — conflict = ถามก่อน:**

- เวลาเริ่ม: `urgent` → `now` ทันที (ไม่ต้องส่ง chosenTime) · ไม่ urgent → `chosenTime`
- **ชน** = มี activity **ชนิดเดียวกัน** ที่ `status != skipped` และ `startTime` ∈ `[validFrom, validUntil]`
  - preview → `needsDecision` + `conflicts`
  - apply (`confirmed=true`) → `applied` (สร้างซ้อนถือว่ายืนยันแล้ว) — **ไม่มี parameter `confirmed` ใน request**, `apply` endpoint = confirmed เอง

**หลัง apply สำเร็จ (ทุก entry):**
- rec → `applied` (terminal)
- activity ใหม่: `source='recommendation'`, `source_rec_id=<rec.id>`, `status='pending'`
- id ฝั่ง backend รูป `act:{recId}:{index}` (deterministic)
- backend enqueue `activityEvent` เอง → worker ประมวลใน ~วินาที (แอปแค่ reload)

### 5.6 Flow ที่ frontend ควร implement (สรุปเป็นลำดับ)

```
กด Apply
 ├─ preview(chosenTime?)            ← เสมอ
 │   ├─ rejected    → toast reason
 │   ├─ applied     → ถาม confirm สรุป summary → apply(chosenTime?)
 │   └─ needsDecision → dialog แสดง conflicts (โหลด activity ตาม id) →
 │                       ยืนยัน → apply(chosenTime?)
 └─ apply
     ├─ applied     → reload + toast (formatApplySummary)
     ├─ rejected    → toast reason (อาจ expired ระหว่างรอ)
     └─ HTTP 409     → reload snapshot แล้วเริ่ม preview ใหม่
```

ปุ่ม **Apply to other day (1/7/30)** เป็นคนละระบบกับ apply rec — ใช้ `upsert_activity` ตาม §4.2
(pre-flight `fetchDay` + conflictDays ที่ app ทำอยู่ = ถูกแล้ว, แต่ดู §8)

### 5.7 หลัง apply — ยกเลิก/แก้

- rec ที่ `applied` **เปลี่ยนกลับไม่ได้** (ไม่มี unapply endpoint)
- สิ่งที่ทำได้: activity ของ rec → เปลี่ยนสถานะเป็น **`skipped`** (ผ่าน `save_checklist`/`upsert_activity`)
  = "คราวนี้ไม่เอา" — **ลบไม่ได้** (guard)
- ถ้าสาเหตุยังอยู่ tick ถัดไประบบ **สร้าง rec ใหม่เสนอเอง** (safety net — skip ≠ ปิดปากถาวร)
- rec ที่ `applied` ยัง **แก้เวลา/สถานะ activity ได้** ตามกฎปกติ (immutable คือ source/source_rec_id ไม่ใช่เวลา)

---

## 6. การแสดงผล — กติกาที่ควรทำตาม

| เรื่อง | กฎ |
|---|---|
| rec-origin row | tint + AppliedBadge + dot urgency (อ่าน `recUrgencyById`) — ทำอยู่แล้ว ✅ |
| dot urgency | ต่อ rec ที่ distinct 1 ตัว (ไม่ใช่ต่อ row) — ทำอยู่แล้ว ✅ |
| `missed` | computed column พร้อมใช้ (`v_activities.missed`) — ตัดสินใจโชว์เมื่อไหร่ก็ได้ |
| `skipped` | ต่างจาก pending ตรง: ไม่นับ overlap, ไม่ถูก resurrect, ควรแสดงผลต่าง (เช่น line-through) |
| การ์ด Other | กรอง `type ∉ {feeding, aeration}` (**ไม่ใช่ `type == other`** — ไม่มี type นี้, bug §8) |
| rec card | อ่านจาก `v_recommendations` (มี `parameters[]` ให้แล้ว) |

---

## 7. Error mapping (ทุกช่องทาง → UI)

| ช่องทาง | error ที่ app ได้ | ควรทำ |
|---|---|---|
| 3 RPC | PostgREST error code/message → `CoreFailure.databaseError` | **map ข้อความดิบ** (`outside_retro_window`, `status_rollback`, `recommendation_activity_not_deletable`, `invalid_source`, constraint check) เป็นข้อความ user แทน "Save failed" ตายตัว |
| HTTP apply | `{status:"rejected", reason}` / `needsDecision` | §5.4 table |
| HTTP apply | 409 | reload + retry flow |
| HTTP apply | 401 | token หมดอายุ → `refreshSession` แล้วยิงใหม่ |

---

## 8. Gap ที่ยังค้าง (เทียบ spec — ยืนยันจากโค้ดแล้ว)

| # | เรื่อง | สถานะ |
|---|---|---|
| 1 | ปุ่ม Skip ก่อน Save (§146) | ❌ ไม่มี — `skipped` เขียนผ่าน RPC ได้แล้ว แค่ไม่มีปุ่ม |
| 2 | Repeat + `series_id` (§145) | ❌ ไม่แตะ (ตาราง `activity_series` มี check ของตัวเอง: aeration⇔duration_minutes) |
| 3 | retro window validate ในแอป | ⚠️ ปล่อย DB error ดิบ → map ข้อความ (§7) |
| 4 | ลบ rec-origin กลาง loop | ⚠️ เช็ค `originRecId` ก่อนลบ (§4.3) |
| 5 | Add/Edit เช็ค overlap ฝั่ง UI | ⚠️ เฉพาะ aeration ที่ DB กัน; ชนิดอื่นระบบ apply จัดการให้เอง |
| 6 | การ์ด Other filter `type==other` | ❌ **bug จริง** — ได้รายการว่างเสมอ → เปลี่ยนเป็น `type != feeding && type != aeration` |
| 7 | แสดง `missed` | ⚠️ โหลดมาไม่ใช้ (field พร้อมแล้ว) |
| 8 | `fetchDay` error → คืน `[]` เงียบ | ⚠️ วันดูว่างผิด → ควร propagate error |
| 9 | ปุ่ม label "Feed the shrimp" | ❌ label ผิด species (ปลานิล) |

---

## 9. ตัวอย่าง request/response จริง

### preview AERATE (มี prediction)

```http
POST /recommendations/rec:f156d24b-...:AERATE:2026-11-15T.../preview
Authorization: Bearer eyJ...
Content-Type: application/json

{}
```
```json
{
  "status": "applied",
  "reason": null,
  "summary": {
    "created": [["2026-11-15T01:00:00", "2026-11-15T05:00:00"]],
    "modified": [{"activityId": "…", "before": ["…","…"], "after": ["…","…"]}],
    "kept": [["2026-11-15T01:00:00", "2026-11-15T03:00:00"]],
    "coveredByDone": false
  }
}
```

### preview WATER_CHANGE ที่ชน

```json
{ "status": "needsDecision", "reason": null,
  "summary": { "conflicts": ["<activity-uuid>"] } }
```
→ user ยืนยัน → `apply` body เดิม → `"status": "applied"`

### apply ที่หมดอายุ

```json
{ "status": "rejected", "reason": "expired", "summary": {} }
```

### snooze ที่ illegal (urgent)

HTTP 400 `{"detail": "only pending non-urgent recs can be snoozed"}`
(หมายเหตุ: DB check กันไว้แล้วซ้ำ — urgent+snoozed ข้ามไม่ได้แม้ยิง SQL ตรง)

---

## 10. Checklist ตรวจตัวเองฝั่ง app

- [ ] ส่ง `type` ได้แค่ 6 ค่า (ไม่มี `other`/`unknown`), `water_change` มาพร้อม `fraction`
- [ ] form feeding/alkalinity/... **ไม่ส่ง `endTime`**; aeration ส่งเสมอ
- [ ] ไม่ update `recommendations` ตรง (ใช้ HTTP เท่านั้น)
- [ ] ไม่ insert activity `source='recommendation'` เอง (ใช้ HTTP apply)
- [ ] ลบ activity เช็ค `originRecId` ก่อน → ข้อความ "ใช้ skip"
- [ ] apply flow: preview → (needsDecision dialog) → apply, รองรับ 409 retry
- [ ] map `reason` ทั้ง 7 + error จาก RPC เป็นข้อความ user
- [ ] การ์ด Other กรองด้วย `!= feeding && != aeration`
- [ ] ทุก write → reload (ทำอยู่แล้ว) + realtime activities (ทำอยู่แล้ว)

---

*ไฟล์นี้อ่านจาก: `001_extensions_enums.sql`, `006_activities.sql`, `009_rls.sql`, `010_views_realtime.sql`,
`config/constants.py`, `identity/recommendation/apply_plan.py`, `services/activity_edit.py`, `main.py`
(ณ 2026-11-15 — ถ้า backend เปลี่ยน contract ให้ทวนไฟล์นี้อีกครั้ง)*
