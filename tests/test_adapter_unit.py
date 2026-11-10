"""Adapter unit tests — pure, no DB (มติข้อ 11: StaleSnapshot path แบบ mock)."""
from datetime import datetime, timezone

import pytest

from db.adapter import (
    ASRC,
    StaleSnapshot,
    _causes_json,
    _json,
    _parse_dt,
    _proposed_json,
    _req_naive,
    _snapshot_from_json,
    _snapshot_json,
    _to_aware,
    _to_naive,
)
from db import enum_map as EM
from identity.analysis.models import ActivitySource, PondInfo


def test_naive_aware_roundtrip():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aw = _to_aware(naive)
    assert aw is not None and aw.tzinfo is not None
    assert _to_naive(aw) == naive
    assert _to_aware(aw) is aw
    assert _to_naive(None) is None
    assert _to_aware(None) is None


def test_req_naive_rejects_null():
    with pytest.raises(ValueError, match="required column"):
        _req_naive(None, "t.c")
    assert _req_naive(datetime(2026, 1, 1), "t.c") == datetime(2026, 1, 1)


def test_parse_dt_variants():
    assert _parse_dt(None) == datetime(1970, 1, 1)
    assert _parse_dt(datetime(2026, 5, 1, 8)) == datetime(2026, 5, 1, 8)
    assert _parse_dt("2026-05-01T08:00:00") == datetime(2026, 5, 1, 8, 0, 0)
    aw = datetime(2026, 5, 1, 8, tzinfo=timezone.utc)
    assert _parse_dt(aw) == datetime(2026, 5, 1, 8)


def test_snapshot_json_roundtrip():
    p = PondInfo(pondId="p1", timezone="Asia/Bangkok", biomassKg=400.0, avgWeightG=400.0, fishCount=1000)
    back = _snapshot_from_json(_snapshot_json(p))
    assert back == p


def test_causes_json_shape():
    from identity.analysis.models import Cause, DiagnosticReport
    from identity.parameters.pond_parameter_enum import PondParameters
    from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
    from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
    import json
    d = DiagnosticReport(
        id="diag:x", pondId="p", parameter=PondParameters.DO, direction=None,
        onsetAt=datetime(2026, 1, 1), endAt=None, status="open",  # type: ignore[arg-type]
        peakSeverity=SeverityLevelType.Critical, lastSeverity=SeverityLevelType.Critical,
        causes=(Cause(ruleId="DO_C_FEED", facts={"kg": 1.0}),),
        noClearCause=False, pondSnapshot=PondInfo(pondId="p"), revisedAt=None,
    )
    got = json.loads(_causes_json(d))
    assert got == [{"rule_id": "DO_C_FEED", "facts": {"kg": 1.0}}]


def test_asrc_mapping():
    assert ASRC(ActivitySource.user) == "user"
    assert ASRC(ActivitySource.recommendation) == "recommendation"


def test_proposed_json_uses_db_names():
    from identity.analysis.models import ActivityType, ProposedActivity
    import json
    props = (ProposedActivity(type=ActivityType.waterChange, startTime=datetime(2026, 1, 1, 8), fraction=0.5),)
    got = json.loads(_proposed_json(props))
    assert got[0]["type"] == "water_change"
    assert got[0]["startTime"] == "2026-01-01T08:00:00"
