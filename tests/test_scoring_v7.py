import pytest
from test_scoring_v6 import isolated_run, record  # noqa: F401

from reasoning_budget import scoring_v7 as v7
from reasoning_budget.runner import load_run
from reasoning_budget.storage import atomic_json, digest, read_json


@pytest.mark.parametrize("text,expected", [
    (r"Working \boxed{170}, \boxed{180}" + "\n### ✅ Final Answer:\n$$\n\\boxed{180}\n$$", "180"),
    ("### Final Answer\nThe number of cans of corn is:\n$$\n\\boxed{10}\n$$", "10"),
    (r"Final answer: Beth bought $\boxed{10}$ cans of corn.", "10"),
    ("Final Answer:\n\\boxed{1}\nBilly must run **1 mile**.", "1"),
    ("Final answer:\n$$\n\\boxed{3000}\n$$\nBen makes **$3000 per month before taxes**.", "3000"),
    ("Final answer:\n\\boxed{37}\nThis is the total change.", "37"),
    (r"Final answer: 4 \boxed{4}", "4"),
    ("Final answer: -3/2\nThe result is -1.5.", "-3/2"),
    (r"Final answer: \boxed{1/6}" + "\nThis equals $0.1\\overline{6}$.", "1/6"),
    ("Final answer:\n\\boxed{4}\nAnswer: 4", "4"),
    ("Final answer: \\$18 dollars", "18"),
    ("Final answer:\n\\boxed{4}\nThe result is 4miles.", "4"),
    ("### Final Answer\n4 apples", "4"),
    (r"Final answer: **\boxed{4}**.", "4"),
    (r"Final answer: \boxed{10}\%", "10"),
])
def test_prose_can_confirm_but_never_replace_explicit_answer(text, expected):
    assert v7.parse_answer(text) == (expected, "ok")


@pytest.mark.parametrize("text,status", [
    ("Final answer:\nThe girl has 180 followers.", "missing"),
    ("Final answer: see below\n\\boxed{4}", "invalid_number"),
    (r"\boxed{3}" + "\nFinal answer 4", "invalid_number"),
    (r"\boxed{3}" + "\nFinal answer:", "missing"),
    (r"\boxed{3" + "\nFinal answer: 4", "incomplete"),
    ("Final answer: 4\nFinal answer: 5", "conflicting"),
    ("Answer: 3\nFinal answer: 4", "conflicting"),
    ("Final answer: 4\n#### 5", "conflicting"),
    ("Final answer: 4\n5", "conflicting"),
    (r"Final answer: \boxed{4} or five", "invalid_number"),
    ("Final answer: 4 or 5", "invalid_number"),
    ("Final answer: 4 is wrong", "invalid_number"),
    ("Final answer:\n\\boxed{4}\nThe answer is five.", "invalid_number"),
    ("Final answer:\n\\boxed{4}\nThis is not correct.", "invalid_number"),
    ("Final answer:\n\\boxed{4}\nActually it is 5.", "conflicting"),
    ("Final answer:\n\\boxed{4}\nThe result is 5miles.", "conflicting"),
    ("Final answer:\n$$\n\\boxed{4}", "incomplete"),
    ("Final answer:\n\\boxed{1/0}", "invalid_number"),
    ("Final answer:\n\\boxed{4}\nIt equals \\frac{1}{0}.", "invalid_number"),
    ("Final answer:\n\\boxed{10} + 10", "invalid_number"),
    ("Final answer:\n\\boxed{10} × 10", "invalid_number"),
    ("Final answer:\n10 + \\boxed{10}", "invalid_number"),
    ("Final answer:\n\\boxed{-10} -10", "invalid_number"),
    ("Final answer:\n\\boxed{10} \\times 10", "invalid_number"),
    ("Final answer:\n\\boxed{10}\nThis isn't correct.", "invalid_number"),
    ("Final answer:\n\\boxed{10}\nDouble that value.", "invalid_number"),
    (r"Final answer: \boxed{10} doubled.", "invalid_number"),
    (r"Final answer: \boxed{10} multiplied by itself.", "invalid_number"),
    (r"Final answer: \boxed{10} was subtracted.", "invalid_number"),
    (r"Final answer: \boxed{10} increased by the same amount.", "invalid_number"),
    (r"Final answer: \boxed{10} is half the result.", "invalid_number"),
    (r"Final answer: \boxed{10} and eleven.", "invalid_number"),
    (r"Final answer: Beth bought \boxed{10} cans and five more.", "invalid_number"),
    (r"Final answer: \boxed{10} with a second value of eleven.", "invalid_number"),
    (r"Final answer: \boxed{10} could be eleven.", "invalid_number"),
    (r"Final answer: \boxed{10}^10", "invalid_number"),
    (r"Final answer: \boxed{10} squared.", "invalid_number"),
    (r"Final answer: \boxed{10} mod 10", "invalid_number"),
    (r"Final answer: \boxed{10} % 10", "invalid_number"),
    ("Final answer:\n\\boxed{10}\n10 % 10", "invalid_number"),
    (r"Final answer: \boxed{10} percent of 10.", "invalid_number"),
    (r"Final answer: \boxed{10}% of 10.", "invalid_number"),
    (r"Final answer: \boxed{10} out of 10.", "invalid_number"),
    (r"Final answer: \boxed{10} raised to 10.", "invalid_number"),
    (r"Final answer: \boxed{10} less than 10.", "invalid_number"),
    (r"Final answer: \boxed{10} reduced by 10.", "invalid_number"),
])
def test_prose_cannot_hide_conflicts_or_malformed_claims(text, status):
    assert v7.parse_answer(text) == (None, status)


