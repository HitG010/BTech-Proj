"""Verify cached experiment decisions and render exploratory comparison figures.

No refitting, text encoding, scoring or reference access. All writes go to a new
review directory; frozen inputs and completed experiment outputs are immutable.
"""

import os
from pathlib import Path

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, verified
from scripts.repeat_contrastive_pilot import write_new
from scripts.repeat_cpu_feasibility import load_panel
from scripts.verify_phase2_repeat import verify

ROOT = Path("artifacts/research/data-efficiency-v1")


def close(actual, expected):
    if not np.isclose(actual, expected, rtol=1e-10, atol=1e-10):
        raise ValueError(f"Cached arithmetic mismatch: {actual} versus {expected}")


def measured(d, t, actions):
    """Independent vector arithmetic from paired scored endpoint and decisions."""
    actions = np.asarray(actions)
    if actions.dtype != bool or actions.shape != d.shape[:2] or d.shape != t.shape:
        raise ValueError("Invalid paired actions")
    correct = np.where(actions, t[..., 0], d[..., 0])
    tokens = d[..., 1] + actions * t[..., 1]
    seconds = d[..., 2] + actions * t[..., 2]
    gain = t[..., 0] - d[..., 0] - .05 * t[..., 1] / 1000
    return {"accuracy": correct.mean(1), "tokens": tokens.mean(1),
            "seconds": seconds.mean(1), "utility": (correct - .05 * tokens / 1000).mean(1),
            "escalation_rate": actions.mean(1),
            "rescued": (actions & (d[..., 0] == 0) & (t[..., 0] == 1)).sum(1),
            "harmed": (actions & (d[..., 0] == 1) & (t[..., 0] == 0)).sum(1),
            "positive_gain_escalations": (actions & (gain > 0)).sum(1),
            "nonpositive_gain_escalations": (actions & (gain <= 0)).sum(1),
            "missed_positive_gains": (~actions & (gain > 0)).sum(1)}


def interval(values, seed):
    values = np.asarray(values)
    indices = np.random.default_rng(seed).integers(0, len(values), (2000, len(values)))
    return np.quantile(values[indices].mean(1), [.05, .95]).tolist()


def check_conditions(panel, stats, spec, kind):
    ids, checked = panel["ids"], 0
    for name, (train_draws, eval_draws) in spec["conditions"].items():
        condition = stats["conditions"][name]
        for detail in condition["folds"]:
            fold = detail["fold"]
            train = [qid for qid in ids if panel["folds"][qid] != fold]
            test = [qid for qid in ids if panel["folds"][qid] == fold]
            if detail["train_ids"] != train or detail["test_ids"] != test:
                raise ValueError("Frozen outer question partition differs")
            for inside in detail["inner_splits"]:
                if kind == "cpu":
                    a = {ids[i] for i in inside["training_indices"]}
                    b = {ids[i] for i in inside["validation_indices"]}
                else:
                    a, b = set(inside["train_ids"]), set(inside["validation_ids"])
                    if inside["draws"] != train_draws:
                        raise ValueError("Inner training draw boundary differs")
                if a & b or (a | b) != set(train):
                    raise ValueError("Inner question partition leaks or loses groups")
            if kind == "cpu":
                selected = max(spec["families"], key=lambda f: detail["settings"][f]["inner_utility"])
                target = "selected_new"
            else:
                selected = max(spec["families"], key=lambda f:
                               detail["inner_scores"][f][str(detail["family_thresholds"][f])])
                target = "nested_selected"
            if selected != detail["selected_family"]:
                raise ValueError("Reported family was not selected from inner utility")
            for qid in test:
                rows = condition["per_question"][qid]["policies"]
                if rows[target]["decisions"] != rows[selected]["decisions"]:
                    raise ValueError("Nested selected decisions differ from selected family")
        for policy, summary in condition["summary"].items():
            rows = [condition["per_question"][qid]["policies"][policy] for qid in ids]
            actions = np.asarray([row["decisions"] for row in rows])
            values = measured(panel["d"][:, eval_draws], panel["t"][:, eval_draws], actions)
            for metric, expected in values.items():
                if metric in rows[0]:
                    for i, row in enumerate(rows):
                        close(row[metric], expected[i])
                    close(summary[f"mean_{metric}"], expected.mean())
            if kind == "cpu":
                counts = {"escalations": actions.sum(),
                          "positive_gain_escalations": values["positive_gain_escalations"].sum(),
                          "nonpositive_gain_escalations": values["nonpositive_gain_escalations"].sum(),
                          "harmful_escalations": values["harmed"].sum(),
                          "missed_positive_gain_opportunities": values["missed_positive_gains"].sum()}
                for key, count in counts.items():
                    close(summary[key], count)
            confidence = np.array([condition["per_question"][qid]["policies"]["confidence"]["utility"]
                                   for qid in ids])
            delta = values["utility"] - confidence
            reported = summary["delta_vs_confidence"]
            close(reported["mean"] if kind == "cpu" else reported, delta.mean())
            ci = interval(delta, spec["bootstrap_seed"] if kind == "cpu" else spec["seed"])
            for actual, expected in zip(reported["ci90"] if kind == "cpu" else summary["delta_ci90"], ci):
                close(actual, expected)
            checked += actions.size
    halves = list(spec["conditions"])[:2]
    for policy, reported in stats["family_average_vs_confidence"].items():
        values = np.mean([[stats["conditions"][name]["per_question"][qid]["policies"][policy]["utility"]
                           - stats["conditions"][name]["per_question"][qid]["policies"]["confidence"]["utility"]
                           for qid in ids] for name in halves], axis=0)
        close(reported["mean"], values.mean())
        for a, b in zip(reported["ci90"], interval(values, spec["bootstrap_seed"] if kind == "cpu" else spec["seed"])):
            close(a, b)
    return checked


