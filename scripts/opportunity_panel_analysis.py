"""Fixed, question-grouped opportunity analysis and gated v7 score sidecar.

The analysis accepts cached paired outcomes only. The sidecar's caller owns the
frozen collection protocol, locks, and attempt/session verification.
"""

import math
from pathlib import Path

import numpy as np

from reasoning_budget import scoring_v7
from reasoning_budget.storage import atomic_json, digest, envelope, verified
from scripts.opportunity_panel_plan import confidence_crossfit

SOLVERS = ("qwen3-1.7b", "qwen3-0.6b")
MODES = ("direct", "thinking")
SPEC = {"version": "opportunity-panel-analysis-v1", "lambda": 0.05,
        "bootstrap_seed": 20261009, "bootstrap_draws": 2000,
        "interval": [0.05, 0.95], "positive_questions_minimum": 10,
        "confidence_gain_minimum": 0.01,
        "scope": "diagnostic; fixed actions, 64 independent question groups; no superiority confirmation"}
ROW_KEYS = {"question_id", "solver", "draw", "direct_correct", "thinking_correct",
            "direct_tokens", "thinking_tokens", "confidence", "raw_confidence"}
SCORE_KEYS = {"solver", "job_id", "question_id", "mode", "extracted_answer", "correct",
              "parser_status", "scoring_version"}


def _ids(question_ids, folds):
    ids = list(question_ids)
    if len(ids) != 64 or len(set(ids)) != 64 or set(folds) != set(ids):
        raise ValueError("Exactly 64 unique prepared question groups required")
    if any(type(folds[q]) is not int or folds[q] not in range(5) for q in ids):
        raise ValueError("Invalid frozen question folds")
    if sorted(sum(folds[q] == f for q in ids) for f in range(5)) != [12, 13, 13, 13, 13]:
        raise ValueError("Frozen question-fold balance changed")
    return ids


def validate_pairs(rows, folds, question_ids):
    ids = _ids(question_ids, folds)
    expected = {(q, solver, draw) for q in ids for solver in SOLVERS for draw in (0, 1)}
    if len(rows) != 256:
        raise ValueError("Exactly 256 paired outcomes required")
    seen = set()
    for row in rows:
        if set(row) != ROW_KEYS:
            raise ValueError("Paired outcome schema changed")
        key = (row["question_id"], row["solver"], row["draw"])
        if key in seen or type(row["draw"]) is not int:
            raise ValueError("Duplicate or invalid paired cell")
        seen.add(key)
        for name in ("direct_correct", "thinking_correct"):
            if type(row[name]) is not int or row[name] not in (0, 1):
                raise ValueError("Correctness must be binary integers")
        for name in ("direct_tokens", "thinking_tokens"):
            if type(row[name]) is not int or row[name] < 0:
                raise ValueError("Charged costs must be nonnegative integers")
        for key in ("confidence", "raw_confidence"):
            if type(row[key]) not in (int, float) or not math.isfinite(row[key]):
                raise ValueError("Finite post-warper and raw confidence required")
    if seen != expected:
        raise ValueError("Paired endpoint cell coverage changed")
    return ids


def _threshold(value):
    if value == math.inf:
        return "always"
    if value == -math.inf:
        return "never"
    return float(value)


def _ci(values, samples, spec):
    array = np.asarray(values, dtype=float)
    means = array[samples].mean(axis=1)
    return [float(x) for x in np.quantile(means, spec["interval"])]


def _metric(values, samples, spec):
    array = np.asarray(values, dtype=float)
    return {"mean": float(array.mean()), "ci90": _ci(array, samples, spec)}


def _policy(row, escalate, lam):
    correct = row["thinking_correct"] if escalate else row["direct_correct"]
    tokens = row["direct_tokens"] + (row["thinking_tokens"] if escalate else 0)
    return {"correct": correct, "tokens": tokens,
            "utility": correct - lam * tokens / 1000, "escalate": int(escalate)}


