from datetime import datetime

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.threshold_units.threshold_level.threshold_direction import ThresholdDirection

class AnalysisReportModel:
    dateTime : datetime
    parameter : PondParameters
    thresholdStatus : ThresholdLevelType
    thresholdDirection : ThresholdDirection | None
    severity: SeverityModel

    def __init__(
        self,
        *,
        dateTime : datetime,
        parameter : PondParameters,
        thresholdStatus : ThresholdLevelType,
        severity : SeverityModel,
        thresholdDirection : ThresholdDirection | None = None
    ):
        self.dateTime = dateTime
        self.parameter = parameter
        self.thresholdStatus = thresholdStatus
        self.thresholdDirection = thresholdDirection
        self.severity = severity

    @property
    def severityStatus(self) -> SeverityLevelType:
        return self.severity.severityLevel

    @property
    def description(self) -> str:
        return self.severity.severityDescription.description

    @property
    def guidance(self) -> str:
        return self.severity.severityDescription.guidance