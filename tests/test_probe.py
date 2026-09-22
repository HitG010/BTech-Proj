import copy

import numpy as np
import pytest

from reasoning_budget import probe


def replay_data():
    return {
        "direct": np.array(
            [
                [[1, 10, 1], [1, 20, 2], [0, 30, 3]],
                [[0, 10, 1], [1, 20, 2], [1, 30, 3]],
                [[0, 10, 1], [0, 20, 2], [0, 30, 3]],
                [[0, 10, 1], [0, 20, 2], [0, 30, 3]],
            ],
            float,
        ),
        "thinking": np.array(
            [
                [[0, 100, 10], [0, 200, 20]],
                [[1, 100, 10], [0, 200, 20]],
                [[1, 100, 10], [1, 200, 20]],
                [[1, 100, 10], [1, 200, 20]],
            ],
            float,
        ),
        "answers": [["4", "4", "7"], ["2", "4", "4"], ["1", "2", "3"], [None, None, "3"]],
    }


def test_consumed_probe_costs_and_regressions():
    data = replay_data()
    rows = probe.continuation_rows(data)
    assert rows.shape == (4, 2, 3, 3)
    # Agreement skips thinking; an immediate thinking action can harm a correct answer.
    np.testing.assert_array_equal(rows[0, 0], [[1, 10, 1], [1, 30, 3], [0, 110, 11]])
    # Second orientation starts correct but the disagree-then-think continuation fails.
    np.testing.assert_array_equal(rows[1, 1, 1], [0, 230, 23])
    # Failed extraction cannot establish agreement.
    np.testing.assert_array_equal(rows[3, 0, 1], [1, 130, 13])
    selected = probe.selected_rows(rows, np.ones(8, int))
    np.testing.assert_array_equal(selected[1], [0.5, 180, 18])


def test_dart_third_draft_and_fallback_costs():
    data = replay_data()
    result = probe.dart_sc3(data)
    np.testing.assert_array_equal(result, [[1, 30, 3], [1, 60, 6], [1, 210, 21], [1, 210, 21]])
    # Changing future scoring labels does not alter the consumed draft branch/cost.
    data["direct"][:, :, 0] = 1 - data["direct"][:, :, 0]
    np.testing.assert_array_equal(probe.dart_sc3(data)[:, 1:], result[:, 1:])


def test_first_state_never_reads_gold_or_future_responses():
    result = {
        "mean_generated_logprob": -0.3,
        "final_answer": r"\boxed{4}",
        "answer_tokens": 12,
        "answer_truncated": False,
    }
    original = probe.first_features(result)
    changed = result | {"correct": False, "gold": "9", "thinking": "wrong", "second_draft": "9"}
    assert probe.first_features(changed) == original
    states = probe.state_features(np.array([[1, 2]]), [[result, result, {"unreadable": True}]])
    assert states.shape == (2, 6)
    with pytest.raises(ValueError, match="finite"):
        probe.first_features(result | {"mean_generated_logprob": None})


def test_joint_models_handle_constant_binary_and_multiclass_and_serialize():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(8, 7))
    rows = probe.continuation_rows(replay_data())
    for kind in ("joint", "gain-ridge"):
        model = probe.fit(x, rows, probe.SETTINGS[0], kind, response_only=True)
        gain, cost = probe.predictions(model, x)
        assert gain.shape == cost.shape == (8, 2)
        assert np.isfinite(gain).all() and (cost >= 1).all()
        assert (abs(gain) <= 1).all()
        assert set(probe.actions(model, x, 0.05, binary=True)) <= {0, 1}
        np.testing.assert_array_equal(
            probe.actions(model, x, 0.05), probe.actions(copy.deepcopy(model), x, 0.05)
        )
        if kind == "joint":
            no_harm, _ = probe.predictions(model, x, ignore_harm=True)
            assert (no_harm >= gain).all()
    # Constant classes need no logistic estimator.
    rows[:, :, :, 0] = 1
    constant = probe.fit(x, rows, probe.SETTINGS[0], response_only=True)
    np.testing.assert_array_equal(probe.actions(constant, x, 0.05), np.zeros(8))
    assert constant["heads"][0]["classes"] == [3]


def test_confidence_thresholds_include_always_accept_and_charge_first_draft():
    rows = probe.continuation_rows(replay_data())
    setting = probe.select_confidence(np.full(8, -0.2), rows, 100)
    assert not probe.confidence_actions(np.full(8, -0.2), setting).any()
    with pytest.raises(ValueError, match="valid action"):
        probe.selected_rows(rows, np.full(8, 3))
