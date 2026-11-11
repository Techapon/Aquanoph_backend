from identity.units.severity_units.severity_elavuator.severity_escalation_policy import EscalationPolicy
from identity.units.severity_units.severity_description.severity_des_set_builder import build_level_severity_des_set
from identity.units.severity_units.severity_description.severity_content import DO_CONTENT
from identity.units.severity_units.severity_description.severity_des_set_model import SeverityDesSetModel
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def DO_EscalationPolicy() -> EscalationPolicy:
    return EscalationPolicy()


def DO_SeverityDesSet() -> SeverityDesSetModel:
    context = SeverityTextContext(
        parameter_label="DO",
        direction_label=None,
        abnormal_label="DO ต่ำ",
    )
    return build_level_severity_des_set(context=context, contents=DO_CONTENT)
