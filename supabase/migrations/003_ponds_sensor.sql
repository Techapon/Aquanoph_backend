-- 003: devices, sensor_readings (+ trigger late/enqueue), ponds, pond_states, pond_analysis_state
-- CONFIG ข้อ 2, DB_DESIGN §3.1, §3.3, T1, T3, T4
-- NOTE: devices/sensor_readings ไม่มีอยู่จริงบน remote (design สมมติว่ามีแล้ว) → สร้างเป็น base table ที่นี่

create table devices (
  device_id text primary key,
  created_at timestamptz not null default now()
);

create table sensor_readings (
  id bigint generated always as identity primary key,
  device_id text not null references devices (device_id),
  measured_at timestamptz not null,
  received_at timestamptz not null default now(),
  late boolean not null default false,
  "DO" numeric,
  "pH" numeric,
  "NH3" numeric,
  "NO2" numeric,
  "temperature" numeric,
  "salinity" numeric,
  -- ค่า NaN/Inf ห้ามเก็บ (engine raise ValueError — DB_DESIGN §3.1)
  constraint sensor_no_nan check (
    coalesce("DO", 0) <> 'NaN'::numeric
    and coalesce("pH", 0) <> 'NaN'::numeric
    and coalesce("NH3", 0) <> 'NaN'::numeric
    and coalesce("NO2", 0) <> 'NaN'::numeric
    and coalesce("temperature", 0) <> 'NaN'::numeric
    and coalesce("salinity", 0) <> 'NaN'::numeric
  ),
  unique (device_id, measured_at)
);
create index sensor_readings_device_measured_idx on sensor_readings (device_id, measured_at desc);

-- T1 (BEFORE INSERT): late = ผิดลำดับ เท่านั้น (มติข้อ 8.4)
-- แถวไหนถูกประมวลผลแล้ว = join ponds.device_id + pond_analysis_state.last_reading_at
-- measured_at <= last_reading_at ของบ่อที่ผูก device นั้น → late
create or replace function sensor_readings_mark_late() returns trigger
language plpgsql as $$
begin
  new.late := exists (
    select 1
    from ponds p
    join pond_analysis_state s on s.pond_id = p.id
    where p.device_id = new.device_id
      and s.last_reading_at is not null
      and new.measured_at <= s.last_reading_at
  );
  return new;
end;
$$;
create trigger sensor_readings_set_late
  before insert on sensor_readings
  for each row execute function sensor_readings_mark_late();

-- T1 (AFTER INSERT): enqueue 'reading' — ข้ามถ้า late หรือก่อน analysis_start_at (§7 ข้อ 1)
-- enqueue_analysis สร้างใน 007 — plpgsql ไม่ resolve ตอน create, runtime ใช้หลัง migrate ครบ
create or replace function sensor_readings_enqueue() returns trigger
language plpgsql as $$
begin
  if not new.late then
    perform enqueue_analysis(p.id, 'reading')
    from ponds p
    where p.device_id = new.device_id
      and new.measured_at >= p.analysis_start_at;
  end if;
  return null;
end;
$$;
create trigger sensor_readings_after_insert
  after insert on sensor_readings
  for each row execute function sensor_readings_enqueue();

