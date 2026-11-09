-- 001: extensions, enums, app_config, helpers
-- CONFIG_RESOLUTION ข้อ 2 (10 ไฟล์), ข้อ 6 (pg_cron/pg_net บรรทัดแรก), ข้อ 3 (app_config)

create extension if not exists pg_cron with schema extensions;
create extension if not exists pg_net with schema extensions;
create extension if not exists citext;
create extension if not exists btree_gist;

-- enum types (ชื่อ DB สะอาด; python side แปลงผ่าน db/enum_map.py)
create type species as enum ('nile_tilapia');
create type parameter as enum ('DO', 'NH3', 'NO2_N', 'pH', 'Temperature', 'Salinity');
create type threshold_zone as enum ('optimal', 'stress', 'high_risk', 'critical');
create type severity_level as enum ('optimal', 'stress', 'elevated_risk', 'critical');
create type direction as enum ('low', 'high');
-- 6 kinds เท่านั้น ไม่มี other (CONFIG ข้อ 4)
create type activity_type as enum ('feeding', 'aeration', 'alkalinity', 'lime', 'probiotic', 'water_change');
create type activity_status as enum ('pending', 'done', 'skipped');
create type activity_source as enum ('user', 'recommendation');
create type urgency as enum ('urgent', 'non_urgent');
create type rec_status as enum ('pending', 'snoozed', 'applied', 'dismissed', 'expired');
create type apply_mode as enum ('fixed', 'pick_window');
create type pred_status as enum ('active', 'ended');
create type pred_end_reason as enum ('mitigated', 'conditions_gone', 'window_over');
create type diag_status as enum ('open', 'closed');
create type signal_source as enum ('episode', 'prediction', 'detector');
create type job_status as enum ('queued', 'running', 'done', 'failed');

-- updated_at trigger (ใช้กับทุก table ที่มี updated_at)
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- timezone validator
create or replace function is_valid_timezone(tz text) returns boolean
language sql stable as $$
  select tz is not null
    and exists (select 1 from pg_timezone_names where name = tz);
$$;

-- app_config: ค่าที่ trigger/แอปใช้ (สูตรวิเคราะห์อยู่ที่ config/constants.py — CONFIG ข้อ 3)
create table app_config (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

create trigger app_config_set_updated_at
  before update on app_config
  for each row execute function set_updated_at();

insert into app_config (key, value) values
  ('retro_window_days', '4'::jsonb),
  ('param_priority', '["DO","NH3","NO2_N","Temperature","pH","Salinity"]'::jsonb),
  ('tick_minutes', '30'::jsonb)
on conflict (key) do nothing;
