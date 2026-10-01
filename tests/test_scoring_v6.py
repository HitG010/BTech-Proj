import pytest

from reasoning_budget import scoring as v5
from reasoning_budget import scoring_v6 as v6
from reasoning_budget.config import Config
from reasoning_budget.data import save_dataset
from reasoning_budget.records import Question
from reasoning_budget.runner import load_run, run
from reasoning_budget.storage import atomic_json, digest, read_json


@pytest.mark.parametrize("text,expected", [
    (r"Working: \boxed{170}, then \boxed{180}." + "\n### ✅ Final Answer:\n$$\n\\boxed{180}\n$$", "180"),
    (r"\boxed{3}" + "\nFinal answer: \\boxed{4}", "4"),
    (r"\boxed{3}" + "\n### Final Answer:\n$$\n\\boxed{4}\n$$", "4"),
    (r"\boxed{3}" + "\n#### 4", "4"),
    (r"\boxed{3}" + "\n## **Final Answer**\n\\[\n\\boxed{4}\n\\]", "4"),
    (r"\boxed{x = 3}" + "\n**Final Answer:** **4**", "4"),
    ("Final answer: -3/2", "-3/2"),
    (r"Final answer: \$18 dollars", "18"),
    ("Final answer: $18 dollars", "18"),
    (r"Final answer: $\boxed{7}$", "7"),
    ("Final answer:\n\\boxed{\\frac{\n3}{4}}", "3/4"),
    (r"Final answer: \boxed{0.1\overline{6}}", "1/6"),
    (r"Final answer: \boxed{4}" + "\nAnswer: 4", "4"),
    ("Final answer: 4\n#### 4", "4"),
    (r"Answer: \boxed{4}" + "\nWorking: \\boxed{3}\nFinal answer: 4", "4"),
    ("The answer is 4.\nWorking: \\boxed{3}\nFinal answer: 4", "4"),
    (r"Final answer: \boxed{4} \boxed{4}", "4"),
    (r"Final answer: 4 \boxed{4}", "4"),
])
def test_final_section_selects_answer_without_using_gold(text, expected):
    assert v6.parse_answer(text) == (expected, "ok")


@pytest.mark.parametrize("text,status", [
    ("Final answer: 4\nFinal answer: 5", "conflicting"),
    ("Final answer: 4\n#### 5", "conflicting"),
    ("#### 4\nFinal answer: 5", "conflicting"),
    (r"Answer: \boxed{3}" + "\nFinal answer: 4", "conflicting"),
    ("Answer:\n\\boxed{3}\nFinal answer: 4", "conflicting"),
    ("The answer is 3.\nFinal answer: 4", "conflicting"),
    ("Final answer: 4 or 5", "ambiguous"),
    ("Final answer: 4 or five", "invalid_number"),
    ("Final answer: not 4", "invalid_number"),
    ("Final answer: 4 is wrong", "invalid_number"),
    (r"Final answer: \boxed{4} or five", "invalid_number"),
    (r"Final answer: \boxed{4} is wrong", "invalid_number"),
    ("Final answer: see below\n\\boxed{4}", "invalid_number"),
    (r"\boxed{3}" + "\nFinal answer:", "missing"),
    (r"\boxed{3}" + "\nFinal answer: 4\nFinal answer:", "missing"),
    (r"\boxed{3" + "\nFinal answer: 4", "incomplete"),
    (r"\boxed{3}" + "\nFinal answer: 4\n\\boxed{5}", "conflicting"),
    ("Final answer: 4\n5", "conflicting"),
    ("Final answer: 4\nActually it is wrong.", "invalid_number"),
    (r"\boxed{3}" + "\nFinal answer 4", "invalid_number"),
    (r"\boxed{3}" + "\n### **Final Answer** maybe four", "invalid_number"),
    ("Final answer:\n$$\n\\boxed{4}", "incomplete"),
    ("Final answer:\n\\[\n\\boxed{4}\n\\)", "invalid_number"),
    ("Final answer: 1/0", "invalid_number"),
    (r"Final answer: \boxed{7 \text{or eight}}", "invalid_number"),
    ("Answer: not 3\nFinal answer: 4", "invalid_number"),
])
def test_final_sections_cannot_hide_invalid_or_conflicting_claims(text, status):
    assert v6.parse_answer(text) == (None, status)


@pytest.mark.parametrize("text", [
    "42", "The answer is 4.25.", r"\boxed{3} and \boxed{4}",
    r"\boxed{7 or eight}", r"\boxed{not 7}", "I cannot solve this.",
    "#### Billy:\n\\boxed{4}", "A prose mention of final answer: 4\n\\boxed{3}",
    r"\boxed{0.75} Final answer: 3/4", r"\boxed{\$18}",
    "Final answers: 3 and 4", "<think>42</think>", "",
])
def test_without_structural_final_section_preserve_v5(text):
    assert v6.parse_answer(text) == v5.parse_answer(text)


def record(text, **result_overrides):
    return {
        "job": {"id": "j", "question_id": "q", "mode": "direct"},
        "status": "completed", "result": {"final_answer": text,
        "answer_truncated": False, "termination": "eos", **result_overrides},
    }


