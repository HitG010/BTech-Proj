"""Synthetic endpoint, label-access and question-group analysis checks."""

import copy
import math

import pytest

from reasoning_budget.records import GenerationResult
from reasoning_budget.storage import atomic_json, envelope
from scripts import opportunity_panel_analysis as analysis


def panel():
    ids = [f"q{i:02d}" for i in range(64)]
    folds = {q: i % 5 for i, q in enumerate(ids)}
    rows = []
    for i, q in enumerate(ids):
        for solver in analysis.SOLVERS:
            for draw in (0, 1):
                # Twelve rescue questions for the first solver; second has
                # twelve harmful calls and no positive-gain questions.
                rescue = solver == analysis.SOLVERS[0] and i < 12
                harm = solver == analysis.SOLVERS[1] and i < 12
                rows.append({"question_id": q, "solver": solver, "draw": draw,
                    "direct_correct": int(not rescue), "thinking_correct": int(not harm),
                    "direct_tokens": 100, "thinking_tokens": 100,
                    "confidence": -float(i + draw) / 10,
                    "raw_confidence": -float((i + 7 * draw) % 19) / 10})
    return ids, folds, rows


def records(ids):
    result = GenerationResult(raw_output="7", reasoning="", final_answer="7", prompt_tokens=20,
        reasoning_tokens=0, answer_tokens=3, inserted_tokens=0, elapsed_seconds=.2,
        reasoning_seconds=0, answer_seconds=.2, closure_seconds=0, forced_closure=False,
        answer_truncated=False, termination="eos", mean_generated_logprob=-0.2,
        mean_generated_logprob_raw=-0.4, metadata={}).to_dict()
    return {solver: [{"job": {"id": f"{solver}-{q}-{mode}-{draw}", "question_id": q,
                                "mode": mode, "sample": draw},
                      "status": "completed", "result": dict(result)}
                     for q in ids for draw in (0, 1) for mode in analysis.MODES]
            for solver in analysis.SOLVERS}


def test_exact_paired_schema_and_question_folds():
    ids, folds, rows = panel()
    assert analysis.validate_pairs(rows, folds, ids) == ids
    with pytest.raises(ValueError, match="256"):
        analysis.validate_pairs(rows[:-1], folds, ids)
    bad = copy.deepcopy(rows)
    bad[1] = copy.deepcopy(bad[0])
    with pytest.raises(ValueError, match="Duplicate"):
        analysis.validate_pairs(bad, folds, ids)
    bad = copy.deepcopy(rows)
    bad[0]["direct_tokens"] = 1.5
    with pytest.raises(ValueError, match="integers"):
        analysis.validate_pairs(bad, folds, ids)
    bad = copy.deepcopy(rows)
    bad[0]["confidence"] = math.nan
    with pytest.raises(ValueError, match="Finite"):
        analysis.validate_pairs(bad, folds, ids)
    bad = copy.deepcopy(rows)
    bad[0]["raw_confidence"] = None
    with pytest.raises(ValueError, match="Finite"):
        analysis.validate_pairs(bad, folds, ids)
    wrong = dict(folds, q00=1)
    with pytest.raises(ValueError, match="balance"):
        analysis.validate_pairs(rows, wrong, ids)


def test_descriptive_opportunity_and_fixed_policy_cost_arithmetic():
    ids, folds, rows = panel()
    report = analysis.analyze_pairs(rows, folds, question_ids=ids)
    first = report["solvers"][analysis.SOLVERS[0]]
    second = report["solvers"][analysis.SOLVERS[1]]
    assert first["screen"]["positive_gain_questions"] == 12
    assert first["screen"]["availability_pass"]
    assert second["screen"]["positive_gain_questions"] == 0
    assert not second["screen"]["availability_pass"]
    assert first["draws"]["0"]["counts"] == {"rescue": 12, "harm": 0, "positive_gain": 12}
    assert second["draws"]["1"]["counts"] == {"rescue": 0, "harm": 12, "positive_gain": 0}
    accept = first["draws"]["0"]["policies"]["accept"]
    escalate = first["draws"]["0"]["policies"]["escalate"]
    assert accept["tokens"]["mean"] == 100
    assert escalate["tokens"]["mean"] == 200
    assert accept["utility"]["mean"] == pytest.approx(accept["correct"]["mean"] - .005)
    assert escalate["utility"]["mean"] == pytest.approx(escalate["correct"]["mean"] - .01)
    assert report == analysis.analyze_pairs(rows, folds, question_ids=ids)
    assert report["between_solver"]["rescue_rate_difference"]["mean"] == 12 / 64
    assert report["fixed_threshold_fits"] == 40
    assert "raw_confidence_secondary_screen" in first
    assert first["draws"]["0"]["confidence_actions"] != first["draws"]["0"]["raw_confidence_actions"]


def test_confidence_actions_do_not_read_heldout_or_opposite_draw_labels():
    ids, folds, rows = panel()
    baseline = analysis.analyze_pairs(rows, folds, question_ids=ids)
    altered = copy.deepcopy(rows)
    for row in altered:
        if row["question_id"] == "q00" or row["draw"] == 1:
            row["direct_correct"] = 1 - row["direct_correct"]
            row["thinking_correct"] = 1 - row["thinking_correct"]
    after = analysis.analyze_pairs(altered, folds, question_ids=ids)
    for solver in analysis.SOLVERS:
        before = baseline["solvers"][solver]["draws"]["1"]
        current = after["solvers"][solver]["draws"]["1"]
        # q00's held-out fold and all draw-1 outcomes cannot train 0->1.
        assert before["confidence_actions"][0] == current["confidence_actions"][0]
        assert before["confidence_thresholds"][0] == current["confidence_thresholds"][0]
        assert before["raw_confidence_actions"][0] == current["raw_confidence_actions"][0]
        assert before["raw_confidence_thresholds"][0] == current["raw_confidence_thresholds"][0]


