"""Synthetic-only checks for the frozen repeat-panel diagnostic contract."""

import json

import numpy as np
import pytest

from reasoning_budget.repeat_stats import ANALYSIS, _ci, _rows, analyze


def panel(n=10):
    ids = [f"synthetic-{i}" for i in range(n)]
    q = np.column_stack([np.arange(n) % 2, np.arange(n) / n]).astype(float)
    d = np.zeros((n, 8, 3), dtype=float)
    t = np.zeros_like(d)
    z = np.zeros((n, 8, 4), dtype=float)
    for i in range(n):
        for draw in range(8):
            d[i, draw] = [int((i + draw) % 3 != 0), 10 + draw, 0.2]
            t[i, draw] = [int((i + draw) % 2 == 0), 100 + draw, 1.0]
            z[i, draw] = [float((i * 3 + draw) % 7) / 7, i % 2, draw / 8, 1]
    return ids, q, d, t, z, {qid: i % 5 for i, qid in enumerate(ids)}


def test_cost_always_charges_direct_and_charges_thinking_on_escalation():
    d = np.array([[[1, 10, 2], [0, 20, 3]]], dtype=float)
    t = np.array([[[0, 100, 5], [1, 200, 7]]], dtype=float)
    rows = _rows(d, t, np.array([0]), [0, 1], np.array([[False, True]]), 0.05)
    assert rows["accuracy"].tolist() == [1]
    assert rows["tokens"].tolist() == [115]
    assert rows["seconds"].tolist() == [6]
    assert rows["utility"].tolist() == pytest.approx([1 - 0.05 * 115 / 1000])


def test_grouped_bootstrap_draws_one_question_at_a_time():
    values = np.array([-1, 3, 7], dtype=float)
    observed = _ci(values, ANALYSIS)
    rng = np.random.default_rng(ANALYSIS["bootstrap_seed"])
    samples = rng.integers(0, 3, size=(ANALYSIS["bootstrap_draws"], 3))
    expected = np.quantile(values[samples].mean(axis=1), [0.05, 0.95])
    assert observed == pytest.approx(expected)


def test_oof_decisions_ignore_that_questions_labels_and_ties_are_deterministic():
    data = panel()
    result = analyze(*data)
    ids, q, d, t, z, folds = data
    d_changed, t_changed = d.copy(), t.copy()
    d_changed[0, :, 0] = 1 - d_changed[0, :, 0]
    t_changed[0, :, 0] = 1 - t_changed[0, :, 0]
    changed = analyze(ids, q, d_changed, t_changed, z, folds)
    for name in result["conditions"]:
        before = result["conditions"][name]["per_question"][ids[0]]["policies"]
        after = changed["conditions"][name]["per_question"][ids[0]]["policies"]
        assert {key: value["decisions"] for key, value in before.items()} == {
            key: value["decisions"] for key, value in after.items()
        }

    # Every candidate has the same utility when both arms always succeed at zero cost.
    d_tie, t_tie = d.copy(), t.copy()
    d_tie[:, :, 0] = t_tie[:, :, 0] = 1
    d_tie[:, :, 1:] = t_tie[:, :, 1:] = 0
    tied = analyze(ids, q, d_tie, t_tie, z, folds)
    for condition in tied["conditions"].values():
        assert all(fold["selected_baseline"] == "accept" for fold in condition["folds"])
        assert all(set(fold["alphas"].values()) == {100.0} for fold in condition["folds"])

    assert json.dumps(result, allow_nan=False)
    assert result["question_count"] == 10
    rescue = (d[:, :, 0] == 0) & (t[:, :, 0] == 1)
    harm = (d[:, :, 0] == 1) & (t[:, :, 0] == 0)
    assert result["paired_outcome_states"] == {
        "rescue_draws": int(rescue.sum()),
        "rescue_questions": int(rescue.any(axis=1).sum()),
        "harm_draws": int(harm.sum()),
        "harm_questions": int(harm.any(axis=1).sum()),
    }
    for condition in result["conditions"].values():
        for policy, metrics in condition["summary"].items():
            assert set(metrics) == {
                "mean_accuracy", "mean_tokens", "mean_seconds", "mean_utility",
                "mean_escalation_rate", "ci90",
            }
            per_q = condition["per_question"]
            assert metrics["mean_tokens"] == pytest.approx(np.mean([
                per_q[qid]["policies"][policy]["tokens"] for qid in ids
            ]))
    assert set(result["reproducibility"]) == {"1", "2", "4", "8_descriptive"}
    assert len(result["reproducibility"]["8_descriptive"]["per_question"]) == 10
    assert set(result["conditions"]) == {
        "k1_A_to_B", "k1_B_to_A", "k2_A_to_B", "k2_B_to_A",
        "k4_A_to_B", "k4_B_to_A", "k8_full",
    }


