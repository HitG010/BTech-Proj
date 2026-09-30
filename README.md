# Reasoning budget experiments

A reproducible Qwen3-1.7B direct-versus-thinking experiment pipeline. The
repository includes offline scoring, local inference, immutable GSM8K splits,
resumable jobs, pilot calibration, router studies, and a prepared confirmation
protocol. See the [research map](docs/README.md) for the current worktree layout,
results, the [active research roadmap](docs/research-roadmap.md) for phases and
decision gates, and the [plan](plan.md) for the milestone log.

The [completed pilot results](docs/pilot-results.md) and
[verification record](docs/verification.md) summarize the local runs and audit.
The [answer-cap calibration](docs/calibration-results.md) selects 512 answer
tokens for the full pilot confirmation; the original 256-token pilot is retained.

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

## Answer allowance calibration

The original pilot is preserved. Select 25 pilot questions by a fixed seeded
hash, without consulting outcomes, and compare its selected 256-token responses
with actual 512- and 1,024-token runs:

```sh
.venv/bin/rb calibrate prepare --baseline artifacts/runs/af1f1e56c5d453bbfd5e
HF_HUB_OFFLINE=1 .venv/bin/rb calibrate run artifacts/calibration/answer-cap-v1
.venv/bin/rb calibrate report artifacts/calibration/answer-cap-v1
# After all arms finish, export a stratified worksheet for a person to review.
.venv/bin/rb calibrate audit artifacts/calibration/answer-cap-v1 --count 50
# After freezing protocol-decision.json, run/resume the full confirmation.
HF_HUB_OFFLINE=1 .venv/bin/rb calibrate confirm artifacts/calibration/answer-cap-v1
```

`prepare` freezes `study.json`, a scoring-isolated subset, and resolved YAMLs.
The original question identities and generation seeds are preserved. `run`
executes the two longer-cap arms sequentially, retaining the same model,
tokenizer, prompt, decoder, precision, generation implementation, and environment.
It rejects an unmatched comparison before loading model weights. Each arm has a
two-hour elapsed limit and a token ceiling covering all maximum job reservations
plus 10% for explicit retries. Repeating the command resumes completed work.
No prefix-derived samples or estimated prefix runtimes enter the comparison.

`report` writes `report/summary.json` and `report/report.md` inside the study.
Accuracy and cap differences use paired whole-question bootstrap intervals;
the label-based retrospective routing headroom is explicitly exploratory.
Partial reports cannot establish protocol superiority. The original strict
scorer remains unchanged, and human review is recorded as pending. See the
[research rationale](docs/research-next-steps.md) for the decision checkpoint
before collecting controller-training traces.

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
and nested LaTeX fraction boxes are supported. Scorer `numeric-v3` also supports
exact repeating decimals written with LaTeX `\overline{}`. Conflicting explicit final answers
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
`rb routing` now provides an exploratory controller/baseline comparison from a
complete two-sample pilot. Dedicated `rb fit`, `rb acquire`, and `rb evaluate`
commands for the disjoint main study remain deferred; this pilot comparison
does not constitute final test evaluation.

The calibrated pipeline uses scorer `numeric-v4`, which fixes text Markdown
headings being mistaken for numerical `####` answer declarations. Strict
truncation and conflict rules are unchanged. Calibration direct accuracy is
72% after this fix; archived v3 reports show 68%. Original pilot and smoke
decisions were checked and remain unchanged. Confirmation automatically exports
separate results for questions used and not used to choose the answer allowance.

## Exploratory routing learnability

```sh
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  uv run --locked rb routing artifacts/runs/d00485799f1c8932bafa
```

Remove `HF_HUB_OFFLINE=1` for the first download of the pinned
`sentence-transformers/all-MiniLM-L6-v2` checkpoint. This command uses CPU
embeddings and cached Qwen responses; it never launches model generation.
It refuses the official test split and incomplete or stale-scored pilot runs.
See [results and next steps](docs/routing-learnability.md).

Outputs under `artifacts/routing/STUDY_ID/` include `report.md`, `curve.csv`,
`accuracy-cost.png`, a checksummed `study.json` with question-level outcomes and
fold identities, and portable `controller-fold-N.json` models. The study ID
includes response/score hashes, implementation, package versions, seed, and the
cost-preference grid. Feature caches include checkpoint revision and package
versions. Each outer fold fits its scaler and tunes alpha without its held-out
questions. Saved fold models can route new gold-free `Question` objects:

