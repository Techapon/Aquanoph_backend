-- 013: parameter_forecasts — kNN forecast (6 parameters × horizon hours) สำหรับหน้า Full Analysis
-- อ่านฝั่งแอปตาม RLS (เจ้าของบ่อ); backend เขียนด้วย service role
-- 1 แถวต่อ (pond, parameter) — เขียนทับทุก run; generated_at ใช้ตัดสินความสด

create table parameter_forecasts (
  pond_id uuid not null references ponds (id),
  parameter parameter not null,
  generated_at timestamptz not null,
  model text not null,               -- 'knn_v1'
  horizon_hours integer not null check (horizon_hours > 0),
  -- [{t, v, p25, p75, n}] เรียงเวลา; v = null เมื่อเพื่อนบ้านที่มีข้อมูลไม่ถึงขั้นต่ำ
  points jsonb not null default '[]'::jsonb,
  -- [{date, distance}] เพื่อนบ้านที่ใช้ (debug/อธิบายผล)
  neighbors jsonb not null default '[]'::jsonb,
  primary key (pond_id, parameter)
);
create index parameter_forecasts_pond_idx on parameter_forecasts (pond_id);

alter table parameter_forecasts enable row level security;
grant select on parameter_forecasts to authenticated;
create policy parameter_forecasts_read_own on parameter_forecasts
  for select to authenticated using (private.owns_pond(pond_id));

-- Realtime: forecast เปลี่ยนทุก analysis run — app อัปเดตกราฟแบบ live
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'parameter_forecasts'
  ) then
    execute 'alter publication supabase_realtime add table public.parameter_forecasts';
  end if;
end;
$$;