def test_thresholds_serialize_without_nonfinite_numbers():
    ids, folds, rows = panel()
    for row in rows:
        row["confidence"] = -1.0
        row["raw_confidence"] = -2.0
        row["thinking_correct"] = row["direct_correct"]
    report = analysis.analyze_pairs(rows, folds, question_ids=ids)
    for solver in analysis.SOLVERS:
        for draw in ("0", "1"):
            assert set(report["solvers"][solver]["draws"][draw]["confidence_thresholds"]) == {"never"}
            assert set(report["solvers"][solver]["draws"][draw]["raw_confidence_thresholds"]) == {"never"}


def test_incomplete_endpoint_never_opens_references(tmp_path):
    ids, _, _ = panel()
    selected = [{"child_question": {"id": q}} for q in ids]
    runs = records(ids)
    runs[analysis.SOLVERS[1]].pop()
    called = []
    with pytest.raises(ValueError, match="full 256"):
        analysis.score_complete_endpoint(runs, selected, lambda _: called.append(True),
            protocol_sha256="fixture", output=tmp_path / "scores.json")
    assert not called and not (tmp_path / "scores.json").exists()


def test_score_cache_reuse_never_reopens_gold_and_pairs_are_exact(tmp_path, monkeypatch):
    ids, folds, _ = panel()
    selected = [{"child_question": {"id": q}} for q in ids]
    runs = records(ids)
    calls = []
    def gold_loader(chosen):
        calls.append(chosen)
        return {q: "7" for q in ids}
    def fake_score(record, gold):
        assert gold == "7"
        job = record["job"]
        return {"job_id": job["id"], "question_id": job["question_id"],
                "mode": job["mode"], "extracted_answer": "7", "parser_status": "ok",
                "correct": True, "scoring_version": "numeric-v7"}
    monkeypatch.setattr(analysis.scoring_v7, "score_record", fake_score)
    output = tmp_path / "scores.json"
    scored = analysis.score_complete_endpoint(runs, selected, gold_loader,
        protocol_sha256="fixture", output=output)
    assert len(calls) == 1 and len(scored["scores"]) == 512
    assert analysis.score_complete_endpoint(runs, selected, lambda _: pytest.fail("gold reopened"),
        protocol_sha256="fixture", output=output) == scored
    pairs = analysis.paired_rows(runs, scored)
    assert len(pairs) == 256
    assert analysis.validate_pairs(pairs, folds, ids) == ids
    assert all(row["confidence"] == -0.2 and row["raw_confidence"] == -0.4 for row in pairs)
    with pytest.raises(ValueError, match="identity"):
        analysis.score_complete_endpoint(runs, selected, lambda _: pytest.fail("gold reopened"),
            protocol_sha256="changed", output=output)


def test_tampered_score_cache_job_set_fails_without_gold(tmp_path):
    ids, _, _ = panel()
    selected = [{"child_question": {"id": q}} for q in ids]
    runs = records(ids)
    output = tmp_path / "scores.json"
    header = {"protocol_sha256": "fixture", "selected_sha256": analysis.digest(selected),
              "records_sha256": analysis.digest(runs), "scoring_version": "numeric-v7",
              "scoring_implementation_sha256": analysis.scoring_v7.implementation_digest()}
    scores = [{"solver": solver, "job_id": r["job"]["id"],
               "question_id": r["job"]["question_id"], "mode": r["job"]["mode"],
               "extracted_answer": "7", "parser_status": "ok", "correct": True,
               "scoring_version": "numeric-v7"}
              for solver in analysis.SOLVERS for r in runs[solver]]
    scores[0]["job_id"] = "different"
    atomic_json(output, envelope(header | {"scores": scores, "gold_sha256": "fixture"}))
    with pytest.raises(ValueError, match="identity"):
        analysis.score_complete_endpoint(runs, selected, lambda _: pytest.fail("gold reopened"),
            protocol_sha256="fixture", output=output)


@pytest.mark.parametrize("field,value", [
    ("question_id", "wrong"), ("mode", "wrong"), ("scoring_version", "numeric-v5"),
    ("parser_status", None), ("correct", 1)])
def test_cached_score_semantics_checked_before_return(tmp_path, field, value):
    ids, _, _ = panel()
    selected = [{"child_question": {"id": q}} for q in ids]
    runs = records(ids)
    scores = [{"solver": solver, "job_id": r["job"]["id"],
               "question_id": r["job"]["question_id"], "mode": r["job"]["mode"],
               "extracted_answer": "7", "parser_status": "ok", "correct": True,
               "scoring_version": "numeric-v7"}
              for solver in analysis.SOLVERS for r in runs[solver]]
    scores[0][field] = value
    output = tmp_path / "scores.json"
    header = {"protocol_sha256": "fixture", "selected_sha256": analysis.digest(selected),
              "records_sha256": analysis.digest(runs), "scoring_version": "numeric-v7",
              "scoring_implementation_sha256": analysis.scoring_v7.implementation_digest()}
    atomic_json(output, envelope(header | {"scores": scores, "gold_sha256": "fixture"}))
    with pytest.raises(ValueError, match="semantics"):
        analysis.score_complete_endpoint(runs, selected, lambda _: pytest.fail("gold reopened"),
            protocol_sha256="fixture", output=output)
