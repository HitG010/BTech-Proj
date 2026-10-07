"""Bounded matched local 1.7B thinking-cap bridge runtime.

Only runtime-v1 receives writes. Operator commands are prepare, launch, resume,
and status; collector, supervisor, and finalizer are private authenticated modes.
"""

import argparse
import os
import random
import signal
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reasoning_budget import scoring_v7
from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob, GenerationResult, Question
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import opportunity_panel_collect as orig
from scripts import opportunity_panel_recovery as recovery
from scripts import qwen17_cap_bridge_plan as cap

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = cap.OUTPUT / "runtime-v1"
SOURCE_FILES = ("scripts/qwen17_cap_bridge_collect.py", "tests/test_qwen17_cap_bridge_collect.py",
                "docs/qwen17-cap-bridge-runtime-protocol.md")
DEPENDENCY_FILES = ("scripts/qwen17_cap_bridge_plan.py", "scripts/opportunity_panel_collect.py",
                    "scripts/opportunity_panel_recovery.py", "scripts/macos_runtime_guard.py",
                    "scripts/qwen17_solver_diagnosis.py", "scripts/opportunity_panel_plan.py",
                    "scripts/verify_phase2_repeat.py",
                    "src/reasoning_budget/backend.py", "src/reasoning_budget/config.py",
                    "src/reasoning_budget/records.py", "src/reasoning_budget/runner.py",
                    "src/reasoning_budget/scoring_v7.py", "src/reasoning_budget/storage.py",
                    "src/reasoning_budget/confirmation.py")
VERSION = "qwen17-cap-bridge-runtime-v1"
SPEC = {"version": VERSION, "cells": 18, "question_groups": 11, "responses": 36,
        "global_tokens": 160000, "global_seconds": 14400,
        "setup_seconds": 900, "job_seconds": 600,
        "maximum_setups": 2, "maximum_invocations": 2, "maximum_launches": 2,
        "maximum_polled_rss_bytes": 9 * 1024**3, "poll_seconds": 2,
        "watchdog_grace_seconds": 5, "automatic_resume": False,
        "cloud_spend_usd": 0, "first_failure_stop": True}


def fail(message):
    raise orig.IntegrityError(message)


def source_hashes():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES + DEPENDENCY_FILES}


def prepared_paths():
    paths = [cap.OUTPUT / name for name in ("plan.json", "prepare-started.json",
            "preparation-verification.json", "question-snapshot.json",
            "question-snapshot/questions.json", "question-snapshot/manifest.json")]
    paths.extend(cap.VALIDATION / name for name in
                 ("status.json", "report.json", "completion-review-verification.json"))
    return paths


def safe_path():
    if (RUNTIME.is_symlink() or cap.OUTPUT.is_symlink()
            or RUNTIME.resolve() != cap.OUTPUT.resolve() / "runtime-v1"
            or RUNTIME.exists() and any(p.is_symlink() for p in RUNTIME.rglob("*"))):
        fail("Cap bridge runtime path contains symlink or escaped output")


def _write(path, value):
    orig.write_once(path, value)


def _current_inputs():
    cap.verify()
    cap_plan = verified(cap.OUTPUT / "plan.json")
    review = verified(cap.OUTPUT / "preparation-verification.json")
    snapshot = verified(cap.OUTPUT / "question-snapshot.json")
    if (not review.get("checks_passed") or review.get("plan_sha256") != digest(cap_plan)
            or review.get("development_cells") != 18
            or review.get("development_question_groups") != 11
            or review.get("potential_response_jobs") != 36
            or digest(snapshot) != cap_plan["question_snapshot_sha256"]):
        fail("Prepared cap bridge or independent review changed")
    ordered_jobs(cap_plan)
    if (orig.read_protocol()["generation_implementation_sha256"] != orig.implementation_digest()
            or cap_plan["parent_protocol_sha256"] != digest(orig.read_protocol())):
        fail("Frozen original generator/protocol changed")
    return cap_plan, snapshot


def ordered_jobs(cap_plan):
    """Manual, balanced pair sequence; IDs/seeds/configs come only from the prepared plan."""
    if len(cap_plan["cells"]) != 18 or set(cap_plan["arms"]) != {"control_2k", "extended_4k"}:
        fail("Cap cells or arms changed")
    result = []
    for i, cell in enumerate(cap_plan["cells"]):
        arms = ("control_2k", "extended_4k") if i % 2 == 0 else ("extended_4k", "control_2k")
        for arm in arms:
            jobs = cap_plan["arms"][arm]["jobs"]
            if len(jobs) != 18:
                fail("Cap arm job count changed")
            job = jobs[i]
            if (job["id"] != digest(job["identity"])
                    or job["mode"] != "thinking" or job["question_id"] != cell["question_id"]
                    or job["sample"] != cell["draw"] or job["seed"] != cell["generation_seed"]
                    or job["identity"]["bridge_arm"] != arm
                    or job["identity"]["original_job_id"] != cell["original_job"]["id"]
                    or job["max_tokens"] != (2562 if arm == "control_2k" else 4610)):
                fail("Cap job/cell/seed identity changed")
            result.append({"arm": arm, "cell_index": i, "job": job})
    if len({r["job"]["id"] for r in result}) != 36 or sum(r["job"]["max_tokens"] for r in result) != 129096:
        fail("Cap job IDs or response bound changed")
    return result


def prepare():
    """One-time runtime snapshot; never constructs the model or opens references."""
    safe_path()
    if RUNTIME.exists():
        fail("Cap runtime already prepared or attempted")
    with run_lock(RUNTIME):
        if any(p.name != ".lock" for p in RUNTIME.iterdir()):
            fail("Cap runtime already prepared")
        cap_plan, snapshot = _current_inputs()
        pins = {str(p): file_hash(p) for p in prepared_paths()}
        jobs = ordered_jobs(cap_plan)
        for path, sha in cap_plan["arms"]["control_2k"]["asset_file_sha256"].items():
            if file_hash(path) != sha:
                fail("Pinned local 1.7B asset changed")
        plan = {"version": VERSION, "spec": SPEC, "source_file_sha256": source_hashes(),
            "environment": orig.stable_environment(), "prepared_file_sha256": pins,
            "cap_plan_sha256": digest(cap_plan), "snapshot_sha256": digest(snapshot),
            "preparation_review_sha256": digest(verified(cap.OUTPUT / "preparation-verification.json")),
            "scoring_implementation_sha256": scoring_v7.implementation_digest(),
            "generation_implementation_sha256": orig.implementation_digest(),
            "ordered_jobs": jobs, "question_ids": [r["id"] for r in snapshot["questions"]],
            "prepared_at": time.time(),
            "generation_started": False, "reference_access": False,
            "purpose": "matched 1.7B thinking-cap development bridge, not confirmation"}
        _write(RUNTIME / "prepare-started.json", {"plan_sha256": digest(plan),
            "started_at": time.time(), "one_time": True})
        _write(RUNTIME / "plan.json", plan)
        atomic_json(RUNTIME / "status.json", envelope({"state": "prepared",
            "plan_sha256": digest(plan), "updated_at": time.time(),
            "completed": 0, "expected": 36,
            "generation_started": False, "references_opened": False}))
        return {"plan_sha256": digest(plan), "jobs": 36,
                "collection": "locked_until_independent_prelaunch_audit"}


