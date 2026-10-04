"""Gold-free synthetic checks for the additive monotonic recovery wrapper."""

from types import SimpleNamespace

import pytest

from reasoning_budget.storage import digest, verified
from scripts import opportunity_panel_recovery as recovery


def test_ac_and_clock_preflight_rejects_sleep_gap():
    def run(command, **_):
        return SimpleNamespace(returncode=0, stdout=("Now drawing from 'AC Power'" if "pmset" in command[0]
            else '"System Capabilities" = 15'))
    assert recovery.launch_preflight(run=run, wall=iter([1., 3.]).__next__,
        monotonic=iter([4., 6.]).__next__, sleep=lambda _: None)["ac_power"]
    with pytest.raises(recovery.orig.IntegrityError, match="clocks"):
        recovery.launch_preflight(run=run, wall=iter([1., 900.]).__next__,
            monotonic=iter([4., 6.]).__next__, sleep=lambda _: None)
    assert not recovery.ac_power("Now drawing from 'Battery Power'")


def test_reservation_anchor_binds_original_and_monotonic_before_call(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "RECOVERY", tmp_path)
    seen = []
    row = {"id": "r", "invocation_id": "i", "reserved_seconds": 600, "kind": "job"}
    def original(*args, **kwargs):
        seen.append((args, kwargs))
        return row
    monkeypatch.setattr(recovery, "_ORIGINAL_RESERVE", original)
    monkeypatch.setattr(recovery.time, "monotonic", lambda: 10.)
    out = recovery.anchored_reserve({}, "solver", "i", "job", session_id="s")
    assert out is row and len(seen) == 1 and seen[0][1]["session_id"] == "s"
    anchor = verified(tmp_path / "anchors/r.json")
    assert anchor["reservation_sha256"] == digest(row)
    assert anchor["monotonic_before_reserve"] == 10.
    monkeypatch.setattr(recovery.time, "monotonic", lambda: 15.)
    assert recovery.operation_elapsed(row, "i", now=lambda: 15.) == 5.
    with pytest.raises(recovery.orig.IntegrityError, match="anchor"):
        recovery.operation_elapsed(row, "i", now=lambda: 15., expected_pid=-1)
    with pytest.raises(recovery.orig.IntegrityError, match="anchor"):
        recovery.operation_elapsed(row | {"reserved_seconds": 599}, "i", now=lambda: 15.)


def test_original_inventory_excludes_only_mutable_status_and_recovery(tmp_path, monkeypatch):
    study = tmp_path / "study"
    study.mkdir()
    (study / "protocol.json").write_text("p")
    (study / "active.json").write_text("a")
    (study / "background-status.json").write_text("b")
    (study / "status.json").write_text("s")
    (study / "clock-diagnosis-v1").mkdir()
    (study / "clock-diagnosis-v1" / "power-log.json").write_text("clock")
    (study / "recovery-v1").mkdir()
    (study / "recovery-v1" / "plan.json").write_text("new")
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery, "RECOVERY", study / "recovery-v1")
    monkeypatch.setattr(recovery.orig, "safe_paths", lambda: None)
    names = recovery._original_inventory()
    assert set(names) == {"protocol.json", "background-status.json",
                          "clock-diagnosis-v1/power-log.json"}


def test_one_shot_boundary_requires_single_failed_original_invocation(monkeypatch, tmp_path):
    study = tmp_path / "study"
    (study / "supervisor-launches").mkdir(parents=True)
    (study / "supervisor-launches" / "old.json").write_text("x")
    (study / "background-status.json").write_text('{"state":"needs_attention","failure_kind":"runtime"}')
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery.orig, "collection_status", lambda p: {
        "completed": 0, "attempts": 1, "unresolved": 1, "setup_reservations": 1,
        "budget_seconds": 1100., "charged_tokens": 512})
    monkeypatch.setattr(recovery.orig, "invocation_records", lambda p: [{"solver": recovery.orig.SOLVERS[0]}])
    assert recovery._preflight_state({})["completed"] == 0
    monkeypatch.setattr(recovery.orig, "invocation_records", lambda p: [{"solver": recovery.orig.SOLVERS[1]}])
    with pytest.raises(recovery.orig.IntegrityError, match="boundary"):
        recovery._preflight_state({})


