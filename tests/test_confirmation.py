import copy
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest
from scipy.stats import ttest_1samp

from reasoning_budget import confirmation, probe
from reasoning_budget.backend import FakeBackend
from reasoning_budget.config import from_dict
from reasoning_budget.confirmation_stats import SECONDARY, analyze_policies, holm, paired_test
from reasoning_budget.controller import Controller
from reasoning_budget.data import save_dataset
from reasoning_budget.records import Question
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, verified


def test_paired_test_matches_reference_and_keeps_question_unit():
    differences = np.array([0.02, -0.04, 0.03, 0.01, 0.06])
    result = paired_test(differences, draws=256)
    reference = ttest_1samp(differences, 0)
    assert result["p_two_sided"] == pytest.approx(reference.pvalue)
    assert result["t_statistic"] == pytest.approx(reference.statistic)
    assert result["n_questions"] == 5
    assert result == paired_test(differences, draws=256)
    assert paired_test(np.zeros(5), draws=20)["p_two_sided"] == 1
    assert paired_test(np.ones(5), draws=20)["t_statistic"] is None
    with pytest.raises(ValueError):
        paired_test(np.ones((5, 2)))


def test_holm_preserves_original_order_and_primary_gate():
    assert holm([0.03, 0.001, 0.04, 0.02]) == pytest.approx([0.06, 0.004, 0.06, 0.06])
    base = np.column_stack([np.full(20, 0.5), np.full(20, 100), np.ones(20)])
    candidate = base.copy()
    candidate[:, 0] += np.linspace(0.05, 0.1, 20)
    policies = {name: base for name in SECONDARY}
    policies.update(joint=candidate, **{"confidence-continuation": base})
    result = analyze_policies(policies)
    assert result["primary"]["positive_superiority"]
    assert all(r["positive_superiority"] for r in result["secondary"].values())
    policies["confidence-continuation"] = candidate.copy()
    result = analyze_policies(policies)
    assert not result["primary"]["positive_superiority"]
    assert not any(r["positive_superiority"] for r in result["secondary"].values())


def test_selection_excludes_normalized_duplicates_and_is_deterministic():
    excluded = [Question("reserved", "fixture", "test", "HELLO world").to_dict()]
    prompts = [" hello  WORLD ", *[f"unique {i}" for i in range(10)], "unique 0"]
    chosen, pool = confirmation.select_fresh(prompts, excluded, 6)
    assert pool == 10
    assert [q.to_dict() for _, q in chosen] == [
        q.to_dict() for _, q in confirmation.select_fresh(list(reversed(prompts)), excluded, 6)[0]
    ]
    assert len({q.id for _, q in chosen}) == 6
    with pytest.raises(ValueError, match="Insufficient"):
        confirmation.select_fresh(prompts, excluded, 11)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    artifacts, parent, cache = tmp_path / "artifacts", tmp_path / "parent", tmp_path / "cache"
    data = artifacts / "data"
    excluded = [
        Question("q0", "fixture", "train", "Reserved question 0"),
        Question("q1", "fixture", "test", "Reserved question 1"),
    ]
    save_dataset(data, excluded, {q.id: "0" for q in excluded}, {"revision": "fixture-revision"})
    arrow = cache / "openai___gsm8k/main/0.0.0/fixture-revision/gsm8k-train.arrow"
    arrow.parent.mkdir(parents=True)
    table = pa.table(
        {
            "question": [q.prompt for q in excluded]
            + [f"New unique question {i}" for i in range(10)],
            "answer": ["must not score excluded answers"] * 2 + ["#### 0"] * 10,
        }
    )
    with pa.OSFile(str(arrow), "wb") as sink, pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    configs = {}
    for mode in ("direct", "thinking"):
        configs[mode] = from_dict(
            {
                "backend": "fake",
                "name": mode,
                "split": "train",
                "modes": [mode],
                "answer_tokens": 512,
                "model": {"device": "cpu", "dtype": "float32"},
            }
        ).to_dict()
    prior = {
        "configs": configs,
        "excluded_ids": [q.id for q in excluded],
        "diagnostic": [],
        "audit": {"status": "waived_by_user", "review_completed": False},
        "baseline_scope": "fixture",
    }
    monkeypatch.setattr(confirmation, "read_parent", lambda path: prior)
    x = np.random.default_rng(10).normal(size=(8, 7))
    rows = np.ones((4, 2, 3, 3))
    rows[:, :, :, 1] = [2, 5, 10]
    models = {
        "models": {
            name: {"model": probe.fit(x, rows, probe.SETTINGS[0], kind, response_only)}
            for name, kind, response_only in [
                ("joint", "joint", False),
                ("gain-ridge", "gain-ridge", False),
                ("response-only", "joint", True),
            ]
        },
        "question_ridge": Controller(
            np.zeros(3), np.ones(3), np.zeros((4, 3)), np.array([0.5, 0.7, 2, 10]), [1] * 4
        ).to_dict(),
        "thresholds": {
            "confidence-continuation": [{"threshold": -0.3, "action": 1} for _ in probe.PREFERENCES]
        },
        "frozen_at": time.time() - 10,
    }
    atomic_json(parent / "models.json", envelope(models))
    atomic_json(
        parent / "report.json",
        envelope({"protocol": digest(prior), "models_sha256": digest(models)}),
    )
    output = artifacts / "confirmation"
    confirmation.prepare(parent, output, data, artifacts, cache, count=6, batch_size=3)
    monkeypatch.setattr(
        confirmation,
        "feature_matrix",
        lambda questions, **kwargs: (
            np.array([[len(q.prompt), i, i % 2] for i, q in enumerate(questions)]),
            {},
        ),
    )
    return output, (parent, output, data, artifacts, cache)


