"""Independent fixed-endpoint audit of the frozen Phase 2 repeat panel.

This script reads only existing v7 scores. It never loads reference answers or
re-scores responses, and it refuses partial collection before opening scores or
the analysis report.
"""

import argparse
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.research_repeat import ROOT, STUDY, checked_run, read_protocol
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, verified


def close(actual, expected):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError(f"Arithmetic mismatch: {actual} versus {expected}")


def policy_rows(cells, scores, qid, draws, decisions, preference):
    """Recompute a policy's per-question outcome from cached paired records."""
    if len(decisions) != len(draws) or any(type(decision) is not bool for decision in decisions):
        raise ValueError("Invalid frozen policy decisions")
    chosen, tokens, seconds = [], [], []
    for sample, escalate in zip(draws, decisions):
        direct = cells[qid, "direct", sample]
        thinking = cells[qid, "thinking", sample]
        d_result, t_result = direct["result"], thinking["result"]
        d_score, t_score = scores[direct["job"]["id"]], scores[thinking["job"]["id"]]
        chosen.append(int(t_score["correct"] if escalate else d_score["correct"]))
        tokens.append(stage_tokens(d_result) + (stage_tokens(t_result) if escalate else 0))
        seconds.append(d_result["elapsed_seconds"] + (t_result["elapsed_seconds"] if escalate else 0))
    n = len(draws)
    return {
        "accuracy": sum(chosen) / n,
        "tokens": sum(tokens) / n,
        "seconds": sum(seconds) / n,
        "utility": sum(correct - preference * cost / 1000 for correct, cost in zip(chosen, tokens)) / n,
        "escalation_rate": sum(decisions) / n,
    }


def stage_tokens(result):
    return sum(result[f"{stage}_tokens"] for stage in ("reasoning", "answer", "inserted"))


def check_condition_folds(condition, ordered_ids, frozen_folds, train_draws, cells):
    """Verify question partitions and one-time acquisition totals for each outer fit."""
    if len(condition["folds"]) != 5 or set(frozen_folds) != set(ordered_ids):
        raise ValueError("Frozen outer-fold coverage mismatch")
    for fold_number, fold in enumerate(condition["folds"]):
        expected_train = [qid for qid in ordered_ids if frozen_folds[qid] != fold_number]
        expected_test = [qid for qid in ordered_ids if frozen_folds[qid] == fold_number]
        if (fold["fold"] != fold_number or fold["train_ids"] != expected_train
                or fold["test_ids"] != expected_test or not expected_test):
            raise ValueError("Reported outer-fold train/test IDs differ from frozen partition")
        direct_cost = sum(stage_tokens(cells[qid, "direct", sample]["result"])
                          for qid in expected_train for sample in train_draws)
        thinking_cost = sum(stage_tokens(cells[qid, "thinking", sample]["result"])
                            for qid in expected_train for sample in train_draws)
        acquisition = fold["training_acquisition"]
        pairs = len(expected_train) * len(train_draws)
        if acquisition["paired_draws"] != pairs or acquisition["responses"] != 2 * pairs:
            raise ValueError("Training acquisition pair/response count mismatch")
        close(acquisition["direct_tokens"], direct_cost)
        close(acquisition["thinking_tokens"], thinking_cost)
        close(acquisition["total_tokens"], direct_cost + thinking_cost)


