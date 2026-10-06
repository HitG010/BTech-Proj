"""One cached scalar baseline fit and question-only preparation for a fresh guard test.

There is deliberately no collection, generation, scoring, or reference entry point.
"""

import argparse
import math
from pathlib import Path

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.data import normalized
from reasoning_budget.records import Question
from reasoning_budget.research_data import load_allocation
from reasoning_budget.runner import build_jobs
from reasoning_budget.storage import digest, read_json, run_lock, verified
from scripts import opportunity_panel_collect as original
from scripts import opportunity_panel_plan as old_child
from scripts import qwen06_router_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
BASE = original.BASE
OUTPUT = BASE / "qwen06-sparse-validation-v1"
CHILD = BASE / "reserve-children/qwen06-guard-fresh228-v1"
SPLIT = "guard_fresh228"
SEED = 20261018
JOB_SEED = 20261019
N = 228
MAX_ELIGIBLE = 32
LAM = 0.05
SOURCE_FILES = ("scripts/qwen06_sparse_validation.py", "tests/test_qwen06_sparse_validation.py",
                "docs/qwen06-sparse-validation-protocol.md",
                "scripts/qwen06_router_pilot.py", "scripts/opportunity_panel_collect.py",
                "scripts/opportunity_panel_plan.py", "src/reasoning_budget/data.py",
                "src/reasoning_budget/research_data.py", "src/reasoning_budget/runner.py",
                "src/reasoning_budget/scoring_v7.py", "src/reasoning_budget/storage.py")
SPEC = {"version": "qwen06-sparse-validation-v1", "purpose": "fresh sparse guard diagnostic",
        "training_groups": 64, "training_rows": 128, "fresh_questions": N,
        "selection_seed": SEED, "job_seed": JOB_SEED, "split": SPLIT,
        "max_eligible": MAX_ELIGIBLE, "lambda": LAM, "bootstrap_seed": SEED,
        "bootstrap_draws": 2000, "interval": [0.025, 0.975],
        "answer_cap": 512, "reasoning_cap": 2048, "closure_tokens": 2,
        "response_only_bound": N * 512 + MAX_ELIGIBLE * (2048 + 512 + 2),
        "proposed_global_tokens": 250000, "proposed_global_seconds": 21600,
        "proposed_setup_seconds": 900, "proposed_job_seconds": 600,
        "proposed_max_rss_bytes": 9 * 1024**3,
        "proposed_initial_invocations": 1, "proposed_explicit_resumes": 1,
        "proposed_max_setups": 2, "first_failure_stop": True,
        "automatic_resume": False, "collector": "unimplemented_locked"}


def fail(message):
    raise ValueError(message)


def _safe():
    for path in (BASE, OUTPUT, CHILD.parent, CHILD):
        if path.is_symlink():
            fail("Symlink in sparse-validation path")
    if OUTPUT.resolve() != BASE.resolve() / SPEC["version"]:
        fail("Sparse output escaped study root")
    if CHILD.resolve() != BASE.resolve() / "reserve-children" / CHILD.name:
        fail("Reserve child escaped study root")
    for root in (OUTPUT, CHILD):
        if root.exists() and any(p.is_symlink() for p in root.rglob("*")):
            fail("Symlink in sparse-validation artifact")


def _sources():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def _pins(paths):
    return {str(path): file_hash(path) for path in paths}


def _check_pins(pins):
    if any(file_hash(path) != sha for path, sha in pins.items()):
        fail("Pinned input changed")


def _write(path, payload):
    original.write_once(path, payload)


def _training_rows(rows):
    if (len(rows) != 128 or len({(r["question_id"], r["draw"]) for r in rows}) != 128
            or len({r["question_id"] for r in rows}) != 64
            or {r["draw"] for r in rows} != {0, 1}):
        fail("Expected 64 complete two-draw training groups")
    for r in rows:
        c, reject = r["features"][0], r["features"][2]
        if (type(c) not in (float, int) or not math.isfinite(c)
                or reject not in (0.0, 1.0)
                or r["direct_correct"] not in (0, 1)
                or r["thinking_correct"] not in (0, 1)
                or type(r["thinking_tokens"]) is not int or r["thinking_tokens"] < 0):
            fail("Training row has invalid feature, outcome, or cost")


