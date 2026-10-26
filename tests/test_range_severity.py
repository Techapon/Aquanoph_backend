"""
รันจาก root ของโปรเจกต์:  pytest tests/test_range_severity.py -v
ครอบคลุม: classifier, การแยก low/high, recurrence รายฝั่ง, Recovery Hold, การกรอง parameter, Level model เดิม
"""
from datetime import datetime, timedelta

import pytest

from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.parameters.pond_parameter_enum import PondParameters
from identity.parameters.pond_parameter_history_model import PondParametersHistoryModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from identity.units.severity_units.severity_description.severity_des_set_model import (
    AnySeverityDesSet,
    RangeSeverityDesSet,
    SeverityDesSetModel,
)
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    AnyEscalationPolicy,
    EscalationPolicy,
    RangeEscalationPolicy,
)
from identity.units.severity_units.severity_elavuator.severity_evaluator import SeverityEvaluator
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType as S
from identity.units.threshold_units.threshold.threshold_model import LevelThreshold, RangeThreshold
from identity.units.threshold_units.threshold.threshold_type_level_enum import LevelType
from identity.units.threshold_units.threshold.value_range import Range, RangeType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection as D
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType as T
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel

from identity.parameters.pond_parameter_history_model import PondParametersHistoryModel
NOW = datetime(2026, 10, 25, 12, 0)
TEM, PH, DO = PondParameters.tem, PondParameters.pH, PondParameters.DO


# ---------- helpers ----------
def desSet(tag: str) -> SeverityDesSetModel:
    def d(name): return SeverityDescriptionModel(des=f"{tag}:{name}", detail="-", guid=f"{tag}:{name}:guid")
    return SeverityDesSetModel(
        abnormalLabel=tag,
        pureOptimal=d("pureOptimal"), needRocoveryEleveted=d("recElevated"), needRocoveryCritical=d("recCritical"),
        pureStress=d("pureStress"), continuousStressExceeded=d("contStress"), cumStressExceeded=d("cumStress"),
        pureHighRisk=d("pureHigh"), continuousHighRiskExceeded=d("contHigh"), cumHighRiskExceeded=d("cumHigh"),
        pureCritical=d("pureCritical"), episodeExceeded=d("episode"),
    )

RANGE_DES = RangeSeverityDesSet(low=desSet("LOW"), high=desSet("HIGH"))
RANGE_POL = RangeEscalationPolicy(low=EscalationPolicy(), high=EscalationPolicy())


def rep(minAgo, level, direction=None, severity=S.Optimal, parameter=TEM):
    sev = SeverityModel(severityLevel=severity, severityDes=SeverityDescriptionModel(des="x", detail="x", guid="x"))
    return AnalysisReportModel(
        dateTime=NOW - timedelta(minutes=minAgo), parameter=parameter,
        thresholdStatus=level, thresholdDirection=direction, severity=sev,
    )


def series(fromMinAgo, toMinAgo, level, direction=None, severity=S.Optimal, step=30, parameter=TEM):
    """สร้างตัวอย่างทุก step นาที จาก fromMinAgo ถึง toMinAgo (รวมปลายทาง)"""
    return [rep(m, level, direction, severity, parameter) for m in range(fromMinAgo, toMinAgo - 1, -step)]


def run(level, direction, hist,
        policy: AnyEscalationPolicy = RANGE_POL, des: AnySeverityDesSet = RANGE_DES):
    return SeverityEvaluator(
        currentThresholdLevelModel=ThresholdLevelModel(level=level, direction=direction),
        parameterDateTime=NOW, analysisHis=hist, policy=policy, descriptionSet=des,
    )


# ---------- Phase 2: classifier ----------
temp = RangeThreshold(
    parameter=TEM,
    optimal=Range(min=26, max=30), stress=Range(min=22, max=32), highRisk=Range(min=16, max=35),
    critical=Range(min=RangeType.noMin, max=RangeType.noMax),
)

