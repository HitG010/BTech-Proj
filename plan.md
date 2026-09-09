# Research pilot plan v2

Branch `research/pilot-v2`, started 2026-09-09 from the state in which Milestones A–C were
implemented and the first 400-job pilot had completed but had not been scored. This document
is the forward plan. The previous checklist and its execution notes are kept verbatim in the
appendix.

## 1. Where the project stands

Implemented and tested on `master`: strict YAML configuration; a batch-one Transformers backend
with separate reasoning and answer stages; atomic, resumable runs with token and elapsed-time
ledgers; frozen disjoint GSM8K splits (100 pilot, 400 train, 100 validation, 500 test);
gold-free exact numeric scoring; whole-question bootstrap reporting; deterministic audit
sampling. 59 offline tests pass and Ruff is clean. Re-running `rb prepare gsm8k` on this branch
reproduced the frozen manifest, questions and gold byte-for-byte.

### Pilot v1 result (run `af1f1e56c5d453bbfd5e`)

100 pilot questions × 2 samples × 2 modes; Qwen3-1.7B at commit `70d244cc…`; MPS fp16;
prompt suffix "In your final response, give only the numerical answer in \boxed{}";
2,048 reasoning tokens then 256 answer tokens.

| Mode | Accuracy as scored | Answers cut at 256 tokens | Accuracy among untruncated | Forced closure at 2,048 | Mean generated tokens | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| direct | 63.0% | 63 / 200 | 92.0% | 0 / 200 | 194 | 7.9 |
| thinking | 46.0% | 105 / 200 | 96.8% | 30 / 200 | 1,287 | 53.9 |

Paired thinking-minus-direct accuracy is -0.17 with a whole-question bootstrap interval of
[-0.255, -0.085]. This is a protocol artifact, not a finding. The model ignores "only the
numerical answer" in both modes: direct writes a full worked solution of about 200 tokens, and
thinking restates the solution after `</think>`. The 256-token answer allowance therefore cuts
a third of direct answers and half of thinking answers; 90 of the 105 truncated thinking
answers had already stated a final answer inside the reasoning. Forced closure at 2,048
reasoning tokens hit 15% of thinking runs, which trips the proposal's 5% gate. Local
throughput was about 24 tokens per second and the run took 3.4 hours including setup.

### Defects found in review, fixed on this branch

- Answer allowance and prompt produce truncation (above).
- Scorer rejects LaTeX-decorated boxes such as `\boxed{\$18}`, `\boxed{18\%}`,
  `\boxed{18 \text{ hours}}`, `\boxed{\text{18}}` as `invalid_number`.
- The budget ledger re-reads every attempt file before every job, so cost grows quadratically
  (0.27 s at 400 attempts; about four hours of pure re-reading for a 6,400-job run).
- One failed job halts the whole run; unattended cloud runs would sit idle.
- The run identity hashes five source files, so any edit orphans every existing run.
- The backend passes a single EOS id although the checkpoint declares two (151645, 151643).
- Direct-mode confidence is computed after temperature, top-k and top-p warpers only.
- The frozen split manifest is excluded from version control.

### Research-design risks, decided at the feasibility gate

- Headroom on GSM8K may be small: among untruncated v1 responses direct reached 92% and
  thinking 96.8%. The Qwen3 report gives Qwen3-1.7B MATH-500 thinking 93.4 versus
  non-thinking 73.0, a far larger gap.
- The fixed 400-question training pool forbids the breadth baseline (more distinct questions,
  one sample each) under the same token budget.
- Whether label noise is the controller's bottleneck is unknown; a ceiling check with
  1-sample versus 8-sample labels should gate the acquisition method.
- The batch-one Transformers backend cannot run the full programme within $100; a batched
  engine is required for cloud runs.

## 2. Protocol v2 (frozen for the re-pilot)

- Modes: `direct` is Qwen3 non-thinking mode (the chat template prefills an empty think
  block) with natural short chain-of-thought allowed; `thinking` is thinking mode. Both
  receive the same prompt.
- Prompt suffix: "Please reason step by step, and put your final answer within \boxed{}."
  (Qwen3 model-card wording for math.)
- Allowances: 4,096 reasoning tokens, then 1,024 answer tokens, for both modes' answer stage.
- Forced closure text at the reasoning limit: the Qwen3 report's budget phrase
  "Considering the limited time by the user, I have to give the solution based on the
  thinking directly now.\n</think>\n\n" (23 tokens, counted separately as inserted tokens).
