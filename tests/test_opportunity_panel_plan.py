"""Synthetic, gold-free checks for the proposed reserve child and pure diagnostics."""

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

from reasoning_budget.data import normalized
from reasoning_budget.storage import digest, envelope

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "opportunity_panel_plan.py"
spec = importlib.util.spec_from_file_location("opportunity_panel_plan", SCRIPT)
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


def allocation():
    rows = []
    for i in range(70):
        prompt = f"What is {i} plus one?"
        q = {"id": f"q{i}", "source": "fixture", "split": "reserve",
             "prompt": prompt, "answer_type": "number"}
        rows.append({"question": q, "upstream_index": i,
                     "normalized_prompt_sha256": digest(normalized(prompt)),
                     "group_id": q["id"], "pool": "external"})
    return {"roles": {"reserve": rows, "bridge": []},
            "source": {"revision": "fixture", "arrow_sha256": "fixture"}}


def test_question_only_selection_is_deterministic_and_parent_immutable():
    parent = allocation()
    original = copy.deepcopy(parent)
    first, folds = panel.choose_child(parent)
    assert (first, folds) == panel.choose_child(parent)
    assert parent == original
    assert len(first) == len(folds) == 64
    assert set(folds.values()) == set(range(5))
    assert all(r["child_question"]["split"] == "opportunity64" for r in first)
    assert all(r["parent_question"]["split"] == "reserve" for r in first)


def test_parent_overlap_rejected():
    parent = allocation()
    parent["roles"]["bridge"].append(copy.deepcopy(parent["roles"]["reserve"][0]))
    with pytest.raises(ValueError, match="overlaps"):
        panel.choose_child(parent)


def test_exclusive_preparation_and_tamper_guard(tmp_path, monkeypatch):
    root = tmp_path / "study"
    (root / "allocations").mkdir(parents=True)
    (root / "allocations" / "manifest.json").write_text("fixture\n")
    parent = allocation()
    monkeypatch.setattr(panel, "load_allocation", lambda path: copy.deepcopy(parent))
    monkeypatch.setattr(panel, "FILES", ("scripts/opportunity_panel_plan.py",))
    child = panel.prepare(root)
    assert panel.verify(root)["status"] == "prepared_question_only_collection_locked"
    with pytest.raises(ValueError, match="already exists"):
        panel.prepare(root)
    questions = child / "dataset" / "questions.json"
    questions.write_text(questions.read_text().replace("plus one", "plus two", 1))
    with pytest.raises(ValueError, match="plan changed|dataset changed"):
        panel.verify(root)


def test_sibling_overlap_and_gold_guard(tmp_path, monkeypatch):
    root = tmp_path / "study"
    (root / "allocations").mkdir(parents=True)
    (root / "allocations" / "manifest.json").write_text("fixture\n")
    monkeypatch.setattr(panel, "load_allocation", lambda path: allocation())
    monkeypatch.setattr(panel, "FILES", ("scripts/opportunity_panel_plan.py",))
    child = panel.prepare(root)
    selected = panel.verify(root)["selected"][0]
    sibling = child.parent / "sibling"
    sibling.mkdir()
    (sibling / "child-manifest.json").write_text(json.dumps(envelope({"selected": [selected]})))
    with pytest.raises(ValueError, match="overlaps"):
        panel.verify(root)
    (sibling / "child-manifest.json").unlink()
    sibling.rmdir()
    (child / "dataset" / "gold.json").write_text("{}")
    with pytest.raises(ValueError, match="forbidden"):
        panel.verify(root)


def test_symlink_rejected(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (root / "reserve-children").symlink_to(target)
    with pytest.raises(ValueError, match="Symlink"):
        panel._safe_child(root, root / "reserve-children" / panel.CHILD)


def sample_rows():
    folds = {f"q{i}": i % 5 for i in range(10)}
    rows = []
    for i in range(10):
        for draw in (0, 1):
            rows.append({"solver": "small", "question_id": f"q{i}", "draw": draw,
                         "confidence": -float(i + draw) / 10,
                         "direct_correct": int(i % 2 == 0),
                         "thinking_correct": int(i % 3 != 0),
                         "thinking_tokens": 100})
    return folds, rows


def test_opportunity_arithmetic_and_response_cap():
    folds, rows = sample_rows()
    summary = panel.opportunity_stats(rows, folds, "small", 0)
    assert summary["questions"] == 10
    assert summary["rescue"] == sum(r["thinking_correct"] > r["direct_correct"]
                                    for r in rows if r["draw"] == 0)
    assert summary["harm"] == sum(r["thinking_correct"] < r["direct_correct"]
                                  for r in rows if r["draw"] == 0)
    assert 64 * 2 * 2 * (512 + 512 + 2048 + 2) == 786944


def test_crossfit_has_no_heldout_or_opposite_half_label_access():
    folds, rows = sample_rows()
    original = panel.confidence_crossfit(rows, folds, "small")
    changed = copy.deepcopy(rows)
    for row in changed:
        if row["question_id"] == "q0" or row["draw"] == 1:
            row["direct_correct"] = 1 - row["direct_correct"]
            row["thinking_correct"] = 1 - row["thinking_correct"]
    altered = panel.confidence_crossfit(changed, folds, "small")
    for (qid, train_draw, eval_draw), value in original.items():
        if train_draw == 0 and qid == "q0":
            assert altered[qid, train_draw, eval_draw] == value
    assert len(original) == 20
    assert all(math.isfinite(v["threshold"]) or math.isinf(v["threshold"])
               for v in original.values())


def test_crossfit_rejects_duplicates_and_bad_training_cost():
    folds, rows = sample_rows()
    with pytest.raises(ValueError, match="Exactly two"):
        panel.confidence_crossfit(rows + [rows[0]], folds, "small")
    rows[0]["thinking_tokens"] = float("nan")
    with pytest.raises(ValueError, match="Training"):
        panel.confidence_crossfit(rows, folds, "small")


def test_every_heldout_group_and_opposite_half_label_can_change_without_leakage():
    plain_folds, plain_rows = sample_rows()
    expected = panel.confidence_crossfit(plain_rows, plain_folds, "small")
    changed = copy.deepcopy(plain_rows)
    for row in changed:
        if plain_folds[row["question_id"]] == 0 or row["draw"] == 1:
            row["direct_correct"] = 1 - row["direct_correct"]
            row["thinking_correct"] = 1 - row["thinking_correct"]
            row["thinking_tokens"] *= 200
    observed = panel.confidence_crossfit(changed, plain_folds, "small")
    for key in expected:
        if key[1] == 0 and plain_folds[key[0]] == 0:
            assert expected[key] == observed[key]
