import pytest

from scripts.review_local_research_preflight import independent_power


def test_normal_power_null_and_symmetry():
    assert independent_power(64, 0, .16, .05) == pytest.approx(.05)
    assert independent_power(128, .01, .16, .05) == pytest.approx(
        independent_power(128, -.01, .16, .05))


def test_sufficient_question_groups_raise_power():
    assert independent_power(64, .01, .16, .05) < .1
    assert independent_power(2000, .01, .16, .05) < .8
    assert independent_power(2010, .01, .16, .05) >= .8
