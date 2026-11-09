"""enum_map round-trip tests — CONFIG ข้อ 1: ไป-กลับครบทุก member."""
from db.enum_map import (
    ACTIVITY_STATUS_FROM_DB,
    ACTIVITY_STATUS_TO_DB,
    ACTIVITY_TYPE_FROM_DB,
    ACTIVITY_TYPE_TO_DB,
    APPLY_MODE_FROM_DB,
    APPLY_MODE_TO_DB,
    DIRECTION_FROM_DB,
    DIRECTION_TO_DB,
    DIAG_STATUS_FROM_DB,
    DIAG_STATUS_TO_DB,
    PARAMETER_FROM_DB,
    PARAMETER_TO_DB,
    PRED_STATUS_FROM_DB,
    PRED_STATUS_TO_DB,
    REC_STATUS_FROM_DB,
    REC_STATUS_TO_DB,
    SEVERITY_FROM_DB,
    SEVERITY_TO_DB,
    SIGNAL_SOURCE_FROM_DB,
    SIGNAL_SOURCE_TO_DB,
    URGENCY_FROM_DB,
    URGENCY_TO_DB,
    ZONE_FROM_DB,
    ZONE_TO_DB,
)

# (to_db, from_db, expected db names in python-member order)
CASES = [
    (PARAMETER_TO_DB, PARAMETER_FROM_DB,
     ["DO", "NH3", "NO2_N", "pH", "Temperature", "Salinity"]),
    (ZONE_TO_DB, ZONE_FROM_DB, ["optimal", "stress", "high_risk", "critical"]),
    (SEVERITY_TO_DB, SEVERITY_FROM_DB, ["optimal", "stress", "elevated_risk", "critical"]),
    (DIRECTION_TO_DB, DIRECTION_FROM_DB, ["low", "high"]),
    (ACTIVITY_TYPE_TO_DB, ACTIVITY_TYPE_FROM_DB,
     ["feeding", "aeration", "alkalinity", "lime", "probiotic", "water_change"]),
    (ACTIVITY_STATUS_TO_DB, ACTIVITY_STATUS_FROM_DB, ["pending", "done", "skipped"]),
    (URGENCY_TO_DB, URGENCY_FROM_DB, ["urgent", "non_urgent"]),
    (REC_STATUS_TO_DB, REC_STATUS_FROM_DB,
     ["pending", "snoozed", "applied", "dismissed", "expired"]),
    (APPLY_MODE_TO_DB, APPLY_MODE_FROM_DB, ["fixed", "pick_window"]),
    (PRED_STATUS_TO_DB, PRED_STATUS_FROM_DB, ["active", "ended"]),
    (DIAG_STATUS_TO_DB, DIAG_STATUS_FROM_DB, ["open", "closed"]),
    (SIGNAL_SOURCE_TO_DB, SIGNAL_SOURCE_FROM_DB,
     ["episode", "prediction", "detector"]),
]


def test_all_pairs():
    for i, (to_db, from_db, expected) in enumerate(CASES):
        assert len(to_db) == len(expected), f"case {i}: {len(to_db)} != {len(expected)}"
        assert list(to_db.values()) == expected, f"case {i}: db names mismatch {list(to_db.values())}"
        # round-trip: python -> db -> python
        for py, db in to_db.items():
            assert from_db[db] == py, f"case {i}: {py} -> {db} -> {from_db.get(db)}"
        # round-trip: db -> python -> db
        for db, py in from_db.items():
            assert to_db[py] == db, f"case {i}: {db} -> {py} -> {to_db.get(py)}"


def test_no_other_activity_kind():
    assert "other" not in ACTIVITY_TYPE_TO_DB.values()
    assert len(ACTIVITY_TYPE_TO_DB) == 6


def test_known_mappings():
    # engine typos map to clean db names (CONFIG ข้อ 1)
    from identity.analysis.models import ActivityType, ApplyMode, Urgency
    from identity.parameters.pond_parameter_enum import PondParameters
    from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
    from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType

    assert PARAMETER_TO_DB[PondParameters.tem] == "Temperature"
    assert PARAMETER_TO_DB[PondParameters.NO2_N] == "NO2_N"
    assert ZONE_TO_DB[ThresholdLevelType.HighRisk] == "high_risk"
    assert SEVERITY_TO_DB[SeverityLevelType.ElevatedRisk] == "elevated_risk"
    assert ACTIVITY_TYPE_TO_DB[ActivityType.waterChange] == "water_change"
    assert URGENCY_TO_DB[Urgency.nonUrgent] == "non_urgent"
    assert APPLY_MODE_TO_DB[ApplyMode.pickWindow] == "pick_window"
