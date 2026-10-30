"""Post-hoc token-level deferral check on the repeat panel.

Teacher-forces the cached direct drafts through the frozen Qwen3-1.7B backend to
recover per-token log probabilities, then evaluates token-level deferral rules on
the repeat study's folds and draw halves against the frozen confidence policy.
No generation, scoring or reference access; held-out labels choose nothing.
"""

import argparse
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from reasoning_budget import repeat_stats as historical
from reasoning_budget.storage import digest, envelope, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
REPEAT = BASE / "repeat-panel-v1"
OUTPUT = BASE / "token-deferral-v1"
SOURCE_FILES = ("scripts/audit_token_deferral.py", "tests/test_audit_token_deferral.py",
                "docs/token-deferral-protocol.md")
QUANTILES = [0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
FEATURES = [f"quantile_{q:g}" for q in QUANTILES] + ["mean", "log1p_tokens"]
CANDIDATES = ("learned_error_score", "min_token_threshold", "token_gain_ridge")
SPEC = {
    "version": "token-deferral-v1", "label": "post_hoc/exploratory/reused-development",
    "panel": "repeat_qwen3_1.7b", "drafts": 400,
    "token_logprob": "pre-warper log_softmax of teacher-forced logits at recorded answer_token_ids",
    "quantiles": QUANTILES, "features": FEATURES,
    "fidelity": {"raw_mean_tolerance": 0.02, "raw_mean_share_within": 0.99,
                 "raw_mean_maximum": 0.10},
    "conditions": {"k4_A_to_B": [[0, 1, 2, 3], [4, 5, 6, 7]],
                   "k4_B_to_A": [[4, 5, 6, 7], [0, 1, 2, 3]],
                   "k8_full": [list(range(8)), list(range(8))]},
    "primary_conditions": ["k4_A_to_B", "k4_B_to_A"],
    "lambda": 0.05, "inner_folds": 4, "seed": 20261030, "logistic_C": 1.0,
    "ridge_alphas": [1.0, 10.0, 100.0, 1000.0], "ridge_thresholds": [0.0, 0.02, 0.05],
    "candidates": list(CANDIDATES), "primary_candidate": "learned_error_score",
    "comparator": "frozen four-draw confidence decisions reproduced from the primary report",
    "bootstrap_seed": 20261030, "bootstrap_draws": 2000, "interval": [0.05, 0.95],
    "screen": {"minimum_mean": 0.01, "both_directions_positive": True,
               "all_leave_one_question_out_positive": True},
    "selection": "training questions and draws only; ties prefer larger alpha/threshold",
}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quantile_features(raw):
    raw = np.asarray(raw, dtype=float)
    if raw.ndim != 1 or not raw.size or not np.isfinite(raw).all():
        raise ValueError("Nonempty finite token log probabilities required")
    return [*map(float, np.quantile(raw, QUANTILES)), float(raw.mean()), float(np.log1p(raw.size))]


def warped_logprobs(top_values, top_indices, tokens, temperature, top_p):
    """Post-warper token log probabilities in transformers order: temperature, top-k, top-p.

    `top_values`/`top_indices` hold the k largest raw logits per position in
    descending order. A token outside the kept support returns -inf.
    """
    values = np.asarray(top_values, dtype=float) / temperature
    indices, tokens = np.asarray(top_indices), np.asarray(tokens)
    if values.ndim != 2 or values.shape != indices.shape or tokens.shape != values.shape[:1]:
        raise ValueError("Aligned per-position top-k arrays required")
    if np.any(np.diff(values, axis=1) > 0):
        raise ValueError("Top-k values must be in descending order")
    probabilities = np.exp(values - values[:, :1])
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    remove = np.cumsum(probabilities[:, ::-1], axis=1) <= 1 - top_p
    remove[:, -1] = False
    keep = ~remove[:, ::-1]
    out = np.full(len(tokens), -np.inf)
    for i, token in enumerate(tokens):
        hit = np.flatnonzero(indices[i] == token)
        if hit.size and keep[i, hit[0]]:
            kept = values[i][keep[i]]
            out[i] = values[i, hit[0]] - kept.max() - np.log(np.exp(kept - kept.max()).sum())
    return out


def fidelity(rows, spec=SPEC):
    rule = spec["fidelity"]
    raw = [abs(r["raw_mean"] - r["recorded_raw_mean"]) for r in rows
           if r["recorded_raw_mean"] is not None]
    warped = [abs(r["warped_mean"] - r["recorded_warped_mean"]) for r in rows
              if r["warped_mean"] is not None]
    within = float(np.mean(np.asarray(raw) <= rule["raw_mean_tolerance"])) if raw else 0.0
    checks = {
        "all_drafts_present": len(rows) == spec["drafts"],
        "unique_question_draws": len({(r["question_id"], r["sample"]) for r in rows}) == len(rows),
        "prompt_tokens_match": all(r["prompt_tokens"] == r["recorded_prompt_tokens"] for r in rows),
        "answer_tokens_match": all(r["answer_tokens"] == r["recorded_answer_tokens"] for r in rows),
        "decoded_text_matches": all(r["decoded_matches"] for r in rows),
        "raw_mean_recorded_for_all": len(raw) == len(rows),
        "raw_mean_share_within_tolerance": within >= rule["raw_mean_share_within"],
        "raw_mean_maximum_difference": bool(raw) and max(raw) <= rule["raw_mean_maximum"],
    }

    def spread(values):
        return {"median": float(np.median(values)), "p99": float(np.quantile(values, 0.99)),
                "max": float(np.max(values))} if values else None

    return {"checks": checks, "passed": all(checks.values()),
            "raw_mean_abs_difference": spread(raw), "raw_mean_share_within_tolerance": within,
            "warped_mean_abs_difference": spread(warped),
            "warped_support_misses": int(sum(r["warped_support_misses"] for r in rows)),
            "drafts_with_warped_support_misses":
                int(sum(r["warped_support_misses"] > 0 for r in rows))}


def prompt_ids(engine, prompt):
    """Rebuild the exact direct-mode prefix used by the collection backend."""
    text = engine.tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt + "\n\n" + engine.config.prompt_suffix}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return engine.tokenizer.encode(text, add_special_tokens=False)