@pytest.mark.parametrize("value, level, direction", [
    (28, T.Optimal, None), (26, T.Optimal, None), (30, T.Optimal, None),
    (25.9, T.Stress, D.Low), (22, T.Stress, D.Low),
    (21.9, T.HighRisk, D.Low), (16, T.HighRisk, D.Low),
    (15.9, T.Critical, D.Low),
    (30.1, T.Stress, D.High), (32, T.Stress, D.High),
    (32.1, T.HighRisk, D.High), (35, T.HighRisk, D.High),
    (35.1, T.Critical, D.High),
])
def test_range_classifier(value, level, direction):
    r = temp.checkThreshold(parameterValueNow=value)
    assert (r.level, r.direction) == (level, direction)

def test_range_rejects_bad_order_and_nan():
    with pytest.raises(ValueError):
        RangeThreshold(parameter=TEM, optimal=Range(min=26, max=30), stress=Range(min=27, max=32),
                       highRisk=Range(min=16, max=35), critical=Range(min=RangeType.noMin, max=RangeType.noMax))
    with pytest.raises(ValueError):
        temp.checkThreshold(parameterValueNow=float("nan"))

def test_level_threshold_has_no_direction():
    do = LevelThreshold(parameter=DO, levelType=LevelType.eqaMoreThan, optimal=6, stress=4.5, highRisk=3.5, critical=0)
    assert do.checkThreshold(parameterValueNow=4.0).direction is None

def test_optimal_with_direction_is_rejected():
    with pytest.raises(ValueError):
        ThresholdLevelModel(level=T.Optimal, direction=D.Low)


# ---------- Phase 5: evaluator (Range) ----------
def test_low_and_high_stress_are_not_summed():
    # Low 9h->4h แล้วสลับเป็น High โดยไม่ผ่าน Optimal; รวมกัน 9h (เกิน 8h) แต่แยกฝั่งแล้วแต่ละฝั่งไม่ถึง
    hist = series(540, 270, T.Stress, D.Low) + series(240, 30, T.Stress, D.High)
    r = run(T.Stress, D.High, hist)
    assert r.severityLevel == S.Stress
    assert r.severityDescription.description == "HIGH:pureStress"

def test_continuous_stress_escalates_with_direction_message():
    hist = series(510, 30, T.Stress, D.Low)                      # 8.5h ต่อเนื่อง
    r = run(T.Stress, D.Low, hist)
    assert r.severityLevel == S.ElevatedRisk
    assert r.severityDescription.description == "LOW:contStress"
    assert "LOW" in (r.severityDescription.appendDes or "")            # label ของฝั่งถูกใส่ในข้อความเชิงเวลา

def test_cumulative_stress_per_side():
    # Low stress สะสม 9h ใน 24h คั่นด้วย optimal -> Elevated; ฝั่ง high ที่ไม่มีประวัติ -> Stress
    hist = (series(900, 600, T.Stress, D.Low) + series(570, 540, T.Optimal)
            + series(510, 270, T.Stress, D.Low) + series(240, 30, T.Optimal))
    assert run(T.Stress, D.Low, hist).severityDescription.description == "LOW:cumStress"
    assert run(T.Stress, D.High, hist).severityLevel == S.Stress

def test_critical_is_immediate_and_directional():
    r = run(T.Critical, D.High, [])
    assert r.severityLevel == S.Critical and r.severityDescription.description == "HIGH:pureCritical"

def test_episode_recurrence_counts_same_side_only():
    two_high = (series(600, 570, T.HighRisk, D.High, S.ElevatedRisk) + series(540, 400, T.Optimal))
    r = run(T.HighRisk, D.High, two_high)
    assert r.severityLevel == S.Critical and r.severityDescription.description == "HIGH:episode"

    low_then_high = (series(600, 570, T.HighRisk, D.Low, S.ElevatedRisk) + series(540, 400, T.Optimal))
    r = run(T.HighRisk, D.High, low_then_high)               # ครั้งแรกเป็น low จึงไม่นับให้ high
    assert r.severityLevel == S.ElevatedRisk

