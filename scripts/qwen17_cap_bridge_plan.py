"""Preparation only for a matched, development-only 1.7B thinking-cap bridge.

No generation, model construction, reference access, scoring or fitting entry point.
Preparation is locked until the fresh 0.6B validation is complete and reviewed.
"""

import argparse
import time
from copy import deepcopy
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob
from reasoning_budget.storage import atomic_json, digest, read_json, run_lock, verified
from scripts import opportunity_panel_collect as original
from scripts import qwen17_solver_diagnosis as diagnosis

ROOT = Path(__file__).resolve().parents[1]
BASE = original.BASE
OUTPUT = BASE / "qwen17-cap-bridge-v1"
VALIDATION = BASE / "qwen06-sparse-validation-v1/runtime-v1"
SOLVER = "qwen3-1.7b"
FILES = ("scripts/qwen17_cap_bridge_plan.py", "tests/test_qwen17_cap_bridge_plan.py",
         "docs/qwen17-cap-bridge-protocol.md", "scripts/qwen17_solver_diagnosis.py",
         "src/reasoning_budget/backend.py", "src/reasoning_budget/config.py",
         "src/reasoning_budget/records.py", "src/reasoning_budget/runner.py",
         "src/reasoning_budget/storage.py", "src/reasoning_budget/scoring_v7.py")
SPEC = {"version": "qwen17-cap-bridge-v1", "scope": "cap-enriched cached-development",
        "trigger": "original thinking forced_closure with reasoning_tokens=2048",
        "cells": 18, "question_groups": 11, "arms": {"control_2k": 2048, "extended_4k": 4096},
        "answer_tokens": 512, "closure_tokens": 2, "responses": 36,
        "response_only_bound": 129096, "proposed_global_tokens": 160000,
        "proposed_global_seconds": 14400, "setup_seconds": 900, "job_seconds": 600,
        "maximum_invocations": 2, "maximum_setups": 2, "first_failure_stop": True,
        "automatic_resume": False, "lambda": 0.05, "bootstrap_seed": 20261020,
        "bootstrap_draws": 2000, "interval": [0.025, 0.975],
        "primary_grouping": "mean cells within question, then mean 11 questions",
        "generation": "unimplemented_locked", "cloud_spend_usd": 0}


def fail(message):
    raise ValueError(message)


def sources():
    return {name: file_hash(ROOT / name) for name in FILES}


def require_validation_review(directory=VALIDATION):
    """Ordering gate only; a negative scientific result may still pass review."""
    directory = Path(directory)
    for name in ("status.json", "report.json", "completion-review-verification.json"):
        path = directory / name
        if not path.is_file() or path.is_symlink():
            fail("Fresh validation must be terminal complete and independently reviewed first")
    status = verified(directory / "status.json")
    report = verified(directory / "report.json")
    review = verified(directory / "completion-review-verification.json")
    if (status.get("state") != "complete" or status.get("report_sha256") != digest(report)
            or review.get("checks_passed") is not True
            or review.get("report_sha256") != digest(report)):
        fail("Fresh validation completion/review identity changed")
    return {name: file_hash(directory / name) for name in
            ("status.json", "report.json", "completion-review-verification.json")}


def capped_cells(protocol, records):
    """Select by original output metadata only, never correctness or confidence."""
    arm = protocol["arms"][SOLVER]
    expected = {job["id"]: job for job in arm["jobs"]}
    if len(records) != 256 or len({row["job"]["id"] for row in records}) != 256:
        fail("Complete original 1.7B arm required")
    by_id = {row["job"]["id"]: row for row in records}
    if set(by_id) != set(expected):
        fail("Original 1.7B job coverage changed")
    cells = []
    for job in arm["jobs"]:
        row = by_id[job["id"]]
        if row["job"] != job or row["status"] != "completed":
            fail("Original generation identity changed")
        if job["mode"] != "thinking" or not row["result"]["forced_closure"]:
            continue
        if row["result"]["reasoning_tokens"] != 2048 or job["sample"] not in (0, 1):
            fail("Forced-closure trigger differs from frozen 2k cap")
        cells.append({"question_id": job["question_id"], "draw": job["sample"],
                      "generation_seed": job["seed"], "original_job": job,
                      "original_record_sha256": digest(row)})
    if (len(cells) != SPEC["cells"]
            or len({cell["question_id"] for cell in cells}) != SPEC["question_groups"]
            or len({(cell["question_id"], cell["draw"]) for cell in cells}) != SPEC["cells"]
            or len({cell["generation_seed"] for cell in cells}) != SPEC["cells"]):
        fail("Expected exactly 18 cap-hit cells on 11 development questions")
    return cells


