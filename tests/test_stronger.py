import json

import numpy as np
import pytest

from reasoning_budget.stronger import (
    fit_model,
    fit_transform,
    predict_modes,
    predict_targets,
    select_model,
    transform,
)


def examples(n=40):
    rng = np.random.default_rng(5)
    x = rng.normal(size=(n, 20))
    y = np.column_stack([x[:, 0] < 0, x[:, 0] >= 0, np.full(n, 100), np.full(n, 1000)])
    return x, y


def test_retrieval_shrinks_to_training_population_and_roundtrips():
    x = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]])
    y = np.array([[1, 0, 10, 100], [0, 1, 20, 200], [1, 1, 30, 300], [0, 0, 40, 400]])
    model = fit_model("retrieval", x, y, {"neighbors": 3, "shrinkage": 5})
    actual = predict_targets(json.loads(json.dumps(model)), [[1, 0]])
    # Self, orthogonal neighbor 1, orthogonal neighbor 3; opposite excluded.
    np.testing.assert_allclose(actual[0], (y[[0, 1, 3]].sum(0) + 5 * y.mean(0)) / 8)


def test_decision_learns_mode_advantage_and_can_route_without_responses():
    x, y = examples(60)
    model = fit_model("decision", x, y, {"dimensions": None, "inverse_regularization": 10})
    restored = json.loads(json.dumps(model))
    assert np.mean(predict_modes(restored, x, 0.05) == (x[:, 0] > 0)) > 0.95
    assert np.array_equal(predict_modes(model, x, 0.05), predict_modes(restored, x, 0.05))
    with pytest.raises(ValueError, match="not trained"):
        predict_modes(model, x, 0.1234)


def test_zero_regret_and_one_class_are_well_defined():
    x, _ = examples()
    y = np.tile([1, 1, 100, 1000], (len(x), 1))
    model = fit_model("decision", x, y, {"dimensions": 16, "inverse_regularization": 1})
    assert predict_modes(model, x, 0).tolist() == [0] * len(x)
    assert predict_modes(model, x, 0.05).tolist() == [0] * len(x)
    y[:, 0] = 0
    model = fit_model("decision", x, y, {"dimensions": 16, "inverse_regularization": 1})
    assert predict_modes(model, x, 0).tolist() == [1] * len(x)


def test_regret_weights_prioritize_large_mistakes_over_class_majority():
    x = np.zeros((4, 2))
    # Three tiny direct advantages versus one large thinking advantage.
    y = np.array([[0.51, 0.5, 100, 1000]] * 3 + [[0, 1, 100, 1000]])
    model = fit_model("decision", x, y, {"dimensions": None, "inverse_regularization": 1})
    assert predict_modes(model, [[0, 0]], 0).tolist() == [1]


def test_pca_and_standardization_use_training_only():
    x, _ = examples()
    z, state = fit_transform(x[:30], 16)
    np.testing.assert_allclose(z.mean(0), 0, atol=1e-12)
    np.testing.assert_allclose(state["pca_mean"], x[:30].mean(0))
    before = json.dumps(state, sort_keys=True)
    transform(x[30:] * 10000, state)
    assert json.dumps(state, sort_keys=True) == before
    assert np.asarray(state["pca_components"]).shape == (16, 20)


def test_tuning_selects_setting_without_fitting_to_tune_data():
    x, y = examples()
    model, candidates = select_model("ridge", x[:30], y[:30], x[30:], y[30:])
    best = max(candidates, key=lambda c: c["tuning_utility"])
    assert model["setting"] == best["setting"]
    np.testing.assert_allclose(model["transform"]["mean"], x[:30].mean(0))
    assert model == fit_model("ridge", x[:30], y[:30], best["setting"])


def test_invalid_inputs_fail_before_training():
    x, y = examples()
    y[0, 0] = 2
    with pytest.raises(ValueError, match="Invalid accuracy"):
        fit_model("ridge", x, y, {"alpha": 1.0})
