import json

import numpy as np
import pytest

from reasoning_budget import probe, router_dev
from reasoning_budget.storage import verified


def synthetic_states(n=20):
    rng = np.random.default_rng(44)
    x = rng.normal(size=(n, 2, 391))
    x[:, :, -4] = rng.uniform(-1.8, -0.1, size=(n, 2))
    x[:, :, -3] = np.log1p(100)
    x[:, :, -2] = 1
    x[:, :, -1] = 0
    rows = np.zeros((n, 2, 3, 3), dtype=float)
    for i in range(n):
        for orientation in (0, 1):
            first = int((i + orientation) % 4 != 0)
            rows[i, orientation, 0] = [first, 100, 1]
            rows[i, orientation, 1] = [int(first or i % 5 == 0), 250, 2.5]
            rows[i, orientation, 2] = [int(i % 7 != 0), 800, 8]
    return x, rows


def test_shared_model_has_one_first_correct_probability_and_safe_rare_heads():
    x, rows = synthetic_states()
    model = router_dev.fit_shared(x.reshape(-1, 391), rows, router_dev.SHARED_SETTINGS[-1])
    prediction = router_dev.shared_predictions(model, x.reshape(-1, 391))
    assert prediction["first_correct"].shape == (40,)
    assert prediction["gain"].shape == prediction["cost"].shape == (40, 2)
    assert np.isfinite(prediction["gain"]).all()
    assert (prediction["cost"] >= 1).all()
    np.testing.assert_allclose(
        prediction["gain"],
        (1 - prediction["first_correct"][:, None]) * prediction["rescue"]
        - prediction["first_correct"][:, None] * prediction["harm"],
    )
    json.dumps(model, allow_nan=False)
    # A missing rescue class yields a finite prior rather than a failed fit.
    rows[:, :, :, 0] = 1
    constant = router_dev.fit_shared(x.reshape(-1, 391), rows, router_dev.SHARED_SETTINGS[0])
    assert constant["heads"][0]["rescue"]["coef"] is None
    assert np.isfinite(router_dev.shared_predictions(constant, x.reshape(-1, 391))["gain"]).all()


def test_question_folds_keep_both_orientations_together():
    roles = np.array(["train"] * 10 + ["tune"] * 10)
    x = np.repeat(np.arange(20), 2).reshape(20, 2, 1)
    seen = []
    for train, test in router_dev.question_folds(roles, 5, router_dev.SEED):
        assert not set(train) & set(test)
        assert len(test) == 4
        np.testing.assert_array_equal(router_dev._states(x, test)[::2, 0], test)
        np.testing.assert_array_equal(router_dev._states(x, test)[1::2, 0], test)
        seen.extend(test.tolist())
    assert sorted(seen) == list(range(20))


def test_standalone_thinking_charges_only_its_generation():
    direct = np.array([[[0, 100, 2], [0, 250, 5]], [[1, 40, 1], [1, 60, 1.5]]])
    thinking = np.array([[[1, 800, 16], [0, 900, 18]], [[0, 300, 6], [1, 500, 10]]])
    rows = probe.continuation_rows(
        {"direct": direct, "thinking": thinking, "answers": [["3", "3"], ["4", "4"]]}
    )
    original = rows.copy()
    baselines = router_dev.fixed_baselines(rows)
    np.testing.assert_allclose(baselines["always-thinking"], thinking.mean(axis=1))
    np.testing.assert_allclose(baselines["always-direct"], direct.mean(axis=1))
    np.testing.assert_allclose(baselines["DART-SC-2-adapted"], rows[:, :, 1].mean(axis=1))
    # Thinking after a draft is a different policy and still pays for both calls.
    np.testing.assert_allclose(rows[:, :, 2, 1:], direct[:, :, 1:] + thinking[:, :, 1:])
    np.testing.assert_array_equal(rows, original)