def _encode_threshold(value):
    if value == math.inf:
        return "always"
    if value == -math.inf:
        return "never"
    if not math.isfinite(value):
        fail("Invalid threshold")
    return float(value)


def decode_threshold(value):
    if value == "always":
        return math.inf
    if value == "never":
        return -math.inf
    if type(value) not in (float, int) or not math.isfinite(value):
        fail("Invalid serialized threshold")
    return float(value)


def select_threshold(rows):
    """One full-data scalar fit. Inference uses confidence only."""
    _training_rows(rows)
    candidates = [-math.inf, *sorted({float(r["features"][0]) for r in rows}), math.inf]
    def objective(tau):
        actions = [r["features"][0] < tau for r in rows]
        gain = sum(a * (r["thinking_correct"] - r["direct_correct"]
                        - LAM * r["thinking_tokens"] / 1000)
                   for a, r in zip(actions, rows)) / len(rows)
        return gain, -sum(actions), -tau
    tau = max(candidates, key=objective)
    return {"threshold": _encode_threshold(tau), "training_gain": objective(tau)[0],
            "training_escalations": -objective(tau)[1],
            "candidates": len(candidates), "selection": "max_gain_then_fewer_escalations_then_lower_threshold",
            "feature": "postwarper_mean_generated_logprob", "rule": "confidence_strictly_less_than_threshold"}


def prepare_policy():
    _safe()
    with run_lock(OUTPUT / "policy-preparation"):
        if any((OUTPUT / name).exists() for name in ("policy-plan.json", "fit-started.json", "policy.json")):
            fail("Policy fit is one-time")
        pilot_plan, data = pilot.checked_plan()
        _training_rows(data["rows"])
        pilot_report = verified(pilot.OUTPUT / "report.json")
        if (pilot_report["plan_sha256"] != digest(pilot_plan)
                or pilot_report["rows_sha256"] != digest(data)
                or pilot_report["fit_count"] != 20):
            fail("Closed pilot report identity changed")
        old_inventory = pilot_plan["study_inventory"]
        if len(old_inventory) != 2652:
            fail("Closed study inventory size changed")
        pilot_files = sorted(p for p in pilot.OUTPUT.rglob("*") if p.is_file())
        if any(p.is_symlink() for p in pilot.OUTPUT.rglob("*")):
            fail("Symlink in completed pilot artifacts")
        pins = _pins(pilot_files + [ROOT / "scripts/qwen06_router_pilot.py"])
        plan = {"spec": SPEC, "source_file_sha256": _sources(),
                "environment": original.stable_environment(), "pilot_pins": pins,
                "old_study_inventory_sha256": digest(old_inventory),
                "old_study_inventory_count": len(old_inventory),
                "pilot_plan_sha256": digest(pilot_plan), "training_rows_sha256": digest(data),
                "scope": "one full-data cached scalar threshold fit; no fresh allocation"}
        _write(OUTPUT / "policy-plan.json", plan)
        _write(OUTPUT / "fit-started.json", {"plan_sha256": digest(plan), "one_fit": True})
        fit = select_threshold(data["rows"])
        # A long fit must not publish a policy against changed cached inputs.
        post_plan, post_data = pilot.checked_plan()
        if (digest(post_plan) != digest(pilot_plan) or digest(post_data) != digest(data)
                or _sources() != plan["source_file_sha256"]
                or original.stable_environment() != plan["environment"]
                or {str(p) for p in pilot.OUTPUT.rglob("*") if p.is_file()}
                   != {str(p) for p in pilot_files}):
            fail("Cached inputs, sources, or environment changed during threshold fit")
        _check_pins(pins)
        tau = decode_threshold(fit["threshold"])
        plain = [r["features"][0] < tau for r in data["rows"]]
        or_reject = [a or bool(r["features"][2]) for a, r in zip(plain, data["rows"])]
        policy = {"plan_sha256": digest(plan), "training_rows_sha256": digest(data),
                  "fit": fit, "same_threshold_for_both": True,
                  "training_plain_escalations": sum(plain),
                  "training_or_reject_escalations": sum(or_reject),
                  "training_reject_rows": sum(bool(r["features"][2]) for r in data["rows"]),
                  "status": "fitted_once_question_preparation_pending_independent_review",
                  "no_reference_or_generation_access": True}
        _write(OUTPUT / "policy.json", policy)
        return {"policy_sha256": digest(policy), "threshold": fit["threshold"]}


