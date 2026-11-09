# Config Resolution v1 — จุดชนที่ตกลงแล้ว

สถานะ: ตกลงแล้ว 28/28 ข้อ (27 ข้อตามที่เสนอ, ข้อ 4 แก้ไข, ข้อ 8 อิงตาม DB_DESIGN §14)
อ้างอิง: `DB_DESIGN_supabase_v0_2.md`, สรุป config 28 ข้อจากบทสนทนาก่อนหน้า

ไฟล์นี้คือ **single source of truth ของการตัดสินใจ** ที่เหลือจากนี้คือ agent ต้องไปปรับ `BACKEND_BUILD_ROADMAP.md` และ `AGENT_CONTEXT.md` (และไฟล์อื่นถ้ามี) ให้ตรงกับที่นี่ — ดูคำสั่งท้ายไฟล์

---

## ขั้น 1 — DB migration

| # | จุดชน | มติ |
|---|---|---|
| 1 | Enum โค้ด ≠ Enum DB | สร้าง `enum_map.py` ไฟล์เดียว เก็บคู่แปลงทุกตัว (`tem`→`Temperature`, `NO2_N`, `"hight risk"`→`high_risk`, `waterChange`→`water_change`, `nonUrgent`→`non_urgent`, `pickWindow`→`pick_window`) + test ไป-กลับทุก member |
| 2 | FK บังคับลำดับ | migration แยก 10 ไฟล์ เลขนำหน้า (`001_...sql` ... `010_...sql`) รันทีละไฟล์ ห้ามรวม |
| 3 | `app_config` vs `AnalysisConfig` | สูตรวิเคราะห์ → `constants.py` เท่านั้น. ค่าที่ trigger/แอปใช้ (retro_window, param_priority, tick_minutes) → `app_config` เท่านั้น. ห้ามซ้ำที่ + test เทียบ drift |
| 4 | **`activities.title`** | **(แก้จากที่เสนอ)** ลบ `title`/`other` ออกจากทั้งระบบ — ไม่ใช้ activity kind `other` ใน project นี้ ตัด field `title text` ออกจาก DB schema (`activities` table) และไม่ต้องเพิ่ม field ใน `Activity` model ฝั่ง Python. เหลือ 6 kind ตามเดิม |
| 5 | `plan_text` / `text` ใน report | Adapter เขียนตอน `apply_changeset` เท่านั้น ผ่านฟังก์ชันกลาง `render_plan_text(rec)` จุดเดียว |
| 6 | pg_cron C1–C3 | `create extension pg_cron; create extension pg_net;` เป็นบรรทัดแรกของไฟล์ `001` ยืนยันด้วย P2 pinger (ขั้น 6) |
| 7 | Guard trigger ซ้ำกับ Python | test คู่ใน CI: เคสเดียวกันยิงผ่าน Python validate และยิงตรง SQL ต้อง reject ตรงกัน |
| 8 | **§14 คำถาม 6 ข้อ** | **(ตามที่ DB_DESIGN เสนอ — ใช้ค่าเสนอทั้งหมด)**: ① `pond_states` มีจริง เป็น insert-only snapshot ② user เขียน activity ตรงผ่าน RLS + guard trigger + RPC (ไม่ผ่าน Python API) ③ host = Render free tier (ปิดแล้ว) ④ `late` = เฉพาะผิดลำดับเท่านั้น ไม่นับ "ช้าเกิน X นาที" (เก็บ `received_at` ไว้วัดย้อนหลัง) ⑤ push Critical เฉพาะตอน "เพิ่งเข้า" Critical (เปลี่ยนจากไม่ใช่ Critical → Critical) ไม่ส่งซ้ำทุก reading ⑥ เพิ่มคอลัมน์ `dismissed_at`/`dismiss_note` เขียนผ่าน API เท่านั้น ไม่ผ่าน ChangeSet |

## ขั้น 2 — DB adapter

| # | จุดชน | มติ |
|---|---|---|
| 9 | supabase-py ไม่รองรับ transaction | เขียนทั้งหมดใช้ `asyncpg` อ่านอย่างเดียวจะใช้ supabase-py ก็ได้ |
| 10 | ขัด AGENT_CONTEXT "no new dep" | Phase 8 ยกเว้นกฎนี้โดยเฉพาะ — ต้องแก้ข้อความใน `AGENT_CONTEXT.md` ให้ชัด |
| 11 | StaleSnapshot | เทียบ `updated_at` ของ record กับ snapshot ก่อนเขียน ไม่ตรง → rollback transaction + requeue job |
| 12 | Worker ต้อง skip `late` | ใส่ `WHERE late = false` ตั้งแต่ query ดึง reading ไม่ filter ทีหลังใน Python |
| 13 | Job หลาย kind รันทีละ trigger | worker ดึง 1 job → ประมวลจบ → เขียน ChangeSet จบ → ค่อยดึงงานถัดไป ห้าม batch รวม trigger kind |
| 14 | Python version | pin `3.11.x` ผ่าน `runtime.txt` หรือ Render env `PYTHON_VERSION` ห้ามใช้ syntax > 3.11 |

