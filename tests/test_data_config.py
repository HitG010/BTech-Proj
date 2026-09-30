import pytest

from reasoning_budget.config import from_dict
from reasoning_budget.data import freeze_gsm8k, load_questions, prepare_fixtures
from reasoning_budget.storage import read_json


@pytest.mark.parametrize(
    "config,message",
    [
        ({"typo": 1}, "Unknown"),
        ({"answer_tokens": -1}, "positive"),
        ({"limits": {"max_elapsed_seconds": float("nan")}}, "finite"),
        ({"model": {"device": "auto"}}, "device"),
        ({"thinking": {"top_p": 2}}, "top_p"),
        ({"modes": ["direct", "direct"]}, "unique"),
        ({"model": None}, "mapping"),
        ({"samples": True}, "integer"),
        ({"model": {"local_files_only": "false"}}, "boolean"),
        ({"closure_text": "stop"}, "closure_text"),
        ({"closure_text": None}, "closure_text"),
        ({"limits": {"max_consecutive_failures": 0}}, "max_consecutive_failures"),
        ({"limits": {"max_consecutive_failures": True}}, "max_consecutive_failures"),
    ],
)
def test_invalid_configuration(config, message):
    with pytest.raises(ValueError, match=message):
        from_dict(config)


def test_decoding_defaults():
    c = from_dict({"thinking": {"top_k": 10}})
    assert c.thinking.temperature == 0.6
    assert c.thinking.top_p == 0.95
    assert c.closure_text == "</think>\n\n"
    assert c.limits.max_consecutive_failures == 3
    assert c.answer_tokens == 256 and c.reasoning_tokens == 2048
    assert c.prompt_suffix == r"In your final response, give only the numerical answer in \boxed{}."


def test_fixtures_gold_separate(tmp_path):
    prepare_fixtures(tmp_path)
    (tmp_path / "gold.json").unlink()
    assert len(load_questions(tmp_path)) == 10
    assert all("answer" not in q.to_dict() for q in load_questions(tmp_path))


def test_splits_deterministic_disjoint_and_deduplicated(tmp_path):
    train = [{"question": f"Question {i}?", "answer": f"work\n#### {i}"} for i in range(30)]
    test = [{"question": f"Question {i}?", "answer": f"work\n#### {i}"} for i in range(25, 40)]
    train += [{"question": "  QUESTION   1?  ", "answer": "#### 1"}]
    sizes = {"pilot": 3, "train": 5, "validation": 3, "test": 4}
    for name in ["a", "b"]:
        freeze_gsm8k(train, test, tmp_path / name, 123, "frozen", sizes)
    assert read_json(tmp_path / "a/manifest.json") == read_json(tmp_path / "b/manifest.json")
    qs = load_questions(tmp_path / "a")
    assert len(qs) == 15
    assert all("gsm8k-test" in q.id for q in qs if q.split == "test")
    manifest = read_json(tmp_path / "a/manifest.json")
    assert manifest["metadata"]["duplicates_removed"] == 6
    with pytest.raises(ValueError, match="already frozen"):
        freeze_gsm8k(train, test, tmp_path / "a", 124, "frozen", sizes)
