"""Synthetic verifier checks; no collected responses or reference answers."""

import copy

import pytest

from scripts import verify_phase2_repeat as verifier


def test_incomplete_endpoint_precedes_scores_reports_and_protected_files(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(verifier, "read_protocol", lambda _: calls.append("protocol") or {
        "snapshot": {"jobs": [{"id": str(i)} for i in range(800)]}
    })
    monkeypatch.setattr(verifier, "checked_run", lambda *_: calls.append("run") or (
        {"run_id": "synthetic"}, [{"status": "completed"}] * 799
    ))
    monkeypatch.setattr(verifier, "verified", lambda *_: pytest.fail("Opened scored/report artifact before endpoint"))
    monkeypatch.setattr(verifier, "file_hash", lambda *_: pytest.fail("Opened protected file before endpoint"))
    with pytest.raises(ValueError, match="all 800 responses"):
        verifier.verify(tmp_path)
    assert calls == ["protocol", "run"]


def test_policy_arithmetic_charges_direct_then_conditional_thinking():
    def record(job_id, mode, sample, tokens, seconds):
        return {"job": {"id": job_id, "question_id": "q", "mode": mode, "sample": sample},
                "result": {"reasoning_tokens": 0, "answer_tokens": tokens,
                           "inserted_tokens": 0, "elapsed_seconds": seconds}}

    cells = {
        ("q", "direct", 0): record("d0", "direct", 0, 10, 2),
        ("q", "thinking", 0): record("t0", "thinking", 0, 100, 5),
        ("q", "direct", 1): record("d1", "direct", 1, 20, 3),
        ("q", "thinking", 1): record("t1", "thinking", 1, 200, 7),
    }
    scores = {job: {"correct": correct} for job, correct in
              [("d0", True), ("t0", False), ("d1", False), ("t1", True)]}
    measured = verifier.policy_rows(cells, scores, "q", [0, 1], [False, True], 0.05)
    assert measured == pytest.approx({
        "accuracy": 1.0, "tokens": 115.0, "seconds": 6.0,
        "utility": 1 - 0.05 * 115 / 1000, "escalation_rate": 0.5,
    })
    with pytest.raises(ValueError, match="decisions"):
        verifier.policy_rows(cells, scores, "q", [0, 1], [False], 0.05)


def test_frozen_outer_folds_and_current_acquisition_schema():
    ids = [f"q{i}" for i in range(5)]
    folds = {qid: i for i, qid in enumerate(ids)}
    cells = {}
    for qid in ids:
        for mode, tokens in (("direct", 10), ("thinking", 100)):
            cells[qid, mode, 0] = {"result": {
                "reasoning_tokens": 0, "answer_tokens": tokens, "inserted_tokens": 0,
            }}
    condition = {"folds": []}
    for index in range(5):
        condition["folds"].append({
            "fold": index, "train_ids": [qid for qid in ids if folds[qid] != index],
            "test_ids": [ids[index]],
            "training_acquisition": {"paired_draws": 4, "responses": 8,
                                     "direct_tokens": 40, "thinking_tokens": 400,
                                     "total_tokens": 440},
        })
    verifier.check_condition_folds(condition, ids, folds, [0], cells)

    wrong = copy.deepcopy(condition)
    wrong["folds"][0]["training_acquisition"]["responses"] = 4
    with pytest.raises(ValueError, match="pair/response"):
        verifier.check_condition_folds(wrong, ids, folds, [0], cells)
    wrong = copy.deepcopy(condition)
    wrong["folds"][0]["test_ids"] = ["q1"]
    with pytest.raises(ValueError, match="train/test IDs"):
        verifier.check_condition_folds(wrong, ids, folds, [0], cells)
