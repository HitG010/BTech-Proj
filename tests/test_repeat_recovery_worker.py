"""Synthetic guard checks for the additive, single-invocation recovery worker."""

import contextlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import repeat_recovery_worker as recovery


def test_prepare_refuses_live_original_supervisor_before_inspecting_run(monkeypatch):
    protocol = {"snapshot": {"jobs": [{}] * 800}}
    monkeypatch.setattr(recovery, "frozen_protocol", lambda: protocol)
    monkeypatch.setattr(recovery, "original_exhausted", lambda: ({}, {}, {}))
    monkeypatch.setattr(recovery, "supervisor_idle", lambda: False)
    monkeypatch.setattr(recovery, "checked_run", lambda *_: pytest.fail("Opened active run"))
    with pytest.raises(ValueError, match="still active"):
        recovery.prepare()


def test_first_failed_progress_stops_after_durable_runner_callback():
    recovery.progress_guard("q1 direct sample=0 completed tokens=42 time=2.0s termination=eos")
    with pytest.raises(RuntimeError, match="first durable failed job"):
        recovery.progress_guard("q1 thinking sample=0 failed tokens=15 time=601.0s termination=timeout")
    with pytest.raises(RuntimeError, match="first durable failed job"):
        recovery.progress_guard("q1 direct sample=1 completed tokens=15 time=601.0s termination=timeout")


def test_one_recovery_reservation_is_durable_and_cannot_repeat(monkeypatch, tmp_path):
    journal = tmp_path / "journal.json"
    monkeypatch.setattr(recovery, "JOURNAL", journal)
    policy = {"one": 1}
    recovery.atomic_json(journal, recovery.envelope({
        "policy_sha256": recovery.digest(policy), "collector_invocations_reserved": 0,
    }))
    recovery.reserve_once(policy)
    assert recovery.verified(journal)["collector_invocations_reserved"] == 1
    with pytest.raises(ValueError, match="already reserved"):
        recovery.reserve_once(policy)


@pytest.mark.parametrize("statuses,expected", [
    (["completed"] * 800, True),
    (["completed"] * 799 + ["failed"], False),
    (["completed"] * 799, False),
])
def test_only_full_completed_endpoint_unlocks_analysis(monkeypatch, statuses, expected):
    monkeypatch.setattr(recovery, "checked_run", lambda *_: ({}, [{"status": s} for s in statuses]))
    assert recovery.checked_endpoint({}) is expected


def test_inventory_freezes_completed_failed_attempts_and_sessions(monkeypatch, tmp_path):
    run = tmp_path / "run"
    for directory, names in (("attempts", ["a"] * 57), ("sessions", ["s"] * 2)):
        folder = run / directory
        folder.mkdir(parents=True)
        for i, _ in enumerate(names):
            (folder / f"{i}.json").write_text(str(i))
    monkeypatch.setattr(recovery, "_fixed_paths", lambda _: [Path(__file__)])
    monkeypatch.setattr(recovery, "_inventory", lambda paths: {str(path): "hash" for path in paths})
    rows = [{"status": "completed", "job": {"id": f"c{i}"}} for i in range(51)]
    rows += [{"status": "failed", "job": {"id": f"f{i}"}} for i in range(3)]
    snapshot = recovery.preservation_inventory({"snapshot": {"run_dir": str(run)}}, rows)
    assert (snapshot["completed"], snapshot["failed_jobs"], snapshot["attempts_count"],
            snapshot["sessions_count"]) == (51, 3, 57, 2)


def test_zero_exit_but_incomplete_endpoint_never_launches_analysis(monkeypatch, tmp_path):
    state = tmp_path / "status.json"
    state.write_text(json.dumps({"launch_id": "synthetic"}))
    journal = tmp_path / "journal.json"
    policy = {"synthetic": True}
    recovery.atomic_json(journal, recovery.envelope({"collector_invocations_reserved": 1}))
    monkeypatch.setattr(recovery, "STATE", state)
    monkeypatch.setattr(recovery, "JOURNAL", journal)
    monkeypatch.setattr(recovery, "run_lock", lambda _: contextlib.nullcontext())
    monkeypatch.setattr(recovery, "checked_recovery", lambda **_: ({}, policy,
                                                                   {"collector_invocations_reserved": 0}, {}))
    monkeypatch.setattr(recovery, "collection_idle", lambda _: True)
    monkeypatch.setattr(recovery, "checked_endpoint", lambda _: False)
    monkeypatch.setattr(recovery, "reserve_once", lambda _: None)
    monkeypatch.setattr(recovery, "status", lambda _: {"completed": 51})
    monkeypatch.setattr(recovery.os, "chdir", lambda _: None)
    monkeypatch.setattr(recovery.signal, "signal", lambda *_: None)
    monkeypatch.setitem(sys.modules, "macos_runtime_guard",
                        SimpleNamespace(runtime_snapshot=lambda: {"synthetic": True}))
    commands = []

    class FinishedChild:
        returncode = 0
        pid = 123

        def poll(self):
            return 0

    monkeypatch.setattr(recovery.subprocess, "Popen", lambda command, **_: commands.append(command)
                        or FinishedChild())
    assert recovery.worker("synthetic") == 1
    assert len(commands) == 1 and "--collector" in commands[0]
    assert recovery.read_json(state)["state"] == "needs_attention"


def test_fixed_inventory_contains_run_identity_files():
    protocol = {"snapshot": {"config": {"data_dir": "/fixture/data"},
                             "run_dir": "/fixture/run"}}
    paths = {path.name for path in recovery._fixed_paths(protocol) if path.parent == Path("/fixture/run")}
    assert paths == {"manifest.json", "environment.json", "questions.json", "resolved_config.json"}


def test_prepare_holds_supervisor_study_run_then_recovery_locks(monkeypatch, tmp_path):
    run = tmp_path / "run"
    protocol = {"snapshot": {"run_dir": str(run)}}
    entered = []

    @contextlib.contextmanager
    def lock(path):
        entered.append(path)
        yield

    monkeypatch.setattr(recovery, "frozen_protocol", lambda: protocol)
    monkeypatch.setattr(recovery, "original_exhausted", lambda: ({}, {}, {}))
    monkeypatch.setattr(recovery, "supervisor_idle", lambda: True)
    monkeypatch.setattr(recovery, "collection_idle", lambda _: True)
    monkeypatch.setattr(recovery, "run_lock", lock)
    monkeypatch.setattr(recovery, "checked_run", lambda *_: ({}, [{"status": "completed"}] * 800))
    with pytest.raises(ValueError, match="already complete"):
        recovery.prepare()
    assert entered == [recovery.STUDY / "background-supervisor", recovery.STUDY,
                       run, recovery.RECOVERY]
