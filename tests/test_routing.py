import copy

import numpy as np
import pytest

from reasoning_budget.controller import (
    Controller,
    choose_modes,
    chunks,
    fit_controller,
    lexical_features,
)
from reasoning_budget.records import Question
from reasoning_budget.routing import (
    confidence_threshold,
    cross_validate,
    escalation,
    load_pilot,
    outcomes,
    summarize,
)


def synthetic(n=30):
    rng = np.random.default_rng(42)
    return {
        "accuracy": rng.integers(0, 2, (n, 2, 2)).astype(float),
        "tokens": rng.integers(10, 100, (n, 2, 2)).astype(float)
        + np.array([0, 500])[None, :, None],
        "seconds": rng.random((n, 2, 2)),
        "confidence": -rng.random((n, 2)),
        "agreement": rng.integers(0, 2, n).astype(bool),
    }


def test_features_question_only_and_long_input_endings():
    q = Question("q", "fixture", "train", "12.5 + 7 = ?")
    assert lexical_features(q) == [12, 2, 2]
    with pytest.raises(TypeError, match="gold-free"):
        lexical_features({**q.to_dict(), "gold": 19.5})
    ids = list(range(800))
    pieces = chunks(ids, 254)
    assert [token for part in pieces for token in part] == ids
    assert max(map(len, pieces)) == 254


def test_portable_controller_clips_and_selects_without_responses():
    x = np.arange(60).reshape(20, 3)
    y = np.column_stack([np.ones(20), np.zeros(20), np.ones(20) * 20, np.ones(20) * 50])
    model = fit_controller(x, y)
    restored = Controller.from_dict(model.to_dict())
    assert np.array_equal(restored.predict(x), model.predict(x))
    assert np.array_equal(model.mean, x.mean(0))
    assert choose_modes(model.predict(x), 0.1).tolist() == [0] * 20
    assert choose_modes([[-4, 8, -20, 1000]], 0).tolist() == [1]
    with pytest.raises(ValueError):
        choose_modes([[0, 1, 10, 20]], -1)


def test_saved_controller_routes_new_questions_without_gold(monkeypatch):
    x = np.arange(60).reshape(20, 3)
    y = np.tile([1, 0, 20, 100], (20, 1))
    model = Controller.from_dict(fit_controller(x, y).to_dict())
    new_question = Question("unseen", "fixture", "validation", "What is 19 + 4?")

    def encode(questions, cache_dir):
        assert questions == [new_question]
        return np.array([[8, 9, 10]]), {}

    monkeypatch.setattr("reasoning_budget.controller.feature_matrix", encode)
    assert model.route([new_question], 0.1) == ["direct"]


def test_all_probe_costs_and_agreement_do_not_invent_extra_trials():
    data = synthetic(3)
    never = np.zeros((3, 2), dtype=bool)
    always = ~never
    np.testing.assert_allclose(escalation(data, never), outcomes(data, np.zeros(3, dtype=int)))
    escalated = escalation(data, always)
    np.testing.assert_allclose(escalated[:, 1], data["tokens"].sum(1).mean(1))
    dart_accept = escalation(data, never, two_drafts=True)
    np.testing.assert_allclose(dart_accept[:, 1], data["tokens"][:, 0].sum(1))
    dart_escalate = escalation(data, always, two_drafts=True)
    np.testing.assert_allclose(
        dart_escalate[:, 1], data["tokens"][:, 0].sum(1) + data["tokens"][:, 1].mean(1)
    )
    np.testing.assert_allclose(dart_escalate[:, 0], data["accuracy"][:, 1].mean(1))
    assert dart_accept.shape == (3, 3)


def test_confidence_tuning_cannot_see_evaluation_labels():
    data = synthetic()
    ids = np.arange(20)
    expected = confidence_threshold(data, ids, 0.1)
    changed = copy.deepcopy(data)
    changed["accuracy"][20:] = 1 - changed["accuracy"][20:]
    changed["tokens"][20:] *= 1000
    assert confidence_threshold(changed, ids, 0.1) == expected


def test_nested_cv_evaluation_labels_do_not_change_own_predictions():
    data = synthetic()
    x = np.random.default_rng(44).normal(size=(30, 6))
    ids = [str(i) for i in range(30)]
    result = cross_validate(x, data, ids)
    first = result["folds"][0]
    held_out = np.array([int(i) for i in first["evaluation_ids"]])
    train = np.array([int(i) for i in first["train_ids"]])
    np.testing.assert_allclose(first["controller"]["mean"], x[train].mean(0))
    assert set(first["train_ids"]).isdisjoint(first["evaluation_ids"])
    assert sorted(i for f in result["folds"] for i in f["evaluation_ids"]) == sorted(ids)
    changed = copy.deepcopy(data)
    changed["accuracy"][held_out] = 1 - changed["accuracy"][held_out]
    changed["tokens"][held_out] *= 3
    again = cross_validate(x, changed, ids)
    np.testing.assert_array_equal(
        np.array(result["predictions"])[held_out], np.array(again["predictions"])[held_out]
    )
    assert first["confidence_thresholds"] == again["folds"][0]["confidence_thresholds"]
    assert result["predictions"] == cross_validate(x, data, ids)["predictions"]


def test_paired_summary_random_has_zero_excess():
    data = synthetic()
    direct = outcomes(data, np.zeros(30, dtype=int))
    thinking = outcomes(data, np.ones(30, dtype=int))
    rows = summarize(
        [
            ("direct", None, direct),
            ("thinking", None, thinking),
            ("random", 0.5, (direct + thinking) / 2),
        ]
    )
    assert abs(rows[2]["accuracy_advantage_over_cost_matched_random"]) < 1e-12
    np.testing.assert_allclose(rows[2]["advantage_ci95"], [0, 0], atol=1e-12)


def test_replay_rejects_official_test_before_features(monkeypatch):
    monkeypatch.setattr(
        "reasoning_budget.routing.load_run",
        lambda _: ({"identity": {"config": {"split": "test", "samples": 2}}}, []),
    )
    with pytest.raises(ValueError, match="test is sealed"):
        load_pilot("ignored")
