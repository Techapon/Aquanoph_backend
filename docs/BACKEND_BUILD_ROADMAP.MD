ขั้นตอนสำหรับ `DB_DESIGN_supabase_v0_2` — อ้างอิงมติทั้งหมดจาก `CONFIG_RESOLUTION_v1.md` (single source of truth)

## ขั้น 1 — ทำ DB migration

**ที่ไหน:** Supabase dashboard → SQL Editor. หรือ Supabase CLI (`supabase migration new <ชื่อ>`)

**งานแรกสุด — ปิด §14 ก่อนรัน (มติข้อ 8: ใช้ค่าที่ DB_DESIGN 提出 ทั้ง 6 ข้อ ไม่มีคำถามค้าง):**
1. `pond_states` มีจริง — insert-only snapshot ของบ่อ ให้ `severity_reports` อ้าง FK
2. user เขียน activity ตรงผ่าน RLS + guard trigger + RPC (ไม่ผ่าน Python API)
3. host = Render free tier (ปิดแล้ว — ดูขั้น 4)
4. `late` = เฉพาะผิดลำดับเท่านั้น (เก่ากว่า reading ที่ประมวลผลแล้ว) ไม่นับ "ช้าเกิน X นาที"; เก็บ `received_at` ไว้วัดย้อนหลัง
5. push Critical เฉพาะตอน "เพิ่งเข้า" Critical (เปลี่ยนจากไม่ใช่ Critical → Critical) ไม่ส่งซ้ำทุก reading
6. เพิ่มคอลัมน์ `dismissed_at`/`dismiss_note` ที่ `recommendations` — เขียนผ่าน Python API เท่านั้น ไม่ผ่าน ChangeSet

**งานก่อนไฟล์ migration ที่แตะ enum (มติข้อ 1):**
- สร้าง `enum_map.py` — ตารางแปลงคู่เดียวของทุก member (`tem`→`Temperature`, `NO2_N`, `"hight risk"`→`high_risk`, `waterChange`→`water_change`, `nonUrgent`→`non_urgent`, `pickWindow`→`pick_window`) + test ไป-กลับครบทุก member

**ทำอะไร:** รันตามลำดับ §15 เป็น **10 ไฟล์ เรียงเลข** (`001_...sql` … `010_...sql`) รันทีละไฟล์ ห้ามรวม ห้ามข้าม
1. `001_...sql` — **บรรทัดแรกของไฟล์:** `create extension pg_cron; create extension pg_net;` (มติข้อ 6) แล้วตามด้วย extension อื่น (`citext`, `btree_gist`) + enum + `app_config` + `is_valid_timezone` + trigger `set_updated_at`
2. `002_...sql` — `profiles` + trigger จาก `auth.users`
3. `003_...sql` — แก้ `sensor_readings` เพิ่ม column + trigger `late` + สร้าง `ponds`, `pond_states`, `pond_analysis_state` + column grants
4. `004_...sql` — `severity_reports` + trigger severity Critical
5. `005_...sql` — `recommendations` (+ `dismissed_at`/`dismiss_note`), `predictions`, `diagnostic_reports`, `recommendation_sources`
6. `006_...sql` — `activity_series`, `activities` + constraints + guard triggers + RPC — **ไม่มี `title` column, 6 activity kind เท่านั้น** (มติข้อ 4)
7. `007_...sql` — `analysis_jobs`, `analysis_runs`, `enqueue_analysis`, cron
8. `008_...sql` — `notifications`, `push_tokens`
9. `009_...sql` — RLS ทุก table + view + Realtime publication
10. `010_...sql` — test ชุดเทียบกฎ DB ↔ Python (§11) + test idempotency ของ `apply_changeset`

**อย่างไร:** เช็ค error แต่ละไฟล์ก่อนไปไฟล์ถัดไป — FK ต้องพึ่ง table ก่อนหน้า. **test คู่ (มติข้อ 7):** เคสเดียวกันยิงผ่าน Python `validateActivityEdit` และยิงตรง SQL ต้อง reject ตรงกัน. **กติกาค่า config (มติข้อ 3):** สูตรวิเคราะห์อยู่ที่ `config/constants.py` เท่านั้น; ค่าที่ trigger/แอปใช้ (`retro_window`, `param_priority`, `tick_minutes`) อยู่ที่ `app_config` เท่านั้น; ห้ามซ้ำที่ — มี test เทียบกันกัน drift.

