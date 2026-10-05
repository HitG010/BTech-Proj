"""Frozen, bounded cached-data pilot for the Qwen3-0.6B opportunity regime.

No model generation, reference access, parser scoring, embedding, or allocation.
Preparation freezes cached inputs/features before the one-time 20-fit execute.
"""

import argparse
import math
import time
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from reasoning_budget import scoring_v7
from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, run_lock, verified
from scripts import opportunity_panel_collect as original
from scripts import opportunity_panel_completion as completion

ROOT = Path(__file__).resolve().parents[1]
STUDY = original.STUDY
OUTPUT = original.BASE / "qwen06-router-pilot-v1"
SOLVER = "qwen3-0.6b"
SOURCE_FILES = ("scripts/qwen06_router_pilot.py", "tests/test_qwen06_router_pilot.py",
                "docs/qwen06-router-pilot-protocol.md")
SPEC = {"version": "qwen06-router-pilot-v1", "scope": "exploratory/cached-development",
    "solver": SOLVER, "questions": 64, "draws": 2, "folds": 5,
    "directions": [[0, 1], [1, 0]], "lambda": 0.05,
    "features": ["postwarper_confidence", "log1p_direct_answer_tokens", "v7_parser_reject"],
    "matched_features": ["postwarper_confidence"], "alpha": 10.0,
    "decision": "predicted_incremental_utility_strictly_greater_than_zero",
    "fit_limit": 20, "bootstrap_seed": 20261012, "bootstrap_draws": 2000,
    "interval": [0.05, 0.95], "threads": 1,
    "primary_screen": {"mean_delta_vs_frozen_confidence_at_least": 0.01,
        "both_direction_points_positive": True,
        "mean_delta_vs_matched_confidence_ridge_at_least": 0.0,
        "mean_delta_vs_confidence_or_reject_at_least": 0.0},
    "no_fresh_data_or_deployment_claim": True}
POLICIES = ("accept", "think", "confidence", "confidence_or_reject",
            "matched_confidence_ridge", "full_three_feature_ridge")


def fail(message):
    raise ValueError(message)


def sources():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def study_inventory():
    original.safe_paths()
    return {str(path.relative_to(STUDY)): file_hash(path)
            for path in sorted(STUDY.rglob("*")) if path.is_file()}


def direct_features(record, score):
    """Inference-time fields only; correctness and thinking never enter here."""
    if record["job"]["mode"] != "direct" or score["mode"] != "direct":
        fail("Direct-only feature boundary changed")
    result = record["result"]
    confidence, length = result["mean_generated_logprob"], result["answer_tokens"]
    _, parser_status = scoring_v7.extract_record(record)
    if (type(confidence) not in (float, int) or not math.isfinite(confidence)
            or type(length) is not int or length < 0
            or not isinstance(parser_status, str)
            or score["parser_status"] != parser_status):
        fail("Invalid direct feature")
    return [float(confidence), math.log1p(length), float(parser_status != "ok")]


def _threshold(value):
    if value == "always":
        return math.inf
    if value == "never":
        return -math.inf
    if type(value) not in (int, float) or not math.isfinite(value):
        fail("Frozen confidence threshold invalid")
    return float(value)


