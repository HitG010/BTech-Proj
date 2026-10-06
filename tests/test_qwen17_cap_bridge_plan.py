"""Synthetic preparation/seed/ordering checks; no real jobs or model calls."""

from copy import deepcopy

import pytest

from reasoning_budget.config import Config
from reasoning_budget.storage import digest
from scripts import qwen17_cap_bridge_plan as bridge


def fixture():
    config = Config().to_dict()
    config.update(samples=2, answer_tokens=512, reasoning_tokens=2048)
    metadata = {"closure_tokens": 2, "closure_ids": [151668, 271],
                "eos_token_ids": [151643, 151645]}
    cells = []
    for i in range(18):
        qid = f"q{i // 2}" if i < 14 else f"q{i - 7}"
        draw = i % 2 if i < 14 else 0
        question = {"id": qid, "source": "synthetic", "split": "opportunity64",
                    "prompt": "Return a number", "answer_type": "number"}
        job = {"id": f"original-{i}", "question_id": qid, "mode": "thinking", "sample": draw,
               "seed": 900 + i, "max_tokens": 2562,
               "identity": {"question": question}}
        cells.append({"question_id": qid, "draw": draw, "generation_seed": 900 + i,
                      "original_job": job, "original_record_sha256": f"record-{i}"})
    protocol = {"arms": {bridge.SOLVER: {"config": config, "backend_metadata": metadata,
                                         "asset_file_sha256": {}, "jobs": []}}}
    return protocol, cells


def test_matched_jobs_preserve_original_seeds_and_question_metadata():
    protocol, cells = fixture()
    before = deepcopy(protocol)
    arms = bridge.matched_jobs(protocol, cells, "/tmp/synthetic-cap-bridge")
    assert protocol == before
    all_jobs = [j for arm in arms.values() for j in arm["jobs"]]
    assert len(all_jobs) == len({j["id"] for j in all_jobs}) == 36
    assert sum(j["max_tokens"] for j in all_jobs) == 129096
    for a, b, original in zip(arms["control_2k"]["jobs"], arms["extended_4k"]["jobs"], cells):
        assert a["seed"] == b["seed"] == original["generation_seed"]
        assert a["sample"] == b["sample"] == original["draw"]
        assert a["identity"]["question"] == b["identity"]["question"] == original["original_job"]["identity"]["question"]
        assert a["id"] == digest(a["identity"]) and b["id"] == digest(b["identity"])
        assert (a["max_tokens"], b["max_tokens"]) == (2562, 4610)


def test_validation_order_gate_requires_terminal_and_bound_review(tmp_path):
    from scripts.opportunity_panel_collect import write_once
    with pytest.raises(ValueError, match="complete"):
        bridge.require_validation_review(tmp_path)
    report = {"scientific_screen": False}
    write_once(tmp_path / "report.json", report)
    write_once(tmp_path / "status.json", {"state": "complete", "report_sha256": digest(report)})
    write_once(tmp_path / "completion-review-verification.json", {"checks_passed": True,
                                                                 "report_sha256": digest(report)})
    assert len(bridge.require_validation_review(tmp_path)) == 3


def test_prefix_gate_ignores_answer_tokens_beyond_forced_close():
    def row(ids, answer):
        return {"result": {"metadata": {"reasoning_token_ids": ids, "answer_token_ids": answer}}}
    control = row([11, 12, 13], [1])
    extended = row([11, 12, 13, 14, 15], [2])
    assert bridge.shared_reasoning_prefix(control, extended) == {
        "compared_tokens": 3, "matches": True,
        "scope": "shared reasoning through first close/EOS/shorter cap; not final answer equality"}
    assert not bridge.shared_reasoning_prefix(control, row([11, 99], [1]))["matches"]
    assert bridge.shared_reasoning_prefix(row([11, 151668, 90], []),
                                          row([11, 151668, 91], []))["matches"]
    with pytest.raises(ValueError, match="Nonempty"):
        bridge.shared_reasoning_prefix(row([], []), extended)


def test_cap_selection_cannot_use_labels():
    protocol, cells = fixture()
    records = []
    # Fill all 256 original arm cells without any score or correctness fields.
    for i in range(256):
        if i < 18:
            job = cells[i]["original_job"]
        else:
            job = {"id": f"other-{i}", "mode": "direct", "sample": 0,
                   "question_id": f"unused-{i}"}
        records.append({"job": job, "status": "completed", "result": {
            "forced_closure": i < 18, "reasoning_tokens": 2048 if i < 18 else 0}})
    protocol["arms"][bridge.SOLVER]["jobs"] = [r["job"] for r in records]
    selected = bridge.capped_cells(protocol, records)
    assert len(selected) == 18 and len({r["question_id"] for r in selected}) == 11
    broken = deepcopy(records)
    broken[0]["result"]["reasoning_tokens"] = 4096
    with pytest.raises(ValueError, match="2k"):
        bridge.capped_cells(protocol, broken)


def test_question_snapshot_keeps_original_split_and_source_rows():
    protocol, cells = fixture()
    questions = {}
    for cell in cells:
        questions[cell["question_id"]] = cell["original_job"]["identity"]["question"]
    protocol["selected"] = [{"child_question": q, "upstream_index": i}
                            for i, q in enumerate(questions.values())]
    snapshot = bridge.question_snapshot(protocol, cells)
    assert len(snapshot["questions"]) == len(snapshot["selected_training_source_rows"]) == 11
    assert {q["split"] for q in snapshot["questions"]} == {"opportunity64"}
    manifest = bridge.dataset_manifest(snapshot)
    assert manifest["gold_sha256"] is None
    assert manifest["questions_sha256"] == digest(snapshot["questions"])
    assert len(manifest["splits"]["opportunity64"]) == 11


def test_preparation_is_locked_before_validation_without_model_access(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "OUTPUT", tmp_path / bridge.SPEC["version"])
    monkeypatch.setattr(bridge, "BASE", tmp_path)
    monkeypatch.setattr(bridge, "require_validation_review", lambda: (_ for _ in ()).throw(
        ValueError("validation incomplete")))
    monkeypatch.setattr(bridge.diagnosis, "checked", lambda: pytest.fail("old-data selection before gate"))
    with pytest.raises(ValueError, match="validation incomplete"):
        bridge.prepare()
    assert not (bridge.OUTPUT / "plan.json").exists()


def test_budget_and_development_scope():
    assert bridge.SPEC["response_only_bound"] == 18 * (2562 + 4610)
    assert bridge.SPEC["proposed_global_tokens"] == 160000
    assert bridge.SPEC["proposed_global_seconds"] == 14400
    assert bridge.SPEC["scope"] == "cap-enriched cached-development"
    assert bridge.SPEC["generation"] == "unimplemented_locked"