def read_plan(*, check_assets=False, verify_inputs=True):
    safe_path()
    plan = verified(RUNTIME / "plan.json")
    marker = verified(RUNTIME / "prepare-started.json")
    if (plan["version"] != VERSION or plan["spec"] != SPEC
            or marker["plan_sha256"] != digest(plan) or marker["one_time"] is not True
            or plan["source_file_sha256"] != source_hashes()
            or plan["environment"] != orig.stable_environment()
            or plan["generation_implementation_sha256"] != orig.implementation_digest()
            or plan["scoring_implementation_sha256"] != scoring_v7.implementation_digest()):
        fail("Cap runtime source, scorer, or environment changed")
    for path, sha in plan["prepared_file_sha256"].items():
        if file_hash(path) != sha:
            fail("Frozen prepared input changed")
    if set(plan["prepared_file_sha256"]) != {str(p) for p in prepared_paths()}:
        fail("Frozen prepared input inventory changed")
    if verify_inputs:
        cap_plan, snapshot = _current_inputs()
    else:
        # Collector authentication is deliberately cheap. The setup reservation
        # precedes the full source/asset walk and model construction below.
        cap_plan = verified(cap.OUTPUT / "plan.json")
        snapshot = verified(cap.OUTPUT / "question-snapshot.json")
    if (digest(cap_plan) != plan["cap_plan_sha256"]
            or digest(snapshot) != plan["snapshot_sha256"]
            or digest(verified(cap.OUTPUT / "preparation-verification.json")) != plan["preparation_review_sha256"]
            or plan["ordered_jobs"] != ordered_jobs(cap_plan)
            or plan["question_ids"] != [r["id"] for r in snapshot["questions"]]):
        fail("Cap runtime input or job identity changed")
    if list((RUNTIME / "launches").glob("*.json")):
        review = verified(RUNTIME / "prelaunch-review.json")
        if review != {"plan_sha256": digest(plan),
                       "prepared_file_sha256": digest(plan["prepared_file_sha256"]),
                       "decision": "independently_audited_allow_launch"}:
            fail("Cap prelaunch review changed after launch")
    if check_assets:
        for path, sha in cap_plan["arms"]["control_2k"]["asset_file_sha256"].items():
            if file_hash(path) != sha:
                fail("Pinned local solver asset changed")
    return plan, cap_plan, snapshot


def _all(folder):
    return {p.stem: verified(p) for p in (RUNTIME / folder).glob("*.json")}


def _jobs(plan):
    return {r["job"]["id"]: r for r in plan["ordered_jobs"]}


def _launch_rows(plan):
    rows = _all("launches")
    plan_sha = digest(plan)
    if len(rows) > SPEC["maximum_launches"]:
        fail("Cap launch ceiling exceeded")
    for key, row in rows.items():
        if (row["launch_id"] != key or row["plan_sha256"] != plan_sha
                or type(row["explicit_resume"]) is not bool
                or not orig.finite_number(row["reserved_at"])):
            fail("Cap launch identity changed")
    ordered = sorted(rows.values(), key=lambda r: r["reserved_at"])
    if any(r["explicit_resume"] != (i == 1) for i, r in enumerate(ordered)):
        fail("Cap initial/resume launch order changed")
    return ordered


def usage(plan, *, now=None):
    """Reverse-snapshot ledger; unresolved operations retain full reservation."""
    plan_sha = digest(plan)
    receipts = _all("ledger/settlements")
    attempts = _all("attempt-records")
    reservations = _all("ledger/reservations")
    if not set(receipts) <= set(reservations) or not set(attempts) <= set(reservations):
        fail("Orphan cap ledger entry")
    jobs = _jobs(plan)
    invocations = _all("invocations")
    if len(invocations) > SPEC["maximum_invocations"]:
        fail("Cap invocation ceiling exceeded")
    for invocation_id, invocation in invocations.items():
        launch = verified(RUNTIME / "launches" / f"{invocation['launch_id']}.json")
        supervisor = verified(RUNTIME / "supervisor-starts" / f"{invocation['launch_id']}.json")
        if (invocation["invocation_id"] != invocation_id
                or invocation["plan_sha256"] != plan_sha
                or launch["plan_sha256"] != plan_sha
                or supervisor["launch_id"] != invocation["launch_id"]
                or supervisor["pid"] != invocation["supervisor_pid"]):
            fail("Cap invocation/launch/supervisor binding changed")
    tokens = 0
    seconds = 0.0
    setups = 0
    setup_by_invocation = set()
    seen_attempts = {}
    for key, row in reservations.items():
        invocation = invocations.get(row["invocation_id"])
        invocation_start_path = (RUNTIME / "invocation-starts" /
                                 f"{row['invocation_id']}.json")
        invocation_start = verified(invocation_start_path) if invocation_start_path.exists() else None
        if (row["id"] != key or invocation is None
                or invocation_start is None
                or invocation_start["invocation_id"] != row["invocation_id"]
                or not orig.finite_number(invocation_start["started_at"])
                or row["started_at"] < invocation_start["started_at"]
                or row["plan_sha256"] != plan_sha
                or invocation["plan_sha256"] != plan_sha
                or row["kind"] not in ("setup", "job")
                or not orig.finite_number(row["started_at"])
                or row["started_at"] < plan["prepared_at"]
                or type(row["reserved_tokens"]) is not int or row["reserved_tokens"] < 0
                or not orig.finite_number(row["reserved_seconds"]) or row["reserved_seconds"] <= 0):
            fail("Cap reservation identity changed")
        if row["kind"] == "setup":
            setups += 1
            if (row["invocation_id"] in setup_by_invocation
                    or row["reserved_tokens"] != 0
                    or row["reserved_seconds"] > SPEC["setup_seconds"]):
                fail("Cap setup reservation invalid")
            setup_by_invocation.add(row["invocation_id"])
        else:
            job = jobs.get(row["job_id"])
            setup = reservations.get(row["session_id"])
            setup_path = RUNTIME / "ledger/settlements" / f"{row['session_id']}.json"
            setup_receipt = verified(setup_path) if setup_path.exists() else None
            if (job is None or row["reserved_tokens"] != job["job"]["max_tokens"]
                    or row.get("arm") != job["arm"] or row.get("cell_index") != job["cell_index"]
                    or row["reserved_seconds"] > SPEC["job_seconds"]
                    or setup is None or setup["kind"] != "setup"
                    or setup["invocation_id"] != row["invocation_id"]
                    or setup_receipt is None or setup_receipt["status"] != "loaded"
                    or setup_receipt["id"] != row["session_id"]
                    or setup_receipt["reservation_sha256"] != digest(setup)
                    or row["started_at"] < setup_receipt["finished_at"]):
                fail("Cap job reservation or loaded setup changed")
            seen_attempts.setdefault(job["job"]["id"], []).append(row)
        receipt = receipts.get(key)
        spent, duration = row["reserved_tokens"], row["reserved_seconds"]
        if receipt is not None:
            anchor = verified(RUNTIME / "anchors" / f"{key}.json")
            if (anchor["id"] != key or anchor["reservation_sha256"] != digest(row)
                    or anchor["invocation_id"] != row["invocation_id"]
                    or anchor["pid"] != invocation_start["pid"]
                    or not orig.finite_number(anchor["monotonic_before_reserve"])):
                fail("Settled cap operation lost its monotonic anchor")
            if (receipt["id"] != key or receipt["reservation_sha256"] != digest(row)
                    or receipt["status"] not in (("loaded", "failed") if row["kind"] == "setup" else ("completed", "failed"))
                    or type(receipt["charged_tokens"]) is not int
                    or not 0 <= receipt["charged_tokens"] <= row["reserved_tokens"]
                    or not orig.finite_number(receipt["elapsed_seconds"])
                    or receipt["elapsed_seconds"] < 0
                    or not orig.finite_number(receipt["finished_at"])
                    or receipt["finished_at"] < row["started_at"]):
                fail("Cap settlement identity or cost changed")
            spent, duration = receipt["charged_tokens"], receipt["elapsed_seconds"]
            if receipt["status"] in ("loaded", "completed") and duration > row["reserved_seconds"]:
                fail("Successful cap operation exceeded reservation")
            if row["kind"] == "job":
                record = attempts.get(key)
                if record is None or receipt["record_sha256"] != digest(record):
                    fail("Cap attempt/receipt link changed")
                if (record["job"] != jobs[row["job_id"]]["job"]
                        or record.get("arm") != job["arm"]
                        or record.get("cell_index") != job["cell_index"]
                        or record["attempt_id"] != key
                        or record["session_id"] != row["session_id"]
                        or record["status"] != receipt["status"]
                        or record["plan_sha256"] != plan_sha
                        or record["implementation_sha256"] != plan["generation_implementation_sha256"]):
                    fail("Cap attempt identity changed")
                actual = row["reserved_tokens"]
                if record["result"] is not None:
                    try:
                        actual = orig.validate_result(GenerationResult(**record["result"]),
                                                      GenerationJob(**record["job"]))
                    except (ValueError, TypeError, KeyError):
                        if receipt["status"] == "completed":
                            fail("Completed cap result invalid")
                if receipt["charged_tokens"] != actual:
                    fail("Cap token charge differs from result")
                if receipt["status"] == "completed":
                    if (record["result"] is None or record["result"]["termination"] == "timeout"
                            or verified(RUNTIME / "results" / f"{row['job_id']}.json") != record):
                        fail("Cap completed result differs from settled attempt")
        tokens += spent
        seconds += duration
    if (setups > SPEC["maximum_setups"]
            or any(len(v) > 2 or len({r["invocation_id"] for r in v}) != len(v)
                   for v in seen_attempts.values())):
        fail("Cap setup or attempt ceiling exceeded")
    start_path, end_path = RUNTIME / "collection-start.json", RUNTIME / "collection-end.json"
    opening = verified(start_path) if start_path.exists() else None
    ending = verified(end_path) if end_path.exists() else None
    launches = _launch_rows(plan)
    if opening is not None and (opening["plan_sha256"] != plan_sha
            or not orig.finite_number(opening["started_at"])
            or opening["started_at"] < plan["prepared_at"]
            or not launches or opening["launch_id"] != launches[0]["launch_id"]
            or opening["started_at"] < launches[0]["reserved_at"]):
        fail("Cap collection start changed")
    if launches and opening is None:
        fail("Cap launch lacks global wall-clock origin")
    if reservations and opening is None:
        fail("Cap operation preceded collection start")
    if opening and any(r["started_at"] < opening["started_at"] for r in reservations.values()):
        fail("Cap reservation preceded collection start timestamp")
    if ending is not None and (opening is None or ending["plan_sha256"] != plan_sha
            or not orig.finite_number(ending["finished_at"])
            or ending["finished_at"] < opening["started_at"]
            or any(r["started_at"] > ending["finished_at"] for r in reservations.values())
            or any(r["finished_at"] > ending["finished_at"] for r in receipts.values())):
        fail("Cap collection end changed")
    wall = max(0.0, (ending["finished_at"] if ending is not None
                     else time.time() if now is None else now) - opening["started_at"]) if opening else 0.0
    return {"charged_tokens": tokens, "charged_seconds": seconds, "wall_seconds": wall,
            "budget_seconds": max(wall, seconds), "setup_reservations": setups,
            "attempts": sum(r["kind"] == "job" for r in reservations.values()),
            "unresolved": len(set(reservations) - set(receipts))}


