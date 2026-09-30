"""Exercise actual generate hooks and stage orchestration without weights/network."""

import json
import math
import time
from types import SimpleNamespace

import pytest
import torch
from transformers import GenerationConfig

from reasoning_budget.backend import (
    GENERATION_PROTOCOL,
    FakeBackend,
    RawLogprobRecorder,
    TransformersBackend,
    normalize_eos_ids,
)
from reasoning_budget.config import from_dict
from reasoning_budget.records import GenerationResult, Question
from reasoning_budget.runner import build_jobs


class Tokenizer:
    eos_token_id = 9
    pad_token_id = 0
    bos_token_id = 0
    chat_template = "fake chat template"

    def apply_chat_template(self, messages, **kwargs):
        self.thinking = kwargs["enable_thinking"]
        return "prompt"

    def encode(self, text, **kwargs):
        if text == "</think>":
            return [4]
        if text == "</think>\n\n":
            return [4, 6]
        return [1, 2]

    def decode(self, tokens, skip_special_tokens=False):
        table = {
            3: "reason",
            4: "</think>",
            5: "Final answer: 7",
            6: " ",
            7: "<think>",
            9: "" if skip_special_tokens else "<|im_end|>",
            10: "" if skip_special_tokens else "<|endoftext|>",
        }
        return "".join(table.get(token, "?") for token in tokens)


class ScriptModel:
    config = SimpleNamespace(max_position_embeddings=10000)

    def __init__(self, scripts, invoke_processors=False, processor_steps=None):
        self.scripts = iter(scripts)
        self.prefixes = []
        self.invoke_processors = invoke_processors
        self.processor_steps = processor_steps
        self.processor_preserved_scores = True

    def generate(self, input_ids, max_new_tokens, stopping_criteria, **kwargs):
        self.prefixes.append(input_ids[0].tolist())
        sequence = input_ids
        scores = []
        for step, token in enumerate(list(next(self.scripts))[:max_new_tokens]):
            processor = kwargs.get("logits_processor")
            if self.invoke_processors and processor and (
                self.processor_steps is None or step < self.processor_steps
            ):
                raw = torch.arange(11, dtype=torch.float32).unsqueeze(0)
                unchanged = raw.clone()
                self.processor_preserved_scores &= torch.equal(processor(sequence, raw), unchanged)
            sequence = torch.cat([sequence, torch.tensor([[token]])], dim=1)
            scores.append(torch.zeros(1, 11))
            eos_ids = kwargs["generation_config"].eos_token_id
            if token in eos_ids or bool(stopping_criteria(sequence, None)[0]):
                break
        return SimpleNamespace(sequences=sequence, scores=scores)


def backend(scripts, mode="thinking", reasoning_tokens=4, answer_tokens=3):
    config = from_dict(
        {
            "backend": "fake",
            "model": {"device": "cpu", "dtype": "float32"},
            "reasoning_tokens": reasoning_tokens,
            "answer_tokens": answer_tokens,
        }
    )
    b = object.__new__(TransformersBackend)
    b.config, b.torch, b.tokenizer = config, torch, Tokenizer()
    b.model, b.close_id, b.closure = ScriptModel(scripts), 4, [4, 6]
    b.eos_ids = [9, 10]
    b.generation_configs = {m: GenerationConfig(eos_token_id=b.eos_ids) for m in config.modes}
    question = Question("q", "test", "smoke", "Question?")
    job = next(j for j in build_jobs(config, [question], {"closure_tokens": 2}) if j.mode == mode)
    return b, question, job


def test_natural_closure_stops_before_answer_and_continues_same_assistant():
    b, q, j = backend([[7, 3, 4, 5], [5, 9]])
    result = b.generate(q, j, time.monotonic() + 10)
    assert result.reasoning_tokens == 3
    assert result.answer_tokens == 2
    assert result.final_answer == "Final answer: 7"
    assert result.reasoning == "reason"
    assert not result.forced_closure
    assert result.termination == "eos"
    assert b.model.prefixes == [[1, 2], [1, 2, 7, 3, 4]]


