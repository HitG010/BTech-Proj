"""Synthetic accounting, prefix, shared-weight and endpoint tests; no real model."""

import math
import random
from copy import deepcopy

import numpy as np
import pytest

from reasoning_budget.records import GenerationJob, GenerationResult
from reasoning_budget.storage import digest, verified
from scripts import qwen17_cap_bridge_collect as runtime
from scripts import qwen17_cap_bridge_plan as cap
from tests.test_qwen17_cap_bridge_plan import fixture


def write(path, payload):
    runtime.orig.write_once(path, payload)


def plans():
    protocol, cells = fixture()
    arms = cap.matched_jobs(protocol, cells, "/tmp/synthetic-cap-runtime")
    questions = {c["question_id"]: c["original_job"]["identity"]["question"] for c in cells}
    snapshot = {"questions": [questions[q] for q in sorted(questions)],
                "selected_training_source_rows": []}
    prepared = {"arms": arms, "cells": cells, "question_snapshot_sha256": digest(snapshot)}
    plan = {"prepared_at": 900., "ordered_jobs": runtime.ordered_jobs(prepared),
            "question_ids": sorted(questions), "cap_plan_sha256": digest(prepared),
            "generation_implementation_sha256": "generator",
            "scoring_implementation_sha256": runtime.scoring_v7.implementation_digest()}
    return plan, prepared, snapshot


def result(answer="1", *, answer_tokens=3):
    return GenerationResult(
        raw_output=f"</think>\\boxed{{{answer}}}", reasoning="synthetic",
        final_answer=f"\\boxed{{{answer}}}", prompt_tokens=10,
        reasoning_tokens=2, answer_tokens=answer_tokens, inserted_tokens=0,
        elapsed_seconds=.001, reasoning_seconds=0., answer_seconds=.001,
        closure_seconds=0., forced_closure=False, answer_truncated=False, termination="eos",
        metadata={"reasoning_token_ids": [11, 151668],
                  "answer_token_ids": [90] * (answer_tokens - 1) + [151645],
                  "inserted_token_ids": []})


def rows_and_scores(plan, *, varying=False):
    rows = []
    scores = []
    for entry in plan["ordered_jobs"]:
        extended = entry["arm"] == "extended_4k"
        correct = (extended if entry["cell_index"] < 14 else not extended) if varying else True
        value = result("1" if correct else "0", answer_tokens=8 if extended else 3)
        row = {"plan_sha256": digest(plan), "cap_plan_sha256": plan["cap_plan_sha256"],
               "implementation_sha256": plan["generation_implementation_sha256"],
               **entry, "status": "completed", "result": value.to_dict(),
               "attempt_id": f"A{len(rows)}", "session_id": "S0"}
        rows.append(row)
        scores.append({"arm": entry["arm"], "cell_index": entry["cell_index"],
                       "job_id": entry["job"]["id"], "question_id": entry["job"]["question_id"],
                       "mode": "thinking", "extracted_answer": "1" if correct else "0",
                       "correct": bool(correct), "parser_status": "ok", "scoring_version": "numeric-v7"})
    pairs = runtime.prefix_gate(plan, rows)
    artifact = runtime._score_header(plan, rows, pairs) | {"gold_sha256": "a" * 64, "scores": scores}
    return rows, artifact


def journals(tmp_path, plan, *, started=True, setup=True):
    pin = digest(plan)
    write(tmp_path / "launches/L0.json", {"launch_id": "L0", "plan_sha256": pin,
                                        "reserved_at": 905., "explicit_resume": False})
    write(tmp_path / "supervisor-starts/L0.json", {"launch_id": "L0", "pid": 123, "started_at": 910.})
    write(tmp_path / "invocations/I0.json", {"invocation_id": "I0", "launch_id": "L0",
                                            "plan_sha256": pin, "supervisor_pid": 123})
    write(tmp_path / "collection-start.json", {"plan_sha256": pin, "launch_id": "L0", "started_at": 910.})
    if started:
        write(tmp_path / "invocation-starts/I0.json", {"invocation_id": "I0", "pid": 124, "started_at": 915.})
    if setup:
        reservation = {"id": "S0", "plan_sha256": pin, "invocation_id": "I0", "kind": "setup",
                       "started_at": 920., "reserved_tokens": 0, "reserved_seconds": 900.}
        write(tmp_path / "ledger/reservations/S0.json", reservation)
        write(tmp_path / "anchors/S0.json", {"id": "S0", "reservation_sha256": digest(reservation),
                                            "invocation_id": "I0", "pid": 124,
                                            "monotonic_before_reserve": 100.})
        write(tmp_path / "ledger/settlements/S0.json", {"id": "S0", "reservation_sha256": digest(reservation),
               "status": "loaded", "charged_tokens": 0, "elapsed_seconds": 5., "finished_at": 925.})


