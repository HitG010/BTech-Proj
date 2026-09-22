import numpy as np
import pytest

from reasoning_budget.power import approximate_power, paired_summary, required_questions


def test_sample_size_scales_with_variance_and_effect():
    n = required_questions(0.02, 0.2)
    assert 783 <= n <= 786
    assert abs(required_questions(0.01, 0.2) - 4 * n) <= 4
    assert abs(required_questions(0.02, 0.4) - 4 * n) <= 4
    assert required_questions(0.02, 0.2, 0.9) > n
    assert 0.799 < approximate_power(n, 0.02, 0.2) < 0.802


def test_negative_effect_is_not_converted_to_superiority():
    assert required_questions(-0.01, 0.2) is None
    assert required_questions(0, 0.2) is None
    assert approximate_power(500, -0.01, 0.2) < 0.025
    assert approximate_power(500, 0, 0.2) == pytest.approx(0.025)
    with pytest.raises(ValueError):
        required_questions(0.01, 0)


def test_pairing_preserves_covariance_and_counts_whole_questions():
    base = np.array([[0, 10, 1], [1, 20, 2], [0, 30, 3], [1, 40, 4]], float)
    treatment = base.copy()
    treatment[:, 0] += [0, -0.1, 0.2, 0]
    result = paired_summary(treatment, base)
    assert result["n_questions"] == 4
    assert result["paired_sd"] == pytest.approx(np.std([0, -0.1, 0.2, 0], ddof=1))
    assert result["mean_utility_difference"] == pytest.approx(0.025)
    with pytest.raises(ValueError):
        paired_summary(treatment, base[:3])
