from datetime import datetime
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_elavuator.severity_evaluator import SeverityEvaluator
from identity.units.threshold_units.threshold.threshold_model import Threshold
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel

class ParameterModel:
    def __init__(
            self,
            *,
            identity: PondParameters,
            valueNow: float,
            threshold: Threshold,
            escalationPolicy: EscalationPolicy,
            analysisHis: list[AnalysisReportModel],
            dateTime: datetime
        ):
        self.identity = identity
        self.valueNow = valueNow
        self.threshold = threshold
        self.escalationPolicy = escalationPolicy
        self.analysisHis = analysisHis
        self.dateTime = dateTime

    def checkParameterThreshold(self) -> ThresholdLevelModel:
        return self.threshold.checkThreshold(parameterValueNow = self.valueNow)

    def getCurrentSeverityLevel(self) -> SeverityModel:
        return SeverityEvaluator(
            currentThresholdLevelModel = self.checkParameterThreshold(),
            analysisHis = self.analysisHis,
            policy = self.escalationPolicy,
            parameterDateTime = self.dateTime
        )