def teacher_force(engine, prefix, answer, top_k):
    """One forward pass over prompt plus recorded answer; no token is generated."""
    torch = engine.torch
    ids = torch.tensor([prefix + answer], dtype=torch.long, device=engine.config.model.device)
    with torch.inference_mode():
        logits = engine.model(input_ids=ids, attention_mask=torch.ones_like(ids)).logits[0]
        rows = logits[len(prefix) - 1:len(prefix) - 1 + len(answer)].float()
        target = torch.tensor(answer, dtype=torch.long, device=rows.device)[:, None]
        raw = torch.log_softmax(rows, dim=-1).gather(1, target)[:, 0]
        top_values, top_indices = torch.topk(rows, top_k, dim=-1)
    return (raw.cpu().numpy(), top_values.cpu().numpy(), top_indices.cpu().numpy())


def direct_drafts(study):
    from scripts.diagnose_repeat_signal import endpoint
    protocol, _, rows = endpoint(study)
    order = {item["question"]["id"]: i for i, item in enumerate(protocol["selected"])}
    questions = {item["question"]["id"]: item["question"] for item in protocol["selected"]}
    drafts = sorted((r for r in rows if r["job"]["mode"] == "direct"),
                    key=lambda r: (order[r["job"]["question_id"]], r["job"]["sample"]))
    return protocol, questions, drafts


def direct_job_ids(panel_rows):
    return {(r["job"]["question_id"], r["job"]["sample"]): r["job"]["id"]
            for r in panel_rows if r["job"]["mode"] == "direct"}


