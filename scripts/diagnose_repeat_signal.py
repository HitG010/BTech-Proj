"""Post-hoc CPU-only diagnostics on the completed frozen repeat panel.

No model is fit, no reference answers are opened, and no primary report or gate
is changed. The output is a separately versioned development artifact.
"""

import argparse
import math
from pathlib import Path

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.research_repeat import ROOT, STUDY, checked_run, read_protocol
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified

SEED = 20261003
BOOTSTRAPS = 2000
INTERVAL = [0.05, 0.95]


def endpoint(study):
    """Never open scores or the primary report before the exact endpoint."""
    protocol = read_protocol(study)
    manifest, rows = checked_run(study, protocol)
    if (manifest is None or len(protocol["snapshot"]["jobs"]) != 800 or len(rows) != 800
            or any(row["status"] != "completed" for row in rows)):
        raise ValueError("Post-hoc diagnosis locked until all 800 responses complete")
    return protocol, manifest, rows


def close(actual, expected):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError(f"Diagnostic arithmetic differs from primary report: {actual}, {expected}")


def ci90(question_values):
    values = np.asarray(question_values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Question bootstrap requires finite grouped values")
    rng = np.random.default_rng(SEED)
    samples = rng.integers(0, len(values), (BOOTSTRAPS, len(values)))
    return [float(x) for x in np.quantile(values[samples].mean(1), INTERVAL)]


def signed_between(gains):
    values = np.asarray(gains, dtype=float)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 2:
        raise ValueError("Need repeated gains on at least two questions")
    within = float(values.var(axis=1, ddof=1).mean())
    means = values.mean(axis=1)
    variance_of_means = float(means.var(ddof=1))
    return {"within_mean_sample_variance": within,
            "question_mean_sample_variance": variance_of_means,
            "signed_between_estimate": variance_of_means - within / values.shape[1]}


def between_ci90(gains):
    values = np.asarray(gains, dtype=float)
    rng = np.random.default_rng(SEED)
    samples = rng.integers(0, len(values), (BOOTSTRAPS, len(values)))
    estimates = [signed_between(values[indices])["signed_between_estimate"] for indices in samples]
    return [float(x) for x in np.quantile(estimates, INTERVAL)]


def outcomes(direct, thinking, preference):
    """Return aggregate, hindsight oracle, and same-question half transfer."""
    d, t = np.asarray(direct, dtype=float), np.asarray(thinking, dtype=float)
    if d.shape != t.shape or d.ndim != 3 or d.shape[1:] != (8, 3):
        raise ValueError("Expected paired [question, eight draws, correctness/tokens/seconds]")
    accept = d[:, :, 0] - preference * d[:, :, 1] / 1000
    escalate = t[:, :, 0] - preference * (d[:, :, 1] + t[:, :, 1]) / 1000
    gain = escalate - accept
    rescue = (d[:, :, 0] == 0) & (t[:, :, 0] == 1)
    harm = (d[:, :, 0] == 1) & (t[:, :, 0] == 0)
    both_correct = (d[:, :, 0] == 1) & (t[:, :, 0] == 1)
    both_wrong = (d[:, :, 0] == 0) & (t[:, :, 0] == 0)
    oracle = np.maximum(accept, escalate)
    half = {}
    for name, train, evaluate in (("A_to_B", range(4), range(4, 8)),
                                  ("B_to_A", range(4, 8), range(4))):
        train_draws = list(train)
        acquisition_tokens = (d[:, train_draws, 1] + t[:, train_draws, 1]).sum(1)
        acquisition_seconds = (d[:, train_draws, 2] + t[:, train_draws, 2]).sum(1)
        decision = gain[:, list(train)].mean(1) > 0
        chosen = np.where(decision[:, None], escalate[:, list(evaluate)], accept[:, list(evaluate)])
        per_q = (chosen - accept[:, list(evaluate)]).mean(1)
        half[name] = {
            "same_question_train_half_positive": int(decision.sum()),
            "selection_acquisition": {
                "paired_draws_per_question": len(train_draws),
                "responses_per_question": 2 * len(train_draws),
                "paired_draws_total": int(len(d) * len(train_draws)),
                "responses_total": int(2 * len(d) * len(train_draws)),
                "tokens_per_question": [float(x) for x in acquisition_tokens],
                "seconds_per_question": [float(x) for x in acquisition_seconds],
                "tokens_total": float(acquisition_tokens.sum()),
                "seconds_total": float(acquisition_seconds.sum()),
            },
            "evaluation_accuracy": float(np.where(decision[:, None],
                t[:, list(evaluate), 0], d[:, list(evaluate), 0]).mean()),
            "evaluation_utility": float(chosen.mean()),
            "gain_over_accept": float(per_q.mean()), "gain_ci90": ci90(per_q),
            "evaluation_utility_excludes_selection_acquisition": True,
            "not_net_acquisition_utility_or_deployed_policy": True,
            "same_question_only_not_unseen_question_generalization": True,
        }
    full_gain = gain.mean(1)
    oracle_gain = (oracle - accept).mean(1)
    return {
        "question_count": len(d), "pairs": int(d.shape[0] * 8),
        "direct": {"correct": int(d[:, :, 0].sum()), "tokens": float(d[:, :, 1].sum()),
                   "seconds": float(d[:, :, 2].sum())},
        "thinking": {"correct": int(t[:, :, 0].sum()), "tokens": float(t[:, :, 1].sum()),
                     "seconds": float(t[:, :, 2].sum())},
        "paired_states": {"both_correct": int(both_correct.sum()), "rescue": int(rescue.sum()),
                          "harm": int(harm.sum()), "both_wrong": int(both_wrong.sum())},
        "mean_accept_utility": float(accept.mean()),
        "mean_escalate_utility": float(escalate.mean()),
        "mean_paired_escalation_gain": float(full_gain.mean()),
        "paired_escalation_gain_ci90": ci90(full_gain),
        "oracle": {"nondeployable_hindsight_upper_bound": True,
                   "mean_utility": float(oracle.mean()),
                   "mean_gain_over_accept": float(oracle_gain.mean()),
                   "gain_ci90": ci90(oracle_gain),
                   "escalated_pairs": int((gain > 0).sum())},
        "same_question_half_transfer": half,
        "variance": signed_between(gain) | {"signed_between_ci90": between_ci90(gain)},
    }, gain


def policy_diagnostics(report_statistics, ids, direct, thinking, preference):
    index = {qid: i for i, qid in enumerate(ids)}
    results = {}
    gain = thinking[:, :, 0] - direct[:, :, 0] - preference * thinking[:, :, 1] / 1000
    for name, condition in report_statistics["conditions"].items():
        draws = condition["evaluation_draws"]
        if set(condition["per_question"]) != set(ids):
            raise ValueError("Primary policy question coverage changed")
        policies = {}
        for policy, summary in condition["summary"].items():
            correct, tokens, seconds, utility, escalation = [], [], [], [], []
            useful = wasted = harmful = missed = 0
            for qid in ids:
                i = index[qid]
                decisions = condition["per_question"][qid]["policies"][policy]["decisions"]
                if len(decisions) != len(draws) or any(type(value) is not bool for value in decisions):
                    raise ValueError("Primary policy decisions changed")
                for sample, action in zip(draws, decisions):
                    d, t = direct[i, sample], thinking[i, sample]
                    g = gain[i, sample]
                    correct.append(t[0] if action else d[0])
                    charged = d[1] + (t[1] if action else 0)
                    tokens.append(charged)
                    seconds.append(d[2] + (t[2] if action else 0))
                    utility.append(correct[-1] - preference * charged / 1000)
                    escalation.append(action)
                    useful += bool(action and g > 0)
                    wasted += bool(action and g <= 0)
                    harmful += bool(action and d[0] == 1 and t[0] == 0)
                    missed += bool(not action and g > 0)
            measured = {"mean_accuracy": float(np.mean(correct)),
                        "mean_tokens": float(np.mean(tokens)),
                        "mean_seconds": float(np.mean(seconds)),
                        "mean_utility": float(np.mean(utility)),
                        "mean_escalation_rate": float(np.mean(escalation))}
            for metric, value in measured.items():
                close(value, summary[metric])
            policies[policy] = measured | {
                "useful_escalations_gain_positive": useful,
                "wasted_escalations_gain_nonpositive": wasted,
                "harmful_escalations_thinking_wrong_direct_correct": harmful,
                "missed_positive_gain_opportunities": missed,
                "evaluated_pairs": len(correct),
            }
        results[name] = {"train_draws": condition["train_draws"],
                         "evaluation_draws": draws, "policies": policies}
    return results


def freeze_plan(path, payload):
    """An existing identity is immutable; no overwrite on source/input changes."""
    if path.exists():
        if verified(path) != payload:
            raise ValueError("Post-hoc diagnosis source or input identity changed")
    else:
        atomic_json(path, envelope(payload))


def write_output(output, plan, report):
    """Serialize both immutable envelopes under one output-directory lock."""
    with run_lock(output):
        freeze_plan(output / "analysis-plan.json", plan)
        freeze_plan(output / "report.json", report)


def diagnose(study=Path(ROOT) / STUDY, output=None):
    study = Path(study).resolve()
    protocol, manifest, rows = endpoint(study)
    # The following are opened only after the completed endpoint guard.
    score = verified(study / "scores.numeric-v7.json")
    primary = verified(study / "report.json")
    features = verified(study / "question-features.json")
    if (score["protocol_sha256"] != digest(protocol)
            or score["allocation_sha256"] != protocol["allocation_sha256"]
            or score["scoring_implementation_sha256"] != protocol["scoring_implementation_sha256"]
            or score["run_id"] != manifest["run_id"]
            or score["records_sha256"] != digest(rows) or score["scoring_version"] != "numeric-v7"
            or primary["protocol_sha256"] != digest(protocol)
            or primary["scores_sha256"] != digest(score)
            or primary["statistics"]["analysis"] != protocol["analysis"]
            or primary["statistics"]["scale_acquisition"]):
        raise ValueError("Frozen scored endpoint or failed primary gate identity changed")
    ids = [item["question"]["id"] for item in protocol["selected"]]
    scores = {item["job_id"]: item for item in score["scores"]}
    if (len(ids) != 50 or len(set(ids)) != 50 or len(scores) != 800
            or len(score["scores"]) != 800 or set(scores) != {row["job"]["id"] for row in rows}):
        raise ValueError("Repeat role or score coverage changed")
    if (set(protocol["folds"]) != set(ids)
            or [list(protocol["folds"].values()).count(fold) for fold in range(5)] != [10] * 5):
        raise ValueError("Frozen question-fold sizes changed")
    direct = np.full((50, 8, 3), np.nan)
    thinking = np.full_like(direct, np.nan)
    index = {qid: i for i, qid in enumerate(ids)}
    for row in rows:
        job, result = row["job"], row["result"]
        score_row = scores[job["id"]]
        if (score_row["question_id"] != job["question_id"] or score_row["mode"] != job["mode"]
                or type(score_row["correct"]) is not bool):
            raise ValueError("Score job fields changed")
        array = direct if job["mode"] == "direct" else thinking
        array[index[job["question_id"]], job["sample"]] = [
            float(score_row["correct"]),
            float(sum(result[f"{stage}_tokens"] for stage in ("reasoning", "answer", "inserted"))),
            float(result["elapsed_seconds"]),
        ]
    if not (np.isfinite(direct).all() and np.isfinite(thinking).all()):
        raise ValueError("Paired response matrix is incomplete")
    if features["questions"] != [item["question"] for item in protocol["selected"]]:
        raise ValueError("Question features differ from frozen role")
    q_features = np.asarray(features["features"], dtype=float)
    if q_features.shape != (50, 387):
        raise ValueError("Question feature dimension changed")
    preference = protocol["analysis"]["lambda"]
    aggregate, _ = outcomes(direct, thinking, preference)
    conditions = policy_diagnostics(primary["statistics"], ids, direct, thinking, preference)
    if aggregate["paired_states"]["rescue"] != primary["statistics"]["paired_outcome_states"]["rescue_draws"]:
        raise ValueError("Paired rescue states differ from primary report")
    plan = {
        "version": "repeat-diagnosis-v1", "label": "post_hoc/development",
        "primary_report_unchanged": True, "primary_gates_failed": True,
        "protocol_sha256": digest(protocol), "records_sha256": digest(rows),
        "scores_sha256": digest(score), "primary_report_sha256": digest(primary),
        "features_sha256": digest(features), "script_sha256": file_hash(__file__),
        "input_file_sha256": {name: file_hash(study / name) for name in
            ("protocol.json", "scores.numeric-v7.json", "report.json", "question-features.json")},
        "bootstrap": {"questions": 50, "draws": BOOTSTRAPS, "seed": SEED,
                      "interval": INTERVAL, "conditional_on_cached_labels": True},
        "no_new_model_fit": True, "no_new_gold": True, "no_generation": True,
        "scope": "Explains a failed diagnostic gate; cannot revive it or support confirmation",
    }
    report = {"plan_sha256": digest(plan), "label": "post_hoc/development",
              "primary_gates": primary["statistics"]["gates"],
              "aggregate": aggregate, "conditions": conditions,
              "dimensions": {"question_features": int(q_features.shape[1]),
                             "draft_features": 4, "outer_training_unique_questions": 40,
                             "inner_training_unique_questions": 30,
                             "draw_rows_per_outer_training_fold": {str(k): 40 * k for k in (1, 2, 4, 8)}},
              "interpretation_limits": [
                  "Oracle uses hindsight and is not deployable.",
                  "Half-transfer uses four paired acquisitions from the same question; its evaluation utility excludes selection acquisition and is not deployed net utility.",
                  "Half-transfer is not unseen-question generalization.",
                  "Intervals resample questions with cached predictions/labels; no multiplicity adjustment.",
                  "Post-hoc analysis does not change failed predeclared gates or justify scaling.",
              ]}
    output = Path(output).resolve() if output else study.parent / "repeat-diagnosis-v1"
    write_output(output, plan, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", default=str(Path(ROOT) / STUDY))
    parser.add_argument("--output")
    args = parser.parse_args()
    result = diagnose(args.study, args.output)
    output = Path(args.output).resolve() if args.output else Path(args.study).resolve().parent / "repeat-diagnosis-v1"
    print({"post_hoc_report": str(output / "report.json"),
           "primary_gates_unchanged": result["primary_gates"]})


if __name__ == "__main__":
    main()
