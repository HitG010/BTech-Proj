import copy
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pytest
import yaml

from reasoning_budget import backend, bridge_worker, research_bridge, research_data
from reasoning_budget.records import Question
from reasoning_budget.runner import load_run
from reasoning_budget.storage import atomic_json, envelope, read_json


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    class RecordedFake(backend.FakeBackend):
        def generate(self, question, job, deadline):
            result = super().generate(question, job, deadline)
            result.mean_generated_logprob_raw = -0.2 if job.mode == "direct" else None
            result.metadata.update({
                "reasoning_token_ids": [1] * result.reasoning_tokens,
                "answer_token_ids": [2] * result.answer_tokens,
                "inserted_token_ids": [3] * result.inserted_tokens,
                "memory": {"mps_allocated_bytes": 1024},
            })
            return result

    monkeypatch.setattr(backend, "FakeBackend", RecordedFake)
    root = tmp_path / "research"
    arrow = tmp_path / "train.arrow"
    answers = ["UNSELECTED_ANSWER_MUST_NOT_BE_PARSED"] * 6
    answers[2] = answers[4] = "A worked solution. #### 0"
    table = pa.table({"question": [f"Question {i}" for i in range(6)], "answer": answers})
    with pa.OSFile(str(arrow), "wb") as sink, pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    allocation = {
        "source": {"arrow_path": str(arrow), "arrow_sha256": research_bridge.file_hash(arrow),
                   "revision": "fixture"},
        "roles": {"bridge": [
            {"question": Question(f"q{i}", "fixture-train", "bridge", f"Question {i}").to_dict(),
             "upstream_index": i} for i in (2, 4)
        ]},
    }
    # Allocator integrity and exclusion logic are tested independently. Here we
    # exercise the bridge's selected-answer access and frozen full fake workflow.
    monkeypatch.setattr(research_data, "load_allocation", lambda _: allocation)
    config_path = tmp_path / "fake.yaml"
    config_path.write_text(yaml.safe_dump({
        "backend": "fake", "name": "bridge-fixture", "split": "bridge", "samples": 2,
        "answer_tokens": 512, "reasoning_tokens": 2048,
        "model": {"device": "cpu", "dtype": "float32"},
        "limits": {"max_tokens": 30000, "max_elapsed_seconds": 300},
    }))

    def resolver(config, source, output):
        snapshot, _, _ = bridge_worker.inspect(config)
        atomic_json(output, envelope(snapshot))
        return snapshot

    source = Path(research_bridge.__file__).parent.parent
    study = research_bridge.prepare(root, config_path, source, resolver=resolver)
    return study, root, config_path, source, resolver


def test_bridge_freezes_matching_seeds_isolated_configs_and_only_selected_gold(bridge):
    study, root, config, source, resolver = bridge
    protocol = research_bridge.read_protocol(study)
    assert protocol["question_count"] == 2
    assert protocol["prepared_at"] > 0
    assert read_json(root / "data" / "bridge" / "gold.json") == {"q2": "0", "q4": "0"}
    pairs = []
    for arm in ["legacy", "v3"]:
        snapshot = protocol["arms"][arm]["snapshot"]
        pairs.append({(j["question_id"], j["mode"], j["sample"]): j["seed"]
                      for j in snapshot["jobs"]})
    assert pairs[0] == pairs[1] and len(pairs[0]) == 8
    old_yaml = yaml.safe_load(Path(protocol["arms"]["legacy"]["config_path"]).read_text())
    assert "closure_text" not in old_yaml
    assert "max_consecutive_failures" not in old_yaml["limits"]
    original = (study / "protocol.json").read_bytes()
    assert research_bridge.prepare(root, config, source, resolver=resolver) == study
    assert (study / "protocol.json").read_bytes() == original


def test_incomplete_bridge_cannot_open_gold_or_score(bridge, monkeypatch):
    study, *_ = bridge
    monkeypatch.setattr(research_bridge, "score_run", lambda _: pytest.fail("Gold/scoring unlocked early"))
    with pytest.raises(ValueError, match="incomplete"):
        research_bridge.evaluate(study)
    assert not (study / "report.json").exists()


def test_capped_arm_does_not_prevent_other_arm_collection_or_unlock_gold(bridge, monkeypatch):
    study, *_ = bridge
    calls = []

    def worker(command, **kwargs):
        arm = command[-1]
        calls.append(arm)
        if arm == "v3":
            bridge_worker.collect(study, arm, lambda _: None)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(research_bridge.subprocess, "run", worker)
    monkeypatch.setattr(research_bridge, "score_run", lambda _: pytest.fail("Incomplete bridge opened gold"))
    research_bridge.run_study(study, lambda _: None)
    assert calls == ["legacy", "legacy", "legacy", "v3"]
    state = read_json(study / "status.json")
    assert state["state"] == "paused"
    assert state["arms"]["legacy"]["completed"] == 0
    assert state["arms"]["v3"]["completed"] == 8
    assert not (study / "report.json").exists()


