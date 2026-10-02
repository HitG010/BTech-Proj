"""Bounded exploratory CPU controls; prepare a frozen plan before any fitting.

Reads only the completed endpoint, cached v7 scores, primary report and frozen
features. Never scores, fetches references, generates, or changes primary gates.
"""

import argparse
import importlib.metadata
import platform
import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from reasoning_budget import repeat_stats as historical
from reasoning_budget.confirmation import file_hash
from reasoning_budget.research_repeat import ROOT, STUDY
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import diagnose_repeat_signal as diagnosis

SPEC = {
    "version": "repeat-cpu-feasibility-v1", "label": "post_hoc/development",
    "conditions": {"k4_A_to_B": [[0, 1, 2, 3], [4, 5, 6, 7]],
                   "k4_B_to_A": [[4, 5, 6, 7], [0, 1, 2, 3]],
                   "k8_full": [list(range(8)), list(range(8))]},
    "lambda": 0.05, "inner_folds": 4, "alphas": [100.0, 1000.0, 10000.0],
    "thresholds": [0.0, 0.02, 0.05], "correction_margins": [0.02, 0.05, 0.10],
    "pca_components": 8, "families": ["draft4", "compressed", "correction"],
    "seed": 20261002, "bootstrap_seed": 20261002,
    "bootstrap_draws": 2000, "interval": [0.05, 0.95],
    "threads": 1, "maximum_ridge_fits": 1035, "maximum_pca_fits": 75,
    "promotion_minimum_mean": 0.01,
    "selection": "grouped inner mean utility; ties prefer larger alpha/threshold/margin; family order",
    "correction": "best inner-selected draft4 recommendation overrides confidence only when abs(predicted gain)>=margin",
    "scope": "Fixed exploratory grid; no adaptive expansion or router latency claim; primary failed gates remain authoritative",
}
PARSER_REPORT_SHA256 = "51cbe6a6db3b0ec8be6e033427af7ad58fbfaf7721924fef3126c0321a5ec199"


def parser_preflight(study):
    path = Path(study).resolve().parent / "parser-compatibility-v1" / "report.json"
    report = verified(path)
    if (digest(report) != PARSER_REPORT_SHA256
            or report["decision"] != "compatible_narrow_candidate_retain_v7_primary"
            or report["compatibility_gate_pass"] is not True
            or report["primary_labels"] != "unchanged frozen v7"
            or report["no_score_cache_written"] is not True
            or report["input_records_preserved"] is not True):
        raise ValueError("Completed Phase 2a parser preflight identity changed")
    return {"path": str(path), "payload_sha256": digest(report), "file_sha256": file_hash(path)}


def load_inputs(study):
    study = Path(study).resolve()
    protocol, manifest, rows = diagnosis.endpoint(study)
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
            or primary["statistics"]["scale_acquisition"]
            or digest(features) != protocol["question_features_sha256"]):
        raise ValueError("Frozen cached endpoint identity changed")
    ids = [item["question"]["id"] for item in protocol["selected"]]
    scores = {item["job_id"]: item for item in score["scores"]}
    if (len(ids) != 50 or len(set(ids)) != 50 or len(scores) != 800
            or len(score["scores"]) != 800 or set(scores) != {row["job"]["id"] for row in rows}
            or set(protocol["folds"]) != set(ids)
            or [list(protocol["folds"].values()).count(fold) for fold in range(5)] != [10] * 5
            or features["questions"] != [item["question"] for item in protocol["selected"]]):
        raise ValueError("Frozen question/score/fold coverage changed")
    d = np.full((50, 8, 3), np.nan)
    t = np.full_like(d, np.nan)
    z = np.full((50, 8, 4), np.nan)
    index = {qid: i for i, qid in enumerate(ids)}
    for row in rows:
        job, result = row["job"], row["result"]
        cached = scores[job["id"]]
        if (cached["question_id"] != job["question_id"] or cached["mode"] != job["mode"]
                or type(cached["correct"]) is not bool or job["mode"] not in ("direct", "thinking")
                or not isinstance(cached["parser_status"], str)):
            raise ValueError("Cached score job fields changed")
        i, draw = index[job["question_id"]], job["sample"]
        target = d if job["mode"] == "direct" else t
        if np.isfinite(target[i, draw]).any():
            raise ValueError("Duplicate paired endpoint cell")
        target[i, draw] = [float(cached["correct"]),
            sum(result[f"{stage}_tokens"] for stage in ("reasoning", "answer", "inserted")),
            result["elapsed_seconds"]]
        if job["mode"] == "direct":
            z[i, draw] = [result["mean_generated_logprob"], np.log1p(result["answer_tokens"]),
                          float(cached["parser_status"] == "ok"), float(result["answer_truncated"])]
    q = np.asarray(features["features"], dtype=float)
    validate(ids, q, d, t, z, protocol["folds"])
    identity = {"protocol_sha256": digest(protocol), "records_sha256": digest(rows),
        "scores_sha256": digest(score), "primary_report_sha256": digest(primary),
        "features_sha256": digest(features),
        "input_file_sha256": {name: file_hash(study / name) for name in
            ("protocol.json", "scores.numeric-v7.json", "report.json", "question-features.json")}}
    return (ids, q, d, t, z, protocol["folds"]), primary, identity