def checked_policy():
    _safe()
    plan, marker, policy = (verified(OUTPUT / name) for name in
                            ("policy-plan.json", "fit-started.json", "policy.json"))
    if (plan["spec"] != SPEC or plan["source_file_sha256"] != _sources()
            or plan["environment"] != original.stable_environment()
            or marker != {"plan_sha256": digest(plan), "one_fit": True}
            or policy["plan_sha256"] != digest(plan)
            or policy["status"] != "fitted_once_question_preparation_pending_independent_review"):
        fail("Frozen policy identity changed")
    _check_pins(plan["pilot_pins"])
    live_pilot = {str(p) for p in pilot.OUTPUT.rglob("*") if p.is_file()}
    pinned_pilot = {p for p in plan["pilot_pins"] if Path(p).is_relative_to(pilot.OUTPUT)}
    if live_pilot != pinned_pilot:
        fail("Completed pilot artifact inventory changed")
    pilot_plan, data = pilot.checked_plan()
    if (plan["pilot_plan_sha256"] != digest(pilot_plan)
            or plan["training_rows_sha256"] != digest(data)
            or policy["training_rows_sha256"] != digest(data)
            or plan["old_study_inventory_sha256"] != digest(pilot_plan["study_inventory"])
            or plan["old_study_inventory_count"] != len(pilot_plan["study_inventory"])):
        fail("Closed training inputs changed")
    return plan, policy


def _claimed_reserve(allocation, sibling_root, exclude=None):
    reserve = {r["question"]["id"]: r for r in allocation["roles"]["reserve"]}
    reserve_prompts = {normalized(r["question"]["prompt"]) for r in reserve.values()}
    other = [r for role, rows in allocation["roles"].items() if role != "reserve" for r in rows]
    other_ids = {r["question"]["id"] for r in other}
    other_prompts = {normalized(r["question"]["prompt"]) for r in other}
    if (len(reserve) != len(allocation["roles"]["reserve"])
            or len(reserve_prompts) != len(reserve) or set(reserve) & other_ids
            or reserve_prompts & other_prompts):
        fail("Parent role/prompt overlap")
    claimed_ids, claimed_prompts, siblings = set(), set(), {}
    for child in sibling_root.iterdir():
        if child.name == ".lock" or child == exclude:
            continue
        if child.is_symlink() or not child.is_dir():
            fail("Unauditable reserve-child entry")
        manifest = child / "child-manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            fail("Unauditable reserve-child manifest")
        payload = verified(manifest)
        if payload["parent_payload_sha256"] != digest(allocation):
            fail("Sibling parent identity changed")
        for row in payload["selected"]:
            qid = row["parent_question"]["id"]
            prompt = normalized(row["parent_question"]["prompt"])
            parent = reserve.get(qid)
            if (parent is None or qid in claimed_ids or prompt in claimed_prompts
                    or row["parent_question"] != parent["question"]
                    or any(row[k] != parent[k] for k in
                           ("upstream_index", "pool", "group_id", "normalized_prompt_sha256"))
                    or row["normalized_prompt_sha256"] != digest(prompt)
                    or row["child_question"] != dict(parent["question"], split=row["child_question"]["split"])):
                fail("Sibling overlap or provenance changed")
            claimed_ids.add(qid)
            claimed_prompts.add(prompt)
        siblings[child.name] = file_hash(manifest)
    return reserve, claimed_ids, siblings


def select_fresh(allocation, siblings, exclude=None):
    reserve, claimed, pins = _claimed_reserve(allocation, siblings, exclude)
    remaining = [r for qid, r in reserve.items() if qid not in claimed]
    if len(remaining) < N:
        fail("Fewer than 228 unclaimed reserve questions")
    ordered = sorted(remaining, key=lambda r: (digest({"seed": SEED,
        "id": r["question"]["id"], "prompt": normalized(r["question"]["prompt"])}),
        r["question"]["id"]))
    chosen = []
    for row in ordered[:N]:
        q = row["question"]
        if (row["pool"] != "external" or row["group_id"] != q["id"]
                or row["normalized_prompt_sha256"] != digest(normalized(q["prompt"]))):
            fail("Parent source provenance changed")
        cq = dict(q, split=SPLIT)
        Question(**cq)
        chosen.append({"parent_question": q, "child_question": cq,
                       "upstream_index": row["upstream_index"], "pool": row["pool"],
                       "normalized_prompt_sha256": row["normalized_prompt_sha256"],
                       "group_id": row["group_id"]})
    return chosen, pins, len(remaining)


