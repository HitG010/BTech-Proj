"""Prospective question-level precision and local budget sensitivity, no fitting.

Only completed cached reports and question-role metadata are read. This is a
planning calculation, never a collector, scorer or allocation writer.
"""

import argparse
import math
import statistics
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, envelope, run_lock, verified

ROOT = Path("artifacts/research/data-efficiency-v1")
SPEC = {
    "version": "broader-signal-power-v1",
    "alpha": 0.05,
    "powers": [0.8, 0.9],
    "effects": [0.01, 0.02, 0.03],
    "paired_question_sd": [0.05, 0.10, 0.16, 0.25, 0.32],
    "question_counts": [64, 128, 200, 548, 2000],
    "proposed_questions": 64,
    "proposed_solvers": 2,
    "draws_per_mode_per_solver": 2,
    "normal_approximation": "two-sided known-SD paired mean, independent question groups",
    "scope": "sensitivity only; no AULC power, allocation change, labels or generation",
}
PINNED = {
    "repeat-panel-v1/report.json": "e4d17cc5ab4e0d3ffd1b79d301a988537d43bd2379fd1a99243f1e2843dd6d56",
    "repeat-cpu-feasibility-v1/report.json": "42e95eaa38bce5719ebcf700e6c0bf4527617ec7b8704cdd7a48034024502e01",
    "repeat-contrastive-pilot-v1/report.json": "e8ddebe38f211359eda4a60742e5cd388ea6a823981b60f7461293b21004a5eb",
}
NORMAL = statistics.NormalDist()


def power(n, effect, sd, alpha=0.05):
    if n < 2 or sd <= 0 or not 0 < alpha < 1 or not math.isfinite(effect + sd):
        raise ValueError("Invalid question count, effect, SD or alpha")
    z = NORMAL.inv_cdf(1 - alpha / 2)
    shift = abs(effect) * math.sqrt(n) / sd
    return NORMAL.cdf(shift - z) + NORMAL.cdf(-shift - z)


def required_n(effect, sd, target=0.8):
    if effect <= 0 or not math.isfinite(effect):
        return None  # negative development effects do not justify superiority
    if not 0.05 < target < 1:
        raise ValueError("Invalid target power")
    low, high = 2, 2
    while power(high, effect, sd) < target:
        high *= 2
    while low < high:
        mid = (low + high) // 2
        if power(mid, effect, sd) >= target:
            high = mid
        else:
            low = mid + 1
    return low


def detectable_effect(n, sd, target=0.8):
    if sd <= 0 or not 0.05 < target < 1:
        raise ValueError("Invalid SD or target power")
    low, high = 0.0, sd
    while power(n, high, sd) < target:
        high *= 2
    for _ in range(80):
        mid = (low + high) / 2
        if power(n, mid, sd) >= target:
            high = mid
        else:
            low = mid
    return high


