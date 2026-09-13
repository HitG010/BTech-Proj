# GSM8K pilot results

Milestones A–C are implemented and verified. The local Qwen3-1.7B pilot completed
all 400 generations: 100 frozen GSM8K training-split questions, two samples per
mode. The scoring audit is complete. These results measure the specified token
limits; answer truncation materially affects the comparison.

| Metric | Direct | Thinking |
|---|---:|---:|
| Completed generations | 200 | 200 |
| Correct final answers | 126 | 92 |
| Accuracy | 63.0% | 46.0% |
| Truncated final answers | 63 (31.5%) | 105 (52.5%) |
| Other parse failures after correction | 0 | 0 |
| Parsed answers unequal to benchmark label | 11 | 3 |
| Forced reasoning closure | 0 | 30 (15.0%) |
| Mean sampled tokens per response | 194.3 | 1,287.5 |
| Mean seconds per response | 7.90 | 53.91 |

Thinking minus direct accuracy is **-17 percentage points**, with a 95%
whole-question bootstrap interval of **[-25.5, -8.5] points**. The bootstrap
retains both samples from each question and pairs modes on the same 100 questions.
This does not establish that unconstrained thinking is worse: 168 of the 182
recorded answer failures are truncated responses. Increasing the answer allowance
requires a separate configuration and fresh run to measure its effect.

## Protocol and provenance

- Run: `af1f1e56c5d453bbfd5ebaa454110948a4690245fed898f96473bfbebb926ca4`.
- Experiment seed: `20260909`; per-job seeds are stored in the manifest.
- Model and tokenizer: `Qwen/Qwen3-1.7B`, commit
  `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- GSM8K commit: `740312add88f781978c0658806c59bc2815b9866`.
- FP16 on local MPS, SDPA attention, batch size one; no quantization or fallback.
- Direct: temperature 0.7, top-p 0.8, top-k 20; 256 answer tokens.
- Thinking: temperature 0.6, top-p 0.95, top-k 20; 2,048 reasoning tokens followed
  by 256 answer tokens. Forced closure continues the same assistant prefix.
- The shared prompt requests a boxed numerical final answer. Many responses
  nevertheless contain lengthy explanations in the final-answer stage.

## Verification and audit

All 400 records and 400 attempt records are complete. Sampled token counts agree
with saved IDs. Each of the 30 forced closures occurs at 2,048 reasoning tokens
and inserts exactly the configured two closure tokens. Natural reasoning endings
contain the closing marker, and reasoning does not enter the scoring input.
An explicit guarded resume check skipped all 400 jobs without loading model weights.

Codex individually inspected a deterministic stratified sample of 50 responses
(25 per mode), then checked all additional nontruncated errors. The formal audit
contains 51 reviews, including the additional repeating-decimal case. This is an
agent review, not a human review. No unresolved scorer defects remain in these
reviews; audit acceptance is about record and scoring verification.

The additional check found `137.\overline{3}`, which `numeric-v2` did not parse.
`numeric-v3` extracts the exact rational 412/3, with regression tests for signs,
nonrepeating prefixes, and conflicting claims. The frozen benchmark label is
138, so this fix changes the parse status but not correctness. No gold-dependent
rounding or answer selection was introduced. Fifty sampled decisions and all 20
smoke decisions remained unchanged; their reviews were carried forward only
after checking that equality.

One upstream question says “2 132 contracts,” while its solution treats this as
two contracts of 132 pages and labels the answer 44. Both direct samples interpret
it as 2,132 contracts and answer 356. The ambiguity exists in the cached upstream
dataset. The frozen prompt and gold label remain unchanged, and this disagreement
is not an extraction error. Other observed nontruncated errors include omitting
the second bridge anchor, annualizing only one month's rent, and failing to
multiply red/white jelly beans by the number of bags.

## Runtime and cost

The pilot used **296,362 sampled tokens plus 60 inserted tokens**, taking **3.438
hours including setup**. Maximum MPS driver memory sampled after a response was
4.32 GB; this is not a measured peak. Actual cloud expenditure was **$0**.

At measured local inference speed, 1,100 questions × two samples × two modes
projects to **37.78 inference hours**. At a hypothetical **$1/hour with identical
throughput**, that is **$37.78**. This is not a vendor quote or a CUDA estimate.
Setup, idle rental time, adaptive-acquisition repeats, and confirmation are
excluded. The original $100 allocation remains $10 pilot, $50 main, $20
confirmation, $20 reserve. No cloud experiment has been launched.

Before controller or acquisition experiments, revisit final-answer verbosity and
the answer allowance using a new comparison. Keep this pilot immutable so that
any protocol change is visible.

## Local artifacts

- [Full report](../artifacts/runs/af1f1e56c5d453bbfd5e/report/report.md)
- [Machine-readable summary](../artifacts/runs/af1f1e56c5d453bbfd5e/report/summary.json)
- [Comparison plot](../artifacts/runs/af1f1e56c5d453bbfd5e/report/comparison.png)
- [Audited responses](../artifacts/runs/af1f1e56c5d453bbfd5e/audit.json)
- [Token integrity verification](../artifacts/runs/af1f1e56c5d453bbfd5e/integrity_verification.json)

Large models, datasets, and generated traces are intentionally excluded from Git.
Recreate reports with `rb report artifacts/runs/af1f1e56c5d453bbfd5e --hourly-rate 1`.