## ขั้น 3 — Endpoints

| # | จุดชน | มติ |
|---|---|---|
| 15 | JWT secret หายจาก roadmap | เพิ่ม env `SUPABASE_JWT_SECRET` ตอน deploy Render verify ทุก request เข้า `/apply` `/preview` |
| 16 | `/health` ต้องเบาสุด | `return {"status":"ok"}` บรรทัดเดียว ห้าม import DB client ในฟังก์ชันนี้ |
| 17 | `main.py` ว่าง + ไม่มี `requirements.txt` | สร้างสองไฟล์นี้ก่อนอย่างอื่นในขั้น 3 (fastapi, uvicorn, asyncpg, pyjwt ขั้นต่ำ) |
| 18 | Worker loop ไม่ได้เขียนใน roadmap | เพิ่ม background task (`asyncio.create_task` ตอน startup) รันใน process เดียวกับ API |

## ขั้น 4 — Render

| # | จุดชน | มติ |
|---|---|---|
| 19 | Secret ที่ต้องใส่ | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (`PORT` Render ให้เอง) ห้าม commit |
| 20 | Free tier sleep 15 นาที | ตั้ง pinger (ขั้น 6) ก่อน test cold path (ขั้น 7) เสมอ |

## ขั้น 5 — Webhooks

| # | จุดชน | มติ |
|---|---|---|
| 21 | W1 → `/wake` | ตั้งหลัง Render มี URL จริงเท่านั้น |
| 22 | W2 → `push-dispatch` ยังไม่มี | เขียน Edge Function (Deno/TS) ใน Supabase project แยกก่อน ค่อยตั้ง W2 |
| 23 | Secret W2 | เก็บใน Supabase Vault ไม่ใช่ env ธรรมดา retry เองจาก `pushed_at is null` ทุกนาที |

## ขั้น 6 — cron-job.org

| # | จุดชน | มติ |
|---|---|---|
| 24 | P1 | ชี้ `GET /health` Render เท่านั้น ทุก ~10 นาที ห้ามชี้ endpoint ธุรกิจ |
| 25 | P2 ใช้ key ผิด | ใช้ anon/publishable key ไม่ใช่ service role วันละ 1-2 ครั้ง |
| 26 | P2 คู่กับ pg_cron | ตั้งพร้อมกับ P1 เสมอ ลืมไม่ได้ (ดูคำอธิบายเหตุผลในบทสนทนา) |

## ขั้น 7 — ทดสอบ

| # | จุดชน | มติ |
|---|---|---|
| 27 | Cold path test | ปิด pinger ชั่วคราว → ยืนยัน sleep จริง → เปิดกลับ → wake ต้อง ≤ 60 วิ |
| 28 | Idempotency test | ยิง `/apply` id เดิม 2 ครั้ง → เช็ค `revised_at` update ไม่ใช่ insert แถวใหม่ |

---

## สรุปสิ่งที่เปลี่ยนจาก draft ก่อนหน้า

- **ข้อ 4:** ไม่เพิ่ม field `title` ใน `Activity` model — แทนที่ด้วยการ **ลบ** `title`/`other` ออกจาก schema และระบบทั้งหมด เพราะ project นี้ไม่ใช้ activity kind `other`
- **ข้อ 8:** ยืนยันใช้ค่าที่ DB_DESIGN §14 เสนอไว้ทั้ง 6 ข้อ ไม่มีข้อไหนเปลี่ยน

---

## คำสั่งสำหรับ Agent — ไฟล์ที่ต้องแก้ต่อ

เมื่ออ่านไฟล์นี้จบแล้ว ให้ไปแก้ไฟล์ต่อไปนี้ให้สอดคล้องกับมติด้านบนทั้งหมด:

