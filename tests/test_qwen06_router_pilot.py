"""Synthetic cached-only tests; no real panel fit, gold, model or generation."""

from copy import deepcopy

import numpy as np
import pytest

from reasoning_budget.storage import digest
from scripts import qwen06_router_pilot as pilot


def synthetic_rows():
    rows = []
    for draw in (0, 1):
        for i in range(64):
            rows.append({"question_id": f"q{i:02d}", "draw": draw, "fold": i % 5,
                "features": [-2. + i / 40 + draw / 10, np.log1p(70 + i), float(i % 17 == 0)],
                "direct_correct": int(i % 3 != 0), "thinking_correct": int(i % 4 != 0),
                "direct_tokens": 200 + i, "thinking_tokens": 1000 + i,
                "frozen_confidence_action": i % 3 == 0, "parser_status": "ok",
                "frozen_confidence_threshold": -1.5})
    return rows


def test_direct_features_ignore_labels_and_thinking():
    record = {"job": {"mode": "direct"}, "status": "completed",
        "result": {"mean_generated_logprob": -1.25, "answer_tokens": 199,
            "final_answer": "\\boxed{42}", "answer_truncated": True,
            "termination": "answer_limit"}}
    score = {"mode": "direct", "parser_status": "incomplete", "correct": False}
    features = pilot.direct_features(record, score)
    score["correct"] = True
    record["thinking_correct"] = 1
    assert pilot.direct_features(record, score) == features
    assert features == [-1.25, np.log1p(199), 1.]
    with pytest.raises(ValueError, match="Invalid direct feature"):
        pilot.direct_features(record, dict(score, parser_status="ok"))
    with pytest.raises(ValueError, match="Direct-only"):
        pilot.direct_features({"job": {"mode": "thinking"}, "result": record["result"]}, score)


def test_training_excludes_heldout_question_and_opposite_draw_labels():
    rows = synthetic_rows()
    first, detail = pilot.fold_fit(rows, 0, 1, 2)
    assert len(first) == 13 and len(detail["train_question_ids"]) == 51
    assert set(detail["train_question_ids"]).isdisjoint(detail["test_question_ids"])
    assert detail["test_question_ids_in_prediction_order"] == [a["question_id"] for a in first]
    assert all(a["test_draw"] == 1 and a["train_draw"] == 0 for a in first)
    changed = deepcopy(rows)
    for row in changed:
        if row["draw"] == 1 or row["fold"] == 2:
            row["direct_correct"] = 1 - row["direct_correct"]
            row["thinking_correct"] = 1 - row["thinking_correct"]
    second, other = pilot.fold_fit(changed, 0, 1, 2)
    for family in ("matched_confidence_ridge", "full_three_feature_ridge"):
        assert detail["models"][family]["predictions"] == other["models"][family]["predictions"]
        assert [a["actions"][family] for a in first] == [a["actions"][family] for a in second]


def test_scaler_uses_training_rows_only():
    rows = synthetic_rows()
    _, detail = pilot.fold_fit(rows, 0, 1, 0)
    expected = np.mean([r["features"][0] for r in rows if r["draw"] == 0 and r["fold"] != 0])
    assert detail["models"]["matched_confidence_ridge"]["scaler_mean"][0] == pytest.approx(expected)
    changed = deepcopy(rows)
    for row in changed:
        if row["draw"] == 1 or row["fold"] == 0:
            row["features"][0] += 1000
    _, other = pilot.fold_fit(changed, 0, 1, 0)
    assert other["models"]["matched_confidence_ridge"]["scaler_mean"][0] == pytest.approx(expected)


def test_fixed_twenty_fit_limit_and_grouped_coverage():
    rows = synthetic_rows()
    ids = [f"q{i:02d}" for i in range(64)]
    report = pilot.analyze(rows, ids)
    assert report["fit_count"] == 20 and len(report["fits"]) == 10
    assert len(report["actions"]) == 128
    assert len({(a["question_id"], a["test_draw"]) for a in report["actions"]}) == 128
    assert report["spec"] == pilot.SPEC


def test_shared_question_bootstrap_and_gate_arithmetic():
    actions = []
    for draw in (0, 1):
        for i in range(64):
            u = {name: 0. for name in pilot.POLICIES}
            u["full_three_feature_ridge"] = .02
            actions.append({"question_id": f"q{i:02d}", "test_draw": draw,
                "utility": u, "correct": {name: 1 for name in pilot.POLICIES},
                "tokens": {name: 100 for name in pilot.POLICIES},
                "actions": {name: False for name in pilot.POLICIES},
                "rescue": 0, "harm": 0})
    summary = pilot.summarize(actions, [f"q{i:02d}" for i in range(64)])
    delta = summary["deltas_vs_confidence"]["full_three_feature_ridge"]
    assert delta["mean"] == pytest.approx(.02)
    assert delta["ci90"] == pytest.approx([.02, .02])
    assert summary["further_study_gate"]["all_pass"]
    assert summary["bootstrap"]["grouping"].startswith("same 64 question")


def test_cached_report_returns_without_fit_or_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "OUTPUT", tmp_path)
    plan, data = {"plan": 1}, {"rows": 1}
    monkeypatch.setattr(pilot, "checked_plan", lambda: (plan, data))
    monkeypatch.setattr(pilot, "analyze", lambda *a: pytest.fail("refit"))
    pilot.original.write_once(tmp_path / "report.json", {"plan_sha256": digest(plan),
        "rows_sha256": digest(data), "spec": pilot.SPEC,
        "fit_count": pilot.SPEC["fit_limit"], "fits": [{}] * 10,
        "actions": [{}] * 128, "parent_study_preserved": True})
    assert pilot.execute()["cached"] is True
    (tmp_path / "report.json").unlink()
    pilot.original.write_once(tmp_path / "execute-started.json", {"one_attempt": True})
    with pytest.raises(ValueError, match="already attempted"):
        pilot.execute()


def test_postfit_preservation_check_precedes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "OUTPUT", tmp_path)
    plan, data = {"plan": 1}, {"rows": [], "question_ids": [], "feature_extraction_seconds": 0.}
    versions = iter([(plan, data), ({"plan": 2}, data)])
    monkeypatch.setattr(pilot, "checked_plan", lambda: next(versions))
    monkeypatch.setattr(pilot, "analyze", lambda *_: {"fit_count": 20})
    with pytest.raises(ValueError, match="changed during execution"):
        pilot.execute()
    assert (tmp_path / "execute-started.json").exists()
    assert not (tmp_path / "report.json").exists()


def test_cost_and_target_exclude_sunk_direct_from_gain():
    row = {"direct_correct": 0, "thinking_correct": 1, "direct_tokens": 200,
           "thinking_tokens": 1000}
    assert pilot.target(row) == pytest.approx(.95)
    assert pilot.policy_utility(row, False) == pytest.approx(-.01)
    assert pilot.policy_utility(row, True) == pytest.approx(.94)
    assert pilot.policy_utility(row, True) - pilot.policy_utility(row, False) == pytest.approx(pilot.target(row))
