import copy
import time

import pytest

from reasoning_budget.config import from_dict
from reasoning_budget.records import GenerationResult, Question
from reasoning_budget.runner import build_jobs
from reasoning_budget.storage import digest, verified
from scripts import opportunity_panel_collect as collect


def fixture_study(tmp_path, monkeypatch, *, tokens=1000000):
    monkeypatch.setattr(collect, "STUDY", tmp_path)
    monkeypatch.setattr(collect, "SPEC", collect.SPEC | {"responses": 4, "global_tokens": tokens})
    question = Question("fixture-q", "fixture:synthetic", "synthetic", "Return zero")
    arms = {}
    for i, solver in enumerate(collect.SOLVERS):
        config = from_dict({"name": solver, "backend": "fake", "seed": 10 + i,
            "data_dir": "unused", "output_dir": "unused", "answer_tokens": 512, "reasoning_tokens": 2048})
        meta = {"closure_tokens": 2, "closure_ids": [151668, 271], "eos_token_ids": [151643, 151645]}
        arms[solver] = {"config": config.to_dict(), "backend_metadata": meta,
            "asset_file_sha256": {}, "jobs": [j.to_dict() for j in build_jobs(config, [question], meta)]}
    p = {"prepared_at": time.time() - 10, "arms": arms,
        "selected": [{"child_question": question.to_dict()}], "generation_implementation_sha256": "a" * 64}
    return p


def job_for(p, solver, index=0):
    return collect.GenerationJob(**p["arms"][solver]["jobs"][index])


def result_for(job, *, termination="eos"):
    reason = [7, 8] if job.mode == "thinking" else []
    answer = [22, 151645]
    return GenerationResult("0", "fixture", "0", 10, len(reason), len(answer), 0,
        .001, 0., .001, 0., False, False, termination, -.1,
        {"reasoning_token_ids": reason, "answer_token_ids": answer, "inserted_token_ids": []}, -.2)


def test_exclusive_atomic_results_never_overwrite(tmp_path):
    path = tmp_path / "immutable.json"
    collect.write_once(path, {"first": True})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        collect.write_once(path, {"first": False})
    assert path.read_bytes() == original


def test_global_budget_counts_both_arms_and_unresolved_reservations(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch, tokens=1000)
    a, b = collect.SOLVERS
    ia, ib = collect.reserve_invocation(p, a), collect.reserve_invocation(p, b)
    sa = collect.reserve(p, a, ia, "setup")
    collect.settle(sa, "loaded", time.monotonic(), tokens=0)
    first = collect.reserve(p, a, ia, "job", job=job_for(p, a), session_id=sa["id"])
    sb = collect.reserve(p, b, ib, "setup")
    collect.settle(sb, "loaded", time.monotonic(), tokens=0)
    with pytest.raises(collect.BudgetExhausted):
        collect.reserve(p, b, ib, "job", job=job_for(p, b), session_id=sb["id"])
    tally = collect.usage(p)
    assert tally["charged_tokens"] == 512 and tally["charged_seconds"] >= 600
    job = job_for(p, a)
    record = {"protocol_sha256": digest(p), "solver": a, "job": job.to_dict(),
        "attempt_id": first["id"], "session_id": sa["id"], "status": "failed",
        "implementation_sha256": p["generation_implementation_sha256"],
        "result": result_for(job, termination="timeout").to_dict()}
    collect.write_once(tmp_path / "attempt-records" / f"{first['id']}.json", record)
    collect.settle(first, "failed", time.monotonic(), tokens=2, record=record)
    collect.reserve(p, b, ib, "job", job=job_for(p, b), session_id=sb["id"])
    assert collect.usage(p)["charged_tokens"] == 514


@pytest.mark.parametrize("tokens,seconds", [(True, 1), (-1, 1), (0, float("nan")), (0, -1)])
def test_ledger_rejects_invalid_settlements(tmp_path, monkeypatch, tokens, seconds):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    inv = collect.reserve_invocation(p, solver)
    r = collect.reserve(p, solver, inv, "setup")
    # Write raw JSON for a nonfinite corrupt fixture; normal durable writer rejects it.
    import json
    path = tmp_path / "ledger/settlements" / f"{r['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"id": r["id"], "reservation_sha256": digest(r), "status": "loaded",
        "charged_tokens": tokens, "elapsed_seconds": seconds, "finished_at": time.time()}
    if not collect.finite_number(seconds):
        path.write_text(json.dumps({"checksum": "invalid", "payload": receipt}))
    else:
        collect.write_once(path, receipt)
    with pytest.raises(ValueError):
        collect.usage(p)


