"""Strict experiment configuration; paths are relative to the invocation directory."""

import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml


@dataclass
class Decoder:
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20


@dataclass
class Model:
    name: str = "Qwen/Qwen3-1.7B"
    revision: str = "main"
    tokenizer_revision: str = "main"
    device: str = "mps"
    dtype: str = "float16"
    attention: str = "sdpa"
    cache_dir: str = ".cache/huggingface"
    local_files_only: bool = False


@dataclass
class Limits:
    max_tokens: int = 30000
    max_elapsed_seconds: float = 3600
    job_seconds: float = 600
    max_consecutive_failures: int = 3


@dataclass
class Config:
    name: str = "smoke"
    backend: str = "transformers"
    seed: int = 20260909
    data_dir: str = "artifacts/data/fixtures"
    split: str = "smoke"
    output_dir: str = "artifacts/runs"
    samples: int = 1
    modes: list[str] = field(default_factory=lambda: ["direct", "thinking"])
    answer_tokens: int = 256
    reasoning_tokens: int = 2048
    prompt_suffix: str = "In your final response, give only the numerical answer in \\boxed{}."
    closure_text: str = "</think>\n\n"
    model: Model = field(default_factory=Model)
    limits: Limits = field(default_factory=Limits)
    direct: Decoder = field(default_factory=Decoder)
    thinking: Decoder = field(default_factory=lambda: Decoder(0.6, 0.95, 20))

    def to_dict(self):
        return asdict(self)

    def validate(self):
        if self.backend not in {"fake", "transformers"}:
            raise ValueError("backend must be fake or transformers")
        if self.model.device not in {"cpu", "mps", "cuda"}:
            raise ValueError("model.device must be cpu, mps, or cuda; no implicit fallback")
        if self.model.dtype not in {"float16", "float32", "bfloat16"}:
            raise ValueError("model.dtype must be float16, float32, or bfloat16")
        if self.model.attention not in {"sdpa", "eager"}:
            raise ValueError("model.attention must be sdpa or eager")
        if (
            not isinstance(self.modes, list)
            or not self.modes
            or any(mode not in {"direct", "thinking"} for mode in self.modes)
            or len(set(self.modes)) != len(self.modes)
        ):
            raise ValueError("modes must be a nonempty unique list of direct/thinking")
        for name, value in [
            ("samples", self.samples),
            ("answer_tokens", self.answer_tokens),
            ("reasoning_tokens", self.reasoning_tokens),
            ("limits.max_tokens", self.limits.max_tokens),
            ("limits.max_consecutive_failures", self.limits.max_consecutive_failures),
        ]:
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.closure_text, str) or "</think>" not in self.closure_text:
            raise ValueError("closure_text must be a string containing </think>")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for name in ["max_elapsed_seconds", "job_seconds"]:
            _positive(f"limits.{name}", getattr(self.limits, name))
        for mode in ["direct", "thinking"]:
            decoder = getattr(self, mode)
            _positive(f"{mode}.temperature", decoder.temperature)
            _positive(f"{mode}.top_p", decoder.top_p)
            if decoder.top_p > 1 or type(decoder.top_k) is not int or decoder.top_k < 1:
                raise ValueError(f"{mode}: top_p must be <= 1 and top_k a positive integer")
        for obj, names in [
            (self, ["name", "data_dir", "split", "output_dir", "prompt_suffix"]),
            (self.model, ["name", "revision", "tokenizer_revision", "cache_dir"]),
        ]:
            for name in names:
                if not isinstance(getattr(obj, name), str) or not getattr(obj, name).strip():
                    raise ValueError(f"{name} must be a nonempty string")
        if type(self.model.local_files_only) is not bool:
            raise ValueError("model.local_files_only must be a boolean")
        return self


def _positive(name, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a positive finite number")


def _construct(cls, values, name):
    if not isinstance(values, dict):
        raise ValueError(f"{name} must be a mapping")
    unknown = set(values) - {f.name for f in fields(cls)}
    if unknown:
        raise ValueError(f"Unknown {name} keys: {', '.join(sorted(unknown))}")
    return cls(**values)


def from_dict(values):
    if not isinstance(values, dict):
        raise ValueError("configuration must be a YAML mapping")
    values = dict(values)
    for key, cls in [
        ("model", Model),
        ("limits", Limits),
        ("direct", Decoder),
        ("thinking", Decoder),
    ]:
        if key in values:
            defaults = asdict(getattr(Config(), key))
            if not isinstance(values[key], dict):
                raise ValueError(f"{key} must be a mapping")
            values[key] = _construct(cls, defaults | values[key], key)
    return _construct(Config, values, "configuration").validate()


def load_config(path):
    try:
        return from_dict(yaml.safe_load(Path(path).read_text()))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
