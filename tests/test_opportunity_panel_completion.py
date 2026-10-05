"""Synthetic, gold-free checks for the separate 60-job completion child."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from reasoning_budget.storage import digest
from scripts import opportunity_panel_completion as completion


def example_plan(*, original_tokens=342047):
    return {"prepared_at": 90., "parent_protocol_sha256": "parent",
        "generation_implementation_sha256": "generator", "original_charged_tokens": original_tokens,
        "jobs": [{"id": "job", "max_tokens": 512}]}


def setup_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(completion, "CHILD", tmp_path)
    plan = example_plan()
    pin = digest(plan)
    completion.orig.write_once(tmp_path / "collection-start.json", {"started_at": 95., "plan_sha256": pin})
    completion.orig.write_once(tmp_path / "invocation.json", {"invocation_id": "inv", "plan_sha256": pin})
    setup = {"id": "setup", "completion_plan_sha256": pin, "parent_protocol_sha256": "parent",
        "invocation_id": "inv", "kind": "setup", "started_at": 100.,
        "reserved_tokens": 0, "reserved_seconds": 900.}
    completion.orig.write_once(tmp_path / "ledger/reservations/setup.json", setup)
    completion.orig.write_once(tmp_path / "ledger/settlements/setup.json", {"id": "setup",
        "reservation_sha256": digest(setup), "status": "loaded", "charged_tokens": 0,
        "elapsed_seconds": 4., "finished_at": 105.})
    job = {"id": "attempt", "completion_plan_sha256": pin, "parent_protocol_sha256": "parent",
        "invocation_id": "inv", "kind": "job", "started_at": 106.,
        "reserved_tokens": 512, "reserved_seconds": 600., "job_id": "job", "session_id": "setup"}
    completion.orig.write_once(tmp_path / "ledger/reservations/attempt.json", job)
    return plan, setup, job


def test_exact_pending_uses_original_job_identities():
    old_large = [{"job": {"id": f"large-{n}"}} for n in range(256)]
    old_small = [{"job": {"id": f"small-{n}"}} for n in range(196)]
    jobs = [{"id": f"small-{n}", "max_tokens": 512} for n in range(256)]
    protocol = {"arms": {completion.SOLVER: {"jobs": jobs}}}
    pending = completion.pending_jobs(protocol, {completion.orig.SOLVERS[0]: old_large,
        completion.SOLVER: old_small})
    assert pending == jobs[196:] and len(pending) == 60
    with pytest.raises(completion.orig.IntegrityError, match="exactly 60"):
        completion.pending_jobs(protocol, {completion.orig.SOLVERS[0]: old_large,
            completion.SOLVER: old_small[:-1]})


def test_setup_settlement_snapshot_race_reads_live_receipt(tmp_path, monkeypatch):
    plan, _, _ = setup_ledger(tmp_path, monkeypatch)
    actual_all = completion._all
    monkeypatch.setattr(completion, "_all", lambda directory:
        {} if directory == "ledger/settlements" else actual_all(directory))
    tally = completion.usage(plan, now=110.)
    assert tally["charged_tokens"] == 512
    assert tally["charged_seconds"] == 1500.  # Conservative missing setup snapshot.
    assert tally["unresolved"] == 2
    monkeypatch.setattr(completion, "_all", actual_all)
    tally = completion.usage(plan, now=110.)
    assert tally["charged_seconds"] == 604. and tally["unresolved"] == 1


def test_duplicate_job_and_bad_charge_fail_closed(tmp_path, monkeypatch):
    plan, _, job = setup_ledger(tmp_path, monkeypatch)
    duplicate = dict(job, id="second", started_at=107.)
    completion.orig.write_once(tmp_path / "ledger/reservations/second.json", duplicate)
    with pytest.raises(completion.orig.IntegrityError, match="twice"):
        completion.usage(plan, now=110.)
    (tmp_path / "ledger/reservations/second.json").unlink()
    record = {"job": plan["jobs"][0], "attempt_id": "attempt", "session_id": "setup",
        "status": "completed", "solver": completion.SOLVER,
        "parent_protocol_sha256": "parent", "completion_plan_sha256": digest(plan),
        "implementation_sha256": "generator", "result": {"termination": "eos"}}
    completion.orig.write_once(tmp_path / "attempt-records/attempt.json", record)
    completion.orig.write_once(tmp_path / "ledger/settlements/attempt.json", {
        "id": "attempt", "reservation_sha256": digest(job), "status": "completed",
        "charged_tokens": 6, "elapsed_seconds": 2., "finished_at": 108.,
        "record_sha256": digest(record)})
    monkeypatch.setattr(completion, "GenerationResult", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(completion, "GenerationJob", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(completion.orig, "validate_result", lambda *_: 5)
    with pytest.raises(completion.orig.IntegrityError, match="charge differs"):
        completion.usage(plan, now=110.)


def test_inflight_published_result_waits_for_receipt(tmp_path, monkeypatch):
    plan, _, job = setup_ledger(tmp_path, monkeypatch)
    record = {"job": plan["jobs"][0], "attempt_id": "attempt", "session_id": "setup",
        "status": "completed", "solver": completion.SOLVER,
        "parent_protocol_sha256": "parent", "completion_plan_sha256": digest(plan),
        "implementation_sha256": "generator", "result": {"termination": "eos"}}
    completion.orig.write_once(tmp_path / "results/job.json", record)
    monkeypatch.setattr(completion, "GenerationResult", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(completion, "GenerationJob", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(completion.orig, "validate_result", lambda *_: 5)
    assert completion.completed_new(plan) == []
    completion.orig.write_once(tmp_path / "ledger/settlements/attempt.json", {
        "id": "attempt", "reservation_sha256": digest(job), "status": "completed",
        "charged_tokens": 5, "elapsed_seconds": 2., "finished_at": 108.,
        "record_sha256": digest(record)})
    assert completion.completed_new(plan) == [record]


def test_combined_token_and_new_wall_budget_admission(tmp_path, monkeypatch):
    monkeypatch.setattr(completion, "CHILD", tmp_path)
    plan = example_plan(original_tokens=999800)
    job = SimpleNamespace(id="job", max_tokens=512)
    with pytest.raises(completion.orig.BudgetExhausted, match="budget"):
        completion.reserve(plan, "job", "inv", job=job, session_id="setup")
    plan = example_plan()
    completion.orig.write_once(tmp_path / "collection-start.json", {"started_at": 91.,
        "plan_sha256": digest(plan)})
    with pytest.raises(completion.orig.BudgetExhausted, match="budget"):
        completion.reserve(plan, "setup", "inv")


def test_parent_inventory_preserves_old_recovery_and_excludes_new_child(tmp_path, monkeypatch):
    study = tmp_path / "study"
    (study / "recovery-v1").mkdir(parents=True)
    (study / "recovery-v1/status.json").write_text("old failure")
    (study / "completion-v1").mkdir()
    (study / "completion-v1/status.json").write_text("new child")
    monkeypatch.setattr(completion.orig, "STUDY", study)
    monkeypatch.setattr(completion, "CHILD", study / "completion-v1")
    monkeypatch.setattr(completion.orig, "safe_paths", lambda: None)
    inventory = completion.parent_inventory()
    assert set(inventory) == {"recovery-v1/status.json"}
    assert inventory["recovery-v1/status.json"] == completion.file_hash(study / "recovery-v1/status.json")


def test_finalizer_rejects_partial_endpoint_before_gold(tmp_path, monkeypatch):
    study = tmp_path / "study"
    child = study / "completion-v1"
    child.mkdir(parents=True)
    monkeypatch.setattr(completion.orig, "STUDY", study)
    monkeypatch.setattr(completion, "CHILD", child)
    plan = example_plan()
    protocol = {"selected": [], "folds": {}, "analysis": {}}
    monkeypatch.setattr(completion, "read_plan", lambda: (plan, protocol))
    monkeypatch.setattr(completion, "progress", lambda _: {"completed_new": 59,
        "combined_completed": 511, "combined_charged_tokens": 342047, "budget_seconds": 1.})
    monkeypatch.setattr(completion.orig, "selected_gold", lambda _: pytest.fail("opened gold early"))
    monkeypatch.setattr(completion, "run_lock", lambda _: nullcontext())
    monkeypatch.setattr(completion.os, "getppid", lambda: 123)
    completion.orig.write_once(child / "launch.json", {"launch_id": "launch"})
    completion.orig.write_once(child / "supervisor-start.json", {"launch_id": "launch", "pid": 123})
    completion.orig.write_once(child / "finalize-request.json", {"launch_id": "launch",
        "plan_sha256": digest(plan), "completed_new": 60})
    completion.orig.write_once(child / "invocation-finish.json", {"state": "complete"})
    completion.orig.write_once(child / "invocation-process.json", {"exit_code": 0})
    with pytest.raises(completion.orig.IntegrityError, match="endpoint"):
        completion.finalize()