def test_balanced_manual_catalog_uses_original_paired_seeds():
    plan, prepared, _ = plans()
    sequence = plan["ordered_jobs"]
    assert len(sequence) == len({e["job"]["id"] for e in sequence}) == 36
    assert sum(e["job"]["max_tokens"] for e in sequence) == 129096
    for i in range(18):
        pair = sequence[2*i:2*i+2]
        assert [e["arm"] for e in pair] == (["control_2k", "extended_4k"] if i % 2 == 0 else
                                           ["extended_4k", "control_2k"])
        assert all(e["job"]["seed"] == prepared["cells"][i]["generation_seed"] for e in pair)
    changed = deepcopy(prepared)
    changed["arms"]["extended_4k"]["jobs"][0]["seed"] += 1
    with pytest.raises(ValueError, match="identity"):
        runtime.ordered_jobs(changed)


def test_prepare_reads_actual_plan_after_summary_returning_verifier(tmp_path, monkeypatch):
    _, prepared, snapshot = plans()
    original_protocol = {"generation_implementation_sha256": runtime.orig.implementation_digest()}
    prepared["parent_protocol_sha256"] = digest(original_protocol)
    monkeypatch.setattr(runtime.orig, "read_protocol", lambda: original_protocol)
    capdir = tmp_path / "cap"
    capdir.mkdir()
    write(capdir / "plan.json", prepared)
    write(capdir / "question-snapshot.json", snapshot)
    write(capdir / "preparation-verification.json", {"checks_passed": True,
          "plan_sha256": digest(prepared), "development_cells": 18,
          "development_question_groups": 11, "potential_response_jobs": 36})
    monkeypatch.setattr(runtime.cap, "OUTPUT", capdir)
    monkeypatch.setattr(runtime, "RUNTIME", capdir / "runtime-v1")
    monkeypatch.setattr(runtime.cap, "verify", lambda: {"plan_sha256": digest(prepared),
          "responses": 36, "generation": "unimplemented_locked"})
    monkeypatch.setattr(runtime, "prepared_paths", lambda: [capdir / "plan.json",
          capdir / "question-snapshot.json", capdir / "preparation-verification.json"])
    monkeypatch.setattr(runtime, "source_hashes", lambda: {"synthetic": "pin"})
    monkeypatch.setattr(runtime.orig, "stable_environment", lambda: {})
    monkeypatch.setattr(runtime.orig, "TransformersBackend", lambda _: pytest.fail("model construction"))
    answer = runtime.prepare()
    frozen = verified(runtime.RUNTIME / "plan.json")
    assert answer["jobs"] == 36
    assert frozen["cap_plan_sha256"] == digest(prepared)
    assert frozen["generation_implementation_sha256"] == runtime.orig.implementation_digest()
    with pytest.raises(ValueError, match="prepared"):
        runtime.prepare()


def test_shared_weights_have_separate_immutable_cap_configs():
    _, prepared, _ = plans()
    before = digest(prepared)
    calls = []
    class Engine:
        def __init__(self, config):
            self.config = config
            self.metadata = prepared["arms"]["control_2k"]["backend_metadata"]
            self.model = None
            self.tokenizer = object()
        def load(self):
            calls.append(self.config.reasoning_tokens)
            self.model = object()
    engines = runtime.load_backends(prepared, backend_factory=Engine)
    control, extended = engines["control_2k"], engines["extended_4k"]
    assert calls == [2048]
    assert control.model is extended.model and control.tokenizer is extended.tokenizer
    assert control.config is not extended.config
    assert (control.config.reasoning_tokens, extended.config.reasoning_tokens) == (2048, 4096)
    assert digest(prepared) == before


