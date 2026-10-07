"""One separately authorized completion of 30 frozen 1.7B cap-bridge jobs.

Only completion-v1 receives writes. Operator commands are prepare, launch,
and status; collector, supervisor, and finalizer are private authenticated modes.
"""

import argparse
import fcntl
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reasoning_budget import scoring_v7
from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob, GenerationResult, Question
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import macos_runtime_guard as macos_guard
from scripts import opportunity_panel_collect as orig
from scripts import opportunity_panel_recovery as recovery
from scripts import qwen17_cap_bridge_collect as parent
from scripts import qwen17_cap_bridge_plan as cap

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = cap.OUTPUT / "completion-v1"
DECISION = orig.BASE / "qwen17-cap-completion-decision-v1/report.json"
SOURCE_FILES = ("scripts/qwen17_cap_bridge_completion.py", "tests/test_qwen17_cap_bridge_completion.py",
                "docs/qwen17-cap-bridge-completion-protocol.md")
DEPENDENCY_FILES = ("scripts/qwen17_cap_bridge_plan.py", "scripts/opportunity_panel_collect.py",
                    "scripts/opportunity_panel_recovery.py", "scripts/macos_runtime_guard.py",
                    "scripts/qwen17_cap_bridge_collect.py",
                    "scripts/qwen17_solver_diagnosis.py", "scripts/opportunity_panel_plan.py",
                    "scripts/verify_phase2_repeat.py",
                    "src/reasoning_budget/backend.py", "src/reasoning_budget/config.py",
                    "src/reasoning_budget/records.py", "src/reasoning_budget/runner.py",
                    "src/reasoning_budget/scoring_v7.py", "src/reasoning_budget/storage.py",
                    "src/reasoning_budget/confirmation.py")
VERSION = "qwen17-cap-bridge-completion-v1"
SPEC = {"version": VERSION, "cells": 18, "question_groups": 11,
        "old_responses": 6, "pending_responses": 30, "combined_responses": 36,
        "combined_token_limit": 160000, "new_wall_seconds": 28800,
        "setup_seconds": 900, "job_seconds": 1800,
        "maximum_setups": 1, "maximum_invocations": 1, "maximum_launches": 1,
        "maximum_polled_rss_bytes": 9 * 1024**3, "poll_seconds": 2,
        "watchdog_grace_seconds": 5, "automatic_resume": False,
        "cloud_spend_usd": 0, "first_failure_stop": True}


def fail(message):
    raise orig.IntegrityError(message)


def source_hashes():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES + DEPENDENCY_FILES}


def parent_snapshot():
    """Hash every old cap artifact; only the sibling completion directory is excluded."""
    if cap.OUTPUT.is_symlink() or not cap.OUTPUT.is_dir() or RUNTIME.is_symlink():
        fail("Cap output or completion path changed")
    entries = [p for p in sorted(cap.OUTPUT.rglob("*")) if not p.is_relative_to(RUNTIME)]
    if any(p.is_symlink() for p in entries):
        fail("Parent cap inventory contains a symlink")
    files = [p for p in entries if p.is_file()]
    return {str(p.relative_to(cap.OUTPUT)): file_hash(p) for p in files}


def _assert_parent_idle():
    for name in ("collection", "supervisor", "analysis"):
        lock = parent.RUNTIME / name / ".lock"
        if lock.exists():
            with lock.open("rb") as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    fail(f"Frozen parent {name} lock remains held: {error}")
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def pending_jobs(parent_plan, completed):
    """Return only the exact uncompleted suffix of the original manual catalog."""
    catalog = parent_plan["ordered_jobs"]
    if len(catalog) != 36 or len(completed) != 6:
        fail("Frozen parent is not at exactly six completed cap responses")
    for expected, row in zip(catalog[:6], completed):
        if (row.get("job") != expected["job"] or row.get("arm") != expected["arm"]
                or row.get("cell_index") != expected["cell_index"]
                or row.get("status") != "completed"):
            fail("Frozen completed cap response changed identity or order")
    pending = catalog[6:]
    if (len(pending) != 30 or len({e["job"]["id"] for e in pending}) != 30
            or sum(e["job"]["max_tokens"] for e in pending) != 107580
            or sum(e["arm"] == "control_2k" for e in pending) != 15
            or sum(e["arm"] == "extended_4k" for e in pending) != 15):
        fail("Frozen pending cap catalog or reservation bound changed")
    return pending


