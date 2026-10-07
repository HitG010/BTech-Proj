"""Synthetic completion tests; never construct a real model or open references."""

from copy import deepcopy
from types import ModuleType, SimpleNamespace

import pytest

from reasoning_budget.records import GenerationJob
from reasoning_budget.storage import digest, verified
from scripts import macos_runtime_guard
from scripts import qwen17_cap_bridge_completion as completion
from tests.test_qwen17_cap_bridge_collect import plans, result, rows_and_scores


def synthetic_parent():
    plan, cap_plan, snapshot = plans()
    rows, _ = rows_and_scores(plan)
    return plan, cap_plan, snapshot, rows[:6], rows


def write(path, payload):
    completion.orig.write_once(path, payload)


def test_pending_is_exact_original_order_and_seed_without_identity_change():
    parent, _, _, old, _ = synthetic_parent()
    before = digest(parent)
    pending = completion.pending_jobs(parent, old)
    assert pending == parent["ordered_jobs"][6:]
    assert len(pending) == len({entry["job"]["id"] for entry in pending}) == 30
    assert sum(entry["job"]["max_tokens"] for entry in pending) == 107580
    assert sum(entry["arm"] == "control_2k" for entry in pending) == 15
    assert sum(entry["arm"] == "extended_4k" for entry in pending) == 15
    assert digest(parent) == before
    assert all(entry["job"]["identity"]["config"]["limits"]["job_seconds"] == 600
               for entry in pending)
    for bad in (old[:-1], old + [old[0]], old[:-1] + [old[0]]):
        with pytest.raises(ValueError):
            completion.pending_jobs(parent, bad)


def test_pending_rejects_foreign_or_modified_completed_job():
    parent, _, _, old, _ = synthetic_parent()
    altered = deepcopy(old)
    altered[0]["job"]["seed"] += 1
    with pytest.raises(ValueError):
        completion.pending_jobs(parent, altered)
    foreign = deepcopy(old)
    foreign[0]["job"]["id"] = "foreign"
    with pytest.raises(ValueError):
        completion.pending_jobs(parent, foreign)


def test_parent_snapshot_preserves_every_old_byte_and_excludes_only_child(tmp_path, monkeypatch):
    root = tmp_path / "cap"
    parent = root / "runtime-v1"
    parent.mkdir(parents=True)
    (parent / "status.json").write_text("stopped original")
    (root / "plan.json").write_text("old cap plan")
    child = root / "completion-v1"
    child.mkdir()
    (child / "status.json").write_text("new child")
    monkeypatch.setattr(completion.cap, "OUTPUT", root)
    monkeypatch.setattr(completion, "RUNTIME", child)
    snapshot = completion.parent_snapshot()
    assert set(snapshot) == {"runtime-v1/status.json", "plan.json"}
    assert snapshot["runtime-v1/status.json"] == completion.file_hash(parent / "status.json")
    (child / "other.json").write_text("child is additive")
    assert completion.parent_snapshot() == snapshot
    (parent / "status.json").write_text("corrupted old status")
    assert completion.parent_snapshot() != snapshot


