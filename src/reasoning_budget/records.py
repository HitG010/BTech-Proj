"""Gold-free inference record types."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Question:
    id: str
    source: str
    split: str
    prompt: str
    answer_type: str = "number"

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GenerationJob:
    id: str
    question_id: str
    mode: str
    sample: int
    seed: int
    max_tokens: int
    identity: dict

    def to_dict(self):
        return asdict(self)


@dataclass
class GenerationResult:
    raw_output: str
    reasoning: str
    final_answer: str
    prompt_tokens: int
    reasoning_tokens: int
    answer_tokens: int
    inserted_tokens: int
    elapsed_seconds: float
    reasoning_seconds: float
    answer_seconds: float
    closure_seconds: float
    forced_closure: bool
    answer_truncated: bool
    termination: str
    mean_generated_logprob: float | None = None
    mean_generated_logprob_raw: float | None = None
    metadata: dict | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ScoredResult:
    job_id: str
    question_id: str
    mode: str
    extracted_answer: str | None
    correct: bool
    parser_status: str
    scoring_version: str

    def to_dict(self):
        return asdict(self)