def parent_boundary():
    """Read-only audit of the stopped two-launch parent, without its old endpoint."""
    _assert_parent_idle()
    parent_plan, cap_plan, snapshot = parent.read_plan()
    completed = parent.completed_rows(parent_plan)
    pending = pending_jobs(parent_plan, completed)
    status = verified(parent.RUNTIME / "status.json")
    tally = parent.usage(parent_plan)
    old_reservations = parent._all("ledger/reservations")
    old_settlements = parent._all("ledger/settlements")
    unknown = [r for key, r in old_reservations.items() if key not in old_settlements]
    launches = parent._launch_rows(parent_plan)
    processes = parent._all("invocation-processes")
    finishes = parent._all("supervisor-finishes")
    invocations = parent._all("invocations")
    killed_owner = invocations.get(unknown[0]["invocation_id"]) if len(unknown) == 1 else None
    killed_launch = killed_owner["launch_id"] if killed_owner else None
    if (status.get("state") != "needs_attention" or status.get("failure_kind") != "runtime"
            or status.get("plan_sha256") != digest(parent_plan)
            or len(launches) != 2 or len(processes) != 2 or len(finishes) != 2
            or any(r.get("state") != "needs_attention" for r in finishes.values())
            or any(r.get("exit_code") in (None, 0) for r in processes.values())
            or tally["charged_tokens"] != 28035 or tally["setup_reservations"] != 2
            or tally["attempts"] != 8 or tally["unresolved"] != 1
            or len(unknown) != 1 or unknown[0]["kind"] != "job"
            or unknown[0]["reserved_tokens"] != 4610
            or unknown[0]["reserved_seconds"] != 600
            or unknown[0]["job_id"] != pending[0]["job"]["id"]
            or killed_owner is None or killed_launch not in processes
            or processes[killed_launch]["invocation_id"] != unknown[0]["invocation_id"]
            or processes[killed_launch]["exit_code"] in (None, 0)
            or finishes[killed_launch]["state"] != "needs_attention"
            or (parent.RUNTIME / "collection-end.json").exists()
            or (parent.RUNTIME / "score-started.json").exists()
            or (parent.RUNTIME / "scores.numeric-v7.json").exists()
            or (parent.RUNTIME / "report.json").exists()):
        fail("Stopped cap parent boundary changed")
    # The preserved status records the terminal charge, not a growing old wall age.
    frozen = status.get("progress", {})
    if (frozen.get("charged_tokens") != 28035 or frozen.get("completed") != 6
            or frozen.get("charged_seconds") != tally["charged_seconds"]
            or frozen.get("budget_seconds", 0) >= 14400
            or frozen.get("charged_tokens") >= 160000):
        fail("Frozen parent terminal accounting changed")
    return parent_plan, cap_plan, snapshot, completed, pending, frozen


def safe_path():
    if (RUNTIME.is_symlink() or cap.OUTPUT.is_symlink()
            or RUNTIME.resolve() != cap.OUTPUT.resolve() / "completion-v1"
            or RUNTIME.exists() and any(p.is_symlink() for p in RUNTIME.rglob("*"))):
        fail("Cap completion path contains symlink or escaped output")


def _write(path, value):
    orig.write_once(path, value)


