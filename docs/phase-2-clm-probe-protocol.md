# Phase 2d: one cached released-CLM diagnostic

Protocol date: 2026-10-03, following the completed [local engineering preflight](local-clm-and-power-results.md).
User authorized this next step, with local experiments and Docker kept running.
Freeze this document, source, tests, requests, dependencies and inputs before
encoding or fitting. Outputs go only to the new ignored `repeat-clm-probe-v1/`.
This is **reused-development evidence**, not confirmation or a new primary gate.

## Hypothesis and scope

Do the actual pretrained CLM state/action heads expose useful incremental-utility
signal beyond confidence in this frozen 1.7B solver, and beyond a small supervised
control on the **same** Qwen3-8B embeddings? The prior MiniLM pilot did not test
released heads. This one bounded diagnostic tests that distinct transfer hypothesis.

Use all 400 existing direct drafts on the 50 repeat questions. Thinking outcomes,
tokens and elapsed seconds are training/evaluation targets from the unchanged
cached v7 sidecar; **thinking response text never enters encoder requests**.
No new responses, new references, reserve/validation/confirmation questions,
scoring calls, cloud/model APIs, acquisition or RL are permitted in this study.
The original failed progression report remains authoritative.

## Encoder, heads and one input recipe

Reuse the pinned local assets and isolated environment from the preflight:
`mlx-community/Qwen3-8B-4bit` at `545dc4251c05440727734bcd94334791f6ab0192`,
CLM heads at `e939398d4556fcd9400c76fa8c5a513202f42b0a`, and official head code
at `bb42c6c5bf914fd449bed2f6ca65be80602cb1f7`. Preserve every asset hash and
the preflight source/output. No asset redownload or package upgrade.

`scripts/repeat_clm_probe.py` uses one fixed plain-text state: a routing objective
at λ=.05, frozen solver name, question-only thinking semantics, then original
question and completed direct draft. The exact template and both action texts
are in the script and plan. Actions are accept this draft versus discard it and
pay for a fresh thinking solve of the original question. No confidence numbers,
parser status, correctness labels, future thinking cost or thinking text appear
in the state. Do not try prompt variants after viewing scores.

Select direct rows before accessing their result fields. Prepare a separate
label-free request file with question ID, draw index and formatted text only.
The MLX worker loads this file, not the cached panel/score sidecar. It encodes
400 states and two reusable action vectors at batch size one, without a
persistent KV cache. Plain-text tokenization adds no special tokens and keeps
the final 2,047 tokens. Record raw/kept counts, truncation, token/text hashes,
tokenization and forward-to-NumPy timing. Do not remove rejected/incomplete drafts.

Take the final normalized transformer hidden state at the last input token,
cast to float32 and L2-normalize 4,096 components. Store `50×8×4096` states and
`2×4096` actions in an exclusive-created NPZ. Frozen released heads are loaded
with safe weights-only PyTorch, strict dictionaries and the pinned official
architecture. Normalize both projections, apply the released log-scale exponent
clamped to 100, and calculate think-minus-accept margin. No head finetuning.

This is a quantized MLX adaptation. Full-precision equivalence, pretraining
disjointness and the release's other-task benchmark claims remain unverified.

## Policies and bounded supervision

Always accept, always escalate and the original training-fitted confidence gate
are controls. Reproduce historical confidence actions exactly in all three
conditions before publishing a result.

- **Zero-shot CLM:** margin strictly >0, no tuning.
- **Calibrated CLM:** standardize the frozen scalar margin using training states
  only; fit Ridge with intercept to paired gain.
- **Matched raw-encoder control:** fit PCA8 on training-state embeddings only,
  standardize those components and divide by √8; fit the same Ridge gain target.

The two learned families use alphas [100, 1,000, 10,000] and action thresholds
[0, .02, .05], selected using four inner question folds on the training draw half.
Gain is `thinking_correct − direct_correct − .05 × thinking_tokens / 1000`;
the already-paid draft cost cancels in action gain but stays in total utility.
Stable ties prefer larger alpha, then threshold; family ties follow the frozen
family order. Retain all 18 outer configuration action arrays, both selected
families, zero-shot and a training-selected family; no outer-score model choice.

Neither learned family includes the four auxiliary draft statistics. The
confidence gate retains its original mean-logprob signal. This tests semantic
transfer, not confidence/CLM fusion. The backbone is matched across learned
families; their dimensions, pretrained head capacity and prior training differ.
It cannot isolate a causal contrastive-objective effect.

## Question/draw splits, reporting and exploratory screen

Use unchanged five outer question folds. In A4→B4 and B4→A4, training and
evaluation draw halves are disjoint; inner tuning uses only training-half labels
and outer-training questions. The inner split seed remains `20261002 + fold`.
PCA and scalers fit only those permitted states. Changing held-out/opposite-half
outcomes must leave fitted settings and actions unchanged in synthetic tests.
Secondary full8 has no independent same-question eight-draw replica.

The fixed grid is **450 Ridge fits and 75 PCA fits**, with one CPU thread.
Report all policies' accuracy, charged generated tokens, original cached solver
seconds, utility, escalations, captured positive gain and harmful decisions.
Primary diagnostic comparisons are calibrated CLM minus confidence and calibrated
CLM minus raw control, averaging both independent-half directions at question
level. Retain separate directions, zero-shot, raw and nested-selected results.
Whole-question bootstrap: 2,000 draws, seed 20261006, central 90% interval, fixed
fits. These intervals omit refitting, selection and researcher uncertainty.

Use the earlier exploratory screen for each diagnostic family: average gain
≥.01, both direction means positive, every leave-one-question-out average
positive. A pass only prioritizes a separately frozen fresh diagnostic; it
does not repair failed primary gates or justify scaling. A failure closes this
bounded recipe without prompt, alpha, head-capacity or representation expansion.

Measure single-state CPU projection/scoring and selected Ridge/PCA prediction
work. Keep generated-token utility unchanged and report encoder work separately.
The sum of historical solver times and observed encoder/head/prediction times
is a **descriptive proxy from different runs**, not live co-resident latency.
Cold imports/loading, tokenization, action cache setup, peak allocation, RSS
and total analysis work remain separate. No deployment speed claim.

## Resource and execution boundary

One native encoder invocation, **zero retries**, 2,400-second encoder wall limit,
60-second per-input limit, MLX memory guideline/observed peak ≤7 GiB, free cache
128 MiB, observed worker RSS ≤9 GiB polled every .5 s. The MLX limit is a
guideline; macOS RSS excludes some GPU allocations. Only this worker child may
be terminated; never Docker or unrelated processes. Stop on first failure and
preserve invocation, log, partial progress and terminal status; no journal reset.

`prepare` freezes source/test/protocol hashes, cached endpoint identity, folds,
exact request, complete encoder environment and analysis packages before work.
`execute` checks every identity, exclusively records its invocation, encodes,
applies frozen heads, fits the fixed grid, rechecks inputs and writes new reports.
The encoder exits before CPU analysis. Never overwrite existing completed files.

```sh
PYTHONPATH=src .venv/bin/python -m scripts.repeat_clm_probe prepare
PYTHONPATH=src .venv/bin/python -m scripts.repeat_clm_probe execute
```

Execution needs native Metal access. The researcher verifies cached decisions
and accounting in a separate fresh process, without refitting, scoring or encoder
execution. Preserve the official test, both confirmations, allocations and all
old experiment sources/outputs. Cloud spend remains $0.
