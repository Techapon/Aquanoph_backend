"""DB adapter (Phase 8): load_snapshot + apply_changeset.

- Driver เขียน = asyncpg เท่านั้น (มติข้อ 9) — service role DSN (ข้าม RLS ฝั่ง backend)
- 1 transaction ต่อ apply_changeset (มติข้อ 2), StaleSnapshot ผ่าน updated_at (มติข้อ 11)
- skip late ตั้งแต่ query (มติข้อ 12), ทีละ 1 job (มติข้อ 13 — ฝั่ง worker loop ขั้น 3)
- text cache (plan_text/text/renderNotification) เติมตอน apply เท่านั้น (มติข้อ 5)
- enum python <-> postgres ผ่าน db.enum_map (มติข้อ 1)

Rule (§9): ไม่เรียก datetime.now() ในชั้น logic — รับ now เข้ามา; naive UTC เข้า logic.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence, overload

import asyncpg

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from db import enum_map as EM
from identity.analysis.changeset import ChangeSet
from identity.analysis.models import (
    Activity,
    ActivityStatus,
    ActivityType,
    ApplyMode,
    DiagnosticReport,
    DiagStatus,
    Notification,
    PondInfo,
    PondSnapshot,
    Prediction,
    PredStatus,
    Recommendation,
    RecStatus,
    Urgency,
)
from identity.analysis.severity_view import SeverityReportView
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType


class StaleSnapshot(Exception):
    """updated_at ของ rec เปลี่ยนระหว่าง load กับ apply — rollback แล้ว requeue job."""


# pool.acquire() คืน PoolConnectionProxy ไม่ใช่ Connection — รับทั้งคู่
Conn = asyncpg.Connection | asyncpg.pool.PoolConnectionProxy


# UTC: naive <-> aware helpers (DB เป็น timestamptz, engine ใช้ naive UTC)
def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


@overload
def _to_aware(dt: datetime) -> datetime: ...


@overload
def _to_aware(dt: None) -> None: ...


def _to_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def _req_naive(dt: datetime | None, field: str) -> datetime:
    """Unwrap required timestamptz column — DB guarantees NOT NULL, fail loud if null."""
    out = _to_naive(dt)
    if out is None:
        raise ValueError(f"required column {field} is null")
    return out


# ============================ load_snapshot ============================

async def load_snapshot(
    conn: Conn,
    pond_id: str,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> PondSnapshot:
    """โหลด PondSnapshot ตาม DB_DESIGN §9. `now` ต้อง naive UTC."""
    now_aw = _to_aware(now)
    horizon_from = now_aw - timedelta(days=cfg.historyHorizonDays)
    retro_from = now_aw - timedelta(days=cfg.retroWindowDays)
    horizon_need = max(cfg.historyHorizonDays, retro_from and cfg.retroWindowDays or 0)

    # pond + pond_states ล่าสุด → PondInfo (§9)
    prow = await conn.fetchrow(
        """
        select p.id, p.avg_weight_g, p.stocking_count, p.biomass_kg, p.timezone,
               s.avg_weight_g as sw, s.fish_count as sc
        from ponds p
        left join pond_states s on s.id = (
          select id from pond_states where pond_id = p.id order by effective_from desc limit 1
        )
        where p.id = $1
        """,
        pond_id,
    )
    if prow is None:
        raise ValueError(f"pond not found: {pond_id}")
    pond = PondInfo(
        pondId=str(prow["id"]),
        timezone=prow["timezone"],
        biomassKg=float(prow["biomass_kg"]),
        avgWeightG=float(prow["sw"] if prow["sw"] is not None else prow["avg_weight_g"]),
        fishCount=int(prow["sc"] if prow["sc"] is not None else prow["stocking_count"]),
    )

    # severityReports: ตั้งแต่ max(analysis_start_at, now - horizon) เรียงเวลา (§9)
    sev_rows = await conn.fetch(
        """
        select parameter, measured_at, value, zone, direction, severity
        from severity_reports
        where pond_id = $1
          and measured_at >= greatest(
                (select analysis_start_at from ponds where id = $1),
                $2::timestamptz)
        order by measured_at asc
        """,
        pond_id,
        horizon_from,
    )
    severity = tuple(_row_to_sev(r) for r in sev_rows)

    # activities: ตั้งแต่ now - max(horizon, retro) + pending ในอนาคตทั้งหมด (§9)
    act_from = now_aw - timedelta(days=max(horizon_need, cfg.retroWindowDays))
    act_rows = await conn.fetch(
        """
        select id, pond_id, type, status, start_time, end_time,
               quantity_kg, fraction, source, source_rec_id, created_at, updated_at
        from activities
        where pond_id = $1
          and (start_time >= $2 or (status = 'pending' and start_time >= $3))
        order by start_time asc
        """,
        pond_id,
        act_from,
        now_aw,
    )
    activities = tuple(_row_to_activity(r) for r in act_rows)

    # diagnostics: onset ใน horizon หรือ open (§9)
    diag_rows = await conn.fetch(
        """
        select id, pond_id, parameter, direction, onset_at, end_at, status,
               peak_severity, last_severity, causes, no_clear_cause,
               pond_snapshot, revised_at
        from diagnostic_reports
        where pond_id = $1 and (status = 'open' or onset_at >= $2)
        order by onset_at asc
        """,
        pond_id,
        horizon_from,
    )
    diagnostics = tuple(_row_to_diag(r) for r in diag_rows)

    # predictions: active + ที่จบใน horizon (§9)
    pred_rows = await conn.fetch(
        """
        select id, pond_id, rule_id, scope, parameter, expected_zone,
               risk_start, risk_end, met, status, end_reason, evidence,
               pond_snapshot, created_at, revised_at
        from predictions
        where pond_id = $1
          and (status = 'active' or risk_end >= $2)
        """,
        pond_id,
        horizon_from,
    )
    predictions = tuple(_row_to_pred(r) for r in pred_rows)

    # recommendations: pending/snoozed + valid_until >= now-1d + ใบที่ activity อ้าง + dismissed ที่ยังไม่หมด (§9)
    rec_rows = await conn.fetch(
        """
        select distinct r.id, r.pond_id, r.entry_id, r.dedupe_key, r.urgency,
               r.apply_mode, r.valid_from, r.valid_until, r.title, r.reason,
               r.based_on, r.guidance, r.proposed_activities, r.plan_text,
               r.status, r.expire_reason, r.snooze_until, r.created_at, r.updated_at
        from recommendations r
        left join activities a on a.source_rec_id = r.id
        where r.pond_id = $1
          and (r.status in ('pending', 'snoozed')
               or r.valid_until >= $2
               or (a.id is not null and a.status in ('pending', 'done'))
               or (r.status = 'dismissed' and r.valid_until >= $3))
        """,
        pond_id,
        now_aw - timedelta(days=1),
        now_aw,
    )
    recommendations = tuple(_row_to_rec(r, pond_id) for r in rec_rows)
    # sources แยก query (N+1 แต่ rec มีไม่กี่ใบ — ponytail: join ทีเดียวถ้าโต)
    rec_list = list(recommendations)
    if rec_list:
        src_rows = await conn.fetch(
            """
            select rec_id, source_type, diagnostic_id, prediction_id, detector_code
            from recommendation_sources
            where rec_id = any($1::text[])
            """,
            [r.id for r in rec_list],
        )
        by_rec: dict[str, list] = {}
        for s in src_rows:
            by_rec.setdefault(s["rec_id"], []).append(_row_to_source(s))
        from identity.analysis.models import SourceRef
        rec_list = [
            replace(r, sources=tuple(by_rec.get(r.id, ()))) for r in rec_list
        ]

    return PondSnapshot(
        pond=pond,
        severityReports=severity,
        activities=activities,
        diagnostics=diagnostics,
        predictions=predictions,
        recommendations=tuple(rec_list),
    )


# ============================ severity runner DB helpers (§7 ขั้น 1) ============================

async def load_pond_engine_meta(conn: Conn, pond_id: str) -> dict | None:
    """ค่าที่ severity engine ต้องใช้: weight/density, pond_state ล่าสุด, cursor, device."""
    row = await conn.fetchrow(
        """
        select p.avg_weight_g, p.density_kg_m3, p.analysis_start_at, p.device_id,
               s.id as pond_state_id,
               (select last_reading_at from pond_analysis_state where pond_id = p.id) as cursor
        from ponds p
        left join pond_states s on s.id = (
          select id from pond_states where pond_id = p.id order by effective_from desc limit 1
        )
        where p.id = $1
        """,
        pond_id,
    )
    if row is None or row["pond_state_id"] is None:
        return None
    return {
        "weight_g": float(row["avg_weight_g"]),
        "density_kg_m3": float(row["density_kg_m3"]),
        "analysis_start": row["analysis_start_at"],
        "device_id": row["device_id"],
        "pond_state_id": str(row["pond_state_id"]),
        "cursor": row["cursor"],  # aware | None
    }


async def load_severity_history(
    conn: Conn, pond_id: str, now: datetime, cfg: AnalysisConfig = DEFAULT_CONFIG,
):
    """severity_reports ใน horizon → PondParametersHistoryModel (engine อ่านครบทุก field)."""
    from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
    from identity.parameters.pond_parameter_history_model import PondParametersHistoryModel
    from identity.units.severity_units.severity.severity_model import SeverityModel
    from identity.units.severity_units.severity_description.severity_description_model import (
        SeverityDescriptionModel,
    )

    now_aw = _to_aware(now)
    rows = await conn.fetch(
        """
        select parameter, measured_at, value, zone, direction, severity,
               description, detail, append_des, guidance
        from severity_reports
        where pond_id = $1
          and measured_at >= greatest(
                (select analysis_start_at from ponds where id = $1),
                $2::timestamptz)
        order by measured_at asc
        """,
        pond_id,
        now_aw - timedelta(days=cfg.historyHorizonDays),
    )
    history = PondParametersHistoryModel()
    by_attr = {  # db enum label → field ของ history
        "DO": "do", "pH": "pH", "Temperature": "tem",
        "NH3": "nh3", "NO2_N": "no2_n", "Salinity": "salinity",
    }
    for r in rows:
        des = SeverityDescriptionModel(
            des=r["description"] or "",
            detail=r["detail"] or "",
            guid=r["guidance"] or "",
            append=r["append_des"],
        )
        report = AnalysisReportModel(
            dateTime=_req_naive(r["measured_at"], "severity_reports.measured_at"),
            parameter=EM.PARAMETER_FROM_DB[r["parameter"]],
            thresholdStatus=EM.ZONE_FROM_DB[r["zone"]],
            severity=SeverityModel(
                severityLevel=EM.SEVERITY_FROM_DB[r["severity"]],
                severityDes=des,
            ),
            thresholdDirection=(
                EM.DIRECTION_FROM_DB[r["direction"]] if r["direction"] else None
            ),
            value=float(r["value"]) if r["value"] is not None else None,
        )
        getattr(history, by_attr[r["parameter"]]).append(report)
    return history


async def fetch_pending_readings(
    conn: Conn,
    pond_id: str,
    meta: Mapping[str, Any],
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> list:
    """reading ใหม่: late=false (มติข้อ 12), > cursor, >= analysis_start. เรียงเวลา asc."""
    rows = await conn.fetch(
        """
        select id, measured_at, "DO", "pH", "NH3", "NO2", "temperature", "salinity"
        from sensor_readings
        where device_id = $1
          and late = false
          and measured_at > coalesce($2::timestamptz, '-infinity'::timestamptz)
          and measured_at >= $3::timestamptz
        order by measured_at asc
        limit 2000
        """,
        meta["device_id"],
        meta["cursor"],
        meta["analysis_start"],
    )
    return list(rows)


async def insert_severity_report(conn: Conn, params: Mapping[str, Any]) -> None:
    """insert แถวเดียว — on conflict do nothing (idempotency §3.4)."""
    await conn.execute(
        """
        insert into severity_reports
          (pond_id, pond_state_id, parameter, measured_at, value, zone, direction,
           severity, description, detail, append_des, guidance, engine_version, reading_id)
        values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        on conflict (pond_id, parameter, measured_at) do nothing
        """,
        params["pond_id"], params["pond_state_id"], params["parameter"],
        params["measured_at"], params["value"], params["zone"], params["direction"],
        params["severity"], params["description"], params["detail"],
        params["append_des"], params["guidance"], params["engine_version"],
        params["reading_id"],
    )


async def advance_reading_cursor(conn: Conn, pond_id: str, ts: datetime) -> None:
    """cursor = reading ล่าสุดที่ประมวลแล้ว — trigger late ใช้ตัดสินผิดลำดับ."""
    await conn.execute(
        """
        update pond_analysis_state set last_reading_at = $2
        where pond_id = $1
        """,
        pond_id, _to_aware(ts),
    )


# ============================ apply_changeset ============================

async def apply_changeset(
    conn: Conn,
    pond_id: str,
    changeset: ChangeSet,
    snapshot_versions: Mapping[str, datetime],
    now: datetime,
    pond_tz: str,
    user_id: str,
    job_id: int | None,
    engine_version: str,
) -> None:
    """เขียน ChangeSet ใน 1 transaction (§9).

    snapshot_versions: {rec_id: updated_at} ตอน load — เทียบก่อนเขียน rec ใด ๆ
      ไม่ตรง → raise StaleSnapshot (caller rollback + requeue run_after=now).
    job_id None ได้ (เช่น apply ผ่าน API ไม่ผ่าน worker — ข้าม analysis_runs).
    """
    from identity.text.render import renderDiagnostic, renderNotification, renderPlan, renderPrediction

    now_aw = _to_aware(now)
    async with conn.transaction():
        # --- 1. diagnostics (upsert เต็ม object + text cache) ---
        for d in changeset.diagnostics:
            text = renderDiagnostic(d)
            await conn.execute(
                """
                insert into diagnostic_reports
                  (id, pond_id, parameter, direction, onset_at, end_at, status,
                   peak_severity, last_severity, causes, no_clear_cause, pond_snapshot, revised_at, text)
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                on conflict (id) do update set
                  end_at = excluded.end_at, status = excluded.status,
                  peak_severity = excluded.peak_severity, last_severity = excluded.last_severity,
                  causes = excluded.causes, no_clear_cause = excluded.no_clear_cause,
                  revised_at = $13, text = excluded.text
                """,
                d.id, pond_id, EM.PARAMETER_TO_DB[d.parameter],
                EM.DIRECTION_TO_DB[d.direction] if d.direction else None,
                _to_aware(d.onsetAt), _to_aware(d.endAt),
                EM.DIAG_STATUS_TO_DB[d.status],
                EM.SEVERITY_TO_DB[d.peakSeverity], EM.SEVERITY_TO_DB[d.lastSeverity],
                _causes_json(d), d.noClearCause, _snapshot_json(d.pondSnapshot),
                now_aw,
                # asyncpg jsonb codec รับ str — ส่ง dict ตรง = "expected str, got dict"
                _json({"title": text.title,
                       "causes": [{"heading": c.heading, "body": c.body} for c in text.causes],
                       "fallback": text.fallback,
                       "footer": text.footer,
                       "revisedLabel": text.revisedLabel}),
            )

        # --- 2. predictions ---
        for p in changeset.predictions:
            rendered = renderPrediction(p)
            await conn.execute(
                """
                insert into predictions
                  (id, pond_id, rule_id, scope, parameter, expected_zone, risk_start, risk_end,
                   met, status, end_reason, evidence, pond_snapshot, revised_at, text)
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                on conflict (id) do update set
                  status = excluded.status, end_reason = excluded.end_reason,
                  met = excluded.met, evidence = excluded.evidence,
                  revised_at = $14, text = excluded.text
                """,
                p.id, pond_id, p.ruleId, p.scope, EM.PARAMETER_TO_DB[p.parameter],
                EM.ZONE_TO_DB[p.expectedZone],
                _to_aware(p.riskStart), _to_aware(p.riskEnd),
                list(p.met), EM.PRED_STATUS_TO_DB[p.status],
                p.endReason,
                _json(p.evidence), _snapshot_json(p.pondSnapshot),
                now_aw,
                _json({"headline": getattr(rendered, "headline", str(rendered))}),
            )

        # --- 3. recommendations: for update + StaleSnapshot check ก่อนทุกใบ ---
        for r in changeset.recommendations:
            row = await conn.fetchrow(
                "select updated_at from recommendations where id = $1 for update",
                r.id,
            )
            if row is not None:
                expect = snapshot_versions.get(r.id)
                if expect is not None and _to_naive(row["updated_at"]) != _to_naive(expect):
                    raise StaleSnapshot(r.id)
            plan_text = renderPlan(r, _pond_stub(pond_id, pond_tz))
            src = _rec_sources_upsert(r)
            await conn.execute(
                """
                insert into recommendations
                  (id, pond_id, entry_id, dedupe_key, urgency, apply_mode,
                   valid_from, valid_until, title, reason, based_on, guidance,
                   proposed_activities, plan_text, status, expire_reason, snooze_until, updated_at)
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
                on conflict (id) do update set
                  urgency = excluded.urgency, valid_from = excluded.valid_from,
                  valid_until = excluded.valid_until, title = excluded.title,
                  reason = excluded.reason, based_on = excluded.based_on,
                  guidance = excluded.guidance, proposed_activities = excluded.proposed_activities,
                  plan_text = excluded.plan_text, status = excluded.status,
                  expire_reason = excluded.expire_reason, snooze_until = excluded.snooze_until,
                  updated_at = $18
                """,
                r.id, pond_id, r.entryId, r.dedupeKey,
                EM.URGENCY_TO_DB[r.urgency], EM.APPLY_MODE_TO_DB[r.applyMode],
                _to_aware(r.validFrom), _to_aware(r.validUntil),
                r.title, r.reason, r.basedOn, list(r.guidance),
                _proposed_json(r.proposedActivities), plan_text,
                EM.REC_STATUS_TO_DB[r.status], r.expireReason,
                _to_aware(r.snoozeUntil), now_aw,
            )
            for s in src:
                await conn.execute(
                    """
                    insert into recommendation_sources
                      (rec_id, source_type, diagnostic_id, prediction_id, detector_code)
                    values ($1,$2,$3,$4,$5)
                    on conflict do nothing
                    """,
                    r.id, s["source_type"], s["diagnostic_id"],
                    s["prediction_id"], s["detector_code"],
                )

        # --- 4. activityOps (ปกติ worker ไม่มี — API apply เท่านั้น) ---
        for op in changeset.activityOps:
            if op.op == "create" and op.activity is not None:
                a = op.activity
                await conn.execute(
                    """
                    insert into activities
                      (id, pond_id, type, status, start_time, end_time,
                       quantity_kg, fraction, source, source_rec_id)
                    values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    on conflict (id) do nothing
                    """,
                    a.id, pond_id, EM.ACTIVITY_TYPE_TO_DB[a.type],
                    EM.ACTIVITY_STATUS_TO_DB[a.status],
                    _to_aware(a.startTime), _to_aware(a.endTime),
                    a.quantityKg, a.fraction,
                    ASRC(a.source),
                    a.sourceRecId,
                )
            elif op.op == "update" and op.activity is not None:
                a = op.activity
                await conn.execute(
                    """
                    update activities set status=$2, start_time=$3, end_time=$4,
                      quantity_kg=$5, fraction=$6, updated_at=$7
                    where id = $1 and pond_id = $8
                    """,
                    a.id, EM.ACTIVITY_STATUS_TO_DB[a.status],
                    _to_aware(a.startTime), _to_aware(a.endTime),
                    a.quantityKg, a.fraction, now_aw, pond_id,
                )
            elif op.op == "delete":
                aid = op.activityId or (op.activity.id if op.activity else None)
                if aid:
                    await conn.execute(
                        "delete from activities where id = $1 and pond_id = $2",
                        aid, pond_id,
                    )

        # --- 5. notifications (เติม pond_id/user_id/text/push_eligible) ---
        for n in changeset.notifications:
            from identity.text.render import renderNotification as _rn
            text = _rn(n, pond_tz)
            push = n.kind in ("urgentRecCreated",) or (
                n.kind == "recChanged" and n.reasonKey == "rec.changed.urgency_raised"
            )
            # severityCritical มาจาก DB trigger เท่านั้น — engine ไม่ส่ง kind นี้
            await conn.execute(
                """
                insert into notifications
                  (pond_id, user_id, kind, target_type, target_id, reason_key, facts, text, push_eligible)
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """,
                pond_id, user_id, n.kind, n.targetType, n.targetId,
                n.reasonKey, _json(n.facts or {}), text, push,
            )

        # --- 6. analysis_runs + cursor + ปิด job ---
        if job_id is not None:
            await conn.execute(
                """
                insert into analysis_runs
                  (job_id, pond_id, trigger_kind, now_at, t_from,
                   diagnostics_count, predictions_count, recommendations_count,
                   notifications_count, activities_created, engine_version)
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                job_id, pond_id, "batch", now_aw, None,
                len(changeset.diagnostics), len(changeset.predictions),
                len(changeset.recommendations), len(changeset.notifications),
                sum(1 for op in changeset.activityOps if op.op == "create"),
                engine_version,
            )
            await conn.execute(
                """
                update pond_analysis_state
                set last_run_at = $2, engine_version = $3
                where pond_id = $1
                """,
                pond_id, now_aw, engine_version,
            )
            await conn.execute(
                "update analysis_jobs set status='done', finished_at=$2 where id=$1",
                job_id, now_aw,
            )