def test_parent_boundary_requires_exhausted_stopped_unscored_run(tmp_path, monkeypatch):
    parent, cap_plan, snapshot, old, _ = synthetic_parent()
    monkeypatch.setattr(completion.parent, "RUNTIME", tmp_path)
    monkeypatch.setattr(completion, "_assert_parent_idle", lambda: None)
    monkeypatch.setattr(completion.parent, "read_plan", lambda: (parent, cap_plan, snapshot))
    monkeypatch.setattr(completion.parent, "completed_rows", lambda _: old)
    tally = {"charged_tokens": 28035, "charged_seconds": 2621.5458,
             "setup_reservations": 2, "attempts": 8, "unresolved": 1, "budget_seconds": 3000.}
    terminal = {"state": "needs_attention", "failure_kind": "runtime", "plan_sha256": digest(parent),
                "progress": tally | {"completed": 6}}
    write(tmp_path / "status.json", terminal)
    monkeypatch.setattr(completion.parent, "usage", lambda _: tally)
    launches = [{"launch_id": "L0"}, {"launch_id": "L1"}]
    monkeypatch.setattr(completion.parent, "_launch_rows", lambda _: launches)
    unknown = {"kind": "job", "reserved_tokens": 4610, "reserved_seconds": 600,
               "job_id": parent["ordered_jobs"][6]["job"]["id"], "invocation_id": "I1"}
    journals = {"invocation-processes": {"L0": {"exit_code": 1, "invocation_id": "I0"},
                                         "L1": {"exit_code": -15, "invocation_id": "I1"}},
                "supervisor-finishes": {"L0": {"state": "needs_attention"},
                                        "L1": {"state": "needs_attention"}},
                "ledger/reservations": {"unknown": unknown}, "ledger/settlements": {},
                "invocations": {"I0": {"launch_id": "L0"}, "I1": {"launch_id": "L1"}}}
    monkeypatch.setattr(completion.parent, "_all", lambda folder: journals[folder])
    assert completion.parent_boundary()[4] == parent["ordered_jobs"][6:]
    owner = journals["invocations"].pop("I1")
    with pytest.raises(ValueError, match="boundary"):
        completion.parent_boundary()
    journals["invocations"]["I1"] = owner
    journals["invocation-processes"]["L1"]["invocation_id"] = "wrong-owner"
    with pytest.raises(ValueError, match="boundary"):
        completion.parent_boundary()
    journals["invocation-processes"]["L1"]["invocation_id"] = "I1"
    launches.pop()
    with pytest.raises(ValueError, match="boundary"):
        completion.parent_boundary()
    launches.append({"launch_id": "L1"})
    unknown["reserved_tokens"] = 0
    with pytest.raises(ValueError, match="boundary"):
        completion.parent_boundary()
    unknown["reserved_tokens"] = 4610
    write(tmp_path / "score-started.json", {"started": True})
    with pytest.raises(ValueError, match="boundary"):
        completion.parent_boundary()


def prepared_fixture(tmp_path, monkeypatch):
    parent, cap_plan, snapshot, old, _ = synthetic_parent()
    parent["generation_implementation_sha256"] = completion.orig.implementation_digest()
    for row in old:
        row["plan_sha256"] = digest(parent)
        row["implementation_sha256"] = parent["generation_implementation_sha256"]
    root = tmp_path / "cap"
    parent_dir = root / "runtime-v1"
    parent_dir.mkdir(parents=True)
    write(parent_dir / "status.json", {"state": "needs_attention"})
    write(parent_dir / "plan.json", parent)
    write(root / "plan.json", cap_plan)
    write(root / "question-snapshot.json", snapshot)
    monkeypatch.setattr(completion.cap, "OUTPUT", root)
    monkeypatch.setattr(completion.parent, "RUNTIME", parent_dir)
    monkeypatch.setattr(completion, "RUNTIME", root / "completion-v1")
    old_tally = {"charged_tokens": 28035, "charged_seconds": 2621.5458, "completed": 6,
                 "wall_seconds": 3000., "budget_seconds": 3000.}
    monkeypatch.setattr(completion, "parent_boundary", lambda:
        (parent, cap_plan, snapshot, old, parent["ordered_jobs"][6:], old_tally))
    monkeypatch.setattr(completion, "source_hashes", lambda: {"synthetic": "pin"})
    monkeypatch.setattr(completion.orig, "stable_environment", lambda: {})
    decision = tmp_path / "decision.json"
    write(decision, {"version": "qwen17-cap-completion-decision-v1", "parent_plan_sha256": digest(parent),
          "remaining_jobs": 30, "response_only_bound": 107580, "parent_conservative_tokens": 28035,
          "combined_maximum_tokens_without_child_retries": 135615,
          "new_completion_wall_and_charged_seconds": 28800})
    monkeypatch.setattr(completion, "DECISION", decision)
    return parent, cap_plan, snapshot, old