def test_missing_anchor_and_watchdog_are_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "RECOVERY", tmp_path)
    with pytest.raises(recovery.orig.IntegrityError, match="anchor"):
        recovery.operation_elapsed({"id": "missing", "kind": "setup", "invocation_id": "i"}, "i")
    assert recovery.operation_elapsed({"kind": "idle"}, "i") is None


def test_recovery_policy_keeps_frozen_limits():
    spec = recovery.orig.SPEC
    assert (spec["global_tokens"], spec["global_seconds"], spec["setup_seconds"],
            spec["job_seconds"], spec["maximum_polled_rss_bytes"]) == (
            1000000, 43200, 900, 600, 9 * 1024**3)
    assert spec["invocations_per_solver"] == 2 and spec["maximum_supervisor_launches"] == 3
    assert recovery.EXPECTED_PROTOCOL_SHA256 == "d4e511ad16c1b7330452492a5c9d0a0c1a3dccc10418b0591ea73666fc1e44bc"


def test_read_plan_allows_original_progress_status_mutation(tmp_path, monkeypatch):
    study = tmp_path / "study"
    study.mkdir()
    recovery_dir = study / "recovery-v1"
    recovery_dir.mkdir()
    (study / "collection-start.json").write_text("first")
    (study / "status.json").write_text("before")
    (study / "active.json").write_text("before")
    (study / "background-status.json").write_text("old failure")
    (recovery_dir / "initial-status.json").write_text("before")
    (recovery_dir / "initial-active.json").write_text("before")
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery, "RECOVERY", recovery_dir)
    monkeypatch.setattr(recovery, "_sources", lambda: {"source": "pin"})
    monkeypatch.setattr(recovery.orig, "stable_environment", lambda: {"environment": "pin"})
    monkeypatch.setattr(recovery.orig, "read_protocol", lambda: {"fixed": True})
    monkeypatch.setattr(recovery, "EXPECTED_PROTOCOL_SHA256", digest({"fixed": True}))
    plan = {"version": recovery.POLICY_VERSION, "protocol_sha256": digest({"fixed": True}),
        "source_file_sha256": {"source": "pin"}, "environment": {"environment": "pin"},
        "original_collection_start_sha256": recovery.file_hash(study / "collection-start.json"),
        "original_inventory": {"background-status.json": recovery.file_hash(study / "background-status.json")},
        "initial_mutable_file_sha256": {"status.json": recovery.file_hash(study / "status.json"),
            "active.json": recovery.file_hash(study / "active.json")}}
    recovery.orig.write_once(recovery_dir / "plan.json", plan)
    (study / "status.json").write_text("after first solver")
    (study / "active.json").write_text("idle after first solver")
    assert recovery.read_plan()[0] == plan
    (study / "background-status.json").write_text("tampered")
    with pytest.raises(recovery.orig.IntegrityError, match="Frozen original"):
        recovery.read_plan()


def test_private_supervisor_requires_original_launch_and_one_start(tmp_path, monkeypatch):
    study = tmp_path / "study"
    recovery_dir = study / "recovery-v1"
    recovery_dir.mkdir(parents=True)
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery, "RECOVERY", recovery_dir)
    protocol, plan, launch_id = {"protocol": 1}, {"plan": 1}, "newlaunch"
    original = {"id": launch_id, "protocol_sha256": digest(protocol), "resume": True}
    recovery.orig.write_once(study / "supervisor-launches" / f"{launch_id}.json", original)
    recovery.orig.write_once(recovery_dir / "launch.json", {"launch_id": launch_id,
        "plan_sha256": digest(plan), "original_launch_sha256": digest(original)})
    assert recovery.verify_supervisor_launch(launch_id, plan, protocol)["launch_id"] == launch_id
    recovery.orig.write_once(recovery_dir / "supervisor-start.json", {"started": True})
    with pytest.raises(recovery.orig.IntegrityError, match="already started"):
        recovery.verify_supervisor_launch(launch_id, plan, protocol)


