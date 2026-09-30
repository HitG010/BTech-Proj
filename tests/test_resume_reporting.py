import math
from pathlib import Path

import numpy as np
import pytest

from reasoning_budget import runner
from reasoning_budget.backend import GENERATION_PROTOCOL, FakeBackend
from reasoning_budget.config import from_dict
from reasoning_budget.data import prepare_fixtures
from reasoning_budget.reporting import bootstrap, paired_statistics, report, score_run, scores_path
from reasoning_budget.runner import _usage, build_jobs, load_run, manifest_implementation, run
from reasoning_budget.scoring import SCORING_VERSION
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, run_lock, verified


@pytest.fixture
def config(tmp_path):
    prepare_fixtures(tmp_path / "data")
    return from_dict(
        {
            "backend": "fake",
            "data_dir": str(tmp_path / "data"),
            "output_dir": str(tmp_path / "runs"),
            "model": {"device": "cpu", "dtype": "float32"},
        }
    )


class CountingBackend(FakeBackend):
    def __init__(self, config, interrupt_after=None):
        super().__init__(config)
        self.calls = 0
        self.interrupt_after = interrupt_after

    def generate(self, question, job, deadline):
        if self.calls == self.interrupt_after:
            raise KeyboardInterrupt
        self.calls += 1
        return super().generate(question, job, deadline)


def test_interrupt_resume_skips_completed_and_retries_failed(config):
    b = CountingBackend(config, interrupt_after=3)
    directory = run(config, b, progress=lambda _: None)
    original = {
        p.name: p.read_bytes()
        for p in (directory / "results").glob("*.json")
        if read_json(p)["payload"]["status"] == "completed"
    }
    assert len(original) == 3
    b2 = CountingBackend(config)
    assert run(config, b2, progress=lambda _: None) == directory
    assert b2.calls == 17
    assert all(
        (directory / "results" / name).read_bytes() == value for name, value in original.items()
    )
    b3 = CountingBackend(config)
    run(config, b3, progress=lambda _: None)
    assert b3.calls == 0
    assert len(list((directory / "attempts").glob("*.json"))) == 21
    assert all(r["status"] == "completed" for r in load_run(directory)[1])


def test_corrupt_result_and_incomplete_temp_retried_only_once(config):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    damaged = next((directory / "results").glob("*.json"))
    damaged.write_text('{"incomplete":')
    (directory / "results/.partial.tmp").write_text("partial")
    b = CountingBackend(config)
    run(config, b, progress=lambda _: None)
    assert b.calls == 1
    assert len(load_run(directory)[1]) == 20


def test_configuration_change_has_distinct_identity(config):
    first = run(config, CountingBackend(config), progress=lambda _: None)
    config.direct.top_p = 0.7
    second = run(config, CountingBackend(config), progress=lambda _: None)
    assert first != second


def test_token_budget_reserved_before_work_and_persists(config):
    config.limits.max_tokens = 256
    b = CountingBackend(config)
    directory = run(config, b, progress=lambda _: None)
    assert b.calls == 1  # First thinking job cannot reserve its maximum allowance.
    b2 = CountingBackend(config)
    run(config, b2, progress=lambda _: None)
    assert b2.calls == 0
    assert _usage(directory)[0] == 5


def test_corrupt_budget_ledger_fails_closed(config):
    directory = run(config, CountingBackend(config, interrupt_after=1), progress=lambda _: None)
    next((directory / "attempts").glob("*.json")).write_text("{}")
    with pytest.raises((ValueError, KeyError)):
        run(config, CountingBackend(config), progress=lambda _: None)


def test_unfinished_reservation_is_not_free(config):
    directory = run(config, CountingBackend(config, interrupt_after=0), progress=lambda _: None)
    assert _usage(directory)[0] == 256
    path = directory / "attempts/killed.json"
    atomic_json(path, envelope({"reserved_tokens": 1000, "reserved_seconds": 12}))
    assert _usage(directory)[0] == 1256
    assert _usage(directory)[1] >= 12