def test_prepare_is_single_no_model_and_read_plan_guards_parent_sources_environment(tmp_path, monkeypatch):
    prepared_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(completion.orig, "TransformersBackend", lambda _: pytest.fail("model construction"))
    answer = completion.prepare()
    plan = verified(completion.RUNTIME / "plan.json")
    assert answer["pending"] == 30 and answer["maximum_combined_reservation_tokens"] == 135615
    assert plan["old_terminal_charged_tokens"] == 28035
    assert plan["spec"]["new_wall_seconds"] == 28800
    assert completion.read_plan()[0] == plan
    with pytest.raises(ValueError, match="prepared"):
        completion.prepare()
    monkeypatch.setattr(completion, "source_hashes", lambda: {"synthetic": "changed"})
    with pytest.raises(ValueError, match="source"):
        completion.read_plan()
    monkeypatch.setattr(completion, "source_hashes", lambda: {"synthetic": "pin"})
    monkeypatch.setattr(completion.orig, "stable_environment", lambda: {"different": True})
    with pytest.raises(ValueError, match="environment"):
        completion.read_plan()
    monkeypatch.setattr(completion.orig, "stable_environment", lambda: {})
    (completion.parent.RUNTIME / "status.json").write_text("changed old failure")
    with pytest.raises(ValueError, match="parent"):
        completion.read_plan()


def child_plan_fixture(tmp_path, monkeypatch):
    parent, cap_plan, snapshot, old = prepared_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(completion.time, "time", lambda: 1000.)
    completion.prepare()
    plan = verified(completion.RUNTIME / "plan.json")
    return plan, parent, cap_plan, snapshot, old


def child_journals(plan, *, started=True, setup=True):
    root = completion.RUNTIME
    pin = digest(plan)
    write(root / "launches/L0.json", {"launch_id": "L0", "plan_sha256": pin,
          "reserved_at": 1002., "explicit_resume": False})
    write(root / "supervisor-starts/L0.json", {"launch_id": "L0", "pid": 123, "started_at": 1005.})
    write(root / "invocations/I0.json", {"invocation_id": "I0", "launch_id": "L0",
          "plan_sha256": pin, "supervisor_pid": 123})
    write(root / "collection-start.json", {"plan_sha256": pin, "launch_id": "L0", "started_at": 1005.})
    if started:
        write(root / "invocation-starts/I0.json", {"invocation_id": "I0", "pid": 124, "started_at": 1008.})
    if setup:
        reservation = {"id": "S0", "plan_sha256": pin, "parent_plan_sha256": plan["parent_plan_sha256"],
              "invocation_id": "I0", "kind": "setup", "started_at": 1010.,
              "reserved_tokens": 0, "reserved_seconds": 900.}
        write(root / "ledger/reservations/S0.json", reservation)
        write(root / "anchors/S0.json", {"id": "S0", "reservation_sha256": digest(reservation),
              "invocation_id": "I0", "pid": 124, "monotonic_before_reserve": 100.})
        write(root / "ledger/settlements/S0.json", {"id": "S0", "reservation_sha256": digest(reservation),
              "status": "loaded", "charged_tokens": 0, "elapsed_seconds": 5., "finished_at": 1015.})


def test_ledger_separates_new_clock_and_charges_old_unknown_and_new_reservation(tmp_path, monkeypatch):
    plan, _, _, _, _ = child_plan_fixture(tmp_path, monkeypatch)
    child_journals(plan)
    monkeypatch.setattr(completion.time, "time", lambda: 1030.)
    first = GenerationJob(**plan["pending_jobs"][0]["job"])
    reservation = completion.reserve(plan, "job", "I0", job=first, session_id="S0")
    assert reservation["reserved_seconds"] == 1800 and first.identity["config"]["limits"]["job_seconds"] == 600
    tally = completion.usage(plan)
    assert tally["wall_seconds"] == 25  # Old parent age is not substituted for this clock.
    assert tally["charged_tokens"] == 4610 and tally["combined_charged_tokens"] == 32645
    assert tally["charged_seconds"] == 1805
    assert tally["combined_charged_seconds"] == pytest.approx(2621.5458 + 1805)
    assert tally["old_unknown_charged_tokens"] == 4610 and tally["old_unknown_charged_seconds"] == 600
    assert tally["unresolved"] == 1
    with pytest.raises(ValueError, match="retry"):
        completion.reserve(plan, "job", "I0", job=first, session_id="S0")
    with pytest.raises(completion.orig.BudgetExhausted):
        completion.reserve(plan, "setup", "I0")
    monkeypatch.setattr(completion, "SPEC", completion.SPEC | {"combined_token_limit": 33000})
    with pytest.raises(completion.orig.BudgetExhausted):
        completion.reserve(plan, "job", "I0", job=GenerationJob(**plan["pending_jobs"][1]["job"]), session_id="S0")


