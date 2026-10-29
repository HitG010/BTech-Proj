import numpy as np
import pytest

from scripts import audit_confidence_gain_shape as audit

SMALL = {**audit.SPEC, "bootstrap_draws": 300}


def threshold_panel(low_confidence_rescued, seed=0, q=40, r=4):
    """Thinking always correct; the direct draft fails on 30% of states."""
    rng = np.random.default_rng(seed)
    confidence = rng.normal(-0.3, 0.1, size=(q, r))
    cut = np.quantile(confidence, 0.3 if low_confidence_rescued else 0.7)
    failed = confidence < cut if low_confidence_rescued else confidence > cut
    direct = np.where(failed, 0.0, 1.0)
    return direct, np.ones((q, r)), np.full((q, r), 500.0), confidence


def test_gain_matches_manuscript_definition():
    gain = audit.gain_matrix(np.array([[0, 1]]), np.array([[1, 1]]), np.array([[2000, 400]]))
    assert np.allclose(gain, [[1 - .1, -.02]])


def test_lower_confidence_rescues_read_as_consistent():
    result = audit.gain_shape(*threshold_panel(True), spec=SMALL)
    pooled = result["trend"]["pooled"]
    assert pooled["spearman"] < 0 and pooled["ci90"][1] < 0 and pooled["share_negative"] == 1
    assert result["bins"][0]["mean_gain"] == max(b["mean_gain"] for b in result["bins"])
    assert result["monotonicity_violations"] == 0
    assert result["reading"] == "consistent"


def test_higher_confidence_rescues_read_as_inconsistent():
    result = audit.gain_shape(*threshold_panel(False), spec=SMALL)
    assert result["trend"]["pooled"]["ci90"][0] > 0
    assert result["reading"] == "inconsistent"


def test_constant_gain_has_no_rank_trend_and_is_inconclusive():
    ones = np.ones((10, 3))
    result = audit.gain_shape(ones, ones, np.full((10, 3), 800.0),
                              np.arange(30.0).reshape(10, 3), spec=SMALL)
    assert result["trend"]["pooled"]["spearman"] is None
    assert result["trend"]["pooled"]["ci90"] is None
    assert result["reading"] == "inconclusive"


def test_bins_are_equal_count_with_bin_one_lowest():
    confidence = np.arange(10.0).reshape(2, 5)
    labels = audit.bin_labels(confidence, 5)
    assert labels.tolist() == [[0, 0, 1, 1, 2], [2, 3, 3, 4, 4]]


def test_bin_rows_count_outcomes_and_questions():
    direct, thinking, tokens, confidence = threshold_panel(True)
    result = audit.gain_shape(direct, thinking, tokens, confidence, spec=SMALL)
    bins = result["bins"]
    assert sum(b["states"] for b in bins) == direct.size
    assert sum(b["rescues"] for b in bins) == int((direct == 0).sum())
    assert all(b["harms"] == 0 and b["both_wrong"] == 0 for b in bins)
    assert bins[0]["direct_accuracy"] == 0 and bins[-1]["direct_accuracy"] == 1
    assert all(b["mean_gain_ci90"][0] <= b["mean_gain"] <= b["mean_gain_ci90"][1] for b in bins)


def test_escalation_curve_matches_hand_calculation():
    confidence = np.array([[0.1, 0.2], [0.3, 0.4]])
    gain = np.array([[1.0, 0.0], [0.0, -1.0]])
    curve = audit.escalation_curve(confidence, gain, [0.0, 0.5, 1.0])
    assert [row["confidence_gain_per_state"] for row in curve["curve"]] == [0, .25, 0]
    assert [row["oracle_gain_per_state"] for row in curve["curve"]] == [0, .25, 0]
    assert [row["random_expected_gain_per_state"] for row in curve["curve"]] == [0, 0, 0]
    assert curve["best_in_sample_confidence"] == {"escalated": 1, "fraction": .25,
                                                  "gain_per_state": .25}
    assert curve["oracle_gain_per_state"] == .25 and curve["best_share_of_oracle"] == 1


