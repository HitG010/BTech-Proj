import importlib.util
import json
from pathlib import Path

import pytest

from reasoning_budget import scoring_v7 as v7
from reasoning_budget.storage import envelope

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/parser_compatibility_preflight.py"
SPEC = importlib.util.spec_from_file_location("parser_compatibility_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


@pytest.mark.parametrize("case", preflight.fixtures())
def test_prespecified_synthetic_cases(case):
    assert list(preflight.parse_answer(case["text"], incomplete=case["incomplete"])) == case[
        "expected"
    ]


@pytest.mark.parametrize("text", [
    "Working \\boxed{2}\nThe total is \\boxed{7}.",
    "**Final answer: \\boxed{7}",
    "The **Final answer: \\boxed{7}** is stated here.",
    "**Final answer: **\\boxed{7}** dollars**",
    "**Final answer:\n\\boxed{7}**",
    "__Final answer: \\boxed{7}__",
    "Final answer:\n0.07 dollars, which is 7 cents.\n\\boxed{7}",
    "Final answer:\nThe remaining two workers need:\n\\boxed{7}",
])
def test_unsupported_expansions_preserve_exact_v7(text):
    assert preflight.normalize(text) == text
    assert preflight.parse_answer(text) == v7.parse_answer(text)


@pytest.mark.parametrize("termination", ["timeout", "early_eos", "reasoning_in_answer"])
def test_generation_metadata_cannot_be_salvaged(termination):
    row = {"status": "completed", "result": {"final_answer":
           "**Final answer: \\boxed{7}**", "answer_truncated": False,
           "termination": termination}}
    assert preflight.extract_record(row) == (None, "incomplete")


def test_extractor_has_no_gold_interface_or_scoring_calls(monkeypatch):
    monkeypatch.setattr(v7, "load_gold", lambda *_: pytest.fail("gold opened"))
    monkeypatch.setattr(v7, "score_run", lambda *_: pytest.fail("score called"))
    assert preflight.parse_answer("**Final answer: \\boxed{7}**") == ("7", "ok")
    with pytest.raises(TypeError):
        preflight.parse_answer("**Final answer: \\boxed{7}**", gold="7")


def test_write_once_and_envelope_integrity(tmp_path):
    path = tmp_path / "plan.json"
    preflight.write_once(path, {"candidate": "one"})
    before = path.read_bytes()
    assert json.loads(before) == envelope({"candidate": "one"})
    with pytest.raises(FileExistsError):
        preflight.write_once(path, {"candidate": "two"})
    assert path.read_bytes() == before


def test_frozen_identity_rejected_before_response_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "OUTPUT", Path("new-preflight"))
    plan = {"policy": {"tampered": True}}
    preflight.write_once(tmp_path / preflight.OUTPUT / "plan.json", plan)
    monkeypatch.setattr(preflight, "extract_record", lambda *_: pytest.fail("response extracted"))
    with pytest.raises(ValueError, match="identity changed"):
        preflight.execute(tmp_path)


def test_incomplete_endpoint_rejected_without_extracting(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "RUNS", [("repeat", "cached-run", 2)])
    monkeypatch.setattr(preflight, "extract_record", lambda *_: pytest.fail("response extracted"))
    with pytest.raises(ValueError, match="Endpoint mismatch"):
        preflight.input_inventory(tmp_path)