def prepare():
    """One-time question/job and parent-byte freeze, without model or references."""
    safe_path()
    if RUNTIME.exists():
        fail("Cap completion already prepared or attempted")
    parent_plan, cap_plan, snapshot, completed, pending, old = parent_boundary()
    decision = verified(DECISION)
    if (decision.get("version") != "qwen17-cap-completion-decision-v1"
            or decision.get("parent_plan_sha256") != digest(parent_plan)
            or decision.get("remaining_jobs") != 30
            or decision.get("response_only_bound") != 107580
            or decision.get("parent_conservative_tokens") != 28035
            or decision.get("combined_maximum_tokens_without_child_retries") != 135615
            or decision.get("new_completion_wall_and_charged_seconds") != 28800):
        fail("Reviewed completion decision does not authorize this exact child")
    inventory = parent_snapshot()
    pins = source_hashes()
    for path, sha in cap_plan["arms"]["control_2k"]["asset_file_sha256"].items():
        if file_hash(path) != sha:
            fail("Pinned local 1.7B asset changed before completion preparation")
    with run_lock(RUNTIME):
        if any(p.name != ".lock" for p in RUNTIME.iterdir()):
            fail("Cap completion already prepared")
        # Recheck the old bytes after creating only our sibling directory.
        if parent_snapshot() != inventory:
            fail("Parent cap bytes changed during completion preparation")
        plan = {"version": VERSION, "spec": SPEC, "source_file_sha256": pins,
            "environment": orig.stable_environment(), "parent_file_sha256": inventory,
            "parent_inventory_sha256": digest(inventory),
            "parent_plan_sha256": digest(parent_plan), "cap_plan_sha256": digest(cap_plan),
            "snapshot_sha256": digest(snapshot), "parent_status_sha256": file_hash(parent.RUNTIME / "status.json"),
            "decision_file_sha256": file_hash(DECISION), "decision_sha256": digest(decision),
            "old_terminal_progress": old, "old_terminal_charged_tokens": 28035,
            "generation_implementation_sha256": parent_plan["generation_implementation_sha256"],
            "scoring_implementation_sha256": parent_plan["scoring_implementation_sha256"],
            "old_completed_job_ids": [r["job"]["id"] for r in completed],
            "ordered_jobs": parent_plan["ordered_jobs"],
            "pending_jobs": pending, "question_ids": parent_plan["question_ids"],
            "maximum_combined_reservation_tokens": 28035 + 107580,
            "prepared_at": time.time(), "original_protocol_completed": False,
            "original_limits_within_at_stop": True,
            "automatic_resume": False, "reference_access": False, "cloud_spend_usd": 0}
        _write(RUNTIME / "prepare-started.json", {"plan_sha256": digest(plan),
            "started_at": time.time(), "one_time": True})
        _write(RUNTIME / "plan.json", plan)
        atomic_json(RUNTIME / "status.json", envelope({"state": "prepared",
            "plan_sha256": digest(plan), "updated_at": time.time(),
            "completed_new": 0, "expected_new": 30, "references_opened": False}))
        return {"plan_sha256": digest(plan), "pending": 30,
                "maximum_combined_reservation_tokens": plan["maximum_combined_reservation_tokens"],
                "launch": "locked_until_independent_prelaunch_audit"}


def read_plan(*, verify_inputs=True, check_assets=False):
    safe_path()
    plan = verified(RUNTIME / "plan.json")
    marker = verified(RUNTIME / "prepare-started.json")
    if (plan["version"] != VERSION or plan["spec"] != SPEC
            or marker["plan_sha256"] != digest(plan) or marker["one_time"] is not True
            or plan["source_file_sha256"] != source_hashes()
            or plan["environment"] != orig.stable_environment()
            or plan["generation_implementation_sha256"] != orig.implementation_digest()
            or plan["scoring_implementation_sha256"] != scoring_v7.implementation_digest()
            or plan["parent_inventory_sha256"] != digest(plan["parent_file_sha256"])):
        fail("Cap completion source, scorer, environment or plan changed")
    if (file_hash(DECISION) != plan["decision_file_sha256"]
            or digest(verified(DECISION)) != plan["decision_sha256"]):
        fail("Frozen completion decision changed")
    if file_hash(parent.RUNTIME / "status.json") != plan["parent_status_sha256"]:
        fail("Stopped parent status changed")
    if verify_inputs:
        if parent_snapshot() != plan["parent_file_sha256"]:
            fail("Frozen parent cap artifact inventory changed")
        parent_plan, cap_plan, snapshot, completed, pending, old = parent_boundary()
        if (old != plan["old_terminal_progress"]
                or [r["job"]["id"] for r in completed] != plan["old_completed_job_ids"]):
            fail("Frozen parent terminal state changed")
    else:
        parent_plan = verified(parent.RUNTIME / "plan.json")
        cap_plan = verified(cap.OUTPUT / "plan.json")
        snapshot = verified(cap.OUTPUT / "question-snapshot.json")
        pending = pending_jobs(parent_plan, parent.completed_rows(parent_plan))
    if (digest(parent_plan) != plan["parent_plan_sha256"]
            or digest(cap_plan) != plan["cap_plan_sha256"]
            or digest(snapshot) != plan["snapshot_sha256"]
            or pending != plan["pending_jobs"]
            or plan["ordered_jobs"] != parent_plan["ordered_jobs"]
            or plan["question_ids"] != parent_plan["question_ids"]
            or plan["maximum_combined_reservation_tokens"] != 135615):
        fail("Cap completion pending jobs or parent identities changed")
    if list((RUNTIME / "launches").glob("*.json")):
        review = verified(RUNTIME / "prelaunch-review.json")
        if review != {"plan_sha256": digest(plan),
                       "parent_inventory_sha256": plan["parent_inventory_sha256"],
                       "decision": "independently_audited_allow_launch"}:
            fail("Cap completion prelaunch review changed")
    if check_assets:
        for path, sha in cap_plan["arms"]["control_2k"]["asset_file_sha256"].items():
            if file_hash(path) != sha:
                fail("Pinned local 1.7B asset changed")
    return plan, parent_plan, cap_plan, snapshot


