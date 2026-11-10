-- 007: analysis_jobs, analysis_runs, enqueue_analysis, cron C1/C2/C3
-- DB_DESIGN §3.7, T1/T2/T3/T4 ที่ enqueue, C1-C3
-- หมายเหตุ: worker ดึง 1 job ต่อครั้ง (มติข้อ 13) — skip locked + for update
--   skip 'late' = filter ที่ query (มติข้อ 12) อยู่ฝั่ง Python adapter ไม่ใช่ DB

create table analysis_jobs (
  id bigint generated always as identity primary key,
  pond_id uuid not null references ponds (id),
  status job_status not null default 'queued',
  kinds text[] not null default '{}',
  activity_t_from timestamptz,
  run_after timestamptz not null default now(),
  attempts integer not null default 0,
  locked_at timestamptz,
  locked_by text,
  last_error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

-- partial unique: 1 queued + 1 running ต่อบ่อ
create unique index analysis_jobs_queued_uniq on analysis_jobs (pond_id) where status = 'queued';
create unique index analysis_jobs_running_uniq on analysis_jobs (pond_id) where status = 'running';
create index analysis_jobs_poll_idx on analysis_jobs (status, run_after, created_at);

create table analysis_runs (
  id bigint generated always as identity primary key,
  job_id bigint not null references analysis_jobs (id) on delete cascade,
  pond_id uuid not null references ponds (id),
  trigger_kind text not null,
  now_at timestamptz not null,
  t_from timestamptz,
  diagnostics_count integer not null default 0,
  predictions_count integer not null default 0,
  recommendations_count integer not null default 0,
  notifications_count integer not null default 0,
  activities_created integer not null default 0,
  duration_ms integer,
  error text,
  engine_version text,
  created_at timestamptz not null default now()
);
create index analysis_runs_job_idx on analysis_runs (job_id);
create index analysis_runs_pond_idx on analysis_runs (pond_id, now_at desc);

-- enqueue_analysis: รวม kind ด้วย union + least(t_from) ตามกฎ special part §4
-- on conflict (pond_id) where status='queued' do update → merge
create or replace function enqueue_analysis(p_pond_id uuid, p_kind text, p_t_from timestamptz default null) returns void
language plpgsql as $$
begin
  insert into analysis_jobs (pond_id, kinds, activity_t_from, status)
  values (p_pond_id, array[p_kind], p_t_from, 'queued')
  on conflict (pond_id) where status = 'queued'
  do update set
    kinds = (select array_agg(distinct k) from unnest(analysis_jobs.kinds || array[p_kind]) as k),
    activity_t_from = least(analysis_jobs.activity_t_from, p_t_from);
end;
$$;

-- C1: pg_cron ทุก 30 นาที enqueue tick ทุกบ่อ
create or replace function cron_enqueue_ticks() returns void
language plpgsql as $$
begin
  perform enqueue_analysis(p.id, 'tick', null) from ponds p;
end;
$$;

-- C2: cron รายวัน renew_activity_series (สร้างใน 006)
-- ปลดล็อก running ค้าง — merge เข้า queued ถ้ามีอยู่แล้ว (กัน queued_uniq)
-- (bugfix: UPDATE ตรง ๆ running→queued โดน partial unique ถ้า pond มี queued อยู่แล้ว)
create or replace function requeue_stale_jobs() returns void
language plpgsql as $$
declare
  r record;
begin
  for r in
    select id, pond_id, kinds, activity_t_from
    from analysis_jobs
    where status = 'running' and locked_at < now() - interval '10 minutes'
    for update
  loop
    if exists (
      select 1 from analysis_jobs
      where pond_id = r.pond_id and status = 'queued' and id <> r.id
    ) then
      update analysis_jobs q set
        kinds = (select array_agg(distinct k) from unnest(q.kinds || r.kinds) as k),
        activity_t_from = least(q.activity_t_from, r.activity_t_from)
      where q.pond_id = r.pond_id and q.status = 'queued';
      update analysis_jobs
      set status = 'failed', last_error = 'stale heartbeat: merged into queued job',
          locked_at = null, finished_at = now()
      where id = r.id;
    else
      update analysis_jobs
      set status = 'queued', locked_at = null, locked_by = null,
          attempts = attempts + 1, run_after = now()
      where id = r.id;
    end if;
  end loop;
end;
$$;

-- C3: cron รายวัน cleanup analysis_jobs done เกิน 7 วัน + ปลด lock งาน running ค้าง
create or replace function cron_cleanup_jobs() returns void
language plpgsql as $$
begin
  delete from analysis_jobs
  where status = 'done' and finished_at < now() - interval '7 days';
  perform requeue_stale_jobs();
end;
$$;

-- ติดตั้ง cron jobs (pg_cron) — ต้อง extension pg_cron (001 แล้ว)
select cron.schedule('analysis-tick', '*/30 * * * *', $$select cron_enqueue_ticks();$$);
select cron.schedule('renew-series', '0 0 * * *', $$select renew_activity_series();$$);
select cron.schedule('cleanup-jobs', '0 2 * * *', $$select cron_cleanup_jobs();$$);