def review(root=ROOT):
    root = Path(root).resolve()
    panel = load_panel(root / "repeat-panel-v1")
    primary = verify(root / "repeat-panel-v1")
    directory = root / "router-feasibility-review-v1"
    reports, identities, checked = {}, {}, {}
    for kind, name in [("cpu", "repeat-cpu-feasibility-v1"),
                       ("contrastive", "repeat-contrastive-pilot-v1")]:
        report = verified(root / name / "report.json")
        plan = verified(root / name / "analysis-plan.json")
        if report["plan_sha256"] != digest(plan) or plan["inputs"] != panel["identity"]:
            raise ValueError("Completed experiment input provenance differs")
        for path, expected in plan["source_file_sha256" if kind == "cpu" else "source_files"].items():
            if file_hash(path) != expected:
                raise ValueError("Frozen experiment source changed")
        stats = report if kind == "cpu" else report["statistics"]
        checked[kind] = check_conditions(panel, stats, plan["spec"], kind)
        reports[kind] = stats
        identities[kind] = {"report_sha256": digest(report), "plan_sha256": digest(plan)}
    result = {"inputs": identities, "script_sha256": file_hash(__file__),
              "verified_decisions": checked, "protected_originals_verified": primary["protected_originals_verified"],
              "primary_report_sha256": panel["identity"]["primary_report_sha256"],
              "no_refitting_scoring_generation_or_references": True,
              "screens": {"cpu": reports["cpu"]["promotion_screen"],
                          "contrastive": reports["contrastive"]["screen"]}}
    write_new(directory / "verification.json", result)
    render(reports, directory)
    return {"verification": str(directory / "verification.json"), "checked_decisions": checked}


def render(reports, output):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib.pyplot as plt
    labels, values = [], []
    for prefix, kind in [("CPU", "cpu"), ("Neural", "contrastive")]:
        for family, result in reports[kind]["family_average_vs_confidence"].items():
            labels.append(f"{prefix}: {family}")
            values.append((result["mean"], *result["ci90"]))
    array = np.asarray(values)
    fig, ax = plt.subplots(figsize=(9.5, 6.5), layout="constrained")
    ax.errorbar(array[:, 0], range(len(labels)),
                xerr=np.array([array[:, 0] - array[:, 1], array[:, 2] - array[:, 0]]),
                fmt="o", color="#285d80", capsize=3)
    ax.axvline(0, color="#555555", linestyle="--", linewidth=1)
    ax.axvline(.01, color="#ac4938", linestyle=":", linewidth=1)
    ax.set(yticks=range(len(labels)), yticklabels=labels,
           xlabel="Average four-draw utility difference versus confidence (λ=.05)",
           title="Exploratory cached-data comparisons: fixed-fit question bootstrap 90% intervals")
    ax.invert_yaxis()
    fig.savefig(output / "utility-comparison.png", dpi=180)
    fig.savefig(output / "utility-comparison.pdf")
    plt.close(fig)


if __name__ == "__main__":
    print(review())