def test_gold_cannot_choose_a_final_claim_or_rescue_incomplete_output():
    r = record("Final answer: 3\nFinal answer: 4")
    for gold in ["3", "4", "42"]:
        s = v6.score_record(r, gold)
        assert s["parser_status"] == "conflicting" and not s["correct"]
    text = r"\boxed{3}" + "\nFinal answer: 4"
    assert v6.score_record(record(text), "3")["extracted_answer"] == "4"
    assert not v6.score_record(record(text), "3")["correct"]
    assert v6.score_record(record(text), "4")["correct"]
    for kwargs in [{"answer_truncated": True}, {"termination": "timeout"},
                   {"termination": "early_eos"}, {"termination": "reasoning_in_answer"}]:
        assert v6.score_record(record(text, **kwargs), "4")["parser_status"] == "incomplete"
    assert v6.parse_answer(text, incomplete=True) == (None, "incomplete")
    assert v5.parse_answer(text) == (None, "conflicting")  # Frozen v5 remains distinct.


@pytest.fixture
def isolated_run(tmp_path):
    dataset = tmp_path / "dataset"
    questions = [Question("q", "fixture-train", "repeat", "What is 2 plus 2?")]
    save_dataset(dataset, questions, {"q": "4"}, {"role": "repeat", "upstream": "train"})
    config = Config(backend="fake", data_dir=str(dataset), split="repeat", samples=1,
                       output_dir=str(tmp_path / "runs"))
    return run(config, progress=lambda _: None), dataset


def test_v6_cache_is_versioned_resumable_and_never_changes_v5(isolated_run):
    path, _ = isolated_run
    canonical = path / "scores.json"
    atomic_json(canonical, {"scoring_version": "numeric-v5", "frozen": True})
    before = canonical.read_bytes()
    artifact = v6.score_run(path)
    assert canonical.read_bytes() == before
    assert artifact["scoring_version"] == "numeric-v6"
    assert artifact["scoring_implementation_sha256"] == v6.implementation_digest()
    output = path / "scores.numeric-v6.json"
    saved = output.read_bytes()
    assert v6.score_run(path) == artifact and output.read_bytes() == saved
    artifact["scoring_implementation_sha256"] = "tampered"
    atomic_json(output, artifact)
    with pytest.raises(ValueError, match="cache identity changed"):
        v6.score_run(path)
    assert canonical.read_bytes() == before


def test_shared_or_sealed_gold_is_rejected_before_access(isolated_run, monkeypatch):
    path, dataset = isolated_run
    original = read_json(dataset / "manifest.json")
    monkeypatch.setattr(v6, "load_gold", lambda _: pytest.fail("Sealed/shared gold accessed"))
    for meta in [{"role": "test", "upstream": "test"}, {"role": "confirmation", "upstream": "train"},
                 {"source": "gsm8k"}]:
        changed = dict(original, metadata=meta)
        atomic_json(dataset / "manifest.json", changed)
        with pytest.raises(ValueError, match="isolated"):
            v6.score_run(path)
    atomic_json(dataset / "manifest.json", original)
    questions = read_json(dataset / "questions.json")
    questions[0]["prompt"] = "Changed prompt"
    atomic_json(dataset / "questions.json", questions)
    atomic_json(dataset / "manifest.json", dict(original, questions_sha256=digest(questions)))
    with pytest.raises(ValueError, match="outside this isolated run"):
        v6.score_run(path)


def test_incomplete_run_cannot_access_gold(isolated_run, monkeypatch):
    path, _ = isolated_run
    manifest, rows = load_run(path)
    rows[0]["status"] = "pending"
    monkeypatch.setattr(v6, "load_run", lambda _: (manifest, rows))
    monkeypatch.setattr(v6, "load_gold", lambda _: pytest.fail("Gold accessed before completion"))
    with pytest.raises(ValueError, match="complete run endpoint"):
        v6.score_run(path)


def test_real_repeat_requires_separate_frozen_protocol(isolated_run, monkeypatch):
    path, _ = isolated_run
    manifest, rows = load_run(path)
    manifest["identity"]["config"]["backend"] = "transformers"
    monkeypatch.setattr(v6, "load_run", lambda _: (manifest, rows))
    monkeypatch.setattr(v6, "load_gold", lambda _: pytest.fail("Unfrozen repeat gold opened"))
    with pytest.raises(ValueError, match="own frozen Phase 2"):
        v6.score_run(path)


def test_completed_bridge_arm_cannot_bypass_paired_endpoint(isolated_run, monkeypatch):
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
    monkeypatch.setattr(v6, "load_run", lambda _: (manifest, rows))
    protocol = {"arms": {arm: {"snapshot": {"run_dir": str(path.resolve()), "jobs": [1]}}
                         for arm in ["legacy", "v3"]}}
    monkeypatch.setattr(research_bridge, "read_protocol", lambda _: protocol)
    monkeypatch.setattr(research_bridge, "checked_arm", lambda _, __, arm:
                        (manifest, rows if arm == "legacy" else []))
    monkeypatch.setattr(v6, "load_gold", lambda _: pytest.fail("Incomplete paired bridge gold opened"))
    with pytest.raises(ValueError, match="Paired bridge endpoint"):
        v6.score_run(path)
