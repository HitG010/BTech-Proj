"""Batch-one Transformers generation with separate reasoning and answer budgets."""

import importlib.metadata
import os
import platform
import random
import time
from dataclasses import asdict
from numbers import Integral
from pathlib import Path

from .records import GenerationResult
from .storage import digest, read_json

GENERATION_PROTOCOL = "qwen3-boxed-budget-v3"


def normalize_eos_ids(*sources):
    """Combine tokenizer and checkpoint EOS IDs without accepting malformed IDs."""
    ids = set()
    for source in sources:
        values = source if isinstance(source, (list, tuple)) else [source]
        for value in values:
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
                raise ValueError("EOS token IDs must be nonnegative integers")
            ids.add(int(value))
    if not ids:
        raise ValueError("Checkpoint and tokenizer provide no EOS token ID")
    return sorted(ids)


class RawLogprobRecorder:
    """Record selected-token likelihood before sampling warpers, one logit row at a time."""

    def __init__(self, torch):
        self.torch, self.previous, self.values = torch, None, []

    def __call__(self, input_ids, scores):
        if self.previous is not None:
            self.values.append(self._logprob(int(input_ids[0, -1])))
        self.previous = scores[0].detach().float().clone()
        return scores

    def _logprob(self, token):
        return float(self.torch.log_softmax(self.previous, dim=-1)[token])

    def finish(self, last_token):
        if self.previous is not None:
            self.values.append(self._logprob(last_token))
            self.previous = None


def environment():
    import torch

    packages = {}
    for name in [
        "torch",
        "transformers",
        "datasets",
        "numpy",
        "scipy",
        "scikit-learn",
        "pandas",
        "matplotlib",
        "PyYAML",
        "huggingface-hub",
        "tokenizers",
    ]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built(),
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "mps_fallback": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0"),
    }


class FakeBackend:
    """Integrity-only backend. Does not read gold or solve questions."""

    def __init__(self, config):
        self.config = config
        self.metadata = {
            "backend": "fake",
            "generation_protocol": GENERATION_PROTOCOL,
            "model_revision": "fake-v1",
            "tokenizer_revision": "fake-v1",
            "chat_template": "fake-v1",
            "closure_text": config.closure_text,
            "closure_tokens": 1,
            "device": "cpu",
            "dtype": "float32",
        }

    def load(self):
        pass

    def generate(self, question, job, deadline):
        thinking = job.mode == "thinking"
        return GenerationResult(
            raw_output="<think>Fixture only.</think>Final answer: 0"
            if thinking
            else "Final answer: 0",
            reasoning="Fixture only." if thinking else "",
            final_answer="Final answer: 0",
            prompt_tokens=10,
            reasoning_tokens=3 if thinking else 0,
            answer_tokens=5,
            inserted_tokens=0,
            elapsed_seconds=0.001,
            reasoning_seconds=0,
            answer_seconds=0.001,
            closure_seconds=0,
            forced_closure=False,
            answer_truncated=False,
            termination="eos",
            metadata={"synthetic": True},
        )