def test_opposite_half_outer_train_outcomes_cannot_tune_a_to_b_fold():
    ids, q, d, t, z, folds = panel()
    original = analyze(ids, q, d, t, z, folds)
    changed_d, changed_t = d.copy(), t.copy()
    outer_train = np.array([i for i, qid in enumerate(ids) if folds[qid] != 0])
    opposite = [4, 5, 6, 7]
    changed_d[np.ix_(outer_train, opposite, [0])] = 1 - changed_d[
        np.ix_(outer_train, opposite, [0])
    ]
    changed_t[np.ix_(outer_train, opposite, [0])] = 1 - changed_t[
        np.ix_(outer_train, opposite, [0])
    ]
    changed_d[np.ix_(outer_train, opposite, [1])] += 1000
    changed_t[np.ix_(outer_train, opposite, [1])] += 1000
    altered = analyze(ids, q, changed_d, changed_t, z, folds)
    for k in (1, 2, 4):
        name = f"k{k}_A_to_B"
        before = original["conditions"][name]
        after = altered["conditions"][name]
        assert before["folds"][0] == after["folds"][0]
        for qid in ids:
            if folds[qid] == 0:
                assert before["per_question"][qid] == after["per_question"][qid]
        acquisition = before["folds"][0]["training_acquisition"]
        expected_d = d[np.ix_(outer_train, list(range(k)), [1])].sum()
        expected_t = t[np.ix_(outer_train, list(range(k)), [1])].sum()
        assert acquisition["paired_draws"] == len(outer_train) * k
        assert acquisition["responses"] == 2 * len(outer_train) * k
        assert acquisition["direct_tokens"] == expected_d
        assert acquisition["thinking_tokens"] == expected_t
        assert acquisition["total_tokens"] == expected_d + expected_t


def test_tie_aware_standalone_postdirect_label_signs():
    ids, q, d, t, z, folds = panel()
    d[:, :, 0] = 1
    t[:, :, 0] = 1
    d[:, :, 1:] = 0
    t[:, :, 1:] = 0
    all_diagnostics = analyze(ids, q, d, t, z, folds)["label_diagnostics"]
    diagnostics = all_diagnostics["k1_A"]
    assert diagnostics["standalone_sign_counts"] == {"negative": 0, "tie": 10, "positive": 0}
    assert diagnostics["postdirect_sign_counts"] == {"negative": 0, "tie": 10, "positive": 0}
    assert diagnostics["sign_agreement_with_ties"] == 1
    cross = all_diagnostics["k1_postdirect_A_B"]
    assert cross["sign_agreement_with_ties"] == 1
    assert cross["both_tie"] == 10

    t[0, 4, 0] = 0
    cross = analyze(ids, q, d, t, z, folds)["label_diagnostics"]["k1_postdirect_A_B"]
    assert cross["one_tie"] == 1
    assert cross["both_tie"] == 9
    t[0, 4, 0] = 1

    d[:, :, 1] = 100
    t[:, :, 1] = 200
    all_diagnostics = analyze(ids, q, d, t, z, folds)["label_diagnostics"]
    assert all_diagnostics["k1_A"]["mean_standalone_gain"] == pytest.approx(-0.005)
    assert all_diagnostics["k1_A"]["mean_postdirect_gain"] == pytest.approx(-0.01)


def test_shapes_and_nonfinite_values_are_rejected():
    data = panel()
    ids, q, d, t, z, folds = data
    with pytest.raises(ValueError, match="eight paired draws"):
        analyze(ids, q, d[:, :7], t, z, folds)
    broken = z.copy()
    broken[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="Non-finite"):
        analyze(ids, q, d, t, broken, folds)
