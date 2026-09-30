"""CPU-only development comparison for a shared-correctness continuation router.

Run with ``python -m reasoning_budget.router_dev``. This module does not alter the
frozen continuation study or read its already-inspected diagnostic outcomes.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold

from . import probe, probe_study
from .controller import feature_matrix
from .data import check_questions
from .records import Question
from .reporting import bootstrap
from .storage import atomic_json, digest, envelope, verified
from .stronger import fit_transform, transform

SEED = 20260923
DEFAULT_SOURCE = "artifacts/probe/continuation-v1"
DEFAULT_OUTPUT = "artifacts/router-dev/shared-base-v1"
PREFERENCE = 0.05
OUTER_FOLDS = 5
INNER_FOLDS = 3
SHARED_SETTINGS = [
    {"features": features, "C": c, "shrinkage": shrinkage, "cost_alpha": 10}
    for features in ("response", "question_response")
    for c in (0.1, 1.0)
    for shrinkage in (10, 30)
]


def _binary_fit(z, labels, c, *, shrinkage=0):
    """Fit a Bernoulli head; rare conditional events shrink to a Beta(1,1) rate."""
    labels = np.asarray(labels, dtype=int)
    if len(labels) != len(z) or not np.isin(labels, [0, 1]).all():
        raise ValueError("Binary labels and features must align")
    positives = int(labels.sum())
    negatives = len(labels) - positives
    prior = (positives + 1) / (len(labels) + 2)
    head = {
        "prior": prior,
        "weight": 0.0,
        "coef": None,
        "intercept": None,
        "positives": positives,
        "negatives": negatives,
    }
    minority = min(positives, negatives)
    if minority >= 5:
        classifier = LogisticRegression(C=c, max_iter=3000).fit(z, labels)
        if classifier.n_iter_[0] >= 3000:
            raise ValueError("Shared-router classifier did not converge")
        head.update(
            weight=1.0 if shrinkage == 0 else minority / (minority + shrinkage),
            coef=classifier.coef_[0].tolist(),
            intercept=float(classifier.intercept_[0]),
        )
    return head


def _binary_predict(head, z):
    if head["coef"] is None:
        return np.full(len(z), head["prior"])
    fitted = expit(z @ np.asarray(head["coef"]) + head["intercept"])
    return head["weight"] * fitted + (1 - head["weight"]) * head["prior"]


def fit_shared(x, rows, setting):
    """Labels and counterfactual outcomes enter fitting only, never prediction."""
    if setting not in SHARED_SETTINGS:
        raise ValueError("Unknown shared-router setting")
    x = np.asarray(x, dtype=float)
    rows = np.asarray(rows, dtype=float)
    if x.ndim != 2 or rows.shape != (len(x) // 2, 2, 3, 3) or len(x) % 2:
        raise ValueError("Expected two linked first-draft states per question")
    if not np.isfinite(x).all() or not np.isfinite(rows).all():
        raise ValueError("Non-finite shared-router training data")
    raw = x[:, -4:] if setting["features"] == "response" else x
    z, state = fit_transform(raw, None if setting["features"] == "response" else 16)
    outcomes = rows.reshape(-1, 3, 3)
    first = outcomes[:, 0, 0].astype(int)
    if not np.isin(outcomes[:, :, 0], [0, 1]).all():
        raise ValueError("Correctness outcomes must be binary")
    base = _binary_fit(z, first, setting["C"])
    heads = []
    for action in (1, 2):
        later = outcomes[:, action, 0].astype(int)
        rescue = _binary_fit(
            z[first == 0],
            later[first == 0],
            setting["C"],
            shrinkage=setting["shrinkage"],
        )
        harm = _binary_fit(
            z[first == 1],
            1 - later[first == 1],
            setting["C"],
            shrinkage=setting["shrinkage"],
        )
        extra = outcomes[:, action, 1] - outcomes[:, 0, 1]
        if (extra <= 0).any():
            raise ValueError("Continuation must charge positive additional tokens")
        cost = Ridge(alpha=setting["cost_alpha"], solver="svd").fit(z, extra)
        heads.append(
            {
                "rescue": rescue,
                "harm": harm,
                "cost_coef": cost.coef_.tolist(),
                "cost_intercept": float(cost.intercept_),
            }
        )
    return {"setting": setting, "transform": state, "first_correct": base, "heads": heads}


def shared_predictions(model, x):
    """Return one p(first correct), action gains/costs and conditional rates."""
    x = np.asarray(x, dtype=float)
    raw = x[:, -4:] if model["setting"]["features"] == "response" else x
    z = transform(raw, model["transform"])
    first = _binary_predict(model["first_correct"], z)
    gains, costs, rescues, harms = [], [], [], []
    for head in model["heads"]:
        rescue = _binary_predict(head["rescue"], z)
        harm = _binary_predict(head["harm"], z)
        rescues.append(rescue)
        harms.append(harm)
        gains.append((1 - first) * rescue - first * harm)
        costs.append(np.maximum(1, z @ head["cost_coef"] + head["cost_intercept"]))
    return {
        "first_correct": first,
        "rescue": np.column_stack(rescues),
        "harm": np.column_stack(harms),
        "gain": np.column_stack(gains),
        "cost": np.column_stack(costs),
    }


def shared_actions(model, x, preference=PREFERENCE):
    if not np.isfinite(preference) or preference < 0:
        raise ValueError("Preference must be finite and nonnegative")
    predicted = shared_predictions(model, x)
    value = predicted["gain"] - preference * predicted["cost"] / 1000
    return np.argmax(np.column_stack([np.zeros(len(x)), value]), axis=1)


def question_folds(roles, n_splits, seed):
    """Split question indices; callers expand each index to its two orientations."""
    roles = np.asarray(roles)
    if roles.ndim != 1 or len(roles) < n_splits or n_splits < 2:
        raise ValueError("Not enough questions for grouped folds")
    return list(
        StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(
            np.zeros(len(roles)), roles
        )
    )


def _states(x, question_indices):
    return x[question_indices].reshape(-1, x.shape[-1])


def _fit_family(name, x, rows, setting):
    if name == "shared":
        return fit_shared(x, rows, setting)
    return probe.fit(x, rows, setting, kind=name)


def _family_actions(name, model, x, preference=PREFERENCE):
    return (
        shared_actions(model, x, preference)
        if name == "shared"
        else probe.actions(model, x, preference)
    )


def select_setting(name, x, rows, roles, *, seed):
    """Tune on training questions only; every inner fold holds out whole questions."""
    settings = SHARED_SETTINGS if name == "shared" else probe.SETTINGS
    folds = question_folds(roles, INNER_FOLDS, seed)
    scores = []
    for setting in settings:
        total = 0.0
        count = 0
        for train, validation in folds:
            model = _fit_family(name, _states(x, train), rows[train], setting)
            actions = _family_actions(name, model, _states(x, validation))
            selected = probe.selected_rows(rows[validation], actions)
            utility = selected[:, 0] - PREFERENCE * selected[:, 1] / 1000
            total += float(utility.sum())
            count += len(validation)
        scores.append(total / count)
    best = int(np.argmax(scores))
    return settings[best], scores


def load_development(source=DEFAULT_SOURCE, progress=print):
    """Read only the frozen pilot and validation roles, with source checksums."""
    protocol = probe_study.read_protocol(source)
    loaded, sources, question_features = {}, {}, {}
    for role in ("train", "tune"):
        data, source_hashes, _ = probe_study.read_sources(
            protocol["source_paths"][role], expected=protocol["development"][role]
        )
        if source_hashes != protocol["sources"][role]:
            raise ValueError("Development source differs from frozen study")
        loaded[role] = data
        sources[role] = source_hashes
        question_features[role], _ = feature_matrix(
            [Question(**q) for q in data["questions"]], progress=progress
        )
    questions = loaded["train"]["questions"] + loaded["tune"]["questions"]
    check_questions([Question(**q) for q in questions])
    x = np.concatenate(
        [
            probe.state_features(question_features[role], loaded[role]["direct_results"]).reshape(
                len(loaded[role]["questions"]), 2, -1
            )
            for role in ("train", "tune")
        ]
    )
    rows = np.concatenate([probe.continuation_rows(loaded[role]) for role in ("train", "tune")])
    roles = [role for role in ("train", "tune") for _ in loaded[role]["questions"]]
    return questions, np.asarray(roles), x, rows, {"protocol": digest(protocol), "sources": sources}


def evaluate(questions, roles, x, rows, *, progress=print):
    n = len(questions)
    if roles.shape != (n,) or x.shape != (n, 2, 391) or rows.shape != (n, 2, 3, 3):
        raise ValueError("Expected aligned question-grouped development data")
    if len({q["id"] for q in questions}) != n:
        raise ValueError("Duplicate question IDs")
    names = ("shared", "joint", "gain-ridge", "confidence-continuation")
    preferences = tuple(probe.PREFERENCES)
    primary_index = preferences.index(PREFERENCE)
    observed = {name: np.full((n, 3), np.nan) for name in names}
    curve_rows = {name: np.full((len(preferences), n, 3), np.nan) for name in names}
    actions_out = {name: np.full((n, 2), -1, dtype=int) for name in names}
    fold_ids = np.full(n, -1, dtype=int)
    selected_settings = []
    p0 = np.full((n, 2), np.nan)
    rescue = np.full((n, 2, 2), np.nan)
    harm = np.full((n, 2, 2), np.nan)
    for fold, (train, test) in enumerate(question_folds(roles, OUTER_FOLDS, SEED)):
        if np.intersect1d(train, test).size or (fold_ids[test] != -1).any():
            raise ValueError("Question fold overlap")
        progress(f"CPU router development: fold {fold + 1}/{OUTER_FOLDS}")
        fold_ids[test] = fold
        row = {
            "fold": fold,
            "train_questions": len(train),
            "held_out_questions": len(test),
            "settings": {},
        }
        for name in ("shared", "joint", "gain-ridge"):
            setting, inner_scores = select_setting(
                name, x[train], rows[train], roles[train], seed=SEED + fold + 1
            )
            model = _fit_family(name, _states(x, train), rows[train], setting)
            for p_index, preference in enumerate(preferences):
                actions = _family_actions(name, model, _states(x, test), preference)
                curve_rows[name][p_index, test] = probe.selected_rows(rows[test], actions)
                if p_index == primary_index:
                    observed[name][test] = curve_rows[name][p_index, test]
                    actions_out[name][test] = actions.reshape(-1, 2)
            row["settings"][name] = {"chosen": setting, "inner_utility": inner_scores}
            if name == "shared":
                predicted = shared_predictions(model, _states(x, test))
                p0[test] = predicted["first_correct"].reshape(-1, 2)
                rescue[test] = predicted["rescue"].reshape(-1, 2, 2)
                harm[test] = predicted["harm"].reshape(-1, 2, 2)
        for p_index, preference in enumerate(preferences):
            confidence = probe.select_confidence(
                _states(x, train)[:, -4], rows[train], preference, allowed=(1, 2)
            )
            actions = probe.confidence_actions(_states(x, test)[:, -4], confidence)
            curve_rows["confidence-continuation"][p_index, test] = probe.selected_rows(
                rows[test], actions
            )
            if p_index == primary_index:
                observed["confidence-continuation"][test] = curve_rows["confidence-continuation"][
                    p_index, test
                ]
                actions_out["confidence-continuation"][test] = actions.reshape(-1, 2)
                row["settings"]["confidence-continuation"] = confidence
        selected_settings.append(row)
    if (
        (fold_ids < 0).any()
        or any(not np.isfinite(value).all() for value in observed.values())
        or any(not np.isfinite(value).all() for value in curve_rows.values())
    ):
        raise ValueError("Out-of-fold result incomplete")
    base = {
        "always-direct": rows[:, :, 0].mean(axis=1),
        "always-thinking": rows[:, :, 2].mean(axis=1),
        "DART-SC-2-adapted": rows[:, :, 1].mean(axis=1),
    }
    all_policies = base | observed
    curve = []
    for name in all_policies:
        for p_index, preference in enumerate(preferences):
            values = base[name] if name in base else curve_rows[name][p_index]
            mean = values.mean(axis=0)
            curve.append(
                {
                    "policy": name,
                    "preference": preference,
                    "accuracy": float(mean[0]),
                    "charged_tokens_per_question": float(mean[1]),
                    "cached_generation_seconds_per_question": float(mean[2]),
                    "utility": float(mean[0] - preference * mean[1] / 1000),
                }
            )
    curve_pairwise = []
    for p_index, preference in enumerate(preferences):
        shared = curve_rows["shared"][p_index]
        confidence = curve_rows["confidence-continuation"][p_index]
        delta = (shared[:, 0] - preference * shared[:, 1] / 1000) - (
            confidence[:, 0] - preference * confidence[:, 1] / 1000
        )
        curve_pairwise.append(
            {
                "preference": preference,
                "shared_minus_confidence_utility": float(delta.mean()),
                "paired_question_bootstrap_ci95": bootstrap(delta, SEED),
            }
        )
    summaries = {}
    utilities = {}
    for name, values in all_policies.items():
        utility = values[:, 0] - PREFERENCE * values[:, 1] / 1000
        utilities[name] = utility
        summaries[name] = {
            "accuracy": float(values[:, 0].mean()),
            "charged_tokens_per_question": float(values[:, 1].mean()),
            "cached_generation_seconds_per_question": float(values[:, 2].mean()),
            "utility": float(utility.mean()),
            "actions": None
            if name in base
            else np.bincount(actions_out[name].ravel(), minlength=3).tolist(),
        }
    comparisons = {}
    for name in (
        "gain-ridge",
        "confidence-continuation",
        "joint",
        "always-direct",
        "always-thinking",
        "DART-SC-2-adapted",
    ):
        delta = utilities["shared"] - utilities[name]
        comparisons[name] = {
            "mean_utility_difference": float(delta.mean()),
            "paired_question_bootstrap_ci95": bootstrap(delta, SEED),
        }
    outcomes = rows[:, :, :, 0].reshape(-1, 3)
    first = outcomes[:, 0].reshape(n, 2)
    calibration = {
        "first_correct_brier": float(np.mean((p0 - first) ** 2)),
        "action_conditional": {},
    }
    for action in (1, 2):
        later = outcomes[:, action].reshape(n, 2)
        wrong, correct = first == 0, first == 1
        calibration["action_conditional"][str(action)] = {
            "wrong_first_states": int(wrong.sum()),
            "rescues": int(later[wrong].sum()),
            "mean_predicted_rescue_given_wrong": float(rescue[:, :, action - 1][wrong].mean()),
            "right_first_states": int(correct.sum()),
            "harms": int((1 - later[correct]).sum()),
            "mean_predicted_harm_given_right": float(harm[:, :, action - 1][correct].mean()),
        }
    per_question = [
        {
            "id": q["id"],
            "role": str(roles[i]),
            "fold": int(fold_ids[i]),
            "policies": {name: values[i].tolist() for name, values in all_policies.items()},
            "actions": {name: actions_out[name][i].tolist() for name in names},
        }
        for i, q in enumerate(questions)
    ]
    return {
        "questions": n,
        "orientations_per_question": 2,
        "preference": PREFERENCE,
        "outer_folds": OUTER_FOLDS,
        "inner_folds": INNER_FOLDS,
        "settings": selected_settings,
        "curve": curve,
        "curve_pairwise": curve_pairwise,
        "summaries": summaries,
        "shared_minus": comparisons,
        "calibration": calibration,
        "per_question": per_question,
    }


def report_markdown(report):
    lines = [
        "# Shared-correctness router: CPU development comparison",
        "",
        "Exploratory out-of-fold replay on 200 previously used pilot/validation questions.",
        "Five question-level outer folds; three inner folds select model settings.",
        "The two first-draft orientations stay together. No diagnostic or official test",
        "question enters fitting or evaluation. One first direct generation and all",
        "requested continuations count in charged tokens. Cached generation seconds",
        "exclude encoder/router CPU time. The human scoring audit was waived.",
        "",
        "| Policy | Accuracy | Tokens/question | Utility at λ=.05 |",
        "|---|---:|---:|---:|",
    ]
    for name, row in report["summaries"].items():
        lines.append(
            f"| {name} | {row['accuracy']:.4f} | {row['charged_tokens_per_question']:.1f} "
            f"| {row['utility']:.4f} |"
        )
    lines += [
        "",
        "Shared model minus comparators (paired whole-question bootstrap;",
        "exploratory intervals after method design on these data):",
        "",
        "| Comparator | Mean utility difference | 95% interval |",
        "|---|---:|---:|",
    ]
    for name, row in report["shared_minus"].items():
        ci = row["paired_question_bootstrap_ci95"]
        lines.append(
            f"| {name} | {row['mean_utility_difference']:+.4f} | [{ci[0]:+.4f}, {ci[1]:+.4f}] |"
        )
    lines += [
        "",
        "| Held-out fold | Shared − confidence utility | Shared − gain-ridge utility |",
        "|---:|---:|---:|",
    ]
    for fold in range(report["outer_folds"]):
        questions = [q for q in report["per_question"] if q["fold"] == fold]
        differences = []
        for comparator in ("confidence-continuation", "gain-ridge"):
            values = []
            for question in questions:
                shared = question["policies"]["shared"]
                other = question["policies"][comparator]
                values.append(
                    (shared[0] - PREFERENCE * shared[1] / 1000)
                    - (other[0] - PREFERENCE * other[1] / 1000)
                )
            differences.append(float(np.mean(values)))
        lines.append(f"| {fold} | {differences[0]:+.4f} | {differences[1]:+.4f} |")
    shared = report["summaries"]["shared"]
    confidence = report["summaries"]["confidence-continuation"]
    if (
        shared["accuracy"] <= confidence["accuracy"]
        and shared["charged_tokens_per_question"] >= confidence["charged_tokens_per_question"]
    ):
        lines += [
            "",
            "On this development pool, tuned confidence weakly dominates the",
            "shared model in aggregate accuracy and generated-token cost.",
        ]
    lines += [
        "",
        f"First-correct Brier score: {report['calibration']['first_correct_brier']:.4f}.",
        "The full out-of-fold accuracy–token curve is in `curve.csv` and",
        "`accuracy-cost.png`. Learned settings were selected at λ=.05 and held",
        "fixed across the curve; confidence thresholds were fitted on each outer",
        "training fold separately for each λ.",
        "All preferences other than λ=.05 are secondary development views.",
        "",
        "| λ | Shared − confidence utility | Paired 95% interval |",
        "|---:|---:|---:|",
    ]
    for row in report["curve_pairwise"]:
        ci = row["paired_question_bootstrap_ci95"]
        lines.append(
            f"| {row['preference']:.3f} | {row['shared_minus_confidence_utility']:+.4f} "
            f"| [{ci[0]:+.4f}, {ci[1]:+.4f}] |"
        )
    lines += [
        "",
        "![Out-of-fold accuracy versus charged generated tokens](accuracy-cost.png)",
        "",
        "This comparison can select an engineering candidate but cannot confirm",
        "superiority. The already-inspected 100-question diagnostic is not a new test;",
        "the prepared 3,100-question confirmation belongs to the old router.",
        "",
    ]
    return "\n".join(lines)


def write_curve_artifacts(output, report):
    output = Path(output)
    fields = [
        "policy",
        "preference",
        "accuracy",
        "charged_tokens_per_question",
        "cached_generation_seconds_per_question",
        "utility",
    ]
    with (output / "curve.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["curve"])
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    names = list(report["summaries"])
    for name in names:
        points = [p for p in report["curve"] if p["policy"] == name]
        x = [p["charged_tokens_per_question"] for p in points]
        y = [100 * p["accuracy"] for p in points]
        if name in {"always-direct", "always-thinking", "DART-SC-2-adapted"}:
            ax.scatter(x[:1], y[:1], label=name, s=55)
        else:
            ax.plot(x, y, marker="o", markersize=3, label=name)
    ax.set(
        xlabel="Charged generated tokens per question",
        ylabel="Accuracy (%)",
        title="CPU development replay: 200 reused questions",
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "accuracy-cost.png", dpi=180)
    plt.close(fig)


def run(source=DEFAULT_SOURCE, output=DEFAULT_OUTPUT, progress=print):
    source, output = Path(source), Path(output)
    questions, roles, x, rows, sources = load_development(source, progress)
    identity = {
        "source": str(source.resolve()),
        "source_checksums": sources,
        "implementation": digest(Path(__file__).read_text()),
        "question_ids": [q["id"] for q in questions],
        "shared_settings": SHARED_SETTINGS,
        "baseline_settings": probe.SETTINGS,
        "seed": SEED,
        "preference": PREFERENCE,
        "outer_folds": OUTER_FOLDS,
        "inner_folds": INNER_FOLDS,
    }
    path = output / "report.json"
    if path.exists():
        saved = verified(path)
        if saved["identity"] != identity:
            raise ValueError("Development report identity changed; choose a new output directory")
        if not (output / "curve.csv").exists() or not (output / "accuracy-cost.png").exists():
            write_curve_artifacts(output, saved["result"])
        if not (output / "report.md").exists():
            (output / "report.md").write_text(report_markdown(saved["result"]))
        return path
    result = evaluate(questions, roles, x, rows, progress=progress)
    payload = {"identity": identity, "result": result}
    write_curve_artifacts(output, result)
    (output / "report.md").write_text(report_markdown(result))
    atomic_json(path, envelope(payload))
    return path


def main():
    parser = argparse.ArgumentParser(description="CPU-only shared router development replay")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(run(args.source, args.output))


if __name__ == "__main__":
    main()
