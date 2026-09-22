# Answer allowance calibration and frozen confirmation protocol

The 25-question calibration is complete: 100 selected responses from the original
256-token pilot and 200 newly generated responses at 512 and 1,024 answer tokens.
Both modes have two samples per question. Selection used a fixed hash of question
identity with seed 20260914, before inspecting outcomes for selection.

| Answer allowance | Direct accuracy | Thinking accuracy | Direct truncation | Thinking truncation |
|---:|---:|---:|---:|---:|
| 256 | 60% (30/50) | 46% (23/50) | 30% (15/50) | 54% (27/50) |
| 512 | 72% (36/50) | 88% (44/50) | 4% (2/50) | 4% (2/50) |
| 1,024 | 72% (36/50) | 88% (44/50) | 2% (1/50) | 2% (1/50) |

These are calibration-subset results, not the full pilot or sealed test results.
At 512 tokens, thinking minus direct accuracy is 16 percentage points, with an
exploratory 95% paired question-bootstrap interval of [4, 30] points. Relative to
256 tokens, direct improves by 12 points [0, 24] and thinking by 42 points
[24, 60]. Intervals retain both samples within each question and do not adjust
for multiple comparisons or protocol selection.

## Decision

Use **512 answer tokens and 2,048 reasoning tokens** for the full pilot
confirmation. Keep the original model/tokenizer commits, FP16, MPS, prompt,
mode-specific decoding settings, and generation implementation unchanged.
The frozen config is [pilot-calibrated.yaml](../configs/pilot-calibrated.yaml).

The 1,024-token arm changes no correctness decisions across the 100 matched
responses. It allows two additional responses to finish, but they remain wrong.
The 512-token allowance is therefore the smaller tested allowance that gives
the observed accuracy improvement with substantially less truncation. This
does not prove global optimality or that 1,024 tokens cannot help other questions.

All 100 matched token prefixes agree from 256 to 512, and all 100 agree from
512 to 1,024, including reasoning and inserted closure tokens. The comparison
uses actual separately timed generations; these checks provide direct evidence
that the changed cap, rather than a changed sampled prefix, explains the observed
completion differences in this run. They do not guarantee prefix equivalence
under other prompts, devices, or inference implementations.

No prompt or extraction change is currently necessary to launch confirmation.
Such changes remain separate experimental arms if residual completion problems
in the full pilot justify them.

## Scorer defect discovered during inspection

The residual-error audit found two direct responses with correct boxed answers
that `numeric-v3` rejected because Markdown headings such as `#### Billy:` and
`#### Tiffany's total:` were interpreted as GSM8K-style answer declarations.

`numeric-v4` distinguishes those text headings from numerical `####` claims.
It still rejects conflicting numerical claims, reasoning contamination, and
truncated final answers, and never receives gold labels during extraction.
Regression tests cover headings, conflicting boxes and hash-delimited answers.

This correction changes direct accuracy from 68% to 72% at both longer caps.
Thinking accuracy is unchanged. All 400 original pilot generation scores
and all 20 smoke scores have identical extracted answers, correctness,
and parser statuses under v3 and v4. Their original saved reports and audits
remain untouched. Calibration v3 reports and the pending v3 review sheet are
archived alongside the current v4 artifacts.

The remaining 512-token failures are four truncated responses and sixteen
nontruncated benchmark disagreements. Inspected examples include reversed
pencil relationships, omitted spare tires, missing multiplication by ticket
or jelly-bean counts, and an incorrect income bracket. The previously documented
ambiguous Enrique contract question retains its frozen benchmark label.
No unresolved extraction defect was found in the remaining inspected failures.
This is agent inspection, not human review.

## Consequences for the controller research

At 512 tokens, thinking has higher observed per-question mean accuracy on five
questions; twenty tie, and none favors direct. A retrospective selector choosing
the more accurate mode and breaking ties by lower observed token cost reaches
88% accuracy with 543.52 mean charged tokens, versus 1,381.52 for always-thinking.
That is approximately 61% lower cost in this observed sample table.

This selector uses labels and outcomes and cannot be deployed. Two samples per
mode provide a noisy estimate. The result motivates a cost-saving router, but
does not establish that question-only features can predict the useful decisions.
The next scientific checkpoint is whether this structure persists on the
75 pilot questions not used to choose the cap.

The proposed acquisition contribution remains a hypothesis: choose between new
questions, independent repeats, and completing unfinished trajectories according
to expected improvement in a question-only router per marginal training cost.
Calibration alone is not evidence that the acquisition method works or is novel.

## Execution and review

- Original pilot: `af1f1e56c5d453bbfd5e` (selected subset reused read-only).
- 512-token calibration: `d883ad976fc94dfe4cda`; 100/100 completed, 100 attempts.
- 1,024-token calibration: `b819354d6b8f8001265b`; 100/100 completed, 100 attempts.
- New calibration expenditure: 161,729 charged tokens, 1.823 local hours including
  setup, and $0 cloud cost. Maximum sampled MPS driver allocation was 5.03 GB;
  this is not a continuously measured peak.
- Full 512-token pilot confirmation launched as `d00485799f1c8932bafa`, with
  400 planned generations, a six-hour ceiling and 700,000 charged-token ceiling.
- Human review: pending. A stratified 50-response worksheet is available at
  `artifacts/calibration/answer-cap-v1/human-audit.json`. Agent inspection does
  not complete this requirement.

Run or resume the confirmation with:

```sh
HF_HUB_OFFLINE=1 .venv/bin/rb calibrate confirm artifacts/calibration/answer-cap-v1
```

When generation returns, the command automatically writes the standard report,
separate all-pilot / cap-selection / remaining-pilot summaries, and a new audit
worksheet if all 400 jobs completed. Incomplete runs remain provisional and can
be resumed. It does not start training or evaluate the official test split.

Detailed calibration artifacts live under `artifacts/calibration/answer-cap-v1/`:
`report/summary.json`, `integrity-verification.json`, `scoring-migration.json`,
`protocol-decision.json`, and `protocol-selection-summary.json`. The last file
preserves the exact evidence checksum referenced when freezing the protocol.