def test_wall_age_counts_gaps_and_freezes_at_collection_end(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    start = p["prepared_at"] + 1
    collect.write_once(tmp_path / "collection-start.json", {"started_at": start, "protocol_sha256": digest(p)})
    assert collect.usage(p, now=start+100)["budget_seconds"] == 100
    collect.write_once(tmp_path / "collection-end.json", {"finished_at": start+50, "protocol_sha256": digest(p)})
    assert collect.usage(p, now=start+10000)["budget_seconds"] == 50


def test_independent_solver_seeds_are_not_reused(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    seeds = [j["seed"] for arm in p["arms"].values() for j in arm["jobs"]]
    assert len(seeds) == len(set(seeds)) == 4
    assert collect.SEEDS[collect.SOLVERS[0]] != collect.SEEDS[collect.SOLVERS[1]]


def test_invocation_ceiling_and_completed_worker_restart(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    collect.reserve_invocation(p, solver)
    collect.reserve_invocation(p, solver)
    with pytest.raises(collect.BudgetExhausted):
        collect.reserve_invocation(p, solver)


@pytest.mark.parametrize("field,value", [("answer_tokens", 3), ("forced_closure", True),
    ("mean_generated_logprob_raw", None), ("termination", "unknown"), ("answer_seconds", -1.)])
def test_result_validator_rejects_accounting_and_confidence_errors(tmp_path, monkeypatch, field, value):
    p = fixture_study(tmp_path, monkeypatch)
    job = job_for(p, collect.SOLVERS[0])
    result = result_for(job)
    setattr(result, field, value)
    with pytest.raises(collect.IntegrityError):
        collect.validate_result(result, job)


def test_incomplete_model_output_is_not_a_quality_retry(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    job = job_for(p, collect.SOLVERS[0], 1)
    result = result_for(job, termination="reasoning_in_answer")
    result.final_answer = ""
    assert collect.validate_result(result, job) == 4
    result.termination = "early_eos"
    result.metadata["reasoning_token_ids"][-1] = 151645
    result.metadata["answer_token_ids"] = []
    result.answer_tokens = 0
    assert collect.validate_result(result, job) == 2


class FixtureEngine:
    def __init__(self, config, metadata, *, timeout=False):
        self.metadata = metadata
        self.timeout = timeout
        self.seen = []

    def load(self):
        pass

    def generate(self, question, job, deadline):
        self.seen.append(job.to_dict())
        return result_for(job, termination="timeout" if self.timeout else "eos")


def test_collect_core_writes_results_before_settlements_and_preserves_them(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    inv = collect.reserve_invocation(p, solver)
    engine = FixtureEngine(None, p["arms"][solver]["backend_metadata"])
    state = collect.collect_core(p, solver, inv, factory=lambda config: engine)
    assert state["completed"] == 2 and state["analysis"] == "locked"
    assert len(engine.seen) == 2
    results = collect.completed_records(p)[solver]
    for row in results:
        receipt = verified(tmp_path / "ledger/settlements" / f"{row['attempt_id']}.json")
        assert receipt["record_sha256"] == digest(row)
    frozen = {path: path.read_bytes() for path in (tmp_path / "results").rglob("*.json")}
    with pytest.raises(FileExistsError):
        collect.collect_core(p, solver, inv, factory=lambda config: engine)
    assert all(path.read_bytes() == data for path, data in frozen.items())


def test_first_timeout_stops_then_bounded_resume_uses_same_frozen_job(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    inv = collect.reserve_invocation(p, solver)
    failed = FixtureEngine(None, p["arms"][solver]["backend_metadata"], timeout=True)
    with pytest.raises(RuntimeError, match="deadline"):
        collect.collect_core(p, solver, inv, factory=lambda config: failed)
    assert len(failed.seen) == 1 and collect.completed_records(p)[solver] == []
    failures = {path: path.read_bytes() for path in (tmp_path / "attempt-records").glob("*.json")}
    resumed = FixtureEngine(None, p["arms"][solver]["backend_metadata"])
    inv2 = collect.reserve_invocation(p, solver)
    collect.collect_core(p, solver, inv2, factory=lambda config: resumed)
    assert failed.seen[0] == resumed.seen[0]
    assert all(path.read_bytes() == data for path, data in failures.items())
    assert collect.usage(p)["attempts"] == 3


def test_result_without_final_receipt_keeps_full_conservative_charge(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    inv = collect.reserve_invocation(p, solver)
    engine = FixtureEngine(None, p["arms"][solver]["backend_metadata"])
    collect.collect_core(p, solver, inv, factory=lambda config: engine)
    rows = collect.completed_records(p)[solver]
    receipt = tmp_path / "ledger/settlements" / f"{rows[0]['attempt_id']}.json"
    receipt.unlink()  # Synthetic crash between durable result and reconciliation.
    assert len(collect.completed_records(p)[solver]) == 2
    assert collect.usage(p)["charged_tokens"] == 516
    assert collect.usage(p)["unresolved"] == 1


def test_unknown_result_and_changed_job_fail_closed(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    solver = collect.SOLVERS[0]
    inv = collect.reserve_invocation(p, solver)
    engine = FixtureEngine(None, p["arms"][solver]["backend_metadata"])
    collect.collect_core(p, solver, inv, factory=lambda config: engine)
    changed = copy.deepcopy(p)
    changed["arms"][solver]["jobs"][0]["seed"] += 1
    with pytest.raises(collect.IntegrityError):
        collect.completed_records(changed)
    collect.write_once(tmp_path / "results/unknown.json", {})
    with pytest.raises(collect.IntegrityError):
        collect.completed_records(p)


def test_finalize_never_opens_gold_before_full_endpoint(tmp_path, monkeypatch):
    p = fixture_study(tmp_path, monkeypatch)
    monkeypatch.setattr(collect, "read_protocol", lambda: p)
    monkeypatch.setattr(collect, "selected_gold", lambda selected: pytest.fail("gold opened"))
    with pytest.raises(collect.IntegrityError, match="endpoint"):
        collect.finalize()


def test_native_environment_disables_network_and_cpu_fallback():
    env = collect.native_environment()
    assert env["HF_HUB_OFFLINE"] == env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["PYTORCH_ENABLE_MPS_FALLBACK"] == "0"
