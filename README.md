# When should a small model think? Learned deferral vs. confidence

Hybrid reasoning models such as Qwen3 can answer directly or think first. This
repository tests a cheap two-stage policy on GSM8K: write a direct draft, then
pay for a fresh thinking solve only when the draft looks unreliable. The
question is whether a **learned** deferral rule picks those escalations better
than a simple **confidence threshold** on the draft, when the utility charges
for both calls.

## Result

It did not, on these data.

- **Qwen3-1.7B, 50 questions × 8 draws per mode.** Thinking fixes 30 of 400
  direct drafts and breaks 10. Confidence deferral reaches 92.75% accuracy at
  628 output tokens per question (direct alone: 89.5% at 221; always thinking:
  94.5% at 1,611). The predeclared learned rule reaches 89.0% at 757 and fails
  four of its five success criteria. Nine follow-up rules and a simulated
  two-draft agreement rule also fail to beat confidence. With refitting
  variation included, the learner's gap to confidence is not distinguishable
  from zero: a missing gain, not a demonstrated loss.
- **Qwen3-0.6B vs Qwen3-1.7B, 64 more questions.** Confidence deferral helps the
  smaller model, mostly because thinking itself helps it; for the larger
  model it does not pay.

These are small, reused development panels, and every predeclared criterion is
reported, including the failed ones. Nothing here claims a new method.

## The paper

- Short paper (workshop length): [`papers/thinking-selection/short/`](papers/thinking-selection/short/README.md)
- Full technical report (manuscript v0.8): [`papers/thinking-selection/manuscript.md`](papers/thinking-selection/manuscript.md)
- Research map, with every study and its record: [`docs/README.md`](docs/README.md)

## Reproducing the paper's numbers

[`scripts/reproduce_paper.py`](scripts/reproduce_paper.py) rebuilds every table
value, figure point, and quoted number of the short paper from one cache file
of scored outcomes and recorded decisions; it never runs a model or opens a
reference answer. See the [guide](docs/reproduce-from-cache.md). On the real
cache all 195 checks pass ([report](docs/reproduction-report.md)). The cache is
not yet published.

```sh
PYTHONPATH=src .venv/bin/python -m scripts.reproduce_paper check --cache PATH/TO/paper-cache.json
```

## Repository layout

| Path | Contents |
|---|---|
| `src/reasoning_budget/` | Package: generation backend, prompts, scorers (numeric-v5/v7), records, CLI `rb` |
| `scripts/` | Entry points for each frozen study, audit, and verification |
| `tests/` | Offline tests (no model download or network) |
| `configs/` | Generation configurations |
| `docs/` | Protocols, result records, and reports for every study ([map](docs/README.md)) |
| `papers/thinking-selection/` | Manuscript, short paper, figures, bibliography |
| `docs/history/`, `papers/thinking-selection/history/` | Superseded plans, logs, and review memos |

Raw responses and score caches live in the ignored `artifacts/` directory on
the author's machine. Each study froze its protocol, grid, endpoints, and
criteria before running and records source, input, and output hashes.

## Setup

Python 3.11 is managed by `uv`; run commands from the repository root.

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv sync --locked --python 3.11 --python-preference only-managed
uv run --locked rb doctor
uv run --locked pytest
```

`rb doctor` reports Python and package versions and MPS/CUDA availability. The
generation experiments ran locally (Apple-silicon MPS, batch size one); the
original command walkthrough is kept in
[`docs/history/root-readme-2026-11-05.md`](docs/history/root-readme-2026-11-05.md).

## Data roles

All questions are GSM8K training rows assigned to frozen roles. The official
GSM8K test split stayed sealed. Two confirmation allocations were prepared but
never run or opened: the predeclared criteria on the development panels failed
first.

## History

The old branch tips are tagged `archive/*`; the September pilot reports, the
agent handoff log, the milestone log (`plan.md`), and superseded plans are in
[`docs/history/`](docs/history/README.md).
