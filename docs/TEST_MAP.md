# TEST_MAP — T1…T18 + Cases 1–3 → test functions

| Spec case | Test function(s) | File |
|---|---|---|
| T1 | `test_T1_diagnostic_causes_through_orchestrator` | `tests/scenarios/test_scenarios_core.py` |
| T1b | `test_T1b_with_hot_temp` | `tests/scenarios/test_scenarios_core.py` |
| T2 (Case 2 pred part) | `test_T2_case2_prediction_and_aerate_rec` | `tests/scenarios/test_scenarios_core.py` |
| T3 | `test_T3_apply_and_prediction_mitigated` | `tests/scenarios/test_scenarios_core.py` |
| T4 | `test_T4_meal_reduced_expires_prediction_and_rec` | `tests/scenarios/test_scenarios_core.py` |
| T5 | `test_T5_apply_skip_new_rec_and_T18_shortened_still_blocked` | `tests/scenarios/test_scenarios_core.py` |
| T6 | `test_T6_full_diagnostic_with_activity_revision` | `tests/scenarios/test_scenarios_core.py` |
| T7 | `test_T7_ph_swing_creates_alkalinity_and_stays` | `tests/scenarios/test_scenarios_core.py` |
| T8 | `test_T8_snooze_then_urgency_raise` | `tests/scenarios/test_scenarios_core.py` |
| T9 | `test_T9_stale_keeps_urgent_rec` | `tests/scenarios/test_scenarios_core.py` |
| T10 | `test_T10_declined_then_critical_allows_new` | `tests/scenarios/test_scenarios_core.py` |
| T11 | `test_T11_repeat_and_T12_nh3_and_T13_time_window` | `tests/scenarios/test_scenarios_core.py` |
| T12 (Case 3 pred part) | `test_case3_golden_water_change_text` | `tests/scenarios/test_scenarios_text.py` |
| T13 | `test_T11_repeat_and_T12_nh3_and_T13_time_window` | `tests/scenarios/test_scenarios_core.py` |
| T14 (D15 examples) | `test_T14_d15_examples_and_T15_T16_water_change` | `tests/scenarios/test_scenarios_core.py` |
| T15 | `test_T14_d15_examples_and_T15_T16_water_change` | `tests/scenarios/test_scenarios_core.py` |
| T16 | `test_T14_d15_examples_and_T15_T16_water_change` | `tests/scenarios/test_scenarios_core.py` |
| T17 | `test_T14_d15_examples_and_T15_T16_water_change` | `tests/scenarios/test_scenarios_core.py` |
| T18 | `test_T5_apply_skip_new_rec_and_T18_shortened_still_blocked` | `tests/scenarios/test_scenarios_core.py` |
| Case 1 (text) | `test_case1_golden_diagnostic_text` | `tests/scenarios/test_scenarios_text.py` |
| Case 2 (text) | `test_case2_golden_recommendation_text` | `tests/scenarios/test_scenarios_text.py` |
| Case 3 (text) | `test_case3_golden_water_change_text` | `tests/scenarios/test_scenarios_text.py` |
| Idempotency | `test_explicit_case2_idempotency` | `tests/scenarios/test_scenarios_invariants.py` |
| Determinism | `test_determinism_no_mutation` | `tests/scenarios/test_scenarios_invariants.py` |
| Rule 5 | `test_rule5_night_only_do_night` | `tests/scenarios/test_scenarios_invariants.py` |
| O3 sources | `test_o3_sources_and_pond_edit` | `tests/scenarios/test_scenarios_invariants.py` |
| Long run | `test_long_run_invariants` | `tests/scenarios/test_scenarios_invariants.py` |