def test_atomic_writes_and_exclusive_lock(tmp_path):
    atomic_json(tmp_path / "a.json", {"a": 1})
    assert read_json(tmp_path / "a.json") == {"a": 1}
    assert not list(tmp_path.glob("*.tmp"))
    with run_lock(tmp_path):
        with pytest.raises(ValueError, match="lock"):
            with run_lock(tmp_path):
                pass


def test_generation_has_no_gold_access(config):
    Path(config.data_dir, "gold.json").unlink()
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    assert len(load_run(directory)[1]) == 20
    with pytest.raises(FileNotFoundError):
        score_run(directory)


def test_scoring_rejects_replaced_gold_even_if_dataset_manifest_changes(config):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    data = Path(config.data_dir)
    gold = read_json(data / "gold.json")
    gold["arithmetic-00"] = "999"
    manifest = read_json(data / "manifest.json")
    manifest["gold_sha256"] = digest(gold)
    atomic_json(data / "gold.json", gold)
    atomic_json(data / "manifest.json", manifest)
    with pytest.raises(ValueError, match="scoring reference"):
        score_run(directory)


def test_generation_seeds_are_independent_of_question_order(config):
    from reasoning_budget.data import load_questions

    questions = load_questions(config.data_dir)
    metadata = CountingBackend(config).metadata
    forward = build_jobs(config, questions, metadata)
    reverse = build_jobs(config, questions[::-1], metadata)
    assert {j.id: j.seed for j in forward} == {j.id: j.seed for j in reverse}
    assert len({j.seed for j in forward}) == len(forward)
    revised = build_jobs(config, questions, metadata | {"model_revision": "fake-v2"})
    assert {j.id for j in forward}.isdisjoint({j.id for j in revised})


def test_expended_elapsed_budget_prevents_generation(config):
    directory = run(config, CountingBackend(config, interrupt_after=0), progress=lambda _: None)
    atomic_json(directory / "sessions/expended.json", envelope({"setup_seconds": 3600}))
    b = CountingBackend(config)
    run(config, b, progress=lambda _: None)
    assert b.calls == 0


def test_timeout_is_explicit_failure_and_can_resume(config):
    class TimeoutBackend(CountingBackend):
        def generate(self, question, job, deadline):
            result = super().generate(question, job, deadline)
            result.termination = "timeout"
            return result

    directory = run(config, TimeoutBackend(config), progress=lambda _: None)
    statuses = [r["status"] for r in load_run(directory)[1]]
    assert statuses[:3] == ["failed"] * 3 and set(statuses[3:]) == {"pending"}
    assert read_json(directory / "status.json")["stop_reason"] == "consecutive_failures"
    b = CountingBackend(config)
    run(config, b, progress=lambda _: None)
    assert b.calls == 20


def test_isolated_failure_continues_and_only_failed_job_is_retried(config):
    class FlakyBackend(CountingBackend):
        def generate(self, question, job, deadline):
            result = super().generate(question, job, deadline)
            if self.calls == 2:
                result.termination = "timeout"
            return result

    directory = run(config, FlakyBackend(config), progress=lambda _: None)
    statuses = [r["status"] for r in load_run(directory)[1]]
    assert statuses.count("completed") == 19 and statuses.count("failed") == 1
    assert read_json(directory / "status.json")["stop_reason"] == "finished_with_failures"
    backend = CountingBackend(config)
    run(config, backend, progress=lambda _: None)
    assert backend.calls == 1


def test_success_resets_consecutive_failure_count(config):
    class AlternatingBackend(CountingBackend):
        def generate(self, question, job, deadline):
            result = super().generate(question, job, deadline)
            if self.calls % 2:
                result.termination = "timeout"
            return result

    backend = AlternatingBackend(config)
    directory = run(config, backend, progress=lambda _: None)
    assert backend.calls == 20
    assert read_json(directory / "status.json")["stop_reason"] == "finished_with_failures"


