from datetime import datetime

from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_des_set_model import AnySeverityDesSet
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import AnyEscalationPolicy
from identity.units.severity_units.severity_elavuator.severity_helper import (
    ZONE_BY_LEVEL,
    buildTimeline,
    calZoneMetrics,
    countEpisodes,
    findPendingRecovery,
)
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection
from services.minute_to_hours import MinuteToHours


def SeverityEvaluator(
    *,
    currentThresholdLevelModel: ThresholdLevelModel,
    parameterDateTime: datetime,
    analysisHis: list[AnalysisReportModel],
    policy: AnyEscalationPolicy,
    descriptionSet: AnySeverityDesSet,
) -> SeverityModel:
    """
    Generic Severity Engine: ใช้ได้ทั้ง Level (direction=None) และ Range (direction=Low/High)
    ลำดับตัดสินตามเอกสาร: Critical -> Optimal(+Recovery Hold) -> Stress -> High-risk
    """
    level = currentThresholdLevelModel.level
    direction = currentThresholdLevelModel.direction

    # กรองเฉพาะ เฉพาะก่อนเวลาปัจจุบัน + เรียงเก่า -> ใหม่ (สร้าง list ใหม่ ไม่แก้ list ที่ส่งเข้ามา)
    history = sorted(
    (r for r in analysisHis if r.dateTime < parameterDateTime),
    key=lambda r: r.dateTime,
)

    # 1) CRITICAL: ทันที ไม่ต้องดูประวัติ
    if level == ThresholdLevelType.Critical:
        des = descriptionSet.forDirection(direction)
        return SeverityModel(severityLevel=SeverityLevelType.Critical, severityDes=des.pureCritical)

    # 2) OPTIMAL: อาจยังติด Recovery Hold
    if level == ThresholdLevelType.Optimal:
        return _evaluateOptimal(
            history=history, now=parameterDateTime, policy=policy, descriptionSet=descriptionSet
        )

    # 3-4) STRESS / HIGH RISK
    if level in ZONE_BY_LEVEL:
        return _evaluateStressOrHighRisk(
            level=level, direction=direction, history=history,
            now=parameterDateTime, policy=policy, descriptionSet=descriptionSet,
        )

    raise ValueError(f"ไม่รู้จัก threshold level: {level}")


def _evaluateOptimal(
    *,
    history: list[AnalysisReportModel],
    now: datetime,
    policy: AnyEscalationPolicy,
    descriptionSet: AnySeverityDesSet,
) -> SeverityModel:
    def holdMinuteOf(event: AnalysisReportModel) -> int:
        # ใช้ policy ของ "ฝั่งที่เกิดเหตุ" (Level parameter คืนชุดเดียวเสมอ)
        eventPolicy = policy.forDirection(event.thresholdDirection)
        if event.severityStatus == SeverityLevelType.Critical:
            return eventPolicy.CriticalRecoveryHoldMinute
        return eventPolicy.ElevatedRecoveryHoldMinute

    state = findPendingRecovery(history, now, holdMinuteOf)

    if state.event is None or state.optimalSince is None:
        return SeverityModel(
            severityLevel=SeverityLevelType.Optimal,
            severityDes=descriptionSet.pureOptimal,
        )

    event = state.event
    optimalMinute = (now - state.optimalSince).total_seconds() / 60
    remainingMinute = max(holdMinuteOf(event) - optimalMinute, 0)

    eventDes = descriptionSet.forDirection(event.thresholdDirection)
    base = (
        eventDes.needRocoveryCritical
        if event.severityStatus == SeverityLevelType.Critical
        else eventDes.needRocoveryEleveted
    )
    return SeverityModel(
        severityLevel=SeverityLevelType.Stress,   # แสดงเป็น Stress (Recovery Hold)
        severityDes=base.withAppend(
            f"เกิดเวลาประมาณ {event.dateTime:%d/%m/%Y %H:%M} เหลืออีก {MinuteToHours(remainingMinute)} ชม."
        ),
    )


def _evaluateStressOrHighRisk(
    *,
    level: ThresholdLevelType,
    direction: ThresholdDirection | None,
    history: list[AnalysisReportModel],
    now: datetime,
    policy: AnyEscalationPolicy,
    descriptionSet: AnySeverityDesSet,
) -> SeverityModel:
    pol = policy.forDirection(direction)
    des = descriptionSet.forDirection(direction)
    label = des.abnormalLabel

    timeline = buildTimeline(history, level, direction, now)
    metrics = calZoneMetrics(timeline, now, ZONE_BY_LEVEL[level], direction)

    isStress = level == ThresholdLevelType.Stress
    limitContinuous = pol.stressCountMinute if isStress else pol.HightRiskCountMinute
    limitCum = pol.stressCumIn24Hs if isStress else pol.HightRiskCumIn24Hs

    isContinuousExceeded = metrics.continuousMinute >= limitContinuous
    isCumExceeded = metrics.cumMinute >= limitCum

    continuousText = (
        f"{label}ต่อเนื่องเกิน {MinuteToHours(limitContinuous)} ชม. แล้ว "
        f"ปัจจุบัน {MinuteToHours(metrics.continuousMinute)} ชม."
    )
    cumText = (
        f"{label}สะสมเกิน {MinuteToHours(limitCum)} ชม. ใน 24 ชม. แล้ว "
        f"ปัจจุบันสะสม {MinuteToHours(metrics.cumMinute)} ชม."
    )

    # STRESS CASE
    if isStress:
        if isContinuousExceeded:
            return SeverityModel(
                severityLevel=SeverityLevelType.ElevatedRisk,
                severityDes=des.continuousStressExceeded.withAppend(continuousText),
            )
        if isCumExceeded:
            return SeverityModel(
                severityLevel=SeverityLevelType.ElevatedRisk,
                severityDes=des.cumStressExceeded.withAppend(cumText),
            )
        return SeverityModel(
            severityLevel=SeverityLevelType.Stress,
            severityDes=des.pureStress.withAppend(
                f"{label}มาแล้ว {MinuteToHours(metrics.continuousMinute)} ชม. "
                f"หากต่อเนื่องจนครบ {MinuteToHours(limitContinuous)} ชม. จะอันตรายขึ้น"
            ),
        )

    # HIGH RISK CASE
    episodeCount = countEpisodes(
        timeline, now, direction,
        separationHours=pol.EpisodeSeparationMinute / 60,
        windowHours=24,
    )
    if isContinuousExceeded:
        return SeverityModel(
            severityLevel=SeverityLevelType.Critical,
            severityDes=des.continuousHighRiskExceeded.withAppend(continuousText),
        )
    if isCumExceeded:
        return SeverityModel(
            severityLevel=SeverityLevelType.Critical,
            severityDes=des.cumHighRiskExceeded.withAppend(cumText),
        )
    if episodeCount >= pol.recurrenceEpisode24H:
        return SeverityModel(
            severityLevel=SeverityLevelType.Critical,
            severityDes=des.episodeExceeded.withAppend(
                f"{label}เข้าโซนเสี่ยงสูงซ้ำ {episodeCount} ครั้งใน 24 ชม. "
                f"(เกณฑ์ {pol.recurrenceEpisode24H} ครั้ง)"
            ),
        )
    return SeverityModel(
        severityLevel=SeverityLevelType.ElevatedRisk,
        severityDes=des.pureHighRisk.withAppend(
            f"{label}มาแล้ว {MinuteToHours(metrics.continuousMinute)} ชม. "
            f"หากต่อเนื่องจนครบ {MinuteToHours(limitContinuous)} ชม. จะอันตรายขึ้นมากกว่าเดิม"
        ),
    )