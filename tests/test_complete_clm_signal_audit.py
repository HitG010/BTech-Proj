import pytest

from scripts.complete_clm_signal_audit import fixed_cost_sensitivity


def test_correct_cached_summary_schema_and_same_independent_half_endpoint():
    prior = {"statistics": {"conditions": {
        "k4_A_to_B": {"summary": {
            "clm_zero_shot": {"mean_accuracy": .95, "mean_tokens": 1500.},
            "confidence": {"mean_accuracy": .90, "mean_tokens": 500.}}},
        "k4_B_to_A": {"summary": {
            "clm_zero_shot": {"mean_accuracy": .90, "mean_tokens": 1600.},
            "confidence": {"mean_accuracy": .91, "mean_tokens": 600.}}},
        "k8_full": {"summary": {"deliberately": "incompatible and unused"}},
    }}}
    result = fixed_cost_sensitivity(prior)
    assert result["accuracy_difference"] == pytest.approx(.02)
    assert result["additional_tokens"] == 1000.
    assert result["break_even_lambda"] == pytest.approx(.02)


def test_old_unsupported_schema_fails_before_statistics():
    with pytest.raises(KeyError):
        fixed_cost_sensitivity({"statistics": {"conditions": {
            name: {"summary": {"clm_zero_shot": {"accuracy": .9, "tokens": 100}}}
            for name in ("k4_A_to_B", "k4_B_to_A")}}})
