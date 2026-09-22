from dataclasses import replace
from pathlib import Path

import pytest

from reasoning_budget.calibration import (
    _headroom,
    confirm_pilot,
    confirmation_report,
    create_study_audit,
    prepare,
    report_study,
    run_study,
    select_questions,
)
from reasoning_budget.config import from_dict
from reasoning_budget.data import FIXTURES, load_questions, save_dataset
from reasoning_budget.records import Question
from reasoning_budget.runner import build_jobs, load_run, run
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, verified


@pytest.fixture
def baseline(tmp_path):
    questions = [
        Question(f"q-{i}", "fixture", "pilot", prompt) for i, (prompt, _) in enumerate(FIXTURES)
    ]
    data = tmp_path / "data"
    save_dataset(data, questions, {q.id: FIXTURES[i][1] for i, q in enumerate(questions)}, {})
    config = from_dict(
        {
            "backend": "fake",
            "data_dir": str(data),
            "split": "pilot",
            "samples": 2,
            "output_dir": str(tmp_path / "runs"),
            "model": {"device": "cpu", "dtype": "float32"},
        }
    )
    return run(config, progress=lambda _: None)


def test_selection_is_order_independent_and_preserves_questions():
    questions = [Question(str(i), "fixture", "pilot", f"Question {i}") for i in range(30)]
    first = select_questions(questions, 25, 42)
    assert first == select_questions(questions[::-1], 25, 42)
    assert len({q.id for q in first}) == 25
    assert set(first).issubset(set(questions))
    assert first != select_questions(questions, 25, 43)
    assert set(first).isdisjoint({replace(q, split="test") for q in first})
    with pytest.raises(ValueError, match="count"):
        select_questions(questions, 31, 42)


def test_frozen_selection_seeds_and_immutable_baseline(baseline, tmp_path):
    before = {str(p): p.read_bytes() for p in baseline.rglob("*.json")}
    study_dir = prepare(baseline, tmp_path / "study", count=5)
    study = verified(study_dir / "study.json")
    manifest, records = load_run(baseline)
    selected = load_questions(study_dir / "data")
    assert selected == select_questions(
        [Question(**q) for q in manifest["identity"]["questions"]], 5, 20260914
    )
    for values in study["configs"].values():
        jobs = build_jobs(from_dict(values), selected, manifest["identity"]["backend"])
        original = {
            (r["job"]["question_id"], r["job"]["mode"], r["job"]["sample"]): r["job"]["seed"]
            for r in records
        }
        assert all(j.seed == original[(j.question_id, j.mode, j.sample)] for j in jobs)
    assert prepare(baseline, study_dir, count=5) == study_dir
    with pytest.raises(ValueError, match="already frozen"):
        prepare(baseline, study_dir, count=4)
    run_study(study_dir, progress=lambda _: None)
    summary = read_json(report_study(study_dir) / "summary.json")
    assert summary["complete"]
    assert len(summary["modes"]) == 6
    assert all(row["completed"] == 10 for row in summary["modes"])
    assert all(row["complete_questions"] == 5 for row in summary["paired_cap_comparisons"])
    assert summary["human_review_status"] == "pending"
    assert {str(p): p.read_bytes() for p in baseline.rglob("*.json")} == before
    state = verified(study_dir / "runs.json")
    attempts = {
        cap: len(list(Path(path, "attempts").glob("*.json"))) for cap, path in state.items()
    }
    run_study(study_dir, progress=lambda _: None)
    assert all(
        len(list(Path(path, "attempts").glob("*.json"))) == attempts[cap]
        for cap, path in state.items()
    )
    audit = read_json(create_study_audit(study_dir, count=12))
    assert audit["status"] == "pending"
    assert len(audit["rows"]) == 12
    assert all(row["review"] == "pending" for row in audit["rows"])
    assert len({row["job_id"] for row in audit["rows"]}) == 12
    with pytest.raises(ValueError, match="already exists"):
        create_study_audit(study_dir)