def matched_jobs(protocol, cells, output=OUTPUT):
    """Construct identities with explicitly inherited seeds; never derive arm seeds."""
    base = protocol["arms"][SOLVER]
    arms = {}
    for name, cap in SPEC["arms"].items():
        config = deepcopy(base["config"])
        config.update(name=f"qwen17-cap-{name}", reasoning_tokens=cap,
                      data_dir=str(Path(output) / "question-snapshot"),
                      output_dir=str(Path(output) / name))
        config["limits"] = {"max_tokens": SPEC["proposed_global_tokens"],
                            "max_elapsed_seconds": SPEC["proposed_global_seconds"],
                            "job_seconds": SPEC["job_seconds"], "max_consecutive_failures": 1}
        # Keep both decoder entries so resolved metadata stays identical to the
        # original backend. The manual catalog contains only thinking jobs.
        config = original.from_dict(config).to_dict()
        jobs = []
        for cell in cells:
            old = cell["original_job"]
            identity = {"question": deepcopy(old["identity"]["question"]),
                        "backend": deepcopy(base["backend_metadata"]), "config": config,
                        "mode": "thinking", "sample": cell["draw"],
                        "protocol_version": original.GENERATION_PROTOCOL,
                        "generation_seed": cell["generation_seed"],
                        "bridge_version": SPEC["version"], "bridge_arm": name,
                        "original_job_id": old["id"]}
            jobs.append(GenerationJob(digest(identity), cell["question_id"], "thinking",
                                      cell["draw"], cell["generation_seed"], cap + 514,
                                      identity).to_dict())
        arms[name] = {"config": config, "backend_metadata": deepcopy(base["backend_metadata"]),
                      "asset_file_sha256": deepcopy(base["asset_file_sha256"]), "jobs": jobs}
    all_jobs = [job for arm in arms.values() for job in arm["jobs"]]
    if (len(all_jobs) != 36 or len({job["id"] for job in all_jobs}) != 36
            or sum(job["max_tokens"] for job in all_jobs) != SPEC["response_only_bound"]):
        fail("Matched response identities or reservation bound changed")
    if any(left["seed"] != right["seed"] for left, right in
           zip(arms["control_2k"]["jobs"], arms["extended_4k"]["jobs"])):
        fail("Matched arms must use identical original per-cell seeds")
    return arms


def question_snapshot(protocol, cells):
    by_question = {row["child_question"]["id"]: row for row in protocol["selected"]}
    ids = sorted({cell["question_id"] for cell in cells})
    selected = [by_question[qid] for qid in ids]
    for cell in cells:
        if cell["original_job"]["identity"]["question"] != by_question[cell["question_id"]]["child_question"]:
            fail("Cached cell and selected source question disagree")
    return {"metadata": {"role": "cap_enriched_development_reuse", "gold_sha256": None,
                         "reserve_allocation_changed": False},
            "questions": [row["child_question"] for row in selected],
            "selected_training_source_rows": selected}


def dataset_manifest(snapshot):
    questions = snapshot["questions"]
    splits = {}
    for question in questions:
        splits.setdefault(question["split"], []).append(question["id"])
    return {"schema_version": 1, "metadata": snapshot["metadata"],
            "questions_sha256": digest(questions), "gold_sha256": None, "splits": splits}


def shared_reasoning_prefix(control, extended, *, close_ids=(151668, 151643, 151645)):
    """Engineering check only: answer streams after a forced close may differ."""
    a = control["result"]["metadata"]["reasoning_token_ids"]
    b = extended["result"]["metadata"]["reasoning_token_ids"]
    if not a or not b or any(type(t) is not int or t < 0 for t in a + b):
        fail("Nonempty valid reasoning tokens required for prefix comparison")
    length = min(len(a), len(b))
    for sequence in (a, b):
        stop = next((i + 1 for i, token in enumerate(sequence) if token in close_ids), len(sequence))
        length = min(length, stop)
    return {"compared_tokens": length, "matches": a[:length] == b[:length],
            "scope": "shared reasoning through first close/EOS/shorter cap; not final answer equality"}


