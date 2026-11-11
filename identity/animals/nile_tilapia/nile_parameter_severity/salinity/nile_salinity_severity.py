from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_builder import build_level_severity_des_set
from identity.units.severity_units.severity_description.severity_content import SALINITY_CONTENT
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def salinity_EscalationPolicy() -> EscalationPolicy:
    return EscalationPolicy()


def salinity_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="salinity",
        direction_label=None,
        abnormal_label="salinity สูง",
    )
    return build_level_severity_des_set(context=context, contents=SALINITY_CONTENT)
