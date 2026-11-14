-- 011_device_secret.sql — [BUOY] E1: secret ต่อ device สำหรับ Edge Function /ingest
-- รันใน Dashboard SQL Editor
alter table devices add column if not exists secret text;

-- backfill device เก่าทั้งหมด (dev-315) — ค่า random, ไม่ hardcode ใน repo
update devices set secret = gen_random_uuid()::text where secret is null;

-- รับกุญแจ (ผลออกครั้งเดียวบนจอคุณ, อย่า commit ลง repo):
select device_id, secret from devices;
