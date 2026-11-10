-- LIVE TEST ผ่าน Supabase SQL Editor (แทน pytest จากเครื่องที่เน็ตบล็อก 5432/6543)
-- รันทั้งไฟล์ทีเดียว: PASS ทุกข้อ → NOTICE 'ALL PASS'; FAIL → EXCEPTION ตรงจุดที่พัง
-- ทุกแถวผูก device 'dev-sqltest' → cleanup หมดทั้งตอนจบและตอน error (รันซ้ำได้)
-- ใช้ role postgres/service_role ใน Editor (ข้าม RLS; guard อนุญาต role นี้)

-- helper ลบ fixture ทั้งหมดที่ผูก device นี้ (รันซ้ำได้)
create or replace function public.cleanup_sqltest(p_dev text) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_pond uuid;
begin
  select id into v_pond from ponds where device_id = p_dev;
  if v_pond is not null then
    delete from analysis_jobs where pond_id = v_pond;
    delete from analysis_runs where pond_id = v_pond;
    delete from notifications where pond_id = v_pond;
    delete from recommendation_sources
      where rec_id in (select id from recommendations where pond_id = v_pond);
    delete from recommendations where pond_id = v_pond;
    delete from predictions where pond_id = v_pond;
    delete from diagnostic_reports where pond_id = v_pond;
    -- severity_reports อ้าง pond_states (restrict): ลบ severity ก่อนแตะ states
    delete from severity_reports where pond_id = v_pond;
    delete from activities where pond_id = v_pond;
    delete from activity_series where pond_id = v_pond;
    delete from pond_analysis_state where pond_id = v_pond;
    -- กันแถว states เกิดใหม่หลังลบ severity (trigger T3/T4): ลบอีกรอบก่อนลบ pond
    delete from severity_reports where pond_id = v_pond;
    delete from pond_states where pond_id = v_pond;
    delete from ponds where id = v_pond;
  end if;
  delete from sensor_readings where device_id = p_dev;
  delete from devices where device_id = p_dev;
end $$;

DO $$
DECLARE
  v_user_id uuid;
  v_dev text := 'dev-sqltest';
  v_pond uuid;
  v_state uuid;
  v_now timestamptz := now();
  v_n int;
  v_late boolean;
  v_upd1 timestamptz;
  v_title text;