def closed_inputs():
    """Read the closed endpoint and cached score/report; never call a scorer."""
    child_plan, protocol = completion.read_plan()
    terminal = verified(STUDY / "completion-v1/supervisor-finish.json")
    status = verified(STUDY / "completion-v1/status.json")
    if (not (STUDY / "completion-v1/collection-end.json").exists()
            or terminal["state"] != "complete" or status["state"] != "complete"
            or verified(STUDY / "completion-v1/invocation-process.json")["exit_code"] != 0
            or verified(STUDY / "completion-v1/finalize-process.json")["exit_code"] != 0):
        fail("Closed completion endpoint required")
    grouped = completion.combined_records(child_plan, protocol)
    report = verified(STUDY / "completion-v1/report.json")
    scores = verified(STUDY / "completion-v1/scores.numeric-v7.json")
    if (terminal["report_sha256"] != digest(report)
            or status["report_sha256"] != digest(report)
            or report["plan_sha256"] != digest(child_plan)
            or report["parent_protocol_sha256"] != digest(protocol)
            or report["scores_sha256"] != digest(scores)
            or report["old_protocol_budget_passed"] is not False
            or scores["protocol_sha256"] != digest(child_plan)
            or scores["records_sha256"] != digest(grouped)
            or scores["selected_sha256"] != digest(protocol["selected"])
            or scores["scoring_implementation_sha256"] != protocol["scoring_implementation_sha256"]
            or scores["scoring_version"] != "numeric-v7"
            or len(scores["scores"]) != 512):
        fail("Cached endpoint identity changed")
    index = {}
    for score in scores["scores"]:
        key = score["solver"], score["job_id"]
        if (key in index or type(score["correct"]) is not bool
                or score["parser_status"] not in ("ok", "invalid_number", "incomplete", "conflicting")
                or score["mode"] not in ("direct", "thinking")):
            fail("Cached score coverage or schema changed")
        index[key] = score
    expected = {(solver, r["job"]["id"]) for solver in original.SOLVERS for r in grouped[solver]}
    if set(index) != expected:
        fail("Cached score IDs changed")
    return child_plan, protocol, grouped, report, index


def build_rows(protocol, grouped, report, scores):
    began = time.monotonic()
    ids = report["statistics"]["question_ids"]
    folds = protocol["folds"]
    if (len(ids) != 64 or len(set(ids)) != 64 or set(ids) != set(folds)
            or report["statistics"]["folds"] != folds
            or sorted(sum(folds[q] == f for q in ids) for f in range(5)) != [12, 13, 13, 13, 13]):
        fail("Frozen question folds changed")
    pairs = {}
    for record in grouped[SOLVER]:
        job, result = record["job"], record["result"]
        score = scores[SOLVER, job["id"]]
        if (score["question_id"] != job["question_id"] or score["mode"] != job["mode"]
                or job["question_id"] not in folds or job["sample"] not in (0, 1)):
            fail("Cached score/job cell changed")
        key = job["question_id"], job["sample"]
        cell = pairs.setdefault(key, {"question_id": key[0], "draw": key[1]})
        mode = job["mode"]
        if mode + "_correct" in cell:
            fail("Duplicate paired mode")
        cell[mode + "_correct"] = int(score["correct"])
        cell[mode + "_tokens"] = sum(result[name] for name in
            ("reasoning_tokens", "answer_tokens", "inserted_tokens"))
        if mode == "direct":
            cell["features"] = direct_features(record, score)
            cell["parser_status"] = score["parser_status"]
    if set(pairs) != {(q, draw) for q in ids for draw in (0, 1)}:
        fail("Paired 0.6B endpoint coverage changed")
    rows = []
    for draw in (0, 1):
        frozen = report["statistics"]["solvers"][SOLVER]["draws"][str(draw)]
        actions, thresholds = frozen["confidence_actions"], frozen["confidence_thresholds"]
        if len(actions) != 64 or len(thresholds) != 64:
            fail("Frozen confidence action coverage changed")
        for i, q in enumerate(ids):
            cell = pairs[q, draw]
            if set(cell) != {"question_id", "draw", "direct_correct", "thinking_correct",
                             "direct_tokens", "thinking_tokens", "features", "parser_status"}:
                fail("Paired 0.6B cell incomplete")
            action = cell["features"][0] < _threshold(thresholds[i])
            if type(actions[i]) is not bool or action != actions[i]:
                fail("Frozen confidence action disagrees with threshold")
            row = cell | {"fold": folds[q], "frozen_confidence_action": action,
                          "frozen_confidence_threshold": thresholds[i]}
            rows.append(row)
        utility = sum(policy_utility(row, row["frozen_confidence_action"])
                      for row in rows if row["draw"] == draw) / 64
        if abs(utility - frozen["policies"]["confidence"]["utility"]["mean"]) > 1e-10:
            fail("Frozen confidence utility did not reproduce")
    return rows, time.monotonic() - began