def _review(policy):
    review = verified(OUTPUT / "policy-review.json")
    if review != {"policy_sha256": digest(policy),
                   "decision": "independently_reviewed_allow_question_only_preparation"}:
        fail("Independent policy review is required before question selection")
    return review


def _jobs(selected, dataset):
    old_protocol = original.read_protocol(check_assets=True)
    if old_protocol["scoring_version"] != "numeric-v7":
        fail("Frozen numeric-v7 scorer identity changed")
    arm = old_protocol["arms"][pilot.SOLVER]
    values = dict(arm["config"])
    values.update(name="qwen06-guard-fresh228", seed=JOB_SEED, samples=1, split=SPLIT,
                  data_dir=str(dataset), output_dir=str(OUTPUT / "unused-runner"))
    values["limits"] = {"max_tokens": SPEC["proposed_global_tokens"],
                        "max_elapsed_seconds": SPEC["proposed_global_seconds"],
                        "job_seconds": SPEC["proposed_job_seconds"],
                        "max_consecutive_failures": 1}
    # Generation fields, local model revision, prompt and decoder remain verbatim.
    config = original.from_dict(values)
    metadata = arm["backend_metadata"]
    original.check_metadata(config, metadata)
    if (config.answer_tokens != 512 or config.reasoning_tokens != 2048
            or metadata["closure_tokens"] != 2 or config.modes != ["direct", "thinking"]):
        fail("Solver caps or modes changed")
    jobs = [j.to_dict() for j in build_jobs(config,
            [Question(**r["child_question"]) for r in selected], metadata)]
    if (len(jobs) != 2 * N or len({j["id"] for j in jobs}) != 2 * N
            or len({j["seed"] for j in jobs}) != 2 * N
            or any(j["sample"] != 0 or j["mode"] not in ("direct", "thinking") for j in jobs)
            or sum(j["max_tokens"] for j in jobs if j["mode"] == "direct") != N * 512):
        fail("Potential job inventory changed")
    return {"config": config.to_dict(), "backend_metadata": metadata,
            "asset_file_sha256": arm["asset_file_sha256"],
            "jobs": jobs, "parent_protocol_sha256": digest(old_protocol),
            "generation_implementation_sha256": old_protocol["generation_implementation_sha256"],
            "scoring_version": old_protocol["scoring_version"],
            "scoring_implementation_sha256": old_protocol["scoring_implementation_sha256"]}