def completed_rows(plan, arm=None):
    jobs = {r["job"]["id"]: r for r in plan["ordered_jobs"]}
    plan_sha = digest(plan)
    paths = list((RUNTIME / "results").glob("*.json"))
    if len(paths) > 36 or any(p.stem not in jobs for p in paths):
        fail("Unknown cap result")
    result = []
    for entry in plan["ordered_jobs"]:
        if arm is not None and entry["arm"] != arm:
            continue
        frozen = entry["job"]
        path = RUNTIME / "results" / f"{frozen['id']}.json"
        if not path.exists():
            continue
        row = verified(path)
        if (row["job"] != frozen or row["status"] != "completed"
                or row.get("arm") != entry["arm"]
                or row.get("cell_index") != entry["cell_index"]
                or row["plan_sha256"] != plan_sha
                or row["cap_plan_sha256"] != plan["cap_plan_sha256"]
                or row["implementation_sha256"] != plan["generation_implementation_sha256"]):
            fail("Cap result identity changed")
        value = GenerationResult(**row["result"])
        orig.validate_result(value, GenerationJob(**frozen))
        if value.termination == "timeout":
            fail("Timeout cannot be completed")
        receipt_path = RUNTIME / "ledger/settlements" / f"{row['attempt_id']}.json"
        if not receipt_path.exists():
            # Live publication is in flight. After an observed failed process,
            # retain the valid output and charge its entire unknown reservation.
            attempt = verified(RUNTIME / "ledger/reservations" / f"{row['attempt_id']}.json")
            invocation = verified(RUNTIME / "invocations" / f"{attempt['invocation_id']}.json")
            launch_id = invocation["launch_id"]
            process_path = RUNTIME / "invocation-processes" / f"{launch_id}.json"
            finish_path = RUNTIME / "supervisor-finishes" / f"{launch_id}.json"
            if not process_path.exists() or not finish_path.exists():
                continue
            process, finish = verified(process_path), verified(finish_path)
            stored = verified(RUNTIME / "attempt-records" / f"{row['attempt_id']}.json")
            setup = verified(RUNTIME / "ledger/settlements" / f"{row['session_id']}.json")
            if (process["launch_id"] != launch_id
                    or process["invocation_id"] != attempt["invocation_id"]
                    or process["exit_code"] in (None, 0)
                    or not orig.finite_number(process["finished_at"])
                    or process["finished_at"] < attempt["started_at"]
                    or finish["state"] != "needs_attention"
                    or attempt["job_id"] != frozen["id"]
                    or attempt["session_id"] != row["session_id"]
                    or stored != row or setup["status"] != "loaded"):
                fail("Terminal unknown cap result lacks failed-process evidence")
            result.append(row)
            continue
        attempt = verified(RUNTIME / "ledger/reservations" / f"{row['attempt_id']}.json")
        receipt = verified(receipt_path)
        setup = verified(RUNTIME / "ledger/settlements" / f"{row['session_id']}.json")
        if (attempt["job_id"] != frozen["id"] or attempt["session_id"] != row["session_id"]
                or receipt["status"] != "completed" or receipt["record_sha256"] != digest(row)
                or setup["status"] != "loaded"):
            fail("Cap result/ledger link changed")
        result.append(row)
    return result


def progress(plan):
    tally = usage(plan)
    rows = completed_rows(plan)
    return tally | {"completed": len(rows), "expected": 36,
                    "control_completed": sum(r["arm"] == "control_2k" for r in rows),
                    "extended_completed": sum(r["arm"] == "extended_4k" for r in rows)}


def status(state, plan, **extra):
    try:
        counts = progress(plan)
    except BaseException as error:
        if state != "needs_attention":
            raise
        counts = {"integrity_error": f"{type(error).__name__}: {error}"}
    atomic_json(RUNTIME / "status.json", envelope({"state": state,
        "plan_sha256": digest(plan), "progress": counts, "updated_at": time.time(),
        "automatic_resume": False, "cloud_spend_usd": 0, **extra}))


def reserve(plan, kind, invocation_id, *, job=None, session_id=None, before_active=None):
    if (RUNTIME / "collection-end.json").exists():
        fail("Cap collection already closed")
    tally = usage(plan)
    remaining = SPEC["global_seconds"] - tally["budget_seconds"]
    amount = 0 if job is None else job.max_tokens
    if (remaining <= 0 or tally["charged_tokens"] + amount > SPEC["global_tokens"]
            or kind == "setup" and tally["setup_reservations"] >= SPEC["maximum_setups"]):
        raise orig.BudgetExhausted("Cap global budget cannot admit operation")
    if job is not None:
        frozen = _jobs(plan).get(job.id)
        if frozen is None or frozen["job"] != job.to_dict() or (RUNTIME / "results" / f"{job.id}.json").exists():
            fail("Cap job unknown or already complete")
        attempts = [r for r in _all("ledger/reservations").values()
                    if r["kind"] == "job" and r["job_id"] == job.id]
        if len(attempts) >= 2 or any(r["invocation_id"] == invocation_id for r in attempts):
            fail("Cap job cannot retry within invocation or beyond explicit resume")
        done = {r["job"]["id"] for r in completed_rows(plan)}
        first_pending = next((e["job"]["id"] for e in plan["ordered_jobs"]
                              if e["job"]["id"] not in done), None)
        if job.id != first_pending:
            fail("Cap job reservation violates frozen alternating pair order")
    row = {"id": uuid.uuid4().hex, "plan_sha256": digest(plan),
        "invocation_id": invocation_id, "kind": kind, "started_at": time.time(),
        "reserved_tokens": amount, "reserved_seconds": min(remaining,
            SPEC["setup_seconds"] if kind == "setup" else SPEC["job_seconds"])}
    if job is not None:
        row.update(job_id=job.id, session_id=session_id,
                   arm=frozen["arm"], cell_index=frozen["cell_index"])
    _write(RUNTIME / "ledger/reservations" / f"{row['id']}.json", row)
    if before_active is not None:
        before_active(row)
    atomic_json(RUNTIME / "active.json", envelope(row))
    return row


