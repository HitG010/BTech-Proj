"""Independent accounting checks for the feasibility result reviewer."""

import numpy as np
import pytest

from scripts.review_router_feasibility import measured


def test_review_charges_sunk_direct_and_thinking_and_distinguishes_harms():
    d = np.array([[[0., 100., 2.], [1., 100., 2.], [0., 100., 2.]]])
    t = np.array([[[1., 400., 5.], [0., 600., 7.], [1., 500., 6.]]])
    values = measured(d, t, np.array([[True, True, False]]))
    assert values["accuracy"][0] == pytest.approx(1 / 3)
    assert values["tokens"][0] == pytest.approx(1300 / 3)
    assert values["utility"][0] == pytest.approx(1 / 3 - .05 * 1300 / 3000)
    assert values["rescued"][0] == values["harmed"][0] == 1
    assert values["missed_positive_gains"][0] == 1
    assert values["positive_gain_escalations"][0] == 1
    assert values["nonpositive_gain_escalations"][0] == 1


def test_review_does_not_accept_nonboolean_or_misaligned_actions():
    rows = np.zeros((2, 4, 3))
    with pytest.raises(ValueError, match="Invalid"):
        measured(rows, rows, np.ones((2, 4)))
    with pytest.raises(ValueError, match="Invalid"):
        measured(rows, rows, np.ones((2, 3), dtype=bool))