def prepare_questions():
    _safe()
    plan, policy = checked_policy()
    _review(policy)
    if policy["fit"]["threshold"] == "always":
        fail("No fresh policy contrast: always-thinking plain confidence makes the parser guard identical")
    with run_lock(OUTPUT / "question-preparation"), run_lock(CHILD.parent):
        if CHILD.exists() or (OUTPUT / "question-protocol.json").exists():
            fail("Fresh question selection is one-time")
        old_child.verify(BASE, ROOT)
        allocation = load_allocation(BASE / "allocations")
        selected, sibling_pins, remaining = select_fresh(allocation, CHILD.parent)
        if remaining != 484 or set(sibling_pins) != {old_child.CHILD}:
            fail("Expected exactly 484 unclaimed reserve questions after old 64 child")
        dataset = CHILD / "dataset"
        arm = _jobs(selected, dataset)
        CHILD.mkdir()
        dataset.mkdir()
        rows = [r["child_question"] for r in selected]
        from reasoning_budget.storage import atomic_json
        atomic_json(dataset / "questions.json", rows)
        atomic_json(dataset / "manifest.json", {"schema_version": 1,
            "metadata": {"role": SPLIT, "gold_deferred": True,
                         "parent_payload_sha256": digest(allocation)},
            "questions_sha256": digest(rows), "gold_sha256": None,
            "splits": {SPLIT: [r["id"] for r in rows]}})
        child_payload = {"schema_version": 1, "status": "prepared_question_only_collection_locked",
            "parent_file_sha256": file_hash(BASE / "allocations/manifest.json"),
            "parent_payload_sha256": digest(allocation), "source": allocation["source"],
            "seed": SEED, "selected": selected, "siblings_file_sha256": sibling_pins,
            "unclaimed_before_selection": remaining, "policy_sha256": digest(policy),
            "gold_sha256": None, "collector": "unimplemented_locked"}
        _write(CHILD / "child-manifest.json", child_payload)
        _write(CHILD / "preparation-plan.json", {"child_sha256": digest(child_payload),
            "dataset_file_sha256": _pins([dataset / "questions.json", dataset / "manifest.json"])})
        protocol = {"spec": SPEC, "policy_plan_sha256": digest(plan),
            "policy_sha256": digest(policy), "policy_review_sha256": digest(_review(policy)),
            "child_sha256": digest(child_payload), "parent_payload_sha256": digest(allocation),
            "parent_file_sha256": child_payload["parent_file_sha256"],
            "source_file_sha256": _sources(), "environment": original.stable_environment(),
            "arm": arm, "dataset_file_sha256": _pins([dataset / "questions.json",
                                                            dataset / "manifest.json"]),
            "status": "question_only_prepared_collection_unimplemented_locked",
            "future_endpoint": "all_228_direct_and_all_eligible_thinking_exited_then_only_eligible_training_references",
            "no_generation_or_reference_access": True}
        _write(OUTPUT / "question-protocol.json", protocol)
        return {"questions": N, "potential_jobs": 2 * N,
                "child_sha256": digest(child_payload), "protocol_sha256": digest(protocol)}


def checked_questions():
    _safe()
    plan, policy = checked_policy()
    review = _review(policy)
    protocol = verified(OUTPUT / "question-protocol.json")
    child = verified(CHILD / "child-manifest.json")
    prep = verified(CHILD / "preparation-plan.json")
    allocation = load_allocation(BASE / "allocations")
    old_child.verify(BASE, ROOT)
    chosen, pins, remaining = select_fresh(allocation, CHILD.parent, CHILD)
    if remaining != 484 or set(pins) != {old_child.CHILD}:
        fail("Reserve sibling census changed")
    dataset = CHILD / "dataset"
    rows = read_json(dataset / "questions.json")
    manifest = read_json(dataset / "manifest.json")
    if (child["selected"] != chosen or child["siblings_file_sha256"] != pins
            or child["unclaimed_before_selection"] != remaining
            or child["parent_payload_sha256"] != digest(allocation)
            or child["parent_file_sha256"] != file_hash(BASE / "allocations/manifest.json")
            or child["policy_sha256"] != digest(policy)
            or child["seed"] != SEED or child["source"] != allocation["source"]
            or child["gold_sha256"] is not None
            or child["collector"] != "unimplemented_locked"
            or child["status"] != "prepared_question_only_collection_locked"
            or rows != [r["child_question"] for r in chosen]
            or manifest != {"schema_version": 1, "metadata": {"role": SPLIT,
                "gold_deferred": True, "parent_payload_sha256": digest(allocation)},
                "questions_sha256": digest(rows), "gold_sha256": None,
                "splits": {SPLIT: [r["id"] for r in rows]}}
            or (dataset / "gold.json").exists() or (dataset / "gold.json").is_symlink()
            or prep != {"child_sha256": digest(child), "dataset_file_sha256":
                        _pins([dataset / "questions.json", dataset / "manifest.json"])}):
        fail("Fresh question child changed")
    expected_arm = _jobs(chosen, dataset)
    if (protocol["spec"] != SPEC or protocol["source_file_sha256"] != _sources()
            or protocol["environment"] != original.stable_environment()
            or protocol["policy_plan_sha256"] != digest(plan)
            or protocol["policy_sha256"] != digest(policy)
            or protocol["policy_review_sha256"] != digest(review)
            or protocol["child_sha256"] != digest(child)
            or protocol["parent_payload_sha256"] != digest(allocation)
            or protocol["parent_file_sha256"] != child["parent_file_sha256"]
            or protocol["arm"] != expected_arm
            or protocol["dataset_file_sha256"] != prep["dataset_file_sha256"]
            or protocol["status"] != "question_only_prepared_collection_unimplemented_locked"
            or protocol["no_generation_or_reference_access"] is not True):
        fail("Fresh question protocol changed")
    return protocol