def feature_tensor(ids, token_rows, job_ids, draws=8):
    index = {qid: i for i, qid in enumerate(ids)}
    features = np.full((len(ids), draws, len(FEATURES)), np.nan)
    recorded = np.full((len(ids), draws), np.nan)
    for row in token_rows:
        key = (row["question_id"], row["sample"])
        if job_ids.get(key) != row["job_id"] or np.isfinite(features[index[key[0]], key[1]]).any():
            raise ValueError(f"Token row does not match a unique panel draft: {key}")
        features[index[key[0]], key[1]] = quantile_features(row["raw_logprobs"])
        recorded[index[key[0]], key[1]] = row["recorded_warped_mean"]
    if not np.isfinite(features).all():
        raise ValueError("Every panel draft needs token features")
    return features, recorded


def _matrix(features, questions, draws):
    return features[np.ix_(questions, draws)].reshape(-1, features.shape[2])


def fit_error_model(features, d, questions, draws, c):
    x = _matrix(features, questions, draws)
    y = (d[np.ix_(questions, draws)][:, :, 0] == 0).astype(int).ravel()
    scaler = StandardScaler().fit(x)
    if len(np.unique(y)) < 2:
        return scaler, float(y.mean())
    return scaler, LogisticRegression(C=c, max_iter=5000).fit(scaler.transform(x), y)


def predict_error(model, features, questions, draws):
    scaler, fitted = model
    x = scaler.transform(_matrix(features, questions, draws))
    p = np.full(len(x), fitted) if isinstance(fitted, float) else fitted.predict_proba(x)[:, 1]
    return p.reshape(len(questions), len(draws))


def fit_gain_ridge(features, gain, questions, draws, alpha):
    x = _matrix(features, questions, draws)
    scaler = StandardScaler().fit(x)
    model = Ridge(alpha=alpha, solver="svd").fit(scaler.transform(x),
                                                 gain[np.ix_(questions, draws)].ravel())
    return scaler, model


def predict_gain(model, features, questions, draws):
    scaler, regressor = model
    x = scaler.transform(_matrix(features, questions, draws))
    return regressor.predict(x).reshape(len(questions), len(draws))


def score_threshold(score, d, t, questions, draws, lam):
    """The repeat study's confidence threshold search on any score (escalate below)."""
    z = np.zeros(score.shape + (4,))
    z[..., 0] = score
    return historical._confidence_threshold(z, d, t, questions, draws, lam)


def candidate_fold(features, d, t, gain, train, test, train_draws, eval_draws, seed, spec=SPEC):
    lam, actions = spec["lambda"], {}
    splits = historical._inner_splits(train, seed, spec["inner_folds"])
    minimum = features[..., 0]
    min_cut = score_threshold(minimum, d, t, train, train_draws, lam)
    actions["min_token_threshold"] = minimum[np.ix_(test, eval_draws)] < min_cut
    oof = np.full(features.shape[:2], np.nan)
    for inside, heldout in splits:
        model = fit_error_model(features, d, inside, train_draws, spec["logistic_C"])
        oof[np.ix_(heldout, train_draws)] = predict_error(model, features, heldout, train_draws)
    error_cut = score_threshold(-oof, d, t, train, train_draws, lam)
    final = fit_error_model(features, d, train, train_draws, spec["logistic_C"])
    actions["learned_error_score"] = -predict_error(final, features, test, eval_draws) < error_cut
    utilities = {(a, h): [] for a in spec["ridge_alphas"] for h in spec["ridge_thresholds"]}
    for inside, heldout in splits:
        for alpha in spec["ridge_alphas"]:
            prediction = predict_gain(fit_gain_ridge(features, gain, inside, train_draws, alpha),
                                      features, heldout, train_draws)
            for h in spec["ridge_thresholds"]:
                utilities[alpha, h].extend(
                    historical._rows(d, t, heldout, train_draws, prediction > h, lam)["utility"])
    alpha, threshold = max(utilities, key=lambda pair: (np.mean(utilities[pair]), *pair))
    prediction = predict_gain(fit_gain_ridge(features, gain, train, train_draws, alpha),
                              features, test, eval_draws)
    actions["token_gain_ridge"] = prediction > threshold
    return actions, {"min_token_cutoff": float(min_cut), "error_score_cutoff": float(error_cut),
                     "ridge_alpha": alpha, "ridge_threshold": threshold,
                     "ridge_inner_utility": float(np.mean(utilities[alpha, threshold])),
                     "logistic_fits": len(splits) + 1,
                     "ridge_fits": len(splits) * len(spec["ridge_alphas"]) + 1}


