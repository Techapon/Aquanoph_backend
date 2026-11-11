"""Builders that assemble SeverityDesSetModel from context + mockup content.

Per SEVERITY_TEXT_REFACTOR_SPEC:
- `description` comes from SeverityTextTemplate (no parameter names in callers)
- `detail` / `guidance` come from SeverityContent (parameter-owned mockup)
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
    """Build a Level parameter description set (direction_label is None)."""
    _check_contents(contents, context)
    # Level direction word comes from abnormal_label (e.g. "DO ต่ำ" -> "ต่ำ").
    dir_word = context.abnormal_label.rsplit(" ", 1)[-1]
    label = context.parameter_label

    return SeverityDesSetModel(
        abnormalLabel=context.abnormal_label,
        pureOptimal=_make(
            _desc(context, "อยู่ในระดับเหมาะสม", force_no_direction=True),
            contents["pureOptimal"],
        ),
        needRocoveryEleveted=_make(
            f"ปลากำลังฟื้นตัวจากเหตุการณ์ {context.abnormal_label} ระดับเสี่ยงสูง",
            contents["needRocoveryEleveted"],
        ),
        needRocoveryCritical=_make(
            f"ปลากำลังฟื้นตัวจากเหตุการณ์ {context.abnormal_label} ระดับวิกฤต",
            contents["needRocoveryCritical"],
        ),
        pureStress=_make(
            _desc(context, f"{dir_word}กว่าช่วงเหมาะสมเล็กน้อย"),
            contents["pureStress"],
        ),
        continuousStressExceeded=_make(
            _desc(context, f"{dir_word}ต่อเนื่องนาน"),
            contents["continuousStressExceeded"],
        ),
        cumStressExceeded=_make(
            _desc(context, f"{dir_word}สะสมหลายช่วงใน 24 ชม."),
            contents["cumStressExceeded"],
        ),
        pureHighRisk=_make(
            _desc(context, f"{dir_word}ถึงระดับเสี่ยงสูง"),
            contents["pureHighRisk"],
        ),
        continuousHighRiskExceeded=_make(
            _desc(context, f"{dir_word}ระดับเสี่ยงสูงต่อเนื่องนาน"),
            contents["continuousHighRiskExceeded"],
        ),
        cumHighRiskExceeded=_make(
            _desc(context, f"{dir_word}ระดับเสี่ยงสูงสะสมใน 24 ชม."),
            contents["cumHighRiskExceeded"],
        ),
        pureCritical=_make(
            _desc(context, f"{dir_word}ถึงระดับวิกฤต"),
            contents["pureCritical"],
        ),
        episodeExceeded=_make(
            _desc(context, f"{dir_word}ระดับเสี่ยงสูงเกิดซ้ำหลายครั้ง"),
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

    # Optimal has no direction; both sides share the same optimal wording.
    optimal_desc = f"{context.parameter_label} อยู่ในช่วงเหมาะสม"

    return SeverityDesSetModel(
        abnormalLabel=context.abnormal_label,
        pureOptimal=_make(optimal_desc, contents["pureOptimal"]),
        needRocoveryEleveted=_make(
            f"ปลากำลังฟื้นตัวจากเหตุการณ์ {context.abnormal_label} ระดับเสี่ยงสูง",
            contents["needRocoveryEleveted"],
        ),
        needRocoveryCritical=_make(
            f"ปลากำลังฟื้นตัวจากเหตุการณ์ {context.abnormal_label} ระดับวิกฤต",
            contents["needRocoveryCritical"],
        ),
        pureStress=_make(
            _desc(context, "กว่าช่วงเหมาะสมเล็กน้อย"),
            contents["pureStress"],
        ),
        continuousStressExceeded=_make(
            _desc(context, "ต่อเนื่องนาน"),
            contents["continuousStressExceeded"],
        ),
        cumStressExceeded=_make(
            _desc(context, "สะสมหลายช่วงใน 24 ชม."),
            contents["cumStressExceeded"],
        ),
        pureHighRisk=_make(
            _desc(context, "ถึงระดับเสี่ยงสูง"),
            contents["pureHighRisk"],
        ),
        continuousHighRiskExceeded=_make(
            _desc(context, "ระดับเสี่ยงสูงต่อเนื่องนาน"),
            contents["continuousHighRiskExceeded"],
        ),
        cumHighRiskExceeded=_make(
            _desc(context, "ระดับเสี่ยงสูงสะสมใน 24 ชม."),
            contents["cumHighRiskExceeded"],
        ),
        pureCritical=_make(
            _desc(context, "ถึงระดับวิกฤต"),
            contents["pureCritical"],
        ),
        episodeExceeded=_make(
            _desc(context, "ระดับเสี่ยงสูงเกิดซ้ำหลายครั้ง"),
            contents["episodeExceeded"],
        ),
    )
