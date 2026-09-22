from pathlib import Path

import numpy as np
import pytest
import yaml

from reasoning_budget.backend import FakeBackend
from reasoning_budget.data import load_questions, save_dataset
from reasoning_budget.learnability import (
    freeze_models,
    load_observations,
    prepare,
    read_protocol,
    run_study,
)
from reasoning_budget.records import Question
from reasoning_budget.storage import atomic_json, envelope, read_json, verified


@pytest.fixture
def study(tmp_path):
    questions = [
        Question(f"q{i}", "fixture", split, f"Compute the unique expression {i} plus 1.")
        for i, split in enumerate(["train"] * 60 + ["validation"] * 110 + ["test"] * 5)
    ]
    save_dataset(
        tmp_path / "source", questions, {q.id: str(int(q.id[1:]) % 3) for q in questions}, {}
    )
    config = {
        "name": "test",
        "backend": "fake",
        "data_dir": str(tmp_path / "source"),
        "output_dir": str(tmp_path / "runs"),
        "answer_tokens": 512,
        "reasoning_tokens": 2048,
        "model": {"device": "cpu", "dtype": "float32"},
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.safe_dump(config))
    return prepare(path, tmp_path / "study")


def test_protocol_disjoint_frozen_and_audit_waiver(study):
    protocol = read_protocol(study)
    ids = [q["id"] for rows in protocol["groups"].values() for q in rows]
    assert len(ids) == len(set(ids)) == 150
    assert all(q["split"] != "test" for rows in protocol["groups"].values() for q in rows)
    assert protocol["audit"]["status"] == "waived_by_user"
    assert protocol["audit"]["review_completed"] is False
    for role, rows in protocol["groups"].items():
        assert [q.to_dict() for q in load_questions(study / "data" / role)] == rows
    protocol["implementation"] = "changed"
    atomic_json(study / "protocol.json", envelope(protocol))
    with pytest.raises(ValueError, match="implementation"):
        read_protocol(study)


def test_official_test_observations_rejected(monkeypatch):
    monkeypatch.setattr(
        "reasoning_budget.learnability.load_run",
        lambda _: ({"identity": {"config": {"split": "test"}}}, []),
    )
    with pytest.raises(ValueError, match="train/validation"):
        load_observations("ignored", [], "test")


def test_full_fake_workflow_freezes_before_holdout_and_resumes_without_generation(
    study, monkeypatch
):
    calls = []

    class ConfidentFake(FakeBackend):
        def generate(self, question, job, deadline):
            if "diagnostic" in self.config.name:
                assert (study / "models.json").exists()
            calls.append(job.id)
            result = super().generate(question, job, deadline)
            result.mean_generated_logprob = -0.2 if job.mode == "direct" else None
            return result

    monkeypatch.setattr("reasoning_budget.backend.make_backend", ConfidentFake)

    def features(questions, **kwargs):
        x = np.array([[int(q.id[1:]), len(q.prompt), int(q.id[1:]) % 5] for q in questions], float)
        return x, {"synthetic": True}

    monkeypatch.setattr("reasoning_budget.learnability.feature_matrix", features)
    run_study(study, progress=lambda _: None)
    assert len(calls) == len(set(calls)) == 500
    assert read_json(study / "status.json")["status"] == "complete"
    models = (study / "models.json").read_bytes()
    report = verified(study / "report.json")
    assert len(report["question_ids"]) == 50
    assert len(verified(study / "models.json")["models"]) == 8
    freeze_models(study, progress=lambda _: None)
    assert (study / "models.json").read_bytes() == models
    run_study(study, progress=lambda _: None)
    assert len(calls) == 500
    assert (study / "models.json").read_bytes() == models
    runs = verified(study / "runs.json")
    assert all(Path(path).exists() for path in runs.values())
    # Corrupting a score dependency must not silently reuse a previously fitted checkpoint.
    path = Path(runs["train"]) / "scores.json"
    scoring = read_json(path)
    scoring["records_sha256"] = "corrupt"
    atomic_json(path, scoring)
    with pytest.raises(ValueError, match="Stale"):
        freeze_models(study)