def summarize(ids, rows, d, t, eval_draws, spec=SPEC):
    gains = t[:, eval_draws, 0] - d[:, eval_draws, 0] - spec["lambda"] * t[:, eval_draws, 1] / 1000
    out = {}
    for policy in rows[ids[0]]["policies"]:
        per_q = [rows[qid]["policies"][policy] for qid in ids]
        actions = np.asarray([r["decisions"] for r in per_q], dtype=bool)
        delta = np.array([r["utility"] - rows[qid]["policies"]["confidence"]["utility"]
                          for qid, r in zip(ids, per_q)])
        out[policy] = {f"mean_{m}": float(np.mean([r[m] for r in per_q]))
                       for m in ("accuracy", "tokens", "utility", "escalation_rate")} | {
            "escalations": int(actions.sum()),
            "positive_gain_escalations": int((actions & (gains > 0)).sum()),
            "harmful_escalations": int((actions & (d[:, eval_draws, 0] == 1)
                                        & (t[:, eval_draws, 0] == 0)).sum()),
            "missed_positive_gain": int((~actions & (gains > 0)).sum()),
            "delta_vs_confidence": {"mean": float(delta.mean()),
                                    "ci90": historical._ci(delta, spec),
                                    "per_question": dict(zip(ids, map(float, delta)))}}
    return out


def average_screen(ids, conditions, candidate, spec=SPEC):
    names = spec["primary_conditions"]
    per = np.array([[conditions[n]["summary"][candidate]["delta_vs_confidence"]["per_question"][qid]
                     for qid in ids] for n in names])
    values = per.mean(0)
    leave = (values.sum() - values) / (len(values) - 1)
    screen = {"average_at_least_minimum": bool(values.mean() >= spec["screen"]["minimum_mean"]),
              "both_directions_positive": bool((per.mean(1) > 0).all()),
              "all_leave_one_question_out_positive": bool((leave > 0).all())}
    screen["passes"] = all(screen.values())

    def mean_of(policy, metric):
        return float(np.mean([conditions[n]["summary"][policy][metric] for n in names]))

    return {"mean": float(values.mean()), "ci90": historical._ci(values, spec),
            "directions": dict(zip(names, map(float, per.mean(1)))),
            "accuracy": mean_of(candidate, "mean_accuracy"),
            "tokens": mean_of(candidate, "mean_tokens"),
            "confidence_accuracy": mean_of("confidence", "mean_accuracy"),
            "confidence_tokens": mean_of("confidence", "mean_tokens"),
            "screen": screen, "per_question": dict(zip(ids, map(float, values)))}


