from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_builder import build_level_severity_des_set
from identity.units.severity_units.severity_description.severity_content import NH3_CONTENT
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def NH3_EscalationPolicy() -> EscalationPolicy:
    return EscalationPolicy()


def NH3_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="NH3",
        direction_label=None,
        abnormal_label="NH3 สูง",
    )
    return build_level_severity_des_set(context=context, contents=NH3_CONTENT)
