"""Severity runner — ขั้น 1 ของ worker (§7): reading ใหม่ → severity_reports.

ส่วน pure: build_delivery / compute_reports / report_params (test ได้โดยไม่ต้อง DB)
ส่วน async: sweep_severity (DB IO ผ่าน adapter)
"""
from __future__ import annotations

from datetime import datetime, timezone

from config.constants import AnalysisConfig, DEFAULT_CONFIG
from db import enum_map as EM
from identity.animals.nile_tilapia.nile_model import NileTilapiaModel
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_history_model import PondParametersHistoryModel
from identity.parameters.pond_parameter_model import (
    PondParametersDeliveryModel,
    PondParametersModel,
)

ENGINE_VERSION = "nile-1"

# field ของ PondParametersModel — ใช้ซ้ำตอน map history เข้า/ออก
_PARAM_ATTRS = ("do", "pH", "tem", "nh3", "no2_n", "salinity")


def build_delivery(values: dict[str, float | None]) -> PondParametersDeliveryModel:
    """reading ค่าครบ 6 ตัว → DeliveryModel (caller กรองค่า null แล้ว — ขาดค่า = ไม่รันแถว)."""
    missing = [k for k in _PARAM_ATTRS if values.get(k) is None]
    if missing:
        raise ValueError(f"reading missing values: {missing}")
    return PondParametersDeliveryModel(
        do=float(values["do"]),          # type: ignore[arg-type]
        pH=float(values["pH"]),          # type: ignore[arg-type]
        tem=float(values["tem"]),        # type: ignore[arg-type]
        nh3=float(values["nh3"]),        # type: ignore[arg-type]
        no2_n=float(values["no2_n"]),    # type: ignore[arg-type]
        salinity=float(values["salinity"]),  # type: ignore[arg-type]
    )


def compute_reports(
    *,
    values: dict[str, float | None],
    history: PondParametersHistoryModel,
    now: datetime,
    weight_g: float,
    density_kg_m3: float,
) -> tuple[AnalysisReportModel, ...]:
    """รัน severity engine 1 reading → 6 AnalysisReportModel (level + 4 description fields)."""
    delivery = build_delivery(values)
    animal = NileTilapiaModel(weight=weight_g, density=density_kg_m3, parameterNow=delivery)
    model = PondParametersModel(species=animal, analysisHis=history, dateTime=now)
    return tuple(getattr(model, attr).buildAnalysisReport() for attr in _PARAM_ATTRS)


def report_params(
    *,
    pond_id: str,
    pond_state_id: str,
    reading_id: int,
    report: AnalysisReportModel,
) -> dict:
    """AnalysisReportModel → dict สำหรับ insert severity_reports (ชื่อคอลัมน์แบบทาง A)."""
    desc = report.severity.severityDescription
    measured = report.dateTime
    if measured.tzinfo is None:
        measured = measured.replace(tzinfo=timezone.utc)
    return {
        "pond_id": pond_id,
        "pond_state_id": pond_state_id,
        "parameter": EM.PARAMETER_TO_DB[report.parameter],
        "measured_at": measured,
        "value": report.value,
        "zone": EM.ZONE_TO_DB[report.thresholdStatus],
        "direction": (
            EM.DIRECTION_TO_DB[report.thresholdDirection]
            if report.thresholdDirection is not None
            else None
        ),
        "severity": EM.SEVERITY_TO_DB[report.severity.severityLevel],
        "description": desc.description,
        "detail": desc.detail,
        "append_des": desc.appendDes,
        "guidance": desc.guidance,
        "engine_version": ENGINE_VERSION,
        "reading_id": reading_id,
    }


def append_history(history: PondParametersHistoryModel, report: AnalysisReportModel) -> None:
    """report ที่เพิ่ง insert ใส่ history ในหน่วยความจำ — reading ถัดไปใน batch เดียวกันต้องเห็น."""
    attr = {  # PondParameters enum → field
        "DO": "do", "pH": "pH", "Temperature": "tem",
        "NH3": "nh3", "NO2_N": "no2_n", "Salinity": "salinity",
    }[EM.PARAMETER_TO_DB[report.parameter]]
    getattr(history, attr).append(report)


async def sweep_severity(conn, pond_id: str, now: datetime, cfg: AnalysisConfig = DEFAULT_CONFIG) -> int:
    """ดึง reading ใหม่ (late=false, ค่าครบ, > cursor) → รัน engine → insert → อัปเดต cursor.

    คืนจำนวน reading ที่ประมวลผล. Idempotent: insert on conflict do nothing.
    """
    from db.adapter import (
        advance_reading_cursor,
        fetch_pending_readings,
        insert_severity_report,
        load_pond_engine_meta,
        load_severity_history,
    )

    meta = await load_pond_engine_meta(conn, pond_id)
    if meta is None:
        return 0
    history = await load_severity_history(conn, pond_id, now, cfg)
    readings = await fetch_pending_readings(conn, pond_id, meta, now, cfg)
    if not readings:
        return 0

    processed = 0
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    max_seen = meta["cursor"] or epoch
    for r in readings:
        ts = r["measured_at"]
        if ts > max_seen:
            max_seen = ts
        values = {
            "do": r["DO"], "pH": r["pH"], "tem": r["temperature"],
            "nh3": r["NH3"], "no2_n": r["NO2"], "salinity": r["salinity"],
        }
        if any(v is None for v in values.values()):
            # ข้อมูลขาด = ไม่ทราบ → ข้ามแถว แต่ cursor ยังข้ามผ่าน (ไม่กลับมาประมวลซ้ำ)
            continue
        # naive UTC ให้ engine (rule §9) — แถว DB เป็น aware
        naive_ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        reports = compute_reports(
            values=values, history=history, now=naive_ts,
            weight_g=meta["weight_g"], density_kg_m3=meta["density_kg_m3"],
        )
        for rep in reports:
            params = report_params(
                pond_id=pond_id, pond_state_id=meta["pond_state_id"],
                reading_id=r["id"], report=rep,
            )
            await insert_severity_report(conn, params)
            append_history(history, rep)  # batch เดียวกันเห็นกันและกัน
        processed += 1

    if max_seen > epoch:
        await advance_reading_cursor(conn, pond_id, max_seen)
    return processed