def test_failed_monitor_keeps_sampled_metrics(tmp_path, monkeypatch):
    study = tmp_path / "study"
    study.mkdir()
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery, "_status", lambda *a, **k: None)
    calls = iter([{"budget_seconds": 1., "charged_tokens": 0}, RuntimeError("stop")])
    def usage(_):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value
    monkeypatch.setattr(recovery.orig, "usage", usage)
    monkeypatch.setattr(recovery.subprocess, "run", lambda *a, **k:
        SimpleNamespace(returncode=0, stdout="1024"))
    monkeypatch.setattr(recovery.time, "sleep", lambda _: None)
    child = SimpleNamespace(pid=123, poll=lambda: None)
    telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
    current = recovery.time.monotonic()
    with pytest.raises(RuntimeError, match="stop"):
        recovery._monitor(child, "inv", {}, current, current, telemetry, "launch", "qwen3-1.7b")
    assert telemetry == {"rss_samples": 1, "maximum_polled_rss_bytes": 1024 * 1024}


def test_private_collector_requires_live_supervisor_parent(tmp_path, monkeypatch):
    study = tmp_path / "study"
    recovery_dir = study / "recovery-v1"
    recovery_dir.mkdir(parents=True)
    monkeypatch.setattr(recovery.orig, "STUDY", study)
    monkeypatch.setattr(recovery, "RECOVERY", recovery_dir)
    protocol, plan = {"protocol": 1}, {"plan": 1}
    launch = {"launch_id": "launch"}
    invocation = {"solver": "qwen3-1.7b", "protocol_sha256": digest(protocol)}
    recovery.orig.write_once(study / "invocations" / "inv.json", invocation)
    recovery.orig.write_once(study / "supervisor-starts" / "launch.json", {"pid": 123})
    recovery.orig.write_once(recovery_dir / "supervisor-start.json", {"launch_id": "launch", "pid": 123})
    recovery.orig.write_once(recovery_dir / "invocations" / "inv.json", {
        "invocation_id": "inv", "solver": "qwen3-1.7b", "launch_id": "launch",
        "original_invocation_sha256": digest(invocation), "plan_sha256": digest(plan),
        "supervisor_pid": 123})
    assert recovery.verify_collector_binding("qwen3-1.7b", "inv", launch, plan, protocol,
        parent_pid=lambda: 123)["supervisor_pid"] == 123
    with pytest.raises(recovery.orig.IntegrityError, match="invocation"):
        recovery.verify_collector_binding("qwen3-1.7b", "inv", launch, plan, protocol,
            parent_pid=lambda: 999)
    recovery.orig.write_once(recovery_dir / "supervisor-finish.json", {"state": "complete"})
    with pytest.raises(recovery.orig.IntegrityError, match="invocation"):
        recovery.verify_collector_binding("qwen3-1.7b", "inv", launch, plan, protocol,
            parent_pid=lambda: 123)


@pytest.mark.parametrize("kind,expected", [
    ("budget", recovery.orig.BudgetExhausted),
    ("integrity", recovery.orig.IntegrityError),
    ("runtime", RuntimeError),
])
def test_collector_failure_preserves_original_kind_and_reason(tmp_path, monkeypatch, kind, expected):
    monkeypatch.setattr(recovery.orig, "STUDY", tmp_path)
    recovery.orig.write_once(tmp_path / "invocation-finishes" / "inv.json", {
        "state": "stopped", "failure_kind": kind, "reason": f"original {kind} detail"})
    with pytest.raises(expected, match=f"original {kind} detail"):
        recovery.raise_collector_failure("inv")
