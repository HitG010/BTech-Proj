"""Exploratory nested question-level CV on a complete, previously scored pilot.

No generator is invoked. DART-SC-2 is an explicitly limited two-draft adaptation,
not a reproduction of DART's default third draft or budget-probing stage.
"""

import csv
import platform
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold

from .controller import choose_modes, feature_matrix, fit_controller
from .data import check_questions
from .records import Question
from .runner import _usage, load_run
from .scoring import SCORING_VERSION, parse_answer
from .storage import atomic_json, digest, envelope, read_json, run_lock

LAMBDAS = (0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
SEED = 20260917


def load_pilot(run_dir):
    manifest, records = load_run(run_dir)
    config = manifest["identity"]["config"]
    if config["split"] != "pilot" or config["samples"] != 2:
        raise ValueError("Exploratory routing requires a two-sample pilot; test is sealed")
    questions = [Question(**q) for q in manifest["identity"]["questions"]]
    if any(q.split != "pilot" for q in questions):
        raise ValueError("Only pilot questions may enter exploratory cross-validation")
    check_questions(questions)
    artifact = read_json(Path(run_dir) / "scores.json")
    if (
        artifact["records_sha256"] != digest(records)
        or artifact["run_id"] != manifest["run_id"]
        or artifact["scoring_version"] != SCORING_VERSION
        or artifact["gold_sha256"] != manifest["scoring_gold_sha256"]
    ):
        raise ValueError("Stale scores: run rb score on this run first")
    scores = {s["job_id"]: s for s in artifact["scores"]}
    index = {q.id: i for i, q in enumerate(questions)}
    # Dimensions question, mode, repeated generation. Columns mean accuracy/tokens/seconds.
    correctness = np.empty((len(questions), 2, 2))
    tokens, seconds = np.empty_like(correctness), np.empty_like(correctness)
    confidence = np.empty((len(questions), 2))
    answers = [[None, None] for _ in questions]
    seen = set()
    for record in records:
        job = record["job"]
        if record["status"] != "completed":
            raise ValueError("Every expected pilot response must be complete before routing")
        mode = {"direct": 0, "thinking": 1}[job["mode"]]
        i, s = index[job["question_id"]], job["sample"]
        key = i, mode, s
        if s not in (0, 1) or key in seen:
            raise ValueError("Duplicate or unsupported sample in pilot")
        seen.add(key)
        result = record["result"]
        correctness[key] = scores[job["id"]]["correct"]
        tokens[key] = sum(
            result[k] for k in ["reasoning_tokens", "answer_tokens", "inserted_tokens"]
        )
        seconds[key] = result["elapsed_seconds"]
        if mode == 0:
            value = result["mean_generated_logprob"]
            if value is None or not np.isfinite(value):
                raise ValueError("Confidence routing requires finite saved direct log-probability")
            confidence[i, s] = value
            answers[i][s] = parse_answer(
                result["final_answer"], incomplete=result["answer_truncated"]
            )[0]
    if len(seen) != len(questions) * 4 or len(scores) != len(seen):
        raise ValueError("Incomplete or duplicated score/response matrix")
    return (
        manifest,
        questions,
        {
            "accuracy": correctness,
            "tokens": tokens,
            "seconds": seconds,
            "confidence": confidence,
            "agreement": np.array([a is not None and a == b for a, b in answers]),
            "source_records_sha256": digest(records),
            "scores_sha256": digest(artifact),
        },
    )


def outcomes(data, modes):
    """Question-only routing: one selected generation per question/sample."""
    ids = np.arange(len(modes))
    return np.column_stack(
        [data[k][ids, modes].mean(axis=1) for k in ["accuracy", "tokens", "seconds"]]
    )


def escalation(data, escalate, two_drafts=False):
    """Both probe and escalation costs count, including inserted closure tokens."""
    escalate = np.asarray(escalate, dtype=bool)
    if escalate.shape != data["confidence"].shape:
        raise ValueError("Escalation decisions must align with direct samples")
    acc = np.where(escalate, data["accuracy"][:, 1], data["accuracy"][:, 0]).mean(1)
    result = [acc]
    for key in ["tokens", "seconds"]:
        probe = data[key][:, 0]
        if two_drafts:
            # Averaging the two possible first-draft orders is NOT two independent trials.
            probe = np.repeat(probe.sum(axis=1, keepdims=True), 2, axis=1)
        result.append((probe + escalate * data[key][:, 1]).mean(1))
    return np.column_stack(result)


def confidence_threshold(data, training_ids, cost_preference):
    """Train threshold on outer-training responses only; never tune on evaluation outcomes."""
    values = data["confidence"][training_ids].ravel()
    candidates = [float(values.min() - 1), *np.unique(values).tolist(), float(values.max() + 1)]
    best, best_utility = candidates[0], -np.inf
    for threshold in candidates:
        rows = escalation(data, data["confidence"] < threshold)[training_ids]
        utility = np.mean(rows[:, 0] - cost_preference * rows[:, 1] / 1000)
        if utility > best_utility:
            best, best_utility = threshold, utility
    return best


def cross_validate(x, data, question_ids, seed=SEED):
    """Each outer fold gets its own training-only scaler, alpha tuning, and thresholds."""
    n = len(x)
    if n < 10 or len(set(question_ids)) != n:
        raise ValueError("Need at least ten unique questions")
    y = np.column_stack([data["accuracy"].mean(2), data["tokens"].mean(2)])
    predictions = np.empty((n, 4))
    confidence_decisions = np.empty((len(LAMBDAS), n, 2), dtype=bool)
    folds = []
    started = time.perf_counter()
    for fold, (train, test) in enumerate(KFold(5, shuffle=True, random_state=seed).split(x)):
        controller = fit_controller(x[train], y[train], seed + fold)
        predictions[test] = controller.predict(x[test])
        thresholds = []
        for j, preference in enumerate(LAMBDAS):
            threshold = confidence_threshold(data, train, preference)
            confidence_decisions[j, test] = data["confidence"][test] < threshold
            thresholds.append(threshold)
        folds.append(
            {
                "fold": fold,
                "train_ids": [question_ids[i] for i in train],
                "evaluation_ids": [question_ids[i] for i in test],
                "controller": controller.to_dict(),
                "confidence_thresholds": thresholds,
            }
        )
    policies = []
    direct = outcomes(data, np.zeros(n, dtype=int))
    thinking = outcomes(data, np.ones(n, dtype=int))
    policies.extend([("always-direct", None, direct), ("always-thinking", None, thinking)])
    for probability in np.linspace(0, 1, 11):
        policies.append(
            (
                "random-expected",
                float(probability),
                (1 - probability) * direct + probability * thinking,
            )
        )
    for j, preference in enumerate(LAMBDAS):
        policies.append(
            ("MiniLM-ridge", preference, outcomes(data, choose_modes(predictions, preference)))
        )
        policies.append(("confidence", preference, escalation(data, confidence_decisions[j])))
    disagree = np.repeat((~data["agreement"])[:, None], 2, axis=1)
    policies.append(("DART-SC-2-adapted", None, escalation(data, disagree, two_drafts=True)))
    return {
        "policies": policies,
        "folds": folds,
        "predictions": predictions.tolist(),
        "fit_and_replay_seconds": time.perf_counter() - started,
    }


def summarize(policies, seed=SEED):
    direct, thinking = policies[0][2], policies[1][2]
    n = len(direct)
    draws = np.random.default_rng(seed).integers(0, n, size=(2000, n))
    direct_boot, thinking_boot = direct[draws].mean(1), thinking[draws].mean(1)
    summaries = []
    for name, parameter, rows in policies:
        mean, boot = rows.mean(0), rows[draws].mean(1)
        ci = np.quantile(boot[:, 0], [0.025, 0.975]).tolist()
        lower_cost, higher_cost = direct[:, 1].mean(), thinking[:, 1].mean()
        fraction = (mean[1] - lower_cost) / (higher_cost - lower_cost)
        advantage, advantage_ci = None, None
        if 0 <= fraction <= 1:
            advantage = float(
                mean[0] - ((1 - fraction) * direct[:, 0].mean() + fraction * thinking[:, 0].mean())
            )
            p = (boot[:, 1] - direct_boot[:, 1]) / (thinking_boot[:, 1] - direct_boot[:, 1])
            # No extrapolation beyond feasible random mixture in each bootstrap draw.
            valid = (p >= 0) & (p <= 1)
            if valid.sum() >= 1900:
                diff = boot[valid, 0] - (
                    (1 - p[valid]) * direct_boot[valid, 0] + p[valid] * thinking_boot[valid, 0]
                )
                advantage_ci = np.quantile(diff, [0.025, 0.975]).tolist()
        summaries.append(
            {
                "policy": name,
                "parameter": parameter,
                "accuracy": float(mean[0]),
                "accuracy_ci95": ci,
                "mean_charged_tokens": float(mean[1]),
                "mean_cached_generation_seconds": float(mean[2]),
                "accuracy_advantage_over_cost_matched_random": advantage,
                "advantage_ci95": advantage_ci,
            }
        )
    return summaries


def explore(run_dir, output="artifacts/routing", seed=SEED, progress=print):
    manifest, questions, data = load_pilot(run_dir)
    source_hash = digest(
        {p.name: p.read_text() for p in [Path(__file__), Path(__file__).with_name("controller.py")]}
    )
    identity = {
        "source_run": manifest["run_id"],
        "records": data["source_records_sha256"],
        "scores": data["scores_sha256"],
        "implementation": source_hash,
        "seed": seed,
        "lambdas": list(LAMBDAS),
        "outer_folds": 5,
        "inner_folds": 4,
        "scope": "exploratory pilot only; no official test evaluation",
        "packages": {
            name: version(name)
            for name in ["torch", "transformers", "tokenizers", "numpy", "scikit-learn"]
        },
    }
    destination = Path(output) / digest(identity)[:20]
    with run_lock(destination):
        x, feature_metadata = feature_matrix(questions, progress=progress)
        progress("Fitting five outer folds; alpha tuning stays inside each training fold")
        result = cross_validate(x, data, [q.id for q in questions], seed)
        summaries = summarize(result["policies"], seed)
        cache_tokens, cache_seconds = _usage(Path(run_dir))
        import sklearn

        payload = {
            "identity": identity,
            "features": feature_metadata,
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "sklearn": sklearn.__version__,
            },
            "folds": result["folds"],
            "out_of_fold_predictions": result["predictions"],
            "question_ids": [q.id for q in questions],
            "summaries": summaries,
            "fit_and_replay_seconds": result["fit_and_replay_seconds"],
            "historical_cache_expenditure": {
                "charged_tokens": cache_tokens,
                "elapsed_seconds_including_setup": cache_seconds,
                "new_qwen_generations_this_study": 0,
            },
            "per_question_policies": [
                {"policy": name, "parameter": p, "rows": rows.tolist()}
                for name, p, rows in result["policies"]
            ],
        }
        atomic_json(destination / "study.json", envelope(payload))
        for fold in result["folds"]:
            atomic_json(
                destination / f"controller-fold-{fold['fold']}.json",
                envelope(
                    {
                        "controller": fold["controller"],
                        "train_ids": fold["train_ids"],
                        "evaluation_ids": fold["evaluation_ids"],
                        "study_identity": identity,
                        "status": "exploratory fold model; not a final frozen test policy",
                    }
                ),
            )
        with (destination / "curve.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
            writer.writeheader()
            writer.writerows(summaries)
        _report(destination, summaries, feature_metadata, len(questions))
    return destination


def _report(destination, summaries, feature_metadata, count):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for name in dict.fromkeys(s["policy"] for s in summaries):
        rows = [s for s in summaries if s["policy"] == name]
        ax.plot(
            [s["mean_charged_tokens"] for s in rows],
            [s["accuracy"] * 100 for s in rows],
            "o--" if name == "random-expected" else "o-",
            label=name,
            markersize=4,
        )
    ax.set(
        xlabel="Charged output tokens per question (all probes included)",
        ylabel="Accuracy (%)",
        title=f"Exploratory pilot routing: {count} questions, nested CV",
    )
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(destination / "accuracy-cost.png", dpi=180)
    plt.close(fig)
    lines = [
        "# Exploratory routing learnability",
        "",
        "Pilot reuse with five outer question folds and four inner alpha-tuning folds. "
        "No official training, validation, or test questions were used. Human scoring "
        "audit is pending; protocol was selected on part of this pilot. This is not "
        "confirmatory evidence or a final test result.",
        "",
        "Ridge predicts four targets from frozen MiniLM and three lexical features. "
        "Each outer fold standardizes and selects alphas using its training questions only. "
        "Lambda is accuracy probability lost per 1,000 charged output tokens. "
        "The predeclared grid is shown in full; do not select a winner on these outcomes.",
        "",
        "Random is the exact expected mixture, without simulation noise. Confidence "
        "thresholds optimize training utility and use saved decoder-warped direct "
        "log-probabilities. Escalation costs include both direct and thinking calls.",
        "",
        "DART-SC-2-adapted uses two direct drafts, accepts only matching valid numeric "
        "answers, and otherwise escalates. Both first-draft orders are averaged within "
        "each question; these are correlated, not extra independent samples. "
        "K_init=K_max=2; fixed local 2,048 reasoning/512 answer caps. This omits the "
        "reference default third draft and DART budget probing, and uses our strict parser. "
        "It is a stage-one adaptation, not full DART. "
        "Reference: https://github.com/js-lee-AI/DART",
        "",
        "Intervals resample whole questions, pairing all policies and both samples. "
        "They are descriptive conditional on saved out-of-fold predictions; they do not "
        "refit models, capture training instability, or correct grid multiplicity. "
        "Cost-matched random comparisons are interpolated only inside feasible costs. "
        "Token costs include forced marker insertion but exclude input/prefill tokens. "
        "Cached generation latency includes prefill and closure processing; it is replay "
        "accounting, not measured deployed policy latency.",
        "",
        f"CPU embedding cold load: {feature_metadata['load_seconds']:.2f}s; "
        f"encoding all questions: {feature_metadata['encode_seconds']:.2f}s. "
        "Router CPU overhead is separate from the plotted Qwen token costs. "
        "No new Qwen generations or cloud expenditure.",
        "",
        "| Policy | Parameter | Accuracy | Tokens/question | Advantage over matched random |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summaries:
        gap = row["accuracy_advantage_over_cost_matched_random"]
        text = "outside cost range" if gap is None else f"{100 * gap:+.2f} pp"
        lines.append(
            f"| {row['policy']} | {row['parameter']} | {100 * row['accuracy']:.1f}% | "
            f"{row['mean_charged_tokens']:.1f} | {text} |"
        )
    lines += [
        "",
        "![Accuracy–cost curve](accuracy-cost.png)",
        "",
        "Next: finish the 50-response human audit; use disjoint training/validation "
        "data to freeze policies and preferences; evaluate once on the sealed test set. "
        "A negative pilot result does not establish unlearnability from larger data.",
    ]
    (destination / "report.md").write_text("\n".join(lines) + "\n")