def analyze_pairs(rows, folds, *, question_ids, spec=SPEC):
    """Fixed descriptive analysis; one bootstrap resampling shared by all cells."""
    if spec != SPEC:
        raise ValueError("Analysis settings differ from frozen specification")
    ids = validate_pairs(rows, folds, question_ids)
    indexed = {(r["question_id"], r["solver"], r["draw"]): r for r in rows}
    rng = np.random.default_rng(spec["bootstrap_seed"])
    samples = rng.integers(0, 64, size=(spec["bootstrap_draws"], 64))
    result = {"spec": spec, "question_ids": ids, "folds": folds,
              "bootstrap_grouping": "same 64 sampled question indices across draws and solvers",
              "solvers": {}, "between_solver": {}, "fixed_threshold_fits": 40}
    paired = {}
    for solver in SOLVERS:
        actions = confidence_crossfit(rows, folds, solver)
        raw_rows = [dict(row, confidence=row["raw_confidence"]) for row in rows]
        raw_actions = confidence_crossfit(raw_rows, folds, solver)
        by_draw = {}
        per_question = {}
        for draw in (0, 1):
            train_draw = 1 - draw
            data = [indexed[q, solver, draw] for q in ids]
            confidence = [actions[q, train_draw, draw] for q in ids]
            raw_confidence = [raw_actions[q, train_draw, draw] for q in ids]
            policies = {name: [_policy(row, flag, spec["lambda"]) for row, flag in
                zip(data, flags)] for name, flags in {
                    "accept": [False] * 64, "escalate": [True] * 64,
                    "confidence": [a["escalate"] for a in confidence],
                    "raw_confidence": [a["escalate"] for a in raw_confidence]}.items()}
            descriptive = {
                "direct_accuracy": [r["direct_correct"] for r in data],
                "thinking_accuracy": [r["thinking_correct"] for r in data],
                "rescue": [int(r["thinking_correct"] == 1 and r["direct_correct"] == 0) for r in data],
                "harm": [int(r["thinking_correct"] == 0 and r["direct_correct"] == 1) for r in data],
                "positive_gain": [int(r["thinking_correct"] - r["direct_correct"]
                    - spec["lambda"] * r["thinking_tokens"] / 1000 > 0) for r in data],
                "direct_tokens": [r["direct_tokens"] for r in data],
                "thinking_tokens": [r["thinking_tokens"] for r in data],
            }
            delta = [c["utility"] - a["utility"] for c, a in
                     zip(policies["confidence"], policies["accept"])]
            raw_delta = [c["utility"] - a["utility"] for c, a in
                         zip(policies["raw_confidence"], policies["accept"])]
            by_draw[str(draw)] = {
                "descriptive": {k: _metric(v, samples, spec) for k, v in descriptive.items()},
                "counts": {k: int(sum(descriptive[k])) for k in ("rescue", "harm", "positive_gain")},
                "policies": {name: {field: _metric([r[field] for r in values], samples, spec)
                                     for field in ("correct", "tokens", "utility", "escalate")}
                             for name, values in policies.items()},
                "confidence_minus_accept": _metric(delta, samples, spec),
                "confidence_actions": [bool(a["escalate"]) for a in confidence],
                "confidence_thresholds": [_threshold(a["threshold"]) for a in confidence],
                "raw_confidence_minus_accept": _metric(raw_delta, samples, spec),
                "raw_confidence_actions": [bool(a["escalate"]) for a in raw_confidence],
                "raw_confidence_thresholds": [_threshold(a["threshold"]) for a in raw_confidence],
            }
            per_question[draw] = {"descriptive": descriptive, "policies": policies,
                                  "confidence_minus_accept": delta,
                                  "raw_confidence_minus_accept": raw_delta}
        positive = [int(any(per_question[d]["descriptive"]["positive_gain"][i]
                            for d in (0, 1))) for i in range(64)]
        averaged = [sum(per_question[d]["confidence_minus_accept"][i]
                        for d in (0, 1)) / 2 for i in range(64)]
        raw_averaged = [sum(per_question[d]["raw_confidence_minus_accept"][i]
                            for d in (0, 1)) / 2 for i in range(64)]
        screen = {"positive_gain_questions": int(sum(positive)),
                  "availability_pass": sum(positive) >= spec["positive_questions_minimum"],
                  "confidence_minus_accept_average": _metric(averaged, samples, spec),
                  "confidence_gain_pass": (sum(averaged) / 64 >= spec["confidence_gain_minimum"]
                      and all(by_draw[str(d)]["confidence_minus_accept"]["mean"] > 0
                              for d in (0, 1))),
                  "interpretation": "further-study screen only; no policy superiority claim"}
        raw_screen = {"raw_confidence_minus_accept_average": _metric(raw_averaged, samples, spec),
                      "raw_confidence_gain_pass": (sum(raw_averaged) / 64 >= spec["confidence_gain_minimum"]
                          and all(by_draw[str(d)]["raw_confidence_minus_accept"]["mean"] > 0
                                  for d in (0, 1))),
                      "interpretation": "predeclared secondary only; does not select or replace primary confidence"}
        result["solvers"][solver] = {"draws": by_draw, "screen": screen,
                                      "raw_confidence_secondary_screen": raw_screen}
        paired[solver] = per_question
    for metric in ("rescue", "harm", "positive_gain"):
        diff = [sum(paired[SOLVERS[0]][d]["descriptive"][metric][i]
                    - paired[SOLVERS[1]][d]["descriptive"][metric][i] for d in (0, 1)) / 2
                for i in range(64)]
        result["between_solver"][metric + "_rate_difference"] = _metric(diff, samples, spec)
    return result