def test_escalation_curve_orders_by_ascending_confidence():
    confidence = np.array([[0.4, 0.1], [0.3, 0.2]])
    gain = np.array([[2.0, -1.0], [0.0, 1.0]])
    curve = audit.escalation_curve(confidence, gain, [0.25, 0.5, 0.75, 1.0])
    expected = np.cumsum([-1.0, 1.0, 0.0, 2.0]) / 4
    assert np.allclose([row["confidence_gain_per_state"] for row in curve["curve"]], expected)
    assert curve["curve"][-1]["random_expected_gain_per_state"] == pytest.approx(gain.mean())


def test_between_and_within_question_trends_are_separated():
    q, r = 30, 4
    question_mean = np.linspace(-0.6, -0.1, q)[:, None]
    offsets = np.array([-0.02, -0.01, 0.01, 0.02])
    confidence = question_mean + offsets
    direct = np.ones((q, r))
    direct[: q // 2, 2:] = 0
    result = audit.gain_shape(direct, np.ones((q, r)), np.zeros((q, r)), confidence, spec=SMALL)
    assert result["trend"]["between_questions"]["spearman"] < 0
    assert result["trend"]["within_questions"]["spearman"] > 0


def test_spearman_matches_rank_pearson_and_rejects_degenerate_inputs():
    rng = np.random.default_rng(3)
    a, b = rng.normal(size=50), rng.normal(size=50)
    ranks = [np.argsort(np.argsort(x)) for x in (a, b)]
    assert audit.safe_spearman(a, b) == pytest.approx(np.corrcoef(*ranks)[0, 1])
    assert audit.safe_spearman(np.ones(5), b[:5]) is None
    assert audit.safe_spearman(a[:2], b[:2]) is None


def test_reading_rule_requires_both_conditions_for_consistent():
    rows = [{"states": 5, "mean_gain": g} for g in (.1, .3, .0)]
    assert audit.reading([-.4, -.1], rows) == "inconclusive"
    rows[1]["mean_gain"] = .05
    assert audit.reading([-.4, -.1], rows) == "consistent"
    assert audit.reading([.1, .4], rows) == "inconsistent"
    assert audit.reading([-.1, .2], rows) == "inconclusive"
    assert audit.reading(None, rows) == "inconclusive"


@pytest.mark.parametrize("bad", [
    lambda d, t, k, c: (d + 2, t, k, c),
    lambda d, t, k, c: (d, t, -k, c),
    lambda d, t, k, c: (d, t, k, np.where(c > -0.3, np.nan, c)),
    lambda d, t, k, c: (d, t[:, :2], k, c),
    lambda d, t, k, c: (d.ravel(), t.ravel(), k.ravel(), c.ravel()),
])
def test_invalid_panels_are_rejected(bad):
    with pytest.raises(ValueError):
        audit.gain_shape(*bad(*threshold_panel(True)), spec=SMALL)


def test_results_are_deterministic_for_the_frozen_seed():
    panel = threshold_panel(True, seed=5)
    assert audit.gain_shape(*panel, spec=SMALL) == audit.gain_shape(*panel, spec=SMALL)


def test_spec_and_sources_are_frozen_as_declared():
    assert audit.SPEC["escalation_fractions"] == [round(0.1 * i, 1) for i in range(11)]
    assert audit.SPEC["bootstrap_draws"] == 2000 and audit.SPEC["interval"] == [.05, .95]
    assert set(audit.SPEC["panels"]) == set(audit.PANELS)
    assert all((audit.ROOT / name).is_file() for name in audit.SOURCE_FILES)
    assert audit.OUTPUT.parent == audit.BASE


def test_markdown_renders_all_panels_with_missing_values():
    stats = audit.gain_shape(*threshold_panel(True), spec=SMALL)
    stats["bins"][1]["mean_gain_ci90"] = None
    report = {"statistics": {name: stats for name in audit.PANELS}}
    text = audit.markdown(report)
    assert all(f"## {name}" in text for name in audit.PANELS) and "n/a" in text
