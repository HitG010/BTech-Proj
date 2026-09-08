# Reasoning budget experiments

A reproducible Qwen3-1.7B direct-versus-thinking experiment pipeline. This first
implementation covers [Milestones A–C](plan.md): offline scoring, local inference,
immutable GSM8K splits, resumable jobs, and a 100-question pilot. Controllers,
adaptive acquisition, and confirmation experiments are later work.

## Setup

Run commands from this repository root. Python 3.11 is managed by `uv`; the local
environment and download caches are ignored by Git. The lockfile pins dependencies
for Mac and Linux; CUDA wheels are resolved on Linux by PyTorch's platform packages.

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv sync --locked --python 3.11 --python-preference only-managed
uv run --locked rb doctor
uv run --locked pytest
```

Use `.venv/bin/rb` and `.venv/bin/pytest` directly for fully offline execution after
installation. `doctor` reports Python/package versions and MPS/CUDA availability.
Some application sandboxes hide the Mac GPU; run the same command in a normal
terminal or grant GPU access. Devices never change implicitly.

## Run the experiments

```sh
# Offline integrity check: fabricated outputs, no model or dataset download.
uv run --locked rb smoke --config configs/offline.yaml

# First real deliverable: 10 questions, one response per mode (20 jobs).
uv run --locked rb smoke --config configs/smoke.yaml

# Use the run directory printed by generation.
uv run --locked rb score artifacts/runs/RUN_ID
uv run --locked rb report artifacts/runs/RUN_ID --hourly-rate 1
uv run --locked rb audit artifacts/runs/RUN_ID --count 20

# Inspect all smoke responses before launching the pilot.
uv run --locked rb prepare gsm8k
uv run --locked rb generate --config configs/pilot.yaml
uv run --locked rb report artifacts/runs/PILOT_RUN_ID --hourly-rate 1
uv run --locked rb audit artifacts/runs/PILOT_RUN_ID --count 50
```

`--hourly-rate 1` means a **hypothetical $1/hour scenario**, not a provider quote or
a cloud launch. Reports project 1,100 questions × two samples × both modes by
default; customize with `--projection-questions` and `--projection-samples`.
Local MPS throughput cannot establish CUDA cost. Dollar estimates exclude idle
rental time, setup, repeated acquisition, and confirmation. Track actual billing
separately. Budget: $10 pilot, $50 main, $20 confirmation, $20 reserve. No command
creates a cloud instance or spends provider credits.

To include recorded billing in a report, create `RUN_DIR/billing.json` with
`{"currency": "USD", "actual_cloud_billing_usd": 0, "note": "Local run; no cloud used"}`,
or the actual invoiced total and explanatory note for a cloud run. Missing billing
stays unknown, rather than being inferred from token usage.

Review `audit.json` manually: set `reviewer`, then mark each reviewed row
`correct_score`, `model_failure`, or `scorer_defect` and explain it in `notes`.
Use `model_failure` when the parser correctly judges an incorrect, missing, or
truncated model answer. Use `scorer_defect` for extraction/scoring mistakes.
Fix scorer defects and regenerate/review the audit before accepting the report.
Audits bind to exact response checksums and scorer version. The pilot report stays
provisional until all jobs finish and at least 50 current responses are reviewed
with no unresolved scorer defects. A smoke audit has only 20 responses and does
not satisfy the pilot audit requirement. The program validates audit bookkeeping;
it cannot certify that a person actually read each response.

## Resume and compute limits

Repeat the exact generation command to resume. Valid completed jobs are skipped;
only failed, missing, or corrupt results are regenerated. Ctrl-C writes an explicit
failed attempt and exits at the current job. An advisory OS lock prevents concurrent
writers. Records are fsynced and atomically replaced, with SHA-256 checksums.
Temporary/incomplete writes are never treated as completed jobs. A corrupt budget
ledger stops the run so it cannot accidentally authorize extra computation.

Each job reserves its **maximum** possible generated plus inserted-closure tokens
before generation. Successful attempts release unused tokens. Failed attempts with
unknown token counts keep the entire reservation. Interrupted attempts remain
charged even when retried. Budgets persist across invocations. A changed resolved
configuration (including limits), device, precision, model/tokenizer revision,
software environment, or generation implementation creates a distinct run.
Changing a limit therefore does not extend an existing run; select limits before
launch. Job seeds depend on experiment seed, question content, mode, and sample,
so job order and interruption do not alter them. MPS/CUDA can still differ
numerically; results are identified separately, and bitwise cross-device
reproducibility is not claimed.

Elapsed limits count model/tokenizer setup and attempt time, excluding idle time
between invocations. A process killed without finalizing an attempt conservatively
charges its entire reserved job duration. Stopping hooks check the deadline after
each generated token; a single model forward, filesystem operation, or model
download cannot be preempted by this cooperative limit. Setup time is recorded
after model loading. A process killed during setup can leave unrecorded setup time.
Do not treat these controls as a cloud billing limit.

## Generation protocol

Batch size is one. The default is FP16 on MPS; set `model.device: cuda` explicitly
on a CUDA host, or `cpu`/`float32` for lightweight experimentation. There is no
automatic quantization, precision change, CPU fallback, or alternative engine.
Model and tokenizer revisions resolve to immutable Hugging Face commits, and the
full checkpoint chat template and effective decoder configuration are saved.
For offline resume, keep the same config and use `HF_HUB_OFFLINE=1` after the cache
is populated; changing `local_files_only` itself changes the experiment config.

The Qwen chat template receives `enable_thinking=False` for direct mode and `True`
for thinking mode. Both receive the same question and boxed-answer instruction.
Direct uses temperature 0.7, top-p 0.8, top-k 20 and at most 256 generated tokens.
Thinking uses temperature 0.6, top-p 0.95, top-k 20, with up to 2,048 reasoning
tokens and a separate 256-token answer allowance. These sampling defaults follow
the [official Qwen model card](https://huggingface.co/Qwen/Qwen3-1.7B).

The reasoning stage stops at the single-token `</think>` marker, EOS, deadline,
or reasoning limit. At the limit, it inserts `</think>\n\n` and continues the same
assistant prefix. An early EOS in reasoning is a model failure with no final
answer. The second `generate` call reprocesses the full prefix instead of reusing
a KV cache between calls; this deliberate implementation overhead is included in
answer-stage and total timings for both natural and forced closure. The pipeline
uses [Transformers generation and stopping hooks](https://huggingface.co/docs/transformers/main_classes/text_generation).

Generated token counts include control/EOS tokens; inserted closure tokens are
counted separately. `raw_output` contains only sampled tokens. `effective_output`
and stored token IDs reconstruct the response including inserted closure. Direct
mean token log-probability is calculated after the configured decoder warpers,
including EOS, for later confidence routing. Reasoning-stage score tensors are
not retained, keeping memory manageable.

## Artifacts and scoring

```text
artifacts/data/gsm8k/
  manifest.json       # revisions, frozen split IDs and checksums
  questions.json      # ID/source/split/prompt/type; no gold labels
  gold.json           # scoring-only answer map
