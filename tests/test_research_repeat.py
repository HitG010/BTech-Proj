import copy
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest
import yaml

from reasoning_budget import backend
from reasoning_budget import research_repeat as repeat
from reasoning_budget.records import Question
from reasoning_budget.storage import atomic_json, envelope, read_json, verified


@pytest.fixture
def panel(tmp_path, monkeypatch):
    class RecordedFake(backend.FakeBackend):
        def generate(self, question, job, deadline):
            result = super().generate(question, job, deadline)
            result.mean_generated_logprob = -0.2
            return result

    monkeypatch.setattr(backend, "FakeBackend", RecordedFake)
    root = tmp_path / "research"
    arrow = tmp_path / "train.arrow"
    questions = [f"Question {i}" for i in range(20)]
    answers = ["UNSELECTED_REFERENCE_ANSWER_MUST_NOT_BE_READ"] * 20
    selected = list(range(0, 20, 2))
    for i in selected:
        answers[i] = "Worked solution. #### 0"
    table = pa.table({"question": questions, "answer": answers})
    with pa.OSFile(str(arrow), "wb") as sink, pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    allocation = {"source": {"arrow_path": str(arrow), "revision": "fixture"},
        "roles": {"repeat": [{"question": Question(f"q{i}", "fixture-train", "repeat", questions[i]).to_dict(),
                              "upstream_index": i} for i in selected]}}
    monkeypatch.setattr(repeat, "load_allocation", lambda _: allocation)
    config = tmp_path / "fake.yaml"
    config.write_text(yaml.safe_dump({"backend": "fake", "split": "repeat", "samples": 8,
        "model": {"device": "cpu", "dtype": "float32"},
        "limits": {"max_tokens": 400000, "max_elapsed_seconds": 300}}))

    def encoder(rows, *_):
        return np.array([[i, i % 2] for i in range(len(rows))], dtype=float), {"synthetic": True}

    return root, config, allocation, encoder


def prepare(panel):
    root, config, _, encoder = panel
    return repeat.prepare(root, config, encoder=encoder)


def test_question_only_preparation_never_reads_reference_answers(panel, monkeypatch):
    from datasets import Dataset

    monkeypatch.setattr(Dataset, "from_file", lambda *_: pytest.fail("Reference source opened in prepare/status"))
    study = prepare(panel)
    root, config, _, encoder = panel
    p = repeat.read_protocol(study)
    assert len(p["snapshot"]["jobs"]) == 160
    assert len({j["seed"] for j in p["snapshot"]["jobs"]}) == 160
    assert set(p["folds"].values()) == set(range(5))
    assert read_json(root / "data/repeat/manifest.json")["gold_sha256"] is None
    assert not (root / "data/repeat/gold.json").exists()
    before = (study / "protocol.json").read_bytes()
    assert repeat.prepare(root, config, encoder=encoder) == study
    assert (study / "protocol.json").read_bytes() == before
    assert repeat.status(study)["completed"] == 0
    assert repeat.status(study)["analysis"] == "locked"


def test_incomplete_endpoint_blocks_gold_scoring_and_analysis(panel, monkeypatch):
    study = prepare(panel)
    monkeypatch.setattr(repeat, "_selected_gold", lambda _: pytest.fail("Incomplete endpoint opened reference gold"))
    for action in [repeat.score, repeat.analyze]:
        with pytest.raises(ValueError, match="complete fixed endpoint"):
            action(study)
    assert not (study / "scores.numeric-v7.json").exists()
    assert not (study / "report.json").exists()


def test_full_fixture_collection_resumes_without_duplicate_attempts_and_scores_only_selected(panel, monkeypatch):
    study = prepare(panel)
    p = repeat.read_protocol(study)
    run = Path(p["snapshot"]["run_dir"])
    state = repeat.collect(study, lambda _: None)
    assert state["completed"] == 160 and state["analysis"] == "eligible"
    before = {x.name: x.read_bytes() for x in (run / "results").glob("*.json")}
    repeat.collect(study, lambda _: None)
    assert before == {x.name: x.read_bytes() for x in (run / "results").glob("*.json")}
    assert len(list((run / "attempts").glob("*.json"))) == 160
    artifact = repeat.score(study)
    assert len(artifact["scores"]) == 160 and all(s["correct"] for s in artifact["scores"])
    assert repeat.score(study) == artifact
    assert not (run / "scores.json").exists()
    assert not (panel[0] / "data/repeat/gold.json").exists()
    report = repeat.analyze(study)
    assert report["synthetic"] and not report["official_test_gold_opened"]
    assert report["statistics"]["question_count"] == 10
    assert not report["statistics"]["scale_acquisition"]
    assert repeat.analyze(study) == report


@pytest.mark.parametrize("target", ["config", "questions", "features", "archive"])
def test_frozen_input_changes_fail_before_gold(panel, monkeypatch, target):
    study = prepare(panel)
    monkeypatch.setattr(repeat, "_selected_gold", lambda _: pytest.fail("Changed study opened gold"))
    paths = {"config": study / "config.yaml", "questions": panel[0] / "data/repeat/questions.json",
             "features": study / "question-features.json", "archive": study / "frozen_code/reasoning_budget/backend.py"}
    paths[target].write_text(paths[target].read_text() + "\nchanged\n")
    with pytest.raises((ValueError, __import__("json").JSONDecodeError)):
        repeat.score(study)


