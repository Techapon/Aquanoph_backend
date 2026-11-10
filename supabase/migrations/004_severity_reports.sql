-- 004: severity_reports + T5 trigger severityCritical (มติข้อ 8.5: แจ้งเฉพาะตอน "เพิ่งเข้า" Critical)
-- DB_DESIGN §3.4, T5

create table severity_reports (
  id bigint generated always as identity primary key,
  pond_id uuid not null references ponds (id),
  pond_state_id uuid not null references pond_states (id),
  parameter parameter not null,
  measured_at timestamptz not null,
  value numeric,
  zone threshold_zone not null,
  direction direction,
  severity severity_level not null,
  -- Recovery Hold: zone optimal แต่ severity ยัง stress
  recovering boolean generated always as (zone = 'optimal' and severity = 'stress') stored,
  symptom text,
  reason text,
  guidance text,
  engine_version text not null,
  reading_id bigint references sensor_readings (id),
  -- idempotency: รันซ้ำ reading เดิม → on conflict do nothing (§3.4)
  unique (pond_id, parameter, measured_at)
);
create index severity_reports_lookup_idx on severity_reports (pond_id, parameter, measured_at desc);
create index severity_reports_reading_idx on severity_reports (reading_id);

-- insert-only ห้าม update/delete (Rule 6) — dev/service ไว้ cleanup ได้
create trigger severity_reports_no_update_delete
  before update or delete on severity_reports
  for each row execute function forbid_mutation();

-- T5: insert notification severityCritical เมื่อ "เพิ่งเข้า" Critical
-- เพิ่งเข้า = severity = critical และ reading ก่อนหน้าของ (pond, parameter) ไม่ใช่ critical (หรือไม่มี)
-- notifications สร้างใน 008 — plpgsql ไม่ resolve ตอน create, runtime หลัง migrate ครบ
create or replace function severity_reports_notify_critical() returns trigger
language plpgsql as $$
declare
  prev_severity severity_level;
  owner_id uuid;
  prev_count integer;
begin
  if new.severity <> 'critical' then
    return null;
  end if;

  select s.severity into prev_severity
  from severity_reports s
  where s.pond_id = new.pond_id
    and s.parameter = new.parameter
    and s.measured_at < new.measured_at
  order by s.measured_at desc
  limit 1;

  -- แถวใหม่สุด (ไม่ใช่ reading ที่ order เพี้ยน): นับแถวใหม่กว่าในตารางด้วย
  -- กัน insert ย้อนหลัง: ถ้ามีแถวใหม่กว่าอยู่แล้ว แถวใหม่นี้ไม่ใช่ "ล่าสุด" → ห้ามแจ้ง
  select count(*) into prev_count
  from severity_reports s
  where s.pond_id = new.pond_id
    and s.parameter = new.parameter
    and s.measured_at > new.measured_at;

  if prev_count > 0 then
    return null;
  end if;

  -- เปลี่ยนจากไม่ใช่ Critical → Critical (prev null = ก่อนหน้าไม่เคยมี → เข้า Critical)
  if prev_severity is not null and prev_severity = 'critical' then
    return null;  -- ค้างอยู่แล้ว ไม่ส่งซ้ำทุก reading
  end if;

  select p.user_id into owner_id from ponds p where p.id = new.pond_id;
  if owner_id is null then
    return null;
  end if;

  insert into notifications (pond_id, user_id, kind, target_type, target_id, reason_key, facts, text, push_eligible)
  values (
    new.pond_id,
    owner_id,
    'severityCritical',
    'severity',
    new.id::text,
    'severity.critical.entered',
    jsonb_build_object(
      'parameter', new.parameter,
      'value', new.value,
      'direction', case when new.direction is not null then new.direction::text end,
      'measuredAt', new.measured_at
    ),
    format('Critical level detected for %s.', new.parameter),
    true  -- push_eligible (§3.7): severityCritical เสมอ
  );
  return null;
end;
$$;
create trigger severity_reports_critical_notify
  after insert on severity_reports
  for each row execute function severity_reports_notify_critical();
