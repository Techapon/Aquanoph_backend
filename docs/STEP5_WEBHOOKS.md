# ขั้น 5 — Webhooks + Edge Function (push-dispatch)

## 5.1 Edge Function `push-dispatch` (โค้ดอยู่ใน repo แล้ว)

ที่ไหน: Supabase Dashboard → Edge Functions → **Deploy a new function**
- Name: `push-dispatch`
- วางโค้ดจาก [`supabase/functions/push-dispatch/index.ts`](../supabase/functions/push-dispatch/index.ts) (หรือ deploy ผ่าน CLI: `supabase functions deploy push-dispatch`)
- Body parser: ใช้ `req.json()` ตามที่เขียนไว้ — ไม่ต้องตั้งอะไรเพิ่ม

### Secret (บังคับ 1 ตัว)
**FIREBASE_SERVICE_ACCOUNT** = JSON string ของ Firebase service account:
1. Firebase Console → Project settings → **Service accounts** → Generate new private key (ได้ไฟล์ `.json`)
2. คัดลอก **ทั้งไฟล์** เป็นบรรทัดเดียว (หรือ base64?) — ใส่เป็น secret value ตรง ๆ (JSON string)
3. ตั้งที่: Dashboard → Edge Functions → push-dispatch → **Secrets** → `FIREBASE_SERVICE_ACCOUNT`

### ต้องมีก่อน ( prerequisite )
- Firebase project + เปิด **Cloud Messaging** (Project settings → Cloud Messaging)
- มือถือตัว test register token เข้า `push_tokens` (user_id ตรงกับ notification)

## 5.2 W1 — analysis_jobs → /wake

ที่ไหน: Dashboard → Database → **Webhooks**
1. **Create webhook**
2. Name: `W1-wake`
3. Table: `analysis_jobs`
4. Events: **Insert** (勾 Insert อย่างเดียว — ตาม §8)
5. Type: **HTTP Request**
6. Method: `POST`
7. URL: `https://aquanoph-backend.onrender.com/wake`
8. Headers: ไม่ต้องมี (ไม่มี auth ฝั่ง `/wake`)
9. Save

ผล: ทุกครั้งมีงานเข้าคิว → Render ตื่น poll ทันที (เสริมจาก poll 7 วิ)

## 5.3 W2 — notifications (push_eligible) → push-dispatch

1. **Create webhook**
2. Name: `W2-push`
3. Table: `notifications`
4. Events: **Insert**
5. Type: **HTTP Request** → `POST`
6. URL: `https://axhgdirpwsevkilbjshu.supabase.co/functions/v1/push-dispatch`
7. Headers: `Authorization: Bearer <ANON_KEY>` (Edge Function รับ anon key ได้ตาม default)
8. Save

## 5.4 ทดสอบ W2 (retry path ไม่ต้องรอ W2)

ยิงซ้ำจาก pg_cron ที่ตั้งไว้ใน 008 (`push-retry` ทุกนาที) จะ retry แถว `pushed_at is null` อยู่แล้ว — ถ้า Edge Function deploy แล้ว แถว notification ใหม่จะถูกส่งอัตโนมัติ

ตรวจผล: `select id, kind, text, pushed_at from notifications order by created_at desc limit 5;`