def policy_utility(row, escalate):
    correct = row["thinking_correct"] if escalate else row["direct_correct"]
    tokens = row["direct_tokens"] + (row["thinking_tokens"] if escalate else 0)
    return correct - SPEC["lambda"] * tokens / 1000


def target(row):
    return row["thinking_correct"] - row["direct_correct"] - SPEC["lambda"] * row["thinking_tokens"] / 1000


def prepare():
    with run_lock(OUTPUT / "preparation"):
        if (OUTPUT / "plan.json").exists() or (OUTPUT / "rows.json").exists():
            fail("Pilot preparation already exists")
        child_plan, protocol, grouped, report, scores = closed_inputs()
        rows, feature_seconds = build_rows(protocol, grouped, report, scores)
        inventory = study_inventory()
        payload = {"rows": rows, "question_ids": report["statistics"]["question_ids"],
                   "folds": protocol["folds"], "feature_extraction_seconds": feature_seconds}
        plan = {"spec": SPEC, "study_inventory": inventory,
            "study_inventory_sha256": digest(inventory), "source_file_sha256": sources(),
            "environment": original.stable_environment(),
            "dependencies": {"numpy": np.__version__, "scikit_learn": sklearn.__version__},
            "parent_protocol_sha256": digest(protocol), "completion_plan_sha256": digest(child_plan),
            "completion_report_sha256": digest(report), "cached_scores_sha256": report["scores_sha256"],
            "combined_records_sha256": digest(grouped), "rows_sha256": digest(payload),
            "prepared_at": time.time(), "no_generation_or_reference_access": True}
        original.write_once(OUTPUT / "rows.json", payload)
        original.write_once(OUTPUT / "plan.json", plan)
        return {"plan_sha256": digest(plan), "rows_sha256": digest(payload), "rows": len(rows)}


def checked_plan():
    plan, data = verified(OUTPUT / "plan.json"), verified(OUTPUT / "rows.json")
    if (plan["spec"] != SPEC or plan["source_file_sha256"] != sources()
            or plan["environment"] != original.stable_environment()
            or plan["dependencies"] != {"numpy": np.__version__, "scikit_learn": sklearn.__version__}
            or plan["study_inventory_sha256"] != digest(plan["study_inventory"])
            or plan["rows_sha256"] != digest(data)):
        fail("Frozen pilot plan or features changed")
    for relative, sha in plan["study_inventory"].items():
        if file_hash(STUDY / relative) != sha:
            fail(f"Closed study file changed: {relative}")
    if set(study_inventory()) != set(plan["study_inventory"]):
        fail("Closed study inventory changed")
    child_plan, protocol, grouped, report, scores = closed_inputs()
    if (digest(protocol) != plan["parent_protocol_sha256"]
            or digest(child_plan) != plan["completion_plan_sha256"]
            or digest(report) != plan["completion_report_sha256"]
            or report["scores_sha256"] != plan["cached_scores_sha256"]
            or digest(grouped) != plan["combined_records_sha256"]):
        fail("Closed input identity changed")
    # Rebuild the inference-only features and labels; elapsed feature time is
    # excluded because it is an observation rather than model input.
    rebuilt, _ = build_rows(protocol, grouped, report, scores)
    if (rebuilt != data["rows"] or data["question_ids"] != report["statistics"]["question_ids"]
            or data["folds"] != protocol["folds"]):
        fail("Frozen rows no longer reproduce")
    return plan, data


