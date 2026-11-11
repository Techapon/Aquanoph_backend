"""Severity runner unit tests (pure — ไม่แตะ DB)."""
from datetime import datetime

import pytest

from db import enum_map as EM
from identity.parameters.pond_parameter_enum import PondParameters
from identity.parameters.pond_parameter_history_model import PondParametersHistoryModel
from services.severity_runner import (
    ENGINE_VERSION,
    append_history,
    build_delivery,
    compute_reports,
    report_params,
)

NOW = datetime(2026, 11, 11, 10, 0, 0)
VALUES: dict[str, float | None] = {"do": 7.0, "pH": 7.2, "tem": 28.5, "nh3": 0.1, "no2_n": 0.1, "salinity": 0.2}


def test_build_delivery_ok():
    d = build_delivery(VALUES)
    assert d.do == 7.0 and d.salinity == 0.2


def test_build_delivery_missing_raises():
    with pytest.raises(ValueError, match="missing"):
        build_delivery({**VALUES, "nh3": None})


def test_compute_reports_6_params_with_4_fields():
    reports = compute_reports(
        values=VALUES, history=PondParametersHistoryModel(), now=NOW,
        weight_g=400.0, density_kg_m3=2.67,
    )
    assert len(reports) == 6
    assert {r.parameter for r in reports} == {
        PondParameters.DO, PondParameters.pH, PondParameters.tem,
        PondParameters.NH3, PondParameters.NO2_N, PondParameters.salinity,
    }
    for r in reports:
        desc = r.severity.severityDescription
        assert desc.description, f"description ว่างสำหรับ {r.parameter}"
        assert desc.detail, f"detail ว่างสำหรับ {r.parameter}"
        assert desc.guidance, f"guidance ว่างสำหรับ {r.parameter}"
        # appendDes สร้าง runtime — optimal อาจเป็น None ก็ได้
        assert desc.appendDes is None or isinstance(desc.appendDes, str)


def test_report_params_maps_enums_and_fields():
    reports = compute_reports(
        values=VALUES, history=PondParametersHistoryModel(), now=NOW,
        weight_g=400.0, density_kg_m3=2.67,
    )
    r = next(x for x in reports if x.parameter == PondParameters.DO)
    p = report_params(pond_id="p1", pond_state_id="s1", reading_id=42, report=r)
    assert p["parameter"] in ("DO", "NH3", "NO2_N", "pH", "Temperature", "Salinity")
    assert p["zone"] in EM.ZONE_TO_DB.values()
    assert p["severity"] in EM.SEVERITY_TO_DB.values()
    assert p["description"] == r.severity.severityDescription.description
    assert p["detail"] == r.severity.severityDescription.detail
    assert p["append_des"] == r.severity.severityDescription.appendDes
    assert p["guidance"] == r.severity.severityDescription.guidance
    assert p["engine_version"] == ENGINE_VERSION
    assert p["reading_id"] == 42
    assert p["pond_id"] == "p1" and p["pond_state_id"] == "s1"


def test_append_history_targets_right_field():
    reports = compute_reports(
        values=VALUES, history=PondParametersHistoryModel(), now=NOW,
        weight_g=400.0, density_kg_m3=2.67,
    )
    hist = PondParametersHistoryModel()
    for rep in reports:
        append_history(hist, rep)
    assert len(hist.do) == 1
    assert len(hist.no2_n) == 1
    assert hist.do[0].parameter == PondParameters.DO