- Decoding per model card: direct 0.7 / 0.8 / 20, thinking 0.6 / 0.95 / 20; both EOS ids.
- Scoring `numeric-v4`: LaTeX currency, percent, spacing and text wrappers are stripped
  inside claims, and prose after an answer label is not a claim (the v2 smoke showed
  "the answer is correct, ..." being read as a conflicting claim); conflicts,
  `2:30`-style values, and truncated outputs remain unscorable.
- Confidence: store both post-warper and raw-logit mean log-probability for direct answers.
- Same 100 pilot questions, 2 samples per mode; Mac MPS fp16; new run identity.

## 3. Work items on this branch

| # | Item | Files | Done when |
|---|---|---|---|
| 1 | This plan | `plan.md` | committed |
| 2 | Protocol v2 configs; track split manifest | `configs/smoke_v2.yaml`, `configs/pilot_v2.yaml`, ignore rules, `artifacts/data/gsm8k/manifest.json` | configs load; manifest tracked |
| 3 | Scorer `numeric-v3` | `src/reasoning_budget/scoring.py`, `tests/test_scoring.py` | new cases pass; v1 rescoring flips no `correct` value |
| 4 | Backend: EOS list, raw log-prob, configurable closure text | `backend.py`, `records.py`, `config.py`, `tests/test_generation.py` | tests pass |
| 5 | Runner: incremental ledger, consecutive-failure threshold, protocol-version identity | `runner.py`, `config.py`, `tests/test_resume_reporting.py`, `README.md` | tests pass; tally equals `_usage()` |
| 6 | `rb analyze RUN_DIR` | `src/reasoning_budget/analysis.py`, `cli.py` | analysis.md and analysis.json written for pilot v1 and v2 |
| 7 | Smoke v2 then pilot v2 | runs under `artifacts/runs/` | 20/20 and 400/400 complete; report, analysis, audit created |
| 8 | Agent pre-screen; human audit of 50 | `RUN/report/prescreen.md`, `RUN/audit.json` | 50 reviewed rows with a named human reviewer |
| 9 | Feasibility report | `docs/pilot-v2-report.md`, `docs/verification.md` | go/no-go written for supervisor |

Every item is committed on this branch. `master` receives nothing until the supervisor has
seen the feasibility report.

## 4. Gates

**Feasibility gate (end of this branch).** Inputs: the v2 gap and its interval, the
decision-relevant fraction of questions, forced-closure rate against 5%, scorer pre-screen
results, cost projection for the full programme at observed and cloud throughput, and the
minimum detectable paired difference on 500 test questions. Decision: keep GSM8K alone,
add a numeric-answer MATH or GSM-Plus set, or promote the procedural tasks to a primary
setting. If the GSM8K gap is under 8 points, build a 100-question procedural probe before
deciding.

**Novelty gate (supervisor).** Table distinguishing the adaptive acquisition rule from DARS
(repeated observations, uniform), active learning, and reasoning routers. The DARS-style
uniform-repeat baseline is mandatory.

**Method gate (Milestone E).** Before implementing acquisition, train the ridge controller on
1-sample labels and on 8-sample mean labels from the replay cache. If denoised labels do not
improve the controller, label noise is not the bottleneck and the acquisition contribution
cannot exist in this setting.

## 5. Deferred designs (not built on this branch)

- **vLLM backend** for cloud runs: `src/reasoning_budget/backends/vllm.py`; batched job loop
  with per-batch reservations; engine name and version, sampling parameters, and closure
  text in the run identity; the two-stage protocol via prefix caching; a 20-output cross-check
  against the Transformers backend on the same GPU. Trigger: cloud access.
- **Breadth pool**: `artifacts/data/gsm8k-v2` with split algorithm `v2-extend` that keeps every
  v1 id and adds 1,100 further train candidates, so every acquisition strategy chooses between
  new questions and re-samples under one token budget.
- **Milestone D** baselines and controller as in the appendix, unchanged.
- **Procedural probe**: Boolean and state-tracking generators with executable keys, validated
  against an independent implementation, 100 questions, only if the feasibility gate asks.

## Appendix: previous checklist and execution notes (verbatim from `master`)

# Research repository implementation checklist

## Scope and first deliverable

Implement Milestones A–C in this first pass. Run 10 arithmetic questions through
Qwen3-1.7B in direct and thinking modes, save and score 20 responses, then inspect
them before running a resumable 100-question GSM8K pilot with two samples per mode.
Target: M2 Pro, 16 GB shared memory; explicit CUDA support for later experiments.

## A — Bootstrap and offline pipeline