def eligibility(direct_rows, direct_jobs, threshold):
    """Gold-free all-direct endpoint: reject AND plain-confidence accepts."""
    from reasoning_budget import scoring_v7
    if (len(direct_jobs) != N or len({j["id"] for j in direct_jobs}) != N
            or len({j["question_id"] for j in direct_jobs}) != N
            or any(j["mode"] != "direct" or j.get("sample", 0) != 0 for j in direct_jobs)):
        fail("Expected 228 distinct direct jobs")
    expected = {j["id"]: j for j in direct_jobs}
    if len(direct_rows) != N or {r["job"]["id"] for r in direct_rows} != set(expected):
        fail("All 228 direct outputs must finish before eligibility")
    tau = decode_threshold(threshold)
    eligible = []
    for row in direct_rows:
        job = row["job"]
        if (job != expected[job["id"]] or job["mode"] != "direct"
                or row["status"] != "completed" or not isinstance(row.get("result"), dict)
                or row["result"].get("termination") == "timeout"):
            fail("Direct endpoint job or status changed")
        c = row["result"].get("mean_generated_logprob")
        if type(c) not in (int, float) or not math.isfinite(c):
            fail("Finite postwarper confidence required")
        _, status = scoring_v7.extract_record(row)
        if status not in ("ok", "invalid_number", "incomplete", "conflicting"):
            fail("Invalid gold-free parser status")
        if status != "ok" and not (c < tau):
            eligible.append(job["question_id"])
    if len(set(eligible)) != len(eligible):
        fail("Duplicate eligible question")
    if len(eligible) > MAX_ELIGIBLE:
        fail("Hard resource stop: more than 32 eligible; no subsample")
    return sorted(eligible)


def sparse_delta(eligible_ids, thinking_outcomes, question_ids, *, seed=SEED, draws=2000):
    """Pure fixed-action conditional estimate; no gold for unchanged questions."""
    if (type(seed) is not int or type(draws) is not int or draws <= 0
            or len(question_ids) != N or len(set(question_ids)) != N
            or len(eligible_ids) != len(set(eligible_ids))
            or len(eligible_ids) > MAX_ELIGIBLE
            or not set(eligible_ids) <= set(question_ids)
            or set(thinking_outcomes) != set(eligible_ids)):
        fail("Sparse endpoint coverage changed")
    gains = {}
    successes = 0
    tokens = 0
    for q in question_ids:
        if q not in thinking_outcomes:
            gains[q] = 0.0
            continue
        outcome = thinking_outcomes[q]
        y, t = outcome["thinking_correct"], outcome["thinking_tokens"]
        if (type(y) is not int or y not in (0, 1)
                or type(t) is not int or t < 0 or t > 2562):
            fail("Invalid eligible outcome")
        gains[q] = y - LAM * t / 1000
        successes += y
        tokens += t
    values = np.asarray([gains[q] for q in question_ids], dtype=float)
    rng = np.random.default_rng(seed)
    boots = np.mean(values[rng.integers(0, N, size=(draws, N))], axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    point = float(values.mean())
    return {"mean_incremental_utility": point, "ci95": [float(lo), float(hi)],
            "accuracy_delta": successes / N, "extra_thinking_tokens_per_question": tokens / N,
            "eligible_events": len(eligible_ids), "event_rate": len(eligible_ids) / N,
            "conditional_thinking_accuracy": successes / len(eligible_ids) if eligible_ids else None,
            "further_study_screen": point >= 0.01 and lo > 0,
            "bootstrap_seed": seed, "bootstrap_draws": draws,
            "scope": "fixed_sparse_actions_conditional_not_confirmation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare-policy", "verify-policy",
                                            "prepare-questions", "verify-questions"))
    args = parser.parse_args()
    if args.command == "prepare-policy":
        result = prepare_policy()
    elif args.command == "verify-policy":
        result = {"policy_sha256": digest(checked_policy()[1])}
    elif args.command == "prepare-questions":
        result = prepare_questions()
    else:
        result = {"protocol_sha256": digest(checked_questions())}
    print(result)


if __name__ == "__main__":
    main()