# ============================ row mappers ============================

def _row_to_sev(r: asyncpg.Record) -> SeverityReportView:
    return SeverityReportView(
        parameter=EM.PARAMETER_FROM_DB[r["parameter"]],
        time=_req_naive(r["measured_at"], "severity_reports.measured_at"),
        value=float(r["value"]) if r["value"] is not None else 0.0,
        zone=EM.ZONE_FROM_DB[r["zone"]],
        direction=EM.DIRECTION_FROM_DB[r["direction"]] if r["direction"] else None,
        severity=EM.SEVERITY_FROM_DB[r["severity"]],
    )


def _row_to_activity(r: asyncpg.Record) -> Activity:
    return Activity(
        id=r["id"],
        pondId=str(r["pond_id"]),
        type=EM.ACTIVITY_TYPE_FROM_DB[r["type"]],
        status=EM.ACTIVITY_STATUS_FROM_DB[r["status"]],
        startTime=_req_naive(r["start_time"], "activities.start_time"),
        endTime=_to_naive(r["end_time"]),
        quantityKg=float(r["quantity_kg"]) if r["quantity_kg"] is not None else None,
        fraction=float(r["fraction"]) if r["fraction"] is not None else None,
        source=_src_from_db(r["source"]),
        sourceRecId=r["source_rec_id"],
        createdAt=_req_naive(r["created_at"], "activities.created_at"),
        updatedAt=_req_naive(r["updated_at"], "activities.updated_at"),
    )


