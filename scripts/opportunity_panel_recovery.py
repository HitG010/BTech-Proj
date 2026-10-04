"""One manual, additive recovery of the frozen opportunity-panel collector.

Only ``prepare`` and ``launch`` are operator entry points. The other commands
are private children of the one launch. No original code or protocol is edited.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, run_lock, verified
from scripts import opportunity_panel_collect as orig

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = orig.STUDY / "recovery-v1"
POLICY_VERSION = "opportunity-panel-monotonic-recovery-v1"
EXPECTED_PROTOCOL_SHA256 = "d4e511ad16c1b7330452492a5c9d0a0c1a3dccc10418b0591ea73666fc1e44bc"
PIN_FILES = ("scripts/opportunity_panel_recovery.py", "tests/test_opportunity_panel_recovery.py",
             "docs/opportunity-panel-runtime-recovery.md")
MUTABLE_ORIGINALS = {"active.json", "status.json"}


def _integrity(message):
    raise orig.IntegrityError(message)


def _original_inventory():
    orig.safe_paths()
    return {str(path.relative_to(orig.STUDY)): file_hash(path)
            for path in sorted(orig.STUDY.rglob("*")) if path.is_file()
            and not path.is_relative_to(RECOVERY)
            and str(path.relative_to(orig.STUDY)) not in MUTABLE_ORIGINALS}


def _sources():
    return {name: file_hash(ROOT / name) for name in PIN_FILES}


def _preflight_state(protocol):
    status = orig.collection_status(protocol)
    launches = list((orig.STUDY / "supervisor-launches").glob("*.json"))
    invocations = orig.invocation_records(protocol)
    if (status["completed"] != 0 or status["attempts"] != 1 or status["unresolved"] != 1
            or status["setup_reservations"] != 1 or len(launches) != 1
            or len(invocations) != 1 or invocations[0]["solver"] != orig.SOLVERS[0]
            or (orig.STUDY / "collection-end.json").exists()
            or (orig.STUDY / "score-started.json").exists()):
        _integrity("The one-shot stopped-run boundary changed")
    old = read_json(orig.STUDY / "background-status.json")
    if old["state"] != "needs_attention" or old["failure_kind"] != "runtime":
        _integrity("Original supervisor did not stop on runtime failure")
    if status["budget_seconds"] >= orig.SPEC["global_seconds"] or status["charged_tokens"] >= orig.SPEC["global_tokens"]:
        raise orig.BudgetExhausted("Original shared budget has expired")
    return status


def prepare():
    """Freeze additive policy and every existing immutable original byte."""
    with run_lock(orig.STUDY / "supervisor"), run_lock(orig.STUDY / "collection"):
        if RECOVERY.exists():
            _integrity("Recovery preparation already exists")
        protocol = orig.read_protocol()
        if digest(protocol) != EXPECTED_PROTOCOL_SHA256:
            _integrity("Original protocol identity changed")
        status = _preflight_state(protocol)
        inventory = _original_inventory()
        mutable_hashes = {name: file_hash(orig.STUDY / name) for name in MUTABLE_ORIGINALS}
        plan = {"version": POLICY_VERSION, "protocol_sha256": digest(protocol),
                "original_inventory_sha256": digest(inventory), "original_inventory": inventory,
                "initial_mutable_file_sha256": mutable_hashes,
                "source_file_sha256": _sources(), "environment": orig.stable_environment(),
                "initial_status": status, "original_collection_start_sha256":
                file_hash(orig.STUDY / "collection-start.json"),
                "one_manual_launch": True, "automatic_resume": False,
                "time_policy": "original global wall age; monotonic per-operation sidecars",
                "cloud_spend_usd": 0}
        RECOVERY.mkdir(parents=True, exist_ok=False)
        for name, sha in mutable_hashes.items():
            original = orig.STUDY / name
            archived = RECOVERY / f"initial-{name}"
            with original.open("rb") as source, archived.open("xb") as destination:
                shutil.copyfileobj(source, destination)
                destination.flush()
                os.fsync(destination.fileno())
            if file_hash(archived) != sha or file_hash(original) != sha:
                _integrity(f"Mutable original changed during archive: {name}")
        orig.write_once(RECOVERY / "plan.json", plan)
        atomic_json(RECOVERY / "status.json", envelope({"state": "prepared", "plan_sha256": digest(plan),
            "updated_at": time.time(), "completed": 0, "automatic_resume": False}))
        return {"plan_sha256": digest(plan), "initial_status": status}


def read_plan(*, check_originals=True):
    plan = verified(RECOVERY / "plan.json")
    if (plan["version"] != POLICY_VERSION or plan["protocol_sha256"] != EXPECTED_PROTOCOL_SHA256
            or plan["source_file_sha256"] != _sources()
            or plan["environment"] != orig.stable_environment()
            or file_hash(orig.STUDY / "collection-start.json") != plan["original_collection_start_sha256"]):
        _integrity("Recovery plan/source/environment changed")
    if check_originals:
        for relative, sha in plan["original_inventory"].items():
            if file_hash(orig.STUDY / relative) != sha:
                _integrity(f"Frozen original changed: {relative}")
        for name, sha in plan["initial_mutable_file_sha256"].items():
            if file_hash(RECOVERY / f"initial-{name}") != sha:
                _integrity(f"Initial mutable original archive changed: {name}")
    protocol = orig.read_protocol()
    if digest(protocol) != plan["protocol_sha256"]:
        _integrity("Original protocol changed")
    return plan, protocol


def ac_power(text):
    return "Now drawing from 'AC Power'" in text


def launch_preflight(*, sleep=time.sleep, wall=time.time, monotonic=time.monotonic, run=subprocess.run):
    battery = run(["/usr/bin/pmset", "-g", "batt"], capture_output=True, text=True, timeout=10)
    if battery.returncode != 0 or not ac_power(battery.stdout):
        _integrity("AC power is required for process-scoped recovery guard")
    power = run(["/usr/sbin/ioreg", "-r", "-n", "IOPMrootDomain", "-d", "1", "-l"],
        capture_output=True, text=True, timeout=10)
    if power.returncode != 0:
        _integrity("System capability telemetry unavailable")
    import re
    match = re.search(r'"System Capabilities"\s*=\s*(\d+)', power.stdout)
    if match is None or int(match.group(1)) & 3 != 3:
        _integrity("System lacks CPU and graphics capabilities")
    w0, m0 = wall(), monotonic()
    sleep(2)
    w1, m1 = wall(), monotonic()
    if not (1.5 <= m1 - m0 <= 5 and abs((w1 - w0) - (m1 - m0)) <= 2):
        _integrity("Wall/monotonic clocks are not stable in no-model preflight")
    return {"wall_seconds": w1 - w0, "monotonic_seconds": m1 - m0,
            "ac_power": True, "system_capabilities": int(match.group(1))}


def _status(state, launch_id, protocol, **extra):
    try:
        progress = orig.collection_status(protocol)
    except Exception as error:
        if state != "needs_attention":
            raise
        progress = {"integrity_error": f"{type(error).__name__}: {error}"}
    atomic_json(RECOVERY / "status.json", envelope({"state": state, "launch_id": launch_id,
        "protocol_sha256": digest(protocol), "updated_at": time.time(), "progress": progress,
        "automatic_resume": False, "cloud_spend_usd": 0, **extra}))


def launch():
    """The only manual resume; launcher commits journals before its child runs."""
    os.chdir(ROOT)
    plan, protocol = read_plan()
    clocks = launch_preflight()
    with run_lock(orig.STUDY / "supervisor"), run_lock(orig.STUDY / "collection"):
        read_plan()
        if (RECOVERY / "launch.json").exists():
            _integrity("Recovery invocation already consumed")
        _preflight_state(protocol)
        if len(list((orig.STUDY / "supervisor-launches").glob("*.json"))) >= orig.SPEC["maximum_supervisor_launches"]:
            raise orig.BudgetExhausted("Original supervisor launch ceiling exhausted")
        launch_id = uuid.uuid4().hex
        launch_row = {"id": launch_id, "protocol_sha256": digest(protocol),
                      "reserved_at": time.time(), "resume": True}
        orig.write_once(orig.STUDY / "supervisor-launches" / f"{launch_id}.json", launch_row)
        orig.write_once(RECOVERY / "launch.json", {"launch_id": launch_id,
            "plan_sha256": digest(plan), "original_launch_sha256": digest(launch_row),
            "clock_preflight": clocks, "reserved_at": time.time()})
        (RECOVERY / "logs").mkdir(exist_ok=True)
        command = ["/usr/bin/caffeinate", "-s", "-i", sys.executable, "-m",
                   "scripts.opportunity_panel_recovery", "supervisor", "--launch-id", launch_id]
        try:
            with (RECOVERY / "logs" / f"supervisor-{launch_id}.log").open("x") as log:
                process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, env=orig.native_environment(), start_new_session=True)
        except BaseException as error:
            _status("needs_attention", launch_id, protocol, failure_kind="runtime",
                reason=f"Launch failed: {type(error).__name__}: {error}")
            orig.write_once(orig.STUDY / "supervisor-finishes" / f"{launch_id}.json", {
                "state": "needs_attention", "failure_kind": "runtime",
                "reason": f"Launch failed: {type(error).__name__}: {error}"})
            orig.write_once(RECOVERY / "supervisor-finish.json", {"state": "needs_attention",
                "launch_id": launch_id, "reason": f"Launch failed: {type(error).__name__}: {error}"})
            raise
        _status("launched", launch_id, protocol, pid=process.pid)
    orig.write_once(RECOVERY / "launch-ready.json", {"launch_id": launch_id, "ready_at": time.time()})
    return {"launch_id": launch_id, "pid": process.pid,
            "log": str(RECOVERY / "logs" / f"supervisor-{launch_id}.log")}


def anchored_reserve(protocol, solver, invocation_id, kind, *, job=None, session_id=None):
    """Call the original reservation exactly once, then bind a monotonic anchor."""
    begin = time.monotonic()
    reservation = _ORIGINAL_RESERVE(protocol, solver, invocation_id, kind, job=job, session_id=session_id)
    orig.write_once(RECOVERY / "anchors" / f"{reservation['id']}.json", {
        "id": reservation["id"], "reservation_sha256": digest(reservation),
        "invocation_id": invocation_id, "monotonic_before_reserve": begin,
        "pid": os.getpid()})
    return reservation


_ORIGINAL_RESERVE = orig.reserve


def collector(solver, invocation_id):
    plan, protocol = read_plan()
    launch = verified(RECOVERY / "launch.json")
    if launch["plan_sha256"] != digest(plan) or solver not in orig.SOLVERS:
        _integrity("Unreserved recovery collector")
    verify_collector_binding(solver, invocation_id, launch, plan, protocol)
    orig.reserve = anchored_reserve
    try:
        return orig.collector(solver, invocation_id)
    finally:
        orig.reserve = _ORIGINAL_RESERVE


def verify_collector_binding(solver, invocation_id, launch, plan, protocol, *, parent_pid=os.getppid):
    invocation = verified(orig.STUDY / "invocations" / f"{invocation_id}.json")
    binding = verified(RECOVERY / "invocations" / f"{invocation_id}.json")
    supervisor = verified(RECOVERY / "supervisor-start.json")
    original_supervisor = verified(orig.STUDY / "supervisor-starts" / f"{launch['launch_id']}.json")
    if (invocation["solver"] != solver or invocation["protocol_sha256"] != digest(protocol)
            or binding != {"invocation_id": invocation_id, "solver": solver,
                "launch_id": launch["launch_id"], "original_invocation_sha256": digest(invocation),
                "plan_sha256": digest(plan), "supervisor_pid": supervisor["pid"]}
            or supervisor["launch_id"] != launch["launch_id"]
            or supervisor["pid"] != original_supervisor["pid"]
            or supervisor["pid"] != parent_pid()
            or (RECOVERY / "supervisor-finish.json").exists()
            or (orig.STUDY / "supervisor-finishes" / f"{launch['launch_id']}.json").exists()):
        _integrity("Recovery collector invocation changed")
    return binding


def operation_elapsed(active, invocation_id, *, now=time.monotonic, expected_pid=None):
    if active.get("kind") == "idle" or active.get("invocation_id") != invocation_id:
        return None
    anchor_path = RECOVERY / "anchors" / f"{active['id']}.json"
    if not anchor_path.exists() or anchor_path.is_symlink():
        _integrity("Active operation monotonic anchor missing or linked")
    anchor = verified(anchor_path)
    if (anchor["id"] != active["id"] or anchor["reservation_sha256"] != digest(active)
            or anchor["invocation_id"] != invocation_id
            or expected_pid is not None and anchor["pid"] != expected_pid):
        _integrity("Active operation monotonic anchor changed")
    elapsed = now() - anchor["monotonic_before_reserve"]
    if elapsed < 0:
        _integrity("Monotonic clock moved backward")
    return elapsed


def _stop_child(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def _monitor(child, invocation_id, protocol, supervisor_began, child_began, telemetry,
             launch_id, solver):
    missing_id, missing_first_seen = None, None
    last_update = time.monotonic() - 10
    while child.poll() is None:
        current = time.monotonic()
        if not (orig.STUDY / "invocation-ready" / f"{invocation_id}.json").exists() and current - child_began > orig.SPEC["setup_seconds"]:
            raise RuntimeError("Collector startup watchdog reached")
        if current - supervisor_began > orig.SPEC["supervisor_seconds"]:
            raise orig.BudgetExhausted("Recovery supervisor monotonic ceiling reached")
        tally = orig.usage(protocol)
        if tally["budget_seconds"] > orig.SPEC["global_seconds"] or tally["charged_tokens"] > orig.SPEC["global_tokens"]:
            raise orig.BudgetExhausted("Original shared budget reached")
        active_path = orig.STUDY / "active.json"
        if active_path.exists():
            active = verified(active_path)
            if active.get("kind") != "idle" and active.get("invocation_id") == invocation_id:
                anchor_path = RECOVERY / "anchors" / f"{active['id']}.json"
                if anchor_path.exists():
                    elapsed = operation_elapsed(active, invocation_id, expected_pid=child.pid)
                    missing_id, missing_first_seen = None, None
                    if elapsed > active["reserved_seconds"] + orig.SPEC["watchdog_grace_seconds"]:
                        raise RuntimeError("Monotonic setup/job watchdog reached")
                else:
                    if missing_id != active["id"]:
                        missing_id, missing_first_seen = active["id"], current
                    elif current - missing_first_seen > orig.SPEC["watchdog_grace_seconds"]:
                        _integrity("Active reservation lacks recovery clock anchor")
        reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
            text=True, capture_output=True, timeout=5)
        if reading.returncode == 0 and reading.stdout.strip():
            telemetry["maximum_polled_rss_bytes"] = max(telemetry["maximum_polled_rss_bytes"],
                int(reading.stdout.strip()) * 1024)
            telemetry["rss_samples"] += 1
        elif child.poll() is None:
            raise RuntimeError("Own collector RSS telemetry unavailable")
        if telemetry["maximum_polled_rss_bytes"] > orig.SPEC["maximum_polled_rss_bytes"]:
            raise RuntimeError("Own collector sampled RSS ceiling reached")
        if current - last_update >= 10:
            _status("collecting", launch_id, protocol, solver=solver,
                invocation_id=invocation_id, child_pid=child.pid,
                maximum_polled_rss_bytes=telemetry["maximum_polled_rss_bytes"])
            last_update = current
        time.sleep(orig.SPEC["poll_seconds"])


def verify_supervisor_launch(launch_id, plan, protocol):
    launch = verified(RECOVERY / "launch.json")
    original = verified(orig.STUDY / "supervisor-launches" / f"{launch_id}.json")
    if (launch["launch_id"] != launch_id or launch["plan_sha256"] != digest(plan)
            or launch["original_launch_sha256"] != digest(original)
            or original["id"] != launch_id or original["protocol_sha256"] != digest(protocol)
            or original["resume"] is not True
            or (RECOVERY / "supervisor-start.json").exists()
            or (orig.STUDY / "supervisor-starts" / f"{launch_id}.json").exists()):
        _integrity("Recovery supervisor launch is unreserved or already started")
    return launch


def raise_collector_failure(invocation_id):
    finish_path = orig.STUDY / "invocation-finishes" / f"{invocation_id}.json"
    if finish_path.exists():
        finish = verified(finish_path)
        reason = finish.get("reason", "Recovery collector exited with error")
        if finish.get("failure_kind") == "budget":
            raise orig.BudgetExhausted(reason)
        if finish.get("failure_kind") == "integrity":
            raise orig.IntegrityError(reason)
        raise RuntimeError(reason)
    raise RuntimeError("Recovery collector exited without a terminal event")


def supervisor(launch_id):
    os.chdir(ROOT)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    deadline = time.monotonic() + 30
    while not (RECOVERY / "launch-ready.json").exists():
        if time.monotonic() > deadline:
            reason = "Recovery launch handshake expired"
            try:
                _, protocol = read_plan()
                _status("needs_attention", launch_id, protocol, failure_kind="runtime", reason=reason)
                orig.write_once(orig.STUDY / "supervisor-finishes" / f"{launch_id}.json", {
                    "state": "needs_attention", "failure_kind": "runtime", "reason": reason})
                orig.write_once(RECOVERY / "supervisor-finish.json", {"state": "needs_attention",
                    "launch_id": launch_id, "failure_kind": "runtime", "reason": reason})
            finally:
                _integrity(reason)
        time.sleep(.1)
    ready = verified(RECOVERY / "launch-ready.json")
    if ready["launch_id"] != launch_id:
        _integrity("Recovery launch handshake changed")
    with run_lock(orig.STUDY / "supervisor"):
        if ((RECOVERY / "supervisor-start.json").exists()
                or (orig.STUDY / "supervisor-starts" / f"{launch_id}.json").exists()):
            _integrity("Recovery supervisor already started; no second invocation")
        try:
            plan, protocol = read_plan()
            verify_supervisor_launch(launch_id, plan, protocol)
        except BaseException as error:
            reason = f"{type(error).__name__}: {error}"
            atomic_json(RECOVERY / "status.json", envelope({"state": "needs_attention",
                "launch_id": launch_id, "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
                "failure_kind": "integrity", "reason": reason, "updated_at": time.time(),
                "automatic_resume": False, "cloud_spend_usd": 0}))
            orig.write_once(orig.STUDY / "supervisor-finishes" / f"{launch_id}.json", {
                "state": "needs_attention", "failure_kind": "integrity", "reason": reason})
            orig.write_once(RECOVERY / "supervisor-finish.json", {"state": "needs_attention",
                "launch_id": launch_id, "failure_kind": "integrity", "reason": reason})
            return 1
        began = time.monotonic()
        orig.write_once(orig.STUDY / "supervisor-starts" / f"{launch_id}.json", {
            "pid": os.getpid(), "started_at": time.time()})
        orig.write_once(RECOVERY / "supervisor-start.json", {"launch_id": launch_id,
            "pid": os.getpid(), "started_at": time.time(), "implementation_sha256":
            plan["source_file_sha256"]["scripts/opportunity_panel_recovery.py"]})
        try:
            for solver in orig.SOLVERS:
                if len(orig.completed_records(protocol)[solver]) == len(protocol["arms"][solver]["jobs"]):
                    continue
                with run_lock(orig.STUDY / "collection"):
                    invocation_id = orig.reserve_invocation(protocol, solver)
                    invocation = verified(orig.STUDY / "invocations" / f"{invocation_id}.json")
                    orig.write_once(RECOVERY / "invocations" / f"{invocation_id}.json", {
                        "invocation_id": invocation_id, "solver": solver, "launch_id": launch_id,
                        "original_invocation_sha256": digest(invocation), "plan_sha256": digest(plan),
                        "supervisor_pid": os.getpid()})
                _status("collecting", launch_id, protocol, solver=solver,
                    invocation_id=invocation_id, child_pid=None)
                child = None
                telemetry = {"maximum_polled_rss_bytes": 0, "rss_samples": 0}
                child_begin = time.monotonic()
                try:
                    with (RECOVERY / "logs" / f"collector-{invocation_id}.log").open("x") as log:
                        child = subprocess.Popen([sys.executable, "-m", "scripts.opportunity_panel_recovery",
                            "collector", "--solver", solver, "--invocation-id", invocation_id],
                            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            env=orig.native_environment())
                        _monitor(child, invocation_id, protocol, began, child_begin, telemetry,
                            launch_id, solver)
                finally:
                    _stop_child(child)
                    orig.write_once(orig.STUDY / "invocation-processes" / f"{invocation_id}.json", {
                        "pid": child.pid if child else None, "exit_code": child.returncode if child else None,
                        "wall_seconds": time.monotonic() - child_begin, **telemetry,
                        "finished_at": time.time()})
                if child is None or child.returncode != 0:
                    raise_collector_failure(invocation_id)
                if not telemetry["rss_samples"]:
                    raise RuntimeError("Recovery collector lacked RSS observations")
                if len(orig.completed_records(protocol)[solver]) != len(protocol["arms"][solver]["jobs"]):
                    _integrity("Collector exited before frozen endpoint")
                _status("collecting", launch_id, protocol, solver=solver)
            if orig.collection_status(protocol)["completed"] != orig.SPEC["responses"]:
                _integrity("Full endpoint not reached")
            _status("analyzing", launch_id, protocol)
            orig.write_once(RECOVERY / "finalize-request.json", {"launch_id": launch_id,
                "plan_sha256": digest(plan), "protocol_sha256": digest(protocol),
                "completed": orig.SPEC["responses"], "requested_at": time.time()})
            child = None
            try:
                with (RECOVERY / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                    child = subprocess.Popen([sys.executable, "-m", "scripts.opportunity_panel_collect", "finalize"],
                        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=orig.native_environment())
                    while child.poll() is None:
                        if time.monotonic() - began > orig.SPEC["supervisor_seconds"]:
                            raise orig.BudgetExhausted("Recovery supervisor ceiling during finalization")
                        time.sleep(orig.SPEC["poll_seconds"])
            finally:
                _stop_child(child)
                orig.write_once(RECOVERY / "finalize-process.json", {"pid": child.pid if child else None,
                    "exit_code": child.returncode if child else None, "finished_at": time.time()})
            if child is None or child.returncode != 0:
                _integrity("Frozen endpoint scoring/analysis failed")
            report = verified(orig.STUDY / "report.json")
            _status("complete", launch_id, protocol, report_sha256=digest(report))
            orig.write_once(orig.STUDY / "supervisor-finishes" / f"{launch_id}.json", {
                "state": "complete", "report_sha256": digest(report)})
            orig.write_once(RECOVERY / "supervisor-finish.json", {"state": "complete",
                "launch_id": launch_id, "report_sha256": digest(report)})
            return 0
        except BaseException as error:
            kind = "budget" if isinstance(error, orig.BudgetExhausted) else "integrity" if isinstance(error, (orig.IntegrityError, ValueError)) else "runtime"
            reason = f"{type(error).__name__}: {error}"
            _status("needs_attention", launch_id, protocol, failure_kind=kind, reason=reason)
            orig.write_once(orig.STUDY / "supervisor-finishes" / f"{launch_id}.json", {
                "state": "needs_attention", "failure_kind": kind, "reason": reason})
            orig.write_once(RECOVERY / "supervisor-finish.json", {"state": "needs_attention",
                "launch_id": launch_id, "failure_kind": kind, "reason": reason})
            print(reason, flush=True)
            return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "status", "launch", "collector", "supervisor"))
    parser.add_argument("--solver", choices=orig.SOLVERS)
    parser.add_argument("--invocation-id")
    parser.add_argument("--launch-id")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "status":
        print(verified(RECOVERY / "status.json"))
    elif args.command == "launch":
        print(launch())
    elif args.command == "collector":
        if not args.solver or not args.invocation_id:
            parser.error("Reserved collector identity required")
        sys.exit(collector(args.solver, args.invocation_id))
    else:
        if not args.launch_id:
            parser.error("Reserved launch ID required")
        sys.exit(supervisor(args.launch_id))


if __name__ == "__main__":
    main()
