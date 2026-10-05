"""Question-role and power sensitivity for a conditional 0.6B follow-up.

This planning command never selects questions, fits policies, scores outputs,
loads a model, or reads upstream references. It deserializes existing question-
only manifests and completed report/protocol metadata for integrity accounting.
"""

import argparse
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, run_lock, verified
from scripts.opportunity_panel_collect import write_once
from scripts.signal_study_power import detectable_effect, power, required_n

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
OUTPUT = BASE / "qwen06-next-design-v1"
SOURCES = ("scripts/qwen06_next_design.py", "tests/test_qwen06_next_design.py",
           "docs/qwen06-next-experiment.md", "scripts/signal_study_power.py")
SPEC = {"version": "qwen06-next-design-v1", "alpha": .05, "power": .8,
        "effects": [.01, .03, .05], "paired_sd": [.05, .10, .16, .25],
        "counts": [64, 128, 200, 228, 484, 2000],
        "conditional_fresh_questions": 228, "allocation_authorized": False,
        "scope": "known-SD sensitivity for learner-minus-confidence; not AULC or refit power"}
EXPECTED_REPORT = "f3f0d33ca554bf5f5ba724fc87c60601a58fcde8939a4172a932aca28acac6fd"


def audit_roles(allocation, children):
    """Reject overlapping or unauditable earmarks; never mutate parent roles."""
    reserve = allocation["roles"]["reserve"]
    parent = {r["question"]["id"]: r for r in reserve}
    if len(parent) != len(reserve):
        raise ValueError("Duplicate reserve IDs")
    prompts = {r["normalized_prompt_sha256"] for r in reserve}
    if len(prompts) != len(reserve):
        raise ValueError("Duplicate reserve prompts")
    claimed, claimed_prompts = set(), set()
    for child in children:
        if child["parent_payload_sha256"] != digest(allocation):
            raise ValueError("Child parent changed")
        for row in child["selected"]:
            key = row["parent_question"]["id"]
            if (key not in parent or key in claimed
                    or row["parent_question"] != parent[key]["question"]
                    or row["normalized_prompt_sha256"] != parent[key]["normalized_prompt_sha256"]
                    or row["normalized_prompt_sha256"] in claimed_prompts
                    or row["upstream_index"] != parent[key]["upstream_index"]):
                raise ValueError("Child membership, duplicate, or source mismatch")
            claimed.add(key)
            claimed_prompts.add(row["normalized_prompt_sha256"])
    free = sorted(set(parent) - claimed)
    return {"reserve": len(parent), "claimed": len(claimed), "unclaimed": len(free),
            "unclaimed_id_set_sha256": digest(free), "children": len(children)}


def calculate(roles, direct_cap, thinking_cap):
    n = SPEC["conditional_fresh_questions"]
    if roles["unclaimed"] < n or min(direct_cap, thinking_cap) <= 0:
        raise ValueError("Conditional design exceeds capacity")
    return {"spec": SPEC, "role_audit": roles,
        "power_grid": [{"effect": effect, "sd": sd,
            "required_n_80pct": required_n(effect, sd),
            "power_by_n": {str(k): power(k, effect, sd) for k in SPEC["counts"]}}
            for sd in SPEC["paired_sd"] for effect in SPEC["effects"]],
        "detectable_80pct": [{"n": k, "sd": sd, "effect": detectable_effect(k, sd)}
            for sd in SPEC["paired_sd"] for k in SPEC["counts"]],
        "conditional_design": {"questions": n, "responses": 2 * n,
            "draws_per_mode": 1, "response_only_token_bound": n * (direct_cap + thinking_cap),
            "remaining_reserve_if_allocated": roles["unclaimed"] - n,
            "setup_retry_router_limits": "must be frozen in a separate collection protocol",
            "status": "proposed only; no allocation or generation"},
        "limitations": ["Known-SD normal approximation, not exact finite-sample power",
            "The learner-minus-confidence effect and single-draw SD are unknown",
            "The +.152677 confidence-minus-direct gain does not size this comparison",
            "64 reused groups are development; repeats do not multiply independent sample size",
            "228 groups do not generally power +.01; +.03 at SD .16 is a sensitivity scenario",
            "No training/refit uncertainty or acquisition learning-curve power included"]}


def build():
    paths = [BASE / "allocations/manifest.json",
             BASE / "opportunity-panel-v1/protocol.json",
             BASE / "opportunity-panel-v1/completion-v1/report.json"]
    allocation, protocol, report = [verified(p) for p in paths]
    if (digest(report) != EXPECTED_REPORT
            or report["parent_protocol_sha256"] != digest(protocol)):
        raise ValueError("Completed study identity changed")
    registry = BASE / "reserve-children"
    children = []
    for entry in sorted(registry.iterdir()):
        if entry.name == ".lock":
            continue
        if entry.is_symlink() or not entry.is_dir():
            raise ValueError("Unauditable reserve registry entry")
        path = entry / "child-manifest.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing reserve child manifest")
        paths.append(path)
        children.append(verified(path))
    roles = audit_roles(allocation, children)
    if roles["reserve"] != 548 or roles["claimed"] != 64 or roles["unclaimed"] != 484:
        raise ValueError("Reviewed reserve boundary changed")
    jobs = protocol["arms"]["qwen3-0.6b"]["jobs"]
    caps = {mode: {j["max_tokens"] for j in jobs if j["mode"] == mode}
            for mode in ("direct", "thinking")}
    if caps != {"direct": {512}, "thinking": {2562}}:
        raise ValueError("Frozen response caps changed")
    report = calculate(roles, 512, 2562)
    report["input_sha256"] = {str(p.relative_to(ROOT)): file_hash(p) for p in paths}
    return report


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    plan = {"spec": SPEC, "source_sha256": {p: file_hash(ROOT / p) for p in SOURCES},
            "no_fitting_generation_reference_access": True}
    result = build()
    with run_lock(OUTPUT):
        write_once(OUTPUT / "plan.json", plan)
        result["plan_sha256"] = digest(plan)
        write_once(OUTPUT / "report.json", result)
    print({"report_sha256": digest(result), "conditional_budget": result["conditional_design"],
           "unclaimed": result["role_audit"]["unclaimed"]})


if __name__ == "__main__":
    main()