def test_identity_versions_protocol_but_tracks_code_per_session(config, monkeypatch):
    monkeypatch.setattr(runner, "implementation_digest", lambda: "a" * 64)
    directory = run(config, CountingBackend(config, interrupt_after=2), progress=lambda _: None)
    manifest = verified(directory / "manifest.json")
    assert manifest["schema_version"] == 2
    assert manifest["identity"]["protocol_version"] == GENERATION_PROTOCOL
    assert "implementation_sha256" not in manifest["identity"]
    assert manifest_implementation(manifest) == "a" * 64
    assert all(j["identity"]["protocol_version"] == GENERATION_PROTOCOL for j in manifest["jobs"])
    monkeypatch.setattr(runner, "implementation_digest", lambda: "b" * 64)
    backend = CountingBackend(config)
    assert run(config, backend, progress=lambda _: None) == directory
    assert backend.calls == 18
    sessions = [verified(p) for p in (directory / "sessions").glob("*.json")]
    assert {s["implementation_sha256"] for s in sessions} == {"a" * 64, "b" * 64}
    by_session = {s["session_id"]: s for s in sessions}
    records = load_run(directory)[1]
    assert sum(r["implementation_sha256"] == "a" * 64 for r in records) == 2
    assert sum(r["implementation_sha256"] == "b" * 64 for r in records) == 18
    for record in records:
        assert record["implementation_sha256"] == by_session[record["session_id"]][
            "implementation_sha256"
        ]
    for path in (directory / "attempts").glob("*.json"):
        attempt = verified(path)
        assert attempt["implementation_sha256"] == by_session[attempt["session_id"]][
            "implementation_sha256"
        ]
    with pytest.raises(ValueError, match="different generation implementation"):
        runner.require_implementation(manifest, records, "a" * 64)
    monkeypatch.setattr(runner, "GENERATION_PROTOCOL", "different-protocol")
    changed = run(config, CountingBackend(config), progress=lambda _: None)
    assert changed != directory
    assert {j["id"] for j in verified(changed / "manifest.json")["jobs"]}.isdisjoint(
        {j["id"] for j in manifest["jobs"]}
    )


def test_response_with_mismatched_session_provenance_is_rejected(config):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    path = next((directory / "results").glob("*.json"))
    record = verified(path)
    record["implementation_sha256"] = "0" * 64
    atomic_json(path, envelope(record))
    assert sum(r["status"] == "pending" for r in load_run(directory)[1]) == 1
    backend = CountingBackend(config)
    run(config, backend, progress=lambda _: None)
    assert backend.calls == 1


def test_setup_is_reserved_before_load_and_killed_setup_cannot_be_free(config):
    class ObserveSetup(CountingBackend):
        def load(self):
            session_path = next((directory / "sessions").glob("*.json"))
            session = verified(session_path)
            assert session["status"] == "setup_started"
            assert "setup_seconds" not in session
            assert _usage(directory)[1] == config.limits.max_elapsed_seconds
            super().load()

    from reasoning_budget.backend import environment
    from reasoning_budget.data import load_questions

    backend = ObserveSetup(config)
    identity = runner.build_run_identity(
        config, load_questions(config.data_dir, config.split), backend.metadata, environment()
    )
    directory = Path(config.output_dir) / digest(identity)[:20]
    run(config, backend, progress=lambda _: None)
    # Emulate a hard kill: the durable pre-load session lacks a final duration.
    session_path = next((directory / "sessions").glob("*.json"))
    session = verified(session_path)
    session.pop("setup_seconds")
    session["status"] = "setup_started"
    atomic_json(session_path, envelope(session))
    resumed = CountingBackend(config)
    run(config, resumed, progress=lambda _: None)
    assert resumed.calls == 0
    assert _usage(directory)[1] >= config.limits.max_elapsed_seconds


def test_incremental_tally_matches_disk_and_scans_once_per_invocation(config, monkeypatch):
    calls = []

    def tally(directory):
        calls.append(directory)
        return _usage(directory)

    monkeypatch.setattr(runner, "_usage", tally)
    directory = run(config, CountingBackend(config, interrupt_after=5), progress=lambda _: None)
    run(config, CountingBackend(config), progress=lambda _: None)
    assert len(calls) == 2
    status = read_json(directory / "status.json")
    tokens, elapsed = _usage(directory)
    assert status["charged_tokens"] == tokens
    assert math.isclose(status["elapsed_seconds"], elapsed, rel_tol=1e-9)


