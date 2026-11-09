-- 009: RLS ทุก table + grants (§10)
-- service role ข้าม RLS อยู่แล้ว — policies นี้คุมเฉพาะ authenticated/anon
-- ไม่มี function body ใหม่ (ใช้ private.owns_pond จาก 006)

-- แก้ bug จาก 008: notifications/push_tokens ไม่มีคอลัมน์ updated_at ตามสเปก
-- (trigger set_updated_at ที่ 008 ติดไว้จะ crash ตอน UPDATE — ลบออก)
drop trigger if exists notifications_set_updated_at on notifications;
drop trigger if exists push_tokens_set_updated_at on push_tokens;

-- เปิด RLS ทุก table
alter table profiles enable row level security;
alter table ponds enable row level security;
alter table pond_states enable row level security;
alter table pond_analysis_state enable row level security;
alter table severity_reports enable row level security;
alter table sensor_readings enable row level security;
alter table activities enable row level security;
alter table activity_series enable row level security;
alter table diagnostic_reports enable row level security;
alter table predictions enable row level security;
alter table recommendations enable row level security;
alter table recommendation_sources enable row level security;
alter table notifications enable row level security;
alter table push_tokens enable row level security;
alter table analysis_jobs enable row level security;
alter table analysis_runs enable row level security;
alter table app_config enable row level security;
alter table devices enable row level security;

-- ============================ profiles ============================
grant select, update on profiles to authenticated;
create policy profiles_read_own on profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy profiles_update_own on profiles
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- ============================ ponds ============================
grant select, insert on ponds to authenticated;
-- update 3 คอลัมน์ให้ไปแล้วที่ 003 (column grant) — guard กันคอลัมน์อื่น
create policy ponds_read_own on ponds
  for select to authenticated using (user_id = (select auth.uid()));
create policy ponds_insert_own on ponds
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy ponds_update_own on ponds
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
-- ไม่มี delete policy = ไม่มีหน้าลบบ่อ (§3.3)

-- ============================ pond_states / analysis_state ============================
grant select on pond_states to authenticated;
create policy pond_states_read_own on pond_states
  for select to authenticated using (private.owns_pond(pond_id));

grant select on pond_analysis_state to authenticated;
create policy pond_analysis_state_read_own on pond_analysis_state
  for select to authenticated using (private.owns_pond(pond_id));

-- ============================ severity_reports ============================
grant select on severity_reports to authenticated;
create policy severity_reports_read_own on severity_reports
  for select to authenticated using (private.owns_pond(pond_id));

-- ============================ sensor_readings ============================
grant select on sensor_readings to authenticated;
create policy sensor_readings_read_own on sensor_readings
  for select to authenticated using (
    exists (
      select 1 from ponds p
      where p.device_id = sensor_readings.device_id
        and p.user_id = (select auth.uid())
        and sensor_readings.measured_at >= p.analysis_start_at
    )
  );

-- ============================ activities / series ============================
grant select, insert, update, delete on activities to authenticated;
create policy activities_all_own on activities
  for all to authenticated
  using (private.owns_pond(pond_id))
  with check (private.owns_pond(pond_id));
-- guard trigger (006) บังคับ source='user' + retro window + immutable ต่ออีกชั้น

grant select, insert, update, delete on activity_series to authenticated;
create policy activity_series_all_own on activity_series
  for all to authenticated
  using (private.owns_pond(pond_id))
  with check (private.owns_pond(pond_id));

-- ============================ analysis results ============================
grant select on diagnostic_reports to authenticated;
create policy diagnostic_reports_read_own on diagnostic_reports
  for select to authenticated using (private.owns_pond(pond_id));

grant select on predictions to authenticated;
create policy predictions_read_own on predictions
  for select to authenticated using (private.owns_pond(pond_id));

grant select on recommendations to authenticated;
create policy recommendations_read_own on recommendations
  for select to authenticated using (private.owns_pond(pond_id));

grant select on recommendation_sources to authenticated;
create policy recommendation_sources_read_own on recommendation_sources
  for select to authenticated using (
    exists (select 1 from recommendations r where r.id = rec_id and private.owns_pond(r.pond_id))
  );

-- ============================ notifications ============================
grant select on notifications to authenticated;
-- update เฉพาะ read_at (notifications ไม่มี updated_at ตามสเปก §3.7)
grant update (read_at) on notifications to authenticated;
create policy notifications_read_own on notifications
  for select to authenticated using (user_id = (select auth.uid()));
create policy notifications_read_receipt on notifications
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- ============================ push_tokens ============================
grant select, insert, update, delete on push_tokens to authenticated;
create policy push_tokens_all_own on push_tokens
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- ============================ jobs / runs / config ============================
-- analysis_jobs, analysis_runs: ไม่มี grant = user อ่าน/เขียนไม่ได้ (§10)
revoke all on analysis_jobs from authenticated, anon;
revoke all on analysis_runs from authenticated, anon;

-- app_config: อ่านได้อย่างเดียว (ไม่มี insert/update/delete grant)
grant select on app_config to authenticated, anon;
create policy app_config_read_all on app_config
  for select to authenticated, anon using (true);

-- devices: ทะเบียนอุปกรณ์ — user อ่านได้ (ต้องรู้ device_id ตอนกรอก), เขียนไม่ได้
grant select on devices to authenticated;
create policy devices_read_all on devices
  for select to authenticated using (true);
