from identity.units.severity_units.severity_description.severity_desscription_model import SeverityDescriptionModel
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType


class SeverityModel:
    severityLevel: SeverityLevelType
    severityDescription : SeverityDescriptionModel

    def __init__(
        self,
        *,
        severityLevel : SeverityLevelType,
        severityDes : SeverityDescriptionModel
    ):
        self.severityLevel = severityLevel
        self.severityDescription = severityDes
        