def test_gold_and_incomplete_guards():
    text = r"\boxed{3}" + "\nFinal answer: \\boxed{4}"
    assert v7.score_record(record(text), "3")["extracted_answer"] == "4"
    assert not v7.score_record(record(text), "3")["correct"]
    assert v7.score_record(record(text), "4")["correct"]
    assert not v7.score_record(record(text, answer_truncated=True), "4")["correct"]
    for gold in ["4", "5", "42"]:
        assert not v7.score_record(record("Final answer: 4\nFinal answer: 5"), gold)["correct"]


def test_separate_v7_cache_preserves_v5_and_v6(isolated_run):  # noqa: F811
    from reasoning_budget.scoring_v6 import score_run as score_v6

    path, _ = isolated_run
    atomic_json(path / "scores.json", {"scoring_version": "numeric-v5"})
    score_v6(path)
    before = {name: (path / name).read_bytes() for name in ["scores.json", "scores.numeric-v6.json"]}
    artifact = v7.score_run(path)
    assert artifact["scoring_version"] == "numeric-v7"
    assert v7.score_run(path) == artifact
    assert before == {name: (path / name).read_bytes() for name in before}
    artifact["scores"][0]["extracted_answer"] = "tampered"
    atomic_json(path / "scores.numeric-v7.json", artifact)
    with pytest.raises(ValueError, match="cache identity changed"):
        v7.score_run(path)
    assert before == {name: (path / name).read_bytes() for name in before}


def test_v7_sealed_shared_and_changed_question_gold_stays_closed(isolated_run, monkeypatch):  # noqa: F811
    path, dataset = isolated_run
    original = read_json(dataset / "manifest.json")
    monkeypatch.setattr(v7, "load_gold", lambda _: pytest.fail("Sealed/shared gold accessed"))
    for meta in [{"role": "test", "upstream": "test"}, {"role": "confirmation", "upstream": "train"},
                 {"source": "gsm8k"}]:
        atomic_json(dataset / "manifest.json", dict(original, metadata=meta))
        with pytest.raises(ValueError, match="isolated"):
            v7.score_run(path)
    atomic_json(dataset / "manifest.json", original)
    questions = read_json(dataset / "questions.json")
    questions[0]["prompt"] = "Changed prompt"
    atomic_json(dataset / "questions.json", questions)
    atomic_json(dataset / "manifest.json", dict(original, questions_sha256=digest(questions)))
    with pytest.raises(ValueError, match="outside this isolated run"):
        v7.score_run(path)


def test_v7_incomplete_and_unfrozen_repeat_gold_stays_closed(isolated_run, monkeypatch):  # noqa: F811
    path, _ = isolated_run
    manifest, rows = load_run(path)
    monkeypatch.setattr(v7, "load_gold", lambda _: pytest.fail("Unfrozen or incomplete gold opened"))
    rows[0]["status"] = "pending"
    monkeypatch.setattr(v7, "load_run", lambda _: (manifest, rows))
    with pytest.raises(ValueError, match="complete run endpoint"):
        v7.score_run(path)
    rows[0]["status"] = "completed"
    manifest["identity"]["config"]["backend"] = "transformers"
    with pytest.raises(ValueError, match="own frozen Phase 2"):
        v7.score_run(path)


def test_v7_complete_arm_requires_complete_pair_before_gold(isolated_run, monkeypatch):  # noqa: F811
    from reasoning_budget import research_bridge

    path, dataset = isolated_run
    manifest, rows = load_run(path)
    manifest["identity"]["config"]["backend"] = "transformers"
    manifest["identity"]["questions"][0]["split"] = "bridge"
    data_manifest = read_json(dataset / "manifest.json")
    data_manifest["metadata"]["role"] = "bridge"
    questions = read_json(dataset / "questions.json")
    questions[0]["split"] = "bridge"
    data_manifest["questions_sha256"] = digest(questions)
    data_manifest["splits"] = {"bridge": ["q"]}
    atomic_json(dataset / "questions.json", questions)
    atomic_json(dataset / "manifest.json", data_manifest)
    monkeypatch.setattr(v7, "load_run", lambda _: (manifest, rows))
    protocol = {"arms": {arm: {"snapshot": {"run_dir": str(path.resolve()), "jobs": [1]}}
                         for arm in ["legacy", "v3"]}}
    monkeypatch.setattr(research_bridge, "read_protocol", lambda _: protocol)
    monkeypatch.setattr(research_bridge, "checked_arm", lambda _, __, arm:
                        (manifest, rows if arm == "legacy" else []))
    monkeypatch.setattr(v7, "load_gold", lambda _: pytest.fail("Incomplete paired bridge gold opened"))
    with pytest.raises(ValueError, match="Paired bridge endpoint"):
        v7.score_run(path)