---

## ขั้น 2 — เขียน DB adapter (Phase 8)

**ที่ไหน:** repo นี้ สร้างไฟล์ใหม่ `db/adapter.py` (+ `db/enum_map.py` ถ้ายังไม่สร้างจากขั้น 1)

**ทำอะไร:** สองฟังก์ชันหลัก
- `load_snapshot(pond_id, now)` → ดึง `ponds`, `pond_states`, `sensor_readings` (**`WHERE late = false`** ตั้งแต่ query), `activities` ฯลฯ แปลงเป็น `PondSnapshot`
- `apply_changeset(...)` → เขียน `diagnostic_reports`, `predictions`, `recommendations`, `notifications` ใน **1 transaction เดียว**

**อย่างไร:**
- **Driver เขียน = `asyncpg` เท่านั้น** (มติข้อ 9) — supabase-py/PostgREST ทำ real transaction หลาย statement ไม่ได้; อ่านอย่างเดียวจะใช้ supabase-py ก็ได้
- **StaleSnapshot (มติข้อ 11):** เทียบ `updated_at` ของ record กับ snapshot ก่อนเขียน — ไม่ตรง → rollback transaction + requeue job
- **skip `late` (มติข้อ 12):** `WHERE late = false` ตั้งแต่ query ดึง reading ไม่ filter ทีหลังใน Python
- **ทีละ 1 job (มติข้อ 13):** ดึง 1 job → ประมวลจบ → เขียน ChangeSet จบ → ค่อยดึงงานถัดไป; ห้าม batch รวม trigger kind
- **text cache (มติข้อ 5):** `plan_text`/`text` ใน report เติมตอน `apply_changeset` เท่านั้น ผ่านฟังก์ชันกลาง `render_plan_text(rec)` จุดเดียว
- Enum python ↔ postgres แปลงผ่าน `enum_map.py` + test ไป-กลับทุก member
- **Pin Python 3.11.x ผ่าน `runtime.txt`** (มติข้อ 14) — ห้ามใช้ syntax ใหม่กว่า 3.11
- เขียน test ยิง Supabase จริง (หรือ local) เช็ค apply ซ้ำ id เดิมไม่สร้างซ้ำ (idempotent)

---

## ขั้น 3 — เติม endpoint + worker loop

**ที่ไหน:** repo นี้ (`main.py` + `requirements.txt`)

**งานแรกสุด (มติข้อ 17):** สร้าง `main.py` (FastAPI) + `requirements.txt` — dependencies ขั้นต่ำ: `fastapi`, `uvicorn`, `asyncpg`, `pyjwt`

**ทำอะไร:** เพิ่ม route
- `GET /health` → `return {"status": "ok"}` บรรทัดเดียว **ห้ามแตะ DB ห้าม import DB client ในฟังก์ชันนี้** (มติข้อ 16)
- `POST /wake` → ปลุก worker loop ให้ poll เร็วขึ้น (ไม่บังคับสำเร็จ)
- `POST /recommendations/{id}/apply`
- `POST /recommendations/{id}/preview`
- `POST /recommendations/{id}/snooze`
- `POST /recommendations/{id}/dismiss`

**Worker loop (มติข้อ 18):** background task (`asyncio.create_task` ตอน startup) รันใน process เดียวกับ API — poll `analysis_jobs` ทุก 5-10 วินาที

**อย่างไร:** `/apply` กับ `/preview` ต้อง **verify JWT ด้วย env `SUPABASE_JWT_SECRET`** (มติข้อ 15) ก่อน — เช็คว่า user เป็นเจ้าของบ่อจริง (อย่าเชื่อ `pond_id` จาก body) แล้วค่อยเรียก `buildApplyPlan` → เขียนผ่าน adapter ขั้น 2. `/snooze` `/dismiss` เรียก `snoozeRec`/`dismissRec` เช่นกัน.