def verify(study=Path(ROOT) / STUDY):
    study = Path(study).resolve()
    protocol = read_protocol(study)
    manifest, rows = checked_run(study, protocol)
    jobs = protocol["snapshot"]["jobs"]
    if (manifest is None or len(jobs) != 800 or len(rows) != 800
            or any(row["status"] != "completed" for row in rows)):
        raise ValueError("Repeat verification locked until all 800 responses complete")

    # No score, report, protected-file, or reference-answer access occurs above.
    score_artifact = verified(study / "scores.numeric-v7.json")
    report = verified(study / "report.json")
    expected_jobs = {job["id"]: job for job in jobs}
    if len(expected_jobs) != 800 or {row["job"]["id"] for row in rows} != set(expected_jobs):
        raise ValueError("Repeat job identity mismatch")
    if any(row["job"] != expected_jobs[row["job"]["id"]] for row in rows):
        raise ValueError("Repeat record differs from frozen job")
    ordered_ids = [item["question"]["id"] for item in protocol["selected"]]
    selected_ids = set(ordered_ids)
    if len(selected_ids) != 50 or len(ordered_ids) != 50:
        raise ValueError("Repeat role is not exactly 50 questions")
    cells = {(row["job"]["question_id"], row["job"]["mode"], row["job"]["sample"]): row for row in rows}
    expected_cells = {(qid, mode, sample) for qid in selected_ids
                      for mode in ("direct", "thinking") for sample in range(8)}
    if len(cells) != 800 or set(cells) != expected_cells:
        raise ValueError("Repeat panel is not exactly 50 by 8 by 2")
    if score_artifact["protocol_sha256"] != digest(protocol) or score_artifact["allocation_sha256"] != protocol["allocation_sha256"]:
        raise ValueError("Score protocol/allocation identity mismatch")
    if score_artifact["run_id"] != manifest["run_id"] or score_artifact["records_sha256"] != digest(rows):
        raise ValueError("Score run/records identity mismatch")
    if score_artifact["scoring_version"] != "numeric-v7" or score_artifact["scoring_implementation_sha256"] != protocol["scoring_implementation_sha256"]:
        raise ValueError("Frozen v7 scorer identity mismatch")
    scored = score_artifact["scores"]
    scores = {item["job_id"]: item for item in scored}
    if len(scored) != 800 or len(scores) != 800 or set(scores) != set(expected_jobs):
        raise ValueError("Score cache has missing or duplicate jobs")
    for job_id, item in scores.items():
        job = expected_jobs[job_id]
        if (item["question_id"] != job["question_id"] or item["mode"] != job["mode"]
                or item["scoring_version"] != "numeric-v7" or type(item["correct"]) is not bool):
            raise ValueError("Score fields disagree with frozen job")
    if report["protocol_sha256"] != digest(protocol) or report["scores_sha256"] != digest(score_artifact):
        raise ValueError("Report identity mismatch")
    if report["synthetic"] or report["official_test_gold_opened"] or report["cloud_spend_usd"] != 0:
        raise ValueError("Unexpected report scope")

    run = Path(protocol["snapshot"]["run_dir"])
    attempts = [verified(path) for path in (run / "attempts").glob("*.json")]
    sessions = [verified(path) for path in (run / "sessions").glob("*.json")]
    attempt_by_id = {attempt["attempt_id"]: attempt for attempt in attempts}
    if len(attempt_by_id) != len(attempts):
        raise ValueError("Duplicate attempt IDs")
    for attempt in attempts:
        if (attempt["started_at"] < protocol["prepared_at"] or attempt["job_id"] not in expected_jobs
                or attempt["implementation_sha256"] != protocol["snapshot"]["generation_implementation"]):
            raise ValueError("Attempt provenance mismatch")
    spent = sum(attempt.get("charged_tokens", attempt["reserved_tokens"]) for attempt in attempts)
    duration = sum(attempt.get("elapsed_seconds", attempt["reserved_seconds"]) for attempt in attempts)
    setup = sum(session["setup_seconds"] if "setup_seconds" in session else session["reserved_seconds"]
                for session in sessions)
    close(report["collection_charged_tokens_all_attempts"], spent)
    close(report["collection_hours_all_attempts_and_setup"], (duration + setup) / 3600)
    limits = protocol["snapshot"]["config"]["limits"]
    if spent > limits["max_tokens"] or duration + setup > limits["max_elapsed_seconds"]:
        raise ValueError("Collection ledger exceeds frozen limits")
    for row in rows:
        result = row["result"]
        for stage in ("reasoning", "answer", "inserted"):
            if len(result["metadata"][f"{stage}_token_ids"]) != result[f"{stage}_tokens"]:
                raise ValueError("Stage-token accounting mismatch")
        if stage_tokens(result) > row["job"]["max_tokens"]:
            raise ValueError("Response exceeds job token cap")
        attempt = attempt_by_id[row["attempt_id"]]
        if attempt["job_id"] != row["job"]["id"] or attempt["charged_tokens"] != stage_tokens(result):
            raise ValueError("Final response/attempt charge mismatch")

    stats = report["statistics"]
    if stats["analysis"] != protocol["analysis"] or stats["question_count"] != 50 or set(stats["conditions"]) != {
        "k1_A_to_B", "k1_B_to_A", "k2_A_to_B", "k2_B_to_A",
        "k4_A_to_B", "k4_B_to_A", "k8_full",
    }:
        raise ValueError("Unexpected diagnostic analysis endpoint")
    preference = protocol["analysis"]["lambda"]
    expected_draws = {
        f"k{k}_{direction}": (list(range(k)) if direction == "A_to_B" else list(range(4, 4 + k)),
                                list(range(4, 8)) if direction == "A_to_B" else list(range(4)))
        for k in (1, 2, 4) for direction in ("A_to_B", "B_to_A")
    }
    expected_draws["k8_full"] = (list(range(8)), list(range(8)))
    for name, condition in stats["conditions"].items():
        train_draws, expected_evaluation = expected_draws[name]
        draws = condition["evaluation_draws"]
        if condition["train_draws"] != train_draws or draws != expected_evaluation:
            raise ValueError("Condition draw partition changed")
        if set(condition["per_question"]) != selected_ids:
            raise ValueError("Policy question coverage mismatch")
        check_condition_folds(condition, ordered_ids, protocol["folds"], train_draws, cells)
        for qid, item in condition["per_question"].items():
            if item["fold"] != protocol["folds"][qid]:
                raise ValueError("Per-question outer fold differs from frozen partition")
            for policy, observed in item["policies"].items():
                expected = policy_rows(cells, scores, qid, draws, observed["decisions"], preference)
                for key, value in expected.items():
                    close(observed[key], value)
        for policy, observed in condition["summary"].items():
            for metric in ("accuracy", "tokens", "seconds", "utility", "escalation_rate"):
                value = sum(condition["per_question"][qid]["policies"][policy][metric]
                            for qid in selected_ids) / 50
                close(observed[f"mean_{metric}"], value)
    if stats["scale_acquisition"] != all(stats["gates"].values()):
        raise ValueError("Scale gate flag inconsistent")
    parser_protocol = verified(Path(protocol["request"]["root"]) / "parser-v7-preflight-v1" / "protocol.json")
    protected = parser_protocol["protected_files_sha256"]
    if len(protected) != 2319 or any("gold" in path.lower() for path in protected):
        raise ValueError("Unexpected protected-original inventory")
    for path, expected in protected.items():
        if file_hash(path) != expected:
            raise ValueError(f"Protected original changed: {path}")
    old_confirmation = read_json("artifacts/confirmation/frozen-router-v1/status.json")
    if old_confirmation["generation_started"]:
        raise ValueError("Old confirmation unexpectedly started")
    verification = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": digest(protocol), "protocol_file_sha256": file_hash(study / "protocol.json"),
        "scores_sha256": digest(score_artifact), "scores_file_sha256": file_hash(study / "scores.numeric-v7.json"),
        "report_sha256": digest(report), "report_file_sha256": file_hash(study / "report.json"),
        "verification_script_sha256": file_hash(__file__),
        "completed_responses": 800, "question_count": 50,
        "attempts": len(attempts), "sessions": len(sessions),
        "attempt_statuses": dict(Counter(attempt["status"] for attempt in attempts)),
        "charged_tokens_all_attempts": spent, "elapsed_hours_all_attempts_and_setup": (duration + setup) / 3600,
        "protected_originals_verified": len(protected),
        "policy_arithmetic_verified": True, "gate_consistency_verified": True,
        "old_confirmation_generation_started": False, "official_test_gold_opened": False,
        "training_gold_opened_by_verifier": False, "cloud_spend_usd": 0,
    }
    target = study / "background-verification.json"
    if target.exists():
        existing = verified(target)
        def stable(value):
            return {key: entry for key, entry in value.items() if key != "verified_at_utc"}

        if stable(existing) != stable(verification):
            raise ValueError("Existing background verification requires separate review")
        return existing
    atomic_json(target, envelope(verification))
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", default=str(Path(ROOT) / STUDY))
    args = parser.parse_args()
    result = verify(args.study)
    print({"independent_verification": "passed", "completed": result["completed_responses"],
           "protected": result["protected_originals_verified"]})


if __name__ == "__main__":
    main()
