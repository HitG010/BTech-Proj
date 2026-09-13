# Implementation verification

The first pass implements Milestones A–C. Detailed run artifacts are local and
excluded from Git; the source, tests, configurations, plan, and dependency lock
are tracked.

## Environment and tests

- Managed Python 3.11.13; PyTorch 2.14.0; Transformers 4.57.6.
- Qwen3-1.7B model/tokenizer commit `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- FP16, MPS, SDPA, one question per batch; no fallback or quantization.
- 64 offline tests passed; Ruff checks passed; uv lock consistency verified.
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

## Pilot

GSM8K commit `740312add88f781978c0658806c59bc2815b9866`; seed 20260909. Frozen
splits contain 100 pilot, 400 training, 100 validation, and 500 official-test
questions. The pilot is run `af1f1e56c5d453bbfd5e`, with two samples per question
per mode (400 jobs). All 400 jobs completed in 3.438 hours including setup, with
296,362 sampled tokens and 60 inserted closure tokens. All 30 forced closures
were checked against saved token IDs and the 2,048-token reasoning limit.
There were no failed generation attempts. Maximum sampled MPS driver allocation
was 4.32 GB (decimal; not a measured peak).

The [final pilot results](pilot-results.md) report 63% direct accuracy and 46%
thinking accuracy, with 31.5% and 52.5% answer truncation respectively. Fifty
stratified sampled responses plus a repeating-decimal diagnostic have formal
audit notes (51 total), authored after individual inspection by Codex. The
additional parser case is fixed in `numeric-v3`; accuracy is unchanged. No
unresolved scorer defects remain in the reviewed records. This is an agent audit,
not a human review or a claim that the token-limited protocol is free of bias.

The smoke throughput projects roughly 2.17 hours for 400 jobs and 23.84 hours for
1,100 questions × two samples × both modes. These are arithmetic-based local
estimates. A hypothetical $1/hour rental at identical speed would cost $2.17 and
$23.84 respectively; CUDA speed, idle time, setup, acquisition repeats, and
confirmation are not measured by this projection. The completed pilot replaces
these preliminary throughput estimates: the measured pilot projects 37.78 inference
hours for 1,100 questions, or $37.78 in the same hypothetical $1/hour scenario.
Actual cloud billing was $0.

A guarded real-backend resume verification skipped all 400 saved pilot jobs
without loading model weights or generating new answers. The saved configuration,
software environment, backend metadata, implementation digest, and jobs matched.
