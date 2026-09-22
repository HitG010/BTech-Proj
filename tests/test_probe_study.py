from pathlib import Path

import numpy as np
import pytest
import yaml

from reasoning_budget.backend import FakeBackend
from reasoning_budget.config import from_dict
from reasoning_budget.data import save_dataset
from reasoning_budget.probe_study import (
    freeze_models,
    prepare,
    read_protocol,
    read_sources,
    run_study,
)
from reasoning_budget.records import Question
from reasoning_budget.reporting import score_run
from reasoning_budget.runner import run
from reasoning_budget.storage import atomic_json, envelope, read_json, verified


class ConfidentFake(FakeBackend):
    def generate(self, question, job, deadline):
        result = super().generate(question, job, deadline)
        result.mean_generated_logprob = -0.2 if job.mode == "direct" else None
        return result


@pytest.fixture
def study(tmp_path, monkeypatch):
    all_questions = [
        Question(f"q{i}", "fixture", split, f"Unique arithmetic question {i} plus 3")
        for i, split in enumerate(
            ["pilot"] * 10 + ["validation"] * 8 + ["train"] * 12 + ["test"] * 2
        )
    ]
    gold = {q.id: "0" for q in all_questions}
    save_dataset(tmp_path / "data", all_questions, gold, {})
    config = {
        "name": "fixture",
        "backend": "fake",
        "data_dir": str(tmp_path / "data"),
        "output_dir": str(tmp_path / "runs"),
        "samples": 2,
        "answer_tokens": 512,
        "reasoning_tokens": 2048,
        "model": {"device": "cpu", "dtype": "float32"},
    }
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump(config))
    runs = {}
    for role, questions in [
        ("pilot", all_questions[:10]),
        ("tune", all_questions[10:14]),
        ("diagnostic", all_questions[14:18]),
    ]:
        save_dataset(tmp_path / role, questions, {q.id: gold[q.id] for q in questions}, {})
        c = from_dict(
            config | {"name": role, "data_dir": str(tmp_path / role), "split": questions[0].split}
        )
        runs[role] = str(run(c, ConfidentFake(c), progress=lambda _: None))
        score_run(runs[role])
    old = tmp_path / "old"
    atomic_json(
        old / "protocol.json",
        envelope(
            {
                "groups": {"train": [q.to_dict() for q in all_questions[18:20]]},
                "audit": {"status": "waived_by_user", "review_completed": False},
            }
        ),
    )
    atomic_json(old / "runs.json", envelope(runs))
    path = prepare(base, tmp_path / "study", runs["pilot"], old, count=6)
    monkeypatch.setattr(
        "reasoning_budget.probe_study.feature_matrix",
        lambda questions, **kwargs: (
            np.array([[len(q.prompt), int(q.id[1:]) % 5, int(q.id[1:])] for q in questions]),
            {},
        ),
    )
    return path


def test_fresh_allocation_and_frozen_sources(study):
    protocol = read_protocol(study)
    ids = {q["id"] for q in protocol["diagnostic"]}
    assert len(ids) == 6 and not ids.intersection(protocol["excluded_ids"])
    assert all(q["split"] == "train" for q in protocol["diagnostic"])
    saved = freeze_models(study, progress=lambda _: None)
    assert saved["diagnostic_used_for_fitting"] is False
    assert len(saved["models"]) == 3
    assert freeze_models(study, progress=lambda _: None) == saved
    score_path = Path(protocol["source_paths"]["train"][0]) / "scores.json"
    artifact = read_json(score_path)
    artifact["records_sha256"] = "wrong"
    atomic_json(score_path, artifact)
    with pytest.raises(ValueError, match="Stale"):
        freeze_models(study)


def test_fake_fresh_pipeline_freezes_before_generation_and_resume(study, monkeypatch):
    calls = []

    class RecordingFake(ConfidentFake):
        def generate(self, question, job, deadline):
            assert (study / "models.json").exists()
            calls.append(job.id)
            return super().generate(question, job, deadline)

    monkeypatch.setattr("reasoning_budget.backend.make_backend", RecordingFake)
    run_study(study, progress=lambda _: None)
    assert len(calls) == len(set(calls)) == 30
    assert read_json(study / "status.json")["status"] == "complete"
    models = (study / "models.json").read_bytes()
    report = verified(study / "report.json")
    assert len(report["question_ids"]) == 6
    assert any(r["policy"] == "DART-SC-3-adapted" for r in report["summaries"])
    run_study(study, progress=lambda _: None)
    assert len(calls) == 30
    assert (study / "models.json").read_bytes() == models


def test_test_split_is_rejected_before_score_access(monkeypatch):
    monkeypatch.setattr(
        "reasoning_budget.probe_study.load_run",
        lambda _: ({"identity": {"config": {"split": "test"}}}, []),
    )
    with pytest.raises(ValueError, match="sealed"):
        read_sources(["unused"])


def test_failed_stage_resumes_without_repeating_completed_drafts(study, monkeypatch):
    calls, failed = [], []

    class FailOnce(ConfidentFake):
        def generate(self, question, job, deadline):
            calls.append((job.mode, job.id))
            if job.mode == "thinking" and not failed:
                failed.append(job.id)
                raise RuntimeError("simulated interruption")
            return super().generate(question, job, deadline)

    monkeypatch.setattr("reasoning_budget.backend.make_backend", FailOnce)
    run_study(study, progress=lambda _: None)
    assert read_json(study / "status.json")["status"] == "paused"
    frozen = (study / "models.json").read_bytes()
    run_study(study, progress=lambda _: None)
    assert read_json(study / "status.json")["status"] == "complete"
    assert len([c for c in calls if c[0] == "direct"]) == 18
    assert len(calls) == 31 and len(set(calls)) == 30
    assert (study / "models.json").read_bytes() == frozen
