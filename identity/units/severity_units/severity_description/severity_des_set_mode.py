from identity.units.severity_units.severity_description.severity_description_model import SeverityDescriptionModel

class SeverityDesSetModel:

    # # Optimal
    # pureOptimal: SeverityDescriptionModel
    # needRocoveryEleveted:SeverityDescriptionModel
    # needRocoveryCritical:SeverityDescriptionModel

    # # Stress
    # pureStress: SeverityDescriptionModel
    # continuousStressExceeded: SeverityDescriptionModel
    # cumStressExceeded: SeverityDescriptionModel

    # # High Risk
    # pureHighRisk: SeverityDescriptionModel
    # continuousHighRiskExceeded: SeverityDescriptionModel
    # cumHighRiskExceeded: SeverityDescriptionModel

    # # Episode
    # episodeExceeded: SeverityDescriptionModel

    # # Critical
    # pureCritical: SeverityDescriptionModel

    def __init__(
        self,
        *,
        # Optimal
        pureOptimal: SeverityDescriptionModel,
        needRocoveryEleveted:SeverityDescriptionModel,
        needRocoveryCritical:SeverityDescriptionModel,

        # Stress
        pureStress: SeverityDescriptionModel,
        continuousStressExceeded: SeverityDescriptionModel,
        cumStressExceeded: SeverityDescriptionModel,

        # High Risk
        pureHighRisk: SeverityDescriptionModel,
        continuousHighRiskExceeded: SeverityDescriptionModel,
        cumHighRiskExceeded: SeverityDescriptionModel,

        # Critical
        pureCritical: SeverityDescriptionModel,

        # Episode
        episodeExceeded: SeverityDescriptionModel
    ):
        self.pureOptimal = pureOptimal
        self.needRocoveryEleveted = needRocoveryEleveted
        self.needRocoveryCritical = needRocoveryCritical

        self.pureStress = pureStress
        self.continuousStressExceeded = continuousStressExceeded
        self.cumStressExceeded = cumStressExceeded

        self.pureHighRisk = pureHighRisk
        self.continuousHighRiskExceeded = continuousHighRiskExceeded
        self.cumHighRiskExceeded = cumHighRiskExceeded

        self.pureCritical = pureCritical

        self.episodeExceeded = episodeExceeded