# Implementation verification

The first pass implements Milestones A–C; branch `research/pilot-v2` adds protocol
v2, scorer v4, the runner fixes and `rb analyze` (see `plan.md`). Detailed run
artifacts are local and excluded from version control; the source, tests,
configurations, plan, dependency lock and the frozen GSM8K split manifest are
tracked.

## Environment and tests

- Managed Python 3.11.13; PyTorch 2.14.0; Transformers 4.57.6.
- Qwen3-1.7B model/tokenizer commit `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- FP16, MPS, SDPA, one question per batch; no fallback or quantization.
- 87 offline tests pass on the branch (59 on `master`); Ruff check and format pass;
  uv lock consistency verified. `rb prepare gsm8k` in a fresh worktree reproduced
  the frozen manifest, questions and gold byte-for-byte.
- Offline end-to-end run `0d73cf0fd0c32a5c5722` completed 20/20 jobs, produced
  reports, and a second invocation skipped all completed records.
- Interruption, incomplete/corrupt writes, conservative token reservations,
  elapsed limits, deterministic seeds/splits, and whole-question statistics are
  covered by tests. An initial real calibration run also exercised Ctrl-C and
  preserved completed results and the interrupted attempt's reservation.

## Real smoke result

Run `63d94a10f6f9b7d31309`, experiment seed 20260909, ten arithmetic fixtures,
one sample per mode. All 20 final responses were individually inspected by Codex;
this is an agent review, not a human review. No unresolved scorer defects remain.

| Mode | Accuracy | Mean generated tokens | Mean seconds | Truncated answers |
|---|---:|---:|---:|---:|
| Direct | 10/10 | 47.9 | 2.20 | 0/10 |
| Thinking | 7/10 | 813.6 | 36.81 | 3/10 |

The three thinking failures are final responses cut off by the 256-token answer
allowance. Intermediate correct numbers were deliberately not scored as complete
answers. The remaining responses have correct boxed final answers. Numeric
scoring does not evaluate the validity of every explanation step.

There were no forced reasoning closures in this smoke run. Total generation:
8,615 tokens and 390.1 seconds; setup-inclusive time: 403.1 seconds. MPS driver
memory sampled after responses was approximately 4 GB, not a measured peak.
Actual cloud billing: $0; the model ran locally.

The paired accuracy difference (thinking minus direct) is -0.30, with a whole-
question bootstrap interval of [-0.60, 0.00]. Ten easy fixtures are a pipeline
check and cannot establish benchmark performance. Answer truncation is a material
protocol limitation to revisit before controller experiments, with a new
configuration and fresh comparison if changed.

The original seven-response calibration artifact `0d1ecd02bf9f50e2a9ee` is partial.
It motivated a clearer shared final-answer instruction before the definitive
smoke/pilot. Its scores also exposed the multiline boxed-answer parser defect,
which was fixed and regression-tested in `numeric-v2`.

## Pilot v1 (protocol v1, superseded)

GSM8K commit `740312add88f781978c0658806c59bc2815b9866`; seed 20260909. Frozen
splits contain 100 pilot, 400 training, 100 validation, and 500 official-test
questions. Run `af1f1e56c5d453bbfd5e` completed all 400 jobs (two samples per
question per mode) in 3.44 hours including setup, 296,422 charged tokens, no cloud
billing. It was scored on 2026-09-09 during the review that started this branch.

| Mode | Accuracy as scored | Answers cut at 256 tokens | Accuracy among untruncated | Forced closure at 2,048 | Mean generated tokens | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| Direct | 63.0% | 63 / 200 | 92.0% | 0 / 200 | 194.3 | 7.90 |
| Thinking | 46.0% | 105 / 200 | 96.8% | 30 / 200 | 1,287.5 | 53.91 |

The paired difference of -0.17 (interval [-0.255, -0.085]) is a protocol artifact:
the prompt's "only the numerical answer" instruction was ignored in both modes and
the 256-token answer allowance truncated the answers. Forced closure at 15% trips
the proposal's 5% gate. No human audit was performed on this run; it is retained
as evidence for the protocol change, not as a result. Rescoring it with
`numeric-v3` and `numeric-v4` changed no correctness value.

## Protocol v2 smoke

Run `2116b22fe18c9b25a354`: ten arithmetic fixtures, one sample per mode, prompt
"Please reason step by step, and put your final answer within \boxed{}", 4,096
reasoning and 1,024 answer tokens, Qwen3 budget closure phrase, both EOS ids.
All 20 responses were individually inspected by Claude (an agent review, not a
human review). Scorer `numeric-v4`; actual cloud billing $0.

| Mode | Accuracy | Mean generated tokens | Mean seconds | Truncated | Forced closure |
|---|---:|---:|---:|---:|---:|
| Direct | 9/10 | 132.2 | 5.96 | 0/10 | 0/10 |
| Thinking | 10/10 | 1,178.5 | 50.94 | 0/10 | 0/10 |

The single direct failure computed 17 + 25 = 44 (a sampled model error, scored
correctly). Every response ended with a natural EOS. Raw-logit mean
log-probability was recorded for all ten direct answers and was below the
post-warper value in every case, as expected from renormalisation. One thinking
answer exposed a scorer defect: "To ensure the answer is correct, we can reverse
the operation ... 37" was read as a conflicting labelled claim; `numeric-v4` now
requires a labelled claim to start with a number, fraction or box. Total charged
tokens 13,107; throughput about 22 to 23 tokens per second on MPS.

## Pilot v2

Run `f73a5665230cd83a7f12`, `configs/pilot_v2.yaml`: the same 100 pilot questions,
two samples per mode, 400 jobs, launched 2026-09-09 on the Mac. Its completion,
`rb analyze` output, scorer pre-screen and the human audit will be recorded in
`docs/pilot-v2-report.md`.