class TransformersBackend:
    def __init__(self, config):
        import torch
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError
        from transformers import AutoTokenizer, GenerationConfig

        self.config, self.torch, self.model = config, torch, None
        device = config.model.device
        if device == "mps" and not torch.backends.mps.is_available():
            raise ValueError("MPS is unavailable; select an explicit alternative in a new config")
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA was explicitly requested but is unavailable")
        if device == "mps" and os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") != "0":
            raise ValueError("Unset PYTORCH_ENABLE_MPS_FALLBACK to prevent hidden CPU fallback")
        shared = {
            "repo_id": config.model.name,
            "cache_dir": config.model.cache_dir,
            "local_files_only": config.model.local_files_only,
        }
        model_file = hf_hub_download(
            filename="config.json", revision=config.model.revision, **shared
        )
        tokenizer_file = hf_hub_download(
            filename="tokenizer_config.json", revision=config.model.tokenizer_revision, **shared
        )
        try:
            generation_file = hf_hub_download(
                filename="generation_config.json", revision=config.model.revision, **shared
            )
        except EntryNotFoundError:
            generation_file = None
        model_revision = Path(model_file).parent.name
        model_config = read_json(model_file)
        tokenizer_revision = Path(tokenizer_file).parent.name
        self.tokenizer = AutoTokenizer.from_pretrained(
            config.model.name,
            revision=tokenizer_revision,
            cache_dir=config.model.cache_dir,
            local_files_only=config.model.local_files_only,
            trust_remote_code=False,
        )
        if not self.tokenizer.chat_template:
            raise ValueError("Checkpoint has no chat template")
        close = self.tokenizer.encode("</think>", add_special_tokens=False)
        if len(close) != 1:
            raise ValueError("This backend requires Qwen's single-token </think> marker")
        self.close_id = close[0]
        self.closure = self.tokenizer.encode(config.closure_text, add_special_tokens=False)
        if self.close_id not in self.closure:
            raise ValueError("closure_text must encode to a sequence containing </think>")
        declared_eos = read_json(generation_file).get("eos_token_id") if generation_file else None
        self.eos_ids = normalize_eos_ids(
            self.tokenizer.eos_token_id, model_config.get("eos_token_id"), declared_eos
        )
        pad_id = self.tokenizer.pad_token_id
        if pad_id is None:
            pad_id = self.eos_ids[0]
        bos_id = self.tokenizer.bos_token_id
        if bos_id is None:
            bos_id = model_config.get("bos_token_id")
        self.generation_configs = {}
        for mode in config.modes:
            self.generation_configs[mode] = GenerationConfig(
                do_sample=True,
                **asdict(getattr(config, mode)),
                min_p=0.0,
                repetition_penalty=1.0,
                num_beams=1,
                use_cache=True,
                eos_token_id=self.eos_ids,
                pad_token_id=pad_id,
                bos_token_id=bos_id,
            )
        self.metadata = {
            "backend": "transformers",
            "generation_protocol": GENERATION_PROTOCOL,
            "model_name": config.model.name,
            "model_revision": model_revision,
            "tokenizer_revision": tokenizer_revision,
            "chat_template": self.tokenizer.chat_template,
            "chat_template_sha256": digest(self.tokenizer.chat_template),
            "closure_text": config.closure_text,
            "closure_tokens": len(self.closure),
            "closure_ids": self.closure,
            "eos_token_ids": self.eos_ids,
            "device": device,
            "dtype": config.model.dtype,
            "attention": config.model.attention,
            "batch_size": 1,
            "continuation": "same-assistant-full-prefix-prefill",
            "decoder_configs": {m: c.to_dict() for m, c in self.generation_configs.items()},
        }

    def load(self):
        from transformers import AutoModelForCausalLM

        if self.model is None:
            self.model = (
                AutoModelForCausalLM.from_pretrained(
                    self.config.model.name,
                    revision=self.metadata["model_revision"],
                    cache_dir=self.config.model.cache_dir,
                    trust_remote_code=False,
                    local_files_only=self.config.model.local_files_only,
                    dtype=getattr(self.torch, self.config.model.dtype),
                    attn_implementation=self.config.model.attention,
                )
                .to(self.config.model.device)
                .eval()
            )

    def _sync(self):
        if self.config.model.device == "mps":
            self.torch.mps.synchronize()
        elif self.config.model.device == "cuda":
            self.torch.cuda.synchronize()

    def _stage(self, prefix, limit, mode, deadline, stop_on_close=False, confidence=False):
        from transformers import LogitsProcessorList, StoppingCriteria, StoppingCriteriaList

        torch = self.torch
        close_id = self.close_id

        class Stop(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return time.monotonic() >= deadline or (
                    stop_on_close and int(input_ids[0, -1]) == close_id
                )

        recorder = RawLogprobRecorder(torch) if confidence else None
        input_ids = torch.tensor([prefix], dtype=torch.long, device=self.config.model.device)
        self._sync()
        started = time.monotonic()
        with torch.inference_mode():
            output = self.model.generate(
                input_ids=input_ids,
                attention_mask=torch.ones_like(input_ids),
                generation_config=self.generation_configs[mode],
                max_new_tokens=limit,
                stopping_criteria=StoppingCriteriaList([Stop()]),
                logits_processor=LogitsProcessorList([recorder]) if recorder else None,
                return_dict_in_generate=True,
                output_scores=confidence,
            )
        self._sync()
        elapsed = time.monotonic() - started
        tokens = output.sequences[0, len(prefix) :].tolist()
        logprob = logprob_raw = None
        if confidence and tokens:
            if output.scores is None or len(output.scores) != len(tokens):
                raise ValueError("Direct confidence needs one score row per generated token")
            # Scores are after the configured temperature / top-k / top-p warpers.
            values = [
                float(torch.log_softmax(scores[0].float(), dim=-1)[token])
                for scores, token in zip(output.scores, tokens)
            ]
            logprob = sum(values) / len(values)
            recorder.finish(tokens[-1])
            if recorder.values:
                if len(recorder.values) != len(tokens):
                    raise ValueError("Raw confidence hook did not observe every generated token")
                logprob_raw = sum(recorder.values) / len(recorder.values)
        if tokens and tokens[-1] == self.close_id and stop_on_close:
            reason = "close"
        elif tokens and tokens[-1] in self.eos_ids:
            reason = "eos"
        elif time.monotonic() >= deadline:
            reason = "timeout"
        else:
            reason = "limit"
        return tokens, reason, elapsed, logprob, logprob_raw

    def generate(self, question, job, deadline):
        import numpy as np

        random.seed(job.seed)
        np.random.seed(job.seed)
        self.torch.manual_seed(job.seed)
        if self.config.model.device == "mps":
            self.torch.mps.manual_seed(job.seed)
        if self.config.model.device == "cuda":
            self.torch.cuda.manual_seed_all(job.seed)
        self._sync()
        started = time.monotonic()
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": question.prompt + "\n\n" + self.config.prompt_suffix}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=job.mode == "thinking",
        )
        prefix = self.tokenizer.encode(text, add_special_tokens=False)
        if len(prefix) + job.max_tokens > self.model.config.max_position_embeddings:
            raise ValueError(
                "Prompt and output allowances exceed model context; no truncation allowed"
            )
        prompt_tokens = len(prefix)
        reasoning, answer, inserted = [], [], []
        reasoning_seconds = answer_seconds = closure_seconds = 0.0
        forced, truncated, logprob, logprob_raw = False, False, None, None
        termination = "timeout"
        if time.monotonic() < deadline and job.mode == "thinking":
            reasoning, reason, reasoning_seconds, _, _ = self._stage(
                prefix, self.config.reasoning_tokens, job.mode, deadline, stop_on_close=True
            )
            prefix += reasoning
            if reason == "limit":
                closure_started = time.monotonic()
                inserted = self.closure[:]
                prefix += inserted
                forced = True
                closure_seconds = time.monotonic() - closure_started
            elif reason in {"eos", "timeout"}:
                termination = "early_eos" if reason == "eos" else "timeout"
                return self._result(
                    prompt_tokens,
                    reasoning,
                    answer,
                    inserted,
                    started,
                    reasoning_seconds,
                    0.0,
                    closure_seconds,
                    forced,
                    False,
                    termination,
                    None,
                    None,
                )
        if time.monotonic() < deadline:
            answer, reason, answer_seconds, logprob, logprob_raw = self._stage(
                prefix,
                self.config.answer_tokens,
                job.mode,
                deadline,
                confidence=job.mode == "direct",
            )
            truncated = reason == "limit"
            termination = "answer_limit" if truncated else reason
        return self._result(
            prompt_tokens,
            reasoning,
            answer,
            inserted,
            started,
            reasoning_seconds,
            answer_seconds,
            closure_seconds,
            forced,
            truncated,
            termination,
            logprob,
            logprob_raw,
        )

    def _result(
        self,
        prompt_tokens,
        reasoning,
        answer,
        inserted,
        started,
        reasoning_seconds,
        answer_seconds,
        closure_seconds,
        forced,
        truncated,
        termination,
        logprob,
        logprob_raw,
    ):
        decode = self.tokenizer.decode
        final_answer = decode(answer, skip_special_tokens=True).strip()
        if "<think>" in final_answer or "</think>" in final_answer:
            termination = "reasoning_in_answer"
            final_answer = ""
        memory = {}
        if self.config.model.device == "mps":
            memory = {
                "mps_allocated_bytes": self.torch.mps.current_allocated_memory(),
                "mps_driver_bytes": self.torch.mps.driver_allocated_memory(),
            }
        elif self.config.model.device == "cuda":
            memory = {"cuda_peak_allocated_bytes": self.torch.cuda.max_memory_allocated()}
        return GenerationResult(
            raw_output=decode(reasoning + answer, skip_special_tokens=False),
            reasoning=decode(reasoning, skip_special_tokens=True)
            .replace("<think>", "")
            .replace("</think>", "")
            .strip(),
            final_answer=final_answer,
            prompt_tokens=prompt_tokens,
            reasoning_tokens=len(reasoning),
            answer_tokens=len(answer),
            inserted_tokens=len(inserted),
            elapsed_seconds=time.monotonic() - started,
            reasoning_seconds=reasoning_seconds,
            answer_seconds=answer_seconds,
            closure_seconds=closure_seconds,
            forced_closure=forced,
            answer_truncated=truncated,
            termination=termination,
            mean_generated_logprob=logprob,
            mean_generated_logprob_raw=logprob_raw,
            metadata={
                "reasoning_token_ids": reasoning,
                "answer_token_ids": answer,
                "inserted_token_ids": inserted,
                "memory": memory,
                "effective_output": decode(
                    reasoning + inserted + answer, skip_special_tokens=False
                ),
                "continuation_prefill_included_in_answer_seconds": True,
            },
        )


def make_backend(config):
    return FakeBackend(config) if config.backend == "fake" else TransformersBackend(config)
