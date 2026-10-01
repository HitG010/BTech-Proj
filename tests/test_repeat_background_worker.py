import importlib.util
from pathlib import Path

import pytest

from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/repeat_background_worker.py"
    spec = importlib.util.spec_from_file_location("repeat_worker_tests", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


@pytest.fixture
def worker(tmp_path, monkeypatch):
    w = module()
    study = tmp_path / "study"
    study.mkdir()
    monkeypatch.setattr(w, "STUDY", study)
    monkeypatch.setattr(w, "JOURNAL", study / "journal.json")
    monkeypatch.setattr(w, "STATE", study / "background-status.json")
    monkeypatch.setattr(w, "POLICY", study / "policy.json")
    monkeypatch.setattr(w, "checked_protocol", lambda: {"snapshot": {"run_dir": str(study / "run")}})
    return w


def test_idle_probe_detects_study_run_and_supervisor_locks(worker):
    protocol = worker.checked_protocol()
    assert worker.collection_idle(protocol)
    with run_lock(worker.STUDY):
        assert not worker.collection_idle(protocol)
    with run_lock(worker.STUDY / "run"):
        assert not worker.collection_idle(protocol)
    assert worker.collection_idle(protocol)
    with run_lock(worker.STUDY / "background-supervisor"):
        assert not worker.supervisor_idle()
    assert worker.supervisor_idle()


def test_one_resume_is_durable_across_supervisor_restarts(worker):
    policy = {"max_collector_invocations": 2}
    atomic_json(worker.JOURNAL, envelope({"policy_sha256": digest(policy), "collector_invocations_reserved": 0}))
    assert worker.reserve_collection(policy) == 1
    assert worker.reserve_collection(policy) == 2
    assert verified(worker.JOURNAL)["collector_invocations_reserved"] == 2
    with pytest.raises(ValueError, match="one bounded resume"):
        worker.reserve_collection(policy)
    with pytest.raises(ValueError, match="differs from policy"):
        worker.reserve_collection({"max_collector_invocations": 3})


def test_active_supervisor_prevents_launching_another_process(worker, monkeypatch):
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_a, **_k: pytest.fail("Duplicate process spawned"))
    with run_lock(worker.STUDY / "background-supervisor"):
        worker.launch()


def test_completed_study_is_never_restarted(worker, monkeypatch):
    atomic_json(worker.STATE, {"state": "complete_with_gate_failures"})
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *_a, **_k: pytest.fail("Finished study restarted"))
    worker.launch()


def configure_worker(worker, monkeypatch, progress, on_spawn):
    policy = {"max_collector_invocations": 2,
              "supervisor_sha256": "fixture-supervisor", "audit_sha256": "fixture-audit"}
    monkeypatch.setattr(worker, "policy_payload", lambda: policy)
    monkeypatch.setattr(worker, "status", lambda _study: dict(progress))
    atomic_json(worker.POLICY, envelope(policy))
    atomic_json(worker.JOURNAL, envelope({"policy_sha256": digest(policy), "collector_invocations_reserved": 0}))
    atomic_json(worker.STATE, {"launch_id": "test-launch"})

    class FinishedChild:
        returncode = 0

        def __init__(self, command, **_kwargs):
            on_spawn(command)

        def poll(self):
            return self.returncode

    monkeypatch.setattr(worker.subprocess, "Popen", FinishedChild)


def test_zero_exit_at_partial_endpoint_cannot_trigger_analysis(worker, monkeypatch):
    commands = []
    configure_worker(worker, monkeypatch, {"completed": 799, "expected": 800}, commands.append)
    assert worker.worker("test-launch") == 1
    assert len(commands) == 2
    assert all("collect" in command for command in commands)
    assert verified(worker.JOURNAL)["collector_invocations_reserved"] == 2
    assert worker.read_json(worker.STATE)["state"] == "needs_attention"


def test_full_endpoint_triggers_analysis_audit_and_preserves_failed_gates(worker, monkeypatch):
    progress = {"completed": 799, "expected": 800}
    commands = []

    def finished(command):
        commands.append(command)
        if "collect" in command:
            progress["completed"] = 800

    configure_worker(worker, monkeypatch, progress, finished)
    atomic_json(worker.STUDY / "report.json", envelope({"statistics": {
        "scale_acquisition": False, "gates": {"signal": False}}}))
    assert worker.worker("test-launch") == 0
    assert len(commands) == 3
    assert "collect" in commands[0]
    assert "analyze" in commands[1]
    assert str(worker.AUDIT) in commands[2]
    assert verified(worker.JOURNAL)["collector_invocations_reserved"] == 1
    final = worker.read_json(worker.STATE)
    assert final["state"] == "complete_with_gate_failures"
    assert not final["scale_acquisition"]
    assert not final["later_studies_launched"]