def test_preparation_is_immutable_offline_and_never_starts_generation(prepared):
    path, args = prepared
    p = confirmation.read_protocol(path)
    assert p["sample_size"] == 6 and p["expected_responses"] == 30
    assert len(p["batches"]) == 2
    assert not (path / "runs.json").exists()
    assert (path / "models.json").read_bytes() == (args[0] / "models.json").read_bytes()
    frozen = (path / "protocol.json").read_bytes()
    confirmation.prepare(*args, count=6, batch_size=3)
    assert (path / "protocol.json").read_bytes() == frozen
    assert confirmation.status(path)["completed"] == 0
    with pytest.raises(ValueError, match="locked"):
        confirmation.evaluate(path)
    (path / "models.json").write_text("changed")
    with pytest.raises(ValueError, match="models changed"):
        confirmation.read_protocol(path)


def test_batched_fake_workflow_defers_scores_and_resumes_without_refitting(prepared, monkeypatch):
    path, _ = prepared
    calls = []

    class Fake(FakeBackend):
        def generate(self, question, job, deadline):
            calls.append(job.id)
            assert not (path / "report.json").exists()
            result = super().generate(question, job, deadline)
            result.mean_generated_logprob = -0.2 if job.mode == "direct" else None
            return result

    monkeypatch.setattr("reasoning_budget.backend.make_backend", Fake)

    def forbidden(*args, **kwargs):
        raise AssertionError("Confirmation must never fit a model")

    monkeypatch.setattr("reasoning_budget.probe.fit", forbidden)
    frozen = (path / "models.json").read_bytes()
    confirmation.run_study(path, progress=lambda _: None, max_batches=1)
    assert len(calls) == 15
    assert not list((path / "runs").rglob("scores.json"))
    assert confirmation.status(path)["state"]["status"] == "paused"
    with pytest.raises(ValueError, match="locked"):
        confirmation.evaluate(path)
    confirmation.run_study(path, progress=lambda _: None, max_batches=1)
    assert len(calls) == len(set(calls)) == 30
    assert read_json(path / "status.json")["status"] == "complete"
    assert (path / "models.json").read_bytes() == frozen
    result = verified(path / "report.json")
    assert result["inference"]["primary"]["n_questions"] == 6
    assert set(result["inference"]["secondary"]) == set(SECONDARY)
    confirmation.run_study(path, progress=lambda _: None)
    assert len(calls) == 30


def test_changed_dataset_manifest_rejected(prepared):
    path, _ = prepared
    protocol = confirmation.read_protocol(path)
    manifest_path = Path(protocol["batches"][0]["configs"]["direct"]["data_dir"]) / "manifest.json"
    manifest = copy.deepcopy(read_json(manifest_path))
    manifest["gold_sha256"] = "changed"
    atomic_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="manifest changed"):
        confirmation.read_protocol(path)


def test_failed_job_retried_without_repeating_completed_work(prepared, monkeypatch):
    path, _ = prepared
    calls, failures = [], []

    class FailOnce(FakeBackend):
        def generate(self, question, job, deadline):
            calls.append(job.id)
            if job.mode == "thinking" and not failures:
                failures.append(job.id)
                raise RuntimeError("simulated interrupted job")
            result = super().generate(question, job, deadline)
            result.mean_generated_logprob = -0.2 if job.mode == "direct" else None
            return result

    monkeypatch.setattr("reasoning_budget.backend.make_backend", FailOnce)
    confirmation.run_study(path, progress=lambda _: None)
    assert read_json(path / "status.json")["status"] == "paused"
    assert not list((path / "runs").rglob("scores.json"))
    confirmation.run_study(path, progress=lambda _: None)
    assert len(calls) == 31 and len(set(calls)) == 30
    assert read_json(path / "status.json")["status"] == "complete"
    late_protocol = confirmation.read_protocol(path) | {"prepared_at": time.time() + 100}
    with pytest.raises(ValueError, match="preceded"):
        confirmation.require_complete(path, late_protocol)
