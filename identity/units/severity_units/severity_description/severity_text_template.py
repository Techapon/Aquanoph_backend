"""Template/structure layer for severity descriptions (SEVERITY_TEXT_REFACTOR_SPEC).

`description` is built from structured context, never hardcoded per parameter.
Mockup content (detail/guidance) lives in severity_content.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeverityTextContext:
    """Structured inputs the system actually knows for a parameter side."""

    parameter_label: str       # "DO", "NH3", "NO2-N", "Salinity", "pH", "อุณหภูมิน้ำ"
    direction_label: str | None # "ต่ำ", "สูง", None (Level)
    abnormal_label: str        # "DO ต่ำ", "NH3 สูง", "pH สูง"


class SeverityTextTemplate:
    """Builds `description` from context + severity_state (no parameter names in callers)."""

    @staticmethod
    def build_description(
        *,
        parameter_label: str,
        direction_label: str | None,
        severity_state: str,
    ) -> str:
        # Direction word is concatenated directly (matches spec examples:
        # "pH" + "ต่ำ" + "กว่าช่วงเหมาะสมเล็กน้อย" -> "pH ต่ำกว่าช่วงเหมาะสมเล็กน้อย").
        # Without direction, severity_state already carries the direction word
        # (e.g. Level "ต่ำกว่าช่วงเหมาะสมเล็กน้อย").
        if direction_label:
            return f"{parameter_label}{direction_label}{severity_state}"
        return f"{parameter_label} {severity_state}"