def test_forced_closure_separate_tokens_and_raw_reconstruction():
    b, q, j = backend([[3, 3, 3, 3], [5, 9]])
    result = b.generate(q, j, time.monotonic() + 10)
    assert result.forced_closure
    assert result.inserted_tokens == 2
    assert result.reasoning_tokens == 4
    assert result.answer_tokens == 2
    assert b.model.prefixes[1] == [1, 2, 3, 3, 3, 3, 4, 6]
    assert "</think>" not in result.raw_output
    assert "</think>" in result.metadata["effective_output"]
    assert result.elapsed_seconds >= result.reasoning_seconds + result.answer_seconds


@pytest.mark.parametrize(
    "scripts,mode,termination,answer_tokens",
    [
        ([[3, 9]], "thinking", "early_eos", 0),
        ([[3, 10]], "thinking", "early_eos", 0),
        ([[9]], "direct", "eos", 1),
        ([[5, 10]], "direct", "eos", 2),
        ([[5, 6, 6, 6]], "direct", "answer_limit", 3),
        ([[7, 5, 9]], "direct", "reasoning_in_answer", 3),
    ],
)
def test_termination(scripts, mode, termination, answer_tokens):
    b, q, j = backend(scripts, mode)
    result = b.generate(q, j, time.monotonic() + 10)
    assert result.termination == termination
    assert result.answer_tokens == answer_tokens
    assert result.answer_truncated == (termination == "answer_limit")
    if termination in {"early_eos", "reasoning_in_answer"}:
        assert not result.final_answer


def test_expired_deadline_does_not_start_a_stage():
    b, q, j = backend([])
    result = b.generate(q, j, time.monotonic() - 1)
    assert result.termination == "timeout"
    assert not b.model.prefixes


def test_time_hook_stops_running_stage():
    b, _, _ = backend([[3, 3, 3, 3]])
    tokens, reason, _, _, _ = b._stage([1], 4, "thinking", time.monotonic() - 1)
    assert len(tokens) == 1
    assert reason == "timeout"


def test_normalize_eos_ids_accepts_scalar_or_list_and_rejects_invalid_values():
    assert normalize_eos_ids(9, [10, 9, None]) == [9, 10]
    assert normalize_eos_ids(None, 10) == [10]
    for values in [(None, None), (9, "10"), (9, True), (9, [-1])]:
        with pytest.raises(ValueError, match="EOS"):
            normalize_eos_ids(*values)


def test_backend_metadata_uses_checkpoint_eos_and_preserves_zero_pad_id(tmp_path, monkeypatch):
    import huggingface_hub
    from transformers import AutoTokenizer

    for name, value in [
        ("config.json", {"bos_token_id": 7}),
        ("tokenizer_config.json", {}),
        ("generation_config.json", {"eos_token_id": [10, 9, 10]}),
    ]:
        (tmp_path / name).write_text(json.dumps(value))
    monkeypatch.setattr(
        huggingface_hub,
        "hf_hub_download",
        lambda *, filename, **_kwargs: str(tmp_path / filename),
    )
    monkeypatch.setattr(AutoTokenizer, "from_pretrained", lambda *_args, **_kwargs: Tokenizer())
    config = from_dict(
        {
            "backend": "transformers",
            "model": {"device": "cpu", "dtype": "float32", "local_files_only": True},
        }
    )
    b = TransformersBackend(config)
    assert b.closure == [4, 6]
    assert b.eos_ids == [9, 10]
    assert b.metadata["generation_protocol"] == GENERATION_PROTOCOL
    assert b.metadata["closure_text"] == "</think>\n\n"
    assert b.metadata["eos_token_ids"] == [9, 10]
    assert all(c.eos_token_id == [9, 10] for c in b.generation_configs.values())
    assert all(c.pad_token_id == 0 and c.bos_token_id == 0 for c in b.generation_configs.values())
    assert FakeBackend(config).metadata["generation_protocol"] == GENERATION_PROTOCOL
    assert FakeBackend(config).metadata["closure_text"] == config.closure_text


