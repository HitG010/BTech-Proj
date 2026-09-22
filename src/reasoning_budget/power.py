"""Prospective sensitivity analysis from whole-question paired development outcomes.

Normal-approximation planning is conditional on an assumed effect and variance.
It cannot guarantee significance or turn a development result into confirmation.
"""

import math
from pathlib import Path

import numpy as np
from scipy.stats import norm, t

from .data import load_questions
from .probe_study import read_protocol, read_sources
from .runner import load_run
from .storage import atomic_json, digest, envelope, verified


def required_questions(effect, sd, power=0.8, alpha=0.05):
    if not all(np.isfinite(v) for v in [effect, sd, power, alpha]):
        raise ValueError("Planning inputs must be finite")
    if sd <= 0 or not 0.5 < power < 1 or not 0 < alpha < 0.5:
        raise ValueError("Require positive SD, power in (.5,1), and alpha in (0,.5)")
    # A negative observed effect is not evidence for a positive superiority hypothesis.
    if effect <= 0:
        return None
    return max(2, math.ceil(((norm.ppf(1 - alpha / 2) + norm.ppf(power)) * sd / effect) ** 2))


def approximate_power(n, effect, sd, alpha=0.05):
    if type(n) is not int or n < 2 or not np.isfinite(effect) or not np.isfinite(sd) or sd <= 0:
        raise ValueError("Require at least two questions, finite effect, and positive SD")
    if not 0 < alpha < 0.5:
        raise ValueError("Invalid alpha")
    critical = norm.ppf(1 - alpha / 2)
    shift = effect * np.sqrt(n) / sd
    # Probability of crossing the positive boundary; not rejection in the wrong direction.
    return float(norm.sf(critical - shift))


def paired_summary(candidate, comparator, preference=0.05):
    candidate, comparator = np.asarray(candidate, float), np.asarray(comparator, float)
    if (
        candidate.shape != comparator.shape
        or candidate.ndim != 2
        or candidate.shape[1] != 3
        or len(candidate) < 2
        or not np.isfinite(candidate).all()
        or not np.isfinite(comparator).all()
        or not np.isfinite(preference)
        or preference < 0
    ):
        raise ValueError("Expected aligned finite whole-question accuracy/token/time rows")
    delta = (
        candidate[:, 0]
        - comparator[:, 0]
        - preference * (candidate[:, 1] - comparator[:, 1]) / 1000
    )
    mean, sd, n = float(delta.mean()), float(delta.std(ddof=1)), len(delta)
    if sd <= 0:
        raise ValueError("Zero observed variance is not a credible planning variance")
    se = sd / np.sqrt(n)
    return {
        "n_questions": n,
        "mean_utility_difference": mean,
        "paired_sd": sd,
        "descriptive_t_ci95": [
            float(mean - t.ppf(0.975, n - 1) * se),
            float(mean + t.ppf(0.975, n - 1) * se),
        ],
        "n_for_observed_positive_effect_80pct": required_questions(mean, sd),
        "n_for_observed_positive_effect_90pct": required_questions(mean, sd, 0.9),
        "positive_detection_probability_at_n500": approximate_power(500, mean, sd),
    }


