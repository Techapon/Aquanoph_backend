"""Template/structure layer for severity descriptions (SEVERITY_TEXT_REFACTOR_SPEC).

`description` is built from structured context, never hardcoded per parameter.
Parameter content (detail/guidance) lives in severity_content.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeverityTextContext:
    """Structured inputs the system actually knows for a parameter side."""

    parameter_label: str        # "DO", "NH3", "NO2", "salinity", "pH", "Water temperature"
    direction_label: str | None  # "low", "high", None (Level)
    abnormal_label: str         # label used by the evaluator in appendDes


class SeverityTextTemplate:
    """Builds `description` from context + severity_state (no parameter names in callers)."""

    @staticmethod
    def build_description(
        *,
        parameter_label: str,
        direction_label: str | None,
        severity_state: str,
    ) -> str:
        # Examples:
        #   DO + None + "is slightly outside the suitable range"
        #       -> "DO is slightly outside the suitable range"
        #   pH + "low" + "is slightly outside the suitable range"
        #       -> "pH is low, slightly outside the suitable range"
        if direction_label:
            # Drop a leading "is " from state so "pH is low" is not followed by a second "is".
            state = severity_state.removeprefix("is ").removeprefix("has ")
            state = state[0].lower() + state[1:] if state else state
            return f"{parameter_label} is {direction_label}, {state}"
        return f"{parameter_label} {severity_state}"