BEGIN
  PERFORM cleanup_sqltest(v_dev);

  -- ============ SETUP ============
  SELECT user_id INTO v_user_id FROM profiles LIMIT 1;
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'FAIL setup: no profiles row (สมัคร user ก่อน)';
  END IF;

  INSERT INTO devices (device_id) VALUES (v_dev) ON CONFLICT DO NOTHING;

  INSERT INTO ponds (user_id, name, area_m2, avg_depth_m, stocking_count,
                     avg_weight_g, stocking_date, device_id, timezone)
  VALUES (v_user_id, 'sql-live-test', 10, 1.5, 100, 400, '2025-01-01', v_dev, 'Asia/Bangkok')
  RETURNING id INTO v_pond;

  SELECT id INTO v_state FROM pond_states
  WHERE pond_id = v_pond ORDER BY effective_from DESC LIMIT 1;
  IF v_state IS NULL THEN
    RAISE EXCEPTION 'FAIL setup: T4 ไม่สร้าง pond_states';
  END IF;
  RAISE NOTICE 'PASS setup: pond % state %', v_pond, v_state;

  -- ============ T1: pond insert → tick job ============
  SELECT count(*) INTO v_n FROM analysis_jobs
  WHERE pond_id = v_pond AND status = 'queued' AND 'tick' = ANY(kinds);
  IF v_n < 1 THEN
    RAISE EXCEPTION 'FAIL T1: ไม่มี tick job หลัง pond insert';
  END IF;
  RAISE NOTICE 'PASS T1 enqueue tick';

  -- ============ T2: late = ผิดลำดับเท่านั้น ============
  INSERT INTO sensor_readings (device_id, measured_at, "DO")
  VALUES (v_dev, v_now - interval '2 hours', 7.0);
  UPDATE pond_analysis_state SET last_reading_at = v_now - interval '1 hour'
  WHERE pond_id = v_pond;
  INSERT INTO sensor_readings (device_id, measured_at, "DO")
  VALUES (v_dev, v_now - interval '3 hours', 6.9);

  SELECT late INTO v_late FROM sensor_readings
  WHERE device_id = v_dev AND measured_at = v_now - interval '3 hours';
  IF v_late IS NOT TRUE THEN
    RAISE EXCEPTION 'FAIL T2a: แถวเก่ากว่า cursor ต้อง late=true';
  END IF;
  SELECT late INTO v_late FROM sensor_readings
  WHERE device_id = v_dev AND measured_at = v_now - interval '2 hours';
  IF v_late IS NOT FALSE THEN
    RAISE EXCEPTION 'FAIL T2b: แถวใหม่สุดต้อง late=false (มาช้าแต่ไม่ผิดลำดับ)';
  END IF;
  RAISE NOTICE 'PASS T2 late flag';

  -- ============ T3: T5 critical แจ้งครั้งเดียว ============
  DELETE FROM notifications WHERE pond_id = v_pond;
  INSERT INTO severity_reports
    (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version)
  VALUES (v_pond, v_state, 'DO', v_now - interval '30 minutes', 7.0, 'optimal', 'optimal', 'sqltest')
  ON CONFLICT DO NOTHING;
  INSERT INTO severity_reports
    (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version)
  VALUES (v_pond, v_state, 'DO', v_now, 0.5, 'critical', 'critical', 'sqltest')
  ON CONFLICT DO NOTHING;

  SELECT count(*) INTO v_n FROM notifications
  WHERE pond_id = v_pond AND kind = 'severityCritical';
  IF v_n <> 1 THEN
    RAISE EXCEPTION 'FAIL T3a: เพิ่งเข้า Critical ต้องมี notification 1 แถว (ได้ %)', v_n;
  END IF;

  INSERT INTO severity_reports
    (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version)
  VALUES (v_pond, v_state, 'DO', v_now + interval '30 minutes', 0.4, 'critical', 'critical', 'sqltest')
  ON CONFLICT DO NOTHING;
  SELECT count(*) INTO v_n FROM notifications
  WHERE pond_id = v_pond AND kind = 'severityCritical';
  IF v_n <> 1 THEN
    RAISE EXCEPTION 'FAIL T3b: ค้าง critical ต้องไม่ส่งซ้ำ (ได้ %)', v_n;
  END IF;
  RAISE NOTICE 'PASS T3 severityCritical ครั้งเดียว';

  -- ============ T4: idempotency rec upsert + dedupe ============
  INSERT INTO recommendations
    (id, pond_id, entry_id, dedupe_key, urgency, apply_mode, valid_from, valid_until, title)
  VALUES ('rec:sqltest:1', v_pond, 'AERATE', 'LIVE:1', 'urgent', 'fixed',
          v_now - interval '1 hour', v_now + interval '5 hours', 'v1');
  SELECT updated_at INTO v_upd1 FROM recommendations WHERE id = 'rec:sqltest:1';

  INSERT INTO recommendations
    (id, pond_id, entry_id, dedupe_key, urgency, apply_mode, valid_from, valid_until, title, updated_at)
  VALUES ('rec:sqltest:1', v_pond, 'AERATE', 'LIVE:1', 'urgent', 'fixed',
          v_now - interval '1 hour', v_now + interval '5 hours', 'v2', v_upd1 + interval '1 minute')
  ON CONFLICT (id) DO UPDATE SET
    title = excluded.title, updated_at = excluded.updated_at;

  -- หมายเหตุ: now() คงค่าตลอด transaction → updated_at ไม่ขยับในไฟล์นี้
  -- ยืนยัน upsert ผ่าน title ที่ถูกทับ + แถวเดียว
  SELECT count(*) INTO v_n FROM recommendations WHERE id = 'rec:sqltest:1';
  IF v_n <> 1 THEN
    RAISE EXCEPTION 'FAIL T4a: upsert ซ้ำต้องไม่เพิ่มแถว';
  END IF;
  SELECT title INTO v_title FROM recommendations WHERE id = 'rec:sqltest:1';
  IF v_title <> 'v2' THEN
    RAISE EXCEPTION 'FAIL T4b: upsert ต้องทับ title เป็น v2 (got %)', v_title;
  END IF;

  BEGIN
    INSERT INTO recommendations
      (id, pond_id, entry_id, dedupe_key, urgency, apply_mode, valid_from, valid_until)
    VALUES ('rec:sqltest:2', v_pond, 'AERATE', 'LIVE:1', 'non_urgent', 'fixed',
            v_now, v_now + interval '5 hours');
    RAISE EXCEPTION 'FAIL T4c: pending ซ้ำ dedupe_key ต้องถูกบล็อก';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
  RAISE NOTICE 'PASS T4 idempotency + dedupe';

  -- ============ T5: predictions active ครั้งละ 1 ============
  INSERT INTO predictions
    (id, pond_id, rule_id, parameter, expected_zone, risk_start, risk_end, pond_snapshot)
  VALUES ('pred:sqltest:1', v_pond, 'RULE_SQL', 'DO', 'critical',
          v_now, v_now + interval '6 hours', '{}');
  BEGIN
    INSERT INTO predictions
      (id, pond_id, rule_id, parameter, expected_zone, risk_start, risk_end, pond_snapshot)
    VALUES ('pred:sqltest:2', v_pond, 'RULE_SQL', 'DO', 'critical',
            v_now, v_now + interval '6 hours', '{}');
    RAISE EXCEPTION 'FAIL T5a: active ซ้ำ rule ต้องถูกบล็อก';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
  UPDATE predictions SET status = 'ended', end_reason = 'window_over'
  WHERE id = 'pred:sqltest:1';
  INSERT INTO predictions
    (id, pond_id, rule_id, parameter, expected_zone, risk_start, risk_end, pond_snapshot)
  VALUES ('pred:sqltest:3', v_pond, 'RULE_SQL', 'DO', 'critical',
          v_now, v_now + interval '6 hours', '{}');
  RAISE NOTICE 'PASS T5 prediction active ครั้งละ 1';

  -- ============ T6: check constraints (urgent/snooze, push_eligible) ============
  BEGIN
    INSERT INTO recommendations
      (id, pond_id, entry_id, dedupe_key, urgency, apply_mode, valid_from, valid_until,
       status, snooze_until)
    VALUES ('rec:sqltest:3', v_pond, 'AERATE', 'LIVE:3', 'urgent', 'fixed',
            v_now, v_now + interval '5 hours', 'snoozed', v_now + interval '1 hour');
    RAISE EXCEPTION 'FAIL T6a: urgent ห้าม snoozed';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
  BEGIN
    INSERT INTO notifications
      (pond_id, user_id, kind, target_type, target_id, push_eligible)
    VALUES (v_pond, v_user_id, 'recChanged', 'recommendation', 'rec:sqltest:1', true);
    RAISE EXCEPTION 'FAIL T6b: push_eligible ต้องเฉพาะ 3 เคส (§3.7)';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
  INSERT INTO notifications
    (pond_id, user_id, kind, target_type, target_id, reason_key, push_eligible)
  VALUES (v_pond, v_user_id, 'recChanged', 'recommendation', 'rec:sqltest:1',
          'rec.changed.urgency_raised', true);
  RAISE NOTICE 'PASS T6 check constraints';

  -- ============ CLEANUP ============
  PERFORM cleanup_sqltest(v_dev);
  RAISE NOTICE 'ALL PASS';

EXCEPTION WHEN OTHERS THEN
  PERFORM cleanup_sqltest(v_dev);
  RAISE;
END $$;
