"""Synthetic-only checks for the additive post-hoc diagnosis."""

import numpy as np
import pytest

from reasoning_budget.storage import run_lock
from scripts import diagnose_repeat_signal as diagnosis


def panel():
    d = np.zeros((2, 8, 3), dtype=float)
    t = np.zeros_like(d)
    d[:, :, 1:] = [100, 2]
    t[:, :, 1:] = [200, 5]
    d[0, :, 0] = t[0, :, 0] = 1  # Direct is sunk; thinking adds cost without rescue.
    t[1, :, 0] = 1               # Thinking rescues this question.
    return d, t


def test_hindsight_oracle_charges_direct_and_thinking_and_counts_states():
    d, t = panel()
    report, gains = diagnosis.outcomes(d, t, 0.05)
    assert report["paired_states"] == {"both_correct": 8, "rescue": 8,
                                        "harm": 0, "both_wrong": 0}
    assert gains[0, 0] == pytest.approx(-0.01)
    assert gains[1, 0] == pytest.approx(0.99)
    assert report["oracle"]["escalated_pairs"] == 8
    assert report["oracle"]["mean_gain_over_accept"] == pytest.approx(0.495)
    assert report["mean_accept_utility"] == pytest.approx(0.495)
    assert report["mean_escalate_utility"] == pytest.approx(0.985)


def test_same_question_half_transfer_uses_train_half_only():
    d, t = panel()
    # Q1 changes from a rescue in A to a harm in B. A's selection is fixed by A.
    d[1, 4:, 0] = 1
    t[1, 4:, 0] = 0
    report, _ = diagnosis.outcomes(d, t, 0.05)
    a_to_b = report["same_question_half_transfer"]["A_to_B"]
    b_to_a = report["same_question_half_transfer"]["B_to_A"]
    assert a_to_b["same_question_train_half_positive"] == 1
    assert a_to_b["gain_over_accept"] == pytest.approx(-0.505)
    assert b_to_a["same_question_train_half_positive"] == 0
    assert b_to_a["gain_over_accept"] == 0
    assert a_to_b["same_question_only_not_unseen_question_generalization"] is True
    assert a_to_b["evaluation_utility_excludes_selection_acquisition"] is True
    assert a_to_b["not_net_acquisition_utility_or_deployed_policy"] is True
    acquisition = a_to_b["selection_acquisition"]
    assert acquisition["paired_draws_per_question"] == 4
    assert acquisition["responses_per_question"] == 8
    assert acquisition["paired_draws_total"] == 8
    assert acquisition["responses_total"] == 16
    assert acquisition["tokens_per_question"] == pytest.approx([1200, 1200])
    assert acquisition["seconds_per_question"] == pytest.approx([28, 28])
    assert acquisition["tokens_total"] == pytest.approx(2400)
    assert acquisition["seconds_total"] == pytest.approx(56)


def test_signed_between_variance_is_not_clipped_at_zero():
    gains = np.array([[1, -1] * 4, [1, -1] * 4], dtype=float)
    result = diagnosis.signed_between(gains)
    assert result["question_mean_sample_variance"] == 0
    assert result["within_mean_sample_variance"] == pytest.approx(8 / 7)
    assert result["signed_between_estimate"] == pytest.approx(-1 / 7)
    assert diagnosis.between_ci90(gains) == pytest.approx([-1 / 7, -1 / 7])


def test_policy_counts_useful_wasted_harmful_and_missed_with_sunk_cost():
    d, t = panel()
    t[0, 0, 0] = 0
    summary = {"mean_accuracy": 0.5, "mean_tokens": 200,
               "mean_seconds": 4.5, "mean_utility": 0.49,
               "mean_escalation_rate": 0.5}
    primary = {"conditions": {"synthetic": {
        "train_draws": [0], "evaluation_draws": [0, 1],
        "per_question": {
            "q0": {"policies": {"combined": {"decisions": [True, False]}}},
            "q1": {"policies": {"combined": {"decisions": [True, False]}}},
        },
        "summary": {"combined": summary},
    }}}
    result = diagnosis.policy_diagnostics(primary, ["q0", "q1"], d, t, 0.05)
    policy = result["synthetic"]["policies"]["combined"]
    assert policy["useful_escalations_gain_positive"] == 1
    assert policy["wasted_escalations_gain_nonpositive"] == 1
    assert policy["harmful_escalations_thinking_wrong_direct_correct"] == 1
    assert policy["missed_positive_gain_opportunities"] == 1
    assert policy["mean_utility"] == pytest.approx(0.49)


def test_incomplete_endpoint_blocks_scores_and_report(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnosis, "read_protocol", lambda _: {"snapshot": {"jobs": [{}] * 800}})
    monkeypatch.setattr(diagnosis, "checked_run", lambda *_: ({}, [{"status": "completed"}] * 799))
    monkeypatch.setattr(diagnosis, "verified", lambda *_: pytest.fail("Scored artifact opened early"))
    with pytest.raises(ValueError, match="all 800"):
        diagnosis.diagnose(tmp_path)


def test_frozen_post_hoc_plan_rejects_source_or_input_change(tmp_path):
    target = tmp_path / "analysis-plan.json"
    plan = {"script_sha256": "source-A", "input_file_sha256": {"report": "input-A"}}
    diagnosis.freeze_plan(target, plan)
    diagnosis.freeze_plan(target, plan)
    with pytest.raises(ValueError, match="identity changed"):
        diagnosis.freeze_plan(target, plan | {"script_sha256": "source-B"})
    with pytest.raises(ValueError, match="identity changed"):
        diagnosis.freeze_plan(target, plan | {"input_file_sha256": {"report": "input-B"}})


def test_output_freeze_rejects_held_directory_lock(tmp_path):
    output = tmp_path / "diagnosis"
    with run_lock(output):
        with pytest.raises(ValueError, match="holds the run lock"):
            diagnosis.write_output(output, {"version": 1}, {"report": True})
    assert not (output / "analysis-plan.json").exists()
    diagnosis.write_output(output, {"version": 1}, {"report": True})
    assert diagnosis.verified(output / "report.json") == {"report": True}
