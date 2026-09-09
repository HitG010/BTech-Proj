"""Exercise actual generate hooks and stage orchestration without weights/network."""

import math
import time
from types import SimpleNamespace

import pytest
import torch
from transformers import GenerationConfig

from reasoning_budget.backend import RawLogprobRecorder, TransformersBackend
from reasoning_budget.config import from_dict
from reasoning_budget.records import Question
from reasoning_budget.runner import build_jobs


class Tokenizer:
    eos_token_id = 9

    def apply_chat_template(self, messages, **kwargs):
        self.thinking = kwargs["enable_thinking"]
        return "prompt"

    def encode(self, text, **kwargs):
        return [1, 2]

    def decode(self, tokens, skip_special_tokens=False):
        table = {
            3: "reason",
            4: "</think>",
            5: "Final answer: 7",
            6: " ",
            7: "<think>",
            9: "" if skip_special_tokens else "<|im_end|>",
        }
        return "".join(table.get(token, "?") for token in tokens)


class ScriptModel:
    config = SimpleNamespace(max_position_embeddings=10000)

    def __init__(self, scripts):
        self.scripts = iter(scripts)
        self.prefixes = []

    def generate(self, input_ids, max_new_tokens, stopping_criteria, **kwargs):
        self.prefixes.append(input_ids[0].tolist())
        sequence = input_ids
        scores = []
        for token in list(next(self.scripts))[:max_new_tokens]:
            sequence = torch.cat([sequence, torch.tensor([[token]])], dim=1)
            scores.append(torch.zeros(1, 10))
            if token == 9 or bool(stopping_criteria(sequence, None)[0]):
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
    b.eos_ids = [9]
    b.generation_configs = {m: GenerationConfig() for m in config.modes}
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
        ([[9]], "direct", "eos", 1),
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


def test_direct_confidence_is_post_warper_and_raw_is_absent_without_processor_calls():
    # The scripted model never invokes logits processors, so the raw estimate must
    # stay None rather than being fabricated from partial data.
    b, q, j = backend([[5, 9]], "direct")
    result = b.generate(q, j, time.monotonic() + 10)
    assert result.mean_generated_logprob == pytest.approx(-math.log(10))
    assert result.mean_generated_logprob_raw is None


def test_raw_logprob_recorder_scores_each_sampled_token_once():
    recorder = RawLogprobRecorder(torch)
    logits = torch.log(torch.tensor([[0.5, 0.25, 0.25]]))
    recorder(torch.tensor([[1]]), logits)  # step 1: nothing sampled yet
    recorder(torch.tensor([[1, 0]]), logits)  # token 0 was sampled under step-1 logits
    recorder.finish(2)  # final token 2 under step-2 logits
    assert recorder.values == pytest.approx([math.log(0.5), math.log(0.25)])
    assert recorder.previous is None


def test_closure_text_must_contain_the_think_marker():
    with pytest.raises(ValueError, match="closure_text"):
        from_dict({"closure_text": "stop"})