def anchored_reserve(plan, kind, invocation_id, *, job=None, session_id=None):
    before = time.monotonic()
    def anchor(row):
        _write(RUNTIME / "anchors" / f"{row['id']}.json", {"id": row["id"],
            "reservation_sha256": digest(row), "monotonic_before_reserve": before,
            "pid": os.getpid(), "invocation_id": invocation_id})
    return reserve(plan, kind, invocation_id, job=job, session_id=session_id,
                   before_active=anchor)


def settle(reservation, state, began, *, tokens=None, record=None):
    charged = reservation["reserved_tokens"] if tokens is None else tokens
    receipt = {"id": reservation["id"], "reservation_sha256": digest(reservation),
        "status": state, "charged_tokens": charged,
        "elapsed_seconds": time.monotonic() - began, "finished_at": time.time()}
    if record is not None:
        receipt["record_sha256"] = digest(record)
    _write(RUNTIME / "ledger/settlements" / f"{reservation['id']}.json", receipt)
    atomic_json(RUNTIME / "active.json", envelope({"kind": "idle"}))
    return receipt


def authenticate_collector(invocation_id):
    plan, cap_plan, snapshot = read_plan(verify_inputs=False)
    binding = verified(RUNTIME / "invocations" / f"{invocation_id}.json")
    launch = verified(RUNTIME / "launches" / f"{binding['launch_id']}.json")
    parent = verified(RUNTIME / "supervisor-starts" / f"{binding['launch_id']}.json")
    if (binding != {"invocation_id": invocation_id, "launch_id": launch["launch_id"],
            "plan_sha256": digest(plan), "supervisor_pid": os.getppid()}
            or parent["pid"] != os.getppid() or parent["launch_id"] != launch["launch_id"]
            or launch["plan_sha256"] != digest(plan)
            or (RUNTIME / "supervisor-finishes" / f"{launch['launch_id']}.json").exists()):
        fail("Private cap collector is not bound to live supervisor")
    return plan, cap_plan, snapshot, launch


def load_backends(cap_plan, backend_factory=orig.TransformersBackend):
    """Construct both frozen decoders, loading weights once and sharing them."""
    arms = cap_plan["arms"]
    if arms["control_2k"]["asset_file_sha256"] != arms["extended_4k"]["asset_file_sha256"]:
        fail("Cap arms do not pin the same local weights")
    engines = {}
    for arm in ("control_2k", "extended_4k"):
        engine = backend_factory(orig.from_dict(arms[arm]["config"]))
        if engine.metadata != arms[arm]["backend_metadata"]:
            fail("Cap backend metadata changed")
        engines[arm] = engine
    control, extended = engines["control_2k"], engines["extended_4k"]
    control.load()
    extended.model = control.model
    extended.tokenizer = control.tokenizer
    if hasattr(control, "_sync"):
        control._sync()
    if extended.model is not control.model or extended.tokenizer is not control.tokenizer:
        fail("Cap arms did not share one loaded model/tokenizer")
    return engines


def collect(invocation_id):
    plan, cap_plan, snapshot, _ = authenticate_collector(invocation_id)
    with run_lock(RUNTIME / "collection"):
        _write(RUNTIME / "invocation-starts" / f"{invocation_id}.json", {
            "invocation_id": invocation_id, "pid": os.getpid(), "started_at": time.time()})
        setup_began = time.monotonic()
        session = anchored_reserve(plan, "setup", invocation_id)
        _write(RUNTIME / "invocation-ready" / f"{invocation_id}.json", {
            "invocation_id": invocation_id, "session_id": session["id"], "ready_at": time.time()})
        try:
            checked_plan, cap_plan, snapshot = read_plan()
            if digest(checked_plan) != digest(plan):
                fail("Cap plan changed after setup reservation")
            for path, sha in cap_plan["arms"]["control_2k"]["asset_file_sha256"].items():
                if file_hash(path) != sha:
                    fail("Pinned 1.7B model asset changed")
            engines = load_backends(cap_plan)
            if time.monotonic() - setup_began > session["reserved_seconds"]:
                raise orig.BudgetExhausted("Cap model setup exceeded reservation")
        except BaseException:
            settle(session, "failed", setup_began, tokens=0)
            raise
        receipt = settle(session, "loaded", setup_began, tokens=0)
        if receipt["elapsed_seconds"] > session["reserved_seconds"]:
            raise orig.BudgetExhausted("Cap model setup exceeded reservation")
        questions = {r["id"]: Question(**r) for r in snapshot["questions"]}
        def run_job(entry):
            frozen = entry["job"]
            job = GenerationJob(**frozen)
            began = time.monotonic()
            attempt = anchored_reserve(plan, "job", invocation_id, job=job, session_id=session["id"])
            row = {"plan_sha256": digest(plan),
                "cap_plan_sha256": plan["cap_plan_sha256"],
                "implementation_sha256": plan["generation_implementation_sha256"],
                "arm": entry["arm"], "cell_index": entry["cell_index"],
                "job": frozen, "status": "failed", "result": None,
                "attempt_id": attempt["id"], "session_id": session["id"]}
            tokens, error = None, None
            try:
                engine = engines[entry["arm"]]
                if (engine.config.to_dict() != frozen["identity"]["config"]
                        or engine.metadata != frozen["identity"]["backend"]):
                    fail("Cap engine decoder/config identity changed before generation")
                result = engine.generate(questions[job.question_id], job,
                                         began + attempt["reserved_seconds"])
                row["result"] = result.to_dict()
                tokens = orig.validate_result(result, job)
                if result.termination == "timeout":
                    raise RuntimeError("Cap generation deadline reached")
                if time.monotonic() - began > attempt["reserved_seconds"]:
                    raise orig.BudgetExhausted("Cap generation exceeded reservation")
                row["status"] = "completed"
            except BaseException as exc:
                error = exc
                row["error"] = f"{type(exc).__name__}: {exc}"
            _write(RUNTIME / "attempt-records" / f"{attempt['id']}.json", row)
            if row["status"] == "completed":
                _write(RUNTIME / "results" / f"{job.id}.json", row)
            settle(attempt, row["status"], began, tokens=tokens, record=row)
            status("collecting", plan, invocation_id=invocation_id)
            print(f"cap {entry['arm']} {job.question_id} {row['status']}", flush=True)
            if error is not None:
                raise error
        for entry in plan["ordered_jobs"]:
            if not (RUNTIME / "results" / f"{entry['job']['id']}.json").exists():
                run_job(entry)
        return progress(plan)


def private_collector(invocation_id):
    authenticate_collector(invocation_id)  # Wrong PID cannot write a finish record.
    with run_lock(RUNTIME / "collector-entry"):
        if ((RUNTIME / "invocation-starts" / f"{invocation_id}.json").exists()
                or (RUNTIME / "invocation-finishes" / f"{invocation_id}.json").exists()):
            fail("Cap private collector invocation already used")
        try:
            from scripts.macos_runtime_guard import user_activity
            with user_activity():
                result = collect(invocation_id)
            _write(RUNTIME / "invocation-finishes" / f"{invocation_id}.json", {
                "state": "complete", "progress": result})
            return 0
        except BaseException as error:
            kind = _failure_kind(error)
            _write(RUNTIME / "invocation-finishes" / f"{invocation_id}.json", {
                "state": "stopped", "failure_kind": kind,
                "reason": f"{type(error).__name__}: {error}"})
            print(f"Cap collector stopped: {type(error).__name__}: {error}", flush=True)
            return 1


