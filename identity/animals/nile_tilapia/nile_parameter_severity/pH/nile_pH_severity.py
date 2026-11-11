from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    EscalationPolicy,
    RangeEscalationPolicy,
)
from identity.units.severity_units.severity_description.severity_des_set_builder import (
    build_range_side_severity_des_set,
)
from identity.units.severity_units.severity_description.severity_content import (
    PH_HIGH_CONTENT,
    PH_LOW_CONTENT,
)
from identity.units.severity_units.severity_description.severity_des_set_model import RangeSeverityDesSet
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def pH_EscalationPolicy() -> RangeEscalationPolicy:
    return RangeEscalationPolicy(
        low=EscalationPolicy(),
        high=EscalationPolicy(),
    )


def pH_SeverityDesSet() -> RangeSeverityDesSet:
    low_context = SeverityTextContext(
        parameter_label="pH",
        direction_label="ต่ำ",
        abnormal_label="pH ต่ำ",
    )
    high_context = SeverityTextContext(
        parameter_label="pH",
        direction_label="สูง",
        abnormal_label="pH สูง",
    )
    return RangeSeverityDesSet(
        low=build_range_side_severity_des_set(context=low_context, contents=PH_LOW_CONTENT),
        high=build_range_side_severity_des_set(context=high_context, contents=PH_HIGH_CONTENT),
    )
