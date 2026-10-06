"""Gold-free, cached-only 1.7B solver and fixed-action diagnosis.

The old opportunity study is immutable. This post-hoc report fits no policy,
scores no response, opens no reference and generates no model output.
"""

import argparse
import hashlib
import math
import time
from collections import Counter
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, run_lock, verified
from scripts import opportunity_panel_collect as original
from scripts import opportunity_panel_completion as completion

ROOT = Path(__file__).resolve().parents[1]
STUDY = original.STUDY
OUTPUT = original.BASE / "qwen17-solver-diagnosis-v1"
SOLVER = "qwen3-1.7b"
FILES = ("scripts/qwen17_solver_diagnosis.py", "tests/test_qwen17_solver_diagnosis.py",
         "docs/qwen17-performance-diagnosis.md")
SPEC = {"version": "qwen17-solver-diagnosis-v1", "scope": "post_hoc/descriptive",
        "solver": SOLVER, "questions": 64, "draws": 2, "lambda": .05,
        "policies": ["accept", "think_after_direct", "frozen_confidence",
            "confidence_or_direct_reject", "post_thinking_syntax_fallback",
            "post_thinking_forced_closure_fallback"],
        "bootstrap": "none; exact cached counts and fixed actions only",
        "no_refit_rescore_generation_or_reference_access": True}


def fail(message):
    raise ValueError(message)


def sources():
    return {name: file_hash(ROOT / name) for name in FILES}


def inventory():
    original.safe_paths()
    return {str(path.relative_to(STUDY)): file_hash(path)
            for path in sorted(STUDY.rglob("*")) if path.is_file()}


def inputs():
    child, protocol = completion.read_plan()
    terminal = verified(STUDY / "completion-v1/supervisor-finish.json")
    status = verified(STUDY / "completion-v1/status.json")
    records = completion.combined_records(child, protocol)
    report = verified(STUDY / "completion-v1/report.json")
    score = verified(STUDY / "completion-v1/scores.numeric-v7.json")
    if (terminal["state"] != "complete" or status["state"] != "complete"
            or terminal["report_sha256"] != digest(report)
            or status["report_sha256"] != digest(report)
            or report["plan_sha256"] != digest(child)
            or report["parent_protocol_sha256"] != digest(protocol)
            or report["scores_sha256"] != digest(score)
            or report["old_protocol_budget_passed"] is not False
            or score["protocol_sha256"] != digest(child)
            or score["records_sha256"] != digest(records)
            or score["selected_sha256"] != digest(protocol["selected"])
            or score["scoring_version"] != "numeric-v7"
            or score["scoring_implementation_sha256"] != protocol["scoring_implementation_sha256"]
            or len(score["scores"]) != 512 or len(records[SOLVER]) != 256):
        fail("Closed cached endpoint changed")
    scores = {}
    for row in score["scores"]:
        key = row["solver"], row["job_id"]
        if key in scores or type(row["correct"]) is not bool:
            fail("Duplicate or invalid cached score")
        scores[key] = row
    expected = {(solver, r["job"]["id"]) for solver in original.SOLVERS for r in records[solver]}
    if set(scores) != expected:
        fail("Cached score coverage changed")
    return child, protocol, records, report, score, scores


