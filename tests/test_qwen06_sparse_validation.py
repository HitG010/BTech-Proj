"""Synthetic tests for the frozen sparse-validation preparation boundary."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from reasoning_budget.data import normalized
from reasoning_budget.storage import digest
from scripts import qwen06_sparse_validation as sparse


def training_rows(gain_at_zero=1, gain_at_one=-1):
    rows = []
    for draw in (0, 1):
        for i in range(64):
            confident = i % 2
            rows.append({"question_id": f"q{i}", "draw": draw,
                         "features": [float(confident), 0.0, float(i % 3 == 0)],
                         "direct_correct": 0 if (gain_at_zero if not confident else gain_at_one) > 0 else 1,
                         "thinking_correct": 1 if (gain_at_zero if not confident else gain_at_one) > 0 else 0,
                         "thinking_tokens": 0})
    return rows


def test_one_full_data_threshold_tie_and_label_dependence():
    rows = training_rows()
    fit = sparse.select_threshold(rows)
    assert fit["threshold"] == 1.0
    assert fit["training_escalations"] == 64
    # All equal zero gains: fewer escalations wins, independent of rejects.
    for row in rows:
        row["thinking_correct"] = row["direct_correct"]
    assert sparse.select_threshold(rows)["threshold"] == "never"
    # Features stay fixed, but training labels may legitimately move the fit.
    for row in rows:
        row["direct_correct"], row["thinking_correct"] = 1, 0
    assert sparse.select_threshold(rows)["threshold"] == "never"
    assert sparse.decode_threshold("always") == float("inf")
    assert sparse.decode_threshold("never") == float("-inf")


def test_training_requires_exact_two_draw_64_group_boundary():
    rows = training_rows()
    with pytest.raises(ValueError):
        sparse.select_threshold(rows[:-1])
    bad = deepcopy(rows)
    bad[-1]["question_id"] = "new_question"
    with pytest.raises(ValueError):
        sparse.select_threshold(bad)
    bad = deepcopy(rows)
    bad[0]["features"][0] = float("nan")
    with pytest.raises(ValueError):
        sparse.select_threshold(bad)


def parent_allocation(count=230):
    reserve = []
    for i in range(count):
        q = {"id": f"r{i}", "prompt": f"Compute {i}?", "split": "reserve",
             "source": "fixture"}
        reserve.append({"question": q, "pool": "external", "group_id": q["id"],
                        "upstream_index": i,
                        "normalized_prompt_sha256": digest(normalized(q["prompt"]))})
    other_q = {"id": "other", "prompt": "Other?", "split": "validation", "source": "fixture"}
    return {"roles": {"reserve": reserve, "validation": [{"question": other_q,
             "pool": "external", "group_id": "other", "upstream_index": 900,
             "normalized_prompt_sha256": digest(normalized(other_q["prompt"]))}]},
            "source": {"fixture": True}}


def test_question_only_selection_hashorder_role_and_sibling_audit(tmp_path):
    from reasoning_budget.storage import atomic_json, envelope
    allocation = parent_allocation()
    old = tmp_path / "opportunity64-v1"
    old.mkdir()
    row = allocation["roles"]["reserve"][0]
    selected = {"parent_question": row["question"],
                "child_question": dict(row["question"], split="opportunity64"),
                **{k: row[k] for k in ("upstream_index", "pool", "group_id",
                                        "normalized_prompt_sha256")}}
    atomic_json(old / "child-manifest.json", envelope({"parent_payload_sha256": digest(allocation),
                                                       "selected": [selected]}))
    before = digest(allocation)
    chosen, pins, remaining = sparse.select_fresh(allocation, tmp_path)
    assert len(chosen) == 228 and remaining == 229 and pins.keys() == {old.name}
    assert selected["group_id"] not in {r["group_id"] for r in chosen}
    assert chosen == sparse.select_fresh(allocation, tmp_path)[0]
    assert digest(allocation) == before
    allocation["roles"]["validation"][0]["question"]["prompt"] = chosen[0]["parent_question"]["prompt"]
    with pytest.raises(ValueError, match="overlap"):
        sparse.select_fresh(allocation, tmp_path)


def test_sibling_tamper_and_insufficient_reserve_fail_closed(tmp_path):
    from reasoning_budget.storage import atomic_json, envelope
    allocation = parent_allocation(228)
    sibling = tmp_path / "old"
    sibling.mkdir()
    row = allocation["roles"]["reserve"][0]
    bad = {"parent_question": dict(row["question"], prompt="tampered"),
           "child_question": dict(row["question"], split="old"),
           **{k: row[k] for k in ("upstream_index", "pool", "group_id",
                                   "normalized_prompt_sha256")}}
    atomic_json(sibling / "child-manifest.json",
                envelope({"parent_payload_sha256": digest(allocation), "selected": [bad]}))
    with pytest.raises(ValueError):
        sparse.select_fresh(allocation, tmp_path)
    (sibling / "child-manifest.json").unlink()
    sibling.rmdir()
    with pytest.raises(ValueError, match="Fewer"):
        sparse.select_fresh(parent_allocation(227), tmp_path)


def direct_fixture():
    jobs = [{"id": f"j{i}", "question_id": f"q{i}", "mode": "direct"} for i in range(sparse.N)]
    rows = [{"job": j, "status": "completed",
             "result": {"mean_generated_logprob": 0.0, "final_answer": "unparseable",
                        "answer_truncated": False, "termination": "answer_limit"}}
            for j in jobs]
    return jobs, rows


def test_eligibility_requires_full_direct_and_hard_caps_without_subsample():
    jobs, rows = direct_fixture()
    with patch("reasoning_budget.scoring_v7.extract_record", return_value=(None, "invalid_number")):
        with pytest.raises(ValueError, match="All 228"):
            sparse.eligibility(rows[:-1], jobs, "never")
        with pytest.raises(ValueError, match="Hard resource stop"):
            sparse.eligibility(rows, jobs, "never")
        assert sparse.eligibility(rows, jobs, "always") == []
        rows[0]["result"]["mean_generated_logprob"] = float("nan")
        with pytest.raises(ValueError, match="Finite"):
            sparse.eligibility(rows, jobs, "always")
    rows[0]["result"]["mean_generated_logprob"] = 0.0
    def first_n_reject(n):
        return lambda row: (None, "invalid_number") if int(row["job"]["id"][1:]) < n else ("1", "ok")
    with patch("reasoning_budget.scoring_v7.extract_record", side_effect=first_n_reject(32)):
        assert len(sparse.eligibility(rows, jobs, "never")) == 32
    with patch("reasoning_budget.scoring_v7.extract_record", side_effect=first_n_reject(33)):
        with pytest.raises(ValueError, match="Hard resource stop"):
            sparse.eligibility(rows, jobs, "never")


def test_eligibility_uses_gold_free_reject_not_correctness():
    jobs, rows = direct_fixture()
    rows[0]["result"]["mean_generated_logprob"] = 1.0
    def parser(row):
        return (None, "invalid_number") if row["job"]["id"] == "j0" else ("1", "ok")
    with patch("reasoning_budget.scoring_v7.extract_record", side_effect=parser):
        assert sparse.eligibility(rows, jobs, 0.0) == ["q0"]
    rows[0]["status"] = "pending"
    with patch("reasoning_budget.scoring_v7.extract_record", side_effect=parser):
        with pytest.raises(ValueError, match="status"):
            sparse.eligibility(rows, jobs, 0.0)


def test_eligibility_rejects_duplicate_question_nonzero_sample_and_timeout():
    jobs, rows = direct_fixture()
    jobs[1]["question_id"] = jobs[0]["question_id"]
    with pytest.raises(ValueError, match="distinct direct jobs"):
        sparse.eligibility(rows, jobs, "never")
    jobs[1]["question_id"] = "q1"
    jobs[1]["sample"] = 1
    with pytest.raises(ValueError, match="distinct direct jobs"):
        sparse.eligibility(rows, jobs, "never")
    jobs[1]["sample"] = 0
    rows[0]["result"]["termination"] = "timeout"
    with pytest.raises(ValueError, match="status"):
        sparse.eligibility(rows, jobs, "never")


def test_sparse_delta_cost_accuracy_ci_and_zero_event():
    ids = [f"q{i}" for i in range(sparse.N)]
    out = sparse.sparse_delta([], {}, ids, draws=50)
    assert out["ci95"] == [0.0, 0.0] and out["conditional_thinking_accuracy"] is None
    assert not out["further_study_screen"]
    outcomes = {"q0": {"thinking_correct": 1, "thinking_tokens": 1000},
                "q1": {"thinking_correct": 0, "thinking_tokens": 2000}}
    out = sparse.sparse_delta(["q0", "q1"], outcomes, ids, draws=100)
    assert out["mean_incremental_utility"] == pytest.approx((0.95 - 0.1) / sparse.N)
    assert out["accuracy_delta"] == 1 / sparse.N
    assert out["extra_thinking_tokens_per_question"] == 3000 / sparse.N
    assert out["conditional_thinking_accuracy"] == 0.5
    assert out["ci95"] == sparse.sparse_delta(["q0", "q1"], outcomes, ids, draws=100)["ci95"]
    with pytest.raises(ValueError):
        sparse.sparse_delta(["q0"], outcomes, ids, draws=10)
    overflow = {q: {"thinking_correct": 0, "thinking_tokens": 0} for q in ids[:33]}
    with pytest.raises(ValueError, match="coverage"):
        sparse.sparse_delta(ids[:33], overflow, ids, draws=10)


def test_response_bound_and_collector_locked():
    assert sparse.SPEC["response_only_bound"] == 198720
    assert sparse.SPEC["collector"] == "unimplemented_locked"
    assert sparse.SPEC["proposed_global_tokens"] == 250000


def test_always_threshold_refuses_question_allocation_before_selection():
    policy = {"fit": {"threshold": "always"}}
    with (patch.object(sparse, "checked_policy", return_value=({}, policy)),
          patch.object(sparse, "_review", return_value={}),
          patch.object(sparse, "select_fresh") as selection):
        with pytest.raises(ValueError, match="No fresh policy contrast"):
            sparse.prepare_questions()
        selection.assert_not_called()
