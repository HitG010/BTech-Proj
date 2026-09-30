"""Detached supervisor for the frozen Phase 1 bridge; never launches later studies."""

import argparse
import fcntl
import os
import signal
import subprocess
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from reasoning_budget.confirmation import file_hash  # noqa: E402
from reasoning_budget.research_bridge import read_protocol, status  # noqa: E402
from reasoning_budget.storage import atomic_json, read_json, run_lock, verified  # noqa: E402

STUDY = REPO / "artifacts/research/data-efficiency-v1/bridge-v1"
CHECKPOINT = STUDY.parent / "phase-1-step-3"
STATE = STUDY / "background-status.json"
LOG = STUDY / "background-worker.log"
AUDIT = REPO / "scripts/verify_phase1_bridge.py"


def now():
    return datetime.now(timezone.utc).isoformat()


def collection_idle(protocol):
    """Wait for both the orchestrator and any orphaned arm worker to release locks."""
    directories = [STUDY] + [Path(a["snapshot"]["run_dir"]) for a in protocol["arms"].values()]
    with ExitStack() as stack:
        for directory in directories:
            if not directory.exists():
                continue
            stream = stack.enter_context((directory / ".lock").open("a+"))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
    return True


def collect_command(command):
    env = dict(os.environ, HF_HUB_OFFLINE="1", PYTHONUNBUFFERED="1")
    return subprocess.run(
        [sys.executable, "-m", "reasoning_budget.research_bridge", command, str(STUDY)],
        cwd=REPO, env=env, check=False,
    ).returncode


def worker():
    os.chdir(REPO)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    with run_lock(STUDY / "background-supervisor"):
        protocol = read_protocol(STUDY)
        audit_hash = file_hash(AUDIT)
        started = now()
        deadline = time.monotonic() + 9 * 3600
        resumed = False

        def write(state, **details):
            value = {
                "state": state, "pid": os.getpid(), "started_at_utc": started,
                "updated_at_utc": now(), "supervisor_sha256": file_hash(__file__),
                "audit_sha256": audit_hash, "automatic_resume_used": resumed,
                "poll_seconds": 60, "later_studies_launched": False,
                "cloud_spend_usd": 0, **details,
            }
            atomic_json(STATE, value)

        try:
            while time.monotonic() < deadline:
                progress = status(STUDY)
                complete = all(v["completed"] == v["expected"] for v in progress["arms"].values())
                idle = collection_idle(protocol)
                write("collecting" if not complete else "awaiting_collector_exit", progress=progress)
                if idle and complete:
                    break
                if idle:
                    # At most one automatic resume; existing token/time ledgers and
                    # fixed endpoints stay authoritative. Completed cells are reused.
                    if resumed:
                        write("needs_attention", reason="Incomplete after one bounded automatic resume", progress=progress)
                        return 1
                    resumed = True
                    write("resuming", progress=progress)
                    if collect_command("run"):
                        write("needs_attention", reason="Collector exited with an error; inspect arm logs", progress=status(STUDY))
                        return 1
                    continue
                time.sleep(60)
            else:
                write("needs_attention", reason="Supervisor reached its nine-hour monitoring limit", progress=status(STUDY))
                return 1

            # All 200 complete and no active collection: only now allow analysis.
            if not (STUDY / "report.json").exists() and collect_command("report"):
                write("needs_attention", reason="Frozen report generation failed")
                return 1
            if file_hash(AUDIT) != audit_hash:
                raise ValueError("Independent audit script changed during collection")
            write("verifying", progress=status(STUDY))
            verification = subprocess.run([sys.executable, str(AUDIT)], cwd=REPO, check=False)
            if verification.returncode:
                write("verification_failed", reason="Independent audit failed; inspect background-worker.log")
                return 1
            report = verified(STUDY / "report.json")
            write(
                "complete" if report["engineering_gate_passed"] else "complete_with_gate_failures",
                progress=status(STUDY), engineering_gates=report["engineering_gates"],
                report=str(STUDY / "report.md"), verification=str(CHECKPOINT / "verification.json"),
            )
            print("Bridge finished; report and independent verification recorded.", flush=True)
            return 0
        except Exception as exc:
            write("needs_attention", reason=f"{type(exc).__name__}: {exc}")
            raise


def launch():
    read_protocol(STUDY)  # Fail before detaching if any frozen input changed.
    if STATE.exists():
        previous = read_json(STATE)
        try:
            os.kill(previous["pid"], 0)
        except ProcessLookupError:
            pass
        else:
            print(f"Supervisor already running: PID {previous['pid']}; {STATE}")
            return
    with LOG.open("a") as log:
        process = subprocess.Popen(
            ["/usr/bin/caffeinate", "-i", sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, env=dict(os.environ, HF_HUB_OFFLINE="1", PYTHONUNBUFFERED="1"),
        )
    print(f"Detached supervisor launched: PID {process.pid}; log {LOG}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        import json
        print(json.dumps(read_json(STATE), indent=2))
    elif args.worker:
        sys.exit(worker())
    else:
        launch()


if __name__ == "__main__":
    main()
