from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_desscription_model import SeverityDescriptionModel
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
                    des = "เสี่ยงตาายนใเวลาไม่นาน",
                    guid = "เติม O2 ทันทีเพื่อรักษาระดับที่เหมาะสม"
                )
            )

    # severity
    severityCountMinute:int = policy.stressCountMinute if currentThresholdLevel is ThresholdLevelType.Stress else policy.HightRiskCountMinute
    severityCumIn24Hs:int = policy.stressCumIn24Hs if currentThresholdLevel is ThresholdLevelType.Stress else policy.HightRiskCumIn24Hs

    # OPTIMAL CASE
    if currentThresholdLevel == ThresholdLevelType.Optimal:

        lastestSeverity = next(x for x in analysisHis if x.severityStatus != SeverityLevelType.Optimal)
        lastestOverOptimal = next(x for x in analysisHis if x.thresholdStatus != ThresholdLevelType.Optimal)

        recoveryHoldMinute:int = policy.HightRiskRecoveryHoldMinute if lastestSeverity.severityStatus == SeverityLevelType.ElevatedRisk else policy.CriticalRecoveryHoldMinute
        diffMinute = calDiffMinute(parameterDateTime,lastestOverOptimal.dateTime)

        if (
            lastestSeverity.severityStatus == SeverityLevelType.Stress and 
            lastestOverOptimal.thresholdStatus == ThresholdLevelType.Stress
            ) or diffMinute >= recoveryHoldMinute:
            return SeverityModel(
                severityLevel = SeverityLevelType.Optimal,
                severityDes = SeverityDescriptionModel(
                    des = "ปลาอยู่ในระดับที่เหมาะสมแล้ว",
                    guid = "ดูแลเติม o2 ให้เหมาะสมเสมอ"
                )
            )
        else:
            match lastestSeverity.severityStatus:
                case SeverityLevelType.ElevatedRisk:
                     return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = SeverityDescriptionModel(
                            des = f"ยังมีความเครียดจาก DO ในระดับ 'เสี่ยงสูง' ที่ตกไม่เมื่อ เวลาประมาณ {lastestOverOptimal.dateTime} น.",
                            guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอ"
                        )
                    )
                case SeverityLevelType.Critical:
                    return SeverityModel(
                        severityLevel = SeverityLevelType.Stress,
                        severityDes = SeverityDescriptionModel(
                            des = f"ยังมีความเครียดจาก DO ในระดับ 'อันตราย' ที่ตกไม่เมื่อ เวลาประมาณ {lastestOverOptimal.dateTime} น.",
                            guid = "เฝ้าระวังดูแลเติม o2 ให้เหมาะสมเสมอ"
                        )
                    )
             
    # STRESS CASE (Continous)
    # if currentThresholdLevel == ThresholdLevelType.Stress:
    #     for reportIndex in range(len(analysisHis)):
    #         focusReport = analysisHis[reportIndex]
    #         diffMinute = calDiffMinute(
    #             parameterDateTime,
    #             focusReport.dateTime
    #         )
            

    return SeverityModel(
        severityLevel = SeverityLevelType.Stress,
        severityDes = SeverityDescriptionModel(
            des = "เครียดเล้กน้อย",
            guid = "เติม O2 เพื่อรักษาระดับที่เหมาะสม"
        )
    )
    