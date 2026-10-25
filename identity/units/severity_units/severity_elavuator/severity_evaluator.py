from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel
from identity.units.severity_units.severity_elavuator.severity_helper import ZONE_BY_LEVEL, buildTimeline, calZoneMetrics,countEpisodes
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from services.dif_minute import calDiffMinute
from datetime import datetime
from services.minute_to_hours import MinuteToHours

def SeverityEvaluator(
    *,
    currentThresholdLevelModel :ThresholdLevelModel,
    parameterDateTime:datetime,
    analysisHis: list[AnalysisReportModel],
    policy: EscalationPolicy,
    descriptionSet: SeverityDesSetModel
) -> SeverityModel:    
    analysisHis.sort(key  = lambda report:report.dateTime,reverse=True)
    currentThresholdLevel:ThresholdLevelType = currentThresholdLevelModel.level

    # CRITICAL CASE
    if (currentThresholdLevel == ThresholdLevelType.Critical):
        return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = descriptionSet.pureCritical
            )

    # OPTIMAL CASE
    if currentThresholdLevel == ThresholdLevelType.Optimal:

        NEEDRECOVERY = (SeverityLevelType.ElevatedRisk, SeverityLevelType.Critical)
        optimalResult = SeverityModel(
            severityLevel = SeverityLevelType.Optimal,
            severityDes = descriptionSet.pureOptimal
        )
        
        lastestSeverity = next((x for x in analysisHis if x.severityStatus != SeverityLevelType.Optimal),None)

        # if it's dont have any severity
        if lastestSeverity is None:
            return optimalResult

        # if it's pure stress
        if (
            lastestSeverity.severityStatus == SeverityLevelType.Stress and 
            lastestSeverity.thresholdStatus == ThresholdLevelType.Stress
        ):
            return optimalResult


        lastestOverStressSeverity = next((x for x in analysisHis if x.severityStatus in NEEDRECOVERY),None)

        # if it's dont have 
        if lastestOverStressSeverity is None:
            return optimalResult
            
        recoveryHoldMinute:int = policy.ElevatedRecoveryHoldMinute if lastestOverStressSeverity.severityStatus == SeverityLevelType.ElevatedRisk else policy.CriticalRecoveryHoldMinute
        diffMinute = calDiffMinute(parameterDateTime,lastestOverStressSeverity.dateTime)

        if lastestSeverity.thresholdStatus == ThresholdLevelType.Optimal and diffMinute >= recoveryHoldMinute:
            return optimalResult
        else:
            match lastestOverStressSeverity.severityStatus:
                case SeverityLevelType.ElevatedRisk:
                    descriptionSet.needRocoveryEleveted.appendDes = f"เกิดเวลาประมาณ {lastestOverStressSeverity.dateTime} เหลืออีก {MinuteToHours(recoveryHoldMinute-diffMinute)} ชม."
                    return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = descriptionSet.needRocoveryCritical
                    )
                case SeverityLevelType.Critical:
                    descriptionSet.needRocoveryCritical.appendDes = f"เกิดเวลาประมาณ {lastestOverStressSeverity.dateTime} เหลืออีก {MinuteToHours(recoveryHoldMinute-diffMinute)} ชม."
                    return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = descriptionSet.needRocoveryCritical
                    )
                case _:
                    return optimalResult
                
    timeline = buildTimeline(analysisHis, currentThresholdLevel, parameterDateTime)
    episodeCount = countEpisodes(
        timeline, parameterDateTime,
        separationHours=policy.EpisodeSeparationMinute/60,
        windowHours=24,
    )

    isEpisodeExceeded = episodeCount >= policy.recurrenceEpisode24H

    # severity
    severityCountMinute:int = policy.stressCountMinute if currentThresholdLevel is ThresholdLevelType.Stress else policy.HightRiskCountMinute
    severityCumIn24Hs:int = policy.stressCumIn24Hs if currentThresholdLevel is ThresholdLevelType.Stress else policy.HightRiskCumIn24Hs
             
    metrics = calZoneMetrics(timeline, parameterDateTime, ZONE_BY_LEVEL[currentThresholdLevel])
    isContinuousExceeded = metrics.continuousMinute >= severityCountMinute
    isCumExceeded = metrics.cumMinute >= severityCumIn24Hs

    # STRESS CASE
    if currentThresholdLevel == ThresholdLevelType.Stress:
        if isContinuousExceeded :
            descriptionSet.continuousStressExceeded.appendDes = f"ตํ่าต่อเนื่องเกิน {MinuteToHours(severityCountMinute)} ชม. แล้ว ปัจจุบัน {MinuteToHours(metrics.continuousMinute/60)} ชม."
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = descriptionSet.continuousStressExceeded
            )       
        elif isCumExceeded:
            descriptionSet.cumStressExceeded.appendDes = f"สะสมเกิด {MinuteToHours(severityCumIn24Hs)}ชม.ใน 24 ชม.แล้ว"
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = descriptionSet.cumStressExceeded
            )
        else :
            descriptionSet.pureStress.appendDes = f"หากต่อเนื่องจนครบ {MinuteToHours(severityCountMinute)} ชม. จะอัตรายขึ้น"
            return SeverityModel(
                severityLevel = SeverityLevelType.Stress,
                severityDes = descriptionSet.pureStress
            ) 

    # HIGH RISK CASE
    if currentThresholdLevel == ThresholdLevelType.HighRisk:
        if isContinuousExceeded :
            descriptionSet.continuousHighRiskExceeded.appendDes = f"ตํ่าต่อเนื่องเกิน {MinuteToHours(severityCountMinute)} ชม. แล้ว ปัจจุบัน {MinuteToHours(metrics.continuousMinute/60)} ชม."
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = descriptionSet.continuousHighRiskExceeded
            )           
        elif isCumExceeded:
            descriptionSet.cumHighRiskExceeded.appendDes = f"สะสมเกิด {MinuteToHours(severityCumIn24Hs)}ชม.ใน 24 ชม.แล้ว"
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = descriptionSet.cumHighRiskExceeded
            )
        elif isEpisodeExceeded:
            descriptionSet.episodeExceeded.appendDes = f"เกิดซํ้าเกิน {policy.recurrenceEpisode24H} ครั้ง ใน 24 ชม.แล้ว ปัจจุบันครั้งที่ {episodeCount}"
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = descriptionSet.episodeExceeded
            )
        else :
            descriptionSet.pureHighRisk.appendDes = f"หากต่อเนื่องจนครบ {MinuteToHours(severityCountMinute)} ชม. จะอัตรายขึ้นมากกว่าเดิม"
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = descriptionSet.pureHighRisk
            )

    