def test_reverse_receipt_snapshot_conservatively_handles_live_loaded_setup(tmp_path, monkeypatch):
    plan, _, _, _, _ = child_plan_fixture(tmp_path, monkeypatch)
    child_journals(plan)
    monkeypatch.setattr(completion.time, "time", lambda: 1030.)
    completion.reserve(plan, "job", "I0", job=GenerationJob(**plan["pending_jobs"][0]["job"]), session_id="S0")
    actual_all = completion._all
    monkeypatch.setattr(completion, "_all", lambda folder: {} if folder == "ledger/settlements" else actual_all(folder))
    conservative = completion.usage(plan)
    assert conservative["charged_seconds"] == 2700 and conservative["unresolved"] == 2
    monkeypatch.setattr(completion, "_all", actual_all)
    assert completion.usage(plan)["charged_seconds"] == 1805


def test_new_wall_age_stops_work_and_second_launch_cannot_enter(tmp_path, monkeypatch):
    plan, _, _, _, _ = child_plan_fixture(tmp_path, monkeypatch)
    child_journals(plan)
    monkeypatch.setattr(completion.time, "time", lambda: 1005. + 28801.)
    with pytest.raises(completion.orig.BudgetExhausted):
        completion.reserve(plan, "job", "I0", job=GenerationJob(**plan["pending_jobs"][0]["job"]), session_id="S0")
    write(completion.RUNTIME / "launches/L1.json", {"launch_id": "L1", "plan_sha256": digest(plan),
          "reserved_at": 2000., "explicit_resume": True})
    with pytest.raises(ValueError, match="launch ceiling"):
        completion.usage(plan)


def run_fake_collector(tmp_path, monkeypatch, *, fail_first=False):
    plan, parent, cap_plan, snapshot, old = child_plan_fixture(tmp_path, monkeypatch)
    preserved = completion.parent_snapshot()
    child_journals(plan, started=False, setup=False)
    monkeypatch.setattr(completion.time, "time", lambda: 1030.)
    monkeypatch.setattr(completion.time, "monotonic", lambda: 5000.)
    monkeypatch.setattr(completion, "authenticate_collector", lambda _: (plan, cap_plan, snapshot, {"launch_id": "L0"}))
    monkeypatch.setattr(completion, "read_plan", lambda **_: (plan, parent, cap_plan, snapshot))
    monkeypatch.setattr(completion.parent, "completed_rows", lambda _: old)
    monkeypatch.setattr(macos_runtime_guard, "runtime_snapshot", lambda: {"synthetic_hardware": True})
    seen, loads = [], []
    class Engine:
        def __init__(self, config):
            self.config = config
            self.metadata = cap_plan["arms"]["control_2k"]["backend_metadata"]
            self.model = None
            self.tokenizer = object()
        def load(self):
            loads.append(self.config.reasoning_tokens)
            self.model = object()
        def generate(self, question, job, deadline):
            assert self.config.to_dict() == job.identity["config"]
            assert self.config.limits.job_seconds == 600
            assert deadline == 6800  # New external limit, original immutable identity.
            seen.append((job.id, job.seed, self.config.reasoning_tokens, id(self.model)))
            if fail_first:
                raise RuntimeError("synthetic first failure")
            return result()
    actual_load = completion.load_backends
    monkeypatch.setattr(completion, "load_backends", lambda p: actual_load(p, backend_factory=Engine))
    if fail_first:
        with pytest.raises(RuntimeError, match="synthetic first failure"):
            completion.collect("I0")
    else:
        completion.collect("I0")
    assert completion.parent_snapshot() == preserved
    return plan, parent, cap_plan, snapshot, old, seen, loads