def analyze(data, features, primary=None, spec=SPEC):
    ids, q, d, t, z, folds = data
    gain = t[:, :, 0] - d[:, :, 0] - spec["lambda"] * t[:, :, 1] / 1000
    conditions = {}
    for name, (draws, evaluate) in spec["conditions"].items():
        rows = {qid: {"fold": folds[qid], "policies": {}} for qid in ids}
        details = []
        for fold in range(5):
            train = np.array([i for i, qid in enumerate(ids) if folds[qid] != fold])
            test = np.array([i for i, qid in enumerate(ids) if folds[qid] == fold])
            _, _, confidence_cut, old, _ = historical._fit_fold(
                q, z, d, t, gain, train, test, draws, evaluate, historical.ANALYSIS,
                historical.ANALYSIS["bootstrap_seed"] + fold)
            if primary is not None:
                from scripts.repeat_cpu_feasibility import verify_historical
                verify_historical(primary, name, ids, test, old)
            actions, detail = candidate_fold(features, d, t, gain, train, test, draws, evaluate,
                                             spec["seed"] + fold, spec)
            actions.update({p: old[p] for p in ("accept", "escalate", "confidence")})
            details.append(detail | {"fold": fold, "confidence_cutoff": float(confidence_cut)})
            for policy, decisions in actions.items():
                measured = historical._rows(d, t, test, evaluate, decisions, spec["lambda"])
                for j, i in enumerate(test):
                    rows[ids[i]]["policies"][policy] = {
                        metric: float(values[j]) for metric, values in measured.items()
                    } | {"decisions": decisions[j].tolist()}
        conditions[name] = {"train_draws": draws, "evaluation_draws": evaluate, "folds": details,
                            "summary": summarize(ids, rows, d, t, evaluate, spec),
                            "per_question": rows}
    averages = {c: average_screen(ids, conditions, c, spec) for c in CANDIDATES}
    return {"conditions": conditions, "average_vs_confidence": averages,
            "historical_actions_verified": primary is not None,
            "primary_reading": "pass" if averages[spec["primary_candidate"]]["screen"]["passes"]
            else "fail"}


def descriptive(features, z, d, t, spec=SPEC):
    gain = t[:, :, 0] - d[:, :, 0] - spec["lambda"] * t[:, :, 1] / 1000
    events = {"incorrect_direct": (d[:, :, 0] == 0).ravel(), "positive_gain": (gain > 0).ravel()}
    scores = {"negative_recorded_confidence": -z[:, :, 0], "negative_raw_mean": -features[..., 9],
              "negative_min_token": -features[..., 0], "negative_quantile_0.05": -features[..., 1],
              "negative_quantile_0.1": -features[..., 2],
              "negative_quantile_0.25": -features[..., 3],
              "negative_median": -features[..., 4]}
    auroc = {name: {event: float(roc_auc_score(labels, score.ravel()))
                    if 0 < labels.sum() < labels.size else None
                    for event, labels in events.items()} for name, score in scores.items()}
    length = features[..., 10].ravel()
    return {"pooled_auroc": auroc, "spearman_with_log_length": {
        "recorded_confidence": float(spearmanr(z[:, :, 0].ravel(), length).statistic),
        "min_token": float(spearmanr(features[..., 0].ravel(), length).statistic)},
        "note": "descriptive pooled values over 400 reused states; no interval"}


def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(payload), stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked_output():
    if OUTPUT.is_symlink() or OUTPUT.resolve() != BASE.resolve() / SPEC["version"]:
        raise ValueError("Only the separate token-deferral directory is writable")


def sources():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def packages():
    return {name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "scikit-learn", "torch", "transformers")}


def checked_plan():
    plan = verified(OUTPUT / "plan.json")
    if plan["spec"] != SPEC:
        raise ValueError("Token-deferral spec changed")
    if plan["source_file_sha256"] != sources():
        raise ValueError("Frozen token-deferral source changed")
    if plan["packages"] != packages():
        raise ValueError("Frozen token-deferral environment changed")
    return plan


def prepare():
    checked_output()
    from scripts.repeat_cpu_feasibility import load_panel
    panel = load_panel(REPEAT)
    plan = {"spec": SPEC, "inputs": {"panel": panel["identity"], "study": str(REPEAT)},
            "source_file_sha256": sources(), "packages": packages(),
            "no_generation_scoring_references": True}
    write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "plan_sha256": digest(plan)}