def _stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def monitor(process, plan, invocation_id, began, telemetry):
    missing_id, missing_since, last_status = None, None, began - 10
    while process.poll() is None:
        now = time.monotonic()
        ready = RUNTIME / "invocation-ready" / f"{invocation_id}.json"
        if not ready.exists() and now - began > SPEC["setup_seconds"]:
            raise RuntimeError("Cap collector startup watchdog reached")
        tally = usage(plan)
        if (tally["budget_seconds"] > SPEC["global_seconds"]
                or tally["charged_tokens"] > SPEC["global_tokens"]):
            raise orig.BudgetExhausted("Cap global wall/token budget reached")
        active_path = RUNTIME / "active.json"
        if active_path.exists():
            active = verified(active_path)
            if active.get("kind") != "idle":
                if active["invocation_id"] != invocation_id:
                    try:
                        prior = verified(RUNTIME / "invocations" / f"{active['invocation_id']}.json")
                        prior_launch = prior["launch_id"]
                        previous_process = verified(RUNTIME / "invocation-processes" / f"{prior_launch}.json")
                        previous_finish = verified(RUNTIME / "supervisor-finishes" / f"{prior_launch}.json")
                    except (FileNotFoundError, KeyError, ValueError) as error:
                        fail(f"Cap active operation has unknown prior owner: {error}")
                    if (prior["invocation_id"] != active["invocation_id"]
                            or prior["plan_sha256"] != digest(plan)
                            or previous_process["invocation_id"] != active["invocation_id"]
                            or previous_process["launch_id"] != prior_launch
                            or previous_process["exit_code"] in (None, 0)
                            or previous_finish["state"] != "needs_attention"):
                        fail("Cap active operation belongs to unknown live collector")
                    active = {"kind": "idle"}  # Prior charge remains in the ledger.
            if active.get("kind") != "idle":
                anchor_path = RUNTIME / "anchors" / f"{active['id']}.json"
                if anchor_path.exists():
                    anchor = verified(anchor_path)
                    if (anchor["reservation_sha256"] != digest(active)
                            or anchor["pid"] != process.pid or anchor["id"] != active["id"]
                            or anchor["invocation_id"] != invocation_id):
                        fail("Cap active monotonic anchor changed")
                    if now - anchor["monotonic_before_reserve"] > (
                            active["reserved_seconds"] + SPEC["watchdog_grace_seconds"]):
                        raise RuntimeError("Cap monotonic operation watchdog reached")
                    missing_id, missing_since = None, None
                elif missing_id != active["id"]:
                    missing_id, missing_since = active["id"], now
                elif now - missing_since > SPEC["watchdog_grace_seconds"]:
                    fail("Cap active reservation lacks monotonic anchor")
        reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(process.pid)],
            capture_output=True, text=True, timeout=5)
        if reading.returncode == 0 and reading.stdout.strip():
            telemetry["maximum_polled_rss_bytes"] = max(telemetry["maximum_polled_rss_bytes"],
                int(reading.stdout.strip()) * 1024)
            telemetry["rss_samples"] += 1
        elif process.poll() is None:
            raise RuntimeError("Cap child RSS telemetry unavailable")
        if telemetry["maximum_polled_rss_bytes"] > SPEC["maximum_polled_rss_bytes"]:
            raise ResourceStop("Cap sampled RSS ceiling reached")
        if now - last_status >= 10:
            status("collecting", plan, child_pid=process.pid,
                   maximum_polled_rss_bytes=telemetry["maximum_polled_rss_bytes"])
            last_status = now
        time.sleep(SPEC["poll_seconds"])


def live_wall_seconds():
    start = verified(RUNTIME / "collection-start.json")
    return time.time() - start["started_at"]


def terminal_unknowns(plan):
    """Prior killed operations keep full reservations but can close on explicit resume."""
    reservations = _all("ledger/reservations")
    settlements = _all("ledger/settlements")
    unknown = [r for key, r in reservations.items() if key not in settlements]
    launches = _launch_rows(plan)
    if not launches:
        return 0
    current = launches[-1]["launch_id"]
    invocations = _all("invocations")
    for row in unknown:
        invocation = invocations[row["invocation_id"]]
        launch_id = invocation["launch_id"]
        process = verified(RUNTIME / "invocation-processes" / f"{launch_id}.json")
        finish = verified(RUNTIME / "supervisor-finishes" / f"{launch_id}.json")
        if (launch_id == current or process["exit_code"] in (None, 0)
                or process["launch_id"] != launch_id
                or process["invocation_id"] != row["invocation_id"]
                or finish["state"] != "needs_attention"):
            fail("Current or unobserved unresolved operation cannot close endpoint")
    return len(unknown)


def all_collectors_exited(plan, current_launch_id):
    invocations = _all("invocations")
    reservations = _all("ledger/reservations")
    if not invocations or len(invocations) > SPEC["maximum_invocations"]:
        fail("Cap collector invocation coverage changed")
    latest = None
    for invocation_id, row in invocations.items():
        launch_id = row["launch_id"]
        process = verified(RUNTIME / "invocation-processes" / f"{launch_id}.json")
        finish_path = RUNTIME / "invocation-finishes" / f"{invocation_id}.json"
        finished = verified(finish_path) if finish_path.exists() else None
        no_child_launched = process["pid"] is None and process["exit_code"] is None
        if (row["plan_sha256"] != digest(plan)
                or process["launch_id"] != launch_id
                or process["invocation_id"] != invocation_id):
            fail("Cap collector exit observation changed")
        if launch_id == current_launch_id:
            latest = process
            if process["exit_code"] != 0 or finished is None or finished["state"] != "complete":
                fail("Latest cap collector did not exit successfully")
        else:
            supervisor_finish = verified(RUNTIME / "supervisor-finishes" / f"{launch_id}.json")
            if (not no_child_launched and process["exit_code"] in (None, 0)
                    or no_child_launched and any(r["invocation_id"] == invocation_id
                                                 for r in reservations.values())
                    or supervisor_finish["state"] != "needs_attention"
                    or finished is not None and finished["state"] != "stopped"):
                fail("Prior cap collector terminal state changed")
    if latest is None:
        fail("Cap finalizer lacks latest collector")
    return len(invocations)


def prefix_gate(plan, rows):
    """Strict new-pair token-prefix gate, independent of answers and scoring."""
    if len(rows) != 36:
        fail("All 36 cap results required before pair gate")
    indexed = {(r["cell_index"], r["arm"]): r for r in rows}
    if len(indexed) != 36:
        fail("Cap pair coverage or cell identity changed")
    pairs = []
    for i in range(18):
        control, extended = indexed[(i, "control_2k")], indexed[(i, "extended_4k")]
        compared = cap.shared_reasoning_prefix(control, extended)
        if not compared["matches"]:
            fail(f"New cap pair {i} reasoning prefix diverged; engineering gate failed")
        pairs.append({"cell_index": i, "question_id": control["job"]["question_id"],
                      "draw": control["job"]["sample"], **compared})
    return pairs


def endpoint(plan, *, require_live=True):
    rows = completed_rows(plan)
    if len(rows) != 36:
        fail("Cap endpoint incomplete")
    tally = usage(plan)
    if (tally["unresolved"] != terminal_unknowns(plan)
            or tally["charged_tokens"] > SPEC["global_tokens"]
            or tally["budget_seconds"] > SPEC["global_seconds"]
            or require_live and live_wall_seconds() > SPEC["global_seconds"]):
        raise orig.BudgetExhausted("Cap endpoint budget or settlement failed")
    return rows, prefix_gate(plan, rows), tally


def _score_header(plan, rows, pairs):
    return {"plan_sha256": digest(plan), "cap_plan_sha256": plan["cap_plan_sha256"],
            "records_sha256": digest(rows), "pair_gate_sha256": digest(pairs),
            "selected_question_ids_sha256": digest(plan["question_ids"]),
            "scoring_version": "numeric-v7",
            "scoring_implementation_sha256": plan["scoring_implementation_sha256"]}


