from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_builder import build_level_severity_des_set
from identity.units.severity_units.severity_description.severity_content import NO2_N_CONTENT
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def NO2_N_EscalationPolicy() -> EscalationPolicy:
    return EscalationPolicy()


def NO2_N_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="NO2-N",
        direction_label=None,
        abnormal_label="NO2 สูง",
    )
    return build_level_severity_des_set(context=context, contents=NO2_N_CONTENT)
