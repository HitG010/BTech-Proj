"""Render figures from the frozen repeat-panel and post-hoc reports only.

This script never loads responses, scores, gold, or fits a model. It writes only
to the separate repeat-diagnosis figure directory by default.
"""

import argparse
import hashlib
import os
from pathlib import Path

import numpy as np

from reasoning_budget.storage import atomic_json, digest, verified

ROOT = Path("artifacts/research/data-efficiency-v1")
ORDER = (
    "k1_A_to_B",
    "k1_B_to_A",
    "k2_A_to_B",
    "k2_B_to_A",
    "k4_A_to_B",
    "k4_B_to_A",
    "k8_full",
)


def file_sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verified_inputs(root):
    root = Path(root)
    primary = verified(root / "repeat-panel-v1/report.json")
    diagnosis = verified(root / "repeat-diagnosis-v1/report.json")
    plan = verified(root / "repeat-diagnosis-v1/analysis-plan.json")
    if (
        diagnosis["plan_sha256"] != digest(plan)
        or plan["primary_report_sha256"] != digest(primary)
        or diagnosis["primary_gates"] != primary["statistics"]["gates"]
        or primary["statistics"]["scale_acquisition"]
        or not plan["primary_gates_failed"]
        or plan["label"] != "post_hoc/development"
    ):
        raise ValueError("Frozen repeat report or post-hoc provenance changed")
    if set(primary["statistics"]["conditions"]) != set(ORDER):
        raise ValueError("Primary repeat conditions changed")
    for name in ("combined", "confidence"):
        if diagnosis["conditions"]["k8_full"]["policies"][name]["evaluated_pairs"] != 400:
            raise ValueError("Full-eight diagnostic coverage changed")
    return primary, diagnosis, plan


def render(root=ROOT, output=None):
    os.environ.setdefault("MPLCONFIGDIR", str((Path(".cache/matplotlib")).resolve()))
    os.environ.setdefault("XDG_CACHE_HOME", str(Path(".cache").resolve()))
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib.pyplot as plt

    root = Path(root).resolve()
    primary, diagnosis, plan = verified_inputs(root)
    output = Path(output).resolve() if output else root / "repeat-diagnosis-v1/figures"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 180}
    )
    source = {
        "primary_report_sha256": digest(primary),
        "diagnosis_report_sha256": digest(diagnosis),
        "diagnosis_plan_sha256": digest(plan),
        "plot_script_sha256": file_sha256(__file__),
    }
    metadata = {
        "Title": "Repeat-panel diagnostic results",
        "Creator": "plot_repeat_results.py",
        "Subject": "primary frozen utility deltas; post-hoc escalation counts; "
        + ", ".join(f"{k}={v}" for k, v in source.items()),
    }

    conditions = primary["statistics"]["conditions"]
    means = np.array([conditions[k]["combined_minus_baseline"]["mean"] for k in ORDER])
    intervals = np.array([conditions[k]["combined_minus_baseline"]["ci90"] for k in ORDER])
    if not (
        np.isfinite(means).all()
        and np.isfinite(intervals).all()
        and (intervals[:, 0] <= means).all()
        and (means <= intervals[:, 1]).all()
    ):
        raise ValueError("Invalid primary utility intervals")
    y = np.arange(len(ORDER))
    fig, ax = plt.subplots(figsize=(8.3, 4.7), layout="constrained")
    colors = ["#bf5b4d" if mean < 0 else "#237d68" for mean in means]
    ax.barh(y, means, color=colors, alpha=0.82, height=0.57)
    ax.errorbar(
        means,
        y,
        xerr=np.vstack([means - intervals[:, 0], intervals[:, 1] - means]),
        fmt="none",
        ecolor="#223344",
        capsize=3,
        linewidth=1.4,
    )
    ax.axvline(0, color="#23313f", linewidth=1)
    ax.set_yticks(y, [name.replace("_", " ").replace(" to ", " → ") for name in ORDER])
    ax.invert_yaxis()
    ax.set_xlabel("Combined − inner-selected baseline utility at λ = 0.05")
    ax.set_title(
        "Frozen primary comparison: 90% question-bootstrap intervals\n"
        "50 questions · conditional on fixed fits · no multiplicity adjustment",
        fontsize=11,
    )
    ax.grid(axis="x", alpha=0.2)
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"primary-utility-deltas.{suffix}", metadata=metadata)
    plt.close(fig)

    policies = diagnosis["conditions"]["k8_full"]["policies"]
    names = ("combined", "confidence")
    useful = [policies[name]["useful_escalations_gain_positive"] for name in names]
    wasted = [policies[name]["wasted_escalations_gain_nonpositive"] for name in names]
    if [useful[i] + wasted[i] for i in range(2)] != [
        round(policies[name]["mean_escalation_rate"] * 400) for name in names
    ]:
        raise ValueError("Post-hoc escalation counts do not match policy rates")
    fig, ax = plt.subplots(figsize=(7.4, 3.6), layout="constrained")
    y = np.arange(2)
    ax.barh(y, useful, color="#237d68", label="Positive realized gain")
    ax.barh(y, wasted, left=useful, color="#bf5b4d", label="Nonpositive realized gain")
    for i, (good, bad) in enumerate(zip(useful, wasted)):
        ax.text(good + bad + 3, i, f"{good} useful / {bad} wasted", va="center", fontsize=9)
    ax.set_yticks(y, ["Combined", "Confidence"])
    ax.invert_yaxis()
    ax.set_xlim(0, max(a + b for a, b in zip(useful, wasted)) * 1.42)
    ax.set_xlabel("Escalated paired draws (of 400)")
    ax.set_title("Post-hoc/development: realized escalation composition")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.grid(axis="x", alpha=0.2)
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"posthoc-escalation-counts.{suffix}", metadata=metadata)
    plt.close(fig)

    files = [
        output / f"{stem}.{suffix}"
        for stem in ("primary-utility-deltas", "posthoc-escalation-counts")
        for suffix in ("png", "pdf")
    ]
    atomic_json(
        output / "figure-provenance.json",
        {
            "label": "primary figure plus separately labeled post_hoc/development figure",
            "sources": source,
            "files_sha256": {path.name: file_sha256(path) for path in files},
        },
    )
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output")
    args = parser.parse_args()
    for path in render(args.root, args.output):
        print(path)


if __name__ == "__main__":
    main()