def _check_scores(scores, plan, rows, pairs):
    if any(scores.get(k) != v for k, v in _score_header(plan, rows, pairs).items()):
        fail("Cap score sidecar identity changed")
    expected = {r["job"]["id"]: r for r in rows}
    indexed = {s["job_id"]: s for s in scores["scores"]}
    if len(indexed) != 36 or len(scores["scores"]) != 36 or set(indexed) != set(expected):
        fail("Cap score coverage changed")
    if not isinstance(scores.get("gold_sha256"), str) or len(scores["gold_sha256"]) != 64:
        fail("Cap selected gold digest absent")
    for job_id, score in indexed.items():
        row = expected[job_id]
        extracted, parser_status = scoring_v7.extract_record(row)
        if (score["job_id"] != job_id or score["question_id"] != row["job"]["question_id"]
                or score["mode"] != "thinking" or score["scoring_version"] != "numeric-v7"
                or score["arm"] != row["arm"] or score["cell_index"] != row["cell_index"]
                or score["parser_status"] != parser_status
                or score["extracted_answer"] != extracted
                or type(score["correct"]) is not bool
                or parser_status != "ok" and score["correct"]):
            fail("Cap cached score semantics changed")
    return indexed


def selected_gold(plan, snapshot):
    """Live-authenticated callback opens exactly 11 upstream training answers."""
    from scripts import opportunity_panel_plan as child_plan
    from scripts.verify_phase2_repeat import verify
    live_plan, _, live_snapshot = authenticate_finalizer()
    marker = verified(RUNTIME / "score-started.json")
    if (not orig.finite_number(marker.get("started_at"))
            or marker["started_at"] < verified(RUNTIME / "collection-end.json")["finished_at"]):
        fail("Cap score marker timing changed")
    rows, pairs, _ = endpoint(live_plan)
    if (digest(live_plan) != digest(plan) or live_snapshot != snapshot
            or marker != {"plan_sha256": digest(plan),
                          "records_sha256": digest(rows), "pair_gate_sha256": digest(pairs),
                          "selected_question_ids_sha256": digest(plan["question_ids"]),
                          "started_at": marker["started_at"]}):
        fail("Cap selected-reference callback lacks full endpoint authorization")
    verify(orig.BASE / "repeat-panel-v1")
    endpoint(live_plan)
    read_plan()
    from datasets import Dataset
    child = child_plan.verify(orig.BASE, ROOT)
    source = child["source"]
    if source["split"] != "train":
        fail("Cap references must be selected upstream training rows")
    selected = snapshot["selected_training_source_rows"]
    if (len(selected) != 11 or {r["child_question"]["id"] for r in selected}
            != set(plan["question_ids"])):
        fail("Cap selected training-row coverage changed")
    # Deep source checks are above; enforce the live wall deadline at the read.
    rebound, _, _ = authenticate_finalizer()
    if digest(rebound) != digest(plan):
        fail("Cap finalizer binding changed before selected reference access")
    endpoint(live_plan)
    answers = Dataset.from_file(source["arrow_path"]).select_columns(["answer"]).select(
        [r["upstream_index"] for r in selected])["answer"]
    gold = {}
    for row, answer in zip(selected, answers):
        if "####" not in answer:
            fail("Selected training reference lacks delimiter")
        value = answer.rsplit("####", 1)[1].strip()
        scoring_v7.v5.numeric(value)
        gold[row["child_question"]["id"]] = value
    if set(gold) != set(plan["question_ids"]):
        fail("Cap selected-only reference coverage changed")
    return gold


def score_endpoint(plan, snapshot, rows, pairs):
    path, marker_path = RUNTIME / "scores.numeric-v7.json", RUNTIME / "score-started.json"
    if path.exists():
        cached = verified(path)
        _check_scores(cached, plan, rows, pairs)
        marker = verified(marker_path)
        if (marker["plan_sha256"] != digest(plan)
                or marker["records_sha256"] != digest(rows)
                or marker["pair_gate_sha256"] != digest(pairs)
                or marker["selected_question_ids_sha256"] != digest(plan["question_ids"])
                or not orig.finite_number(marker.get("started_at"))
                or marker["started_at"] < verified(RUNTIME / "collection-end.json")["finished_at"]):
            fail("Cap score marker changed")
        return cached
    if marker_path.exists():
        fail("Cap score marker exists without valid cache; references may not reopen")
    read_plan()
    request = verified(RUNTIME / "finalize-request.json")
    all_collectors_exited(plan, request["launch_id"])
    rebound, _, _ = authenticate_finalizer()
    if digest(rebound) != digest(plan):
        fail("Cap score start lacks private finalizer binding")
    endpoint(plan)
    _write(marker_path, {"plan_sha256": digest(plan), "records_sha256": digest(rows),
        "pair_gate_sha256": digest(pairs),
        "selected_question_ids_sha256": digest(plan["question_ids"]), "started_at": time.time()})
    gold = selected_gold(plan, snapshot)
    scores = [{"arm": r["arm"], "cell_index": r["cell_index"]} |
              scoring_v7.score_record(r, gold[r["job"]["question_id"]]) for r in rows]
    artifact = _score_header(plan, rows, pairs) | {"gold_sha256": digest(gold), "scores": scores}
    _check_scores(artifact, plan, rows, pairs)
    _write(path, artifact)
    return artifact


def _interval(values):
    ordered = sorted(values)
    def percentile(p):
        k = (len(ordered) - 1) * p
        lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
        return ordered[lo] * (hi - k) + ordered[hi] * (k - lo) if hi != lo else ordered[lo]
    return [percentile(.025), percentile(.975)]


def analyze_pairs(plan, rows, scores):
    indexed = _check_scores(scores, plan, rows, prefix_gate(plan, rows))
    cells = {}
    for r in rows:
        score = indexed[r["job"]["id"]]
        tokens = sum(r["result"][k] for k in ("reasoning_tokens", "answer_tokens", "inserted_tokens"))
        cells.setdefault(r["cell_index"], {})[r["arm"]] = {
            "correct": int(score["correct"]), "tokens": tokens,
            "utility": int(score["correct"]) - .05 * tokens / 1000}
    by_question = {qid: [] for qid in plan["question_ids"]}
    arm_by_question = {arm: {qid: [] for qid in plan["question_ids"]}
                       for arm in ("control_2k", "extended_4k")}
    deltas = []
    for i in range(18):
        c, e = cells[i]["control_2k"], cells[i]["extended_4k"]
        delta = {k: e[k] - c[k] for k in ("correct", "tokens", "utility")}
        by_question[plan["ordered_jobs"][2*i]["job"]["question_id"]].append(delta)
        qid = plan["ordered_jobs"][2*i]["job"]["question_id"]
        arm_by_question["control_2k"][qid].append(c)
        arm_by_question["extended_4k"][qid].append(e)
        deltas.append(delta)
    if len(by_question) != 11 or sorted(map(len, by_question.values())) != [1]*4 + [2]*7:
        fail("Cap question-group multiplicities changed")
    group = [{k: statistics.mean(cell[k] for cell in values)
              for k in ("correct", "tokens", "utility")} for values in by_question.values()]
    rng = random.Random(20261020)
    bootstrap = {k: [] for k in ("correct", "tokens", "utility")}
    for _ in range(2000):
        draw = rng.choices(group, k=11)
        for k in bootstrap:
            bootstrap[k].append(statistics.mean(item[k] for item in draw))
    arm_means = {arm: {
        "primary_equal_11_questions": {k: statistics.mean(
            statistics.mean(r[k] for r in values) for values in groups.values())
            for k in ("correct", "tokens", "utility")},
        "secondary_equal_18_cells": {k: statistics.mean(cells[i][arm][k] for i in range(18))
                                     for k in ("correct", "tokens", "utility")}}
        for arm, groups in arm_by_question.items()}
    return {"lambda": .05, "arm_means": arm_means,
            "primary_equal_11_questions": {
                k: {"delta": statistics.mean(item[k] for item in group),
                    "bootstrap_95_ci": _interval(bootstrap[k])} for k in bootstrap},
            "secondary_equal_18_cells": {k: statistics.mean(item[k] for item in deltas)
                                          for k in bootstrap},
            "bootstrap_seed": 20261020, "bootstrap_draws": 2000,
            "fixed_actions_no_refit": True, "development_only": True}