```python
from reasoning_budget.controller import Controller
from reasoning_budget.records import Question
from reasoning_budget.storage import verified

saved = verified("artifacts/routing/STUDY_ID/controller-fold-0.json")
router = Controller.from_dict(saved["controller"])
modes = router.route([Question("new", "user", "inference", "What is 13 + 29?")],
                     cost_preference=0.1)
```

These are exploratory fold models, not final frozen test policies. DART-SC-2 is
only a two-draft stage-one adaptation; full DART still needs additional traces.

## Disjoint stronger-router study

```sh
uv run --locked rb learnability prepare
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  uv run --locked rb learnability run artifacts/learnability/baselines-v1
# Standalone CPU operations after their required generation stages complete:
uv run --locked rb learnability fit artifacts/learnability/baselines-v1
uv run --locked rb learnability report artifacts/learnability/baselines-v1
```

`prepare` freezes the questions, generation configs, code/package identities,
settings grid and primary comparison. `run` serially generates train/tune data,
freezes the selected policies, generates a separate diagnostic partition, then
exports a report. Resume with the same command. A changed protocol or
implementation requires a new study directory. A second writer is rejected.

The study compares the original ridge-MSE router, utility-tuned ridge,
cosine-neighbor retrieval with shrinkage, and regret-weighted logistic heads.
Decision heads compare PCA dimensions 16/32/full and inverse regularization
0.1/1/10. Each model family selects one setting on tuning utility at lambda=.05;
held-out diagnostic outcomes cannot select settings. All transforms fit only
on training data. Confidence and DART-SC-2 escalation costs include their probes.

Models and selection histories are saved in checksummed `models.json`. For new
questions, pass a saved retrieval/decision/ridge model to
`reasoning_budget.stronger.route_questions(model, questions, preference)`; the
original ridge-MSE model uses `Controller.from_dict(...).route(...)`.

The scoring audit was explicitly waived by the user on 2026-09-18; its worksheet
remains pending and reports distinguish the waiver from completed human review.
See [study protocol and tracking](docs/stronger-router-study.md).

## First-draft continuation study

```sh
uv run --locked rb probe prepare
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 uv run --locked rb probe fit artifacts/probe/continuation-v1
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  uv run --locked rb probe run artifacts/probe/continuation-v1
```

This step reuses existing development traces, freezes three-action continuation
routers, then collects a fresh 100-question diagnostic. It includes DART's third
draft SC branch, confidence gates, MiniLM/ridge, random allocation, a gain/cost
regression comparator, and ablations of question features and harmful revisions.
The official test remains sealed. Novelty and superiority are hypotheses, not
assumptions. See [research rationale, limitations, and tracking](docs/continuation-study.md).

To estimate a fresh confirmation study from the completed question-level results:

```sh
uv run --locked rb power artifacts/probe/continuation-v1
```

This verifies the saved result dependencies and writes power/sensitivity and
compute estimates without generation. It cannot guarantee significance. See
[confirmation design and current feasibility](docs/confirmation-design.md).

## CPU router development comparison

Replay the shared-correctness router and its baselines on cached development
traces. Settings are selected in inner folds and each held-out question's two
first-draft orientations stay together. No Qwen generation runs:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -m reasoning_budget.router_dev \
  --output artifacts/router-dev/shared-base-v2
```

The [development result](docs/router-dev-results.md) explains the comparison
and links to its corrected local report. Version 2 repairs standalone-thinking
costs; the original version 1 artifacts are preserved. The prepared confirmation protocol belongs to
the earlier unchanged router.

## Frozen confirmation study

The unchanged router is frozen for 3,100 fresh upstream-training questions,
15,500 responses, in 31 resumable batches. Preparation does not generate responses.

```sh
uv run --locked rb confirm prepare
uv run --locked rb confirm status artifacts/confirmation/frozen-router-v1
# Separate collection command; omit --batches to run all remaining batches:
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  caffeinate -i uv run --locked rb confirm run artifacts/confirmation/frozen-router-v1 --batches 1
```

The fixed primary comparison uses lambda=.05 and a whole-question paired t test.
Secondary comparisons use Holm adjustment and a positive-primary gate. No model
refitting, comparative reporting, or scoring occurs during partial collection.
The official test labels remain sealed. The locally frozen protocol, copied
models/code/lockfile, datasets, and verification record live under
`artifacts/confirmation/frozen-router-v1/`. See the [protocol details](docs/confirmation-design.md).