-- ponds (§3.3) — generated columns ห้ามอ้างกัน จึง inline expression ทุกตัว
create table ponds (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (user_id),
  name text not null,
  area_m2 numeric not null check (area_m2 > 0),
  avg_depth_m numeric not null check (avg_depth_m > 0),
  species species not null default 'nile_tilapia',
  stocking_count integer not null check (stocking_count > 0),
  avg_weight_g numeric not null check (avg_weight_g > 0),
  stocking_date date not null,
  device_id text not null unique references devices (device_id),
  timezone text not null check (is_valid_timezone(timezone)),
  volume_m3 numeric generated always as (area_m2 * avg_depth_m) stored,
  biomass_kg numeric generated always as (stocking_count * avg_weight_g / 1000.0) stored,
  density_kg_m3 numeric generated always as
    (stocking_count * avg_weight_g / 1000.0 / nullif(area_m2 * avg_depth_m, 0)) stored,
  analysis_start_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ponds_user_idx on ponds (user_id);
create index ponds_device_idx on ponds (device_id);  -- §12: sensor_readings RLS policy ใช้ exists กับ index นี้
create trigger ponds_set_updated_at
  before update on ponds
  for each row execute function set_updated_at();

-- แก้ไม่ได้ = column grant (§3.3)
grant select on ponds to authenticated;
grant insert on ponds to authenticated;
grant update (name, avg_weight_g, stocking_count) on ponds to authenticated;

-- guard ปฏิเสธการแก้คอลัมน์อื่นจาก role ที่ไม่ใช่ service/dev (คู่กับ column grant)
create or replace function ponds_guard_immutable() returns trigger
language plpgsql as $$
begin
  if current_user not in ('postgres', 'service_role', 'supabase_admin') then
    if row(
      new.id, new.user_id, new.area_m2, new.avg_depth_m, new.species,
      new.stocking_date, new.device_id, new.timezone, new.analysis_start_at
    ) is distinct from row(
      old.id, old.user_id, old.area_m2, old.avg_depth_m, old.species,
      old.stocking_date, old.device_id, old.timezone, old.analysis_start_at
    ) then
      raise exception 'immutable_field: pond column change not allowed for role %', current_user;
    end if;
  end if;
  return new;
end;
$$;
create trigger ponds_immutable_guard
  before update on ponds
  for each row execute function ponds_guard_immutable();

-- pond_states: insert-only snapshot (มติข้อ 8.1) — ห้าม update/delete
create table pond_states (
  id uuid primary key default gen_random_uuid(),
  pond_id uuid not null references ponds (id),
  effective_from timestamptz not null default now(),
  avg_weight_g numeric not null,
  fish_count integer not null,
  biomass_kg numeric not null,
  density_kg_m3 numeric not null,
  volume_m3 numeric not null,
  timezone text not null
);
create index pond_states_pond_idx on pond_states (pond_id, effective_from desc);

create or replace function forbid_mutation() returns trigger
language plpgsql as $$
begin
  -- dev/service เก็บไว้ cleanup ได้; แอป/role อื่นโดนบล็อก (insert-only กับคนที่ใช้งานจริง)
  if current_user not in ('postgres', 'service_role', 'supabase_admin') then
    raise exception '%: table is insert-only (frozen fact)', tg_table_name;
  end if;
  return null;
end;
$$;
create trigger pond_states_no_update_delete
  before update or delete on pond_states
  for each row execute function forbid_mutation();

-- pond_analysis_state: cursor ของ backend (§3.3)
create table pond_analysis_state (
  pond_id uuid primary key references ponds (id),
  last_reading_at timestamptz,
  last_run_at timestamptz,
  engine_version text
);

-- T4 (BEFORE INSERT ponds): analysis_start_at = max(midnight local ของ stocking_date, created_at) (N2)
create or replace function ponds_set_analysis_start() returns trigger
language plpgsql as $$
begin
  new.created_at := coalesce(new.created_at, now());
  new.analysis_start_at := greatest(
    (new.stocking_date::timestamp at time zone new.timezone),
    new.created_at
  );
  return new;
end;
$$;
create trigger ponds_set_analysis_start_at
  before insert on ponds
  for each row execute function ponds_set_analysis_start();

-- T4 (AFTER INSERT ponds): pond_states แถวแรก + pond_analysis_state + enqueue งานแรก
-- หมายเหตุ: analysis_start_at อาจอยู่ในอนาคต (stocking วันถัดไป) → reading ถูก filter ตาม §7 ข้อ 1
create or replace function ponds_after_insert() returns trigger
language plpgsql as $$
begin
  insert into pond_states (pond_id, effective_from, avg_weight_g, fish_count, biomass_kg, density_kg_m3, volume_m3, timezone)
  values (new.id, new.created_at, new.avg_weight_g, new.stocking_count, new.biomass_kg, new.density_kg_m3, new.volume_m3, new.timezone);
  insert into pond_analysis_state (pond_id) values (new.id);
  perform enqueue_analysis(new.id, 'tick');
  return null;
end;
$$;
create trigger ponds_after_insert_state
  after insert on ponds
  for each row execute function ponds_after_insert();

-- T3 (AFTER UPDATE): แก้ avg_weight_g/stocking_count → pond_states ใหม่ + enqueue pondEdit (§7 ข้อ 6)
create or replace function ponds_after_update() returns trigger
language plpgsql as $$
begin
  if new.avg_weight_g is distinct from old.avg_weight_g
     or new.stocking_count is distinct from old.stocking_count then
    insert into pond_states (pond_id, effective_from, avg_weight_g, fish_count, biomass_kg, density_kg_m3, volume_m3, timezone)
    values (new.id, now(), new.avg_weight_g, new.stocking_count, new.biomass_kg, new.density_kg_m3, new.volume_m3, new.timezone);
    perform enqueue_analysis(new.id, 'pondEdit');
  end if;
  return null;
end;
$$;
create trigger ponds_after_edit_state
  after update on ponds
  for each row execute function ponds_after_update();