artifacts/runs/RUN_ID/
  manifest.json       # complete identity and expected jobs
  resolved_config.json, environment.json, questions.json
  results/JOB_ID.json # checksum envelope around latest result or failure
  attempts/           # immutable attempt history and budget ledger
  sessions/           # setup timing
  status.json, scores.json, audit.json
  report/             # Markdown, JSON, CSV, PNG and PDF
```

GSM8K freezes 100 pilot, 400 training, and 100 validation questions from its
official training split and 500 from its official test split. Unicode-normalized,
case-folded, whitespace-collapsed duplicates are removed globally before sampling,
prioritizing official test questions. The upstream revision, seed, split algorithm,
and selected IDs are persisted. Existing datasets cannot be overwritten with a
different revision or split. The source is [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k).

Scoring parses only separated final answers using exact rational arithmetic.
Integers, decimals, fractions, scientific notation, negatives, thousands separators,
and nested LaTeX fraction boxes are supported. Conflicting explicit final answers
are unscorable. Without explicit markers, the sole numeric literal on the last
nonempty line is accepted; this conservative heuristic is versioned and audited.
Truncated answers are counted incorrect even when they contain a plausible number.
The parser never receives gold labels. Generation never opens `gold.json`.

Reports show completed denominators and pending/failed counts. Repeated samples
are averaged within questions; bootstrap intervals resample whole questions.
Paired differences use only questions with every requested sample in both modes.
Partial reports and synthetic runs cannot support accepted pilot conclusions.

## Verification and later work

```sh
uv run --locked pytest
uv run --locked ruff check src tests
```

Fast tests run without network or model weights. They exercise actual stopping
hooks with a scripted tiny model, token separation, termination cases, budgets,
interruption/resume, atomicity, split integrity, and whole-question statistics.
Real inference is an explicit smoke/pilot invocation, never part of `pytest`.
`rb fit`, `rb acquire`, and `rb evaluate` are deferred to Milestones D–F, after the
pilot establishes scoring and compute feasibility.