# asyncpg คืน jsonb เป็น str — parse ก่อนใช้ทุกที่ (§9: adapter <-> DB type map)
def _as_list(v: Any) -> list:
    import json
    if v is None:
        return []
    if isinstance(v, str):
        return json.loads(v) if v else []
    return list(v)


def _as_dict(v: Any) -> dict:
    import json
    if v is None:
        return {}
    if isinstance(v, str):
        return json.loads(v) if v else {}
    return dict(v)


def _row_to_diag(r: asyncpg.Record) -> DiagnosticReport:
    from identity.analysis.models import Cause
    causes = tuple(
        Cause(ruleId=c.get("rule_id", ""), facts=dict(c.get("facts", {})))
        for c in _as_list(r["causes"])
    )
    snap = _snapshot_from_json(r["pond_snapshot"])
    return DiagnosticReport(
        id=r["id"],
        pondId=str(r["pond_id"]),
        parameter=EM.PARAMETER_FROM_DB[r["parameter"]],
        direction=EM.DIRECTION_FROM_DB[r["direction"]] if r["direction"] else None,
        onsetAt=_req_naive(r["onset_at"], "diagnostic_reports.onset_at"),
        endAt=_to_naive(r["end_at"]),
        status=EM.DIAG_STATUS_FROM_DB[r["status"]],
        peakSeverity=EM.SEVERITY_FROM_DB[r["peak_severity"]],
        lastSeverity=EM.SEVERITY_FROM_DB[r["last_severity"]],
        causes=causes,
        noClearCause=bool(r["no_clear_cause"]),
        pondSnapshot=snap,
        revisedAt=_to_naive(r["revised_at"]),
    )