def old_replay_diagnostic(cap_plan, rows):
    """Descriptive comparison to cached old 2k traces; never a reference gate."""
    from scripts import qwen17_solver_diagnosis as diagnosis
    _, _, records, _, _, _ = diagnosis.inputs()
    original = {r["job"]["id"]: r for r in records["qwen3-1.7b"]}
    controls = {r["cell_index"]: r for r in rows if r["arm"] == "control_2k"}
    compared = []
    for i, cell in enumerate(cap_plan["cells"]):
        old = original[cell["original_job"]["id"]]
        check = cap.shared_reasoning_prefix(old, controls[i])
        old_meta, new_meta = old["result"]["metadata"], controls[i]["result"]["metadata"]
        stream_match = {name: old_meta[f"{name}_token_ids"] == new_meta[f"{name}_token_ids"]
                        for name in ("reasoning", "answer", "inserted")}
        compared.append({"cell_index": i, **check, "stream_matches": stream_match,
                         "all_token_streams_match": all(stream_match.values())})
    return {"compared_cells": 18, "matching_prefix_cells": sum(r["matches"] for r in compared),
            "matching_full_token_stream_cells": sum(r["all_token_streams_match"] for r in compared),
            "comparisons": compared, "diagnostic_only_not_reference_gate": True}


def authenticate_finalizer():
    plan, cap_plan, snapshot = read_plan()
    request = verified(RUNTIME / "finalize-request.json")
    parent = verified(RUNTIME / "supervisor-starts" / f"{request['launch_id']}.json")
    if (request["plan_sha256"] != digest(plan) or parent["pid"] != os.getppid()
            or parent["launch_id"] != request["launch_id"]
            or (RUNTIME / "supervisor-finishes" / f"{request['launch_id']}.json").exists()):
        fail("Private cap finalizer is not bound to live supervisor")
    return plan, cap_plan, snapshot


def finalize():
    with run_lock(RUNTIME / "analysis"), run_lock(RUNTIME / "collection"):
        plan, cap_plan, snapshot = authenticate_finalizer()
        rows, pairs, tally = endpoint(plan)
        request = verified(RUNTIME / "finalize-request.json")
        all_collectors_exited(plan, request["launch_id"])
        if (request["records_sha256"] != digest(rows)
                or request["pair_gate_sha256"] != digest(pairs)
                or request["charged_tokens"] != tally["charged_tokens"]
                or not (RUNTIME / "collection-end.json").exists()
                or verified(RUNTIME / "invocation-processes" / f"{request['launch_id']}.json")["exit_code"] != 0):
            fail("Cap finalizer request or exited collector changed")
        from scripts.verify_phase2_repeat import verify
        before = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        endpoint(plan)
        report_path = RUNTIME / "report.json"
        if report_path.exists():
            report = verified(report_path)
            cached = score_endpoint(plan, snapshot, rows, pairs)
            analysis = verified(RUNTIME / "analysis-started.json")
            if (report["plan_sha256"] != digest(plan) or report["scores_sha256"] != digest(cached)
                    or report["statistics"] != analyze_pairs(plan, rows, cached)
                    or report["old_replay_diagnostic"] != old_replay_diagnostic(cap_plan, rows)
                    or report["ledger"] != tally
                    or analysis["scores_sha256"] != digest(cached)):
                fail("Cap cached report binding changed")
            return report
        scores = score_endpoint(plan, snapshot, rows, pairs)
        _write(RUNTIME / "analysis-started.json", {"plan_sha256": digest(plan),
            "scores_sha256": digest(scores), "started_at": time.time()})
        statistics_result = analyze_pairs(plan, rows, scores)
        replay = old_replay_diagnostic(cap_plan, rows)
        after = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        endpoint(plan)
        report = {"version": VERSION, "plan_sha256": digest(plan),
            "cap_plan_sha256": plan["cap_plan_sha256"], "pair_gate_sha256": digest(pairs),
            "prelaunch_review_sha256": digest(verified(RUNTIME / "prelaunch-review.json")),
            "scores_sha256": digest(scores), "statistics": statistics_result,
            "old_replay_diagnostic": replay,
            "ledger": tally, "protected_originals_verified_before": before["protected_originals_verified"],
            "protected_originals_verified_after": after["protected_originals_verified"],
            "full_prepared_inputs_preserved": True, "references_opened_for": 11,
            "selected_train_only": True, "cloud_spend_usd": 0}
        _write(report_path, report)
        return report


class ResourceStop(RuntimeError):
    """A local resource ceiling failed; no runtime resume is permitted."""


def _failure_kind(error):
    if isinstance(error, orig.BudgetExhausted):
        return "budget"
    if isinstance(error, (ResourceStop, MemoryError)) or "out of memory" in str(error).lower():
        return "resource"
    if isinstance(error, (ValueError, orig.IntegrityError)):
        return "integrity"
    return "runtime"


def supervisor(launch_id):
    os.chdir(ROOT)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    ready_path = RUNTIME / "launch-ready" / f"{launch_id}.json"
    deadline = time.monotonic() + 30
    while not ready_path.exists():
        if time.monotonic() > deadline:
            reason = "Cap launch handshake expired"
            atomic_json(RUNTIME / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "runtime", "reason": reason, "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False}))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json",
                   {"launch_id": launch_id, "state": "needs_attention",
                    "failure_kind": "runtime", "reason": reason})
            return 1
        time.sleep(.1)
    with run_lock(RUNTIME / "supervisor"):
        if (RUNTIME / "supervisor-starts" / f"{launch_id}.json").exists():
            fail("Cap supervisor launch was already used")
        try:
            plan, _, _ = read_plan(verify_inputs=False)
            launch = verified(RUNTIME / "launches" / f"{launch_id}.json")
            ready = verified(ready_path)
            launches = _launch_rows(plan)
            if (launch["launch_id"] != launch_id or launches[-1] != launch
                    or launch["plan_sha256"] != digest(plan) or ready["launch_id"] != launch_id
                    or ready["plan_sha256"] != digest(plan)):
                fail("Cap supervisor launch handshake changed")
            if len(launches) == 2:
                previous = verified(RUNTIME / "supervisor-finishes" /
                                    f"{launches[0]['launch_id']}.json")
                if (previous["state"] != "needs_attention"
                        or previous["failure_kind"] != "runtime"):
                    fail("Cap resume lacks failed prior supervisor")
        except BaseException as error:
            reason = f"{type(error).__name__}: {error}"
            atomic_json(RUNTIME / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "integrity", "reason": reason, "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False}))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json",
                   {"launch_id": launch_id, "state": "needs_attention",
                    "failure_kind": "integrity", "reason": reason})
            return 1
        _write(RUNTIME / "supervisor-starts" / f"{launch_id}.json", {
            "launch_id": launch_id, "pid": os.getpid(), "started_at": time.time()})
        try:
            with run_lock(RUNTIME / "collection"):
                if (RUNTIME / "collection-end.json").exists():
                    fail("Cap collection already closed")
                opening = verified(RUNTIME / "collection-start.json")
                if (opening["plan_sha256"] != digest(plan)
                        or opening["started_at"] < plan["prepared_at"]):
                    fail("Cap global wall-clock origin changed")
                if len(_all("invocations")) >= SPEC["maximum_invocations"]:
                    fail("Cap invocation ceiling reached")
                invocation_id = uuid.uuid4().hex
                _write(RUNTIME / "invocations" / f"{invocation_id}.json", {
                    "invocation_id": invocation_id, "launch_id": launch_id,
                    "plan_sha256": digest(plan), "supervisor_pid": os.getpid()})
            status("collecting", plan, launch_id=launch_id, invocation_id=invocation_id)
            telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
            process = None
            began = time.monotonic()
            try:
                with (RUNTIME / "logs" / f"collector-{invocation_id}.log").open("x") as log:
                    process = subprocess.Popen([sys.executable, "-m", "scripts.qwen17_cap_bridge_collect",
                        "collector", "--invocation-id", invocation_id], cwd=ROOT,
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=orig.native_environment())
                    monitor(process, plan, invocation_id, began, telemetry)
            finally:
                _stop(process)
                _write(RUNTIME / "invocation-processes" / f"{launch_id}.json", {
                    "launch_id": launch_id, "invocation_id": invocation_id,
                    "pid": process.pid if process else None,
                    "exit_code": process.returncode if process else None,
                    "elapsed_monotonic_seconds": time.monotonic() - began,
                    "finished_at": time.time(), **telemetry})
            if process is None or process.returncode != 0:
                finish_path = RUNTIME / "invocation-finishes" / f"{invocation_id}.json"
                if finish_path.exists():
                    finished = verified(finish_path)
                    reason = finished.get("reason", "Cap collector stopped")
                    if finished.get("failure_kind") == "budget":
                        raise orig.BudgetExhausted(reason)
                    if finished.get("failure_kind") == "resource":
                        raise ResourceStop(reason)
                    if finished.get("failure_kind") == "integrity":
                        fail(reason)
                    raise RuntimeError(reason)
                raise RuntimeError("Cap collector exited without terminal event")
            if not telemetry["rss_samples"]:
                raise RuntimeError("No cap collector RSS observations")
            rows, pairs, tally = endpoint(plan)
            _write(RUNTIME / "collection-end.json", {
                "plan_sha256": digest(plan), "finished_at": time.time(),
                "records_sha256": digest(rows), "pair_gate_sha256": digest(pairs)})
            status("analyzing", plan, launch_id=launch_id)
            _write(RUNTIME / "finalize-request.json", {"plan_sha256": digest(plan),
                "launch_id": launch_id, "records_sha256": digest(rows),
                "pair_gate_sha256": digest(pairs),
                "charged_tokens": tally["charged_tokens"], "requested_at": time.time()})
            finalizer = None
            try:
                with (RUNTIME / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                    finalizer = subprocess.Popen([sys.executable, "-m", "scripts.qwen17_cap_bridge_collect",
                        "finalize"], cwd=ROOT, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, env=orig.native_environment())
                    while finalizer.poll() is None:
                        if live_wall_seconds() > SPEC["global_seconds"]:
                            raise orig.BudgetExhausted("Cap finalization global wall ceiling reached")
                        time.sleep(SPEC["poll_seconds"])
            finally:
                _stop(finalizer)
                _write(RUNTIME / "finalize-process.json", {"pid": finalizer.pid if finalizer else None,
                    "exit_code": finalizer.returncode if finalizer else None,
                    "finished_at": time.time()})
            if finalizer is None or finalizer.returncode != 0:
                fail("Cap finalization process failed")
            if live_wall_seconds() > SPEC["global_seconds"]:
                raise orig.BudgetExhausted("Cap global wall budget reached during finalization")
            report = verified(RUNTIME / "report.json")
            status("complete", plan, launch_id=launch_id, report_sha256=digest(report))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "complete", "report_sha256": digest(report),
                "finished_at": time.time()})
            return 0
        except BaseException as error:
            kind = _failure_kind(error)
            reason = f"{type(error).__name__}: {error}"
            status("needs_attention", plan, launch_id=launch_id,
                   failure_kind=kind, reason=reason)
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "needs_attention", "failure_kind": kind,
                "reason": reason, "finished_at": time.time()})
            print(reason, flush=True)
            return 1


