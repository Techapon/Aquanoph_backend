from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_desscription_model import SeverityDescriptionModel
from identity.units.severity_units.severity_elavuator.severity_helper import ZONE_BY_LEVEL, buildTimeline, calZoneMetrics,countEpisodes
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from services.dif_minute import calDiffMinute
from datetime import datetime

def SeverityEvaluator(
    *,
    currentThresholdLevelModel :ThresholdLevelModel,
    parameterDateTime:datetime,
    analysisHis: list[AnalysisReportModel],
    policy : EscalationPolicy
) -> SeverityModel:    
    analysisHis.sort(key  = lambda report:report.dateTime,reverse=True)
    currentThresholdLevel:ThresholdLevelType = currentThresholdLevelModel.level

    # CRITICAL CASE
    if (currentThresholdLevel == ThresholdLevelType.Critical):
        return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = SeverityDescriptionModel(
                    des = "เสี่ยงตายนใเวลาไม่นาน",
                    guid = "เติม O2 ทันทีเพื่อรักษาระดับที่เหมาะสม"
                )
            )

    # OPTIMAL CASE
    if currentThresholdLevel == ThresholdLevelType.Optimal:

        NEEDRECOVERY = (SeverityLevelType.ElevatedRisk, SeverityLevelType.Critical)
        optimalResult = SeverityModel(
            severityLevel = SeverityLevelType.Optimal,
            severityDes = SeverityDescriptionModel(
                des = "ปลาอยู่ในระดับที่เหมาะสมแล้ว",
                guid = "ดูแลเติม o2 ให้เหมาะสมเสมอ"
            )
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
                     return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = SeverityDescriptionModel(
                            des = f"ยังมีความเครียดจาก DO ในระดับ 'เสี่ยงสูง' ที่ตกไม่เมื่อ เวลาประมาณ {lastestOverStressSeverity.dateTime} น.",
                            guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอ"
                        )
                    )
                case SeverityLevelType.Critical:
                    return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = SeverityDescriptionModel(
                            des = f"ยังมีความเครียดจาก DO ในระดับ 'อันตราย' ที่ตกไม่เมื่อ เวลาประมาณ {lastestOverStressSeverity.dateTime} น.",
                            guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอ"
                        )
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
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ตํ่าในระดับ 'เครียด' มาเกิน {severityCountMinute/60} แล้ว ({metrics.continuousMinute/60}ชม.) ปลาเครียดมากกกก",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็ว"
                )
            )       
        elif isCumExceeded:
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ต่ำสะสมรวม {severityCumIn24Hs/60} ชม. ใน 24 ชม. ปลาเครียดมากกกก",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็ว"
                )
            )
        else :
            return SeverityModel(
                severityLevel = SeverityLevelType.Stress,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ต่ำกว่าระดับที่เหมาะสม ตอนนี้ปลาอาจ'เครียดน้อย-ปานกลาง' เริ่มเกยหัว ",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอ ก่อนจะสายเกินไป"
                )
            ) 

    # HIGH RISK CASE
    if currentThresholdLevel == ThresholdLevelType.HighRisk:
        if isContinuousExceeded :
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ตํ่าในระดับ 'เครียด' มาเกิน {severityCountMinute/60} แล้ว ({metrics.continuousMinute/60}ชม.) ปลาเสี่ยงตาย",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็วที่สุดดด"
                )
            )           
        elif isCumExceeded:
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ต่ำสะสมรวม {severityCumIn24Hs/60} ชม. ใน 24 ชม. ปลาเสี่ยงตาย",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็วที่สุดดด"
                )
            )
        elif isEpisodeExceeded:
            return SeverityModel(
                severityLevel = SeverityLevelType.Critical,
                severityDes = SeverityDescriptionModel(
                    des = f"เกิดเหตุการณ์ DO ต่ำรุนแรงแล้ว {episodeCount} ครั้งใน 24 ชม.",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็วที่สุดดด"
                )
            )
        else :
            return SeverityModel(
                severityLevel = SeverityLevelType.ElevatedRisk,
                severityDes = SeverityDescriptionModel(
                    des = f"DO ต่ำกว่าระดับที่เหมาะสม ตอนนี้ปลาอาจ'เครียดน้อย-สูง' เริ่มเกยหัว ",
                    guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอโดยเร็วที่สุดดด"
                )
            )

    