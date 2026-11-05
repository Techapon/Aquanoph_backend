"""Unit tests for SeverityReportView per PHASE_0_prep.md §0.4 and PHASE_1_foundation.md."""
from datetime import datetime, timedelta
import pytest

from identity.analysis.severity_view import (
    SeverityReportView,
    isOptimalZone,
    severityRank,
    toView,
    toViews,
    zoneRank,
)
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from tests.support.factories import makeReport, makeView


# 1. toView maps all fields correctly for one report per parameter
@pytest.mark.parametrize("param", [
    PondParameters.DO,
    PondParameters.pH,
    PondParameters.tem,
    PondParameters.NH3,
    PondParameters.NO2_N,
    PondParameters.salinity,
])
def test_to_view_maps_all_fields_for_all_parameters(param):
    now = datetime(2026, 10, 25, 12, 0)
    rep = makeReport(
        parameter=param,
        dateTime=now,
        thresholdStatus=ThresholdLevelType.Stress,
        thresholdDirection=ThresholdDirection.Low if param in (PondParameters.pH, PondParameters.tem) else None,
        severityLevel=SeverityLevelType.ElevatedRisk,
        value=12.3,
    )
    view = toView(rep)
    assert view.parameter == param
    assert view.time == now
    assert view.value == 12.3
    assert view.zone == ThresholdLevelType.Stress
    assert view.severity == SeverityLevelType.ElevatedRisk


# 2. Recovery Hold report -> isOptimalZone True while severity rank == Stress rank
def test_recovery_hold_is_optimal_zone_with_stress_rank():
    now = datetime(2026, 10, 25, 12, 0)
    rep = makeReport(
        parameter=PondParameters.DO,
        dateTime=now,
        thresholdStatus=ThresholdLevelType.Optimal,
        thresholdDirection=None,
        severityLevel=SeverityLevelType.Stress,  # Recovery Hold displays as Stress
        value=6.0,
    )
    view = toView(rep)
    assert isOptimalZone(view) is True
    assert severityRank(view) == severityRank(SeverityLevelType.Stress)
    assert severityRank(view) == 1


# 3. zoneRank / severityRank ordering for all members (handles HighRisk vs ElevatedRisk naming mismatch)
def test_zone_and_severity_rank_ordering():
    # Zone order: Optimal (0) < Stress (1) < HighRisk (2) < Critical (3)
    assert zoneRank(ThresholdLevelType.Optimal) == 0
    assert zoneRank(ThresholdLevelType.Stress) == 1
    assert zoneRank(ThresholdLevelType.HighRisk) == 2
    assert zoneRank(ThresholdLevelType.Critical) == 3

    # Severity order: Optimal (0) < Stress (1) < ElevatedRisk (2) < Critical (3)
    assert severityRank(SeverityLevelType.Optimal) == 0
    assert severityRank(SeverityLevelType.Stress) == 1
    assert severityRank(SeverityLevelType.ElevatedRisk) == 2
    assert severityRank(SeverityLevelType.Critical) == 3

    # Also accepts SeverityReportView
    vHigh = makeView(zone=ThresholdLevelType.HighRisk, severity=SeverityLevelType.ElevatedRisk)
    assert zoneRank(vHigh) == 2
    assert severityRank(vHigh) == 2


# 4. toViews sorts ascending and is stable for equal times
def test_to_views_sorts_ascending_and_stable():
    t1 = datetime(2026, 10, 25, 10, 0)
    t2 = datetime(2026, 10, 25, 11, 0)
    t3 = datetime(2026, 10, 25, 12, 0)

    r1 = makeReport(PondParameters.DO, t1, value=6.0)
    r2a = makeReport(PondParameters.DO, t2, value=5.5)
    r2b = makeReport(PondParameters.pH, t2, value=7.5)
    r3 = makeReport(PondParameters.DO, t3, value=5.0)

    # Pass in shuffled order
    views = toViews([r3, r2a, r1, r2b])
    assert len(views) == 4
    assert [v.time for v in views] == [t1, t2, t2, t3]
    # Stability for equal times: r2a comes before r2b
    assert views[1].parameter == PondParameters.DO
    assert views[2].parameter == PondParameters.pH


# 5. toView raises ValueError for an incomplete report
def test_to_view_raises_on_missing_value():
    now = datetime(2026, 10, 25, 12, 0)
    repNoVal = makeReport(
        parameter=PondParameters.DO,
        dateTime=now,
        value=None,  # type: ignore
    )
    with pytest.raises(ValueError):
        toView(repNoVal)


# 6. Input history list is not mutated
def test_input_history_list_not_mutated():
    t1 = datetime(2026, 10, 25, 12, 0)
    t2 = datetime(2026, 10, 25, 10, 0)
    r1 = makeReport(PondParameters.DO, t1, value=6.0)
    r2 = makeReport(PondParameters.DO, t2, value=5.0)

    rawList = [r1, r2]
    originalOrder = list(rawList)
    toViews(rawList)
    assert rawList == originalOrder
