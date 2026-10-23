from datetime import datetime

from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.severity_units.severity.severity_model import SeverityModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType

class AnalysisReportModel:
    dateTime : datetime
    parameter : PondParameters
    thresholdStatus : ThresholdLevelType
    severityStatus : SeverityLevelType
    description : str
    guidance : str

    def __init__(
        self,
        *,
        dateTime : datetime,
        parameter : PondParameters,
        thresholdStatus : ThresholdLevelType,
        severity : SeverityModel
    ):
        self.dateTime = dateTime
        self.parameter = parameter
        self.thresholdStatus = thresholdStatus
        self.severityStatus = severity.severityLevel
        self.description = severity.severityDescription.description
        self.guidance = severity.severityDescription.guidance