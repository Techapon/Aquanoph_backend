from identity.units.severity_units.severity_elavuator.severity_escalation_policy import (
    EscalationPolicy,
    RangeEscalationPolicy,
)
from identity.units.severity_units.severity_description.severity_des_set_builder import (
    build_range_side_severity_des_set,
)
from identity.units.severity_units.severity_description.severity_content import (
    TEMPERATURE_HIGH_CONTENT,
    TEMPERATURE_LOW_CONTENT,
)
from identity.units.severity_units.severity_description.severity_des_set_model import RangeSeverityDesSet
from identity.units.severity_units.severity_description.severity_text_template import SeverityTextContext


def temperature_EscalationPolicy() -> RangeEscalationPolicy:
    return RangeEscalationPolicy(
        low=EscalationPolicy(),
        high=EscalationPolicy(),
    )


def temperature_SeverityDesSet() -> RangeSeverityDesSet:
    low_context = SeverityTextContext(
        parameter_label="Water temperature",
        direction_label="low",
        abnormal_label="low water temperature",
    )
    high_context = SeverityTextContext(
        parameter_label="Water temperature",
        direction_label="high",
        abnormal_label="high water temperature",
    )
    return RangeSeverityDesSet(
        low=build_range_side_severity_des_set(context=low_context, contents=TEMPERATURE_LOW_CONTENT),
        high=build_range_side_severity_des_set(context=high_context, contents=TEMPERATURE_HIGH_CONTENT),
    )