- [ ] Initialize Git, Python 3.11 / uv project, local environment, dependency lock.
- [x] Add setup documentation and ignore environments, models, data, and traces.
- [x] Implement strict YAML configuration and `rb doctor`.
- [x] Add 10 arithmetic fixtures with separate scoring-only answers.
- [x] Test numeric parsing and scoring with fabricated responses offline.

## B — Real local inference

- [x] Load Qwen3-1.7B once per invocation; batch size one, FP16, explicit device.
- [x] Use checkpoint chat template and explicit thinking setting; pin revisions.
- [x] Direct: temperature 0.7, top-p 0.8, top-k 20, 256 answer tokens.
- [x] Thinking: temperature 0.6, top-p 0.95, top-k 20, 2,048 reasoning tokens,
      then 256 answer tokens; force closure at reasoning limit and record overhead.
- [x] Save raw text, separated reasoning/answer, token counts, time, and termination.
- [x] Complete and inspect 20 real smoke records; freeze tested environment.

## C — Resumable pilot

- [x] Freeze disjoint GSM8K splits: 100 pilot, 400 controller training,
      100 validation from train, and 500 from official test; reject duplicates.
- [x] Stable job seeds and identities covering content, revisions, template,
      decoding, precision, backend, and software configuration.
- [x] Atomic records, verified resume, explicit failures and retries.
- [x] Enforce cumulative token reservations and elapsed-time limits.
- [x] Report accuracy, parsing failures, forced closure, truncation, tokens,
      runtime, question-level bootstrap intervals, and projected cost.
- [ ] Run 400 pilot generations after smoke inspection.
- [ ] Manually audit at least 50 real pilot scores before accepting the report.

## Scientific integrity tests

- [x] Integers, decimals, fractions, negatives, boxes, conflicts, missing and
      incomplete answers; never choose a candidate using the gold label.
- [x] Natural reasoning closure, forced closure, early EOS, answer truncation,
      timeouts, and distinct token accounting using a fake model.
- [x] Split overlap / normalized duplicates; atomic resume, corrupted writes,
      configuration changes, duplicate prevention, and budgets across retries.
- [x] Paired policies and bootstrap resampling of whole questions.

## Compute controls

$100 overall ceiling: $10 pilot, $50 main experiments, $20 confirmation,
$20 reserve. No cloud launch before local cost estimates. Cloud billing remains
separate from token/time limits, which cannot stop idle instance charges.
Reserve maximum generated tokens before every job. Do not silently switch
device, precision, quantization, or inference engine. Report partial runs honestly.

## Later milestones (outside this implementation pass)

- D: always-direct/thinking, random and confidence routing; frozen MiniLM plus
  question length/numeric/operator features; chunk long inputs; four standardized
  ridge predictors; validation-only alpha tuning over 0.1, 1, 10, 100; clipped
  accuracy/cost predictions and accuracy-minus-cost decisions.
- E: uniform, random and uncertainty/cost-aware acquisition; Beta(1,1), 512 seeded
  posterior draws, expected decision regret across cost preferences per pair cost;
  equal token ceilings, eight-pair cap, periodic fitting, hidden-outcome replay.
- F: SVAMP and procedural tasks, Qwen3-4B confirmation, published comparison
  (method still to be specified), ablations, frozen policies before test, and
  manuscript figures. Two Qwen checkpoints do not establish cross-family transfer.

## Execution notes

Implementation and verification status will be recorded here as work completes.

- 2026-09-09: implemented the A–C CLI and offline pipeline; 59 tests pass.
  Python 3.11.13, PyTorch 2.14.0, Transformers 4.57.6. Git initialized; lock
  generated and verified. Real model revision:
  `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- GSM8K revision `740312add88f781978c0658806c59bc2815b9866`, seed 20260909;
  1,100 questions frozen with no normalized duplicates in this upstream revision.
- Initial calibration run `0d1ecd02bf9f50e2a9ee` was deliberately interrupted after
  7 completed responses: the prompt allowed verbose final answers. It remains a
  partial artifact. The shared prompt was clarified before the definitive smoke
  and pilot. Multiline final-answer boxes exposed a parser defect, fixed and
  regression-tested in `numeric-v2`.
- Definitive smoke `63d94a10f6f9b7d31309`: 20/20 records complete and individually
  inspected by Codex. Direct 10/10; thinking 7/10, with three answer truncations.
  No remaining scorer defects in the smoke audit. Total 8,615 generated tokens;
  390.1 seconds generation, 403.1 seconds including setup. MPS driver memory
  samples were approximately 4 GB. Pilot `af1f1e56c5d453bbfd5e` launched after review.