def fold_fit(rows, train_draw, eval_draw, fold):
    train = [r for r in rows if r["draw"] == train_draw and r["fold"] != fold]
    test = [r for r in rows if r["draw"] == eval_draw and r["fold"] == fold]
    train_ids, test_ids = {r["question_id"] for r in train}, {r["question_id"] for r in test}
    if (len(train) not in (51, 52) or len(test) not in (12, 13)
            or train_ids & test_ids or len(train_ids) != len(train) or len(test_ids) != len(test)
            or any(r["draw"] != train_draw for r in train)
            or any(r["draw"] != eval_draw for r in test)):
        fail("Question/draw training boundary changed")
    y = np.asarray([target(r) for r in train], dtype=float)
    detail = {"fold": fold, "train_draw": train_draw, "test_draw": eval_draw,
        "train_question_ids": sorted(train_ids), "test_question_ids": sorted(test_ids), "models": {}}
    detail["train_question_ids_in_fit_order"] = [r["question_id"] for r in train]
    detail["test_question_ids_in_prediction_order"] = [r["question_id"] for r in test]
    predictions = {}
    for family, columns in (("matched_confidence_ridge", [0]),
                            ("full_three_feature_ridge", [0, 1, 2])):
        x_train = np.asarray([[r["features"][j] for j in columns] for r in train])
        x_test = np.asarray([[r["features"][j] for j in columns] for r in test])
        scaler = StandardScaler().fit(x_train)
        model = Ridge(alpha=SPEC["alpha"], solver="svd").fit(scaler.transform(x_train), y)
        began = time.monotonic()
        predicted = model.predict(scaler.transform(x_test))
        predict_seconds = time.monotonic() - began
        predictions[family] = predicted > 0
        detail["models"][family] = {"columns": columns, "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(), "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_), "predictions": predicted.tolist(),
            "prediction_seconds": predict_seconds}
    actions = []
    for i, row in enumerate(test):
        decisions = {"accept": False, "think": True,
            "confidence": row["frozen_confidence_action"],
            "confidence_or_reject": row["frozen_confidence_action"] or bool(row["features"][2]),
            "matched_confidence_ridge": bool(predictions["matched_confidence_ridge"][i]),
            "full_three_feature_ridge": bool(predictions["full_three_feature_ridge"][i])}
        actions.append({"question_id": row["question_id"], "test_draw": eval_draw,
            "train_draw": train_draw, "fold": fold, "actions": decisions,
            "utility": {name: policy_utility(row, action) for name, action in decisions.items()},
            "correct": {name: row["thinking_correct"] if action else row["direct_correct"]
                        for name, action in decisions.items()},
            "tokens": {name: row["direct_tokens"] + (row["thinking_tokens"] if action else 0)
                       for name, action in decisions.items()},
            "rescue": int(row["thinking_correct"] == 1 and row["direct_correct"] == 0),
            "harm": int(row["thinking_correct"] == 0 and row["direct_correct"] == 1)})
    return actions, detail


def summarize(actions, ids):
    if len(actions) != 128 or len({(a["question_id"], a["test_draw"]) for a in actions}) != 128:
        fail("Pilot actions do not cover 64 questions in both directions")
    by_key = {(a["question_id"], a["test_draw"]): a for a in actions}
    if set(by_key) != {(q, d) for q in ids for d in (0, 1)}:
        fail("Pilot question/draw action coverage changed")
    rng = np.random.default_rng(SPEC["bootstrap_seed"])
    sample = rng.integers(0, 64, size=(SPEC["bootstrap_draws"], 64))
    result = {"policies": {}, "deltas_vs_confidence": {}, "directions": {},
              "bootstrap": {"seed": SPEC["bootstrap_seed"], "draws": SPEC["bootstrap_draws"],
                  "grouping": "same 64 question indices for both draws and every policy; fixed actions"}}
    qdata = {name: np.asarray([sum(by_key[q, d]["utility"][name] for d in (0, 1)) / 2
                               for q in ids], dtype=float) for name in POLICIES}
    for name in POLICIES:
        values = qdata[name]
        result["policies"][name] = {"utility": float(values.mean()),
            "utility_ci90": np.quantile(values[sample].mean(axis=1), SPEC["interval"]).tolist(),
            "accuracy": float(np.mean([a["correct"][name] for a in actions])),
            "tokens_per_question": float(np.mean([a["tokens"][name] for a in actions])),
            "escalations": int(sum(a["actions"][name] for a in actions)),
            "rescues_escalated": int(sum(a["actions"][name] and a["rescue"] for a in actions)),
            "harms_escalated": int(sum(a["actions"][name] and a["harm"] for a in actions))}
        delta = values - qdata["confidence"]
        result["deltas_vs_confidence"][name] = {"mean": float(delta.mean()),
            "ci90": np.quantile(delta[sample].mean(axis=1), SPEC["interval"]).tolist()}
    for draw in (0, 1):
        result["directions"][str(draw)] = {name: float(np.mean([
            by_key[q, draw]["utility"][name] - by_key[q, draw]["utility"]["confidence"]
            for q in ids])) for name in POLICIES}
    candidate = qdata["full_three_feature_ridge"]
    gate = {"mean_vs_frozen_confidence_at_least_0.01":
                float((candidate - qdata["confidence"]).mean()) >= 0.01,
            "both_direction_points_positive": all(
                result["directions"][str(d)]["full_three_feature_ridge"] > 0 for d in (0, 1)),
            "mean_vs_matched_confidence_ridge_nonnegative":
                float((candidate - qdata["matched_confidence_ridge"]).mean()) >= 0,
            "mean_vs_confidence_or_reject_nonnegative":
                float((candidate - qdata["confidence_or_reject"]).mean()) >= 0}
    result["further_study_gate"] = gate | {"all_pass": all(gate.values()),
        "interpretation": "exploratory only; no fresh-question superiority or novelty claim"}
    return result


