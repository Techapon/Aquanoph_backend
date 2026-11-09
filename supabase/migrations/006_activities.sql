-- 006: activity_series, activities + constraints + guard triggers + RPC
-- DB_DESIGN §3.5, R1 — ไม่มี title/other (มติข้อ 4), guard คู่กับ validateActivityEdit (มติข้อ 7)

create schema private;
grant usage on schema private to authenticated, anon, service_role;

-- helper: owns_pond (§10) — stable security definer, auth.uid() ห่อ subquery ให้ planner cache
create or replace function private.owns_pond(p_pond_id uuid) returns boolean
language sql stable security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from ponds p
    where p.id = p_pond_id and p.user_id = (select auth.uid())
  );
$$;

-- helper: retro floor จาก app_config (มติข้อ 3) — trigger guard อ่านผ่านตัวนี้
create or replace function private.retro_floor() returns timestamptz
language sql stable security definer
set search_path = public, pg_temp
as $$
  select now() - (select (value #>> '{}')::integer from app_config where key = 'retro_window_days') * interval '1 day';
$$;

-- ============================ activity_series ============================

create table activity_series (
  id uuid primary key default gen_random_uuid(),
  pond_id uuid not null references ponds (id),
  type activity_type not null,
  local_start_time time not null,
  duration_minutes integer,
  quantity_kg numeric,
  fraction numeric,
  first_local_date date not null,
  ended_at timestamptz,
  generated_through date not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((type = 'aeration') = (duration_minutes is not null)),
  check (duration_minutes is null or duration_minutes > 0),
  check ((type = 'water_change') = (fraction is not null)),
  check (fraction is null or (fraction > 0 and fraction <= 1)),
  check (quantity_kg is null or quantity_kg >= 0)
);
create trigger activity_series_set_updated_at
  before update on activity_series
  for each row execute function set_updated_at();

-- C2: สร้างรายการ pending ล่วงหน้า 7 วันตาม timezone ของบ่อ (§3.5)
-- ชน aeration เดิม → ข้ามวันนั้น ไม่ล้มทั้งงาน
create or replace function renew_activity_series() returns void
language plpgsql as $$
declare
  s record;
  v_pond_tz text;
  v_local_date date;
  v_start timestamptz;
  v_end timestamptz;
begin
  for s in select * from activity_series where ended_at is null loop
    select p.timezone into v_pond_tz from ponds p where p.id = s.pond_id;
    for v_local_date in
      select d::date
      from generate_series(s.generated_through + 1, current_date + 7) as d
      where d::date >= s.first_local_date
    loop
      v_start := (v_local_date + s.local_start_time)::timestamp at time zone v_pond_tz;
      v_end := case
        when s.type = 'aeration' then v_start + make_interval(mins => s.duration_minutes)
      end;
      begin
        insert into activities (id, pond_id, type, status, start_time, end_time, quantity_kg, fraction, source, series_id)
        values (gen_random_uuid()::text, s.pond_id, s.type, 'pending', v_start, v_end, s.quantity_kg, s.fraction, 'user', s.id);
      exception
        when exclusion_violation or unique_violation then
          null;  -- ข้ามวันนั้น (aeration ซ้อน) — ponytail: log ลง analysis_runs ค่อยเพิ่มถ้าต้อง debug
      end;
    end loop;
    update activity_series set generated_through = greatest(generated_through, current_date + 7) where id = s.id;
  end loop;
end;
$$;

-- ============================ activities ============================

create table activities (
  id text primary key,  -- user: gen_random_uuid()::text · backend: act:{recId}:{i}
  pond_id uuid not null references ponds (id),
  type activity_type not null,
  status activity_status not null default 'pending',
  start_time timestamptz not null,
  end_time timestamptz,
  quantity_kg numeric,
  fraction numeric,
  source activity_source not null default 'user',
  source_rec_id text references recommendations (id),
  series_id uuid references activity_series (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- validity คู่กับ Activity.__post_init__ (§11)
  check ((type = 'aeration') = (end_time is not null)),
  check (end_time is null or end_time > start_time),
  check ((type = 'water_change') = (fraction is not null)),
  check (fraction is null or (fraction > 0 and fraction <= 1)),
  check (quantity_kg is null or quantity_kg >= 0),
  check ((source = 'recommendation') = (source_rec_id is not null))
);

-- aeration ซ้อนกันบล็อกเด็ดขาด — deferred เพราะ Apply D15 ลบ/สร้างใน transaction เดียว (§3.5)
alter table activities
  add constraint activities_aeration_no_overlap
  exclude using gist (pond_id with =, tstzrange(start_time, end_time) with &&)
  where (type = 'aeration' and status <> 'skipped')
  deferrable initially deferred;

create index activities_pond_start_idx on activities (pond_id, start_time);
create index activities_pond_type_status_idx on activities (pond_id, type, status);
create index activities_source_rec_idx on activities (source_rec_id);
create trigger activities_set_updated_at
  before update on activities
  for each row execute function set_updated_at();

-- guard คู่ขนานกับ validateActivityEdit (§3.5) — ใช้กับ role แอปเท่านั้น ไม่บล็อก service/dev
-- reason strings ตรงกับ services/activity_edit.py เพื่อ test เทียบคู่ (มติข้อ 7)
create or replace function activities_guard() returns trigger
language plpgsql as $$
declare
  v_floor timestamptz;
  r record;
begin
  if current_user not in ('authenticated', 'anon') then
    return case when tg_op = 'DELETE' then old else new end;
  end if;

  v_floor := private.retro_floor();

  if tg_op = 'INSERT' then
    if new.source <> 'user' then
      raise exception 'invalid_source: user cannot create recommendation activity';
    end if;
    if new.start_time < v_floor then
      raise exception 'outside_retro_window';
    end if;
    return new;

  elsif tg_op = 'UPDATE' then
    if row(new.id, new.pond_id, new.source, new.source_rec_id, new.created_at)
       is distinct from row(old.id, old.pond_id, old.source, old.source_rec_id, old.created_at) then
      raise exception 'immutable_field';
    end if;
    if old.status in ('done', 'skipped') and new.status = 'pending' then
      raise exception 'status_rollback';
    end if;
    if old.start_time < v_floor or new.start_time < v_floor then
      raise exception 'outside_retro_window';
    end if;
    return new;

  else -- DELETE
    if old.source <> 'user' then
      raise exception 'recommendation_activity_not_deletable';
    end if;
    if old.start_time < v_floor then
      raise exception 'outside_retro_window';
    end if;
    return old;
  end if;
end;
$$;
create trigger activities_guard_row
  before insert or update or delete on activities
  for each row execute function activities_guard();

-- T2: AFTER STATEMENT enqueue activityEvent ด้วย min(t_from) (§3.5, special part §2)
-- insert = เวลาใหม่, delete = เวลาเก่า, update = ต่ำสุดของเก่า/ใหม่ — batch = งานเดียว
create or replace function activities_enqueue_ins() returns trigger
language plpgsql as $$
declare
  v_t timestamptz;
begin
  select min(start_time) into v_t from new_rows;
  if v_t is not null then
    perform enqueue_analysis(x.pond_id, 'activityEvent', v_t)
    from (select distinct pond_id from new_rows) x;
  end if;
  return null;
end;
$$;
create trigger activities_enqueue_ai
  after insert on activities
  referencing new table as new_rows
  for each statement execute function activities_enqueue_ins();

create or replace function activities_enqueue_del() returns trigger
language plpgsql as $$
declare
  v_t timestamptz;
begin
  select min(start_time) into v_t from old_rows;
  if v_t is not null then
    perform enqueue_analysis(x.pond_id, 'activityEvent', v_t)
    from (select distinct pond_id from old_rows) x;
  end if;
  return null;
end;
$$;
create trigger activities_enqueue_ad
  after delete on activities
  referencing old table as old_rows
  for each statement execute function activities_enqueue_del();

create or replace function activities_enqueue_upd() returns trigger
language plpgsql as $$
declare
  v_t timestamptz;
begin
  select least(min(n.start_time), min(o.start_time)) into v_t
  from (select start_time from new_rows) n
  cross join (select start_time from old_rows) o;
  -- least(ไม่ใช่ min) — min ข้ามกลุ่มผิด: ต้องการ min ของ union ทั้งสองฝั่ง
  select min(t) into v_t from (
    select start_time as t from new_rows
    union all
    select start_time as t from old_rows
  ) u;
  if v_t is not null then
    perform enqueue_analysis(x.pond_id, 'activityEvent', v_t)
    from (
      select pond_id from new_rows
      union
      select pond_id from old_rows
    ) x;
  end if;
  return null;
end;
$$;
create trigger activities_enqueue_au
  after update on activities
  referencing new table as new_rows old table as old_rows
  for each statement execute function activities_enqueue_upd();

-- ============================ RPC (R1) ============================

-- สร้างบ่อ (T4 trigger ฝั่ง DB ทำ pond_states + analysis_state + enqueue เอง)
create or replace function create_pond(
  p_name text,
  p_area_m2 numeric,
  p_avg_depth_m numeric,
  p_stocking_count integer,
  p_avg_weight_g numeric,
  p_stocking_date date,
  p_device_id text,
  p_timezone text
) returns uuid
language plpgsql security invoker set search_path = public, pg_temp as $$
declare
  v_id uuid;
begin
  insert into ponds (user_id, name, area_m2, avg_depth_m, stocking_count, avg_weight_g, stocking_date, device_id, timezone)
  values (auth.uid(), p_name, p_area_m2, p_avg_depth_m, p_stocking_count, p_avg_weight_g, p_stocking_date, p_device_id, p_timezone)
  returning id into v_id;
  return v_id;
end;
$$;

-- save_checklist: 1 transaction all-or-nothing (§7 ข้อ 2)
-- changes: [{"op":"create","activity":{...}}, {"op":"update","activity":{...}}, {"op":"delete","id":"..."}]
-- pond_id บังคับจาก argument — ไม่เชื่อจาก body
create or replace function save_checklist(p_pond_id uuid, p_changes jsonb) returns void
language plpgsql security invoker set search_path = public, pg_temp as $$
declare
  v_change jsonb;
  v_act jsonb;
begin
  if not private.owns_pond(p_pond_id) then
    raise exception 'not_pond_owner';
  end if;

  for v_change in select * from jsonb_array_elements(p_changes) loop
    if v_change->>'op' = 'create' then
      v_act := v_change->'activity';
      insert into activities (id, pond_id, type, status, start_time, end_time, quantity_kg, fraction, source)
      values (
        coalesce(v_act->>'id', gen_random_uuid()::text),
        p_pond_id,
        (v_act->>'type')::activity_type,
        coalesce((v_act->>'status')::activity_status, 'pending'),
        (v_act->>'startTime')::timestamptz,
        (v_act->>'endTime')::timestamptz,
        (v_act->>'quantityKg')::numeric,
        (v_act->>'fraction')::numeric,
        'user'
      );
    elsif v_change->>'op' = 'update' then
      v_act := v_change->'activity';
      -- แก้ได้เฉพาะ field ที่สเปกอนุญาต — id/pond/source/created_at คงเดิม (guard คุม)
      update activities set
        status = coalesce((v_act->>'status')::activity_status, status),
        start_time = coalesce((v_act->>'startTime')::timestamptz, start_time),
        end_time = case when v_act ? 'endTime' then (v_act->>'endTime')::timestamptz else end_time end,
        quantity_kg = case when v_act ? 'quantityKg' then (v_act->>'quantityKg')::numeric else quantity_kg end,
        fraction = case when v_act ? 'fraction' then (v_act->>'fraction')::numeric else fraction end
      where id = v_act->>'id' and pond_id = p_pond_id;
    elsif v_change->>'op' = 'delete' then
      delete from activities where id = v_change->>'id' and pond_id = p_pond_id;
    else
      raise exception 'unknown_op: %', v_change->>'op';
    end if;
  end loop;
end;
$$;

create or replace function upsert_activity(p_pond_id uuid, p_activity jsonb) returns text
language plpgsql security invoker set search_path = public, pg_temp as $$
declare
  v_id text := coalesce(p_activity->>'id', gen_random_uuid()::text);
begin
  if not private.owns_pond(p_pond_id) then
    raise exception 'not_pond_owner';
  end if;
  insert into activities (id, pond_id, type, status, start_time, end_time, quantity_kg, fraction, source, source_rec_id)
  values (
    v_id,
    p_pond_id,
    (p_activity->>'type')::activity_type,
    coalesce((p_activity->>'status')::activity_status, 'pending'),
    (p_activity->>'startTime')::timestamptz,
    (p_activity->>'endTime')::timestamptz,
    (p_activity->>'quantityKg')::numeric,
    (p_activity->>'fraction')::numeric,
    coalesce((p_activity->>'source')::activity_source, 'user'),
    p_activity->>'sourceRecId'
  )
  on conflict (id) do update set
    status = excluded.status,
    start_time = excluded.start_time,
    end_time = excluded.end_time,
    quantity_kg = excluded.quantity_kg,
    fraction = excluded.fraction
  returning id into v_id;
  return v_id;
end;
$$;

create or replace function delete_activity(p_activity_id text) returns void
language plpgsql security invoker set search_path = public, pg_temp as $$
begin
  delete from activities where id = p_activity_id;
end;
$$;

grant execute on function create_pond(text, numeric, numeric, integer, numeric, date, text, text) to authenticated;
grant execute on function save_checklist(uuid, jsonb) to authenticated;
grant execute on function upsert_activity(uuid, jsonb) to authenticated;
grant execute on function delete_activity(text) to authenticated;
