"""Additive completion of the frozen audit after a cached-summary schema error."""

import argparse
import importlib.metadata
from pathlib import Path

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, verified
from scripts import audit_clm_signal as audit

OUTPUT = audit.OUTPUT / "completion-v1"


def checked_base():
    audit.checked_output()
    plan = verified(audit.OUTPUT / "plan.json")
    if plan["spec"] != audit.SPEC or (audit.OUTPUT / "report.json").exists():
        raise ValueError("Only the incomplete unchanged frozen audit is eligible")
    for path, sha in plan["source_file_sha256"].items():
        if file_hash(path) != sha:
            raise ValueError("Original frozen audit source changed")
    if plan["packages"] != {name: importlib.metadata.version(name) for name in plan["packages"]}:
        raise ValueError("Original audit packages changed")
    if OUTPUT.is_symlink() or OUTPUT.resolve() != audit.OUTPUT.resolve() / "completion-v1":
        raise ValueError("Completion output escaped its separate directory")
    return plan


def fixed_cost_sensitivity(prior):
    summaries = [prior["statistics"]["conditions"][name]["summary"]
        for name in ("k4_A_to_B", "k4_B_to_A")]
    accuracy = float(np.mean([s["clm_zero_shot"]["mean_accuracy"] - s["confidence"]["mean_accuracy"]
        for s in summaries]))
    tokens = float(np.mean([s["clm_zero_shot"]["mean_tokens"] - s["confidence"]["mean_tokens"]
        for s in summaries]))
    return {"accuracy_difference": accuracy, "additional_tokens": tokens,
        "break_even_lambda": audit.break_even(accuracy, tokens),
        "warning": "descriptive fixed actions tuned at lambda=.05; no retuning or endpoint change; encoder cost omitted"}


def prepare():
    base = checked_base()
    files = [Path(__file__), audit.probe.local.ROOT / "tests/test_complete_clm_signal_audit.py",
        audit.probe.local.ROOT / "docs/clm-audit-completion.md"]
    plan = {"base_plan_sha256": digest(base), "base_source_preserved": True,
        "deviation": "First execution raised KeyError('accuracy') after rank calculations; no report written",
        "correction": "Read mean_accuracy/mean_tokens in prior cached summaries; all rank math/spec unchanged",
        "source_file_sha256": {str(p.resolve()): file_hash(p) for p in files}}
    audit.probe.local.write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "completion_plan_sha256": digest(plan)}


def execute():
    base = checked_base()
    plan = verified(OUTPUT / "plan.json")
    if plan["base_plan_sha256"] != digest(base) or (OUTPUT / "report.json").exists():
        raise ValueError("Completed or changed audit cannot be restarted")
    for path, sha in plan["source_file_sha256"].items():
        if file_hash(path) != sha:
            raise ValueError("Frozen completion source changed")
    panel, prior, margins, identity = audit.inputs()
    if identity != base["inputs"]:
        raise ValueError("Original frozen audit input changed")
    sensitivity = fixed_cost_sensitivity(prior)
    statistics = audit.signal_statistics(panel["d"], panel["t"], panel["z"][..., 0], margins)
    statistics["fixed_policy_cost_sensitivity"] = sensitivity
    from scripts.verify_phase2_repeat import verify
    preservation = verify(audit.probe.STUDY)
    report = {"base_plan_sha256": digest(base), "completion_plan_sha256": digest(plan),
        "spec": audit.SPEC, "inputs": identity, "statistics": statistics,
        "protected_originals_verified": preservation["protected_originals_verified"],
        "no_fit_inference_generation_references": True, "cloud_spend_usd": 0.}
    audit.probe.local.write_new(OUTPUT / "report.json", report)
    return {"report_sha256": digest(report), "statistics": statistics,
        "protected_originals_verified": report["protected_originals_verified"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "execute"])
    args = parser.parse_args()
    print(prepare() if args.command == "prepare" else execute())


if __name__ == "__main__":
    main()