def analyze(study_dir, data_dir="artifacts/data/gsm8k"):
    directory = Path(study_dir)
    protocol, models, report = (
        read_protocol(directory),
        verified(directory / "models.json"),
        verified(directory / "report.json"),
    )
    if report["protocol"] != digest(protocol) or report["models_sha256"] != digest(models):
        raise ValueError("Report dependencies changed")
    runs = verified(directory / "runs.json")
    _, sources, _ = read_sources(
        [runs[m] for m in ("direct", "thinking")], expected=protocol["diagnostic"], diagnostic=True
    )
    if sources != report["diagnostic_sources"]:
        raise ValueError("Report source records changed")
    if report["question_ids"] != [q["id"] for q in protocol["diagnostic"]]:
        raise ValueError("Report question order differs from protocol")
    preference = protocol["primary_preference"]
    rows = {
        r["policy"]: np.array(r["rows"])
        for r in report["per_question"]
        if r["parameter"] is None or r["parameter"] == preference
    }
    if any(len(r) != len(report["question_ids"]) for r in rows.values()):
        raise ValueError("Incomplete question-level policy outcomes")
    names = [
        "confidence-continuation",
        "gain-ridge",
        "DART-SC-3-adapted",
        "always-direct",
        "always-thinking",
    ]
    comparisons = {name: paired_summary(rows["joint"], rows[name], preference) for name in names}
    primary = comparisons["confidence-continuation"]
    if not np.isclose(
        primary["mean_utility_difference"],
        report["primary"]["utility_difference"],
        atol=1e-12,
        rtol=0,
    ):
        raise ValueError("Primary effect disagrees with saved report")
    spent_tokens = spent_seconds = 0
    for path in runs.values():
        for record in load_run(path)[1]:
            result = record["result"]
            spent_tokens += sum(
                result[k] for k in ["answer_tokens", "reasoning_tokens", "inserted_tokens"]
            )
            spent_seconds += result["elapsed_seconds"]
    n = len(report["question_ids"])
    sensitivity = [
        {
            "assumed_effect": effect,
            "sd_multiplier": scale,
            "n80": required_questions(effect, primary["paired_sd"] * scale),
            "n90": required_questions(effect, primary["paired_sd"] * scale, 0.9),
        }
        for effect in [0.005, 0.01, 0.02, 0.03]
        for scale in [1.0, 1.25, 1.5]
    ]
    used = set(protocol["excluded_ids"]) | set(report["question_ids"])
    questions = load_questions(data_dir)  # Question manifest only; never opens test gold.
    fresh = [q.id for q in questions if q.split == "train" and q.id not in used]
    estimate = primary["n_for_observed_positive_effect_80pct"]
    result = {
        "analysis_type": "post-development prospective planning, not confirmatory evidence",
        "source_report_sha256": digest(report),
        "implementation_sha256": digest(Path(__file__).read_text()),
        "preference": preference,
        "alpha_two_sided": 0.05,
        "unit": "whole question",
        "comparisons": comparisons,
        "sensitivity": sensitivity,
        "fresh_reserved_train_questions": len(fresh),
        "fresh_reserved_train_ids": fresh,
        "sealed_official_test_questions": sum(q.split == "test" for q in questions),
        "observed_successful_collection_tokens_per_question": spent_tokens / n,
        "observed_successful_collection_hours_per_question": spent_seconds / n / 3600,
        "projected_new_questions": estimate,
        "projected_successful_collection_tokens": None
        if estimate is None
        else estimate * spent_tokens / n,
        "projected_successful_collection_hours": None
        if estimate is None
        else estimate * spent_seconds / n / 3600,
        "projected_hours_with_historical_overhead": None
        if estimate is None
        else estimate
        * sum(v["elapsed_seconds"] for v in report["actual_cache_expenditure"].values())
        / n
        / 3600,
        "limitations": [
            "Effect and SD estimated from only 100 development questions.",
            "Zero or negative true advantage cannot be made positive by enlarging n.",
            "Sample sizes are normal approximations; not guarantees or observed-power evidence.",
            "Keep repeated draft orientations clustered within question.",
            "Training-seed variability and distribution shift are not included.",
            "Additional baselines require a predeclared multiplicity procedure.",
            "Do not pool already-inspected diagnostic outcomes into a fresh confirmatory test.",
        ],
    }
    atomic_json(directory / "power-analysis.json", envelope(result))
    lines = [
        "# Prospective power and feasibility",
        "",
        "This is planning from development results, not new evidence of superiority.",
        "",
        "| Comparator | Utility difference | Paired SD | Approx. fresh n for 80% power |",
        "|---|---:|---:|---:|",
    ]
    for name, row in comparisons.items():
        needed = row["n_for_observed_positive_effect_80pct"]
        lines.append(
            f"| {name} | {row['mean_utility_difference']:.6f} | {row['paired_sd']:.4f} | {needed if needed is not None else 'No positive observed advantage'} |"
        )
    projection_text = (
        "No finite positive-superiority sample size is justified by the observed effect."
        if estimate is None
        else f"Primary comparison estimate: {estimate} NEW questions; about "
        f"{result['projected_successful_collection_hours']:.1f} successful-generation hours or "
        f"{result['projected_hours_with_historical_overhead']:.1f} hours including historical overhead, "
        "using the same five-response cache per question."
    )
    lines += [
        "",
        f"Fresh reserved non-test questions: {len(fresh)}. Official test questions remain sealed: {result['sealed_official_test_questions']}.",
        "",
        projection_text,
        "",
        f"At n=500, the estimated probability of detecting the observed primary positive effect is {primary['positive_detection_probability_at_n500']:.1%}. This is conditional on an uncertain development effect, not a forecast guarantee.",
        "",
        "The original paired-bootstrap interval remains the reported diagnostic uncertainty. The additional t intervals are descriptive planning checks, not replacements chosen for significance.",
        "",
        "## Sensitivity to the assumed effect and variance",
        "",
        "| Assumed utility gain | SD multiplier | n80 | n90 |",
        "|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {r['assumed_effect']} | {r['sd_multiplier']} | {r['n80']} | {r['n90']} |"
        for r in sensitivity
    ]
    lines += ["", *[f"- {item}" for item in result["limitations"]], ""]
    (directory / "power-analysis.md").write_text("\n".join(lines))
    return directory / "power-analysis.md"
