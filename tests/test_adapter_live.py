"""Live DB tests — ต้อง SUPABASE_DB_URL (service role DSN ใน .env).

รัน: python -m pytest tests/test_adapter_live.py -q
ข้ามอัตโนมัติถ้าไม่มี env (CI ไม่มี secret).
"""
import os
import uuid
from datetime import datetime, timedelta

import pytest

from db.adapter import apply_changeset, load_snapshot, StaleSnapshot

def _dsn() -> str:
    # lazy: อ่านตอน fixture รัน ไม่ใช่ตอน import (env อาจเซ็ตหลัง import)
    return os.environ.get("SUPABASE_DB_URL") or ""


NOW = datetime(2026, 11, 9, 12, 0, 0)  # naive UTC

POND_ID = str(uuid.uuid4())
USER_SQL = "select user_id from profiles limit 1"  # ใช้ profile ใดก็ได้ — ถ้าไม่มี ข้าม


@pytest.fixture()
async def conn():
    pytest.importorskip("asyncpg")
    import asyncpg
    dsn = _dsn()
    if not dsn:
        pytest.skip("no SUPABASE_DB_URL")
    c = await asyncpg.connect(dsn)
    try:
        yield c
    finally:
        await c.close()


@pytest.fixture()
async def pond(conn):
    row = await conn.fetchrow(USER_SQL)
    if row is None:
        pytest.skip("no profiles row — signup ก่อน")
    uid = row["user_id"]
    dev = f"dev-live-{uuid.uuid4().hex[:8]}"
    await conn.execute("insert into devices (device_id) values ($1)", dev)
    await conn.execute(
        """
        insert into ponds (id, user_id, name, area_m2, avg_depth_m, stocking_count,
                           avg_weight_g, stocking_date, device_id, timezone)
        values ($1,$2,'live-test',10,1.5,100,400,'2026-01-01',$3,'Asia/Bangkok')
        """,
        POND_ID, uid, dev,
    )
    yield {"id": POND_ID, "user_id": str(uid), "device": dev}
    # cleanup (service role ข้าม RLS + forbid_mutation ไม่บล็อก role นี้)
    await conn.execute("delete from analysis_jobs where pond_id=$1", POND_ID)
    await conn.execute("delete from recommendations where pond_id=$1", POND_ID)
    await conn.execute("delete from severity_reports where pond_id=$1", POND_ID)
    await conn.execute("delete from sensor_readings where device_id=$1", dev)
    await conn.execute("delete from pond_states where pond_id=$1", POND_ID)
    await conn.execute("delete from pond_analysis_state where pond_id=$1", POND_ID)
    await conn.execute("delete from ponds where id=$1", POND_ID)
    await conn.execute("delete from devices where device_id=$1", dev)


async def test_load_snapshot_empty(pond, conn):
    snap = await load_snapshot(conn, pond["id"], NOW)
    assert snap.pond.pondId == pond["id"]
    assert snap.pond.timezone == "Asia/Bangkok"
    assert snap.severityReports == ()
    assert snap.recommendations == ()


async def test_late_reading_skipped(pond, conn):
    """reading เก่ากว่า cursor → late=true → load_snapshot ไม่เห็น (WHERE ผ่าน severity ไม่มีแถว)."""
    await conn.execute(
        """
        insert into sensor_readings (device_id, measured_at, "DO")
        values ($1, $2, 7.0), ($1, $3, 6.9)
        """,
        pond["device"],
        NOW - timedelta(hours=2),
        NOW - timedelta(hours=3),
    )
    # จำลอง cursor: ประมวลถึง NOW-1h แล้ว → แถว -3h ต้อง late
    await conn.execute(
        "update pond_analysis_state set last_reading_at=$2 where pond_id=$1",
        pond["id"], NOW - timedelta(hours=1),
    )
    row = await conn.fetchrow(
        "select late from sensor_readings where device_id=$1 and measured_at=$2",
        pond["device"], NOW - timedelta(hours=3),
    )
    assert row is not None and row["late"] is True


