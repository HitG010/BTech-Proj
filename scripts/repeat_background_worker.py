"""Detached bounded supervisor for the frozen Phase 2 repeat panel."""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from reasoning_budget.confirmation import file_hash  # noqa: E402
from reasoning_budget.research_repeat import read_protocol, status  # noqa: E402
from reasoning_budget.storage import (  # noqa: E402
    atomic_json,
    digest,
    envelope,
    read_json,
    run_lock,
    verified,
)

STUDY = REPO / "artifacts/research/data-efficiency-v1/repeat-panel-v1"
PIN = "8b01db2cbb7b8d1777c40aa0a873f4626e4c6b2a04e9135a377a085a76f3c812"
STATE = STUDY / "background-status.json"
LOG = STUDY / "background-worker.log"
POLICY = STUDY / "background-policy.json"
JOURNAL = STUDY / "background-journal.json"
AUDIT = REPO / "scripts/verify_phase2_repeat.py"
POLL_SECONDS = 60
MONITOR_SECONDS = 14 * 3600


def now():
    return datetime.now(timezone.utc).isoformat()


def environment():
    return dict(os.environ, PYTHONPATH=str(REPO / "src"), HF_HUB_OFFLINE="1",
                PYTHONUNBUFFERED="1", PYTORCH_ENABLE_MPS_FALLBACK="0",
                OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def checked_protocol():
    p = read_protocol(STUDY)
    if digest(p) != PIN or len(p["snapshot"]["jobs"]) != 800 or p["collection_permission"]["role"] != "repeat":
        raise ValueError("Supervisor only permits the pinned 800-response repeat study")
    return p


def collection_idle(protocol):
    with ExitStack() as stack:
        for directory in [STUDY, Path(protocol["snapshot"]["run_dir"])]:
            if not directory.exists():
                continue
            stream = stack.enter_context((directory / ".lock").open("a+"))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
    return True


def supervisor_idle():
    directory = STUDY / "background-supervisor"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
    return True


def reserve_collection(policy):
    journal = verified(JOURNAL)
    if journal["policy_sha256"] != digest(policy):
        raise ValueError("Background invocation journal differs from policy")
    count = journal["collector_invocations_reserved"]
    if count >= policy["max_collector_invocations"]:
        raise ValueError("Incomplete endpoint after the initial collector and one bounded resume")
    journal["collector_invocations_reserved"] = count + 1
    journal["last_reserved_at_utc"] = now()
    atomic_json(JOURNAL, envelope(journal))
    return count + 1


def policy_payload():
    return {"version": "repeat-background-v1", "protocol_sha256": PIN,
            "supervisor_sha256": file_hash(__file__), "audit_sha256": file_hash(AUDIT),
            "max_collector_invocations": 2, "poll_seconds": POLL_SECONDS,
            "monitor_seconds": MONITOR_SECONDS,
            "generation_limits": {"charged_tokens": 1400000, "cumulative_hours": 12},
            "automatic_analysis": "Only after 800 completed responses and collector exit",
            "later_studies_launched": False, "cloud_spend_usd": 0}


def worker(launch_id):
    os.chdir(REPO)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    with run_lock(STUDY / "background-supervisor"):
        started = now()
        started_clock = time.monotonic()
        child = None
        policy = verified(POLICY)
        if policy != policy_payload():
            raise ValueError("Background supervisor/audit policy changed")

        def write(state, **details):
            journal = verified(JOURNAL)
            atomic_json(STATE, {
                "state": state, "pid": os.getpid(), "launch_id": launch_id,
                "started_at_utc": started, "updated_at_utc": now(),
                "protocol_sha256": PIN, "policy_sha256": digest(policy),
                "supervisor_sha256": policy["supervisor_sha256"],
                "audit_sha256": policy["audit_sha256"],
                "collector_invocations_reserved": journal["collector_invocations_reserved"],
                "automatic_resume_used": journal["collector_invocations_reserved"] > 1,
                "poll_seconds": POLL_SECONDS, "ledger_includes_active_reservations": True,
                "later_studies_launched": False, "cloud_spend_usd": 0, **details,
            })

        def run_child(command, state):
            nonlocal child
            child = subprocess.Popen(command, cwd=REPO, env=environment())
            while child.poll() is None:
                if time.monotonic() - started_clock > MONITOR_SECONDS:
                    raise TimeoutError("Supervisor reached its 14-hour monitoring ceiling")
                if policy != policy_payload():
                    raise ValueError("Operational scripts changed during collection")
                write(state, child_pid=child.pid, progress=status(STUDY))
                time.sleep(POLL_SECONDS)
            code = child.returncode
            child = None
            return code

        try:
            # The parent publishes the detached PID before this worker publishes
            # progress, avoiding a late parent write over a newer worker state.
            handshake_deadline = time.monotonic() + 20
            while not (STATE.exists() and read_json(STATE).get("launch_id") == launch_id):
                if time.monotonic() > handshake_deadline:
                    raise TimeoutError("Launcher did not publish its startup record")
                time.sleep(0.1)
            protocol = checked_protocol()
            write("starting", progress=status(STUDY))
            while True:
                if time.monotonic() - started_clock > MONITOR_SECONDS:
                    raise TimeoutError("Supervisor reached its 14-hour monitoring ceiling")
                progress = status(STUDY)
                idle = collection_idle(protocol)
                if idle and progress["completed"] == progress["expected"] == 800:
                    break
                if not idle:
                    write("monitoring_existing_collector", progress=progress)
                    time.sleep(POLL_SECONDS)
                    continue
                invocation = reserve_collection(policy)
                write("collecting" if invocation == 1 else "resuming", progress=progress)
                command = [sys.executable, "-m", "reasoning_budget.research_repeat",
                           "collect", "--study", str(STUDY)]
                if run_child(command, "collecting" if invocation == 1 else "resuming"):
                    raise RuntimeError("Collector exited with an error; inspect background-worker.log")
                # A zero return code can mean budget/failure stop. Recheck the fixed
                # endpoint; one durable automatic resume is the entire allowance.

            if not collection_idle(protocol):
                raise ValueError("Collection locks were reacquired before analysis")
            command = [sys.executable, "-m", "reasoning_budget.research_repeat",
                       "analyze", "--study", str(STUDY)]
            if run_child(command, "analyzing"):
                raise RuntimeError("Frozen repeat analysis failed")
            if run_child([sys.executable, str(AUDIT), "--study", str(STUDY)], "verifying"):
                raise RuntimeError("Independent repeat endpoint/utility verification failed")
            report = verified(STUDY / "report.json")
            scale = report["statistics"]["scale_acquisition"]
            write("complete" if scale else "complete_with_gate_failures", progress=status(STUDY),
                  signal_gates=report["statistics"]["gates"], scale_acquisition=scale,
                  report=str(STUDY / "report.json"), verification=str(STUDY / "background-verification.json"))
            print("Repeat panel completed, analyzed and independently verified; no later study launched.", flush=True)
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
            print(f"Repeat supervisor stopped: {type(exc).__name__}: {exc}", flush=True)
            return 1


def launch():
    os.chdir(REPO)
    with run_lock(STUDY / "background-launch"):
        protocol = checked_protocol()
        if not supervisor_idle():
            print(f"Repeat supervisor already running; {STATE}")
            return
        if STATE.exists():
            prior = read_json(STATE)
            if prior["state"] in {"complete", "complete_with_gate_failures"}:
                print(f"Repeat study already finished; {STATE}")
                return
            try:
                os.kill(prior["pid"], 0)
            except ProcessLookupError:
                pass
            else:
                print(f"Repeat supervisor already starting/running: PID {prior['pid']}; {STATE}")
                return
        if not collection_idle(protocol):
            print("Existing collector detected; supervisor will monitor its locks.")
        p = policy_payload()
        if POLICY.exists():
            if verified(POLICY) != p:
                raise ValueError("Operational policy changed; inspect existing worker identity")
        else:
            atomic_json(POLICY, envelope(p))
            atomic_json(JOURNAL, envelope({"policy_sha256": digest(p), "collector_invocations_reserved": 0}))
        launch_id = uuid.uuid4().hex
        with LOG.open("a") as log:
            process = subprocess.Popen(
                ["/usr/bin/caffeinate", "-i", sys.executable, str(Path(__file__).resolve()),
                 "--worker", "--launch-id", launch_id],
                cwd=REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, env=environment(),
            )
        atomic_json(STATE, {"state": "launched", "pid": process.pid, "launch_id": launch_id,
                          "updated_at_utc": now(), "protocol_sha256": PIN, "cloud_spend_usd": 0})
        print(f"Detached repeat supervisor launched: PID {process.pid}; {LOG}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--launch-id", help=argparse.SUPPRESS)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(read_json(STATE), indent=2))
    elif args.worker:
        sys.exit(worker(args.launch_id))
    else:
        launch()


if __name__ == "__main__":
    main()