@pytest.mark.parametrize("tokens,seconds", [(-1, 1), (True, 1), (257, 1), (0, -1)])
def test_invalid_but_checksummed_ledger_cannot_release_budget(config, tokens, seconds):
    directory = run(config, CountingBackend(config, interrupt_after=0), progress=lambda _: None)
    path = next((directory / "attempts").glob("*.json"))
    attempt = verified(path)
    attempt.update(charged_tokens=tokens, elapsed_seconds=seconds)
    atomic_json(path, envelope(attempt))
    backend = CountingBackend(config)
    with pytest.raises(ValueError, match="budget ledger"):
        run(config, backend, progress=lambda _: None)
    assert backend.calls == 0


def test_score_new_version_preserves_legacy_cache_and_does_not_rewrite_hits(config):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    original = {"scoring_version": "numeric-v4", "historical": "preserve exactly"}
    atomic_json(directory / "scores.json", original)
    previous_bytes = (directory / "scores.json").read_bytes()
    artifact = score_run(directory)
    path = directory / f"scores.{SCORING_VERSION}.json"
    assert scores_path(directory) == path
    assert read_json(path) == artifact
    assert artifact["scoring_version"] == SCORING_VERSION
    assert len(artifact["scoring_implementation_sha256"]) == 64
    assert (directory / "scores.json").read_bytes() == previous_bytes
    modified = path.stat().st_mtime_ns
    assert score_run(directory) == artifact
    assert path.stat().st_mtime_ns == modified


def test_same_name_different_scorer_cannot_overwrite_existing_scores(config):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    artifact = score_run(directory)
    artifact["scoring_implementation_sha256"] = "different"
    atomic_json(scores_path(directory), artifact)
    previous = scores_path(directory).read_bytes()
    with pytest.raises(ValueError, match="new scoring version"):
        score_run(directory)
    assert scores_path(directory).read_bytes() == previous


def test_new_report_preserves_report_without_scorer_provenance(config, monkeypatch):
    directory = run(config, CountingBackend(config), progress=lambda _: None)
    original = directory / "report" / "summary.json"
    atomic_json(original, {"historical": "leave unchanged"})
    old_bytes = original.read_bytes()
    monkeypatch.setattr("reasoning_budget.reporting._plot", lambda *_args: None)
    output = report(directory)
    assert output == directory / f"report.{SCORING_VERSION}"
    assert original.read_bytes() == old_bytes
    assert read_json(output / "summary.json")["scoring_version"] == SCORING_VERSION


def test_audit_rejects_duplicate_and_stale_reviews(config):
    from reasoning_budget.reporting import audit_status, create_audit

    directory = run(config, CountingBackend(config), progress=lambda _: None)
    create_audit(directory, count=20)
    audit = read_json(directory / "audit.json")
    audit["reviewer"] = "Test fixture"
    for row in audit["rows"]:
        row.update(review="model_failure", notes="Synthetic response is zero.")
    audit["rows"] *= 3
    atomic_json(directory / "audit.json", audit)
    manifest, records = load_run(directory)
    scores = score_run(directory)["scores"]
    status = audit_status(directory, manifest, records, scores)
    assert status["verified_reviews"] == 20
    assert not status["accepted"]
    audit["rows"][0]["record_sha256"] = "changed"
    atomic_json(directory / "audit.json", audit)
    assert audit_status(directory, manifest, records, scores)["verified_reviews"] == 19


def test_whole_question_paired_bootstrap_excludes_partial_questions():
    records, scores = [], []
    for q in range(3):
        for mode in ["direct", "thinking"]:
            for sample in range(2):
                job = {"id": f"{q}-{mode}-{sample}", "question_id": str(q), "mode": mode}
                records.append(
                    {
                        "job": job,
                        "status": "pending" if q == 2 and mode == "direct" else "completed",
                    }
                )
                scores.append({"job_id": job["id"], "correct": mode == "thinking"})
    stats = paired_statistics(records, scores, samples=2, seed=123)
    assert stats["questions"] == 2
    assert stats["thinking_minus_direct_accuracy"] == 1
    assert stats["ci95"] == [1, 1]
    assert bootstrap([0, 1], seed=42) == bootstrap(np.array([0, 1]), seed=42)