def extract():
    checked_output()
    plan = checked_plan()
    if any((OUTPUT / name).exists() for name in ("token-logprobs.json", "extraction-report.json")):
        raise ValueError("Extraction already completed; it is not restarted")
    from reasoning_budget.backend import make_backend
    from reasoning_budget.config import load_config
    protocol, questions, drafts = direct_drafts(REPEAT)
    engine = make_backend(load_config(REPEAT / "config.yaml"))
    recorded = protocol["snapshot"]["identity"]["backend"]
    differing = sorted(key for key in set(recorded) | set(engine.metadata)
                       if recorded.get(key) != engine.metadata.get(key))
    if differing:
        raise ValueError(f"Backend metadata differs from collection: {differing}")
    decoder = engine.generation_configs["direct"]
    engine.load()
    started, rows = time.monotonic(), []
    for record in drafts:
        job, result = record["job"], record["result"]
        answer = list((result.get("metadata") or {}).get("answer_token_ids") or [])
        if not answer:
            raise ValueError(f"Missing recorded answer token IDs: {job['id']}")
        prefix = prompt_ids(engine, questions[job["question_id"]]["prompt"])
        raw, top_values, top_indices = teacher_force(engine, prefix, answer, decoder.top_k)
        warped = warped_logprobs(top_values, top_indices, answer,
                                 decoder.temperature, decoder.top_p)
        finite = np.isfinite(warped)
        decoded = engine.tokenizer.decode(answer, skip_special_tokens=True).strip()
        rows.append({"job_id": job["id"], "question_id": job["question_id"],
                     "sample": job["sample"], "answer_tokens": len(answer),
                     "recorded_answer_tokens": result["answer_tokens"],
                     "prompt_tokens": len(prefix),
                     "recorded_prompt_tokens": result["prompt_tokens"],
                     "decoded_matches": decoded == result["final_answer"]
                     or result["termination"] == "reasoning_in_answer",
                     "raw_logprobs": [float(v) for v in raw], "raw_mean": float(raw.mean()),
                     "recorded_raw_mean": result.get("mean_generated_logprob_raw"),
                     "warped_mean": float(warped.mean()) if finite.all() else None,
                     "warped_support_misses": int((~finite).sum()),
                     "recorded_warped_mean": result["mean_generated_logprob"]})
    seconds = time.monotonic() - started
    payload = {"plan_sha256": digest(plan), "drafts": rows}
    write_new(OUTPUT / "token-logprobs.json", payload)
    report = {"plan_sha256": digest(plan), "token_logprobs_sha256": digest(payload),
              "fidelity": fidelity(rows), "forward_pass_seconds": seconds,
              "backend_metadata_sha256": digest(engine.metadata),
              "decoder": {"temperature": decoder.temperature, "top_k": decoder.top_k,
                          "top_p": decoder.top_p},
              "no_generation_scoring_references": True}
    write_new(OUTPUT / "extraction-report.json", report)
    return {"passed": report["fidelity"]["passed"], "checks": report["fidelity"]["checks"],
            "raw_mean_abs_difference": report["fidelity"]["raw_mean_abs_difference"],
            "forward_pass_seconds": round(seconds, 1)}


def fmt(value, digits=4):
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(v, digits) for v in value) + "]"
    return f"{value:+.{digits}f}" if isinstance(value, float) else str(value)


