"""Synthetic runtime boundary tests; no model, source reference or real launch."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from reasoning_budget.storage import atomic_json, digest, envelope
from scripts import qwen06_sparse_collect as runtime


def write(path, payload):
    atomic_json(path, envelope(payload))


def tiny_plan():
    direct = {"id": "direct-0", "question_id": "q0", "mode": "direct",
              "sample": 0, "seed": 1, "max_tokens": 512, "identity": {}}
    thinking = {"id": "thinking-0", "question_id": "q0", "mode": "thinking",
                "sample": 0, "seed": 2, "max_tokens": 2562, "identity": {}}
    return {"prepared_at": 900.0, "direct_jobs": [direct], "thinking_jobs": [thinking],
            "question_ids": ["q0"], "threshold": 0.0,
            "question_protocol_sha256": "protocol", "generation_implementation_sha256": "generation",
            "scoring_implementation_sha256": "scorer"}


def ledger(tmp_path, plan, *, job=True):
    sha = digest(plan)
    launch = {"launch_id": "L0", "plan_sha256": sha, "reserved_at": 905.0,
              "explicit_resume": False, "clock_preflight": {}}
    write(tmp_path / "launches/L0.json", launch)
    write(tmp_path / "supervisor-starts/L0.json", {"launch_id": "L0", "pid": 123, "started_at": 910.0})
    write(tmp_path / "invocations/I0.json", {"invocation_id": "I0", "launch_id": "L0",
                                             "plan_sha256": sha, "supervisor_pid": 123})
    write(tmp_path / "invocation-starts/I0.json", {"invocation_id": "I0",
          "pid": 124, "started_at": 915.0})
    write(tmp_path / "collection-start.json", {"plan_sha256": sha,
          "launch_id": "L0", "started_at": 910.0})
    setup = {"id": "S0", "plan_sha256": sha, "invocation_id": "I0", "kind": "setup",
             "started_at": 920.0, "reserved_tokens": 0, "reserved_seconds": 900.0}
    write(tmp_path / "ledger/reservations/S0.json", setup)
    write(tmp_path / "anchors/S0.json", {"id": "S0", "reservation_sha256": digest(setup),
          "invocation_id": "I0", "pid": 124, "monotonic_before_reserve": 100.0})
    write(tmp_path / "ledger/settlements/S0.json", {"id": "S0", "reservation_sha256": digest(setup),
        "status": "loaded", "charged_tokens": 0, "elapsed_seconds": 5.0, "finished_at": 925.0})
    if not job:
        return setup, None
    attempt = {"id": "A0", "plan_sha256": sha, "invocation_id": "I0", "kind": "job",
               "started_at": 930.0, "reserved_tokens": 512, "reserved_seconds": 600.0,
               "job_id": "direct-0", "session_id": "S0"}
    write(tmp_path / "ledger/reservations/A0.json", attempt)
    write(tmp_path / "anchors/A0.json", {"id": "A0", "reservation_sha256": digest(attempt),
          "invocation_id": "I0", "pid": 124, "monotonic_before_reserve": 110.0})
    return setup, attempt


def synthetic_result():
    return {"raw_output": "\\boxed{1}", "reasoning": "", "final_answer": "\\boxed{1}",
            "prompt_tokens": 20, "reasoning_tokens": 0, "answer_tokens": 42,
            "inserted_tokens": 0, "elapsed_seconds": 1.0, "reasoning_seconds": 0.0,
            "answer_seconds": 1.0, "closure_seconds": 0.0, "forced_closure": False,
            "answer_truncated": False, "termination": "eos",
            "mean_generated_logprob": -0.1, "metadata": {}, "mean_generated_logprob_raw": -0.1}


def test_unresolved_attempt_keeps_full_charge_and_inflight_result_not_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    _, attempt = ledger(tmp_path, plan)
    record = {"plan_sha256": digest(plan), "question_protocol_sha256": "protocol",
              "implementation_sha256": "generation", "job": plan["direct_jobs"][0],
              "status": "completed", "result": synthetic_result(),
              "attempt_id": "A0", "session_id": "S0"}
    write(tmp_path / "attempt-records/A0.json", record)
    write(tmp_path / "results/direct-0.json", record)
    with patch.object(runtime.orig, "validate_result", return_value=42):
        assert runtime.completed_rows(plan, "direct") == []  # result precedes receipt
        tally = runtime.usage(plan, now=940.0)
        assert tally["charged_tokens"] == 512 and tally["unresolved"] == 1
        assert tally["charged_seconds"] == 605.0
        write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
              "invocation_id": "I0", "pid": 124, "exit_code": -15,
              "finished_at": 935.0})
        write(tmp_path / "supervisor-finishes/L0.json", {"launch_id": "L0",
              "state": "needs_attention"})
        assert len(runtime.completed_rows(plan, "direct")) == 1
        assert runtime.usage(plan, now=940.0)["charged_tokens"] == 512
        write(tmp_path / "ledger/settlements/A0.json", {"id": "A0",
            "reservation_sha256": digest(attempt), "status": "completed",
            "charged_tokens": 42, "elapsed_seconds": 1.0,
            "finished_at": 931.0, "record_sha256": digest(record)})
        assert len(runtime.completed_rows(plan, "direct")) == 1
        assert runtime.usage(plan, now=940.0)["charged_tokens"] == 42


def test_loaded_setup_snapshot_race_uses_live_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    ledger(tmp_path, plan)
    original_all = runtime._all
    def racing_all(folder):
        # Snapshot settlements just before publication of the loaded setup.
        if folder == "ledger/settlements":
            return {}
        return original_all(folder)
    with patch.object(runtime, "_all", side_effect=racing_all):
        tally = runtime.usage(plan, now=940.0)
    assert tally["charged_tokens"] == 512
    assert tally["unresolved"] == 2  # conservative snapshot, including setup


def test_ledger_and_completed_scan_hash_large_plan_once_per_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    plan["direct_jobs"] = [dict(plan["direct_jobs"][0], id=f"direct-{i}",
                                question_id=f"q{i}", seed=i) for i in range(32)]
    ledger(tmp_path, plan, job=False)
    for i, job in enumerate(plan["direct_jobs"]):
        attempt = {"id": f"A{i}", "plan_sha256": digest(plan),
                   "invocation_id": "I0", "kind": "job", "started_at": 930.0 + i,
                   "reserved_tokens": 512, "reserved_seconds": 600.0,
                   "job_id": job["id"], "session_id": "S0"}
        write(tmp_path / "ledger/reservations" / f"A{i}.json", attempt)
        record = {"plan_sha256": digest(plan), "question_protocol_sha256": "protocol",
                  "implementation_sha256": "generation", "job": job,
                  "status": "completed", "result": synthetic_result(),
                  "attempt_id": f"A{i}", "session_id": "S0"}
        write(tmp_path / "results" / f"{job['id']}.json", record)
        write(tmp_path / "ledger/settlements" / f"A{i}.json", {"id": f"A{i}",
              "reservation_sha256": digest(attempt), "status": "completed",
              "charged_tokens": 42, "elapsed_seconds": 1.0,
              "finished_at": 931.0 + i, "record_sha256": digest(record)})
        write(tmp_path / "attempt-records" / f"A{i}.json", record)
        write(tmp_path / "anchors" / f"A{i}.json", {"id": f"A{i}",
              "reservation_sha256": digest(attempt), "invocation_id": "I0",
              "pid": 124, "monotonic_before_reserve": 100.0 + i})
    original_digest = runtime.digest
    count = 0
    def counted(value):
        nonlocal count
        if value is plan:
            count += 1
        return original_digest(value)
    with (patch.object(runtime, "digest", side_effect=counted),
          patch.object(runtime.orig, "validate_result", return_value=42)):
        assert len(runtime.completed_rows(plan, "direct")) == 32
        assert count == 1
        count = 0
        assert runtime.usage(plan, now=1000.0)["charged_tokens"] == 32 * 42
        assert count <= 3  # Usage plus its bounded launch census.


def test_terminal_unknown_old_attempt_allowed_only_after_failed_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    ledger(tmp_path, plan)
    sha = digest(plan)
    with pytest.raises((FileNotFoundError, ValueError)):
        runtime.terminal_unknowns(plan)
    write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
          "invocation_id": "I0", "pid": 123, "exit_code": -15})
    write(tmp_path / "supervisor-finishes/L0.json", {"launch_id": "L0",
          "state": "needs_attention"})
    write(tmp_path / "launches/L1.json", {"launch_id": "L1", "plan_sha256": sha,
                                         "reserved_at": 950.0, "explicit_resume": True})
    assert runtime.terminal_unknowns(plan) == 1
    (tmp_path / "invocation-processes/L0.json").unlink()
    write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
          "invocation_id": "I0", "pid": 123, "exit_code": 0})
    with pytest.raises(ValueError, match="unresolved operation"):
        runtime.terminal_unknowns(plan)


def test_resume_monitor_ignores_only_exited_prior_active_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    _, attempt = ledger(tmp_path, plan)
    write(tmp_path / "active.json", attempt)
    write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
          "invocation_id": "I0", "pid": 123, "exit_code": -15})
    write(tmp_path / "supervisor-finishes/L0.json", {"launch_id": "L0",
          "state": "needs_attention"})
    process = SimpleNamespace(pid=456, poll=lambda: None)
    with (patch.object(runtime, "status"), patch.object(runtime, "usage", return_value={
              "budget_seconds": 0, "charged_tokens": 0}),
          patch.object(runtime.time, "sleep"),
          patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(
              returncode=0, stdout="100"))):
        with patch.object(process, "poll", side_effect=[None, 0]):
            telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
            runtime.monitor(process, plan, "I1", runtime.time.monotonic(), telemetry)
            assert telemetry["rss_samples"] == 1
        (tmp_path / "invocation-processes/L0.json").unlink()
        write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
              "invocation_id": "I0", "pid": 123, "exit_code": 0})
        with patch.object(process, "poll", side_effect=[None, 0]):
            with pytest.raises(ValueError, match="unknown live collector"):
                runtime.monitor(process, plan, "I1", runtime.time.monotonic(), telemetry)
        write(tmp_path / "active.json", attempt | {"invocation_id": "foreign"})
        with patch.object(process, "poll", side_effect=[None, 0]):
            with pytest.raises(ValueError, match="unknown prior owner"):
                runtime.monitor(process, plan, "I1", runtime.time.monotonic(), telemetry)


def test_finalizer_requires_all_exited_and_successful_latest_collector(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    ledger(tmp_path, plan, job=False)
    write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
          "invocation_id": "I0", "pid": 123, "exit_code": -15})
    write(tmp_path / "supervisor-finishes/L0.json", {"launch_id": "L0",
          "state": "needs_attention"})
    write(tmp_path / "invocations/I1.json", {"invocation_id": "I1", "launch_id": "L1",
         "plan_sha256": digest(plan), "supervisor_pid": 456})
    write(tmp_path / "invocation-finishes/I1.json", {"state": "complete"})
    with pytest.raises(FileNotFoundError):
        runtime.all_collectors_exited(plan, "L1")
    write(tmp_path / "invocation-processes/L1.json", {"launch_id": "L1",
          "invocation_id": "I1", "pid": 456, "exit_code": 0})
    assert runtime.all_collectors_exited(plan, "L1") == 2


def test_prior_collector_spawn_failure_is_observed_without_child(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    write(tmp_path / "invocations/I0.json", {"invocation_id": "I0", "launch_id": "L0",
         "plan_sha256": digest(plan), "supervisor_pid": 123})
    write(tmp_path / "invocation-processes/L0.json", {"launch_id": "L0",
          "invocation_id": "I0", "pid": None, "exit_code": None})
    write(tmp_path / "supervisor-finishes/L0.json", {"launch_id": "L0",
          "state": "needs_attention"})
    write(tmp_path / "invocations/I1.json", {"invocation_id": "I1", "launch_id": "L1",
         "plan_sha256": digest(plan), "supervisor_pid": 456})
    write(tmp_path / "invocation-processes/L1.json", {"launch_id": "L1",
          "invocation_id": "I1", "pid": 456, "exit_code": 0})
    write(tmp_path / "invocation-finishes/I1.json", {"state": "complete"})
    assert runtime.all_collectors_exited(plan, "L1") == 2
    write(tmp_path / "ledger/reservations/ghost.json", {"invocation_id": "I0"})
    with pytest.raises(ValueError, match="Prior sparse collector"):
        runtime.all_collectors_exited(plan, "L1")


def test_mask_requires_all_direct_and_resource_overflow_stops_without_mask(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    with patch.object(runtime, "completed_rows", return_value=[{"job": {"id": "j"}}]):
        with pytest.raises(ValueError, match="All direct"):
            runtime.freeze_mask(plan)
    rows = [{"job": {"id": f"j{i}"}} for i in range(228)]
    with (patch.object(runtime, "completed_rows", return_value=rows),
          patch.object(runtime.sparse, "eligibility", side_effect=ValueError(
              "Hard resource stop: more than 32 eligible; no subsample"))):
        with pytest.raises(runtime.ResourceStop):
            runtime.freeze_mask(plan)
    assert not (tmp_path / "eligibility.json").exists()


def test_mask_freeze_accepts_prior_terminal_output_without_receipt_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    rows = [{"attempt_id": f"A{i}", "job": {"id": f"d{i}"}} for i in range(228)]
    write(tmp_path / "ledger/reservations/A0.json", {"id": "A0",
          "invocation_id": "I0", "started_at": 930.0})
    write(tmp_path / "invocations/I0.json", {"invocation_id": "I0", "launch_id": "L0"})
    write(tmp_path / "invocation-processes/L0.json", {"finished_at": 935.0})
    for i in range(1, 228):
        write(tmp_path / "ledger/settlements" / f"A{i}.json", {"finished_at": 931.0})
    with (patch.object(runtime, "completed_rows", return_value=rows),
          patch.object(runtime.sparse, "eligibility", return_value=["q0"])):
        mask = runtime._mask_payload(plan, rows) | {"frozen_at": 940.0}
        write(tmp_path / "eligibility.json", mask)
        assert runtime.read_mask(plan) == mask
        mask["frozen_at"] = 934.0
        write(tmp_path / "eligibility.json", mask)
        with pytest.raises(ValueError, match="completion evidence"):
            runtime.read_mask(plan)


def test_no_score_or_reference_before_endpoint_and_zero_event_uses_none(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    mask = {"eligible_count": 0, "eligible_question_ids": []}
    with patch.object(runtime, "selected_gold") as gold:
        sidecar = runtime.score_endpoint(plan, {}, mask, [])
        assert sidecar["scores"] == [] and sidecar["gold_sha256"] is None
        assert runtime.score_endpoint(plan, {}, mask, []) == sidecar
        gold.assert_not_called()
    assert not (tmp_path / "score-started.json").exists()
    with (patch.object(runtime, "authenticate_finalizer", return_value=(plan, {}, {})),
          patch.object(runtime, "endpoint", side_effect=ValueError("incomplete")),
          patch.object(runtime, "selected_gold") as gold):
        with pytest.raises(ValueError, match="incomplete"):
            runtime.finalize()
        gold.assert_not_called()


def test_cached_score_semantics_bind_extracted_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    thinking = [{"job": plan["thinking_jobs"][0], "status": "completed",
                 "result": synthetic_result()}]
    mask = {"eligible_count": 1, "eligible_question_ids": ["q0"]}
    header = runtime._score_header(plan, mask, thinking)
    score = {"job_id": "thinking-0", "question_id": "q0", "mode": "thinking",
             "scoring_version": "numeric-v7", "parser_status": "ok",
             "extracted_answer": "wrong", "correct": True}
    with patch.object(runtime.scoring_v7, "extract_record", return_value=("1", "ok")):
        with pytest.raises(ValueError, match="semantics"):
            runtime._check_scores(header | {"gold_sha256": "hash", "scores": [score]},
                                  plan, mask, thinking)


def test_launch_requires_independent_review_before_power_or_process(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    with (patch.object(runtime, "read_plan", return_value=(plan, {}, {})),
          patch.object(runtime.recovery, "launch_preflight") as power,
          patch.object(runtime.subprocess, "Popen") as spawn):
        with pytest.raises(FileNotFoundError):
            runtime.launch()
        power.assert_not_called()
        spawn.assert_not_called()


def test_score_marker_without_cache_cannot_reopen_selected_gold(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    mask = {"eligible_count": 1, "eligible_question_ids": ["q0"]}
    write(tmp_path / "score-started.json", {"plan_sha256": digest(plan)})
    with patch.object(runtime, "selected_gold") as gold:
        with pytest.raises(ValueError, match="may not reopen"):
            runtime.score_endpoint(plan, {}, mask, [{}])
        gold.assert_not_called()


def test_selected_answer_callback_cannot_bypass_private_finalizer(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    with (patch.object(runtime, "authenticate_finalizer",
                       side_effect=ValueError("not live supervisor")),
          patch("datasets.Dataset.from_file") as arrow):
        with pytest.raises(ValueError, match="not live supervisor"):
            runtime.selected_gold(tiny_plan(), {"selected": []},
                                  {"eligible_question_ids": ["q0"], "eligible_count": 1})
        arrow.assert_not_called()


def test_valid_selected_score_cache_never_reopens_references(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    mask = {"eligible_count": 1, "eligible_question_ids": ["q0"]}
    thinking = [{"job": plan["thinking_jobs"][0], "status": "completed",
                 "result": synthetic_result()}]
    score = {"job_id": "thinking-0", "question_id": "q0", "mode": "thinking",
             "scoring_version": "numeric-v7", "parser_status": "ok",
             "extracted_answer": "1", "correct": True}
    artifact = runtime._score_header(plan, mask, thinking) | {
        "gold_sha256": "selected-gold-hash", "scores": [score]}
    write(tmp_path / "scores.numeric-v7.json", artifact)
    write(tmp_path / "score-started.json", {"plan_sha256": digest(plan),
          "eligibility_sha256": digest(mask),
          "selected_sha256": digest(mask["eligible_question_ids"])})
    with (patch.object(runtime.scoring_v7, "extract_record", return_value=("1", "ok")),
          patch.object(runtime, "selected_gold") as gold):
        assert runtime.score_endpoint(plan, {}, mask, thinking) == artifact
        gold.assert_not_called()


def test_synthetic_prepare_is_one_time_and_does_not_construct_model(tmp_path, monkeypatch):
    child_dir = tmp_path / "runtime-v1"
    monkeypatch.setattr(runtime, "RUNTIME", child_dir)
    direct = [{"id": f"d{i}", "question_id": f"q{i}", "mode": "direct",
               "sample": 0, "seed": i, "max_tokens": 512} for i in range(228)]
    thinking = [{"id": f"t{i}", "question_id": f"q{i}", "mode": "thinking",
                 "sample": 0, "seed": 228 + i, "max_tokens": 2562} for i in range(228)]
    protocol = {"arm": {"jobs": direct + thinking, "asset_file_sha256": {},
                "generation_implementation_sha256": "gen"}}
    child = {"selected": [{"child_question": {"id": f"q{i}"}} for i in range(228)]}
    policy = {"fit": {"threshold": 0.0}}
    with (patch.object(runtime, "safe_path"),
          patch.object(runtime, "_current_inputs", return_value=(protocol, policy, child)),
          patch.object(runtime, "prepared_paths", return_value=[]),
          patch.object(runtime, "source_hashes", return_value={}),
          patch.object(runtime.orig, "stable_environment", return_value={}),
          patch.object(runtime.orig, "TransformersBackend") as backend):
        assert runtime.prepare()["direct_jobs"] == 228
        assert (child_dir / "prepare-started.json").exists()
        assert (child_dir / "plan.json").exists()
        assert all(p.is_relative_to(child_dir) for p in child_dir.rglob("*"))
        backend.assert_not_called()
        with pytest.raises(ValueError, match="already prepared"):
            runtime.prepare()


def test_collector_charges_setup_before_deep_asset_check_or_model(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    plan = tiny_plan()
    events = []
    def reserve(*_args, **_kwargs):
        events.append("reserve")
        return {"id": "S0", "reserved_seconds": 900.0, "reserved_tokens": 0}
    def deep_read(**_kwargs):
        events.append("deep_input_asset_check")
        raise ValueError("synthetic asset mismatch")
    def settle(*_args, **_kwargs):
        events.append("settle_failed_setup")
    with (patch.object(runtime, "authenticate_collector", return_value=(plan, {}, {}, {})),
          patch.object(runtime, "anchored_reserve", side_effect=reserve),
          patch.object(runtime, "read_plan", side_effect=deep_read),
          patch.object(runtime, "settle", side_effect=settle),
          patch.object(runtime.orig, "TransformersBackend") as backend):
        with pytest.raises(ValueError, match="synthetic asset mismatch"):
            runtime.collect("I0")
        assert events == ["reserve", "deep_input_asset_check", "settle_failed_setup"]
        backend.assert_not_called()
