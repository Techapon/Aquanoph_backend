"""Builders that assemble SeverityDesSetModel from context + mockup content.

Per SEVERITY_TEXT_REFACTOR_SPEC:
- `description` comes from SeverityTextTemplate (no parameter names in callers)
- `detail` / `guidance` come from SeverityContent (parameter-owned content)
- `append` is always None here; appendDes is built only by SeverityEvaluator

Slot keys use the real SeverityDesSetModel field names (no renames).
"""
from identity.units.severity_units.severity_description.severity_content import SeverityContent
from identity.units.severity_units.severity_description.severity_des_set_model import (
    RangeSeverityDesSet,
    SeverityDesSetModel,
)
from identity.units.severity_units.severity_description.severity_description_model import (
    SeverityDescriptionModel,
)
from identity.units.severity_units.severity_description.severity_text_template import (
    SeverityTextContext,
    SeverityTextTemplate,
)

_SLOT_KEYS = (
    "pureOptimal",
    "needRocoveryEleveted",
    "needRocoveryCritical",
    "pureStress",
    "continuousStressExceeded",
    "cumStressExceeded",
    "pureHighRisk",
    "continuousHighRiskExceeded",
    "cumHighRiskExceeded",
    "pureCritical",
    "episodeExceeded",
)


def _desc(
    context: SeverityTextContext,
    severity_state: str,
    *,
    force_no_direction: bool = False,
) -> str:
    return SeverityTextTemplate.build_description(
        parameter_label=context.parameter_label,
        direction_label=None if force_no_direction else context.direction_label,
        severity_state=severity_state,
    )


def _make(
    description: str,
    content: SeverityContent,
) -> SeverityDescriptionModel:
    return SeverityDescriptionModel(
        des=description,
        detail=content.detail,
        guid=content.guidance,
        append=None,
    )


def _check_contents(contents: dict, context: SeverityTextContext) -> None:
    missing = [k for k in _SLOT_KEYS if k not in contents]
    if missing:
        raise ValueError(f"{context.parameter_label}: missing content slots {missing}")


def build_level_severity_des_set(
    *,
    context: SeverityTextContext,
    contents: dict,
) -> SeverityDesSetModel:
    """Build a Level parameter description set (no direction in context)."""
    _check_contents(contents, context)

    return SeverityDesSetModel(
        abnormalLabel=context.abnormal_label,
        pureOptimal=_make(
            _desc(context, "is in the suitable range", force_no_direction=True),
            contents["pureOptimal"],
        ),
        needRocoveryEleveted=_make(
            _desc(context, "is recovering from an elevated-risk event", force_no_direction=True),
            contents["needRocoveryEleveted"],
        ),
        needRocoveryCritical=_make(
            _desc(context, "is recovering from a critical event", force_no_direction=True),
            contents["needRocoveryCritical"],
        ),
        pureStress=_make(
            _desc(context, "is slightly outside the suitable range", force_no_direction=True),
            contents["pureStress"],
        ),
        continuousStressExceeded=_make(
            _desc(context, "has been outside the suitable range for a long stretch", force_no_direction=True),
            contents["continuousStressExceeded"],
        ),
        cumStressExceeded=_make(
            _desc(context, "has accumulated out-of-range time in 24 h", force_no_direction=True),
            contents["cumStressExceeded"],
        ),
        pureHighRisk=_make(
            _desc(context, "has reached the high-risk range", force_no_direction=True),
            contents["pureHighRisk"],
        ),
        continuousHighRiskExceeded=_make(
            _desc(context, "has stayed in the high-risk range for a long stretch", force_no_direction=True),
            contents["continuousHighRiskExceeded"],
        ),
        cumHighRiskExceeded=_make(
            _desc(context, "has accumulated high-risk time in 24 h", force_no_direction=True),
            contents["cumHighRiskExceeded"],
        ),
        pureCritical=_make(
            _desc(context, "has reached the critical range", force_no_direction=True),
            contents["pureCritical"],
        ),
        episodeExceeded=_make(
            _desc(context, "has entered high risk repeatedly", force_no_direction=True),
            contents["episodeExceeded"],
        ),
    )


def build_range_side_severity_des_set(
    *,
    context: SeverityTextContext,
    contents: dict,
) -> SeverityDesSetModel:
    """Build one side (low/high) of a Range parameter description set."""
    _check_contents(contents, context)

    return SeverityDesSetModel(
        abnormalLabel=context.abnormal_label,
        pureOptimal=_make(
            _desc(context, "is in the suitable range", force_no_direction=True),
            contents["pureOptimal"],
        ),
        needRocoveryEleveted=_make(
            _desc(context, "is recovering from an elevated-risk event"),
            contents["needRocoveryEleveted"],
        ),
        needRocoveryCritical=_make(
            _desc(context, "is recovering from a critical event"),
            contents["needRocoveryCritical"],
        ),
        pureStress=_make(
            _desc(context, "is slightly outside the suitable range"),
            contents["pureStress"],
        ),
        continuousStressExceeded=_make(
            _desc(context, "has been outside the suitable range for a long stretch"),
            contents["continuousStressExceeded"],
        ),
        cumStressExceeded=_make(
            _desc(context, "has accumulated out-of-range time in 24 h"),
            contents["cumStressExceeded"],
        ),
        pureHighRisk=_make(
            _desc(context, "has reached the high-risk range"),
            contents["pureHighRisk"],
        ),
        continuousHighRiskExceeded=_make(
            _desc(context, "has stayed in the high-risk range for a long stretch"),
            contents["continuousHighRiskExceeded"],
        ),
        cumHighRiskExceeded=_make(
            _desc(context, "has accumulated high-risk time in 24 h"),
            contents["cumHighRiskExceeded"],
        ),
        pureCritical=_make(
            _desc(context, "has reached the critical range"),
            contents["pureCritical"],
        ),
        episodeExceeded=_make(
            _desc(context, "has entered high risk repeatedly"),
            contents["episodeExceeded"],
        ),
    )
