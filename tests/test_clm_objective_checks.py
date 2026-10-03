"""Synthetic mathematical checks for CLM router objectives; no real data used."""

import numpy as np


def softmax(values):
    values = np.asarray(values, dtype=float)
    shifted = values - values.max(axis=-1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / exp_values.sum(axis=-1, keepdims=True)


def binary_entropy_cross_entropy(probability, positive_weight, negative_weight):
    return -positive_weight * np.log(probability) - negative_weight * np.log1p(-probability)


def test_two_action_softmax_is_sigmoid_of_logit_difference():
    scores = np.array([[-2.0, 0.5], [0.3, -1.4], [4.0, 4.0]])
    probabilities = softmax(scores)
    difference = scores[:, 1] - scores[:, 0]
    sigmoid = 1 / (1 + np.exp(-difference))
    np.testing.assert_allclose(probabilities[:, 1], sigmoid, rtol=1e-14, atol=1e-14)


def test_naive_diagonal_infonce_has_duplicate_action_ambiguity():
    # m repeated copies of the same action create m indistinguishable columns.
    # With no other action candidates, each diagonal target gets probability 1/m.
    m = 4
    logits = np.zeros((m, m))
    forward = -np.log(softmax(logits)[np.arange(m), np.arange(m)]).mean()
    assert forward == np.log(m)

    # Transposing the same repeated-pair matrix gives m indistinguishable state
    # candidates for the repeated action, so action-to-state matching is equally
    # ambiguous under a naive diagonal objective.
    reverse_logits = logits.T
    reverse = -np.log(softmax(reverse_logits)[np.arange(m), np.arange(m)]).mean()
    assert reverse == np.log(m)


def test_regret_weighted_bce_optimum_and_event_frequency_can_disagree():
    gains = np.array([0.1, 0.1, -0.8])
    positive_mass = np.maximum(gains, 0).sum()
    total_regret_mass = np.abs(gains).sum()
    optimum_probability = positive_mass / total_regret_mass
    assert optimum_probability == 0.2

    # This is the unique minimum of weighted Bernoulli CE: positive mass is
    # E[max(g, 0)] and negative mass is E[max(-g, 0)].
    grid = np.linspace(0.01, 0.99, 99)
    losses = [
        binary_entropy_cross_entropy(p, positive_mass, total_regret_mass - positive_mass)
        for p in grid
    ]
    assert grid[int(np.argmin(losses))] == 0.2

    assert np.mean(gains > 0) > 0.5  # Event frequency favors thinking.
    assert gains.mean() < 0  # Expected gain favors accepting the draft.
    assert (optimum_probability > 0.5) == (gains.mean() > 0)


def test_direct_solver_cost_cancels_from_incremental_choice_but_encoder_latency_does_not():
    direct_solver_cost = 120.0
    thinking_solver_cost = 480.0
    router_encoder_cost = 6.0

    direct_total = direct_solver_cost
    thinking_total = direct_solver_cost + thinking_solver_cost
    incremental_decision_cost = thinking_total - direct_total
    assert incremental_decision_cost == thinking_solver_cost
    more_expensive_direct = direct_solver_cost + 75.0
    assert (more_expensive_direct + thinking_solver_cost) - more_expensive_direct == incremental_decision_cost

    # A CLM encoder runs before either action is chosen. It therefore adds to
    # the deployed router path even though it does not change the action delta.
    direct_with_router = direct_total + router_encoder_cost
    thinking_with_router = thinking_total + router_encoder_cost
    assert thinking_with_router - direct_with_router == incremental_decision_cost
    assert direct_with_router - direct_total == router_encoder_cost