def test_partial_report_does_not_claim_completeness(baseline, tmp_path):
    directory = prepare(baseline, tmp_path / "study", count=5)
    summary = read_json(report_study(directory) / "summary.json")
    assert not summary["complete"]
    assert set(summary["arms"]) == {"256"}
    assert all(row["planned"] == 10 for row in summary["modes"])
    with pytest.raises(ValueError, match="Finish all"):
        create_study_audit(directory)


def test_backend_change_rejected_before_generation(baseline, tmp_path, monkeypatch):
    from reasoning_budget import backend

    directory = prepare(baseline, tmp_path / "study", count=5)
    original = backend.make_backend

    def changed(config):
        b = original(config)
        b.metadata["model_revision"] = "different"
        b.load = lambda: pytest.fail("Must reject before model loading")
        return b

    monkeypatch.setattr(backend, "make_backend", changed)
    with pytest.raises(ValueError, match="changed backend"):
        run_study(directory)
    assert not (directory / "runs.json").exists()


def test_report_rejects_an_unmatched_arm(baseline, tmp_path):
    directory = prepare(baseline, tmp_path / "study", count=5)
    atomic_json(directory / "runs.json", envelope({"512": str(baseline)}))
    with pytest.raises(ValueError, match="configuration differs"):
        report_study(directory)


def test_confirmation_separates_selection_questions(baseline, tmp_path):
    directory = prepare(baseline, tmp_path / "study", count=5)
    study = verified(directory / "study.json")
    manifest, _ = load_run(baseline)
    config = from_dict(manifest["identity"]["config"] | {"answer_tokens": 512})
    decision = {
        "calibration_study_sha256": digest(study),
        "chosen_config": config.to_dict(),
        "chosen_config_sha256": digest(config.to_dict()),
    }
    atomic_json(directory / "protocol-decision.json", envelope(decision))
    path = run(config, progress=lambda _: None)
    summary = read_json(confirmation_report(directory, path) / "calibration-confirmation.json")
    groups = summary["groups"]
    assert groups["all_pilot"]["planned_questions"] == 10
    assert groups["used_for_cap_selection"]["planned_questions"] == 5
    assert groups["not_used_for_cap_selection"]["planned_questions"] == 5
    assert all(v["complete"] for v in groups.values())
    assert summary["human_review_status"] == "pending"
    with pytest.raises(ValueError, match="full 100-question"):
        confirm_pilot(directory)
    with pytest.raises(ValueError, match="frozen configuration"):
        confirmation_report(directory, baseline)


def test_confirmation_rejects_test_split_before_inference(baseline, tmp_path):
    directory = prepare(baseline, tmp_path / "study", count=5)
    study = verified(directory / "study.json")
    config = study["configs"]["512"] | {"split": "test"}
    atomic_json(
        directory / "protocol-decision.json",
        envelope(
            {
                "calibration_study_sha256": digest(study),
                "chosen_config": config,
                "chosen_config_sha256": digest(config),
            }
        ),
    )
    with pytest.raises(ValueError, match="pilot questions"):
        confirm_pilot(directory)


def test_retrospective_cost_uses_cheaper_ties_and_excludes_partial_questions():
    records, scores = [], []
    for question in range(3):
        for mode in ["direct", "thinking"]:
            for sample in range(2):
                job = {
                    "id": f"{question}-{mode}-{sample}",
                    "question_id": str(question),
                    "mode": mode,
                }
                records.append(
                    {
                        "job": job,
                        "status": "pending"
                        if question == 2 and mode == "thinking"
                        else "completed",
                        "result": {
                            "reasoning_tokens": 0 if mode == "direct" else 900,
                            "answer_tokens": 100,
                            "inserted_tokens": 0,
                        },
                    }
                )
                scores.append({"job_id": job["id"], "correct": question == 0 or mode == "thinking"})
    result = _headroom(records, scores, samples=2)
    assert result["complete_questions"] == 2
    assert result["retrospective_sample_estimated_oracle_accuracy"] == 1
    assert result["retrospective_direct_choices"] == 1
    assert result["retrospective_mean_charged_tokens"] == 550
    assert result["always_thinking_mean_charged_tokens"] == 1000
