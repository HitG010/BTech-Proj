"""Synthetic, cached-only checks for fixed 1.7B descriptive policies."""

from contextlib import nullcontext

import pytest

from reasoning_budget.storage import digest
from scripts import qwen17_solver_diagnosis as diagnosis


def row(**changes):
    value = {"question_id": "q0", "draw": 0, "direct_correct": 1,
        "thinking_correct": 0, "direct_tokens": 200, "thinking_tokens": 1000,
        "confidence": -1., "raw_confidence": -1.1, "confidence_action": True,
        "direct_parser_status": "ok", "thinking_parser_status": "incomplete",
        "direct_termination": "eos", "thinking_termination": "answer_limit",
        "direct_answer_truncated": False, "thinking_answer_truncated": True,
        "thinking_forced_closure": True, "direct_forced_closure": False,
        "direct_answer_tokens": 200, "thinking_answer_tokens": 512,
        "thinking_reasoning_tokens": 2048,
        "direct_final_sha256": "d", "thinking_final_sha256": "t",
        "direct_final_chars": 10, "thinking_final_chars": 20,
        "direct_final_has_box": True, "thinking_final_has_box": False}
    return value | changes


def protocol():
    return {"arms": {diagnosis.SOLVER: {"config": {
        "direct": {"temperature": .7, "top_p": .8, "top_k": 20},
        "thinking": {"temperature": .6, "top_p": .95, "top_k": 20}}}}}


def test_post_thinking_fallback_keeps_paid_cost_and_recovers_harm():
    case = row()
    confidence = diagnosis.policy_value(case, "frozen_confidence")
    syntax = diagnosis.policy_value(case, "post_thinking_syntax_fallback")
    cap = diagnosis.policy_value(case, "post_thinking_forced_closure_fallback")
    assert confidence["correct"] == 0 and syntax["correct"] == cap["correct"] == 1
    assert confidence["tokens"] == syntax["tokens"] == cap["tokens"] == 1200
    assert syntax["utility"] - confidence["utility"] == 1
    assert syntax["escalate"] and not syntax["use_thinking"]


def test_cap_fallback_can_lose_rescue_and_is_not_causal_claim():
    rescue = row(direct_correct=0, thinking_correct=1,
        thinking_parser_status="ok", thinking_termination="eos",
        thinking_answer_truncated=False)
    confidence = diagnosis.policy_value(rescue, "frozen_confidence")
    cap = diagnosis.policy_value(rescue, "post_thinking_forced_closure_fallback")
    syntax = diagnosis.policy_value(rescue, "post_thinking_syntax_fallback")
    assert confidence["correct"] == syntax["correct"] == 1 and cap["correct"] == 0
    assert confidence["tokens"] == cap["tokens"]


def test_direct_reject_or_rule_is_fixed_and_charges_thinking():
    case = row(confidence_action=False, direct_parser_status="invalid_number",
        thinking_parser_status="ok", thinking_forced_closure=False)
    baseline = diagnosis.policy_value(case, "frozen_confidence")
    augmented = diagnosis.policy_value(case, "confidence_or_direct_reject")
    assert not baseline["escalate"] and augmented["escalate"]
    assert augmented["tokens"] == baseline["tokens"] + case["thinking_tokens"]


def test_summarize_groups_repeats_and_reports_fixed_cost_arithmetic():
    rows = [row(question_id=f"q{i}", draw=draw,
        direct_correct=0 if i == 0 else 1,
        thinking_correct=1 if i == 0 else 0) for draw in (0, 1) for i in range(64)]
    report = diagnosis.summarize(rows, protocol())
    assert report["counts"]["rescue"] == {"cells": 2, "distinct_questions": 1,
        "repeated_in_both_draws": 1, "reasoning_cap_cells": 2}
    assert report["counts"]["harm"]["cells"] == 126
    assert report["counts"]["thinking"]["reasoning_at_2048"] == 128
    assert report["policies"]["frozen_confidence"]["escalations"] == 128
    assert report["policies"]["post_thinking_syntax_fallback"]["post_thinking_fallbacks"] == 128
    assert report["policies"]["post_thinking_syntax_fallback"]["harms_recovered_by_fallback"] == 126
    assert report["policies"]["post_thinking_syntax_fallback"]["rescues_lost_by_fallback"] == 2
    assert report["policies"]["accept"]["generated_tokens_per_pair"] == 200
    assert report["policies"]["think_after_direct"]["generated_tokens_per_pair"] == 1200
    assert report["sampling_match_official_qwen3_1p7b_card"]["matches"]
    assert report["gold_free_parser_failures"][0]["final_answer_sha256"] == "t"
    assert all("final_answer" not in item for item in report["gold_free_parser_failures"])
    bound = report["fixed_action_parser_upper_bounds"]
    assert bound["thinking_rejected_cells"] == 128
    assert bound["confidence_selected_rejected_cells"] == 128
    assert bound["always_think_minus_accept_if_all_rejected_thinking_correct"] == pytest.approx(
        bound["always_think_minus_accept_current"] + 126 / 128)


def test_duplicate_pair_fails_before_descriptive_metrics():
    rows = [row(question_id=f"q{i}", draw=draw) for draw in (0, 1) for i in range(64)]
    rows[-1] = rows[0]
    with pytest.raises(ValueError, match="128 unique pairs"):
        diagnosis.summarize(rows, protocol())


def test_one_execute_marker_and_cached_report_never_recompute(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnosis, "OUTPUT", tmp_path)
    plan, rows = {"plan": 1}, []
    monkeypatch.setattr(diagnosis, "checked", lambda: (plan, rows, protocol()))
    monkeypatch.setattr(diagnosis, "summarize", lambda *_: pytest.fail("recomputed"))
    monkeypatch.setattr(diagnosis, "run_lock", lambda _: nullcontext())
    diagnosis.original.write_once(tmp_path / "report.json", {"plan_sha256": digest(plan),
        "rows_sha256": digest(rows)})
    assert diagnosis.execute()["cached"]
    (tmp_path / "report.json").unlink()
    diagnosis.original.write_once(tmp_path / "execute-started.json", {"one_attempt": True})
    with pytest.raises(ValueError, match="already attempted"):
        diagnosis.execute()


def test_study_inventory_uses_only_closed_parent(tmp_path, monkeypatch):
    study = tmp_path / "study"
    (study / "completion-v1").mkdir(parents=True)
    (study / "completion-v1/report.json").write_text("closed")
    monkeypatch.setattr(diagnosis, "STUDY", study)
    monkeypatch.setattr(diagnosis.original, "safe_paths", lambda: None)
    assert set(diagnosis.inventory()) == {"completion-v1/report.json"}