def test_full_fake_collector_reuses_weights_and_preserves_parent_with_exact_30_jobs(tmp_path, monkeypatch):
    plan, parent, _, _, old, seen, loads = run_fake_collector(tmp_path, monkeypatch)
    assert loads == [2048] and len(seen) == 30 and len({r[3] for r in seen}) == 1
    assert [r[0] for r in seen] == [e["job"]["id"] for e in plan["pending_jobs"]]
    assert [r[1] for r in seen] == [e["job"]["seed"] for e in plan["pending_jobs"]]
    assert [r[2] for r in seen] == [e["job"]["identity"]["config"]["reasoning_tokens"] for e in plan["pending_jobs"]]
    tally = completion.usage(plan)
    assert tally["charged_tokens"] == 150 and tally["combined_charged_tokens"] == 28185
    assert tally["attempts"] == 30 and tally["unresolved"] == 0 and tally["setup_reservations"] == 1
    combined = completion.combined_rows(plan, parent)
    assert combined[:6] == old and len(combined) == 36
    assert [r["job"]["id"] for r in combined] == [e["job"]["id"] for e in parent["ordered_jobs"]]
    assert all(r["parent_plan_sha256"] == digest(parent) and r["plan_sha256"] == digest(plan)
               for r in combined[6:])
    assert len(completion.endpoint(plan)[1]) == 18
    admissions = completion._all("hardware")
    assert len(admissions) == 30
    assert all(row["stage"] == "admission" and row["descriptive_only"] is True
               and row["host"] == {"synthetic_hardware": True} for row in admissions.values())


def test_first_failure_stops_without_quality_retry_or_parent_write(tmp_path, monkeypatch):
    plan, _, _, _, _, seen, loads = run_fake_collector(tmp_path, monkeypatch, fail_first=True)
    assert loads == [2048] and len(seen) == 1
    assert completion.completed_new(plan) == []
    tally = completion.usage(plan)
    assert tally["attempts"] == 1 and tally["unresolved"] == 0
    assert tally["combined_charged_tokens"] == 28035 + 4610
    assert len(completion._all("attempt-records")) == 1


def test_inflight_published_child_output_is_not_complete_without_receipt(tmp_path, monkeypatch):
    plan, _, _, _, _ = child_plan_fixture(tmp_path, monkeypatch)
    child_journals(plan)
    monkeypatch.setattr(completion.time, "time", lambda: 1030.)
    entry = plan["pending_jobs"][0]
    reservation = completion.reserve(plan, "job", "I0", job=GenerationJob(**entry["job"]), session_id="S0")
    row = {"plan_sha256": digest(plan), "parent_plan_sha256": plan["parent_plan_sha256"],
           "cap_plan_sha256": plan["cap_plan_sha256"], "implementation_sha256": plan["generation_implementation_sha256"],
           **entry, "status": "completed", "result": result().to_dict(),
           "attempt_id": reservation["id"], "session_id": "S0"}
    write(completion.RUNTIME / "results" / f'{entry["job"]["id"]}.json', row)
    assert completion.completed_new(plan) == []
    assert completion.usage(plan)["unresolved"] == 1


def close_fake_collector(plan, combined):
    pairs = completion.prefix_gate(plan, combined)
    write(completion.RUNTIME / "invocation-processes/L0.json", {"launch_id": "L0", "invocation_id": "I0",
          "exit_code": 0, "finished_at": 1040.})
    write(completion.RUNTIME / "invocation-finishes/I0.json", {"state": "complete"})
    write(completion.RUNTIME / "collection-end.json", {"plan_sha256": digest(plan), "finished_at": 1050.})
    write(completion.RUNTIME / "finalize-request.json", {"launch_id": "L0", "plan_sha256": digest(plan),
          "records_sha256": digest(combined), "pair_gate_sha256": digest(pairs)})
    return pairs