def test_global_budget_charges_unknowns_from_both_arms(tmp_path, monkeypatch):
    plan, _, _ = plans()
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    monkeypatch.setattr(runtime.time, "time", lambda: 940.)
    journals(tmp_path, plan)
    control, extended = plan["ordered_jobs"][:2]
    runtime.reserve(plan, "job", "I0", job=GenerationJob(**control["job"]), session_id="S0")
    with pytest.raises(ValueError, match="alternating pair order"):
        runtime.reserve(plan, "job", "I0", job=GenerationJob(**extended["job"]), session_id="S0")
    # Feed the accounting reducer a second unresolved arm reservation directly;
    # the admission check above independently prevents out-of-order live work.
    write(tmp_path / "ledger/reservations/A1.json", {"id": "A1", "plan_sha256": digest(plan),
          "invocation_id": "I0", "kind": "job", "started_at": 940., "reserved_tokens": 4610,
          "reserved_seconds": 600., "job_id": extended["job"]["id"], "session_id": "S0",
          "arm": extended["arm"], "cell_index": extended["cell_index"]})
    tally = runtime.usage(plan)
    assert tally["charged_tokens"] == 2562 + 4610
    assert tally["charged_seconds"] == 5 + 1200 and tally["unresolved"] == 2
    with pytest.raises(ValueError, match="retry"):
        runtime.reserve(plan, "job", "I0", job=GenerationJob(**control["job"]), session_id="S0")
    monkeypatch.setattr(runtime, "SPEC", runtime.SPEC | {"global_tokens": 8000})
    with pytest.raises(runtime.orig.BudgetExhausted):
        runtime.reserve(plan, "job", "I0", job=GenerationJob(**plan["ordered_jobs"][2]["job"]), session_id="S0")


def test_partial_or_divergent_prefix_endpoint_never_reaches_references(tmp_path, monkeypatch):
    plan, _, snapshot = plans()
    rows, _ = rows_and_scores(plan)
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    monkeypatch.setattr(runtime, "usage", lambda _: {"unresolved": 0, "charged_tokens": 180,
          "budget_seconds": 1.})
    monkeypatch.setattr(runtime, "terminal_unknowns", lambda _: 0)
    monkeypatch.setattr(runtime, "live_wall_seconds", lambda: 1.)
    monkeypatch.setattr(runtime, "read_plan", lambda **_: (plan, {}, snapshot))
    monkeypatch.setattr(runtime, "all_collectors_exited", lambda *args: 1)
    monkeypatch.setattr(runtime, "authenticate_finalizer", lambda: (plan, {}, snapshot))
    monkeypatch.setattr(runtime, "selected_gold", lambda *args: pytest.fail("reference access"))
    write(tmp_path / "finalize-request.json", {"launch_id": "L0"})
    for candidate in (rows[:-1], deepcopy(rows)):
        if len(candidate) == 36:
            candidate[1]["result"]["metadata"]["reasoning_token_ids"][0] = 99
        monkeypatch.setattr(runtime, "completed_rows", lambda _, candidate=candidate: candidate)
        with pytest.raises(ValueError, match="incomplete|diverged"):
            runtime.score_endpoint(plan, snapshot, candidate, [])
        assert not (tmp_path / "score-started.json").exists()


def test_prefix_checks_only_shared_reasoning_and_full_pair_coverage():
    plan, _, _ = plans()
    rows, _ = rows_and_scores(plan, varying=True)
    assert len(runtime.prefix_gate(plan, rows)) == 18  # Different final answers are permitted.
    with pytest.raises(ValueError, match="36"):
        runtime.prefix_gate(plan, rows[:-1])
    duplicated = rows[:-1] + [rows[0]]
    with pytest.raises(ValueError, match="coverage"):
        runtime.prefix_gate(plan, duplicated)