def test_outer_fold_actions_do_not_use_held_out_outcomes(monkeypatch):
    x, rows = synthetic_states()
    roles = np.array(["train"] * 10 + ["tune"] * 10)
    questions = [{"id": f"q{i}"} for i in range(len(roles))]
    monkeypatch.setattr(
        router_dev,
        "select_setting",
        lambda name, *_args, **_kwargs: (
            router_dev.SHARED_SETTINGS[0] if name == "shared" else {"C": 0.1, "alpha": 10},
            [],
        ),
    )
    result = router_dev.evaluate(questions, roles, x, rows, progress=lambda _: None)
    first_fold = np.array([q["fold"] == 0 for q in result["per_question"]])
    changed = rows.copy()
    changed[first_fold, :, :, 0] = 1 - changed[first_fold, :, :, 0]
    repeated = router_dev.evaluate(questions, roles, x, changed, progress=lambda _: None)
    for original, revised in zip(result["per_question"], repeated["per_question"], strict=True):
        if original["fold"] == 0:
            assert original["actions"] == revised["actions"]
    assert result["questions"] == 20
    assert all(np.isfinite(s["utility"]) for s in result["summaries"].values())
    primary = [
        p
        for p in result["curve"]
        if p["policy"] == "shared" and p["preference"] == router_dev.PREFERENCE
    ]
    assert len(primary) == 1
    assert primary[0]["accuracy"] == result["summaries"]["shared"]["accuracy"]
    assert (
        primary[0]["charged_tokens_per_question"]
        == result["summaries"]["shared"]["charged_tokens_per_question"]
    )
    assert len(result["curve_pairwise"]) == len(router_dev.probe.PREFERENCES)
    primary_pair = next(
        p for p in result["curve_pairwise"] if p["preference"] == router_dev.PREFERENCE
    )
    assert (
        primary_pair["shared_minus_confidence_utility"]
        == result["shared_minus"]["confidence-continuation"]["mean_utility_difference"]
    )
    assert "Held-out fold" in router_dev.report_markdown(result)
    for i, question in enumerate(result["per_question"]):
        expected = rows[i, :, 2].mean(axis=0)
        expected[1:] -= rows[i, :, 0, 1:].mean(axis=0)
        np.testing.assert_allclose(question["policies"]["always-thinking"], expected)
    thinking_curve = [p for p in result["curve"] if p["policy"] == "always-thinking"]
    expected_tokens = (rows[:, :, 2, 1] - rows[:, :, 0, 1]).mean()
    assert all(p["charged_tokens_per_question"] == expected_tokens for p in thinking_curve)


def test_report_creates_new_output_and_rejects_changed_identity(tmp_path, monkeypatch):
    questions = [{"id": "q0"}]
    monkeypatch.setattr(
        router_dev, "load_development", lambda *_args: (questions, None, None, None, {"v": 1})
    )
    calls = []

    def evaluate(*_args, **_kwargs):
        calls.append("evaluate")
        return {"marker": "corrected"}

    monkeypatch.setattr(router_dev, "evaluate", evaluate)
    monkeypatch.setattr(router_dev, "report_markdown", lambda report: report["marker"])

    def write_artifacts(output, _report):
        (output / "curve.csv").write_text("curve")
        (output / "accuracy-cost.png").write_bytes(b"plot")

    monkeypatch.setattr(router_dev, "write_curve_artifacts", write_artifacts)
    output = tmp_path / "new" / "shared-base-v2"
    report_path = router_dev.run(tmp_path / "source", output)
    saved = verified(report_path)
    assert saved["identity"]["analysis_version"] == router_dev.ANALYSIS_VERSION
    assert (output / "report.md").read_text() == "corrected"
    assert router_dev.run(tmp_path / "source", output) == report_path
    assert calls == ["evaluate"]
    monkeypatch.setattr(router_dev, "ANALYSIS_VERSION", "different-analysis")
    with pytest.raises(ValueError, match="choose a new output directory"):
        router_dev.run(tmp_path / "source", output)
    assert verified(report_path) == saved