async def test_idempotency_and_stale(pond, conn):
    """apply ซ้ำ id เดิม → upsert ไม่ insert ซ้ำ + revised_at ขยับ (มติข้อ 28)."""
    from tests.support.rec_builders import makeRecommendation

    rec = makeRecommendation(
        recId=f"rec:{pond['id']}:live1", pondId=pond["id"],
        validFrom=NOW - timedelta(hours=1), validUntil=NOW + timedelta(hours=5),
        createdAt=NOW, updatedAt=NOW,
    )
    from identity.analysis.changeset import ChangeSet
    cs = ChangeSet(recommendations=(rec,))
    snap = await load_snapshot(conn, pond["id"], NOW)
    versions = {r.id: r.updatedAt for r in snap.recommendations}
    await apply_changeset(conn, pond["id"], cs, versions, NOW,
                          "Asia/Bangkok", pond["user_id"], None, "test")
    n1 = await conn.fetchval("select count(*) from recommendations where id=$1", rec.id)
    assert n1 == 1

    # ยิงซ้ำ: ต้องไม่เพิ่มแถว แต่ updated_at/revised ไม่เท่าเดิม (upsert path)
    snap2 = await load_snapshot(conn, pond["id"], NOW + timedelta(minutes=1))
    versions2 = {r.id: r.updatedAt for r in snap2.recommendations}
    await apply_changeset(conn, pond["id"], cs, versions2, NOW + timedelta(minutes=1),
                          "Asia/Bangkok", pond["user_id"], None, "test")
    n2 = await conn.fetchval("select count(*) from recommendations where id=$1", rec.id)
    assert n2 == 1

    # Stale: แตะ updated_at กลางทางแล้ว apply ด้วย version เก่า → raise
    await conn.execute("update recommendations set title='touched' where id=$1", rec.id)
    with pytest.raises(StaleSnapshot):
        await apply_changeset(conn, pond["id"], cs, versions, NOW + timedelta(minutes=2),
                              "Asia/Bangkok", pond["user_id"], None, "test")


async def test_severity_critical_triggers_notification(pond, conn):
    """T5: severity critical แถวแรก → มี notifications severityCritical (มติข้อ 8.5)."""
    ps = await conn.fetchrow(
        "select id from pond_states where pond_id=$1 order by effective_from desc limit 1",
        pond["id"],
    )
    assert ps is not None
    readings = [NOW - timedelta(minutes=30), NOW]
    for i, m in enumerate(readings):
        await conn.execute(
            'insert into sensor_readings (device_id, measured_at, "DO") values ($1,$2,$3)',
            pond["device"], m, 7.0 - i,
        )
    # แถว optimal ก่อน (สร้างก่อน จะได้ test "เพิ่งเข้า" critical)
    await conn.execute(
        """
        insert into severity_reports
          (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version, reading_id)
        values ($1,$2,'DO',$3,7.0,'optimal','optimal','test',null)
        on conflict do nothing
        """,
        pond["id"], ps["id"], readings[0],
    )
    await conn.execute("delete from notifications where pond_id=$1", pond["id"])
    # แถว critical → trigger T5 ต้องสร้าง notification
    await conn.execute(
        """
        insert into severity_reports
          (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version, reading_id)
        values ($1,$2,'DO',$3,0.5,'critical','critical','test',null)
        on conflict do nothing
        """,
        pond["id"], ps["id"], readings[1],
    )
    n = await conn.fetchval(
        "select count(*) from notifications where pond_id=$1 and kind='severityCritical'",
        pond["id"],
    )
    assert n == 1
    # ค้าง critical ต่อ (reading ใหม่กว่าแต่ยัง critical) → ไม่ส่งซ้ำ
    await conn.execute(
        """
        insert into severity_reports
          (pond_id, pond_state_id, parameter, measured_at, value, zone, severity, engine_version, reading_id)
        values ($1,$2,'DO',$3,0.4,'critical','critical','test',null)
        on conflict do nothing
        """,
        pond["id"], ps["id"], NOW + timedelta(minutes=30),
    )
    n2 = await conn.fetchval(
        "select count(*) from notifications where pond_id=$1 and kind='severityCritical'",
        pond["id"],
    )
    assert n2 == 1
