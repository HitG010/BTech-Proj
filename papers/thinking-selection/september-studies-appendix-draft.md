# Draft appendix: September development studies

Prepared 1 November 2026 for Phase 2, item 11 of the
[project review](../../docs/project-review-and-publication-plan-2026-10-29.md).
This is a **draft for the author's decision**, not yet part of the manuscript.
It summarizes completed September studies from their tracked records only. No
artifact, score cache, or reference answer was opened, and no number was
recomputed except the utilities marked as derived below.

Proposed placement: a new **Appendix D, Earlier development studies under a
different protocol**, with one sentence in Section 3.3 pointing to it.

## Why include it

The current manuscript reports only the October studies. The September
studies asked closely related questions on different questions, with fewer
draws and an older scorer. They point the same way: question-only routers did
no better than cost-matched random allocation, and confidence was a strong
cheap comparator. They also contain the only earlier result for two-draft
agreement, which the Phase 2 agreement check now tests on the repeat panel.
Leaving them out would hide consistent prior evidence and one mixed result.

## Protocol differences

| Aspect | September studies | October studies in the manuscript |
|---|---|---|
| Solver and decoding | Qwen3-1.7B, local MPS float16, batch one; direct T=.7, top-p .8, top-k 20; thinking T=.6, top-p .95, top-k 20 | Same model and decoders |
| Token caps | 2,048 reasoning / 512 answer after the cap calibration (the first pilot used 256 answer tokens) | 2,048 / 512 |
| Generation protocol | Legacy implementation at `6999eb5` | `qwen3-boxed-budget-v3`. On the 25-question bridge, all 100 matched legacy/v3 cells had identical token sequences, terminations, and extracted answers; equivalence on other inputs is not established |
| Scorer | numeric-v4 | numeric-v7 (repeat and two-solver panels) |
| Draws per mode | Two (three direct drafts in the continuation study) | Eight (repeat panel) or two (two-solver panel) |
| Questions | Calibrated pilot, validation, and diagnostic roles from the GSM8K training split | New disjoint roles; the October allocation excludes every previously influenced question |
| Rules | Question-only MiniLM/Ridge routers, decision-focused and retrieval heads, three-action continuation routers, a shared-correctness model, confidence, and a two-draft agreement adaptation | Post-hoc deferral rules after one paid direct draft |
| Intervals | Whole-question bootstrap, 95%, fits held fixed | Whole-question bootstrap, 90%, fits held fixed |
| Scoring audit | Waived | Waived |

Because the scorer, questions, draws, and rule definitions differ, no
September number should be pooled with or compared numerically against an
October number.

## Results

**Table D1. September development studies.** Accuracy and tokens are as
reported in each record. Utility is at λ = .05. Values marked † are derived
here from the reported accuracy and tokens, as accuracy − .05 × tokens/1000,
rounded to four decimals.
Intervals are the records' 95% whole-question bootstrap intervals with fits
held fixed.

| Study (record) | Data | Result |
|---|---|---|
| Pilot (pilot-results) | 100 questions, two draws, 256 answer tokens | Direct 63.0%, thinking 46.0%. Truncation caused 168 of 182 failures, so this measured the cap, not the modes |
| Answer-cap calibration (calibration-results) | 25 questions, two draws | 512 answer tokens: direct 72%, thinking 88%; 1,024 changed no correctness decision. 512 was frozen |
| Calibrated pilot and question-only routing (routing-learnability) | 100 questions, two draws, five outer folds | Direct 84.0% at 221.0 tokens, thinking 92.0% at 1,331.9. Against cost-matched random at illustrative curve points: MiniLM/Ridge +0.24 pp [−2.58, +3.13], confidence +1.34 pp [−0.58, +3.53], two-draft agreement +1.55 pp [−1.18, +4.36]. None reliable |
| Stronger question-only routers (stronger-router-study) | 50 training, 50 tuning, 50 diagnostic questions | Always direct 88% at 236.91 (utility .8682†), always thinking 92% at 1,599.75 (.8400†), confidence 90% at 404.85 (.8798†), two-draft agreement 95% at 759.33 (.9120†), decision-focused head 88% at 270.72. The decision head beat Ridge (+.039592 [+.006630, +.077631]) but thought on 1 of 50 questions and did not beat cost-matched random |
| Three-action continuation router (continuation-study; research-review-2026-09-24) | 100 training, 100 tuning, 100 fresh diagnostic questions; three direct and two thinking draws | Joint router 88.0% at 728 tokens (.8436†), gain Ridge 89.0% at 877.3 (.8461†), confidence continuation 86.5% at 591.8 (.8354†), always thinking 89.5% at 1,414 (.8243†). Joint minus confidence +.008188 [−.020329, +.044029]: inconclusive |
| Shared-correctness router, development (router-dev-results) | 200 pooled development questions, cross-fitted | Shared 90.25% at 622.0 (utility .8714), confidence continuation 90.25% at 589.4 (.8730), two-draft agreement 90.25% at 702.2 (.8674), always thinking 91.50% at 1,430.7 (.8435, corrected). Shared minus confidence −.0016 [−.0092, +.0055] |

## Reading

- **Question-only routing.** In both studies that tested it, a router using
  only question features did not beat cost-matched random allocation. This is
  consistent with the October results, where adding question features to
  draft features did not beat confidence.
- **Confidence.** Confidence was a strong cheap comparator but not always the
  best. At λ = .05 it led the shared-correctness development study, trailed
  the joint and gain-Ridge continuation routers by about .01 (the joint
  router's difference was inconclusive), and trailed agreement on one
  50-question holdout.
- **Two-draft agreement.** Results were mixed. On the 50-question stronger-router
  holdout it had the highest utility (.9120† against .8798† for confidence). On 200 development questions it trailed confidence (.8674
  against .8730). These studies charged both drafts, as the Phase 2 check
  does, but used a different scorer and different questions.
- **Scale.** Each study had 25 to 200 questions and two or three draws, and
  most reused questions that had shaped the design. They are development
  evidence, not confirmation.

## Draft manuscript text

For Section 3.3, after the chronology paragraph:

> Earlier development studies in September 2026 used an older scorer,
> different questions, and fewer draws. Appendix D summarizes them; their
> numbers are not comparable with the main results.

For Appendix D: the protocol table and Table D1 above, followed by the
reading. Keep the four reading bullets. If the Phase 2 agreement check is
added to the manuscript, cite the mixed September agreement results there as
the motivation, not as supporting evidence.