### 1. `BACKEND_BUILD_ROADMAP.md`
- จัดลำดับขั้นใหม่ตาม 7 ขั้นที่กำหนดไว้ (DB migration → DB adapter → Endpoints → Render deploy → Webhooks → cron-job.org → ทดสอบ) ถ้ายังไม่ตรงลำดับนี้ให้ปรับ
- **ขั้น 1:** เพิ่มขั้นตอนย่อย "ปิด §14 ก่อนรัน migration" เป็นงานแรกสุด (ตอนนี้ปิดแล้วตามมติข้อ 8 ด้านบน — ใส่ค่าที่ตกลงไว้ลงในเอกสารเลย ไม่ต้องเว้นเป็นคำถามแล้ว) และระบุให้แยกไฟล์ migration เป็น 10 ไฟล์เรียงเลข (ข้อ 2)
- **ขั้น 1:** ลบทุกจุดที่พูดถึง `activities.title` หรือ activity kind `other` ออกจาก roadmap ทั้งหมด (ข้อ 4 ที่แก้ใหม่)
- **ขั้น 1:** เพิ่มงานย่อย "สร้าง `enum_map.py` + test ไป-กลับ" เป็นงานที่ต้องทำก่อนไฟล์ migration ที่แตะ enum (ข้อ 1)
- **ขั้น 2:** ระบุชัดว่า driver เขียน = `asyncpg` เท่านั้น (ไม่ใช่ supabase-py) และเพิ่มงานย่อย StaleSnapshot check, `WHERE late = false` ที่ query, worker ประมวลทีละ 1 job (ข้อ 9, 11, 12, 13)
- **ขั้น 2:** เพิ่มบรรทัดระบุ pin Python 3.11.x ผ่าน `runtime.txt` (ข้อ 14)
- **ขั้น 3:** เพิ่มงานย่อย "สร้าง `main.py` + `requirements.txt`" เป็นงานแรกของขั้นนี้ (ข้อ 17) และ "เขียน worker loop เป็น background task" (ข้อ 18) และ "เพิ่ม env `SUPABASE_JWT_SECRET`" (ข้อ 15)
- **ขั้น 4:** list secret ที่ต้องใส่ให้ครบ 3 ตัว (ข้อ 19)
- **ขั้น 5:** เพิ่มงานย่อย "สร้าง Edge Function `push-dispatch` ก่อนตั้ง W2" เป็นงานแยกต่างหาก ระบุว่าอยู่คนละ repo/คนละภาษา (ข้อ 22)
- **ขั้น 6:** ระบุชัดว่า P2 ต้องใช้ anon/publishable key ไม่ใช่ service role (ข้อ 25) และตั้งคู่กับ P1 เสมอ (ข้อ 26)

### 2. `AGENT_CONTEXT.md`
- แก้กฎ "stdlib + pytest only, no new dependencies" ให้มีข้อยกเว้นชัดเจนสำหรับ Phase 8 (DB adapter) — ระบุว่าอนุญาต `asyncpg`, `fastapi`, `uvicorn`, `pyjwt` เป็นต้น พร้อมเหตุผล (ต้องต่อ DB จริง, ต้องมี real transaction ซึ่ง PostgREST ของ supabase-py ทำไม่ได้) (ข้อ 9, 10)
- เพิ่มบรรทัดระบุ Python target version = 3.11 ชัดเจน (เครื่อง dev อาจเป็น 3.14 แต่ deploy ต้อง 3.11) (ข้อ 14)
- ลบ/แก้ทุกจุดที่อ้างถึง `activities.title` หรือ activity kind `other` ให้ตรงกับมติใหม่ (ข้อ 4)
- ถ้ามีส่วนอธิบาย enum ของ activity/recommendation ให้ชี้ไปที่ `enum_map.py` เป็นแหล่งความจริงเดียว (ข้อ 1)

### 3. ไฟล์อื่น (ถ้ามี)
- ถ้ามีไฟล์ schema/model อื่นที่อ้างถึง `activities.title`, kind `other`, หรือ driver DB (เช่น `models.py`, `schema.sql` เดิม) ให้ agent ไล่ grep หาและแก้ให้ตรงกับมติข้อ 4 และ 9 ด้วย
- ถ้ามีไฟล์ README หรือ setup instruction ที่พูดถึง dependency list แบบ "stdlib only" ให้แก้พร้อมกับ `AGENT_CONTEXT.md`

**กฎรวม:** ไฟล์นี้ (`CONFIG_RESOLUTION_v1.md`) คือของจริง ถ้าไฟล์อื่นขัดกับที่นี่ ให้แก้ไฟล์อื่นตามนี้ ไม่ใช่กลับกัน