def _score_cells(records_by_solver, selected):
    ids = [r["child_question"]["id"] for r in selected]
    if len(ids) != 64 or len(set(ids)) != 64 or set(records_by_solver) != set(SOLVERS):
        raise ValueError("The exact frozen two-solver child is required")
    expected = {(q, mode, draw) for q in ids for mode in MODES for draw in (0, 1)}
    all_jobs = set()
    for solver in SOLVERS:
        records = records_by_solver[solver]
        if len(records) != 256:
            raise ValueError("Both full 256-response arms are required before reference access")
        cells = set()
        for row in records:
            job = row["job"]
            cell = (job["question_id"], job["mode"], job["sample"])
            if (row["status"] != "completed" or row["result"] is None or cell in cells
                    or job["id"] in all_jobs or type(job["sample"]) is not int):
                raise ValueError("Incomplete, duplicated, or mixed endpoint")
            cells.add(cell)
            all_jobs.add(job["id"])
        if cells != expected:
            raise ValueError("Solver endpoint cell coverage changed")
    return ids


def _validate_scores(scores, records_by_solver):
    if not isinstance(scores, list) or len(scores) != 512:
        raise ValueError("Exactly 512 cached scores required")
    expected = {(solver, row["job"]["id"]): row
                for solver in SOLVERS for row in records_by_solver[solver]}
    seen = set()
    for score in scores:
        if not isinstance(score, dict) or set(score) != SCORE_KEYS:
            raise ValueError("Cached score schema changed")
        key = (score["solver"], score["job_id"])
        if key not in expected or key in seen:
            raise ValueError("Cached score job identity changed")
        seen.add(key)
        record = expected[key]
        job = record["job"]
        extracted, parser_status = scoring_v7.extract_record(record)
        if (score["question_id"] != job["question_id"] or score["mode"] != job["mode"]
                or score["scoring_version"] != scoring_v7.SCORING_VERSION
                or type(score["correct"]) is not bool
                or score["parser_status"] != parser_status
                or score["extracted_answer"] != extracted
                or parser_status != "ok" and score["correct"]):
            raise ValueError("Cached score semantics changed")
    if seen != set(expected):
        raise ValueError("Cached score coverage changed")


def score_complete_endpoint(records_by_solver, selected, gold_loader, *, protocol_sha256, output):
    """Score only complete endpoints; existing valid cache needs no gold access.

    The collector must hold study/run locks and verify frozen job/attempt identities
    before calling this function. It also owns the one-time score-start marker.
    """
    ids = _score_cells(records_by_solver, selected)
    record_digest = digest({solver: records_by_solver[solver] for solver in SOLVERS})
    scorer_digest = scoring_v7.implementation_digest()
    header = {"protocol_sha256": protocol_sha256, "selected_sha256": digest(selected),
              "records_sha256": record_digest, "scoring_version": scoring_v7.SCORING_VERSION,
              "scoring_implementation_sha256": scorer_digest}
    output = Path(output)
    if output.exists():
        cached = verified(output)
        if (any(cached.get(k) != v for k, v in header.items())
                or "gold_sha256" not in cached):
            raise ValueError("Frozen score cache identity changed")
        _validate_scores(cached.get("scores"), records_by_solver)
        return cached
    gold = gold_loader(selected)
    if set(gold) != set(ids) or len(gold) != 64:
        raise ValueError("Selected-only reference set changed")
    scores = []
    for solver in SOLVERS:
        for row in records_by_solver[solver]:
            scores.append({"solver": solver} | scoring_v7.score_record(
                row, gold[row["job"]["question_id"]]))
    _validate_scores(scores, records_by_solver)
    artifact = header | {"gold_sha256": digest(gold), "scores": scores}
    if output.exists():
        raise ValueError("Score cache appeared during endpoint scoring")
    atomic_json(output, envelope(artifact))
    return artifact


def paired_rows(records_by_solver, score_artifact):
    """Construct fixed 256-cell analysis input from complete cached v7 scores."""
    _validate_scores(score_artifact["scores"], records_by_solver)
    indexed = {(s["solver"], s["job_id"]): s for s in score_artifact["scores"]}
    if len(indexed) != 512:
        raise ValueError("Exactly 512 unique cached scores required")
    pairs = {}
    for solver in SOLVERS:
        for row in records_by_solver[solver]:
            job, result = row["job"], row["result"]
            score = indexed[solver, job["id"]]
            key = (job["question_id"], solver, job["sample"])
            pair = pairs.setdefault(key, {"question_id": key[0], "solver": solver,
                                          "draw": key[2]})
            mode = job["mode"]
            pair[mode + "_correct"] = int(score["correct"])
            pair[mode + "_tokens"] = sum(result[k] for k in
                ("reasoning_tokens", "answer_tokens", "inserted_tokens"))
            if mode == "direct":
                pair["confidence"] = result["mean_generated_logprob"]
                pair["raw_confidence"] = result["mean_generated_logprob_raw"]
    if len(pairs) != 256 or any(set(r) != ROW_KEYS for r in pairs.values()):
        raise ValueError("Paired outcomes have incomplete modes or scores")
    return [pairs[key] for key in sorted(pairs)]
