from datetime import datetime
from identity.units.severity_units.severity_elavuator.severity_escalation_policy import AnyEscalationPolicy
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_elavuator.severity_evaluator import SeverityEvaluator
from identity.units.threshold_units.threshold.threshold_model import Threshold
from identity.units.threshold_units.threshold_level.threshold_level_model import ThresholdLevelModel
from identity.formats.analysis_report.analysis_report_model import AnalysisReportModel
from identity.units.severity_units.severity_description.severity_des_set_model import AnySeverityDesSet

class ParameterModel:
    def __init__(
            self,
            *,
            identity: PondParameters,
            valueNow: float,
            dateTime: datetime,
            threshold: Threshold,
            escalationPolicy: AnyEscalationPolicy,
            severityDesSetModel: AnySeverityDesSet,
            analysisHis: list[AnalysisReportModel],
        ):
        self.identity = identity
        self.valueNow = valueNow
        self.dateTime = dateTime
        self.threshold = threshold
        self.escalationPolicy = escalationPolicy
        self.severityDesSetModel = severityDesSetModel
        self.analysisHis = analysisHis

    def checkParameterThreshold(self) -> ThresholdLevelModel:
        return self.threshold.checkThreshold(parameterValueNow = self.valueNow)

    def _evaluate(self, thresholdLevelModel: ThresholdLevelModel) -> SeverityModel:
        return SeverityEvaluator(
            currentThresholdLevelModel = thresholdLevelModel,
            analysisHis = self.analysisHis,
            policy = self.escalationPolicy,
            parameterDateTime = self.dateTime,
            descriptionSet = self.severityDesSetModel
        )

    def getCurrentSeverityLevel(self) -> SeverityModel:
        return self._evaluate(self.checkParameterThreshold())

    def buildAnalysisReport(self) -> AnalysisReportModel:
        """
        สร้าง report พร้อม thresholdDirection สำหรับบันทึกเป็นประวัติ
        (ประวัติที่ขาด direction จะทำให้รอบถัดไปนับ Range ไม่ได้)
        """
        thresholdLevelModel = self.checkParameterThreshold()
        severity = self._evaluate(thresholdLevelModel)
        return AnalysisReportModel(
            dateTime = self.dateTime,
            parameter = self.identity,
            thresholdStatus = thresholdLevelModel.level,
            thresholdDirection = thresholdLevelModel.direction,
            severity = severity,
            value = self.valueNow,
        )