# BACKLOG

Out-of-scope items tracked for future passes (per AGENT_CONTEXT.md.md section 8 Override O7).

## Thai text issues in severity engine (Phases 1-5)
- **Bug 2**: `NH3`, `NO2_N`, and `salinity` severity description files (`identity/animals/nile_tilapia/nile_parameter_severity/`) contain text referencing "DO" from earlier copy-paste. Update templates to reference their own parameter names once Thai text review is scheduled.
- **Bug 3**: `NH3_EscalationPolicy`, `NO2_N_EscalationPolicy`, and `salinity_EscalationPolicy` default `abnormalLabel` to `"ค่าผิดปกติ"` instead of parameter-specific labels like `"NH3"`, `"NO2-N"`, `"Salinity"`.

## Technical Debt & Architecture Items
- **Dead code `dif_minute.py`**: Function `calDiffMinute` is unused throughout the codebase.
- **Duplicated description factories**: Severity description factories for DO, NH3, NO2-N, and Salinity repeat identical boilerplate; should be consolidated into a shared factory helper (similar to pH and Temperature).
- **Unbounded history scan**: History scans in `SeverityEvaluator` and `findPendingRecovery` are O(N) over all historical reports without a time horizon cap. Needs bounding to `historyHorizonDays` (8 days).
