"""Frozen descriptive audit of cached CLM scores; no fitting or inference."""

import argparse
import importlib.metadata
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, verified
from scripts import repeat_clm_probe as probe
from scripts.repeat_cpu_feasibility import load_panel

OUTPUT = probe.local.BASE / "clm-signal-audit-v1"
SPEC = {
    "version": "clm-signal-audit-v1", "label": "post_hoc/descriptive/reused-development",
    "lambda": .05, "bootstrap_seed": 20261007, "bootstrap_draws": 2000,
    "interval": [.05, .95], "bootstrap_unit": "whole question, all eight paired draws",
    "scores": ["released_clm_margin", "negative_direct_confidence"],
    "events": ["positive_paired_gain", "direct_incorrect", "harmful_escalation"],
    "auc": "pooled draw ranking; question-group bootstrap; higher score predicts event",
    "within_question_auc": "unweighted mean only over questions having both event classes",
    "half_transfer": "question mean score in A vs mean gain in B, and reverse; Spearman",
    "selection": "none; no fitting, threshold search, prompt change or policy promotion",
}


def auc(labels, scores):
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    if labels.shape != scores.shape or labels.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError("Finite aligned one-dimensional labels/scores required")
    if not np.isin(labels, [0, 1]).all() or len(labels) == 0:
        raise ValueError("Nonempty binary labels required")
    positive = labels.astype(bool)
    n = int(positive.sum())
    if n in (0, len(labels)):
        return None
    return float((rankdata(scores)[positive].sum() - n * (n + 1) / 2)
                 / (n * (len(labels) - n)))


def ranked_event(labels, scores, draws):
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if labels.shape != scores.shape or labels.ndim != 2 or draws.ndim != 2:
        raise ValueError("Question-by-draw arrays and question bootstrap required")
    if draws.shape[1] != len(labels) or draws.min() < 0 or draws.max() >= len(labels):
        raise ValueError("Bootstrap must resample whole questions")
    point = auc(labels.ravel(), scores.ravel())
    samples = [auc(labels[index].ravel(), scores[index].ravel()) for index in draws]
    valid = [value for value in samples if value is not None]
    within = [auc(y, x) for y, x in zip(labels, scores)]
    informative = [value for value in within if value is not None]
    return {"event_count": int(labels.sum()), "question_count": len(labels),
        "pooled_auc": point,
        "ci90": np.quantile(valid, SPEC["interval"]).tolist() if valid else None,
        "valid_bootstrap_draws": len(valid), "undefined_bootstrap_draws": len(samples) - len(valid),
        "within_question_macro_auc": float(np.mean(informative)) if informative else None,
        "within_question_informative_groups": len(informative)}


def safe_spearman(a, b):
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(spearmanr(a, b).statistic)


def signal_statistics(direct, thinking, confidence, margins):
    direct, thinking = np.asarray(direct), np.asarray(thinking)
    confidence, margins = np.asarray(confidence), np.asarray(margins)
    if (direct.shape != thinking.shape or direct.ndim != 3 or direct.shape[2] != 3
            or direct.shape[1] != 8 or confidence.shape != direct.shape[:2]
            or margins.shape != confidence.shape
            or not all(np.isfinite(v).all() for v in (direct, thinking, confidence, margins))):
        raise ValueError("Complete finite eight-draw cached panel required")
    if (not np.isin(direct[..., 0], [0, 1]).all()
            or not np.isin(thinking[..., 0], [0, 1]).all()
            or np.any(direct[..., 1:] < 0) or np.any(thinking[..., 1:] < 0)):
        raise ValueError("Binary correctness and nonnegative costs required")
    gain = thinking[..., 0] - direct[..., 0] - .05 * thinking[..., 1] / 1000
    events = {"positive_paired_gain": gain > 0, "direct_incorrect": direct[..., 0] == 0,
        "harmful_escalation": thinking[..., 0] < direct[..., 0]}
    scores = {"released_clm_margin": margins, "negative_direct_confidence": -confidence}
    samples = np.random.default_rng(SPEC["bootstrap_seed"]).integers(
        0, len(direct), size=(SPEC["bootstrap_draws"], len(direct)))
    results = {name: {event: ranked_event(labels, score, samples)
        for event, labels in events.items()} for name, score in scores.items()}
    paired_auc = {}
    for event, labels in events.items():
        a = results["released_clm_margin"][event]
        b = results["negative_direct_confidence"][event]
        differences = []
        for index in samples:
            left = auc(labels[index].ravel(), margins[index].ravel())
            right = auc(labels[index].ravel(), -confidence[index].ravel())
            if left is not None and right is not None:
                differences.append(left - right)
        paired_auc[event] = {"clm_minus_confidence_auc":
            a["pooled_auc"] - b["pooled_auc"] if a["pooled_auc"] is not None else None,
            "ci90": np.quantile(differences, SPEC["interval"]).tolist() if differences else None,
            "valid_bootstrap_draws": len(differences)}
    transfer = {}
    for name, score in scores.items():
        transfer[name] = {"A_score_to_B_gain": safe_spearman(score[:, :4].mean(1), gain[:, 4:].mean(1)),
            "B_score_to_A_gain": safe_spearman(score[:, 4:].mean(1), gain[:, :4].mean(1))}
    chosen = margins > 0
    count = int(chosen.sum())
    captured = int((chosen & events["positive_paired_gain"]).sum())
    return {"ranking": results, "paired_auc_differences": paired_auc,
        "question_mean_half_transfer_spearman": transfer,
        "margin": {"minimum": float(margins.min()), "median": float(np.median(margins)),
            "maximum": float(margins.max()), "positive_count": count, "total": margins.size,
            "positive_gain_captured": captured,
            "positive_gain_precision": captured / count if count else None,
            "positive_gain_recall": captured / int(events["positive_paired_gain"].sum())
                if events["positive_paired_gain"].any() else None,
            "nonpositive_escalations": int((chosen & (gain <= 0)).sum()),
            "harmful_escalations": int((chosen & events["harmful_escalation"]).sum())},
        "no_policy_changes": True}