def test_private_and_complete_prefix_boundaries_block_all_early_reference_access(tmp_path, monkeypatch):
    plan, parent, _, snapshot, _, _, _ = run_fake_collector(tmp_path, monkeypatch)
    combined = completion.combined_rows(plan, parent)
    pairs = close_fake_collector(plan, combined)
    monkeypatch.setattr(completion.time, "time", lambda: 1052.)
    monkeypatch.setattr(completion, "selected_gold", lambda *_: pytest.fail("opened references"))
    monkeypatch.setattr(completion.scoring_v7, "score_record", lambda *_: pytest.fail("scored before full endpoint"))
    monkeypatch.setattr(completion.parent, "score_endpoint", lambda *_: pytest.fail("old scorer called"))
    monkeypatch.setattr(completion.parent, "authenticate_finalizer", lambda: pytest.fail("old authentication called"))
    monkeypatch.setattr(completion.os, "getppid", lambda: 456)
    with pytest.raises(ValueError, match="Private"):
        completion.score_endpoint(plan, snapshot, combined, pairs)
    assert not (completion.RUNTIME / "score-started.json").exists()
    monkeypatch.setattr(completion.os, "getppid", lambda: 123)
    for candidate in (combined[:-1], deepcopy(combined)):
        if len(candidate) == 36:
            candidate[6]["result"]["metadata"]["reasoning_token_ids"][0] = 999
        monkeypatch.setattr(completion, "combined_rows", lambda _, candidate=candidate: candidate)
        with pytest.raises(ValueError, match="36|diverged"):
            completion.score_endpoint(plan, snapshot, candidate, [])
        assert not (completion.RUNTIME / "score-started.json").exists()


def test_late_cached_audit_uses_frozen_close_but_live_scoring_stays_blocked(tmp_path, monkeypatch):
    plan, parent, _, snapshot, _, _, _ = run_fake_collector(tmp_path, monkeypatch)
    combined = completion.combined_rows(plan, parent)
    pairs = close_fake_collector(plan, combined)
    _, original_scores = rows_and_scores(parent)
    cached = completion._score_header(plan, combined, pairs) | {
        "gold_sha256": "a" * 64, "scores": original_scores["scores"]}
    write(completion.RUNTIME / "scores.numeric-v7.json", cached)
    write(completion.RUNTIME / "score-started.json", {"plan_sha256": digest(plan),
          "records_sha256": digest(combined), "pair_gate_sha256": digest(pairs),
          "selected_question_ids_sha256": digest(plan["question_ids"]), "started_at": 1051.})
    monkeypatch.setattr(completion.time, "time", lambda: 1005. + 28801.)
    monkeypatch.setattr(completion, "selected_gold", lambda *_: pytest.fail("cached audit reopened references"))
    assert len(completion.endpoint(plan, require_live=False)[0]) == 36
    with pytest.raises(completion.orig.BudgetExhausted):
        completion.endpoint(plan)
    assert completion.score_endpoint(plan, snapshot, combined, pairs) == cached
    assert completion.analyze_pairs(plan, combined, cached) == completion.parent.analyze_pairs(plan, combined, cached)
    assert completion.analyze_pairs(plan, combined, cached)["primary_equal_11_questions"]["correct"]["delta"] == 0
    assert completion.analyze_pairs(plan, combined, cached)["bootstrap_seed"] == 20261020


def test_asset_or_model_metadata_mismatch_blocks_model_loading():
    _, cap_plan, _, _, _ = synthetic_parent()
    changed_assets = deepcopy(cap_plan)
    changed_assets["arms"]["extended_4k"]["asset_file_sha256"] = {"foreign-model": "wrong"}
    with pytest.raises(ValueError, match="same local weights"):
        completion.load_backends(changed_assets, backend_factory=lambda _: pytest.fail("constructed after asset mismatch"))
    loaded = []
    class WrongEngine:
        def __init__(self, config):
            self.metadata = {"different_revision": True}
        def load(self):
            loaded.append(True)
    with pytest.raises(ValueError, match="metadata"):
        completion.load_backends(cap_plan, backend_factory=WrongEngine)
    assert loaded == []