def _row_to_pred(r: asyncpg.Record) -> Prediction:
    from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
    snap = _snapshot_from_json(r["pond_snapshot"])
    return Prediction(
        id=r["id"],
        pondId=str(r["pond_id"]),
        ruleId=r["rule_id"],
        scope=r["scope"],
        parameter=EM.PARAMETER_FROM_DB[r["parameter"]],
        expectedZone=EM.ZONE_FROM_DB[r["expected_zone"]],
        riskStart=_req_naive(r["risk_start"], "predictions.risk_start"),
        riskEnd=_req_naive(r["risk_end"], "predictions.risk_end"),
        met=tuple(_as_list(r["met"])),
        status=EM.PRED_STATUS_FROM_DB[r["status"]],
        endReason=r["end_reason"],
        evidence=_as_dict(r["evidence"]),
        pondSnapshot=snap,
        createdAt=_req_naive(r["created_at"], "predictions.created_at"),
        revisedAt=_to_naive(r["revised_at"]),
    )


def _parse_dt(v: Any) -> datetime:
    if v is None:
        return _epoch()
    if isinstance(v, datetime):
        return _to_naive(v) or _epoch()
    return _to_naive(datetime.fromisoformat(str(v))) or _epoch()


def _row_to_rec(r: asyncpg.Record, pond_id: str) -> Recommendation:
    from identity.analysis.models import ProposedActivity
    props = tuple(
        ProposedActivity(
            type=EM.ACTIVITY_TYPE_FROM_DB[p.get("type", "feeding")],
            startTime=_parse_dt(p.get("startTime")),
            endTime=_parse_dt(p.get("endTime")) if p.get("endTime") else None,
            quantityKg=p.get("quantityKg"),
            fraction=p.get("fraction"),
        )
        for p in _as_list(r["proposed_activities"])
    )
    return Recommendation(
        id=r["id"],
        pondId=pond_id,
        entryId=r["entry_id"],
        dedupeKey=r["dedupe_key"],
        urgency=EM.URGENCY_FROM_DB[r["urgency"]],
        validFrom=_req_naive(r["valid_from"], "recommendations.valid_from"),
        validUntil=_req_naive(r["valid_until"], "recommendations.valid_until"),
        title=r["title"] or "",
        reason=r["reason"] or "",
        basedOn=r["based_on"] or "",
        guidance=tuple(r["guidance"] or []),
        proposedActivities=props,
        applyMode=EM.APPLY_MODE_FROM_DB[r["apply_mode"]],
        status=EM.REC_STATUS_FROM_DB[r["status"]],
        expireReason=r["expire_reason"],
        sources=(),
        snoozeUntil=_to_naive(r["snooze_until"]),
        createdAt=_req_naive(r["created_at"], "recommendations.created_at"),
        updatedAt=_req_naive(r["updated_at"], "recommendations.updated_at"),
    )