def analyze(rows, ids):
    actions, fits = [], []
    began = time.monotonic()
    with threadpool_limits(limits=SPEC["threads"]):
        for train_draw, eval_draw in SPEC["directions"]:
            for fold in range(5):
                cells, detail = fold_fit(rows, train_draw, eval_draw, fold)
                actions.extend(cells)
                fits.append(detail)
    if len(fits) * 2 != SPEC["fit_limit"]:
        fail("Pilot Ridge fit ceiling changed")
    result = summarize(actions, ids)
    return {"spec": SPEC, "fit_count": len(fits) * 2, "fits": fits,
        "actions": actions, "summary": result,
        "cpu_fit_and_analysis_seconds": time.monotonic() - began,
        "timing_scope": "CPU preprocessing/fit/predict only; not co-resident router/solver latency"}


def execute():
    with run_lock(OUTPUT / "execution"):
        plan, data = checked_plan()
        report_path = OUTPUT / "report.json"
        if report_path.exists():
            report = verified(report_path)
            if (report["plan_sha256"] != digest(plan) or report["rows_sha256"] != digest(data)
                    or report["spec"] != SPEC or report["fit_count"] != SPEC["fit_limit"]
                    or len(report["fits"]) != 10 or len(report["actions"]) != 128
                    or report["parent_study_preserved"] is not True):
                fail("Cached pilot report identity changed")
            return {"cached": True, "report_sha256": digest(report)}
        if (OUTPUT / "execute-started.json").exists():
            fail("Pilot execution was already attempted; no fit retry")
        original.write_once(OUTPUT / "execute-started.json", {"plan_sha256": digest(plan),
            "rows_sha256": digest(data), "started_at": time.time(), "one_attempt": True})
        result = analyze(data["rows"], data["question_ids"])
        checked_after, data_after = checked_plan()
        if digest(checked_after) != digest(plan) or digest(data_after) != digest(data):
            fail("Pilot inputs changed during execution")
        report = result | {"plan_sha256": digest(plan), "rows_sha256": digest(data),
            "feature_extraction_seconds": data["feature_extraction_seconds"],
            "parent_study_preserved": True, "no_reference_or_generation_access": True}
        original.write_once(report_path, report)
        return {"cached": False, "report_sha256": digest(report), "fit_count": report["fit_count"],
                "gate": report["summary"]["further_study_gate"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "verify"))
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "execute":
        print(execute())
    else:
        plan, data = checked_plan()
        print({"plan_sha256": digest(plan), "rows_sha256": digest(data), "rows": len(data["rows"])})


if __name__ == "__main__":
    main()
