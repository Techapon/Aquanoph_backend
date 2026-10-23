from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_description.severity_desscription_model import SeverityDescriptionModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy


def SeverityEvaluator(
    *,
    currentThresholdLevel :ThresholdLevelModel,
    analysisHis: list[AnalysisReportModel],
    policy : EscalationPolicy
) -> SeverityModel:

    

    return SeverityModel(
        severityLevel = SeverityLevelType.Stress,
        severityDes = SeverityDescriptionModel(
            des = "เครียดเล้กน้อย",
            guid = "เติม O2 เพื่อรักษาระดับที่เหมาะสม"
        )
    )
    