def _row_to_source(s: asyncpg.Record) -> Any:
    from identity.analysis.models import SourceRef, SignalSource
    st = EM.SIGNAL_SOURCE_FROM_DB[s["source_type"]]
    sid = s["diagnostic_id"] or s["prediction_id"] or s["detector_code"] or ""
    return SourceRef(sourceType=st, sourceId=sid)


def _rec_sources_upsert(r: Recommendation) -> list[dict]:
    out = []
    for s in r.sources:
        st = EM.SIGNAL_SOURCE_TO_DB[s.sourceType]
        out.append({
            "source_type": st,
            "diagnostic_id": s.sourceId if st == "episode" else None,
            "prediction_id": s.sourceId if st == "prediction" else None,
            "detector_code": s.sourceId if st == "detector" else None,
        })
    # union — ไม่ลบ source เก่า (§9: sources ไม่เคยถูกลบ)
    seen: set[tuple] = set()
    uniq = []
    for o in out:
        key = (o["source_type"], o["diagnostic_id"], o["prediction_id"], o["detector_code"])
        if key not in seen:
            seen.add(key)
            uniq.append(o)
    return uniq


# ============================ json helpers ============================

def _json(v: Mapping[str, Any] | Sequence | None) -> str:
    import json
    return json.dumps(dict(v) if isinstance(v, Mapping) else (list(v) if v is not None else {}),
                      default=str)


