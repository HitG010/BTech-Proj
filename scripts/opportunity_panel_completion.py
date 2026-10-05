"""One separately authorized, bounded completion of 60 frozen 0.6B jobs.

The expired parent study and stopped recovery remain byte-for-byte unchanged.
Only the new completion-v1 child receives writes. ``prepare`` and ``launch``
are the only operator actions; collector, supervisor and finalize are private.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob, GenerationResult, Question
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import opportunity_panel_collect as orig
from scripts import opportunity_panel_recovery as recovery

ROOT = Path(__file__).resolve().parents[1]
CHILD = orig.STUDY / "completion-v1"
SOLVER = "qwen3-0.6b"
VERSION = "opportunity-panel-completion-v1"
SOURCE_FILES = ("scripts/opportunity_panel_completion.py", "tests/test_opportunity_panel_completion.py",
                "docs/opportunity-panel-completion.md", "scripts/opportunity_panel_recovery.py")
SPEC = {"version": VERSION, "pending_jobs": 60, "new_wall_seconds": 14400,
        "combined_token_limit": 1000000, "setup_seconds": 900, "job_seconds": 600,
        "maximum_new_setups": 1, "maximum_new_invocations": 1,
        "maximum_new_launches": 1, "maximum_polled_rss_bytes": 9 * 1024**3,
        "poll_seconds": 2, "watchdog_grace_seconds": 5,
        "automatic_resume": False, "cloud_spend_usd": 0,
        "purpose": "authorized diagnostic completion after original wall-budget failure"}


def fail(message):
    raise orig.IntegrityError(message)


def sources():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def parent_inventory():
    orig.safe_paths()
    return {str(path.relative_to(orig.STUDY)): file_hash(path)
            for path in sorted(orig.STUDY.rglob("*")) if path.is_file()
            and not path.is_relative_to(CHILD)}


def pending_jobs(protocol, completed):
    old = {row["job"]["id"] for row in completed[SOLVER]}
    jobs = [job for job in protocol["arms"][SOLVER]["jobs"] if job["id"] not in old]
    if (len(jobs) != 60 or len(old) != 196 or len(completed[orig.SOLVERS[0]]) != 256
            or len({job["id"] for job in jobs}) != 60):
        fail("Stopped parent does not have exactly 60 frozen 0.6B jobs")
    return jobs


def prepare():
    """Freeze current stopped parent bytes and the exact pending job identities."""
    with run_lock(orig.STUDY / "supervisor"), run_lock(orig.STUDY / "collection"):
        if CHILD.exists():
            fail("Completion child already exists")
        protocol = orig.read_protocol(check_assets=True)
        completed = orig.completed_records(protocol)
        jobs = pending_jobs(protocol, completed)
        old = orig.collection_status(protocol)
        old_invocations = orig.invocation_records(protocol)
        invocation_counts = {solver: sum(row["solver"] == solver for row in old_invocations)
                             for solver in orig.SOLVERS}
        stopped = verified(orig.STUDY / "recovery-v1/status.json")
        if (stopped["state"] != "needs_attention" or stopped["failure_kind"] != "budget"
                or stopped["progress"]["completed"] != 452
                or old["completed"] != 452 or old["charged_tokens"] != 342047
                or old["setup_reservations"] != 3 or old["attempts"] != 454
                or old["unresolved"] != 2 or old["budget_seconds"] <= orig.SPEC["global_seconds"]
                or invocation_counts != {orig.SOLVERS[0]: 2, SOLVER: 1}
                or sum(job["max_tokens"] for job in jobs) != 92220
                or (orig.STUDY / "collection-end.json").exists()
                or (orig.STUDY / "score-started.json").exists()):
            fail("Original budget-failure boundary changed")
        inventory = parent_inventory()
        plan = {"version": VERSION, "spec": SPEC, "parent_protocol_sha256": digest(protocol),
            "parent_inventory": inventory, "parent_inventory_sha256": digest(inventory),
            "source_file_sha256": sources(), "environment": orig.stable_environment(),
            "original_charged_tokens": old["charged_tokens"],
            "original_invocations_by_solver": invocation_counts,
            "combined_maximum_reservation_tokens": old["charged_tokens"] + sum(job["max_tokens"] for job in jobs),
            "original_terminal_progress": stopped["progress"],
            "original_recovery_status_sha256": file_hash(orig.STUDY / "recovery-v1/status.json"),
            "generation_implementation_sha256": protocol["generation_implementation_sha256"],
            "jobs": jobs, "question_ids": [r["child_question"]["id"] for r in protocol["selected"]],
            "prepared_at": time.time(), "old_protocol_budget_failed": True,
            "cloud_spend_usd": 0, "automatic_resume": False}
        orig.write_once(CHILD / "plan.json", plan)
        atomic_json(CHILD / "status.json", envelope({"state": "prepared", "plan_sha256": digest(plan),
            "updated_at": time.time(), "completed_new": 0, "original_protocol_budget_passed": False}))
        return {"plan_sha256": digest(plan), "pending": len(jobs),
                "original_charged_tokens": old["charged_tokens"],
                "combined_maximum_reservation_tokens": plan["combined_maximum_reservation_tokens"]}


def read_plan():
    plan = verified(CHILD / "plan.json")
    if (plan["version"] != VERSION or plan["spec"] != SPEC
            or plan["source_file_sha256"] != sources()
            or plan["environment"] != orig.stable_environment()
            or plan["parent_inventory_sha256"] != digest(plan["parent_inventory"])):
        fail("Completion plan, source, or environment changed")
    for relative, sha in plan["parent_inventory"].items():
        if file_hash(orig.STUDY / relative) != sha:
            fail(f"Parent original changed: {relative}")
    if set(parent_inventory()) != set(plan["parent_inventory"]):
        fail("New file appeared outside the completion child")
    protocol = orig.read_protocol()
    if (digest(protocol) != plan["parent_protocol_sha256"]
            or protocol["generation_implementation_sha256"] != plan["generation_implementation_sha256"]
            or file_hash(orig.STUDY / "recovery-v1/status.json") != plan["original_recovery_status_sha256"]
            or pending_jobs(protocol, orig.completed_records(protocol)) != plan["jobs"]):
        fail("Frozen parent protocol or pending jobs changed")
    return plan, protocol


def _all(directory):
    return {path.stem: verified(path) for path in (CHILD / directory).glob("*.json")}


def usage(plan, *, now=None):
    """Conservatively charge unresolved child reservations and new wall age."""
    # Append order is reservation -> attempt -> settlement. Read in reverse so
    # concurrent publication cannot falsely appear as an orphan receipt.
    settlements = _all("ledger/settlements")
    attempts = _all("attempt-records")
    reservations = _all("ledger/reservations")
    if not set(settlements) <= set(reservations) or not set(attempts) <= set(reservations):
        fail("Orphan child ledger entry")
    plan_sha = digest(plan)
    jobs = {job["id"]: job for job in plan["jobs"]}
    invocation_path = CHILD / "invocation.json"
    invocation = verified(invocation_path) if invocation_path.exists() else None
    if reservations and (invocation is None or invocation["plan_sha256"] != plan_sha):
        fail("Child reservations lack frozen invocation")
    tokens, seconds, setups, seen_jobs = 0, 0., 0, set()
    for key, row in reservations.items():
        if (row["id"] != key or row["completion_plan_sha256"] != plan_sha
                or row["parent_protocol_sha256"] != plan["parent_protocol_sha256"]
                or row["kind"] not in ("setup", "job")
                or row["invocation_id"] != invocation["invocation_id"]
                or not orig.finite_number(row["started_at"])
                or row["started_at"] < plan["prepared_at"]
                or type(row["reserved_tokens"]) is not int or row["reserved_tokens"] < 0
                or not orig.finite_number(row["reserved_seconds"]) or row["reserved_seconds"] <= 0):
            fail("Child reservation changed identity")
        if row["kind"] == "setup":
            setups += 1
            if row["reserved_tokens"] != 0 or row["reserved_seconds"] > SPEC["setup_seconds"]:
                fail("Invalid child setup")
        else:
            setup_path = CHILD / "ledger/settlements" / f"{row['session_id']}.json"
            setup_receipt = verified(setup_path) if setup_path.exists() else None
            if (row["job_id"] not in jobs or row["reserved_tokens"] != jobs[row["job_id"]]["max_tokens"]
                    or row["reserved_seconds"] > SPEC["job_seconds"] or row["session_id"] not in reservations
                    or reservations[row["session_id"]]["kind"] != "setup"
                    or reservations[row["session_id"]]["invocation_id"] != row["invocation_id"]
                    or setup_receipt is None or setup_receipt["status"] != "loaded"
                    or setup_receipt["id"] != row["session_id"]
                    or setup_receipt["reservation_sha256"] != digest(reservations[row["session_id"]])
                    or row["started_at"] < setup_receipt["finished_at"]):
                fail("Invalid child job reservation")
            if row["job_id"] in seen_jobs:
                fail("Child job was reserved twice")
            seen_jobs.add(row["job_id"])
        receipt = settlements.get(key)
        spent, duration = row["reserved_tokens"], row["reserved_seconds"]
        if receipt is not None:
            if (receipt["id"] != key or receipt["reservation_sha256"] != digest(row)
                    or receipt["status"] not in (("loaded", "failed") if row["kind"] == "setup" else ("completed", "failed"))
                    or type(receipt["charged_tokens"]) is not int
                    or not 0 <= receipt["charged_tokens"] <= row["reserved_tokens"]
                    or not orig.finite_number(receipt["elapsed_seconds"])
                    or receipt["elapsed_seconds"] < 0
                    or not orig.finite_number(receipt["finished_at"])
                    or receipt["finished_at"] < row["started_at"]):
                fail("Child settlement changed identity or cost")
            spent, duration = receipt["charged_tokens"], receipt["elapsed_seconds"]
            if receipt["status"] in ("loaded", "completed") and duration > row["reserved_seconds"]:
                fail("Successful child operation exceeded reservation")
            if row["kind"] == "job":
                record = attempts.get(key)
                if record is None or receipt["record_sha256"] != digest(record):
                    fail("Child attempt and settlement differ")
                if (record["job"] != jobs[row["job_id"]] or record["attempt_id"] != key
                        or record["session_id"] != row["session_id"]
                        or record["status"] != receipt["status"] or record["solver"] != SOLVER
                        or record["parent_protocol_sha256"] != plan["parent_protocol_sha256"]
                        or record["completion_plan_sha256"] != plan_sha
                        or record["implementation_sha256"] != plan["generation_implementation_sha256"]):
                    fail("Child attempt job changed")
                actual = row["reserved_tokens"]
                if receipt["status"] == "completed" and record["result"] is None:
                    fail("Completed child attempt lacks result")
                if record["result"] is not None:
                    try:
                        actual = orig.validate_result(GenerationResult(**record["result"]), GenerationJob(**record["job"]))
                    except (ValueError, TypeError, KeyError):
                        if receipt["status"] == "completed":
                            fail("Completed child result invalid")
                if spent != actual:
                    fail("Child token charge differs from result")
                if receipt["status"] == "completed":
                    if record["result"]["termination"] == "timeout":
                        fail("Timeout result cannot be completed")
                    if verified(CHILD / "results" / f"{row['job_id']}.json") != record:
                        fail("Child final result differs from attempt")
        tokens += spent
        seconds += duration
    if setups > 1 or len([r for r in reservations.values() if r["kind"] == "job"]) > 60:
        fail("Child operation ceiling exceeded")
    start = CHILD / "collection-start.json"
    end = CHILD / "collection-end.json"
    opening_row = verified(start) if start.exists() else None
    if (opening_row is not None and (opening_row["plan_sha256"] != plan_sha
            or not orig.finite_number(opening_row["started_at"])
            or opening_row["started_at"] < plan["prepared_at"])):
        fail("Child collection start changed")
    if reservations and opening_row is None:
        fail("Child reservations preceded collection start")
    closing_row = verified(end) if end.exists() else None
    if (closing_row is not None and (opening_row is None
            or closing_row["plan_sha256"] != plan_sha
            or not orig.finite_number(closing_row["finished_at"])
            or closing_row["finished_at"] < opening_row["started_at"]
            or any(row["started_at"] > closing_row["finished_at"] for row in reservations.values())
            or any(row["finished_at"] > closing_row["finished_at"] for row in settlements.values()))):
        fail("Child collection end changed")
    opening = opening_row["started_at"] if opening_row is not None else None
    closing = closing_row["finished_at"] if closing_row is not None else (time.time() if now is None else now)
    age = max(0., closing - opening) if opening is not None else 0.
    return {"charged_tokens": tokens, "charged_seconds": seconds, "wall_seconds": age,
            "budget_seconds": max(age, seconds), "setup_reservations": setups,
            "attempts": sum(r["kind"] == "job" for r in reservations.values()),
            "unresolved": len(set(reservations) - set(settlements)),
            "combined_charged_tokens": plan["original_charged_tokens"] + tokens}


def reserve(plan, kind, invocation_id, *, job=None, session_id=None, before_active=None):
    if (CHILD / "collection-end.json").exists():
        fail("Completion collection closed")
    tally = usage(plan)
    remaining = SPEC["new_wall_seconds"] - tally["budget_seconds"]
    tokens = 0 if job is None else job.max_tokens
    if (remaining <= 0 or tally["combined_charged_tokens"] + tokens > SPEC["combined_token_limit"]
            or kind == "setup" and tally["setup_reservations"] >= 1):
        raise orig.BudgetExhausted("Completion budget cannot admit operation")
    row = {"id": uuid.uuid4().hex, "completion_plan_sha256": digest(plan),
        "parent_protocol_sha256": plan["parent_protocol_sha256"],
        "invocation_id": invocation_id, "kind": kind, "started_at": time.time(),
        "reserved_tokens": tokens, "reserved_seconds": min(remaining,
            SPEC["setup_seconds"] if kind == "setup" else SPEC["job_seconds"])}
    if job is not None:
        row.update(job_id=job.id, session_id=session_id)
    orig.write_once(CHILD / "ledger/reservations" / f"{row['id']}.json", row)
    if before_active is not None:
        before_active(row)
    atomic_json(CHILD / "active.json", envelope(row))
    return row


def settle(reservation, status, began, *, tokens, record=None):
    charged = reservation["reserved_tokens"] if tokens is None else tokens
    receipt = {"id": reservation["id"], "reservation_sha256": digest(reservation),
        "status": status, "charged_tokens": charged,
        "elapsed_seconds": time.monotonic() - began, "finished_at": time.time()}
    if record is not None:
        receipt["record_sha256"] = digest(record)
    orig.write_once(CHILD / "ledger/settlements" / f"{reservation['id']}.json", receipt)
    atomic_json(CHILD / "active.json", envelope({"kind": "idle"}))
    return receipt


def completed_new(plan):
    jobs = {job["id"]: job for job in plan["jobs"]}
    paths = list((CHILD / "results").glob("*.json"))
    if len(paths) > 60 or any(path.stem not in jobs for path in paths):
        fail("Unknown completion result")
    rows = []
    for job in plan["jobs"]:
        path = CHILD / "results" / f"{job['id']}.json"
        if not path.exists():
            continue
        record = verified(path)
        if (record["job"] != job or record["solver"] != SOLVER or record["status"] != "completed"
                or record["parent_protocol_sha256"] != plan["parent_protocol_sha256"]
                or record["completion_plan_sha256"] != digest(plan)
                or record["implementation_sha256"] != plan["generation_implementation_sha256"]):
            fail("Completion result identity changed")
        result = GenerationResult(**record["result"])
        orig.validate_result(result, GenerationJob(**job))
        if result.termination == "timeout":
            fail("Timeout is not completed")
        receipt_path = CHILD / "ledger/settlements" / f"{record['attempt_id']}.json"
        if not receipt_path.exists():
            # Collector publishes its completed result before the receipt. The
            # live heartbeat counts it only after settlement; the endpoint
            # still requires all 60 settled rows.
            continue
        reservation = verified(CHILD / "ledger/reservations" / f"{record['attempt_id']}.json")
        receipt = verified(receipt_path)
        setup = verified(CHILD / "ledger/settlements" / f"{record['session_id']}.json")
        if (reservation["job_id"] != job["id"] or reservation["session_id"] != record["session_id"]
                or receipt["status"] != "completed" or receipt["record_sha256"] != digest(record)
                or setup["status"] != "loaded"):
            fail("Completion result ledger links changed")
        rows.append(record)
    return rows


def progress(plan):
    tally = usage(plan)
    count = len(completed_new(plan))
    return tally | {"completed_new": count, "expected_new": 60,
                    "original_completed": 452, "combined_completed": 452 + count}


def _status(state, plan, **extra):
    try:
        counts = progress(plan)
    except Exception as error:
        if state != "needs_attention":
            raise
        counts = {"integrity_error": f"{type(error).__name__}: {error}"}
    atomic_json(CHILD / "status.json", envelope({"state": state, "updated_at": time.time(),
        "plan_sha256": digest(plan), "progress": counts, "automatic_resume": False,
        "original_protocol_budget_passed": False, "cloud_spend_usd": 0, **extra}))


def collector(invocation_id):
    """Private live child; exact frozen jobs and backend, own child ledger."""
    plan, protocol = authenticate_collector(invocation_id)
    with run_lock(CHILD / "collection"):
        orig.write_once(CHILD / "invocation-start.json", {"invocation_id": invocation_id,
            "pid": os.getpid(), "started_at": time.time()})
        setup_began = time.monotonic()
        session = reserve(plan, "setup", invocation_id)
        orig.write_once(CHILD / "invocation-ready.json", {"invocation_id": invocation_id,
            "session_id": session["id"], "ready_at": time.time()})
        try:
            arm = protocol["arms"][SOLVER]
            config = orig.from_dict(arm["config"])
            for path, sha in arm["asset_file_sha256"].items():
                if file_hash(path) != sha:
                    fail("Frozen 0.6B asset changed before setup")
            engine = orig.TransformersBackend(config)
            if engine.metadata != arm["backend_metadata"]:
                fail("Frozen 0.6B backend metadata changed")
            engine.load()
            if hasattr(engine, "_sync"):
                engine._sync()
            if time.monotonic() - setup_began > session["reserved_seconds"]:
                raise orig.BudgetExhausted("Completion model setup exceeded reservation")
        except BaseException:
            settle(session, "failed", setup_began, tokens=0)
            raise
        receipt = settle(session, "loaded", setup_began, tokens=0)
        if receipt["elapsed_seconds"] > session["reserved_seconds"]:
            raise orig.BudgetExhausted("Completion model setup exceeded reservation")
        questions = {r["child_question"]["id"]: Question(**r["child_question"])
                     for r in protocol["selected"]}
        for frozen in plan["jobs"]:
            job = GenerationJob(**frozen)
            began = time.monotonic()
            attempt = reserve(plan, "job", invocation_id, job=job, session_id=session["id"])
            record = {"parent_protocol_sha256": plan["parent_protocol_sha256"],
                "completion_plan_sha256": digest(plan),
                "implementation_sha256": plan["generation_implementation_sha256"],
                "solver": SOLVER, "job": frozen, "status": "failed", "result": None,
                "attempt_id": attempt["id"], "session_id": session["id"]}
            tokens, error = None, None
            try:
                result = engine.generate(questions[job.question_id], job,
                    began + attempt["reserved_seconds"])
                record["result"] = result.to_dict()
                tokens = orig.validate_result(result, job)
                if result.termination == "timeout":
                    raise RuntimeError("Completion generation deadline reached")
                if time.monotonic() - began > attempt["reserved_seconds"]:
                    raise orig.BudgetExhausted("Completion generation exceeded reservation")
                record["status"] = "completed"
            except BaseException as exc:
                error = exc
                record["error"] = f"{type(exc).__name__}: {exc}"
            orig.write_once(CHILD / "attempt-records" / f"{attempt['id']}.json", record)
            if record["status"] == "completed":
                orig.write_once(CHILD / "results" / f"{job.id}.json", record)
            settle(attempt, record["status"], began, tokens=tokens, record=record)
            _status("collecting", plan, invocation_id=invocation_id)
            print(f"completion {len(completed_new(plan))}/60 {job.mode} draw={job.sample} {record['status']}", flush=True)
            if error is not None:
                raise error
        return progress(plan)


def authenticate_collector(invocation_id):
    plan, protocol = read_plan()
    launch = verified(CHILD / "launch.json")
    binding = verified(CHILD / "invocation.json")
    parent = verified(CHILD / "supervisor-start.json")
    if (binding != {"invocation_id": invocation_id, "launch_id": launch["launch_id"],
            "plan_sha256": digest(plan), "supervisor_pid": os.getppid()}
            or parent["pid"] != os.getppid() or parent["launch_id"] != launch["launch_id"]
            or (CHILD / "supervisor-finish.json").exists()):
        fail("Private completion collector is not bound to live supervisor")
    return plan, protocol


def private_collector(invocation_id):
    try:
        from scripts.macos_runtime_guard import user_activity

        with user_activity():
            result = collector(invocation_id)
        orig.write_once(CHILD / "invocation-finish.json", {"state": "complete", "progress": result})
        return 0
    except BaseException as error:
        kind = "budget" if isinstance(error, orig.BudgetExhausted) else "integrity" if isinstance(error, (ValueError, orig.IntegrityError)) else "runtime"
        orig.write_once(CHILD / "invocation-finish.json", {"state": "stopped", "failure_kind": kind,
            "reason": f"{type(error).__name__}: {error}"})
        print(f"Completion stopped: {type(error).__name__}: {error}", flush=True)
        return 1


def _stop(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def monitor(child, plan, began, telemetry):
    missing_id, missing_since, last_status = None, None, began - 10
    while child.poll() is None:
        now = time.monotonic()
        if not (CHILD / "invocation-ready.json").exists() and now - began > SPEC["setup_seconds"]:
            raise RuntimeError("Completion collector startup watchdog reached")
        tally = usage(plan)
        if (tally["budget_seconds"] > SPEC["new_wall_seconds"]
                or tally["combined_charged_tokens"] > SPEC["combined_token_limit"]):
            raise orig.BudgetExhausted("Completion wall/token budget reached")
        active_path = CHILD / "active.json"
        if active_path.exists():
            active = verified(active_path)
            if active.get("kind") != "idle":
                anchor_path = CHILD / "anchors" / f"{active['id']}.json"
                if anchor_path.exists():
                    anchor = verified(anchor_path)
                    if (anchor["reservation_sha256"] != digest(active)
                            or anchor["pid"] != child.pid or anchor["id"] != active["id"]):
                        fail("Completion active monotonic anchor changed")
                    if now - anchor["monotonic_before_reserve"] > active["reserved_seconds"] + SPEC["watchdog_grace_seconds"]:
                        raise RuntimeError("Completion monotonic operation watchdog reached")
                    missing_id, missing_since = None, None
                elif missing_id != active["id"]:
                    missing_id, missing_since = active["id"], now
                elif now - missing_since > SPEC["watchdog_grace_seconds"]:
                    fail("Completion active reservation lacks anchor")
        reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
            capture_output=True, text=True, timeout=5)
        if reading.returncode == 0 and reading.stdout.strip():
            telemetry["maximum_polled_rss_bytes"] = max(telemetry["maximum_polled_rss_bytes"],
                int(reading.stdout.strip()) * 1024)
            telemetry["rss_samples"] += 1
        elif child.poll() is None:
            raise RuntimeError("Completion child RSS telemetry unavailable")
        if telemetry["maximum_polled_rss_bytes"] > SPEC["maximum_polled_rss_bytes"]:
            raise RuntimeError("Completion child sampled RSS ceiling reached")
        if now - last_status >= 10:
            _status("collecting", plan, child_pid=child.pid,
                maximum_polled_rss_bytes=telemetry["maximum_polled_rss_bytes"])
            last_status = now
        time.sleep(SPEC["poll_seconds"])


def anchored_reserve(plan, kind, invocation_id, *, job=None, session_id=None):
    before = time.monotonic()
    def anchor(row):
        orig.write_once(CHILD / "anchors" / f"{row['id']}.json", {"id": row["id"],
            "reservation_sha256": digest(row), "monotonic_before_reserve": before,
            "pid": os.getpid(), "invocation_id": invocation_id})
    return _RESERVE(plan, kind, invocation_id, job=job, session_id=session_id,
        before_active=anchor)


_RESERVE = reserve


def collection_child(invocation_id):
    global reserve
    with run_lock(CHILD / "collector-entry"):
        authenticate_collector(invocation_id)
        if (CHILD / "invocation-start.json").exists() or (CHILD / "invocation-finish.json").exists():
            fail("Private completion collector invocation already used")
        reserve = anchored_reserve
        try:
            return private_collector(invocation_id)
        finally:
            reserve = _RESERVE


def combined_records(plan, protocol):
    old = orig.completed_records(protocol)
    new = completed_new(plan)
    if len(new) != 60 or len(old[SOLVER]) != 196 or len(old[orig.SOLVERS[0]]) != 256:
        fail("Combined endpoint is incomplete")
    # Analysis expects original record schema. Only the separately authorized
    # child identity fields differ; the frozen job/result/token data are intact.
    converted = [{"protocol_sha256": plan["parent_protocol_sha256"],
        "implementation_sha256": row["implementation_sha256"], "solver": row["solver"],
        "job": row["job"], "status": row["status"], "result": row["result"],
        "attempt_id": row["attempt_id"], "session_id": row["session_id"]} for row in new]
    grouped = {orig.SOLVERS[0]: old[orig.SOLVERS[0]], SOLVER: old[SOLVER] + converted}
    if len({r["job"]["id"] for r in grouped[SOLVER]}) != 256:
        fail("Duplicate 0.6B job across original and completion")
    return grouped


def live_wall_seconds():
    start = verified(CHILD / "collection-start.json")
    return time.time() - start["started_at"]


def finalize():
    """Separate child: full endpoint, exited collector, then selected gold only."""
    from scripts.opportunity_panel_analysis import (
        analyze_pairs,
        paired_rows,
        score_complete_endpoint,
    )

    with run_lock(CHILD / "analysis"), run_lock(orig.STUDY / "collection"):
        plan, protocol = read_plan()
        launch = verified(CHILD / "launch.json")
        supervisor_start = verified(CHILD / "supervisor-start.json")
        request = verified(CHILD / "finalize-request.json")
        finish = verified(CHILD / "invocation-finish.json")
        process = verified(CHILD / "invocation-process.json")
        tally = progress(plan)
        if (request["plan_sha256"] != digest(plan) or request["launch_id"] != launch["launch_id"]
                or request["completed_new"] != 60
                or supervisor_start["pid"] != os.getppid()
                or supervisor_start["launch_id"] != launch["launch_id"]
                or (CHILD / "supervisor-finish.json").exists()
                or finish["state"] != "complete" or process["exit_code"] != 0
                or tally["completed_new"] != 60 or tally["combined_completed"] != 512
                or tally["combined_charged_tokens"] > SPEC["combined_token_limit"]
                or tally["budget_seconds"] > SPEC["new_wall_seconds"]
                or live_wall_seconds() > SPEC["new_wall_seconds"]
                or not (CHILD / "collection-end.json").exists()):
            fail("Completion endpoint or accounting has not passed")
        from scripts.verify_phase2_repeat import verify

        before = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        grouped = combined_records(plan, protocol)

        report_path = CHILD / "report.json"
        if report_path.exists():
            cached = verified(report_path)
            scores_path = CHILD / "scores.numeric-v7.json"
            if not scores_path.exists():
                fail("Completion report lacks score cache")
            checked_scores = score_complete_endpoint(grouped, protocol["selected"],
                lambda _: fail("Cached report cannot reopen references"),
                protocol_sha256=digest(plan), output=scores_path)
            if (cached["plan_sha256"] != digest(plan)
                    or cached["parent_protocol_sha256"] != digest(protocol)
                    or cached["scores_sha256"] != digest(checked_scores)):
                fail("Completion report cache identity changed")
            return cached

        def selected_only_gold(selected):
            read_plan()
            current = progress(plan)
            if (current["completed_new"] != 60 or current["combined_completed"] != 512
                    or current["combined_charged_tokens"] > SPEC["combined_token_limit"]
                    or current["budget_seconds"] > SPEC["new_wall_seconds"]
                    or live_wall_seconds() > SPEC["new_wall_seconds"]):
                fail("Completion reference access boundary expired")
            orig.write_once(CHILD / "score-started.json", {"plan_sha256": digest(plan),
                "requested_at": time.time(), "selected_sha256": digest(selected)})
            return orig.selected_gold(selected)

        scores = score_complete_endpoint(grouped, protocol["selected"], selected_only_gold,
            protocol_sha256=digest(plan), output=CHILD / "scores.numeric-v7.json")
        orig.write_once(CHILD / "analysis-started.json", {"plan_sha256": digest(plan),
            "scores_sha256": digest(scores), "started_at": time.time()})
        rows = paired_rows(grouped, scores)
        statistics = analyze_pairs(rows, protocol["folds"],
            question_ids=plan["question_ids"], spec=protocol["analysis"])
        after = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        if live_wall_seconds() > SPEC["new_wall_seconds"]:
            raise orig.BudgetExhausted("Completion wall ceiling reached during analysis")
        report = {"version": VERSION, "plan_sha256": digest(plan),
            "parent_protocol_sha256": digest(protocol), "scores_sha256": digest(scores),
            "statistics": statistics, "ledger": tally,
            "original_invocations_by_solver": plan["original_invocations_by_solver"],
            "combined_invocations_by_solver": {orig.SOLVERS[0]: 2, SOLVER: 2},
            "combined_maximum_reservation_tokens": plan["combined_maximum_reservation_tokens"],
            "combined_charged_seconds": plan["original_terminal_progress"]["charged_seconds"] + tally["charged_seconds"],
            "combined_setup_reservations": plan["original_terminal_progress"]["setup_reservations"] + tally["setup_reservations"],
            "protected_originals_verified_before": before["protected_originals_verified"],
            "protected_originals_verified_after": after["protected_originals_verified"],
            "old_protocol_budget_passed": False,
            "protocol_deviation": "60 responses collected under separately authorized 4-hour completion child",
            "cloud_spend_usd": 0, "official_test_opened": False,
            "acquisition_or_rl_promotion": False}
        orig.write_once(report_path, report)
        return report


def supervisor(launch_id):
    os.chdir(ROOT)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    deadline = time.monotonic() + 30
    while not (CHILD / "launch-ready.json").exists():
        if time.monotonic() > deadline:
            atomic_json(CHILD / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "runtime", "reason": "Launch handshake expired", "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False}))
            orig.write_once(CHILD / "supervisor-finish.json", {"state": "needs_attention",
                "failure_kind": "runtime", "reason": "Launch handshake expired"})
            return 1
        time.sleep(.1)
    with run_lock(CHILD / "supervisor"), run_lock(orig.STUDY / "supervisor"):
        if (CHILD / "supervisor-start.json").exists():
            fail("Private completion supervisor already started")
        try:
            plan, protocol = read_plan()
            launch = verified(CHILD / "launch.json")
            if (launch["launch_id"] != launch_id or launch["plan_sha256"] != digest(plan)
                    or verified(CHILD / "launch-ready.json")["launch_id"] != launch_id):
                fail("Private completion supervisor launch changed identity")
        except BaseException as error:
            reason = f"{type(error).__name__}: {error}"
            atomic_json(CHILD / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "integrity", "reason": reason, "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False,
                "original_protocol_budget_passed": False}))
            orig.write_once(CHILD / "supervisor-finish.json", {"state": "needs_attention",
                "failure_kind": "integrity", "reason": reason})
            return 1
        orig.write_once(CHILD / "supervisor-start.json", {"launch_id": launch_id,
            "pid": os.getpid(), "started_at": time.time()})
        child = None
        try:
            with run_lock(CHILD / "collection"):
                if (CHILD / "invocation.json").exists():
                    fail("Completion invocation already used")
                invocation_id = uuid.uuid4().hex
                orig.write_once(CHILD / "collection-start.json", {"started_at": time.time(),
                    "plan_sha256": digest(plan)})
                orig.write_once(CHILD / "invocation.json", {"invocation_id": invocation_id,
                    "launch_id": launch_id, "plan_sha256": digest(plan), "supervisor_pid": os.getpid()})
            telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
            began = time.monotonic()
            try:
                with (CHILD / "logs" / f"collector-{invocation_id}.log").open("x") as log:
                    child = subprocess.Popen([sys.executable, "-m", "scripts.opportunity_panel_completion",
                        "collector", "--invocation-id", invocation_id], cwd=ROOT,
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=orig.native_environment())
                    monitor(child, plan, began, telemetry)
            finally:
                _stop(child)
                orig.write_once(CHILD / "invocation-process.json", {"pid": child.pid if child else None,
                    "exit_code": child.returncode if child else None,
                    "elapsed_monotonic_seconds": time.monotonic() - began,
                    **telemetry, "finished_at": time.time()})
            if child is None or child.returncode != 0:
                finish_path = CHILD / "invocation-finish.json"
                if finish_path.exists():
                    finished = verified(finish_path)
                    reason = finished.get("reason", "Completion collector stopped")
                    if finished.get("failure_kind") == "budget":
                        raise orig.BudgetExhausted(reason)
                    if finished.get("failure_kind") == "integrity":
                        raise orig.IntegrityError(reason)
                    raise RuntimeError(reason)
                raise RuntimeError("Completion collector exited without terminal event")
            if not telemetry["rss_samples"]:
                raise RuntimeError("No completion collector RSS observations")
            if len(completed_new(plan)) != 60:
                fail("Completion collector exited before 60 results")
            tally = progress(plan)
            if (tally["combined_charged_tokens"] > SPEC["combined_token_limit"]
                    or tally["budget_seconds"] > SPEC["new_wall_seconds"]):
                raise orig.BudgetExhausted("Completion ceiling reached")
            orig.write_once(CHILD / "collection-end.json", {"finished_at": time.time(),
                "plan_sha256": digest(plan)})
            _status("analyzing", plan)
            orig.write_once(CHILD / "finalize-request.json", {"plan_sha256": digest(plan),
                "launch_id": launch_id, "completed_new": 60, "requested_at": time.time()})
            child = None
            try:
                with (CHILD / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                    child = subprocess.Popen([sys.executable, "-m", "scripts.opportunity_panel_completion", "finalize"],
                        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=orig.native_environment())
                    while child.poll() is None:
                        if live_wall_seconds() > SPEC["new_wall_seconds"]:
                            raise orig.BudgetExhausted("Completion finalization wall ceiling reached")
                        time.sleep(SPEC["poll_seconds"])
            finally:
                _stop(child)
                orig.write_once(CHILD / "finalize-process.json", {"pid": child.pid if child else None,
                    "exit_code": child.returncode if child else None, "finished_at": time.time()})
            if child is None or child.returncode != 0:
                fail("Completion endpoint scoring/analysis process failed")
            report = verified(CHILD / "report.json")
            _status("complete", plan, report_sha256=digest(report))
            orig.write_once(CHILD / "supervisor-finish.json", {"state": "complete",
                "report_sha256": digest(report)})
            return 0
        except BaseException as error:
            kind = "budget" if isinstance(error, orig.BudgetExhausted) else "integrity" if isinstance(error, (ValueError, orig.IntegrityError)) else "runtime"
            reason = f"{type(error).__name__}: {error}"
            _status("needs_attention", plan, failure_kind=kind, reason=reason)
            orig.write_once(CHILD / "supervisor-finish.json", {"state": "needs_attention",
                "failure_kind": kind, "reason": reason})
            print(reason, flush=True)
            return 1


def launch():
    os.chdir(ROOT)
    plan, _ = read_plan()
    clocks = recovery.launch_preflight()
    with run_lock(CHILD / "supervisor"), run_lock(orig.STUDY / "supervisor"):
        read_plan()
        if (CHILD / "launch.json").exists():
            fail("Completion launch already consumed")
        launch_id = uuid.uuid4().hex
        orig.write_once(CHILD / "launch.json", {"launch_id": launch_id,
            "plan_sha256": digest(plan), "reserved_at": time.time(),
            "clock_preflight": clocks})
        (CHILD / "logs").mkdir(exist_ok=True)
        try:
            with (CHILD / "logs" / f"supervisor-{launch_id}.log").open("x") as log:
                process = subprocess.Popen(["/usr/bin/caffeinate", "-s", "-i", sys.executable,
                    "-m", "scripts.opportunity_panel_completion", "supervisor", "--launch-id", launch_id],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    env=orig.native_environment(), start_new_session=True)
        except BaseException as error:
            _status("needs_attention", plan, failure_kind="runtime",
                reason=f"Launch failed: {type(error).__name__}: {error}")
            orig.write_once(CHILD / "supervisor-finish.json", {"state": "needs_attention",
                "failure_kind": "runtime", "reason": f"Launch failed: {type(error).__name__}: {error}"})
            raise
        _status("launched", plan, pid=process.pid, launch_id=launch_id)
    orig.write_once(CHILD / "launch-ready.json", {"launch_id": launch_id, "ready_at": time.time()})
    return {"launch_id": launch_id, "pid": process.pid,
            "log": str(CHILD / "logs" / f"supervisor-{launch_id}.log")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "status", "launch", "collector", "supervisor", "finalize"))
    parser.add_argument("--invocation-id")
    parser.add_argument("--launch-id")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "status":
        print(verified(CHILD / "status.json"))
    elif args.command == "launch":
        print(launch())
    elif args.command == "collector":
        if not args.invocation_id:
            parser.error("Private invocation required")
        sys.exit(collection_child(args.invocation_id))
    elif args.command == "supervisor":
        if not args.launch_id:
            parser.error("Private launch required")
        sys.exit(supervisor(args.launch_id))
    else:
        print(finalize())


if __name__ == "__main__":
    main()
