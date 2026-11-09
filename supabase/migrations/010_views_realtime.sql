-- 010: views แอปใช้ (§12) + Realtime publication + ตรวจ idempotency ฝั่ง DB
-- v_pond_cards, v_pond_status, v_activities, v_recommendations

-- ขั้น 1: เดินหน้าต่อ
-- v_activities: missed = pending ที่เลยเวลาแล้ว (คำนวณ ไม่เก็บ)
create or replace view v_activities as
select
  a.*,
  (a.status = 'pending' and a.start_time < now()) as missed
from activities a;

-- v_recommendations: parameter ที่เกี่ยวข้องมาจาก source (§12)
-- episode -> diagnostic_reports.parameter, prediction -> predictions.parameter, detector -> null
create or replace view v_recommendations as
select
  r.*,
  coalesce(
    (select array_agg(distinct p order by p)
     from (
       select d.parameter::text as p
       from recommendation_sources s
       join diagnostic_reports d on d.id = s.diagnostic_id
       where s.rec_id = r.id and s.source_type = 'episode'
       union
       select pr.parameter::text as p
       from recommendation_sources s
       join predictions pr on pr.id = s.prediction_id
       where s.rec_id = r.id and s.source_type = 'prediction'
     ) u),
    '{}'::text[]
  ) as parameters
from recommendations r;

-- rank severity ไว้ใช้สอง view ข้างล่าง
-- critical=4 > elevated_risk=3 > stress=2 > optimal=1
create or replace function private.severity_rank(s severity_level) returns integer
language sql immutable as $$
  select case s
    when 'critical' then 4
    when 'elevated_risk' then 3
    when 'stress' then 2
    else 1
  end;
$$;

-- v_pond_status: severity สูงสุดต่อบ่อ เสมอกันใช้ param_priority จาก app_config (§12)
create or replace view v_pond_status as
with latest_per_param as (
  select distinct on (s.pond_id, s.parameter)
    s.pond_id, s.parameter, s.severity, s.measured_at
  from severity_reports s
  order by s.pond_id, s.parameter, s.measured_at desc
),
ranked as (
  select
    l.*,
    private.severity_rank(l.severity) as rnk,
    coalesce(
      (select array_position(
        (select array_agg(e order by o)
         from jsonb_array_elements_text(
           (select value from app_config where key = 'param_priority')
         ) with ordinality as t(e, o)),
        l.parameter::text
      )),
      99
    ) as prio
  from latest_per_param l
)
select distinct on (pond_id)
  pond_id, parameter, severity, measured_at as updated_at
from ranked
order by pond_id, rnk desc, prio asc, measured_at desc;

-- v_pond_cards: ข้อมูลบ่อ + แถว status ตัวแทน (ponytail: ตอนนี้ = แถวเดียวกับ v_pond_status;
-- ถ้าแอปอยากได้ล่าสุดทุก parameter ค่อยขยายเป็น lateral join ทีหลัง)
create or replace view v_pond_cards as
select
  p.id as pond_id,
  p.name,
  p.species,
  p.biomass_kg,
  p.density_kg_m3,
  p.timezone,
  st.parameter as rep_parameter,
  st.severity as rep_severity,
  st.updated_at as last_updated
from ponds p
left join v_pond_status st on st.pond_id = p.id;

-- Realtime publication (§12): severity_reports, recommendations, notifications,
-- activities, diagnostic_reports, predictions — เพิ่มเฉพาะตารางที่ยังไม่อยู่
do $$
declare
  t text;
begin
  foreach t in array array[
    'severity_reports', 'recommendations', 'notifications',
    'activities', 'diagnostic_reports', 'predictions'
  ] loop
    if not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime'
        and schemaname = 'public'
        and tablename = t
    ) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end;
$$;

-- ตรวจ idempotency ฝั่ง DB (รันด้วยตา ไม่ใช่ test runner):
-- 1. severity_reports unique (pond_id, parameter, measured_at) → insert ซ้ำต้อง on conflict do nothing ได้
-- 2. recommendations dedupe partial unique → pending ซ้ำ key เดียวกันต้องถูกบล็อก
-- 3. predictions active partial unique → active ซ้ำ rule เดียวกันต้องถูกบล็อก
-- 4. apply_changeset เต็ม (upsert + StaleSnapshot + activityOps) อยู่ฝั่ง Python adapter ขั้น 2 —
--    test คู่ DB↔Python (§11) รันหลัง adapter เสร็จ ไม่ใช่ตอนนี้
