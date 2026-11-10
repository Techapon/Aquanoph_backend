-- 008: notifications (outbox + feed), push_tokens
-- DB_DESIGN §3.7, E2, W2
-- T5 (004) insert severityCritical ลงตารางนี้ runtime หลังไฟล์นี้แล้วเท่านั้น
-- push_eligible ตาม §3.7: severityCritical, urgentRecCreated, recChanged+urgency_raised (T8)

create table notifications (
  id bigint generated always as identity primary key,
  pond_id uuid not null references ponds (id),
  user_id uuid not null references profiles (user_id),  -- denormalize สำหรับ RLS
  kind text not null check (kind in (
    'urgentRecCreated', 'recChanged', 'recExpired', 'recUnsnoozed',
    'predictionEnded', 'activityReplaced', 'severityCritical'
  )),
  target_type text not null check (target_type in (
    'recommendation', 'prediction', 'activity', 'diagnostic', 'severity'
  )),
  target_id text not null,
  reason_key text,
  facts jsonb not null default '{}'::jsonb,
  text text,  -- จาก renderNotification (backend) / format (T5 DB trigger)
  push_eligible boolean not null default false,
  pushed_at timestamptz,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  -- push_eligible ได้เฉพาะ 3 เคส (§3.7)
  -- is not distinct from: กัน NULL hole (= ตอน reason_key null ได้ UNKNOWN แล้ว check ผ่าน)
  constraint push_eligible_only check (
    not push_eligible or kind in ('severityCritical', 'urgentRecCreated')
    or (kind = 'recChanged' and reason_key is not distinct from 'rec.changed.urgency_raised')
  )
);
create index notifications_user_idx on notifications (user_id, created_at desc);
create index notifications_pond_idx on notifications (pond_id, created_at desc);
-- W2 + retry: แถวที่ยังไม่ถูกส่ง (pushed_at is null) — index partial สำหรับ query ทุกนาที
create index notifications_push_pending_idx on notifications (created_at)
  where push_eligible and pushed_at is null;
create trigger notifications_set_updated_at
  before update on notifications
  for each row execute function set_updated_at();

create table push_tokens (
  id bigint generated always as identity primary key,
  user_id uuid not null references profiles (user_id),
  token text not null unique,
  platform text not null check (platform in ('fcm', 'apns')),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);
create index push_tokens_user_idx on push_tokens (user_id);
create trigger push_tokens_set_updated_at
  before update on push_tokens
  for each row execute function set_updated_at();

-- W2 retry: pg_cron ทุกนาที เช็คแถว push_eligible ที่ pushed_at is null
-- หมายเหตุ: Edge Function push-dispatch สร้างในขั้น 5 (คนละ repo) — cron นี้พร้อมใช้หลังนั้น
-- ตอนนี้แค่ log แถวค้าง (ponytail: สลับเป็น pg_net HTTP ยิง Edge Function ทันทีที่ deploy เสร็จ)
create or replace function cron_log_unpushed() returns void
language plpgsql as $$
declare
  v_count bigint;
begin
  select count(*) into v_count
  from notifications
  where push_eligible and pushed_at is null;
  -- ไม่มี edge function ใน migration นี้ — แค่ปลดสัญญาณ ไม่ยิง HTTP
  -- pg_net http จะถูกเพิ่มหลัง push-dispatch deploy แล้ว (ขั้น 5)
  if v_count > 0 then
    raise notice 'push pending: % rows', v_count;
  end if;
end;
$$;
select cron.schedule('push-retry', '* * * * *', $$select cron_log_unpushed();$$);