def reservation_per_pair(protocol):
    config = protocol["snapshot"]["config"]
    closure = protocol["snapshot"]["identity"]["backend"]["closure_tokens"]
    maximum = 2 * config["answer_tokens"] + config["reasoning_tokens"] + closure
    jobs = len(protocol["snapshot"]["jobs"])
    if jobs % 2 or maximum * (jobs // 2) != protocol["snapshot"]["planned_max_tokens"]:
        raise ValueError("Frozen endpoint reservation arithmetic changed")
    return maximum


def build(root):
    root = Path(root).resolve()
    reports, identities = {}, {}
    for relative, expected in PINNED.items():
        payload = verified(root / relative)
        if digest(payload) != expected:
            raise ValueError(f"Completed report changed: {relative}")
        reports[relative] = payload
        identities[relative] = file_hash(root / relative)
    protocol = verified(root / "repeat-panel-v1/protocol.json")
    allocation = verified(root / "allocations/manifest.json")
    if digest(protocol) != reports["repeat-panel-v1/report.json"]["protocol_sha256"]:
        raise ValueError("Primary protocol identity changed")
    if digest(allocation) != protocol["allocation_sha256"]:
        raise ValueError("Allocation identity changed")
    for relative in ("repeat-panel-v1/protocol.json", "allocations/manifest.json"):
        identities[relative] = file_hash(root / relative)
    cpu = reports["repeat-cpu-feasibility-v1/report.json"]
    neural = reports["repeat-contrastive-pilot-v1/report.json"]["statistics"]
    descriptive = {}
    for name, summary in (("cpu", cpu["selected_new_average_vs_confidence"]),
                          ("compact_contrastive", neural["family_average_vs_confidence"]["nested_selected"])):
        values = list(summary["per_question"].values())
        if len(values) != 50:
            raise ValueError("Expected 50 independent question groups")
        mean, sd = statistics.mean(values), statistics.stdev(values)
        descriptive[name] = {"n_questions": 50, "mean": mean, "paired_sd": sd,
            "n_for_observed_positive_effect": required_n(mean, sd),
            "qualification": "fixed-fit, average of two draw-half policies; not single-draw prospective variance"}
    pair = cpu["conditions"]["k8_full"]["summary"]["escalate"]
    maximum = reservation_per_pair(protocol)
    per_solver_pairs = SPEC["proposed_questions"] * SPEC["draws_per_mode_per_solver"]
    total_pairs = per_solver_pairs * SPEC["proposed_solvers"]
    result = {"spec": SPEC, "inputs": identities, "development_description": descriptive,
        "role_counts_unchanged": allocation["role_counts"],
        "power_grid": [{"effect": effect, "sd": sd,
            "required_questions": {str(target): required_n(effect, sd, target) for target in SPEC["powers"]},
            "power_by_n": {str(n): power(n, effect, sd) for n in SPEC["question_counts"]}}
            for sd in SPEC["paired_question_sd"] for effect in SPEC["effects"]],
        "detectable_effect_80pct": [{"n": n, "sd": sd, "effect": detectable_effect(n, sd)}
            for sd in SPEC["paired_question_sd"] for n in SPEC["question_counts"]],
        "proposed_design_budget": {"questions": SPEC["proposed_questions"],
            "solvers": SPEC["proposed_solvers"], "pairs_per_solver": per_solver_pairs,
            "total_pairs": total_pairs, "responses": 2 * total_pairs,
            "maximum_reserved_tokens_per_pair": maximum,
            "maximum_response_tokens": total_pairs * maximum,
            "observed_qwen_1_7b_tokens_per_pair": pair["mean_tokens"],
            "observed_qwen_1_7b_seconds_per_pair": pair["mean_seconds"],
            "qwen_1_7b_slice_profile_tokens": per_solver_pairs * pair["mean_tokens"],
            "qwen_1_7b_slice_profile_hours": per_solver_pairs * pair["mean_seconds"] / 3600,
            "second_solver_runtime": "unknown; engineering pilot required",
            "setup_retry_and_router_cost": "additional; not included in response-only reservations",
            "collection_authorized_by_this_report": False},
        "limitations": ["Known-SD normal approximation; no claim of exact finite-sample power",
            "SD grid is hypothetical sensitivity, not estimated fresh-task variance",
            "Repeat responses do not add independent question groups",
            "This does not power the roadmap's AULC endpoint or multiple solver claims",
            "Small panel is diagnostic; independent confirmation still needs a final frozen model",
            "No question rows, references, sealed outcomes or fitted candidates are accessed"]}
    return result


def write_new(path, payload):
    with Path(path).open("x") as stream:
        import json
        json.dump(envelope(payload), stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "broader-signal-power-v1")
    args = parser.parse_args()
    if args.output.resolve() != args.root.resolve() / "broader-signal-power-v1":
        raise ValueError("Only the separately versioned planning directory is writable")
    sources = [Path(__file__), Path("tests/test_signal_study_power.py"), Path("docs/broader-signal-design.md")]
    plan = {"spec": SPEC, "source_sha256": {str(p): file_hash(p) for p in sources},
            "pinned_reports": PINNED, "no_fitting_generation_reference_access": True}
    with run_lock(args.output):
        write_new(args.output / "analysis-plan.json", plan)
        report = build(args.root)
        report["plan_sha256"] = digest(plan)
        write_new(args.output / "report.json", report)
    print({"report_sha256": digest(report), "response_budget": report["proposed_design_budget"]["maximum_response_tokens"]})


if __name__ == "__main__":
    main()