def cells(protocol, records, report, scores):
    ids = report["statistics"]["question_ids"]
    if (len(ids) != 64 or len(set(ids)) != 64 or set(ids) != set(protocol["folds"])
            or report["statistics"]["folds"] != protocol["folds"]):
        fail("Frozen 64-question folds changed")
    indexed = {(r["job"]["question_id"], r["job"]["sample"], r["job"]["mode"]): r
               for r in records[SOLVER]}
    if len(indexed) != 256 or set(indexed) != {(q, draw, mode) for q in ids
                                               for draw in (0, 1) for mode in ("direct", "thinking")}:
        fail("Frozen 1.7B job cells changed")
    output = []
    for draw in (0, 1):
        frozen = report["statistics"]["solvers"][SOLVER]["draws"][str(draw)]
        actions, thresholds = frozen["confidence_actions"], frozen["confidence_thresholds"]
        if len(actions) != 64 or len(thresholds) != 64:
            fail("Frozen confidence actions changed")
        for i, q in enumerate(ids):
            d, t = indexed[q, draw, "direct"], indexed[q, draw, "thinking"]
            ds, ts = scores[SOLVER, d["job"]["id"]], scores[SOLVER, t["job"]["id"]]
            if (ds["question_id"] != q or ts["question_id"] != q
                    or ds["mode"] != "direct" or ts["mode"] != "thinking"):
                fail("Cached score/job identity changed")
            confidence = d["result"]["mean_generated_logprob"]
            raw = d["result"]["mean_generated_logprob_raw"]
            if not (type(confidence) in (int, float) and type(raw) in (int, float)
                    and math.isfinite(confidence) and math.isfinite(raw)):
                fail("Finite direct confidence required")
            threshold = thresholds[i]
            value = math.inf if threshold == "always" else -math.inf if threshold == "never" else threshold
            if (type(actions[i]) is not bool or type(value) not in (int, float)
                    or threshold not in ("always", "never") and not math.isfinite(value)
                    or bool(confidence < value) != actions[i]):
                fail("Frozen confidence threshold/action changed")
            def charged(row):
                return sum(row["result"][name] for name in
                           ("reasoning_tokens", "answer_tokens", "inserted_tokens"))
            output.append({"question_id": q, "draw": draw, "direct_correct": int(ds["correct"]),
                "thinking_correct": int(ts["correct"]), "direct_tokens": charged(d),
                "thinking_tokens": charged(t), "confidence": confidence, "raw_confidence": raw,
                "confidence_action": actions[i], "direct_parser_status": ds["parser_status"],
                "thinking_parser_status": ts["parser_status"],
                "direct_termination": d["result"]["termination"],
                "thinking_termination": t["result"]["termination"],
                "direct_answer_truncated": d["result"]["answer_truncated"],
                "thinking_answer_truncated": t["result"]["answer_truncated"],
                "thinking_forced_closure": t["result"]["forced_closure"],
                "direct_forced_closure": d["result"]["forced_closure"],
                "direct_answer_tokens": d["result"]["answer_tokens"],
                "thinking_answer_tokens": t["result"]["answer_tokens"],
                "thinking_reasoning_tokens": t["result"]["reasoning_tokens"],
                "direct_final_sha256": hashlib.sha256(d["result"]["final_answer"].encode()).hexdigest(),
                "thinking_final_sha256": hashlib.sha256(t["result"]["final_answer"].encode()).hexdigest(),
                "direct_final_chars": len(d["result"]["final_answer"]),
                "thinking_final_chars": len(t["result"]["final_answer"]),
                "direct_final_has_box": "\\boxed{" in d["result"]["final_answer"],
                "thinking_final_has_box": "\\boxed{" in t["result"]["final_answer"]})
        original_utility = frozen["policies"]["confidence"]["utility"]["mean"]
        actual = sum(policy_value(row, "frozen_confidence")["utility"]
                     for row in output if row["draw"] == draw) / 64
        if abs(actual - original_utility) > 1e-10:
            fail("Frozen confidence utility did not reproduce")
    return output


def policy_value(row, name):
    confidence = row["confidence_action"]
    direct_ok = row["direct_parser_status"] == "ok"
    thinking_reject = row["thinking_parser_status"] != "ok"
    if name == "accept":
        escalate, use_thinking = False, False
    elif name == "think_after_direct":
        escalate, use_thinking = True, True
    elif name == "frozen_confidence":
        escalate, use_thinking = confidence, confidence
    elif name == "confidence_or_direct_reject":
        escalate = confidence or not direct_ok
        use_thinking = escalate
    elif name == "post_thinking_syntax_fallback":
        escalate = confidence
        use_thinking = confidence and not (thinking_reject and direct_ok)
    elif name == "post_thinking_forced_closure_fallback":
        escalate = confidence
        use_thinking = confidence and not (row["thinking_forced_closure"] and direct_ok)
    else:
        fail("Unknown fixed diagnosis policy")
    correct = row["thinking_correct"] if use_thinking else row["direct_correct"]
    tokens = row["direct_tokens"] + (row["thinking_tokens"] if escalate else 0)
    return {"escalate": bool(escalate), "use_thinking": bool(use_thinking),
        "correct": correct, "tokens": tokens,
        "utility": correct - SPEC["lambda"] * tokens / 1000}


