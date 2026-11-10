# ขั้น 6 — cron-job.org keep-alive (P1 + P2)

สมัคร/ล็อกอิน **cron-job.org** (ฟรี ไม่ต้องผูกบัตร) แล้วสร้าง **2 jobs พร้อมกัน** (มติข้อ 26: ลืมไม่ได้)

## P1 — กัน Render sleep

| field | ค่า |
|---|---|
| Title | `render-health` |
| URL | `https://aquanoph-backend.onrender.com/health` |
| Schedule | Every 10 minutes (หรือ `*/10 * * * *`) |
| Request method | GET |
| Save & activate | ✓ |

- ยิงเฉพาะ `/health` เท่านั้น — **ห้ามชี้ endpoint ธุรกิจ** (`/apply` ฯลฯ) (มติข้อ 24)
- ดูได้จาก Execution history → ต้องเขียวทุกรอบ

## P2 — กัน Supabase project pause

| field | ค่า |
|---|---|
| Title | `supabase-ping` |
| URL | `https://axhgdirpwsevkilbjshu.supabase.co/rest/v1/app_config?select=key&limit=1` |
| Schedule | Every 12 hours (หรือ `0 3,15 * * *`) |
| Request method | GET |
| Headers | `apikey: <ANON/PUBLISHABLE KEY>` |

- **ใช้ anon/publishable key ไม่ใช่ service role** (มติข้อ 25) — เอาจาก Dashboard → Settings → API → `anon` `public`
- query เบาสุด (อ่าน 1 แถว) — ห้ามใช้ endpoint ที่แตะ DB หนัก (มติข้อ 24)

## ตรวจหลังตั้ง

- P1: cron-job.org → Execution history → เขียว + `GET /health` ตอบ 200
- P2: เขียว + ไม่ 401 (ถ้า 401 = ใส่ key ผิด)
- Render → Metrics: instance ไม่ sleep (มี request ทุก ~10 นาที)

## ทดสอบ cold path (ขั้น 7) — ทำหลังตั้ง P1/P2 แล้ว

1. **ปิด P1 ชั่วคราว** (pause job ใน cron-job.org)
2. รอ ≥15 นาที → Render sleep (หน้า status จะ `Asleep`)
3. เปิด P1 กลับ → ตัวเลข wake ≤60 วินาที (ดู log: `Application startup complete`)
4. เปิด P1 ค้างไว้ปกติ

ผล: ผ่านถ้า wake ≤60วิ — เสร็จแล้วให้บอกผลทั้ง 4 ขั้นตอน
