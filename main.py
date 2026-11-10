"""FastAPI service: HTTP API + worker loop in one process (DB_DESIGN §16.5)."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException

from db.adapter import StaleSnapshot, apply_changeset, load_snapshot
from services.run_analysis import run_analysis

@asynccontextmanager
async def _lifespan(app: FastAPI):
    task = asyncio.create_task(_worker_loop())
    yield
    task.cancel()


app = FastAPI(title="Aquanoph Analysis Service", lifespan=_lifespan)

_pool: asyncpg.Pool | None = None
_wake = asyncio.Event()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_iso(value: object, field: str) -> datetime:
    """body ISO string -> naive UTC datetime. ไม่ valid → 400 ไม่ใช่ 500."""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid {field}")
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    raise HTTPException(status_code=400, detail=f"{field} required")


async def pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("SUPABASE_DB_URL")
        if not dsn:
            raise RuntimeError("SUPABASE_DB_URL not set")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return _pool


def _verify_jwt(authorization: str = Header(...)) -> dict:
    import jwt

    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET not set")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return jwt.decode(authorization[7:], secret, algorithms=["HS256"], audience="authenticated")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/wake")
async def wake():
    _wake.set()
    return {"ok": True}


async def _one_job() -> str:
    """Poll 1 queued job, run, apply. Returns 'idle' | 'done' | 'stale' | 'error'."""
    p = await pool()
    async with p.acquire() as conn:
        job = await conn.fetchrow(
            """
            update analysis_jobs set status='running', locked_at=now(), started_at=coalesce(started_at, now()), attempts=attempts+1
            where id = (
              select id from analysis_jobs
              where status='queued' and run_after <= now()
              order by created_at asc limit 1
              for update skip locked
            )
            returning id, pond_id, kinds, activity_t_from
            """
        )
    if job is None:
        return "idle"
    try:
        async with (await pool()).acquire() as conn:
            from identity.analysis.models import Trigger, TriggerKind
            now = _now()
            snap = await load_snapshot(conn, str(job["pond_id"]), now)
            versions = {r.id: r.updatedAt for r in snap.recommendations}
            prows = await conn.fetch("select user_id from ponds where id=$1", job["pond_id"])
            user_id = str(prows[0]["user_id"]) if prows else ""
            order = {"activityEvent": 0, "pondEdit": 1, "reading": 2, "tick": 3}
            kinds = sorted(job["kinds"] or ["tick"], key=lambda k: order.get(k, 9))
            wrote = False
            t_from = job["activity_t_from"]
            for k in kinds:
                trig = Trigger(kind=TriggerKind(k), tFrom=t_from)
                cs = run_analysis(snap, trig, now)
                if cs.isEmpty():
                    continue
                wrote = True
                await apply_changeset(
                    conn, str(job["pond_id"]), cs, versions, now,
                    snap.pond.timezone, user_id, job["id"], engine_version="v1",
                )
                # refresh versions หลังเขียน (กัน StaleSnapshot ปลอมรอบถัดไปใน job เดียวกัน)
                snap = await load_snapshot(conn, str(job["pond_id"]), now)
                versions = {r.id: r.updatedAt for r in snap.recommendations}
            if not wrote:
                # ChangeSet ว่างทุก kind — ปิด job + log run (ไม่งั้นค้าง running ตลอดกาล)
                from identity.analysis.changeset import ChangeSet
                await apply_changeset(
                    conn, str(job["pond_id"]), ChangeSet(), versions, now,
                    snap.pond.timezone, user_id, job["id"], engine_version="v1",
                )
        return "done"
    except StaleSnapshot:
        async with (await pool()).acquire() as conn:
            await conn.execute(
                "update analysis_jobs set status='queued', locked_at=null, run_after=now() where id=$1",
                job["id"],
            )
        return "stale"
    except Exception as e:  # noqa: BLE001 — log แล้ว mark failed
        async with (await pool()).acquire() as conn:
            await conn.execute(
                "update analysis_jobs set status='failed', last_error=$2, finished_at=now() where id=$1",
                job["id"], str(e)[:500],
            )
        return "error"


async def _worker_loop() -> None:
    while True:
        try:
            await _one_job()
        except Exception:  # noqa: BLE001 — worker ห้ามตาย
            pass
        try:
            await asyncio.wait_for(_wake.wait(), timeout=7)
            _wake.clear()
        except asyncio.TimeoutError:
            pass


@app.post("/recommendations/{rec_id}/preview")
async def preview(rec_id: str, body: dict, claims: dict = Depends(_verify_jwt)):
    from identity.recommendation.apply_plan import buildApplyPlan

    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "select pond_id from recommendations where id=$1", rec_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="rec not found")
        # ownership: ponds.user_id == claims.sub — ไม่เชื่อ pond_id จาก body (§10)
        own = await conn.fetchrow(
            "select 1 from ponds where id=$1 and user_id=$2",
            row["pond_id"], claims["sub"],
        )
        if own is None:
            raise HTTPException(status_code=403, detail="not pond owner")
        now = _now()
        snap = await load_snapshot(conn, str(row["pond_id"]), now)
        rec = next((r for r in snap.recommendations if r.id == rec_id), None)
        if rec is None:
            raise HTTPException(status_code=404, detail="rec not in snapshot")
        chosen = _parse_iso(body.get("chosenTime"), "chosenTime") if body.get("chosenTime") else None
        res = buildApplyPlan(rec, snap, now, chosen, confirmed=False)
        return {"status": res.status, "reason": res.reason, "summary": dict(res.summary)}


@app.post("/recommendations/{rec_id}/apply")
async def apply(rec_id: str, body: dict, claims: dict = Depends(_verify_jwt)):
    from identity.recommendation.apply_plan import buildApplyPlan

    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "select pond_id from recommendations where id=$1", rec_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="rec not found")
        own = await conn.fetchrow(
            "select user_id from ponds where id=$1", row["pond_id"]
        )
        if own is None or str(own["user_id"]) != claims["sub"]:
            raise HTTPException(status_code=403, detail="not pond owner")
        now = _now()
        snap = await load_snapshot(conn, str(row["pond_id"]), now)
        rec = next((r for r in snap.recommendations if r.id == rec_id), None)
        if rec is None:
            raise HTTPException(status_code=404, detail="rec not in snapshot")
        chosen = _parse_iso(body.get("chosenTime"), "chosenTime") if body.get("chosenTime") else None
        res = buildApplyPlan(rec, snap, now, chosen, confirmed=True)
        if res.status != "applied":
            return {"status": res.status, "reason": res.reason, "summary": dict(res.summary)}
        versions = {r.id: r.updatedAt for r in snap.recommendations}
        try:
            await apply_changeset(
                conn, str(row["pond_id"]), res.changeSet, versions, now,
                snap.pond.timezone, str(own["user_id"]), None, engine_version="v1",
            )
        except StaleSnapshot:
            raise HTTPException(status_code=409, detail="stale snapshot, retry")
        # enqueue activityEvent(t_from = start ของ activity ใหม่) (§7 ข้อ 3)
        starts = [op.activity.startTime for op in res.changeSet.activityOps
                  if op.activity is not None]
        if starts:
            await conn.execute(
                "select enqueue_analysis($1, 'activityEvent', $2)",
                row["pond_id"], min(starts),
            )
        return {"status": "applied", "summary": dict(res.summary)}


@app.post("/recommendations/{rec_id}/snooze")
async def snooze(rec_id: str, body: dict, claims: dict = Depends(_verify_jwt)):
    from identity.recommendation.apply_plan import snoozeRec

    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "select pond_id from recommendations where id=$1", rec_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="rec not found")
        own = await conn.fetchrow("select user_id from ponds where id=$1", row["pond_id"])
        if own is None or str(own["user_id"]) != claims["sub"]:
            raise HTTPException(status_code=403, detail="not pond owner")
        now = _now()
        snap = await load_snapshot(conn, str(row["pond_id"]), now)
        rec = next((r for r in snap.recommendations if r.id == rec_id), None)
        if rec is None:
            raise HTTPException(status_code=404, detail="rec not in snapshot")
        until = _parse_iso(body.get("snoozeUntil"), "snoozeUntil")
        try:
            snoozeRec(rec, until, now)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        await conn.execute(
            "update recommendations set status='snoozed', snooze_until=$2, updated_at=$3 where id=$1",
            rec_id, until, _now(),
        )
        return {"status": "snoozed"}


@app.post("/recommendations/{rec_id}/dismiss")
async def dismiss(rec_id: str, body: dict, claims: dict = Depends(_verify_jwt)):
    from identity.recommendation.apply_plan import dismissRec

    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "select pond_id from recommendations where id=$1", rec_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="rec not found")
        own = await conn.fetchrow("select user_id from ponds where id=$1", row["pond_id"])
        if own is None or str(own["user_id"]) != claims["sub"]:
            raise HTTPException(status_code=403, detail="not pond owner")
        now = _now()
        snap = await load_snapshot(conn, str(row["pond_id"]), now)
        rec = next((r for r in snap.recommendations if r.id == rec_id), None)
        if rec is None:
            raise HTTPException(status_code=404, detail="rec not in snapshot")
        try:
            dismissRec(rec, now)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        await conn.execute(
            "update recommendations set status='dismissed', dismissed_at=$2, dismiss_note=$3, updated_at=$2 where id=$1",
            rec_id, _now(), body.get("note"),
        )
        return {"status": "dismissed"}