def test_reference_callback_rechecks_live_ceiling_after_slow_source_verification(tmp_path, monkeypatch):
    plan, parent, _, snapshot, _, _, _ = run_fake_collector(tmp_path, monkeypatch)
    rows = completion.combined_rows(plan, parent)
    pairs = close_fake_collector(plan, rows)
    write(completion.RUNTIME / "score-started.json", {"plan_sha256": digest(plan),
          "records_sha256": digest(rows), "pair_gate_sha256": digest(pairs),
          "selected_question_ids_sha256": digest(plan["question_ids"]), "started_at": 1051.})
    snapshot["selected_training_source_rows"] = [{"child_question": q, "upstream_index": i}
        for i, q in enumerate(snapshot["questions"])]
    monkeypatch.setattr(completion.time, "time", lambda: 1052.)
    monkeypatch.setattr(completion.os, "getppid", lambda: 123)
    from scripts import opportunity_panel_plan, verify_phase2_repeat
    monkeypatch.setattr(verify_phase2_repeat, "verify", lambda *_: {})
    def slow_source(*_):
        monkeypatch.setattr(completion.time, "time", lambda: 1005. + 28801.)
        return {"source": {"split": "train", "arrow_path": "SYNTHETIC_NEVER_OPENED"}}
    monkeypatch.setattr(opportunity_panel_plan, "verify", slow_source)
    fake_datasets = ModuleType("datasets")
    class Dataset:
        @staticmethod
        def from_file(path):
            pytest.fail("opened answer column after source verification exhausted live time")
    fake_datasets.Dataset = Dataset
    monkeypatch.setitem(completion.sys.modules, "datasets", fake_datasets)
    with pytest.raises(completion.orig.BudgetExhausted):
        completion.selected_gold(plan, snapshot)


def test_unavailable_hardware_is_descriptive_and_coarse_stall_snapshots_are_once(tmp_path, monkeypatch):
    plan, _, _, _, _ = child_plan_fixture(tmp_path, monkeypatch)
    child_journals(plan)
    monkeypatch.setattr(completion.time, "time", lambda: 1030.)
    monkeypatch.setattr(completion.time, "monotonic", lambda: 100.)
    job = GenerationJob(**plan["pending_jobs"][0]["job"])
    completion.anchored_reserve(plan, "job", "I0", job=job, session_id="S0")
    write(completion.RUNTIME / "invocation-ready/I0.json", {"invocation_id": "I0",
          "session_id": "S0", "ready_at": 1010.})
    calls = []
    def unavailable():
        calls.append(True)
        raise RuntimeError("synthetic unavailable host telemetry")
    monkeypatch.setattr(macos_runtime_guard, "runtime_snapshot", unavailable)
    monkeypatch.setattr(completion.time, "monotonic", lambda: 1350.)
    monkeypatch.setattr(completion.time, "sleep", lambda _: None)
    monkeypatch.setattr(completion.subprocess, "run", lambda *_, **__: SimpleNamespace(returncode=0, stdout="1"))
    class Process:
        pid = completion.os.getpid()
        iterations = 0
        def poll(self):
            self.iterations += 1
            return None if self.iterations <= 2 else 0
    telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
    completion.monitor(Process(), plan, "I0", 100., telemetry)
    samples = completion._all("hardware")
    assert set(samples) == {f"{job.id}-stall-600", f"{job.id}-stall-1200"}
    assert len(calls) == 2  # Two thresholds, despite two monitor iterations.
    assert all(sample["stage"] == "coarse_stall" and sample["descriptive_only"] is True
               and "unavailable" in sample["host"] for sample in samples.values())
    assert completion.usage(plan)["charged_tokens"] == 4610
