import math

import pytest
from scipy.stats import norm

from scripts.signal_study_power import detectable_effect, power, required_n, reservation_per_pair


def test_power_matches_independent_two_tailed_normal_calculation():
    n, effect, sd = 128, 0.01, 0.16
    z, shift = norm.ppf(0.975), effect * math.sqrt(n) / sd
    expected = norm.sf(z - shift) + norm.cdf(-z - shift)
    assert power(n, effect, sd) == pytest.approx(expected)
    assert power(n, 0, sd) == pytest.approx(0.05)


def test_required_n_is_minimal_and_negative_point_does_not_justify_confirmation():
    n = required_n(0.01, 0.16)
    assert n == 2010
    assert power(n, 0.01, 0.16) >= 0.8
    assert power(n - 1, 0.01, 0.16) < 0.8
    assert required_n(-0.014, 0.046) is None
    assert required_n(0, 0.046) is None


def test_detectable_effect_inverts_power():
    effect = detectable_effect(64, 0.16)
    assert power(64, effect, 0.16) == pytest.approx(0.8)
    assert effect > 0.05
    assert detectable_effect(128, 0.16) < effect


def test_reservation_includes_forced_closure_and_validates_endpoint():
    protocol = {"snapshot": {"config": {"answer_tokens": 512, "reasoning_tokens": 2048},
        "identity": {"backend": {"closure_tokens": 2}}, "jobs": [None] * 800,
        "planned_max_tokens": 1229600}}
    assert reservation_per_pair(protocol) == 3074
    protocol["snapshot"]["planned_max_tokens"] -= 2
    with pytest.raises(ValueError):
        reservation_per_pair(protocol)


@pytest.mark.parametrize("n,effect,sd", [(1, 0.01, 0.16), (64, 0.01, 0), (64, float("nan"), 0.16)])
def test_invalid_inputs(n, effect, sd):
    with pytest.raises(ValueError):
        power(n, effect, sd)
