"""Post-hoc descriptive audit: does lower direct confidence go with higher gain?

Reads cached repeat-panel and two-solver arrays through the existing guarded
loaders. No fitting, threshold choice, generation, scoring or reference access.
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from reasoning_budget.storage import digest, envelope, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
OUTPUT = BASE / "confidence-gain-shape-v1"
SOURCE_FILES = ("scripts/audit_confidence_gain_shape.py",
                "tests/test_audit_confidence_gain_shape.py",
                "docs/confidence-gain-shape-protocol.md")
PANELS = ("repeat_qwen3_1.7b", "two_solver_qwen3_0.6b", "two_solver_qwen3_1.7b")
SPEC = {
    "version": "confidence-gain-shape-v1", "label": "post_hoc/descriptive/reused-development",
    "lambda": 0.05, "gain": "thinking_correct - direct_correct - lambda * thinking_tokens / 1000",
    "confidence": "direct post-warper mean generated log probability",
    "panels": {"repeat_qwen3_1.7b": [50, 8], "two_solver_qwen3_0.6b": [64, 2],
               "two_solver_qwen3_1.7b": [64, 2]},
    "bins": 5, "binning": "equal-count pooled confidence quantiles; bin 1 lowest; fixed edges",
    "escalation_fractions": [round(0.1 * i, 1) for i in range(11)],
    "bootstrap_seed": 20261029, "bootstrap_draws": 2000, "interval": [0.05, 0.95],
    "bootstrap_unit": "whole question with all its draws",
    "reading": {"consistent": "pooled Spearman 90% interval below zero and bin 1 highest mean gain",
                "inconsistent": "pooled Spearman 90% interval above zero",
                "inconclusive": "otherwise"},
    "selection": "none; no fitting, threshold choice, policy or endpoint change",
}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_panel(direct_correct, thinking_correct, thinking_tokens, confidence):
    arrays = [np.asarray(a, dtype=float)
              for a in (direct_correct, thinking_correct, thinking_tokens, confidence)]
    shape = arrays[0].shape
    if (len(shape) != 2 or shape[0] < 2 or shape[1] < 1
            or any(a.shape != shape for a in arrays)
            or not all(np.isfinite(a).all() for a in arrays)):
        raise ValueError("Finite aligned question-by-draw arrays required")
    if not (np.isin(arrays[0], [0, 1]).all() and np.isin(arrays[1], [0, 1]).all()):
        raise ValueError("Binary correctness required")
    if np.any(arrays[2] < 0):
        raise ValueError("Nonnegative thinking tokens required")
    return arrays


def gain_matrix(direct_correct, thinking_correct, thinking_tokens, lam=SPEC["lambda"]):
    return thinking_correct - direct_correct - lam * thinking_tokens / 1000


def bin_labels(confidence, bins):
    edges = np.quantile(confidence.ravel(), np.linspace(0, 1, bins + 1)[1:-1])
    return np.searchsorted(edges, confidence, side="right")


def safe_spearman(a, b):
    a, b = np.ravel(a), np.ravel(b)
    if a.size < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(spearmanr(a, b).statistic)


def interval(values):
    valid = [v for v in values if v is not None]
    return (np.quantile(valid, SPEC["interval"]).tolist() if valid else None), len(valid)


def demeaned(matrix):
    return matrix - matrix.mean(axis=1, keepdims=True)


def correlations(confidence, gain):
    return {"pooled": safe_spearman(confidence, gain),
            "between_questions": safe_spearman(confidence.mean(1), gain.mean(1)),
            "within_questions": safe_spearman(demeaned(confidence), demeaned(gain))
            if confidence.shape[1] > 1 else None}


def bin_rows(direct, thinking, tokens, confidence, gain, labels, samples, bins):
    rows = []
    for b in range(bins):
        mask = labels == b
        if not mask.any():
            rows.append({"bin": b + 1, "states": 0})
            continue
        boot = [gain[i][labels[i] == b].mean() if (labels[i] == b).any() else None
                for i in samples]
        ci, valid = interval(boot)
        rows.append({"bin": b + 1, "states": int(mask.sum()),
            "questions": int(mask.any(axis=1).sum()),
            "confidence_min": float(confidence[mask].min()),
            "confidence_max": float(confidence[mask].max()),
            "direct_accuracy": float(direct[mask].mean()),
            "thinking_accuracy": float(thinking[mask].mean()),
            "mean_thinking_tokens": float(tokens[mask].mean()),
            "mean_gain": float(gain[mask].mean()), "mean_gain_ci90": ci,
            "valid_bootstrap_draws": valid,
            "positive_gain_states": int((gain[mask] > 0).sum()),
            "rescues": int(((direct == 0) & (thinking == 1))[mask].sum()),
            "harms": int(((direct == 1) & (thinking == 0))[mask].sum()),
            "both_wrong": int(((direct == 0) & (thinking == 0))[mask].sum())})
    return rows


def escalation_curve(confidence, gain, fractions):
    c, g = confidence.ravel(), gain.ravel()
    n = g.size
    order = np.lexsort((np.arange(n), c))
    by_confidence = np.concatenate([[0.0], np.cumsum(g[order])])
    by_oracle = np.concatenate([[0.0], np.cumsum(np.sort(g)[::-1])])
    rows = [{"fraction": f, "escalated": int(round(f * n)),
             "confidence_gain_per_state": float(by_confidence[int(round(f * n))] / n),
             "random_expected_gain_per_state": float(round(f * n) * g.mean() / n),
             "oracle_gain_per_state": float(by_oracle[int(round(f * n))] / n)}
            for f in fractions]
    best = int(np.argmax(by_confidence))
    positive = float(g[g > 0].sum())
    return {"curve": rows,
        "best_in_sample_confidence": {"escalated": best, "fraction": best / n,
                                      "gain_per_state": float(by_confidence[best] / n)},
        "oracle_gain_per_state": positive / n,
        "best_share_of_oracle": float(by_confidence[best] / positive) if positive > 0 else None,
        "warning": "in-sample and optimistic; not a deployable threshold or endpoint"}


def reading(pooled_ci, rows):
    means = [r["mean_gain"] for r in rows if r["states"]]
    if pooled_ci is None or not means:
        return "inconclusive"
    if pooled_ci[1] < 0 and rows[0]["states"] and rows[0]["mean_gain"] == max(means):
        return "consistent"
    if pooled_ci[0] > 0:
        return "inconsistent"
    return "inconclusive"


def gain_shape(direct_correct, thinking_correct, thinking_tokens, confidence, spec=SPEC):
    direct, thinking, tokens, conf = check_panel(
        direct_correct, thinking_correct, thinking_tokens, confidence)
    gain = gain_matrix(direct, thinking, tokens, spec["lambda"])
    labels = bin_labels(conf, spec["bins"])
    samples = np.random.default_rng(spec["bootstrap_seed"]).integers(
        0, len(conf), size=(spec["bootstrap_draws"], len(conf)))
    point = correlations(conf, gain)
    boot = [correlations(conf[i], gain[i]) for i in samples]
    trend = {}
    for name, value in point.items():
        ci, valid = interval([b[name] for b in boot])
        trend[name] = {"spearman": value, "ci90": ci, "valid_bootstrap_draws": valid}
    pooled = [b["pooled"] for b in boot if b["pooled"] is not None]
    trend["pooled"]["share_negative"] = float(np.mean(np.asarray(pooled) < 0)) if pooled else None
    rows = bin_rows(direct, thinking, tokens, conf, gain, labels, samples, spec["bins"])
    filled = [r["mean_gain"] for r in rows if r["states"]]
    return {"questions": int(conf.shape[0]), "draws": int(conf.shape[1]),
        "states": int(conf.size), "mean_gain": float(gain.mean()),
        "direct_accuracy": float(direct.mean()), "thinking_accuracy": float(thinking.mean()),
        "bins": rows, "monotonicity_violations": int(sum(
            later > earlier for earlier, later in zip(filled, filled[1:]))),
        "trend": trend, "escalation": escalation_curve(conf, gain, spec["escalation_fractions"]),
        "reading": reading(trend["pooled"]["ci90"], rows)}


def repeat_inputs():
    from scripts import repeat_clm_probe as probe
    from scripts.repeat_cpu_feasibility import load_panel
    panel = load_panel(probe.STUDY)
    d, t, z = (np.asarray(panel[key]) for key in ("d", "t", "z"))
    arrays = {"direct_correct": d[..., 0], "thinking_correct": t[..., 0],
              "thinking_tokens": t[..., 1], "confidence": z[..., 0]}
    return arrays, {"panel": panel["identity"], "study": str(probe.STUDY)}


def environment_difference(frozen, current):
    return sorted(key for key in set(frozen) | set(current) if frozen.get(key) != current.get(key))


def study_inventory(study):
    return {str(path.relative_to(study)): file_hash(path)
            for path in sorted(study.rglob("*")) if path.is_file()}


def two_solver_endpoint():
    """Byte-identity checks of the closed endpoint; never scores or opens references.

    The collector's own readers also require the live runtime environment to equal
    the collection environment. That guard protects generation, not cached reads,
    so this audit records the difference instead of requiring equality.
    """
    from scripts import opportunity_panel_collect as original
    from scripts import opportunity_panel_completion as completion
    original.safe_paths()
    study, child = original.STUDY, completion.CHILD
    protocol = verified(study / "protocol.json")
    plan = verified(child / "plan.json")
    for path, sha in protocol["source_file_sha256"].items():
        if file_hash(path) != sha:
            raise ValueError(f"Two-solver frozen source changed: {path}")
    if (plan["source_file_sha256"] != completion.sources()
            or plan["parent_protocol_sha256"] != digest(protocol)
            or plan["parent_inventory_sha256"] != digest(plan["parent_inventory"])):
        raise ValueError("Two-solver completion plan or sources changed")
    for relative, sha in plan["parent_inventory"].items():
        if file_hash(study / relative) != sha:
            raise ValueError(f"Two-solver parent original changed: {relative}")
    if set(completion.parent_inventory()) != set(plan["parent_inventory"]):
        raise ValueError("New file appeared outside the two-solver completion child")
    status, terminal, report, scores, review = (verified(child / name) for name in (
        "status.json", "supervisor-finish.json", "report.json", "scores.numeric-v7.json",
        "completion-review-verification.json"))
    if (not (child / "collection-end.json").is_file()
            or terminal["state"] != "complete" or status["state"] != "complete"
            or verified(child / "invocation-process.json")["exit_code"] != 0
            or verified(child / "finalize-process.json")["exit_code"] != 0
            or terminal["report_sha256"] != digest(report)
            or status["report_sha256"] != digest(report)
            or report["plan_sha256"] != digest(plan)
            or report["parent_protocol_sha256"] != digest(protocol)
            or report["scores_sha256"] != digest(scores)
            or scores["protocol_sha256"] != digest(plan)
            or scores["scoring_implementation_sha256"] != protocol["scoring_implementation_sha256"]
            or scores["scoring_version"] != "numeric-v7" or len(scores["scores"]) != 512):
        raise ValueError("Two-solver closed endpoint identity changed")
    grouped = completion.combined_records(plan, protocol)
    if scores["records_sha256"] != digest(grouped):
        raise ValueError("Two-solver cached records changed")
    current = original.stable_environment()
    identity = {"study": str(study), "protocol_sha256": digest(protocol),
        "completion_plan_sha256": digest(plan), "report_sha256": digest(report),
        "scores_sha256": digest(scores), "records_sha256": digest(grouped),
        "review_sha256": digest(review),
        "review_mentions_report_sha256": digest(report) in json.dumps(review),
        "study_inventory_sha256": digest(study_inventory(study)),
        "runtime_environment": {"collection": protocol["environment"], "audit": current,
            "differing_fields": environment_difference(protocol["environment"], current)}}
    return grouped, report, scores, identity


def two_solver_inputs():
    from scripts.opportunity_panel_analysis import SOLVERS, paired_rows
    grouped, report, scores, identity = two_solver_endpoint()
    rows = paired_rows(grouped, scores)
    ids = report["statistics"]["question_ids"]
    index = {qid: i for i, qid in enumerate(ids)}
    draws = sorted({row["draw"] for row in rows})
    if len(ids) != 64 or len(index) != 64 or len(draws) != 2:
        raise ValueError("Expected 64 questions and two draws per solver")
    panels = {}
    for solver in SOLVERS:
        arrays = {k: np.full((64, 2), np.nan) for k in
                  ("direct_correct", "thinking_correct", "thinking_tokens", "confidence")}
        for row in (r for r in rows if r["solver"] == solver):
            i, j = index[row["question_id"]], draws.index(row["draw"])
            if np.isfinite(arrays["confidence"][i, j]):
                raise ValueError("Duplicate two-solver state")
            for key in arrays:
                arrays[key][i, j] = row[key]
        panels["two_solver_" + solver.replace("-", "_")] = arrays
    return panels, identity


def inputs():
    repeat, repeat_identity = repeat_inputs()
    two_solver, two_identity = two_solver_inputs()
    panels = {"repeat_qwen3_1.7b": repeat, **two_solver}
    if set(panels) != set(PANELS):
        raise ValueError("Unexpected panel names")
    for name, arrays in panels.items():
        if list(arrays["confidence"].shape) != SPEC["panels"][name]:
            raise ValueError(f"Unexpected shape for {name}")
    return panels, {"repeat": repeat_identity, "two_solver": two_identity}


def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(payload), stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked_output():
    if OUTPUT.is_symlink() or OUTPUT.resolve() != BASE.resolve() / SPEC["version"]:
        raise ValueError("Only the separate confidence-gain audit directory is writable")


def packages():
    return {name: importlib.metadata.version(name) for name in ("numpy", "scipy")}


def prepare():
    checked_output()
    _, identity = inputs()
    plan = {"spec": SPEC, "inputs": identity,
            "source_file_sha256": {name: file_hash(ROOT / name) for name in SOURCE_FILES},
            "packages": packages(), "no_fit_inference_generation_references": True}
    write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "plan_sha256": digest(plan)}


def fmt(value, digits=4):
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(v, digits) for v in value) + "]"
    return f"{value:.{digits}f}"


def markdown(report):
    lines = ["# Confidence–gain shape audit", "",
             "Post-hoc, descriptive, reused development data. See "
             "`docs/confidence-gain-shape-protocol.md`.", ""]
    deviation = report.get("runtime_environment_deviation")
    if deviation is not None:
        lines += ["Two-solver runtime environment fields differing from collection: "
                  f"{', '.join(deviation) or 'none'}. Cached bytes were verified by hash; "
                  "no generation or scoring occurred.", ""]
    for name in PANELS:
        r = report["statistics"][name]
        t, e = r["trend"], r["escalation"]
        lines += [f"## {name}", "",
                  f"Reading: **{r['reading']}**. States {r['states']}; mean gain "
                  f"{fmt(r['mean_gain'])}; pooled Spearman {fmt(t['pooled']['spearman'])} "
                  f"{fmt(t['pooled']['ci90'])}; between questions "
                  f"{fmt(t['between_questions']['spearman'])} "
                  f"{fmt(t['between_questions']['ci90'])}; within questions "
                  f"{fmt(t['within_questions']['spearman'])} "
                  f"{fmt(t['within_questions']['ci90'])}; monotonicity violations "
                  f"{r['monotonicity_violations']}.", "",
                  "| Bin | States | Confidence range | Direct acc. | Thinking acc. | "
                  "Thinking tokens | Mean gain [90% interval] | Rescues | Harms | Both wrong |",
                  "|---:|---:|---|---:|---:|---:|---|---:|---:|---:|"]
        for b in r["bins"]:
            if not b["states"]:
                lines.append(f"| {b['bin']} | 0 | | | | | | | | |")
                continue
            lines.append(f"| {b['bin']} | {b['states']} | {fmt(b['confidence_min'])} to "
                         f"{fmt(b['confidence_max'])} | {fmt(b['direct_accuracy'], 3)} | "
                         f"{fmt(b['thinking_accuracy'], 3)} | "
                         f"{fmt(b['mean_thinking_tokens'], 1)} | {fmt(b['mean_gain'])} "
                         f"{fmt(b['mean_gain_ci90'])} | {b['rescues']} | {b['harms']} | "
                         f"{b['both_wrong']} |")
        best = e["best_in_sample_confidence"]
        lines += ["", f"Best in-sample confidence escalation: fraction {fmt(best['fraction'], 3)}, "
                  f"gain per state {fmt(best['gain_per_state'], 6)}; hindsight oracle "
                  f"{fmt(e['oracle_gain_per_state'], 6)}; share "
                  f"{fmt(e['best_share_of_oracle'], 3)}. In-sample and optimistic.", ""]
    return "\n".join(lines) + "\n"


def execute():
    checked_output()
    plan = verified(OUTPUT / "plan.json")
    if plan["spec"] != SPEC:
        raise ValueError("Audit spec changed")
    if plan["source_file_sha256"] != {name: file_hash(ROOT / name) for name in SOURCE_FILES}:
        raise ValueError("Frozen audit source changed")
    if plan["packages"] != packages():
        raise ValueError("Frozen audit environment changed")
    panels, identity = inputs()
    if identity != plan["inputs"]:
        raise ValueError("Frozen audit inputs changed")
    statistics = {name: gain_shape(**panels[name]) for name in PANELS}
    from scripts.verify_phase2_repeat import verify
    preservation = verify(Path(identity["repeat"]["study"]))
    two_solver = identity["two_solver"]
    if digest(study_inventory(Path(two_solver["study"]))) != two_solver["study_inventory_sha256"]:
        raise ValueError("Two-solver study files changed")
    report = {"plan_sha256": digest(plan), "spec": SPEC, "inputs": identity,
              "statistics": statistics,
              "repeat_protected_originals_verified": preservation["protected_originals_verified"],
              "two_solver_inventory_unchanged": True,
              "runtime_environment_deviation":
                  identity["two_solver"]["runtime_environment"]["differing_fields"],
              "no_fit_inference_generation_references": True, "cloud_spend_usd": 0.0}
    write_new(OUTPUT / "report.json", report)
    with (OUTPUT / "report.md").open("x") as stream:
        stream.write(markdown(report))
    return {"report_sha256": digest(report),
            "readings": {name: statistics[name]["reading"] for name in PANELS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "execute"])
    args = parser.parse_args()
    print(prepare() if args.command == "prepare" else execute())


if __name__ == "__main__":
    main()