def prepare():
    """Question snapshot and potential jobs only; no model or scorer invocation."""
    if OUTPUT.is_symlink() or OUTPUT.resolve() != BASE.resolve() / SPEC["version"]:
        fail("Cap bridge path escaped study root")
    with run_lock(OUTPUT / "preparation"):
        if (OUTPUT / "prepare-started.json").exists() or (OUTPUT / "plan.json").exists():
            fail("Cap bridge preparation is one-time")
        ordering_pins = require_validation_review()
        old_plan, rows, protocol = diagnosis.checked()
        _, _, records, _, _, _ = diagnosis.inputs()
        cells = capped_cells(protocol, records[SOLVER])
        snapshot = question_snapshot(protocol, cells)
        arms = matched_jobs(protocol, cells)
        pins = sources()
        marker = {"spec": SPEC, "source_file_sha256": pins, "started_at": time.time()}
        original.write_once(OUTPUT / "prepare-started.json", marker)
        after, after_rows, after_protocol = diagnosis.checked()
        if (digest(after) != digest(old_plan) or digest(after_rows) != digest(rows)
                or digest(after_protocol) != digest(protocol) or sources() != pins
                or require_validation_review() != ordering_pins):
            fail("Cap bridge inputs changed during preparation")
        dataset = OUTPUT / "question-snapshot"
        dataset.mkdir(exist_ok=False)
        atomic_json(dataset / "questions.json", snapshot["questions"])
        atomic_json(dataset / "manifest.json", dataset_manifest(snapshot))
        plan = {"spec": SPEC, "source_file_sha256": pins,
                "environment": original.stable_environment(),
                "validation_ordering_file_sha256": ordering_pins,
                "diagnosis_plan_sha256": digest(old_plan), "diagnosis_rows_sha256": digest(rows),
                "parent_protocol_sha256": digest(protocol), "cells": cells, "arms": arms,
                "question_snapshot_sha256": digest(snapshot), "prepared_at": time.time(),
                "dataset_file_sha256": {name: file_hash(dataset / name) for name in
                                        ("questions.json", "manifest.json")},
                "reference_boundary": "new outputs only: exactly 11 selected training references after all 36 responses, collector exit and global accounting",
                "no_model_generation_reference_or_scoring_access": True}
        original.write_once(OUTPUT / "question-snapshot.json", snapshot)
        original.write_once(OUTPUT / "plan.json", plan)
        return {"plan_sha256": digest(plan), "responses": 36, "development_groups": 11,
                "response_only_bound": SPEC["response_only_bound"], "generation": "unimplemented_locked"}


def verify():
    plan = verified(OUTPUT / "plan.json")
    snapshot = verified(OUTPUT / "question-snapshot.json")
    if (plan["spec"] != SPEC or plan["source_file_sha256"] != sources()
            or plan["environment"] != original.stable_environment()
            or plan["question_snapshot_sha256"] != digest(snapshot)
            or plan["validation_ordering_file_sha256"] != require_validation_review()):
        fail("Cap bridge frozen identity changed")
    old_plan, rows, protocol = diagnosis.checked()
    _, _, records, _, _, _ = diagnosis.inputs()
    cells = capped_cells(protocol, records[SOLVER])
    if (plan["diagnosis_plan_sha256"] != digest(old_plan) or plan["diagnosis_rows_sha256"] != digest(rows)
            or plan["parent_protocol_sha256"] != digest(protocol) or plan["cells"] != cells
            or plan["arms"] != matched_jobs(protocol, cells)
            or snapshot != question_snapshot(protocol, cells)):
        fail("Cap bridge original cells/configurations changed")
    dataset = OUTPUT / "question-snapshot"
    for name, sha in plan["dataset_file_sha256"].items():
        if file_hash(dataset / name) != sha:
            fail("Cap bridge question-only dataset changed")
    if (read_json(dataset / "questions.json") != snapshot["questions"]
            or read_json(dataset / "manifest.json") != dataset_manifest(snapshot)):
        fail("Cap bridge question manifest changed")
    if (OUTPUT / "question-snapshot" / "gold.json").exists():
        fail("Question snapshot must not materialize gold")
    return {"plan_sha256": digest(plan), "responses": 36, "generation": "unimplemented_locked"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    command = parser.parse_args().command
    print(prepare() if command == "prepare" else verify())


if __name__ == "__main__":
    main()