def _all(folder):
    return {p.stem: verified(p) for p in (RUNTIME / folder).glob("*.json")}


def _jobs(plan):
    return {r["job"]["id"]: r for r in plan["pending_jobs"]}


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
    if any(r["explicit_resume"] for r in ordered):
        fail("Completion has no resume launch")
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
                or row["parent_plan_sha256"] != plan["parent_plan_sha256"]
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
                        or record["parent_plan_sha256"] != plan["parent_plan_sha256"]
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
            or any(len(v) > 1
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
            "unresolved": len(set(reservations) - set(receipts)),
            "combined_charged_tokens": plan["old_terminal_charged_tokens"] + tokens,
            "combined_charged_seconds": plan["old_terminal_progress"]["charged_seconds"] + seconds,
            "old_unknown_charged_tokens": 4610, "old_unknown_charged_seconds": 600}


def completed_new(plan, arm=None):
    jobs = _jobs(plan)
    plan_sha = digest(plan)
    paths = list((RUNTIME / "results").glob("*.json"))
    if len(paths) > 30 or any(p.stem not in jobs for p in paths):
        fail("Unknown cap result")
    result = []
    for entry in plan["pending_jobs"]:
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
                or row["parent_plan_sha256"] != plan["parent_plan_sha256"]
                or row["cap_plan_sha256"] != plan["cap_plan_sha256"]
                or row["implementation_sha256"] != plan["generation_implementation_sha256"]):
            fail("Cap result identity changed")
        value = GenerationResult(**row["result"])
        orig.validate_result(value, GenerationJob(**frozen))
        if value.termination == "timeout":
            fail("Timeout cannot be completed")
        receipt_path = RUNTIME / "ledger/settlements" / f"{row['attempt_id']}.json"
        if not receipt_path.exists():
            # A published result is live until its receipt is committed. There
            # is no child retry, so a killed/unsettled result cannot close.
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
    rows = completed_new(plan)
    return tally | {"completed_new": len(rows), "expected_new": 30,
                    "old_completed": 6, "combined_completed": 6 + len(rows),
                    "control_new_completed": sum(r["arm"] == "control_2k" for r in rows),
                    "extended_new_completed": sum(r["arm"] == "extended_4k" for r in rows),
                    "control_combined_completed": 3 + sum(r["arm"] == "control_2k" for r in rows),
                    "extended_combined_completed": 3 + sum(r["arm"] == "extended_4k" for r in rows)}


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
    remaining = SPEC["new_wall_seconds"] - tally["budget_seconds"]
    amount = 0 if job is None else job.max_tokens
    if (remaining <= 0 or tally["combined_charged_tokens"] + amount > SPEC["combined_token_limit"]
            or kind == "setup" and tally["setup_reservations"] >= SPEC["maximum_setups"]):
        raise orig.BudgetExhausted("Cap global budget cannot admit operation")
    if job is not None:
        frozen = _jobs(plan).get(job.id)
        if frozen is None or frozen["job"] != job.to_dict() or (RUNTIME / "results" / f"{job.id}.json").exists():
            fail("Cap job unknown or already complete")
        attempts = [r for r in _all("ledger/reservations").values()
                    if r["kind"] == "job" and r["job_id"] == job.id]
        if attempts:
            fail("Completion job cannot retry")
        done = {r["job"]["id"] for r in completed_new(plan)}
        first_pending = next((e["job"]["id"] for e in plan["pending_jobs"]
                              if e["job"]["id"] not in done), None)
        if job.id != first_pending:
            fail("Cap job reservation violates frozen alternating pair order")
    row = {"id": uuid.uuid4().hex, "plan_sha256": digest(plan),
        "parent_plan_sha256": plan["parent_plan_sha256"],
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


def hardware_snapshot(stage, job_id, *, elapsed_seconds=0.0):
    """Bounded read-only host observations; never used to alter inference."""
    try:
        observations = macos_guard.runtime_snapshot()
    except Exception as error:
        observations = {"unavailable": f"{type(error).__name__}: {error}"[:1024]}
    return {"stage": stage, "job_id": job_id, "observed_at": time.time(),
            "operation_elapsed_monotonic_seconds": elapsed_seconds,
            "descriptive_only": True, "host": observations}


def authenticate_collector(invocation_id):
    plan, _, cap_plan, snapshot = read_plan(verify_inputs=False)
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
            checked_plan, _, cap_plan, snapshot = read_plan()
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
            _write(RUNTIME / "hardware" / f"{job.id}-admission.json",
                   hardware_snapshot("admission", job.id))
            row = {"plan_sha256": digest(plan),
                "parent_plan_sha256": plan["parent_plan_sha256"],
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
            elapsed = time.monotonic() - began
            _write(RUNTIME / "job-telemetry" / f"{job.id}.json", {
                "job_id": job.id, "arm": entry["arm"], "cell_index": entry["cell_index"],
                "status": row["status"], "elapsed_monotonic_seconds": elapsed,
                "charged_tokens": tokens if tokens is not None else attempt["reserved_tokens"],
                "tokens_per_second": (tokens / elapsed if tokens is not None and elapsed > 0 else None),
                "attempt_id": attempt["id"], "observed_at": time.time()})
            status("collecting", plan, invocation_id=invocation_id)
            print(f"cap {entry['arm']} {job.question_id} {row['status']}", flush=True)
            if error is not None:
                raise error
        for entry in plan["pending_jobs"]:
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
            with macos_guard.user_activity():
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
        if (tally["budget_seconds"] > SPEC["new_wall_seconds"]
                or tally["combined_charged_tokens"] > SPEC["combined_token_limit"]):
            raise orig.BudgetExhausted("Cap global wall/token budget reached")
        active_path = RUNTIME / "active.json"
        active_state = {"kind": "idle", "elapsed_monotonic_seconds": 0.0}
        if active_path.exists():
            active = verified(active_path)
            if active.get("kind") != "idle":
                if active["invocation_id"] != invocation_id:
                    fail("Cap completion active operation has foreign invocation")
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
                    active_state = {"kind": active["kind"], "job_id": active.get("job_id"),
                        "arm": active.get("arm"), "cell_index": active.get("cell_index"),
                        "elapsed_monotonic_seconds": now - anchor["monotonic_before_reserve"],
                        "reserved_seconds": active["reserved_seconds"]}
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
            if active_state["kind"] == "job" and active_state["job_id"] is not None:
                for threshold in (600, 1200):
                    path = RUNTIME / "hardware" / f"{active_state['job_id']}-stall-{threshold}.json"
                    if active_state["elapsed_monotonic_seconds"] >= threshold and not path.exists():
                        _write(path, hardware_snapshot("coarse_stall", active_state["job_id"],
                            elapsed_seconds=active_state["elapsed_monotonic_seconds"]))
            atomic_json(RUNTIME / "telemetry-latest.json", envelope({
                "observed_at": time.time(), "child_pid": process.pid,
                "active": active_state, "charged_tokens": tally["charged_tokens"],
                "completed_new": len(completed_new(plan)),
                "rss_samples": telemetry["rss_samples"],
                "maximum_polled_rss_bytes": telemetry["maximum_polled_rss_bytes"]}))
            status("collecting", plan, child_pid=process.pid,
                   maximum_polled_rss_bytes=telemetry["maximum_polled_rss_bytes"],
                   active=active_state)
            last_status = now
        time.sleep(SPEC["poll_seconds"])


def live_wall_seconds():
    start = verified(RUNTIME / "collection-start.json")
    return time.time() - start["started_at"]


def combined_rows(plan, parent_plan=None):
    """Require exact old-six plus new-thirty coverage in the original catalog order."""
    if parent_plan is None:
        parent_plan = verified(parent.RUNTIME / "plan.json")
    if digest(parent_plan) != plan["parent_plan_sha256"]:
        fail("Frozen parent plan changed at combined endpoint")
    old = parent.completed_rows(parent_plan)
    new = completed_new(plan)
    if len(old) != 6 or len(new) != 30:
        fail("Combined 36-response cap endpoint is incomplete")
    by_id = {r["job"]["id"]: r for r in old + new}
    if len(by_id) != 36 or set(by_id) != {e["job"]["id"] for e in plan["ordered_jobs"]}:
        fail("Combined cap result IDs duplicate or differ from frozen jobs")
    ordered = []
    for entry in plan["ordered_jobs"]:
        row = by_id[entry["job"]["id"]]
        if (row["job"] != entry["job"] or row["arm"] != entry["arm"]
                or row["cell_index"] != entry["cell_index"]
                or row["status"] != "completed"):
            fail("Combined cap record identity changed")
        ordered.append(row)
    return ordered


def all_collectors_exited(plan, launch_id):
    invocations = _all("invocations")
    if len(invocations) != 1:
        fail("Completion must have exactly one invocation")
    invocation_id, binding = next(iter(invocations.items()))
    process = verified(RUNTIME / "invocation-processes" / f"{launch_id}.json")
    finish = verified(RUNTIME / "invocation-finishes" / f"{invocation_id}.json")
    if (binding["launch_id"] != launch_id or binding["plan_sha256"] != digest(plan)
            or process["launch_id"] != launch_id or process["invocation_id"] != invocation_id
            or process["exit_code"] != 0 or finish["state"] != "complete"
            or not orig.finite_number(process["finished_at"])):
        fail("Completion collector did not exit successfully")
    return process


def prefix_gate(plan, rows):
    return parent.prefix_gate(plan, rows)


def endpoint(plan, *, require_live=True):
    rows = combined_rows(plan)
    tally = usage(plan)
    if (tally["unresolved"] != 0 or tally["setup_reservations"] != 1
            or tally["attempts"] != 30
            or tally["combined_charged_tokens"] > SPEC["combined_token_limit"]
            or tally["budget_seconds"] > SPEC["new_wall_seconds"]
            or require_live and live_wall_seconds() > SPEC["new_wall_seconds"]):
        raise orig.BudgetExhausted("Completion endpoint budget or child settlement failed")
    pairs = prefix_gate(plan, rows)
    if len(pairs) != 18:
        fail("Completion new-pair prefix gate incomplete")
    return rows, pairs, tally


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
    live_plan, _, _, live_snapshot = authenticate_finalizer()
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
    rebound, _, _, _ = authenticate_finalizer()
    if digest(rebound) != digest(plan):
        fail("Cap finalizer binding changed before selected reference access")
    request = verified(RUNTIME / "finalize-request.json")
    all_collectors_exited(live_plan, request["launch_id"])
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
    rebound, _, _, _ = authenticate_finalizer()
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


def analyze_pairs(plan, rows, scores):
    return parent.analyze_pairs(plan, rows, scores)


def old_replay_diagnostic(cap_plan, rows):
    return parent.old_replay_diagnostic(cap_plan, rows)


def authenticate_finalizer():
    plan, parent_plan, cap_plan, snapshot = read_plan()
    request = verified(RUNTIME / "finalize-request.json")
    parent = verified(RUNTIME / "supervisor-starts" / f"{request['launch_id']}.json")
    if (request["plan_sha256"] != digest(plan) or parent["pid"] != os.getppid()
            or parent["launch_id"] != request["launch_id"]
            or (RUNTIME / "supervisor-finishes" / f"{request['launch_id']}.json").exists()):
        fail("Private cap finalizer is not bound to live supervisor")
    return plan, parent_plan, cap_plan, snapshot


def finalize():
    with run_lock(RUNTIME / "analysis"), run_lock(RUNTIME / "collection"):
        plan, parent_plan, cap_plan, snapshot = authenticate_finalizer()
        rows, pairs, tally = endpoint(plan)
        request = verified(RUNTIME / "finalize-request.json")
        all_collectors_exited(plan, request["launch_id"])
        if (request["records_sha256"] != digest(rows)
                or request["pair_gate_sha256"] != digest(pairs)
                or request["charged_tokens"] != tally["charged_tokens"]
                or request["combined_charged_tokens"] != tally["combined_charged_tokens"]
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
            "parent_plan_sha256": plan["parent_plan_sha256"],
            "cap_plan_sha256": plan["cap_plan_sha256"], "pair_gate_sha256": digest(pairs),
            "prelaunch_review_sha256": digest(verified(RUNTIME / "prelaunch-review.json")),
            "scores_sha256": digest(scores), "statistics": statistics_result,
            "old_replay_diagnostic": replay,
            "ledger": tally, "protected_originals_verified_before": before["protected_originals_verified"],
            "protected_originals_verified_after": after["protected_originals_verified"],
            "original_protocol_completed": False,
            "original_limits_within_at_stop": True,
            "old_runtime_failure_preserved": True,
            "protocol_deviation": "30 responses under separately authorized eight-hour completion child with 1800-second job deadlines",
            "old_terminal_progress": plan["old_terminal_progress"],
            "decision_sha256": plan["decision_sha256"],
            "combined_maximum_reservation_tokens": plan["maximum_combined_reservation_tokens"],
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
            plan, _, _, _ = read_plan(verify_inputs=False)
            launch = verified(RUNTIME / "launches" / f"{launch_id}.json")
            ready = verified(ready_path)
            launches = _launch_rows(plan)
            if (launch["launch_id"] != launch_id or launches[-1] != launch
                    or launch["plan_sha256"] != digest(plan) or ready["launch_id"] != launch_id
                    or ready["plan_sha256"] != digest(plan)):
                fail("Cap supervisor launch handshake changed")
            if len(launches) != 1:
                fail("Completion permits exactly one supervisor launch")
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
                    process = subprocess.Popen([sys.executable, "-m", "scripts.qwen17_cap_bridge_completion",
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
                "charged_tokens": tally["charged_tokens"],
                "combined_charged_tokens": tally["combined_charged_tokens"],
                "requested_at": time.time()})
            finalizer = None
            try:
                with (RUNTIME / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                    finalizer = subprocess.Popen([sys.executable, "-m", "scripts.qwen17_cap_bridge_completion",
                        "finalize"], cwd=ROOT, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, env=orig.native_environment())
                    while finalizer.poll() is None:
                        if live_wall_seconds() > SPEC["new_wall_seconds"]:
                            raise orig.BudgetExhausted("Cap finalization global wall ceiling reached")
                        time.sleep(SPEC["poll_seconds"])
            finally:
                _stop(finalizer)
                _write(RUNTIME / "finalize-process.json", {"pid": finalizer.pid if finalizer else None,
                    "exit_code": finalizer.returncode if finalizer else None,
                    "finished_at": time.time()})
            if finalizer is None or finalizer.returncode != 0:
                fail("Cap finalization process failed")
            if live_wall_seconds() > SPEC["new_wall_seconds"]:
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


def launch():
    os.chdir(ROOT)
    plan, _, _, _ = read_plan(verify_inputs=False)
    audit = verified(RUNTIME / "prelaunch-review.json")
    if audit != {"plan_sha256": digest(plan),
                  "parent_inventory_sha256": plan["parent_inventory_sha256"],
                  "decision": "independently_audited_allow_launch"}:
        fail("Independent cap completion prelaunch audit is required")
    clocks = recovery.launch_preflight()
    with run_lock(RUNTIME / "supervisor"):
        read_plan(verify_inputs=False)
        if verified(RUNTIME / "prelaunch-review.json") != audit:
            fail("Cap prelaunch audit changed")
        rows = _launch_rows(plan)
        current = verified(RUNTIME / "status.json")
        if (rows or current["state"] != "prepared"
                or (RUNTIME / "collection-start.json").exists()):
            fail("Completion launch is one-time with no resume")
        launch_id = uuid.uuid4().hex
        _write(RUNTIME / "launches" / f"{launch_id}.json", {
            "launch_id": launch_id, "plan_sha256": digest(plan),
            "reserved_at": time.time(), "explicit_resume": False,
            "clock_preflight": clocks})
        _write(RUNTIME / "collection-start.json", {"started_at": time.time(),
            "plan_sha256": digest(plan), "launch_id": launch_id})
        (RUNTIME / "logs").mkdir(exist_ok=True)
        try:
            with (RUNTIME / "logs" / f"supervisor-{launch_id}.log").open("x") as log:
                process = subprocess.Popen(["/usr/bin/caffeinate", "-s", "-i", sys.executable,
                    "-m", "scripts.qwen17_cap_bridge_completion", "supervisor", "--launch-id", launch_id],
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
    plan, _, cap_plan, snapshot = read_plan()
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
    parser.add_argument("command", choices=("prepare", "verify", "status", "launch",
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
