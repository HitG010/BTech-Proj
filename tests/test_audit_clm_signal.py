import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from scripts import audit_clm_signal as audit


def test_auc_matches_independent_pair_enumeration_with_ties():
    labels = np.array([0, 1, 1, 0, 1, 0])
    scores = np.array([0., 1., 0., 0., 2., 1.])
    positive, negative = scores[labels == 1], scores[labels == 0]
    paired = np.mean([(p > n) + .5 * (p == n) for p in positive for n in negative])
    assert audit.auc(labels, scores) == paired == roc_auc_score(labels, scores)
    assert audit.auc(np.ones(3), np.arange(3)) is None
    assert audit.auc(np.zeros(3), np.arange(3)) is None


def test_auc_rejects_misalignment_and_nonfinite_scores():
    for labels, scores in [([0, 1], [0]), ([0, 2], [0, 1]), ([0, 1], [0, np.nan])]:
        with pytest.raises(ValueError):
            audit.auc(labels, scores)


def test_question_bootstrap_keeps_all_draws_and_reports_undefined_groups():
    labels = np.array([[1, 0], [0, 0]])
    scores = np.array([[3., 2.], [0., 1.]])
    draws = np.array([[0, 1], [1, 1], [0, 0]])
    result = audit.ranked_event(labels, scores, draws)
    assert result["pooled_auc"] == 1
    assert result["valid_bootstrap_draws"] == 2
    assert result["undefined_bootstrap_draws"] == 1
    assert result["within_question_informative_groups"] == 1
    assert result["within_question_macro_auc"] == 1
    assert result["ci90"] == [1., 1.]
    with pytest.raises(ValueError, match="whole questions"):
        audit.ranked_event(labels, scores, np.array([[0, 1, 1]]))


def test_signal_rejects_incomplete_panel_and_future_cost_inputs_are_only_labels(monkeypatch):
    monkeypatch.setitem(audit.SPEC, "bootstrap_draws", 12)
    d = np.zeros((3, 8, 3))
    t = d.copy()
    d[..., 1] = 100
    t[..., 1] = 1000
    t[0, :, 0] = 1
    scores = np.repeat(np.array([2., 1., -1.])[:, None], 8, axis=1)
    result = audit.signal_statistics(d, t, -scores, scores)
    assert result["margin"]["positive_gain_captured"] == 8
    assert result["margin"]["nonpositive_escalations"] == 8
    assert result["margin"]["positive_gain_precision"] == .5
    assert result["margin"]["positive_gain_recall"] == 1
    assert result["no_policy_changes"]
    assert result["ranking"]["released_clm_margin"]["positive_paired_gain"]["pooled_auc"] == 1
    with pytest.raises(ValueError, match="eight-draw"):
        audit.signal_statistics(d[:, :7], t[:, :7], -scores[:, :7], scores[:, :7])


def test_fixed_policy_break_even_does_not_change_lambda_or_actions():
    assert audit.break_even(.02, 1000.) == .02
    assert audit.break_even(.02, 0.) is None
    assert audit.SPEC["lambda"] == .05