def test_full_fake_bridge_records_freeze_before_generation_and_resumes_without_repeats(bridge):
    study, *_ = bridge
    protocol = research_bridge.read_protocol(study)
    # Both fixture arms use current fake source; no claim to reproduce real legacy inference.
    for arm in ["legacy", "v3"]:
        result = bridge_worker.collect(study, arm, lambda _: None)
        assert result["completed"] == result["expected"] == 8
    result = research_bridge.evaluate(study)
    assert result["synthetic"] and result["official_test_opened"] is False
    assert result["paired"]["direct"]["matched_cells"] == 4
    assert result["paired"]["thinking"]["token_ids_equal"] == 4
    assert result["engineering_gates"]["raw_confidence_covered"] is True
    assert result["summaries"]["v3"]["modes"]["direct"]["peak_mps_allocated_bytes"] == 1024
    records_before = {}
    for arm in ["legacy", "v3"]:
        path = Path(protocol["arms"][arm]["snapshot"]["run_dir"])
        records_before[arm] = {p.name: p.read_bytes() for p in (path / "results").glob("*.json")}
    research_bridge.run_study(study, lambda _: None)
    for arm in ["legacy", "v3"]:
        path = Path(protocol["arms"][arm]["snapshot"]["run_dir"])
        assert {p.name: p.read_bytes() for p in (path / "results").glob("*.json")} == records_before[arm]
        assert len(list((path / "attempts").glob("*.json"))) == 8
    assert read_json(study / "status.json")["state"] == "complete"


def test_frozen_template_and_dataset_changes_rejected(bridge):
    study, root, config, *_ = bridge
    previous = config.read_bytes()
    config.write_text(config.read_text() + "\n# changed frozen input\n")
    with pytest.raises(ValueError, match="template changed"):
        research_bridge.read_protocol(study)
    config.write_bytes(previous)
    questions = root / "data" / "bridge" / "questions.json"
    rows = read_json(questions)
    rows[0]["prompt"] = "Changed prompt"
    atomic_json(questions, rows)
    with pytest.raises(ValueError, match="question/dataset artifact changed"):
        research_bridge.read_protocol(study)


def test_changed_paired_seed_is_rejected(bridge):
    study, *_ = bridge
    protocol = research_bridge.read_protocol(study)
    changed = copy.deepcopy(protocol["arms"])
    changed["v3"]["snapshot"]["jobs"][0]["seed"] += 1
    with pytest.raises(ValueError, match="paired seeds"):
        research_bridge._validate_pair(changed)


def test_worker_cannot_freeze_a_different_imported_package(bridge):
    study, *_ = bridge
    changed = copy.deepcopy(research_bridge.read_protocol(study)["arms"])
    changed["legacy"]["snapshot"]["package_root"] = "/some/other/source"
    with pytest.raises(ValueError, match="different source package"):
        research_bridge._validate_sources(changed)


def test_inference_cannot_mix_generation_code(bridge):
    study, *_ = bridge
    protocol = research_bridge.read_protocol(study)
    bridge_worker.collect(study, "v3", lambda _: None)
    changed = copy.deepcopy(protocol)
    changed["arms"]["v3"]["snapshot"]["generation_implementation"] = "0" * 64
    with pytest.raises(ValueError, match="mixed implementations"):
        research_bridge.checked_arm(study, changed, "v3")


def test_paired_statistics_keep_draws_inside_questions_and_reject_duplicates(bridge):
    study, *_ = bridge
    protocol = research_bridge.read_protocol(study)
    for arm in ["legacy", "v3"]:
        bridge_worker.collect(study, arm, lambda _: None)
    records = {arm: load_run(protocol["arms"][arm]["snapshot"]["run_dir"])[1]
               for arm in ["legacy", "v3"]}
    scores = {arm: research_bridge.score_run(protocol["arms"][arm]["snapshot"]["run_dir"])["scores"]
              for arm in ["legacy", "v3"]}
    result = research_bridge.paired_analysis(records["legacy"], records["v3"],
                                            scores["legacy"], scores["v3"])
    assert result["direct"]["questions"] == 2
    assert result["direct"]["accuracy_delta"] == {"mean": 0, "ci95": [0, 0]}
    with pytest.raises(ValueError, match="Duplicate bridge cells"):
        research_bridge.paired_analysis(records["legacy"] + records["legacy"][:1],
                                        records["v3"], scores["legacy"] + scores["legacy"][:1],
                                        scores["v3"])