def test_swapped_role_or_allocated_question_is_rejected(panel, monkeypatch):
    study = prepare(panel)
    changed = copy.deepcopy(panel[2])
    changed["roles"]["repeat"][0]["question"]["split"] = "confirmation"
    monkeypatch.setattr(repeat, "load_allocation", lambda _: changed)
    with pytest.raises(ValueError, match="allocation or role"):
        repeat.score(study)


def test_score_cache_tampering_is_rejected(panel):
    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    artifact = repeat.score(study)
    artifact["scores"][0]["correct"] = False
    atomic_json(study / "scores.numeric-v7.json", envelope(artifact))
    with pytest.raises(ValueError, match="cache identity changed"):
        repeat.score(study)


def test_pre_freeze_attempt_and_inconsistent_run_id_are_rejected(panel, monkeypatch):
    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    protocol = repeat.read_protocol(study)
    manifest, rows = repeat.checked_run(study, protocol)
    monkeypatch.setattr(repeat, "_selected_gold", lambda _: pytest.fail("Changed provenance opened gold"))
    run = Path(protocol["snapshot"]["run_dir"])
    attempt_path = run / "attempts" / f"{rows[0]['attempt_id']}.json"
    original = verified(attempt_path)
    atomic_json(attempt_path, envelope(original | {"started_at": protocol["prepared_at"] - 1}))
    with pytest.raises(ValueError, match="preceded protocol"):
        repeat.score(study)
    atomic_json(attempt_path, envelope(original))
    manifest["run_id"] = "changed"
    atomic_json(run / "manifest.json", envelope(manifest))
    with pytest.raises(ValueError, match="frozen identity"):
        repeat.score(study)


def test_partial_collected_records_cannot_unlock_gold(panel, monkeypatch):
    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    p = repeat.read_protocol(study)
    run = Path(p["snapshot"]["run_dir"])
    (run / "results" / f"{p['snapshot']['jobs'][-1]['id']}.json").unlink()
    monkeypatch.setattr(repeat, "_selected_gold", lambda _: pytest.fail("Partial endpoint opened gold"))
    assert repeat.status(study)["completed"] == 159
    with pytest.raises(ValueError, match="complete fixed endpoint"):
        repeat.score(study)


def test_orphan_old_attempt_is_rejected_even_when_all_final_responses_are_new(panel):
    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    p = repeat.read_protocol(study)
    run = Path(p["snapshot"]["run_dir"])
    old = verified(next((run / "attempts").glob("*.json")))
    atomic_json(run / "attempts/orphan.json", envelope(old | {
        "started_at": p["prepared_at"] - 1, "attempt_id": "orphan"}))
    with pytest.raises(ValueError, match="preceded protocol"):
        repeat.status(study)


def test_preparation_refuses_existing_generation_directory(panel):
    def resolver(path):
        snapshot, config, engine = repeat.inspect(path)
        Path(snapshot["run_dir"]).mkdir(parents=True)
        return snapshot, config, engine

    root, config, _, encoder = panel
    with pytest.raises(ValueError, match="preexisting generation directory"):
        repeat.prepare(root, config, encoder=encoder, resolver=resolver)
    assert not (root / repeat.STUDY / "protocol.json").exists()


def test_complete_run_with_over_limit_ledger_cannot_open_gold(panel, monkeypatch):
    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    p = repeat.read_protocol(study)
    attempt_path = next((Path(p["snapshot"]["run_dir"]) / "attempts").glob("*.json"))
    a = verified(attempt_path)
    atomic_json(attempt_path, envelope(a | {"elapsed_seconds": p["snapshot"]["config"]["limits"]["max_elapsed_seconds"] + 1}))
    monkeypatch.setattr(repeat, "_selected_gold", lambda _: pytest.fail("Over-budget run opened gold"))
    with pytest.raises(ValueError, match="cumulative limits"):
        repeat.score(study)


def test_old_v7_cli_still_rejects_real_repeat_without_using_new_endpoint(panel, monkeypatch):
    from reasoning_budget import scoring_v7

    study = prepare(panel)
    repeat.collect(study, lambda _: None)
    p = repeat.read_protocol(study)
    manifest, rows = repeat.checked_run(study, p)
    manifest["identity"]["config"]["backend"] = "transformers"
    monkeypatch.setattr(scoring_v7, "load_run", lambda _: (manifest, rows))
    monkeypatch.setattr(scoring_v7, "load_gold", lambda _: pytest.fail("Existing CLI opened repeat gold"))
    with pytest.raises(ValueError, match="own frozen Phase 2"):
        scoring_v7.score_run(p["snapshot"]["run_dir"])


def test_no_real_generation_was_started_by_prepare(panel):
    study = prepare(panel)
    state = read_json(study / "status.json")
    assert state["generation_started"] is False and not state["gold_materialized"]
    assert state["state"] == "prepared"
    assert verified(study / "protocol.json")["collection_permission"]["cloud_spend_usd"] == 0