def _causes_json(d: DiagnosticReport) -> str:
    import json
    return json.dumps(
        [{"rule_id": c.ruleId, "facts": dict(c.facts)} for c in d.causes],
        default=str,
    )


def _snapshot_json(p: PondInfo) -> str:
    import json
    return json.dumps({
        "pondId": p.pondId, "timezone": p.timezone, "biomassKg": p.biomassKg,
        "avgWeightG": p.avgWeightG, "fishCount": p.fishCount,
    })


def _snapshot_from_json(v: Any) -> PondInfo:
    import json
    d = json.loads(v) if isinstance(v, str) else dict(v or {})
    return PondInfo(
        pondId=d.get("pondId", ""),
        timezone=d.get("timezone", "Asia/Bangkok"),
        biomassKg=float(d.get("biomassKg", 0) or 0),
        avgWeightG=float(d.get("avgWeightG", 0) or 0),
        fishCount=int(d.get("fishCount", 0) or 0),
    )


def _proposed_json(props: Sequence) -> str:
    import json
    return json.dumps([{
        "type": EM.ACTIVITY_TYPE_TO_DB[p.type],
        "startTime": p.startTime.isoformat() if p.startTime else None,
        "endTime": p.endTime.isoformat() if p.endTime else None,
        "quantityKg": p.quantityKg,
        "fraction": p.fraction,
    } for p in props], default=str)


def ASRC(s: Any) -> str:
    """ActivitySource -> db enum string."""
    from identity.analysis.models import ActivitySource
    return "user" if s == ActivitySource.user else "recommendation"


def _src_from_db(s: str) -> Any:
    from identity.analysis.models import ActivitySource
    return ActivitySource.user if s == "user" else ActivitySource.recommendation


def _epoch() -> datetime:
    return datetime(1970, 1, 1)


def _pond_stub(pond_id: str, tz: str) -> PondInfo:
    return PondInfo(pondId=pond_id, timezone=tz)


# ponytail: render_plan_text ฝั่ง DB_DESIGN เรียก renderPlan ตรง — ไม่มี wrapper แยก
# ถ้าต้อง render แบบไม่ผ่าน Recommendation object (เช่นจากแถว DB) ค่อยเพิ่ม render_plan_text(rec_row)
