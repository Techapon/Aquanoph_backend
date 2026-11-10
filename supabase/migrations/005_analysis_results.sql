-- 005: diagnostic_reports, predictions, recommendations, recommendation_sources
-- DB_DESIGN §3.6 — ผลวิเคราะห์ backend เขียนทั้งหมด (RLS ปิดฝั่ง user ที่ 009)

create table diagnostic_reports (
  id text primary key,  -- deterministic: diag:{pond}:{param}:{dir|-}:{onset}
  pond_id uuid not null references ponds (id),
  parameter parameter not null,
  direction direction,
  onset_at timestamptz not null,
  end_at timestamptz,
  status diag_status not null default 'open',
  peak_severity severity_level not null,
  last_severity severity_level not null,
  causes jsonb not null default '[]'::jsonb,
  no_clear_cause boolean not null default false,
  pond_snapshot jsonb not null,
  revised_at timestamptz,
  created_at timestamptz not null default now(),
  -- text cache จาก renderDiagnostic — adapter เติมตอน apply_changeset (มติข้อ 5)
  text jsonb,
  check (end_at is null or end_at >= onset_at)
);
create index diagnostic_recent_idx on diagnostic_reports (pond_id, onset_at desc);
create index diagnostic_status_idx on diagnostic_reports (pond_id, parameter, status);
-- ไม่มี updated_at ใน diagnostic_reports/predictions (§3.6) — revised_at ทำหน้าที่แทน

create table predictions (
  id text primary key,  -- deterministic: pred:...
  pond_id uuid not null references ponds (id),
  rule_id text not null,
  scope text,
  parameter parameter not null,
  expected_zone threshold_zone not null,
  risk_start timestamptz not null,
  risk_end timestamptz not null,
  met text[] not null default '{}',
  status pred_status not null default 'active',
  end_reason pred_end_reason,
  evidence jsonb not null default '{}'::jsonb,
  pond_snapshot jsonb not null,
  created_at timestamptz not null default now(),
  revised_at timestamptz,
  text jsonb,
  check (end_reason is null or status = 'ended'),
  check (risk_end >= risk_start)
);
-- Phase 4: active ได้ครั้งละ 1 ต่อ rule ต่อบ่อ
create unique index predictions_active_uniq on predictions (pond_id, rule_id) where status = 'active';
create index predictions_status_idx on predictions (pond_id, status);

create table recommendations (
  id text primary key,  -- deterministic: rec:...
  pond_id uuid not null references ponds (id),
  entry_id text not null check (entry_id in ('AERATE', 'WATER_CHANGE', 'ADD_ALKALINITY')),
  dedupe_key text not null,
  urgency urgency not null,
  apply_mode apply_mode not null,
  valid_from timestamptz not null,
  valid_until timestamptz not null,
  title text,
  reason text,
  based_on text,
  guidance text[] not null default '{}',
  proposed_activities jsonb not null default '[]'::jsonb,
  -- plan_text จาก renderPlan — adapter เติมตอน apply_changeset (มติข้อ 5)
  plan_text text,
  status rec_status not null default 'pending',
  expire_reason text check (expire_reason in ('no_longer_applies', 'time_window_over')),
  snooze_until timestamptz,
  -- มติข้อ 8.6: เหตุผลที่ user ปฏิเสธ urgent rec — เขียนผ่าน Python API เท่านั้น ไม่ผ่าน ChangeSet
  dismissed_at timestamptz,
  dismiss_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (valid_until >= valid_from),
  -- snoozed ⇔ snooze_until มีค่า, expired ⇔ expire_reason มีค่า (§3.6)
  check ((status = 'snoozed') = (snooze_until is not null)),
  check ((status = 'expired') = (expire_reason is not null)),
  -- urgent ห้าม snoozed
  check (not (urgency = 'urgent' and status = 'snoozed')),
  -- dismiss fields เฉพาะตอน dismissed
  check ((dismissed_at is not null) = (status = 'dismissed'))
);
-- ไม่สร้าง rec ซ้ำถ้ามี pending/snoozed ที่ dedupe_key เดียวกัน (§3.6)
create unique index recommendations_dedupe_uniq
  on recommendations (pond_id, dedupe_key)
  where status in ('pending', 'snoozed');
create index recommendations_status_idx on recommendations (pond_id, status, valid_until);
create index recommendations_dedupe_idx on recommendations (pond_id, dedupe_key);
create trigger recommendations_set_updated_at
  before update on recommendations
  for each row execute function set_updated_at();

create table recommendation_sources (
  rec_id text not null references recommendations (id) on delete cascade,
  source_type signal_source not null,
  -- FK จริง 3 ทาง — ระบุค่าให้ตรงชนิด 1:1 (§3.6)
  diagnostic_id text references diagnostic_reports (id) on delete restrict,
  prediction_id text references predictions (id) on delete restrict,
  detector_code text,
  constraint sources_target_match check (
    (source_type = 'episode' and diagnostic_id is not null and prediction_id is null and detector_code is null)
    or (source_type = 'prediction' and prediction_id is not null and diagnostic_id is null and detector_code is null)
    or (source_type = 'detector' and detector_code is not null and diagnostic_id is null and prediction_id is null)
  )
);
-- PK แบบ expression (coalesce) — Postgres ไม่รับ expression ใน primary key clause → unique index แทน
create unique index recommendation_sources_pk
  on recommendation_sources (rec_id, source_type, coalesce(diagnostic_id, prediction_id, detector_code));
