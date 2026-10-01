"""One manually authorized recovery invocation for the frozen repeat panel.

Preparation archives the failed rows and inventories every pre-recovery file.
The original supervisor artifacts and frozen generation code are read-only.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from repeat_background_worker import collection_idle, environment, supervisor_idle  # noqa: E402

from reasoning_budget.confirmation import file_hash  # noqa: E402
from reasoning_budget.research_repeat import checked_run, read_protocol, status  # noqa: E402
from reasoning_budget.runner import _usage  # noqa: E402
from reasoning_budget.storage import (  # noqa: E402
    atomic_json,
    digest,
    envelope,
    read_json,
    run_lock,
    verified,
)

STUDY = REPO / "artifacts/research/data-efficiency-v1/repeat-panel-v1"
RECOVERY = STUDY / "recovery-v1"
PIN = "8b01db2cbb7b8d1777c40aa0a873f4626e4c6b2a04e9135a377a085a76f3c812"
POLICY = RECOVERY / "policy.json"
JOURNAL = RECOVERY / "journal.json"
STATE = RECOVERY / "status.json"
LOG = RECOVERY / "worker.log"
SNAPSHOT = RECOVERY / "preservation.json"
AUDIT = REPO / "scripts/verify_phase2_repeat.py"
HELPER = REPO / "scripts/macos_runtime_guard.py"
ORIGINAL_WORKER = REPO / "scripts/repeat_background_worker.py"
POLL_SECONDS = 60
MONITOR_SECONDS = 14 * 3600


def now():
    return datetime.now(timezone.utc).isoformat()


def frozen_protocol():
    protocol = read_protocol(STUDY)
    if digest(protocol) != PIN or len(protocol["snapshot"]["jobs"]) != 800:
        raise ValueError("Recovery requires the unchanged frozen 800-job protocol")
    return protocol


def original_exhausted():
    old_policy = verified(STUDY / "background-policy.json")
    old_journal = verified(STUDY / "background-journal.json")
    old_state = read_json(STUDY / "background-status.json")
    if (old_policy["max_collector_invocations"] != 2
            or old_journal["policy_sha256"] != digest(old_policy)
            or old_journal["collector_invocations_reserved"] != 2
            or old_policy["supervisor_sha256"] != file_hash(ORIGINAL_WORKER)
            or old_policy["audit_sha256"] != file_hash(AUDIT)
            or old_state["state"] != "needs_attention"):
        raise ValueError("Original bounded supervisor has not exhausted its two invocations")
    return old_policy, old_journal, old_state


def _fixed_paths(protocol):
    dataset = Path(protocol["snapshot"]["config"]["data_dir"])
    run = Path(protocol["snapshot"]["run_dir"])
    return [
        STUDY / "protocol.json", STUDY / "config.yaml", STUDY / "question-features.json",
        dataset / "manifest.json", dataset / "questions.json",
        run / "manifest.json", run / "environment.json", run / "questions.json",
        run / "resolved_config.json",
        STUDY / "background-status.json", STUDY / "background-worker.log",
        STUDY / "background-policy.json", STUDY / "background-journal.json",
    ]


def _inventory(paths):
    return {str(path): file_hash(path) for path in paths}


def preservation_inventory(protocol, rows):
    run = Path(protocol["snapshot"]["run_dir"])
    completed = [row for row in rows if row["status"] == "completed"]
    failed = [row for row in rows if row["status"] == "failed"]
    attempts = sorted((run / "attempts").glob("*.json"))
    sessions = sorted((run / "sessions").glob("*.json"))
    if len(completed) != 51 or len(failed) != 3 or len(attempts) != 57 or len(sessions) != 2:
        raise ValueError("Recovery starting endpoint is not the diagnosed 51/3/57/2 state")
    completed_paths = [run / "results" / f"{row['job']['id']}.json" for row in completed]
    failed_paths = [run / "results" / f"{row['job']['id']}.json" for row in failed]
    return {
        "fixed": _inventory(_fixed_paths(protocol)),
        "completed_results": _inventory(completed_paths),
        "failed_results": _inventory(failed_paths),
        "attempts": _inventory(attempts), "sessions": _inventory(sessions),
        "completed": 51, "failed_jobs": 3, "attempts_count": 57, "sessions_count": 2,
        "records_sha256_before": digest(rows),
    }


def check_preservation(snapshot, *, include_failed):
    groups = ["fixed", "completed_results", "attempts", "sessions"]
    if include_failed:
        groups.append("failed_results")
    for group in groups:
        for path, expected in snapshot[group].items():
            if file_hash(path) != expected:
                raise ValueError(f"Pre-recovery {group} changed: {path}")
    for original, archived in snapshot["failed_archive"].items():
        if file_hash(archived) != snapshot["failed_results"][original]:
            raise ValueError(f"Archived failed result changed: {archived}")


def policy_payload():
    return {
        "version": "repeat-recovery-v1", "protocol_sha256": PIN,
        "wrapper_sha256": file_hash(__file__), "runtime_guard_sha256": file_hash(HELPER),
        "audit_sha256": file_hash(AUDIT), "original_worker_sha256": file_hash(ORIGINAL_WORKER),
        "preservation_sha256": digest(verified(SNAPSHOT)),
        "max_collector_invocations": 1, "automatic_resume": False,
        "poll_seconds": POLL_SECONDS, "monitor_seconds": MONITOR_SECONDS,
        "generation_limits": {"charged_tokens": 1400000, "cumulative_hours": 12},
        "docker_action": "keep_running",
        "system_preferences_changed": False,
        "runtime_mitigation": "Process-scoped user-initiated activity and read-only host telemetry; stop at first durable failed job.",
        "causal_status": "Docker contention is an inference, not a proven cause",
        "later_studies_launched": False, "cloud_spend_usd": 0,
    }


def prepare():
    protocol = frozen_protocol()
    original_exhausted()
    if not supervisor_idle() or not collection_idle(protocol):
        raise ValueError("Original supervisor or generation collector is still active")
    # Match the existing supervisor -> study -> run lock order. Revalidate
    # inside the locks so no collector can change the inventory mid-snapshot.
    run = Path(protocol["snapshot"]["run_dir"])
    with (run_lock(STUDY / "background-supervisor"), run_lock(STUDY),
          run_lock(run), run_lock(RECOVERY)):
        protocol = frozen_protocol()
        original_exhausted()
        _, rows = checked_run(STUDY, protocol)
        if sum(row["status"] == "completed" for row in rows) == 800:
            raise ValueError("Recovery is unnecessary: fixed endpoint already complete")
        if any(path.exists() for path in (POLICY, JOURNAL, SNAPSHOT)):
            if not all(path.exists() for path in (POLICY, JOURNAL, SNAPSHOT)):
                raise ValueError("Partial recovery preparation requires review")
            policy = verified(POLICY)
            if policy != policy_payload():
                raise ValueError("Existing recovery policy changed")
            check_preservation(verified(SNAPSHOT), include_failed=True)
            return RECOVERY
        snapshot = preservation_inventory(protocol, rows)
        archive = RECOVERY / "failed-results-before"
        archive.mkdir(parents=True, exist_ok=False)
        snapshot["failed_archive"] = {}
        for original in snapshot["failed_results"]:
            target = archive / Path(original).name
            shutil.copy2(original, target)
            snapshot["failed_archive"][original] = str(target)
        check_preservation(snapshot, include_failed=True)
        atomic_json(SNAPSHOT, envelope(snapshot))
        policy = policy_payload()
        atomic_json(POLICY, envelope(policy))
        atomic_json(JOURNAL, envelope({"policy_sha256": digest(policy), "collector_invocations_reserved": 0}))
        atomic_json(STATE, {"state": "prepared", "updated_at_utc": now(),
                            "protocol_sha256": PIN, "policy_sha256": digest(policy),
                            "completed_before": 51, "cloud_spend_usd": 0})
    return RECOVERY


def checked_recovery(*, include_failed):
    protocol = frozen_protocol()
    original_exhausted()
    policy = verified(POLICY)
    if policy != policy_payload():
        raise ValueError("Recovery wrapper/helper/audit policy changed")
    journal = verified(JOURNAL)
    if journal["policy_sha256"] != digest(policy) or journal["collector_invocations_reserved"] not in (0, 1):
        raise ValueError("Recovery journal changed")
    snapshot = verified(SNAPSHOT)
    check_preservation(snapshot, include_failed=include_failed)
    return protocol, policy, journal, snapshot


def reserve_once(policy):
    journal = verified(JOURNAL)
    if journal["policy_sha256"] != digest(policy) or journal["collector_invocations_reserved"] != 0:
        raise ValueError("One recovery collector invocation was already reserved")
    journal["collector_invocations_reserved"] = 1
    journal["reserved_at_utc"] = now()
    atomic_json(JOURNAL, envelope(journal))


def checked_endpoint(protocol):
    _, rows = checked_run(STUDY, protocol)
    return len(rows) == 800 and all(row["status"] == "completed" for row in rows)


def progress_guard(message):
    print(message, flush=True)
    if " failed " in f" {message} " or "termination=timeout" in message:
        raise RuntimeError("Recovery stopped after the first durable failed job")


def collector():
    protocol, _, journal, _ = checked_recovery(include_failed=True)
    if journal["collector_invocations_reserved"] != 1 or not collection_idle(protocol):
        raise ValueError("Recovery collector was not reserved or generation is busy")
    tokens, seconds = _usage(Path(protocol["snapshot"]["run_dir"]))
    limits = protocol["snapshot"]["config"]["limits"]
    if tokens >= limits["max_tokens"] or seconds >= limits["max_elapsed_seconds"]:
        raise ValueError("Frozen cumulative generation budget is exhausted")
    from macos_runtime_guard import user_activity

    from reasoning_budget.research_repeat import collect

    with user_activity():
        collect(STUDY, progress=progress_guard)
    if not checked_endpoint(protocol):
        raise ValueError("One recovery invocation ended before the fixed endpoint")


def worker(launch_id):
    os.chdir(REPO)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    with run_lock(STUDY / "background-supervisor"):
        started = time.monotonic()
        child = None
        protocol, policy, journal, snapshot = checked_recovery(include_failed=True)
        if journal["collector_invocations_reserved"] != 0:
            raise ValueError("Recovery invocation already spent")

        def write(state, **extra):
            from macos_runtime_guard import runtime_snapshot

            atomic_json(STATE, {"state": state, "updated_at_utc": now(), "pid": os.getpid(),
                                "launch_id": launch_id, "protocol_sha256": PIN,
                                "policy_sha256": digest(policy), "recovery_invocations_reserved":
                                verified(JOURNAL)["collector_invocations_reserved"],
                                "runtime": runtime_snapshot(), "progress": status(STUDY),
                                "later_studies_launched": False, "cloud_spend_usd": 0, **extra})

        def run_child(command, state):
            nonlocal child
            child = subprocess.Popen(command, cwd=REPO, env=environment())
            while child.poll() is None:
                if time.monotonic() - started > MONITOR_SECONDS:
                    raise TimeoutError("Recovery reached the 14-hour monitoring ceiling")
                if verified(POLICY) != policy or policy_payload() != policy:
                    raise ValueError("Recovery policy changed during collection")
                write(state, child_pid=child.pid)
                time.sleep(POLL_SECONDS)
            code = child.returncode
            child = None
            return code

        try:
            deadline = time.monotonic() + 20
            while not (STATE.exists() and read_json(STATE).get("launch_id") == launch_id):
                if time.monotonic() > deadline:
                    raise TimeoutError("Recovery launcher handshake failed")
                time.sleep(0.1)
            if not collection_idle(protocol) or checked_endpoint(protocol):
                raise ValueError("Recovery collector is busy or endpoint already complete")
            reserve_once(policy)
            write("collecting")
            command = [sys.executable, str(Path(__file__).resolve()), "--collector"]
            if run_child(command, "collecting"):
                raise RuntimeError("Recovery collector exited with an error")
            if not collection_idle(protocol) or not checked_endpoint(protocol):
                raise ValueError("Recovery cannot analyze before all 800 completed responses")
            check_preservation(snapshot, include_failed=False)
            analyze = [sys.executable, "-m", "reasoning_budget.research_repeat", "analyze", "--study", str(STUDY)]
            if run_child(analyze, "analyzing"):
                raise RuntimeError("Frozen repeat analysis failed")
            audit = [sys.executable, str(AUDIT), "--study", str(STUDY)]
            if run_child(audit, "verifying"):
                raise RuntimeError("Independent repeat verification failed")
            check_preservation(snapshot, include_failed=False)
            report = verified(STUDY / "report.json")
            scale = report["statistics"]["scale_acquisition"]
            write("complete" if scale else "complete_with_gate_failures",
                  scale_acquisition=scale, signal_gates=report["statistics"]["gates"],
                  report=str(STUDY / "report.json"), verification=str(STUDY / "background-verification.json"))
            return 0
        except Exception as exc:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            write("needs_attention", reason=f"{type(exc).__name__}: {exc}")
            print(f"Recovery stopped: {type(exc).__name__}: {exc}", flush=True)
            return 1


def launch():
    os.chdir(REPO)
    protocol, policy, journal, _ = checked_recovery(include_failed=True)
    if journal["collector_invocations_reserved"] != 0:
        raise ValueError("Recovery collector invocation already spent")
    if not supervisor_idle() or not collection_idle(protocol):
        raise ValueError("Another supervisor or collector is running")
    if checked_endpoint(protocol):
        raise ValueError("Fixed endpoint is already complete")
    with run_lock(RECOVERY / "launch"):
        if STATE.exists() and read_json(STATE)["state"] != "prepared":
            raise ValueError("Recovery was already launched or requires review")
        launch_id = uuid.uuid4().hex
        with LOG.open("a") as log:
            child = subprocess.Popen(["/usr/bin/caffeinate", "-i", sys.executable,
                                      str(Path(__file__).resolve()), "--worker", "--launch-id", launch_id],
                                     cwd=REPO, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True, env=environment())
        atomic_json(STATE, {"state": "launched", "updated_at_utc": now(), "pid": child.pid,
                            "launch_id": launch_id, "protocol_sha256": PIN,
                            "policy_sha256": digest(policy), "cloud_spend_usd": 0})
        return child.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--collector", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--launch-id", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.prepare:
        print(prepare())
    elif args.status:
        print(json.dumps(read_json(STATE), indent=2))
    elif args.worker:
        sys.exit(worker(args.launch_id))
    elif args.collector:
        collector()
    else:
        print(f"Detached recovery supervisor PID {launch()}; {LOG}")


if __name__ == "__main__":
    main()