def markdown(report):
    stats, fid = report["statistics"], report["extraction_fidelity"]
    raw = fid["raw_mean_abs_difference"] or {}
    lines = ["# Token-level deferral check", "",
             "Post-hoc, exploratory, reused development data. See "
             "`docs/token-deferral-protocol.md`.", "",
             f"Extraction fidelity: **{'passed' if fid['passed'] else 'failed'}**. Recomputed "
             f"pre-warper mean versus recorded: median absolute difference "
             f"{fmt(raw.get('median'), 6)}, maximum {fmt(raw.get('max'), 6)}; share within "
             f"tolerance {fmt(fid['raw_mean_share_within_tolerance'], 4)}. Post-warper support "
             f"misses: {fid['warped_support_misses']} tokens in "
             f"{fid['drafts_with_warped_support_misses']} drafts.", "",
             f"Primary reading (learned error score): **{stats['primary_reading']}**.", "",
             "| Rule | Mean utility difference vs confidence [90%] | A→B | B→A | "
             "Leave-one-out all positive | Accuracy | Tokens/state |",
             "|---|---|---:|---:|---|---:|---:|"]
    for name in CANDIDATES:
        a = stats["average_vs_confidence"][name]
        directions = a["directions"]
        lines.append(f"| {name} | {fmt(a['mean'], 6)} {fmt(a['ci90'], 6)} | "
                     f"{fmt(directions['k4_A_to_B'], 6)} | {fmt(directions['k4_B_to_A'], 6)} | "
                     f"{a['screen']['all_leave_one_question_out_positive']} | "
                     f"{a['accuracy']:.4f} | {a['tokens']:.2f} |")
    first = stats["average_vs_confidence"][CANDIDATES[0]]
    full8 = stats["conditions"]["k8_full"]["summary"]
    lines += [f"| confidence (comparator) | reference | | | | {first['confidence_accuracy']:.4f} | "
              f"{first['confidence_tokens']:.2f} |", "",
              "Secondary eight-draw condition, mean difference vs confidence: " + "; ".join(
                  f"{name} {fmt(full8[name]['delta_vs_confidence']['mean'], 6)}"
                  for name in CANDIDATES) + ".", "",
              "| Score (higher = more likely to escalate) | AUROC, incorrect direct | "
              "AUROC, positive gain |", "|---|---:|---:|"]
    for name, values in stats["descriptive"]["pooled_auroc"].items():
        lines.append(f"| {name} | {fmt(values['incorrect_direct'], 4)} | "
                     f"{fmt(values['positive_gain'], 4)} |")
    rho = stats["descriptive"]["spearman_with_log_length"]
    lines += ["", f"Spearman with log answer length: recorded confidence "
              f"{fmt(rho['recorded_confidence'], 4)}; minimum token {fmt(rho['min_token'], 4)}. "
              "Descriptive pooled values without intervals.", ""]
    return "\n".join(lines) + "\n"


def execute():
    checked_output()
    plan = checked_plan()
    if (OUTPUT / "report.json").exists():
        raise ValueError("Analysis already completed; it is not restarted")
    extraction = verified(OUTPUT / "extraction-report.json")
    tokens = verified(OUTPUT / "token-logprobs.json")
    if (extraction["plan_sha256"] != digest(plan) or tokens["plan_sha256"] != digest(plan)
            or extraction["token_logprobs_sha256"] != digest(tokens)):
        raise ValueError("Extraction outputs do not match the frozen plan")
    if not extraction["fidelity"]["passed"]:
        raise ValueError("Token extraction failed its fidelity gate; analysis is not run")
    from scripts.repeat_cpu_feasibility import load_panel
    from scripts.verify_phase2_repeat import verify
    panel = load_panel(REPEAT)
    if {"panel": panel["identity"], "study": str(REPEAT)} != plan["inputs"]:
        raise ValueError("Frozen repeat panel inputs changed")
    features, recorded = feature_tensor(panel["ids"], tokens["drafts"],
                                        direct_job_ids(panel["rows"]))
    if not np.array_equal(recorded, panel["z"][..., 0]):
        raise ValueError("Recorded confidence differs between extraction and panel")
    data = (panel["ids"], panel["q"], panel["d"], panel["t"], panel["z"], panel["folds"])
    statistics = analyze(data, features, panel["primary"])
    statistics["descriptive"] = descriptive(features, panel["z"], panel["d"], panel["t"])
    preservation = verify(REPEAT)
    report = {"plan_sha256": digest(plan), "spec": SPEC, "inputs": plan["inputs"],
              "extraction_report_sha256": digest(extraction),
              "extraction_fidelity": extraction["fidelity"], "statistics": statistics,
              "protected_originals_verified": preservation["protected_originals_verified"],
              "no_generation_scoring_references": True, "cloud_spend_usd": 0.0}
    write_new(OUTPUT / "report.json", report)
    with (OUTPUT / "report.md").open("x") as stream:
        stream.write(markdown(report))
    return {"report_sha256": digest(report), "primary_reading": statistics["primary_reading"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "extract", "execute"])
    args = parser.parse_args()
    print({"prepare": prepare, "extract": extract, "execute": execute}[args.command]())


if __name__ == "__main__":
    main()
