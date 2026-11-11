"""Append text templates for SeverityEvaluator (SEVERITY_TEXT_REFACTOR_SPEC).

`appendDes` is runtime-generated time text. Only the evaluator formats these;
providers must never write appendDes themselves.

Hours/numbers are formatted by the evaluator through MinuteToHours before
being passed to these templates.
"""

# Continuous time beyond the limit, plus the current accumulated time.
CONTINUOUS = "{label} has been continuous beyond {limit_hours} h. Now {current_hours} h."

# Cumulative time in 24 h beyond the limit, plus the current accumulated time.
CUMULATIVE = "{label} totals {current_hours} h in 24 h, beyond the {limit_hours} h limit."

# Repeated high-risk episodes in 24 h.
EPISODE = "{label} recurred {episode_count} times in 24 h, beyond the {limit_count}-time limit."

# Recovery hold after an elevated-risk or critical event.
RECOVERY = "Event around {event_time}. About {remaining_hours} h remaining."

# Still in a non-exceeded state: warn about the upcoming limit.
PENDING_STRESS = (
    "{label} for {current_hours} h. "
    "If it continues to {limit_hours} h, the risk will increase."
)

PENDING_HIGH_RISK = (
    "{label} for {current_hours} h. "
    "If it continues to {limit_hours} h, the risk will increase further."
)
