"""Independent synthetic audit of the two-solver collection boundary.

These fixtures never load a model, open a reference, or touch the real study.
"""

import time
from types import SimpleNamespace

import pytest

from reasoning_budget.storage import atomic_json, digest, envelope, verified
from scripts import opportunity_panel_collect as collect
from tests.test_opportunity_panel_collect import FixtureEngine, fixture_study


def _complete_one_arm(protocol, solver):
    invocation = collect.reserve_invocation(protocol, solver)
    engine = FixtureEngine(None, protocol["arms"][solver]["backend_metadata"])
    collect.collect_core(protocol, solver, invocation, factory=lambda _: engine)
    return invocation, engine


def test_one_complete_solver_keeps_references_and_scores_locked(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    first, second = collect.SOLVERS
    _complete_one_arm(protocol, first)
    assert collect.collection_status(protocol)["by_solver"] == {first: 2, second: 0}
    monkeypatch.setattr(collect, "read_protocol", lambda: protocol)
    monkeypatch.setattr(collect, "selected_gold", lambda _: pytest.fail("reference opened"))
    with pytest.raises(collect.IntegrityError, match="endpoint"):
        collect.finalize()
    assert not (tmp_path / "score-started.json").exists()
    assert not (tmp_path / "scores.numeric-v7.json").exists()


def test_unsettled_retry_charges_full_reservation_across_solvers(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    first, second = collect.SOLVERS
    i1 = collect.reserve_invocation(protocol, first)
    s1 = collect.reserve(protocol, first, i1, "setup")
    collect.settle(s1, "loaded", time.monotonic(), tokens=0)
    attempt = collect.reserve(protocol, first, i1, "job",
        job=collect.GenerationJob(**protocol["arms"][first]["jobs"][0]), session_id=s1["id"])
    before = collect.usage(protocol)
    assert before["charged_tokens"] == attempt["reserved_tokens"] == 512
    assert before["unresolved"] == 1
    i2 = collect.reserve_invocation(protocol, second)
    s2 = collect.reserve(protocol, second, i2, "setup")
    collect.settle(s2, "loaded", time.monotonic(), tokens=0)
    second_attempt = collect.reserve(protocol, second, i2, "job",
        job=collect.GenerationJob(**protocol["arms"][second]["jobs"][0]), session_id=s2["id"])
    assert collect.usage(protocol)["charged_tokens"] == attempt["reserved_tokens"] + second_attempt["reserved_tokens"]
    assert collect.usage(protocol)["attempts"] == 2


def test_failed_job_stops_one_invocation_and_third_attempt_is_forbidden(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    failed = FixtureEngine(None, protocol["arms"][solver]["backend_metadata"], timeout=True)
    first = collect.reserve_invocation(protocol, solver)
    with pytest.raises(RuntimeError, match="deadline"):
        collect.collect_core(protocol, solver, first, factory=lambda _: failed)
    assert len(failed.seen) == 1
    second = collect.reserve_invocation(protocol, solver)
    with pytest.raises(RuntimeError, match="deadline"):
        collect.collect_core(protocol, solver, second, factory=lambda _: failed)
    assert len(failed.seen) == 2
    assert collect.usage(protocol)["attempts"] == 2
    with pytest.raises(collect.BudgetExhausted, match="ceiling"):
        collect.reserve_invocation(protocol, solver)


def test_setup_reservation_count_is_global_across_both_solvers(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    invocations = []
    for solver in collect.SOLVERS:
        for _ in range(2):
            invocation = collect.reserve_invocation(protocol, solver)
            invocations.append((solver, invocation))
            collect.reserve(protocol, solver, invocation, "setup")
    assert collect.usage(protocol)["setup_reservations"] == 4
    with pytest.raises(collect.BudgetExhausted, match="budget"):
        collect.reserve(protocol, *invocations[0], "setup")


def test_settled_charge_must_match_immutable_attempt_record(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    first = collect.SOLVERS[0]
    _complete_one_arm(protocol, first)
    row = collect.completed_records(protocol)[first][0]
    settlement = tmp_path / "ledger/settlements" / f"{row['attempt_id']}.json"
    receipt = verified(settlement)
    receipt["charged_tokens"] = 0  # The completed result actually emitted tokens.
    atomic_json(settlement, envelope(receipt))
    with pytest.raises(collect.IntegrityError):
        collect.collection_status(protocol)


def test_attempt_record_and_result_links_must_agree(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    first = collect.SOLVERS[0]
    _complete_one_arm(protocol, first)
    row = collect.completed_records(protocol)[first][0]
    path = tmp_path / "attempt-records" / f"{row['attempt_id']}.json"
    tampered = verified(path)
    tampered["session_id"] = "wrong-session"
    atomic_json(path, envelope(tampered))
    with pytest.raises(collect.IntegrityError):
        collect.collection_status(protocol)


def test_setup_overrun_stops_before_jobs_and_charges_actual_clock(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    invocation = collect.reserve_invocation(protocol, solver)
    clock = iter((0., collect.SPEC["setup_seconds"] + 1., collect.SPEC["setup_seconds"] + 1.))
    monkeypatch.setattr(collect.time, "monotonic", lambda: next(clock))
    engine = FixtureEngine(None, protocol["arms"][solver]["backend_metadata"])
    with pytest.raises(collect.BudgetExhausted, match="setup"):
        collect.collect_core(protocol, solver, invocation, factory=lambda _: engine)
    tally = collect.usage(protocol)
    assert tally["setup_reservations"] == 1 and tally["attempts"] == 0
    assert tally["charged_seconds"] >= collect.SPEC["setup_seconds"] + 1
    assert engine.seen == []


def test_collection_start_identity_and_time_are_frozen(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    collect.write_once(tmp_path / "collection-start.json", {
        "started_at": protocol["prepared_at"] - 1, "protocol_sha256": "wrong"})
    with pytest.raises(collect.IntegrityError):
        collect.usage(protocol)


def test_collection_end_prevents_later_reservations(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    invocation = collect.reserve_invocation(protocol, solver)
    collect.write_once(tmp_path / "collection-end.json", {
        "finished_at": time.time(), "protocol_sha256": digest(protocol)})
    with pytest.raises((collect.IntegrityError, collect.BudgetExhausted)):
        collect.reserve(protocol, solver, invocation, "setup")


def test_launcher_releases_locks_then_posts_handshake(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    monkeypatch.setattr(collect, "read_protocol", lambda: protocol)
    monkeypatch.setattr(collect.child_plan, "verify", lambda *args: {})
    monkeypatch.setattr(collect.os, "chdir", lambda _: None)
    launches = []
    def fake_popen(command, **kwargs):
        launches.append((command, kwargs))
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(collect.subprocess, "Popen", fake_popen)
    result = collect.launch()
    launch = verified(tmp_path / "supervisor-launches" / f"{result['launch_id']}.json")
    ready = verified(tmp_path / "launch-ready" / f"{result['launch_id']}.json")
    assert launch["id"] == ready["launch_id"] == result["launch_id"]
    assert launches[0][0][:2] == ["/usr/bin/caffeinate", "-i"]
    assert launches[0][1]["start_new_session"] is True


def test_supervisor_handshake_timeout_precedes_model_or_status_access(tmp_path, monkeypatch):
    fixture_study(tmp_path, monkeypatch)
    monkeypatch.setattr(collect.os, "chdir", lambda _: None)
    monkeypatch.setattr(collect.signal, "signal", lambda *args: None)
    monkeypatch.setattr(collect.time, "monotonic", iter((0., 31.)).__next__)
    monkeypatch.setattr(collect.time, "sleep", lambda _: None)
    monkeypatch.setattr(collect, "read_protocol", lambda: pytest.fail("protocol entered before handshake"))
    with pytest.raises(TimeoutError, match="handshake"):
        collect.supervisor("missing-ready")
    assert not (tmp_path / "supervisor-starts").exists()


def test_reserved_missing_ready_handshake_has_recoverable_terminal(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    launch_id = "reserved-without-ready"
    collect.write_once(tmp_path / "supervisor-launches" / f"{launch_id}.json", {
        "id": launch_id, "protocol_sha256": digest(protocol), "reserved_at": time.time(),
        "resume": False})
    atomic_json(tmp_path / "background-status.json", {"state": "launched", "launch_id": launch_id})
    monkeypatch.setattr(collect.os, "chdir", lambda _: None)
    monkeypatch.setattr(collect.signal, "signal", lambda *args: None)
    monkeypatch.setattr(collect.time, "monotonic", iter((0., 31.)).__next__)
    monkeypatch.setattr(collect.time, "sleep", lambda _: None)
    monkeypatch.setattr(collect, "read_protocol", lambda: pytest.fail("protocol entered before handshake"))
    with pytest.raises(TimeoutError, match="handshake"):
        collect.supervisor(launch_id)
    terminal = verified(tmp_path / "supervisor-finishes" / f"{launch_id}.json")
    background = collect.read_json(tmp_path / "background-status.json")
    assert terminal["state"] == background["state"] == "needs_attention"
    assert terminal["failure_kind"] == background["failure_kind"] == "runtime"
    assert terminal["protocol_sha256"] == digest(protocol)
    assert not (tmp_path / "supervisor-starts").exists()


def test_launcher_popen_failure_preserves_runtime_terminal(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    monkeypatch.setattr(collect, "read_protocol", lambda: protocol)
    monkeypatch.setattr(collect.child_plan, "verify", lambda *args: {})
    monkeypatch.setattr(collect.os, "chdir", lambda _: None)
    def fail_popen(*args, **kwargs):
        raise OSError("synthetic launch failure")
    monkeypatch.setattr(collect.subprocess, "Popen", fail_popen)
    with pytest.raises(OSError, match="synthetic launch failure"):
        collect.launch()
    launches = list((tmp_path / "supervisor-launches").glob("*.json"))
    assert len(launches) == 1
    launch_id = launches[0].stem
    terminal = verified(tmp_path / "supervisor-finishes" / f"{launch_id}.json")
    background = collect.read_json(tmp_path / "background-status.json")
    assert terminal["state"] == background["state"] == "needs_attention"
    assert terminal["failure_kind"] == background["failure_kind"] == "runtime"
    assert not (tmp_path / "launch-ready" / f"{launch_id}.json").exists()


def test_budget_recheck_after_close_precedes_any_reference_access(tmp_path, monkeypatch):
    protocol = fixture_study(tmp_path, monkeypatch)
    monkeypatch.setattr(collect, "read_protocol", lambda: protocol)
    monkeypatch.setattr(collect, "completed_records", lambda _: {solver: [] for solver in collect.SOLVERS})
    monkeypatch.setattr(collect, "invocation_records", lambda _: [])
    monkeypatch.setattr(collect, "selected_gold", lambda _: pytest.fail("reference opened"))
    calls = iter(({"completed": 512, "charged_tokens": 0, "budget_seconds": 0},
                  {"completed": 512, "charged_tokens": 0,
                   "budget_seconds": collect.SPEC["global_seconds"] + 1}))
    monkeypatch.setattr(collect, "collection_status", lambda _: next(calls))
    with pytest.raises(collect.IntegrityError, match="after collection close"):
        collect.finalize()
    assert (tmp_path / "collection-end.json").exists()
    assert not (tmp_path / "score-started.json").exists()