def summarize(rows, protocol):
    if len(rows) != 128 or len({(r["question_id"], r["draw"]) for r in rows}) != 128:
        fail("Diagnosis requires 128 unique pairs")
    idset = {r["question_id"] for r in rows}
    if len(idset) != 64 or any(sum(r["question_id"] == q for r in rows) != 2 for q in idset):
        fail("Diagnosis requires 64 repeated question groups")
    out = {"spec": SPEC, "questions": 64, "pairs": 128,
        "counts": {}, "policies": {}, "gold_free_parser_failures": [],
        "sampling_match_official_qwen3_1p7b_card": {}}
    config = protocol["arms"][SOLVER]["config"]
    expected = {"direct": {"temperature": .7, "top_p": .8, "top_k": 20},
                "thinking": {"temperature": .6, "top_p": .95, "top_k": 20}}
    out["sampling_match_official_qwen3_1p7b_card"] = {
        "recommended": expected, "frozen": {mode: config[mode] for mode in expected},
        "matches": all(config[mode] == expected[mode] for mode in expected),
        "backend_do_sample": True,
        "official_card_url": "https://huggingface.co/Qwen/Qwen3-1.7B"}
    categories = {"rescue": lambda r: r["direct_correct"] == 0 and r["thinking_correct"] == 1,
        "harm": lambda r: r["direct_correct"] == 1 and r["thinking_correct"] == 0,
        "both_wrong": lambda r: r["direct_correct"] == 0 and r["thinking_correct"] == 0,
        "both_correct": lambda r: r["direct_correct"] == 1 and r["thinking_correct"] == 1}
    for name, predicate in categories.items():
        group = Counter(r["question_id"] for r in rows if predicate(r))
        out["counts"][name] = {"cells": sum(group.values()), "distinct_questions": len(group),
            "repeated_in_both_draws": sum(value == 2 for value in group.values()),
            "reasoning_cap_cells": sum(predicate(r) and r["thinking_reasoning_tokens"] == 2048 for r in rows)}
    for mode in ("direct", "thinking"):
        out["counts"][mode] = {"correct": sum(r[mode + "_correct"] for r in rows),
            "parser_status": dict(Counter(r[mode + "_parser_status"] for r in rows)),
            "termination": dict(Counter(r[mode + "_termination"] for r in rows)),
            "answer_truncated": sum(r[mode + "_answer_truncated"] for r in rows),
            "forced_closure": sum(r[mode + "_forced_closure"] for r in rows),
            "answer_at_512": sum(r[mode + "_answer_tokens"] == 512 for r in rows),
            "mean_generated_tokens": sum(r[mode + "_tokens"] for r in rows) / 128}
    out["counts"]["thinking"]["reasoning_at_2048"] = sum(r["thinking_reasoning_tokens"] == 2048 for r in rows)
    out["counts"]["finite_direct_post_and_raw_confidence"] = sum(
        math.isfinite(r["confidence"]) and math.isfinite(r["raw_confidence"]) for r in rows)
    for r in rows:
        for mode in ("direct", "thinking"):
            status = r[mode + "_parser_status"]
            if status != "ok":
                out["gold_free_parser_failures"].append({"question_id": r["question_id"],
                    "draw": r["draw"], "mode": mode, "parser_status": status,
                    "termination": r[mode + "_termination"],
                    "final_answer_sha256": r[mode + "_final_sha256"],
                    "final_answer_chars": r[mode + "_final_chars"],
                    "contains_box_marker": r[mode + "_final_has_box"]})
    for name in SPEC["policies"]:
        values = [policy_value(r, name) for r in rows]
        chosen = [r for r, value in zip(rows, values) if value["escalate"]]
        post = [r for r, value in zip(rows, values) if value["escalate"] and not value["use_thinking"]]
        out["policies"][name] = {"accuracy": sum(v["correct"] for v in values) / 128,
            "generated_tokens_per_pair": sum(v["tokens"] for v in values) / 128,
            "utility": sum(v["utility"] for v in values) / 128,
            "escalations": len(chosen),
            "rescues_escalated": sum(r["direct_correct"] == 0 and r["thinking_correct"] == 1 for r in chosen),
            "harms_escalated": sum(r["direct_correct"] == 1 and r["thinking_correct"] == 0 for r in chosen),
            "same_outcome_escalations": sum(r["direct_correct"] == r["thinking_correct"] for r in chosen),
            "post_thinking_fallbacks": len(post),
            "harms_recovered_by_fallback": sum(r["direct_correct"] == 1 and r["thinking_correct"] == 0 for r in post),
            "rescues_lost_by_fallback": sum(r["direct_correct"] == 0 and r["thinking_correct"] == 1 for r in post)}
    rejected = [r for r in rows if r["thinking_parser_status"] != "ok"]
    selected_rejected = [r for r in rejected if r["confidence_action"]]
    out["fixed_action_parser_upper_bounds"] = {
        "thinking_rejected_cells": len(rejected),
        "confidence_selected_rejected_cells": len(selected_rejected),
        "always_think_minus_accept_current": out["policies"]["think_after_direct"]["utility"]
            - out["policies"]["accept"]["utility"],
        "always_think_minus_accept_if_all_rejected_thinking_correct":
            out["policies"]["think_after_direct"]["utility"]
            - out["policies"]["accept"]["utility"]
            + sum(1 - r["thinking_correct"] for r in rejected) / 128,
        "confidence_minus_accept_current": out["policies"]["frozen_confidence"]["utility"]
            - out["policies"]["accept"]["utility"],
        "confidence_minus_accept_if_selected_rejected_thinking_correct":
            out["policies"]["frozen_confidence"]["utility"]
            - out["policies"]["accept"]["utility"]
            + sum(1 - r["thinking_correct"] for r in selected_rejected) / 128,
        "interpretation": "extreme fixed-action bound only; cached v7 labels remain unchanged"}
    return out