---

## ขั้น 4 — Deploy ขึ้น Render

**ที่ไหน:** render.com → New → Web Service → เชื่อม GitHub repo

**ทำอะไร:** ตั้ง
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Python: 3.11 (จาก `runtime.txt`)
- Plan: Free

**อย่างไร:** ไปที่ Environment tab ใส่ secret 3 ตัว (มติข้อ 19 — ห้าม commit ลง repo):
1. `SUPABASE_URL`
2. `SUPABASE_SERVICE_ROLE_KEY`
3. `SUPABASE_JWT_SECRET`

(`PORT` Render ให้เอง) กด deploy. ดู log รอ build เสร็จ. ทดสอบ `curl https://<app>.onrender.com/health` ต้องได้ 200 ไว.

---

## ขั้น 5 — ตั้ง Webhook ใน Supabase

**งานแรก — สร้าง Edge Function `push-dispatch` (มติข้อ 22):** เขียนใน Supabase project **คนละ repo/คนละภาษา** (Deno/TypeScript ไม่ใช่ Python repo นี้) ให้เสร็จก่อนตั้ง W2. Secret W2 เก็บใน **Supabase Vault** ไม่ใช่ env ธรรมดา (มติข้อ 23); retry เองจากแถว `pushed_at is null` ทุกนาที

**ที่ไหน:** Supabase dashboard → Database → Webhooks

**ทำอะไร:** สร้าง 2 ตัว (ต้องมี URL Render จริงจากขั้น 4 ก่อน — มติข้อ 21)
- W1: trigger ตอน `analysis_jobs` insert/update → ยิงไป `https://<app>.onrender.com/wake`
- W2: trigger ตอน `notifications` (`push_eligible`) → ยิงไป Edge Function `push-dispatch`

**อย่างไร:** เลือก HTTP Request type, method POST, วาง URL, save.

---

## ขั้น 6 — ตั้ง cron-job.org

**ที่ไหน:** cron-job.org (สมัครไว้แล้ว เข้า dashboard)

**ทำอะไร:** สร้าง 2 job **ตั้งคู่กันเสมอ (มติข้อ 26):**
- **P1:** `GET /health` ของ Render ทุก ~10 นาที — **ชี้ endpoint นี้เท่านั้น ห้ามชี้ endpoint ธุรกิจ** (มติข้อ 24)
- **P2:** ping Supabase เบาๆ (query table เล็กผ่าน PostgREST) วันละ 1-2 ครั้ง — **ใช้ anon/publishable key ไม่ใช่ service role** (มติข้อ 25). P2 กัน Supabase pause → pg_cron หยุดด้วย

**อย่างไร:** กด Create cronjob → ใส่ URL → ตั้ง interval → save → รอรอบแรก รันแล้วเช็ค execution history ว่าเขียว.

---

## ขั้น 7 — ทดสอบ cold path + idempotency

**ที่ไหน:** terminal + Render dashboard (log tab)

**เงื่อนไข:** ตั้ง pinger (ขั้น 6) เรียบร้อยแล้วเท่านั้น (มติข้อ 20)

**ทำอะไร:**
- ปิด pinger ชั่วคราว → ปล่อย Render ไม่มี traffic เกิน 15 นาที → ยืนยันว่า sleep จริง
- เปิด pinger กลับ → ดู log ว่า worker loop ตื่นและกลับมา poll ปกติ **ภายใน ≤ 60 วินาที** (มติข้อ 27)
- ยิง `/apply` endpoint ด้วย id เดิมซ้ำ 2 ครั้ง → เช็ค `revised_at` ของ record ว่าเป็น update ไม่ใช่ insert แถวใหม่ (มติข้อ 28)

**อย่างไร:** ทดสอบ sleep ตอนปิด pinger ก่อน แล้วค่อยเปิดกลับ. idempotency ยิง curl เดิมซ้ำแล้วดู `revised_at`.