@pytest.mark.parametrize("generation_config", [None, {}])
def test_model_only_eos_survives_missing_generation_declaration(
    tmp_path, monkeypatch, generation_config
):
    import huggingface_hub
    from huggingface_hub.utils import LocalEntryNotFoundError
    from transformers import AutoTokenizer

    (tmp_path / "config.json").write_text(json.dumps({"eos_token_id": [11, 9]}))
    (tmp_path / "tokenizer_config.json").write_text("{}")
    if generation_config is not None:
        (tmp_path / "generation_config.json").write_text(json.dumps(generation_config))

    def local_file(*, filename, **_kwargs):
        if filename == "generation_config.json" and generation_config is None:
            raise LocalEntryNotFoundError("not cached")
        return str(tmp_path / filename)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", local_file)
    monkeypatch.setattr(AutoTokenizer, "from_pretrained", lambda *_args, **_kwargs: Tokenizer())
    config = from_dict(
        {
            "backend": "transformers",
            "model": {"device": "cpu", "dtype": "float32", "local_files_only": True},
        }
    )
    b = TransformersBackend(config)
    assert b.eos_ids == [9, 11]
    assert b.metadata["eos_token_ids"] == [9, 11]
    assert all(c.eos_token_id == [9, 11] for c in b.generation_configs.values())


def test_post_warper_confidence_remains_canonical_when_raw_hook_is_absent():
    b, q, j = backend([[5, 9]], "direct")
    result = b.generate(q, j, time.monotonic() + 10)
    assert result.mean_generated_logprob == pytest.approx(-math.log(11))
    assert result.mean_generated_logprob_raw is None
    old = result.to_dict()
    old.pop("mean_generated_logprob_raw")
    assert GenerationResult(**old).mean_generated_logprob_raw is None
    assert GenerationResult(**old).metadata == result.metadata


def test_raw_likelihood_is_finite_and_processor_does_not_change_sampling_scores():
    b, q, j = backend([[5, 9]], "direct")
    b.model = ScriptModel([[5, 9]], invoke_processors=True)
    result = b.generate(q, j, time.monotonic() + 10)
    raw = torch.arange(11, dtype=torch.float32)
    expected = torch.log_softmax(raw, dim=0)[[5, 9]].mean().item()
    assert result.mean_generated_logprob_raw == pytest.approx(expected)
    assert math.isfinite(result.mean_generated_logprob_raw)
    assert result.mean_generated_logprob == pytest.approx(-math.log(11))
    assert result.mean_generated_logprob_raw != result.mean_generated_logprob
    assert b.model.processor_preserved_scores


def test_raw_recorder_scores_each_sampled_token_once():
    recorder = RawLogprobRecorder(torch)
    logits = torch.log(torch.tensor([[0.5, 0.25, 0.25]]))
    recorder(torch.tensor([[1]]), logits)
    recorder(torch.tensor([[1, 0]]), logits)
    recorder.finish(2)
    assert recorder.values == pytest.approx([math.log(0.5), math.log(0.25)])
    assert recorder.previous is None


def test_direct_confidence_rejects_missing_token_scores():
    class MissingScores(ScriptModel):
        def generate(self, *args, **kwargs):
            output = super().generate(*args, **kwargs)
            output.scores = output.scores[:1]
            return output

    b, q, j = backend([[5, 9]], "direct")
    b.model = MissingScores([[5, 9]])
    with pytest.raises(ValueError, match="one score row"):
        b.generate(q, j, time.monotonic() + 10)


def test_raw_confidence_rejects_partially_observed_generation():
    b, q, j = backend([[5, 9]], "direct")
    b.model = ScriptModel([[5, 9]], invoke_processors=True, processor_steps=1)
    with pytest.raises(ValueError, match="every generated token"):
        b.generate(q, j, time.monotonic() + 10)