def prepare():
    with run_lock(OUTPUT / "preparation"):
        if (OUTPUT / "plan.json").exists():
            fail("Diagnosis preparation already exists")
        child, protocol, records, report, score, scores = inputs()
        rows = cells(protocol, records, report, scores)
        files = inventory()
        plan = {"spec": SPEC, "source_file_sha256": sources(),
            "environment": original.stable_environment(),
            "study_inventory": files, "study_inventory_sha256": digest(files),
            "parent_protocol_sha256": digest(protocol), "completion_plan_sha256": digest(child),
            "records_sha256": digest(records), "cached_scores_sha256": digest(score),
            "completion_report_sha256": digest(report), "rows_sha256": digest(rows),
            "prepared_at": time.time(), "old_protocol_budget_passed": False}
        original.write_once(OUTPUT / "rows.json", rows)
        original.write_once(OUTPUT / "plan.json", plan)
        return {"plan_sha256": digest(plan), "rows": len(rows), "study_files": len(files)}


def checked():
    plan, rows = verified(OUTPUT / "plan.json"), verified(OUTPUT / "rows.json")
    if (plan["spec"] != SPEC or plan["source_file_sha256"] != sources()
            or plan["environment"] != original.stable_environment()
            or plan["study_inventory_sha256"] != digest(plan["study_inventory"])
            or plan["rows_sha256"] != digest(rows)):
        fail("Frozen diagnosis plan or rows changed")
    for name, sha in plan["study_inventory"].items():
        if file_hash(STUDY / name) != sha:
            fail(f"Frozen study file changed: {name}")
    if set(inventory()) != set(plan["study_inventory"]):
        fail("Frozen study inventory changed")
    child, protocol, records, report, score, scores = inputs()
    if (digest(protocol) != plan["parent_protocol_sha256"]
            or digest(child) != plan["completion_plan_sha256"]
            or digest(records) != plan["records_sha256"]
            or digest(score) != plan["cached_scores_sha256"]
            or digest(report) != plan["completion_report_sha256"]
            or rows != cells(protocol, records, report, scores)):
        fail("Frozen diagnosis inputs changed")
    return plan, rows, protocol


def execute():
    with run_lock(OUTPUT / "execution"):
        plan, rows, protocol = checked()
        report_path = OUTPUT / "report.json"
        if report_path.exists():
            report = verified(report_path)
            if report["plan_sha256"] != digest(plan) or report["rows_sha256"] != digest(rows):
                fail("Cached diagnosis report changed")
            return {"cached": True, "report_sha256": digest(report)}
        if (OUTPUT / "execute-started.json").exists():
            fail("Diagnosis execute already attempted; no retry")
        original.write_once(OUTPUT / "execute-started.json", {"plan_sha256": digest(plan),
            "started_at": time.time(), "one_attempt": True})
        summary = summarize(rows, protocol)
        again, checked_rows, _ = checked()
        if digest(again) != digest(plan) or digest(checked_rows) != digest(rows):
            fail("Study changed during descriptive audit")
        report = {"plan_sha256": digest(plan), "rows_sha256": digest(rows),
            "summary": summary, "study_preserved": True,
            "no_model_fit_generation_scoring_or_reference_access": True,
            "old_protocol_budget_passed": False}
        original.write_once(report_path, report)
        return {"cached": False, "report_sha256": digest(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "execute"))
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "execute":
        print(execute())
    else:
        plan, rows, _ = checked()
        print({"plan_sha256": digest(plan), "rows": len(rows)})


if __name__ == "__main__":
    main()