def test_equal_question_math_bootstrap_and_permutation_are_reproducible():
    plan, _, _ = plans()
    rows, scores = rows_and_scores(plan, varying=True)
    report = runtime.analyze_pairs(plan, rows, scores)
    primary = report["primary_equal_11_questions"]
    assert primary["correct"]["delta"] == pytest.approx(3 / 11)
    assert report["secondary_equal_18_cells"]["correct"] == pytest.approx(10 / 18)
    assert primary["tokens"]["delta"] == 5
    assert primary["utility"]["delta"] == pytest.approx(3 / 11 - .05 * 5 / 1000)
    # Independent uniform-draw implementation: choices uses floor(U*n).
    values = [1. if int(q[1:]) < 7 else -1. for q in plan["question_ids"]]
    rng = random.Random(20261020)
    boots = [sum(values[math.floor(rng.random()*11)] for _ in range(11))/11 for _ in range(2000)]
    assert primary["correct"]["bootstrap_95_ci"] == pytest.approx(np.quantile(boots, [.025, .975]))
    reversed_rows = list(reversed(rows))
    reversed_scores = runtime._score_header(plan, reversed_rows,
        runtime.prefix_gate(plan, reversed_rows)) | {"gold_sha256": "a" * 64,
                                                   "scores": list(reversed(scores["scores"]))}
    assert runtime.analyze_pairs(plan, reversed_rows, reversed_scores) == report


def test_valid_cached_scores_cannot_reopen_gold(tmp_path, monkeypatch):
    plan, _, snapshot = plans()
    rows, scores = rows_and_scores(plan)
    pairs = runtime.prefix_gate(plan, rows)
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    write(tmp_path / "scores.numeric-v7.json", scores)
    write(tmp_path / "score-started.json", {"plan_sha256": digest(plan),
          "records_sha256": digest(rows), "pair_gate_sha256": digest(pairs),
          "selected_question_ids_sha256": digest(plan["question_ids"]), "started_at": 1000.})
    write(tmp_path / "collection-end.json", {"finished_at": 999.})
    monkeypatch.setattr(runtime, "selected_gold", lambda *args: pytest.fail("reference reopened"))
    assert runtime.score_endpoint(plan, snapshot, rows, pairs) == scores


def test_late_cached_endpoint_is_readonly_but_live_endpoint_is_blocked(monkeypatch):
    plan, _, _ = plans()
    rows, _ = rows_and_scores(plan)
    monkeypatch.setattr(runtime, "completed_rows", lambda _: rows)
    monkeypatch.setattr(runtime, "usage", lambda _: {"unresolved": 0, "charged_tokens": 180,
          "budget_seconds": 100.})
    monkeypatch.setattr(runtime, "terminal_unknowns", lambda _: 0)
    monkeypatch.setattr(runtime, "live_wall_seconds", lambda: 999999.)
    assert len(runtime.endpoint(plan, require_live=False)[0]) == 36
    with pytest.raises(runtime.orig.BudgetExhausted):
        runtime.endpoint(plan)


def test_collect_uses_prepared_arm_configs_and_loads_weights_once(tmp_path, monkeypatch):
    plan, prepared, snapshot = plans()
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    monkeypatch.setattr(runtime.time, "time", lambda: 940.)
    journals(tmp_path, plan, started=False, setup=False)
    monkeypatch.setattr(runtime, "authenticate_collector", lambda _: (plan, prepared, snapshot,
                                                                     {"launch_id": "L0"}))
    monkeypatch.setattr(runtime, "read_plan", lambda **_: (plan, prepared, snapshot))
    observed = []
    loads = []
    class Engine:
        def __init__(self, config):
            self.config = config
            self.metadata = prepared["arms"]["control_2k"]["backend_metadata"]
            self.model = None
            self.tokenizer = object()
        def load(self):
            loads.append(self.config.reasoning_tokens)
            self.model = object()
        def generate(self, question, job, deadline):
            assert self.config.to_dict() == job.identity["config"]
            observed.append((job.id, self.config.reasoning_tokens, id(self.model)))
            return result()
    original_load = runtime.load_backends
    monkeypatch.setattr(runtime, "load_backends", lambda p: original_load(p, backend_factory=Engine))
    runtime.collect("I0")
    assert loads == [2048] and len(observed) == 36
    assert [x[0] for x in observed] == [e["job"]["id"] for e in plan["ordered_jobs"]]
    assert [x[1] for x in observed] == [e["job"]["identity"]["config"]["reasoning_tokens"] for e in plan["ordered_jobs"]]
    assert len({x[2] for x in observed}) == 1
    assert runtime.usage(plan)["charged_tokens"] == 36 * 5
    assert len(runtime.completed_rows(plan)) == 36