def break_even(accuracy_difference, additional_tokens):
    if additional_tokens <= 0:
        return None
    return accuracy_difference / (additional_tokens / 1000)


def inputs():
    plan = probe.checked_plan()
    panel = load_panel(probe.STUDY)
    report = verified(probe.OUTPUT / "report.json")
    heads = verified(probe.OUTPUT / "released-head-report.json")
    review = verified(probe.local.BASE / "repeat-clm-review-v1/verification.json")
    if (report["plan_sha256"] != digest(plan) or heads["plan_sha256"] != digest(plan)
            or report["panel_identity"] != panel["identity"]
            or review["report_sha256"] != digest(report)
            or review["plan_sha256"] != digest(plan)):
        raise ValueError("Require unchanged completed and independently verified CLM endpoint")
    # The released CPU head computed the subtraction in float32 before JSON.
    logits = np.asarray(heads["logits"], dtype=np.float32)
    margins = np.asarray(heads["margins"])
    if logits.shape != (50, 8, 2) or not np.array_equal(logits[..., 1] - logits[..., 0], margins):
        raise ValueError("Recorded head logits and margins differ")
    identity = {"panel": panel["identity"], "clm_plan_sha256": digest(plan),
        "clm_report_sha256": digest(report), "head_report_sha256": digest(heads),
        "independent_review_sha256": digest(review)}
    return panel, report, margins, identity


def sources():
    return [Path(__file__), probe.local.ROOT / "tests/test_audit_clm_signal.py",
        probe.local.ROOT / "tests/test_clm_objective_checks.py",
        probe.local.ROOT / "docs/clm-signal-audit-protocol.md"]


def checked_output():
    if OUTPUT.is_symlink() or OUTPUT.resolve() != probe.local.BASE.resolve() / SPEC["version"]:
        raise ValueError("Only the separate CLM signal audit directory is writable")


def prepare():
    checked_output()
    _, _, _, identity = inputs()
    plan = {"spec": SPEC, "inputs": identity,
        "source_file_sha256": {str(p.resolve()): file_hash(p) for p in sources()},
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy")},
        "no_fit_inference_generation_references": True}
    probe.local.write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "plan_sha256": digest(plan)}


def execute():
    checked_output()
    plan = verified(OUTPUT / "plan.json")
    if plan["spec"] != SPEC:
        raise ValueError("Audit spec changed")
    for path, sha in plan["source_file_sha256"].items():
        if file_hash(path) != sha:
            raise ValueError("Frozen audit source changed")
    if plan["packages"] != {name: importlib.metadata.version(name) for name in plan["packages"]}:
        raise ValueError("Frozen audit environment changed")
    panel, prior, margins, identity = inputs()
    if identity != plan["inputs"]:
        raise ValueError("Frozen audit inputs changed")
    result = signal_statistics(panel["d"], panel["t"], panel["z"][..., 0], margins)
    summaries = [prior["statistics"]["conditions"][name]["summary"]
        for name in ("k4_A_to_B", "k4_B_to_A")]
    accuracy_delta = float(np.mean([s["clm_zero_shot"]["accuracy"] - s["confidence"]["accuracy"]
        for s in summaries]))
    tokens_delta = float(np.mean([s["clm_zero_shot"]["tokens"] - s["confidence"]["tokens"]
        for s in summaries]))
    result["fixed_policy_cost_sensitivity"] = {
        "accuracy_difference": accuracy_delta, "additional_tokens": tokens_delta,
        "break_even_lambda": break_even(accuracy_delta, tokens_delta),
        "warning": "descriptive fixed actions tuned at lambda=.05; no retuning or endpoint change; encoder cost omitted"}
    from scripts.verify_phase2_repeat import verify
    preservation = verify(probe.STUDY)
    report = {"plan_sha256": digest(plan), "spec": SPEC, "inputs": identity,
        "statistics": result, "protected_originals_verified": preservation["protected_originals_verified"],
        "no_fit_inference_generation_references": True, "cloud_spend_usd": 0.}
    probe.local.write_new(OUTPUT / "report.json", report)
    return {"report_sha256": digest(report), "statistics": result,
        "protected_originals_verified": report["protected_originals_verified"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "execute"])
    args = parser.parse_args()
    print(prepare() if args.command == "prepare" else execute())


if __name__ == "__main__":
    main()