def test_high_risk_continuous_critical():
    hist = series(180, 30, T.HighRisk, D.Low, S.ElevatedRisk)   # 3h > 150 นาที
    r = run(T.HighRisk, D.Low, hist)
    assert r.severityLevel == S.Critical and r.severityDescription.description == "LOW:contHigh"


# ---------- Recovery Hold ----------
def test_recovery_hold_uses_event_side_and_remaining_time():
    hist = [rep(60, T.HighRisk, D.High, S.ElevatedRisk), rep(30, T.Optimal)]
    r = run(T.Optimal, None, hist)
    assert r.severityLevel == S.Stress
    assert r.severityDescription.description == "HIGH:recElevated"
    assert "1.5" in (r.severityDescription.appendDes or "")          # hold 120 - optimal 30 = 90 นาที = 1.5 ชม. (stub MinuteToHours)

def test_recovery_hold_released_after_enough_optimal():
    hist = [rep(300, T.HighRisk, D.High, S.ElevatedRisk)] + series(250, 30, T.Optimal)
    assert run(T.Optimal, None, hist).severityLevel == S.Optimal

def test_critical_hold_is_longer_and_low_side_message():
    hist = [rep(200, T.Critical, D.Low, S.Critical)] + series(150, 30, T.Optimal)   # optimal 150 < 240
    r = run(T.Optimal, None, hist)
    assert r.severityLevel == S.Stress and r.severityDescription.description == "LOW:recCritical"

def test_elevated_then_stress_then_optimal_still_holds():
    # บั๊กเดิม: Elevated -> Stress -> Optimal เคย return Optimal ทันที
    hist = [rep(90, T.HighRisk, D.High, S.ElevatedRisk), rep(60, T.Stress, D.High, S.Stress)]
    assert run(T.Optimal, None, hist).severityLevel == S.Stress

def test_old_event_cleared_by_long_optimal_streak_then_blip():
    hist = ([rep(1000, T.Critical, D.High, S.Critical)] + series(900, 500, T.Optimal)
            + [rep(400, T.Stress, D.High, S.Stress)])
    assert run(T.Optimal, None, hist).severityLevel == S.Optimal

def test_pure_stress_history_does_not_hold():
    hist = series(120, 30, T.Stress, D.Low, S.Stress)
    assert run(T.Optimal, None, hist).severityLevel == S.Optimal


# ---------- parameter filter / immutability / Level model ----------
def test_history_model_rejects_wrong_parameter():
    with pytest.raises(ValueError):
        PondParametersHistoryModel(tem=series(120, 30, T.Stress, D.Low, parameter=PH))   # pH อยู่ผิดช่อง
    PondParametersHistoryModel(
        tem=series(120, 30, T.Stress, D.Low),
        pH=series(120, 30, T.Optimal, parameter=PH),
    )   

def test_history_list_not_mutated():
    hist = series(120, 30, T.Optimal)
    before = [r.dateTime for r in hist]
    run(T.Optimal, None, hist)
    assert [r.dateTime for r in hist] == before

def test_level_model_still_works_without_direction():
    hist = series(510, 30, T.Stress, None)
    r = run(T.Stress, None, hist, policy=EscalationPolicy(), des=desSet("DO"))
    assert r.severityLevel == S.ElevatedRisk and r.severityDescription.description == "DO:contStress"

def test_range_policy_without_direction_raises_clearly():
    with pytest.raises(ValueError):
        RANGE_POL.forDirection(None)


def test_parameter_model_builds_report_with_direction():
    from identity.parameters.parameter_model import ParameterModel
    pm = ParameterModel(
        identity=TEM, valueNow=33.0, dateTime=NOW, threshold=temp,
        escalationPolicy=RANGE_POL, severityDesSetModel=RANGE_DES, analysisHis=[],
    )
    r = pm.buildAnalysisReport()
    assert r.parameter == TEM
    assert (r.thresholdStatus, r.thresholdDirection) == (T.HighRisk, D.High)
    assert r.severityStatus == S.ElevatedRisk