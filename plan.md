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