def launch(*, resume=False):
    os.chdir(ROOT)
    plan, _, _ = read_plan(verify_inputs=False)
    audit = verified(RUNTIME / "prelaunch-review.json")
    if audit != {"plan_sha256": digest(plan),
                  "prepared_file_sha256": digest(plan["prepared_file_sha256"]),
                  "decision": "independently_audited_allow_launch"}:
        fail("Independent cap runtime prelaunch audit is required")
    clocks = recovery.launch_preflight()
    with run_lock(RUNTIME / "supervisor"):
        read_plan(verify_inputs=False)
        if verified(RUNTIME / "prelaunch-review.json") != audit:
            fail("Cap prelaunch audit changed")
        rows = _launch_rows(plan)
        current = verified(RUNTIME / "status.json")
        if not resume:
            if rows or current["state"] != "prepared":
                fail("Initial cap launch is one-time")
        else:
            if (len(rows) != 1 or current["state"] != "needs_attention"
                    or current.get("failure_kind") != "runtime"
                    or (RUNTIME / "collection-end.json").exists()
                    or (RUNTIME / "score-started.json").exists()):
                fail("Only one explicit runtime-failure resume is allowed")
            prior = verified(RUNTIME / "supervisor-finishes" / f"{rows[0]['launch_id']}.json")
            if prior["state"] != "needs_attention" or prior["failure_kind"] != "runtime":
                fail("Prior cap launch is not resumable")
            tally = usage(plan)
            if (tally["charged_tokens"] >= SPEC["global_tokens"]
                    or tally["budget_seconds"] >= SPEC["global_seconds"]):
                raise orig.BudgetExhausted("Cap global budget exhausted before resume")
        launch_id = uuid.uuid4().hex
        _write(RUNTIME / "launches" / f"{launch_id}.json", {
            "launch_id": launch_id, "plan_sha256": digest(plan),
            "reserved_at": time.time(), "explicit_resume": resume,
            "clock_preflight": clocks})
        if not resume:
            _write(RUNTIME / "collection-start.json", {"started_at": time.time(),
                "plan_sha256": digest(plan), "launch_id": launch_id})
        (RUNTIME / "logs").mkdir(exist_ok=True)
        try:
            with (RUNTIME / "logs" / f"supervisor-{launch_id}.log").open("x") as log:
                process = subprocess.Popen(["/usr/bin/caffeinate", "-s", "-i", sys.executable,
                    "-m", "scripts.qwen17_cap_bridge_collect", "supervisor", "--launch-id", launch_id],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, env=orig.native_environment(), start_new_session=True)
        except BaseException as error:
            reason = f"Launch failed: {type(error).__name__}: {error}"
            status("needs_attention", plan, launch_id=launch_id,
                   failure_kind="runtime", reason=reason)
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "needs_attention", "failure_kind": "runtime",
                "reason": reason, "finished_at": time.time()})
            raise
        status("launched", plan, launch_id=launch_id, pid=process.pid)
    _write(RUNTIME / "launch-ready" / f"{launch_id}.json", {
        "launch_id": launch_id, "plan_sha256": digest(plan), "ready_at": time.time()})
    return {"launch_id": launch_id, "pid": process.pid,
            "log": str(RUNTIME / "logs" / f"supervisor-{launch_id}.log")}


def verify_runtime():
    """Read-only source, prepared-input, ledger, and completed-output audit."""
    plan, cap_plan, snapshot = read_plan()
    counts = progress(plan)
    if (RUNTIME / "report.json").exists():
        rows, pairs, _ = endpoint(plan, require_live=False)
        scores = score_endpoint(plan, snapshot, rows, pairs)
        report = verified(RUNTIME / "report.json")
        if (report["plan_sha256"] != digest(plan)
                or report["scores_sha256"] != digest(scores)
                or report["statistics"] != analyze_pairs(plan, rows, scores)
                or report["old_replay_diagnostic"] != old_replay_diagnostic(cap_plan, rows)
                or verified(RUNTIME / "status.json").get("report_sha256") != digest(report)):
            fail("Cap completed report changed")
    return {"plan_sha256": digest(plan), "progress": counts,
            "reference_access": (RUNTIME / "score-started.json").exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "status", "launch", "resume",
                                            "collector", "supervisor", "finalize"))
    parser.add_argument("--invocation-id")
    parser.add_argument("--launch-id")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "verify":
        print(verify_runtime())
    elif args.command == "status":
        print(verified(RUNTIME / "status.json"))
    elif args.command == "launch":
        print(launch())
    elif args.command == "resume":
        print(launch(resume=True))
    elif args.command == "collector":
        if not args.invocation_id:
            parser.error("Private invocation required")
        sys.exit(private_collector(args.invocation_id))
    elif args.command == "supervisor":
        if not args.launch_id:
            parser.error("Private launch required")
        sys.exit(supervisor(args.launch_id))
    else:
        print(finalize())


if __name__ == "__main__":
    main()