def validate(ids, q, d, t, z, folds):
    historical._validate(ids, q, d, t, z, folds, historical.ANALYSIS)
    if q.shape[1] != 387 or min(sum(folds[qid] != f for qid in ids) for f in range(5)) < 12:
        raise ValueError("Need frozen 387 features and enough unique training questions for PCA8")


def load_panel(study):
    """Shared read-only cached loader; labels never become draft features."""
    data, primary, identity = load_inputs(study)
    protocol, _, rows = diagnosis.endpoint(study)
    if digest(rows) != identity["records_sha256"] or digest(protocol) != identity["protocol_sha256"]:
        raise ValueError("Panel inputs changed while loading")
    ids, q, d, t, z, folds = data
    return {"ids": ids, "q": q, "z": z, "d": d, "t": t, "folds": folds,
            "protocol": protocol, "primary": primary, "rows": rows, "identity": identity}


def plan_for(study, identity):
    return {"spec": SPEC, "study": str(Path(study).resolve()), "inputs": identity,
        "parser_preflight": parser_preflight(study),
        "source_file_sha256": {str(Path(path).resolve()): file_hash(path) for path in
            (__file__, historical.__file__, diagnosis.__file__,
             Path(__file__).resolve().parents[1] / "tests" / "test_repeat_cpu_feasibility.py",
             Path(__file__).resolve().parents[1] / "docs" / "phase-2-cpu-feasibility-protocol.md")},
        "environment": {"python": platform.python_version(), "packages": {
            name: importlib.metadata.version(name) for name in
            ("numpy", "scipy", "scikit-learn", "threadpoolctl")}},
        "no_new_references": True, "no_generation": True, "primary_gates_unchanged": True,
        "fit_bound": {"outer_fits": 15, "historical_ridge_per_outer": 39,
                      "new_inner_ridge_per_outer": 24, "new_outer_ridge_per_outer": 6,
                      "pca_per_outer": 5}}


def prepare(study, output):
    output = checked_output(study, output)
    _, _, identity = load_inputs(study)
    plan = plan_for(study, identity)
    with run_lock(output):
        diagnosis.freeze_plan(Path(output) / "analysis-plan.json", plan)
    return plan


def checked_output(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output == study or study in output.parents:
        raise ValueError("CPU output must be outside the frozen study")
    return output


class Representation:
    """All transforms are fit on unique training questions or training draft rows."""

    def __init__(self, kind, q, z, questions, draws):
        self.kind, self.questions = kind, list(map(int, questions))
        self.pca = self.q_scaler = self.lex_scaler = None
        self.z_scaler = StandardScaler().fit(z[np.ix_(questions, draws)].reshape(-1, 4))
        if kind == "compressed":
            self.pca = PCA(n_components=8, svd_solver="full").fit(q[questions, :384])
            self.q_scaler = StandardScaler().fit(self.pca.transform(q[questions, :384]))
            self.lex_scaler = StandardScaler().fit(q[questions, 384:])
        elif kind != "draft4":
            raise ValueError("Unknown representation")

    def transform(self, q, z, questions, draws):
        draft = self.z_scaler.transform(z[np.ix_(questions, draws)].reshape(-1, 4)) / 2
        if self.kind == "draft4":
            # Draft-only has historical standardized 4-feature scale; stronger
            # alpha comparison should not silently rescale that baseline.
            return draft * 2
        embedding = self.q_scaler.transform(self.pca.transform(q[questions, :384])) / np.sqrt(8)
        lexical = self.lex_scaler.transform(q[questions, 384:]) / np.sqrt(3)
        question = np.concatenate([embedding, lexical], axis=1)
        return np.concatenate([np.repeat(question, len(draws), axis=0), draft], axis=1)


def fit_predict(rep, q, z, gain, train, draws, test, eval_draws, alpha):
    model = Ridge(alpha=alpha, solver="svd").fit(
        rep.transform(q, z, train, draws), gain[np.ix_(train, draws)].ravel())
    return model.predict(rep.transform(q, z, test, eval_draws)).reshape(len(test), len(eval_draws))


def key(family, alpha, threshold):
    return f"{family}:alpha={alpha:g}:threshold={threshold:g}"


def correction(confidence, prediction, threshold, margin):
    return np.where(np.abs(prediction) >= margin, prediction > threshold, confidence)


def new_fold(q, z, d, t, gain, train, test, train_draws, eval_draws, seed):
    splits = historical._inner_splits(train, seed, 4)
    candidates = {key(family, a, threshold): [] for family in ("draft4", "compressed")
                  for a in SPEC["alphas"] for threshold in SPEC["thresholds"]}
    predictions, confidences = {}, []
    for split, (inside, heldout) in enumerate(splits):
        confidence_threshold = historical._confidence_threshold(z, d, t, inside, train_draws, 0.05)
        confidences.append(z[np.ix_(heldout, train_draws, [0])][:, :, 0] < confidence_threshold)
        for family in ("draft4", "compressed"):
            rep = Representation(family, q, z, inside, train_draws)
            for alpha in SPEC["alphas"]:
                prediction = fit_predict(rep, q, z, gain, inside, train_draws, heldout, train_draws, alpha)
                predictions[split, family, alpha] = prediction
                for threshold in SPEC["thresholds"]:
                    candidates[key(family, alpha, threshold)].extend(historical._rows(
                        d, t, heldout, train_draws, prediction > threshold, 0.05)["utility"])
    settings = {}
    for family in ("draft4", "compressed"):
        alpha, threshold = max(((a, v) for a in SPEC["alphas"] for v in SPEC["thresholds"]),
            key=lambda pair: (np.mean(candidates[key(family, *pair)]), *pair))
        settings[family] = {"alpha": alpha, "threshold": threshold,
                            "inner_utility": float(np.mean(candidates[key(family, alpha, threshold)]))}
    draft = settings["draft4"]
    for margin in SPEC["correction_margins"]:
        scores = []
        for split, (_, heldout) in enumerate(splits):
            actions = correction(confidences[split], predictions[split, "draft4", draft["alpha"]],
                                 draft["threshold"], margin)
            scores.extend(historical._rows(d, t, heldout, train_draws, actions, 0.05)["utility"])
        candidates[f"correction:margin={margin:g}"] = scores
    margin = max(SPEC["correction_margins"],
                 key=lambda value: (np.mean(candidates[f"correction:margin={value:g}"]), value))
    settings["correction"] = draft | {"margin": margin,
        "inner_utility": float(np.mean(candidates[f"correction:margin={margin:g}"]))}
    selected = max(SPEC["families"], key=lambda family: settings[family]["inner_utility"])
    outer_confidence = historical._confidence_threshold(z, d, t, train, train_draws, 0.05)
    confidence = z[np.ix_(test, eval_draws, [0])][:, :, 0] < outer_confidence
    actions, outer_predictions = {}, {}
    for family in ("draft4", "compressed"):
        rep = Representation(family, q, z, train, train_draws)
        for alpha in SPEC["alphas"]:
            prediction = fit_predict(rep, q, z, gain, train, train_draws, test, eval_draws, alpha)
            outer_predictions[family, alpha] = prediction
            for threshold in SPEC["thresholds"]:
                actions[key(family, alpha, threshold)] = prediction > threshold
        actions[family] = actions[key(family, settings[family]["alpha"], settings[family]["threshold"])]
    for value in SPEC["correction_margins"]:
        actions[f"correction:margin={value:g}"] = correction(confidence,
            outer_predictions["draft4", draft["alpha"]], draft["threshold"], value)
    actions["correction"] = actions[f"correction:margin={margin:g}"]
    actions["selected_new"] = actions[selected]
    detail = {"selected_family": selected, "settings": settings,
              "candidate_inner_utility": {name: float(np.mean(values)) for name, values in candidates.items()},
              "inner_splits": [{"training_indices": a.tolist(), "validation_indices": b.tolist(),
                                "training_pairs": len(a) * len(train_draws),
                                "validation_pairs": len(b) * len(train_draws)} for a, b in splits],
              "ridge_fits": 30, "pca_fits": 5}
    return actions, detail


def verify_historical(primary, name, ids, test, actions):
    cached = primary["statistics"]["conditions"][name]
    for policy in ("accept", "escalate", "confidence", "solver_only", "combined"):
        for j, i in enumerate(test):
            if actions[policy][j].tolist() != cached["per_question"][ids[i]]["policies"][policy]["decisions"]:
                raise ValueError(f"Historical action reproduction failed: {name}/{ids[i]}/{policy}")


def summarize(ids, rows, d, t, eval_draws):
    policies = next(iter(rows.values()))["policies"]
    summaries = {}
    for policy in policies:
        per_q = [rows[qid]["policies"][policy] for qid in ids]
        actions = np.asarray([row["decisions"] for row in per_q])
        gains = t[:, eval_draws, 0] - d[:, eval_draws, 0] - 0.05 * t[:, eval_draws, 1] / 1000
        delta = np.array([row["utility"] - rows[qid]["policies"]["confidence"]["utility"]
                          for qid, row in zip(ids, per_q)])
        summaries[policy] = {f"mean_{metric}": float(np.mean([row[metric] for row in per_q]))
            for metric in ("accuracy", "tokens", "seconds", "utility", "escalation_rate")} | {
            "pairs": int(actions.size), "escalations": int(actions.sum()),
            "positive_gain_escalations": int((actions & (gains > 0)).sum()),
            "nonpositive_gain_escalations": int((actions & (gains <= 0)).sum()),
            "harmful_escalations": int((actions & (d[:, eval_draws, 0] == 1)
                                         & (t[:, eval_draws, 0] == 0)).sum()),
            "missed_positive_gain_opportunities": int((~actions & (gains > 0)).sum()),
            "delta_vs_confidence": {"mean": float(delta.mean()), "ci90": historical._ci(delta, SPEC),
                                    "per_question": dict(zip(ids, map(float, delta)))}}
    return summaries


def analyze(data, primary=None):
    ids, q, d, t, z, folds = data
    validate(*data)
    gain = t[:, :, 0] - d[:, :, 0] - 0.05 * t[:, :, 1] / 1000
    conditions, total_seconds = {}, 0.0
    for name, (draws, evaluate) in SPEC["conditions"].items():
        if primary is not None:
            cached = primary["statistics"]["conditions"][name]
            if cached["train_draws"] != draws or cached["evaluation_draws"] != evaluate:
                raise ValueError("Historical condition draw partition changed")
        rows, details = {qid: {"fold": folds[qid], "policies": {}} for qid in ids}, []
        for fold in range(5):
            train = np.array([i for i, qid in enumerate(ids) if folds[qid] != fold])
            test = np.array([i for i, qid in enumerate(ids) if folds[qid] == fold])
            started = time.perf_counter()
            _, old_settings, confidence, old_actions, _ = historical._fit_fold(
                q, z, d, t, gain, train, test, draws, evaluate, historical.ANALYSIS,
                historical.ANALYSIS["bootstrap_seed"] + fold)
            if primary is not None:
                verify_historical(primary, name, ids, test, old_actions)
            actions, detail = new_fold(q, z, d, t, gain, train, test, draws, evaluate, SPEC["seed"] + fold)
            actions.update({p: old_actions[p] for p in ("accept", "escalate", "confidence", "solver_only", "combined")})
            elapsed = time.perf_counter() - started
            total_seconds += elapsed
            detail.update({"fold": fold, "train_ids": [ids[i] for i in train],
                "test_ids": [ids[i] for i in test], "training_pairs": int(len(train) * len(draws)),
                "evaluation_pairs": int(len(test) * len(evaluate)), "fit_and_prediction_seconds": elapsed,
                "historical_ridge_fits": 39, "historical_alphas": old_settings,
                "historical_confidence_threshold": confidence})
            details.append(detail)
            for policy, decisions in actions.items():
                measured = historical._rows(d, t, test, evaluate, decisions, 0.05)
                for j, i in enumerate(test):
                    rows[ids[i]]["policies"][policy] = {
                        metric: float(values[j]) for metric, values in measured.items()
                    } | {"decisions": decisions[j].tolist()}
        conditions[name] = {"train_draws": draws, "evaluation_draws": evaluate,
                            "folds": details, "per_question": rows,
                            "summary": summarize(ids, rows, d, t, evaluate)}
    names = ["k4_A_to_B", "k4_B_to_A"]
    deltas = np.array([[conditions[name]["summary"]["selected_new"]["delta_vs_confidence"]
                       ["per_question"][qid] for qid in ids] for name in names])
    average = deltas.mean(0)
    leave_one = (average.sum() - average) / (len(ids) - 1)
    averages = {}
    for policy in [*SPEC["families"], "selected_new"]:
        values = np.mean([[conditions[name]["summary"][policy]["delta_vs_confidence"]
                           ["per_question"][qid] for qid in ids] for name in names], axis=0)
        leave = (values.sum() - values) / (len(ids) - 1)
        averages[policy] = {"mean": float(values.mean()), "ci90": historical._ci(values, SPEC),
            "per_question": dict(zip(ids, map(float, values))),
            "leave_one_question_out_mean": dict(zip(ids, map(float, leave)))}
    return {"label": "post_hoc/development", "conditions": conditions,
        "selected_new_average_vs_confidence": {"mean": float(average.mean()),
            "ci90": historical._ci(average, SPEC), "per_question": dict(zip(ids, map(float, average))),
            "leave_one_question_out_mean": dict(zip(ids, map(float, leave_one))),
            "most_influential_question": ids[int(np.argmax(np.abs(leave_one - average.mean())))]},
        "family_average_vs_confidence": averages,
        "promotion_screen": {"passes": bool(average.mean() >= 0.01
                and (deltas.mean(1) > 0).all() and (leave_one > 0).all()),
            "average_at_least_001": bool(average.mean() >= 0.01),
            "both_directions_positive": bool((deltas.mean(1) > 0).all()),
            "all_leave_one_question_out_positive": bool((leave_one > 0).all()),
            "restores_primary_gate": False},
        "fit_accounting": {"ridge_fits": 1035, "pca_fits": 75,
                           "fit_counts": "design-derived fixed grid; instrumented in synthetic tests",
                           "fit_and_prediction_seconds": total_seconds, "router_latency_measured": False},
        "limitations": ["Question-cluster bootstrap conditions on fixed fits; no refitting or multiplicity adjustment.",
            "All new fitting is exploratory on reused development data; no unseen-question confirmation.",
            "Full8 has no independent same-question eight-draw replica.",
            "No scaling, new generation, contrastive training or primary gate change is authorized."]}


def run(study, output):
    output = checked_output(study, output)
    with run_lock(output):
        path = output / "analysis-plan.json"
        if not path.exists():
            raise ValueError("Prepare and freeze analysis-plan.json before fitting")
        data, primary, identity = load_inputs(study)
        plan = plan_for(study, identity)
        if verified(path) != plan:
            raise ValueError("Frozen CPU plan/source/environment/input identity changed")
        if (output / "report.json").exists():
            report = verified(output / "report.json")
            if report["plan_sha256"] != digest(plan):
                raise ValueError("CPU report belongs to another plan")
            return report
        with threadpool_limits(limits=1):
            report = analyze(data, primary)
        # Recheck identities after fitting; never publish mixed-input results.
        _, _, after = load_inputs(study)
        if plan_for(study, after) != plan:
            raise ValueError("CPU inputs changed during fitting")
        report.update({"plan_sha256": digest(plan), "primary_gates": primary["statistics"]["gates"],
                       "historical_actions_exactly_reproduced": True})
        atomic_json(output / "report.json", envelope(report))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--study", default=str(Path(ROOT) / STUDY))
    parser.add_argument("--output")
    args = parser.parse_args()
    output = Path(args.output) if args.output else Path(args.study).parent / "repeat-cpu-feasibility-v1"
    result = prepare(args.study, output) if args.command == "prepare" else run(args.study, output)
    print({"command": args.command, "output": str(output), "payload_sha256": digest(result)})


if __name__ == "__main__":
    main()
