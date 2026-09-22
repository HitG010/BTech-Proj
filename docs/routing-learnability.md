# Routing learnability: first check, 2026-09-17

**The planned MiniLM/ridge controller has not yet demonstrated useful routing
beyond random allocation at the same token cost.** This is an exploratory result
from 100 pilot questions, not evidence that routing is impossible.

We first completed the answer-cap confirmation: direct 84%, thinking 92%, with
1.5% answer truncation in both modes. The fixed protocol is Qwen3-1.7B, MPS FP16,
2,048 reasoning tokens and 512 answer tokens, scored with numeric-v4. The source
is `artifacts/runs/d00485799f1c8932bafa`, containing 400 verified responses.

## What was implemented and run

- Frozen [MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
  pinned to `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, on CPU in float32.
  Masked mean pooling, normalized chunk embeddings, averaged and normalized
  across all chunks; no silent loss of long-question endings. Add character
  length, numeric-literal count, and symbolic-operator count: 387 features.
- Four separate ridge predictors: direct/thinking correctness probability and
  direct/thinking charged output tokens. Clip accuracies to [0,1] and costs to
  at least one token. Route by predicted accuracy minus lambda × tokens/1,000.
- Five outer question folds, each with four inner folds selecting each target's
  alpha from {0.1,1,10,100}. All scaling and tuning uses training questions only.
  Every reported learned-policy outcome comes from a model that did not train
  on that question. Seed 20260917; all eleven cost preferences are reported.
- Always-direct, always-thinking, exact expected random allocation, confidence
  threshold routing, and a two-draft DART stage-one adaptation. Confidence uses
  saved mean decoder-warped log-probability and training-only threshold fitting.
  Every draft and escalation is charged, including inserted closure markers.
- Portable JSON models, checksum/source identities, per-question replay rows,
  full curves, whole-question paired bootstrap intervals, and integrity tests.

No Qwen generation or GPU work was started. The earlier source cache cost
310,586 charged tokens and 3.661 local hours; that historical cost is recorded
separately from replay policy costs. New cloud expenditure: $0.

## Results

Selected points below illustrate the full curves; they are **not validation-
selected deployment policies**. The complete grid is in the linked report.

| Policy | Parameter | Accuracy | Charged tokens/question |
|---|---:|---:|---:|
| Always-direct | — | 84.0% | 221.0 |
| Always-thinking | — | 92.0% | 1,331.9 |
| Random, matched to ridge cost | P(thinking) ≈ 0.595 | 88.76% | 882.0 |
| MiniLM/ridge | lambda = 0.01 | 89.0% | 882.0 |
| Confidence escalation | lambda = 0.15 | 86.5% | 381.8 |
| DART-SC-2 adaptation | two drafts, then thinking on disagreement | 88.5% | 631.2 |

The illustrated ridge point improves over cost-matched random by just **0.24
percentage points**, descriptive paired 95% interval **[-2.58, +3.13] pp**.
Most other ridge points fall below the random-allocation curve. The DART
adaptation's advantage is **+1.55 pp**, interval **[-1.18, +4.36] pp**. Neither
supports a reliable superiority claim. Confidence's illustrated advantage is
+1.34 pp, interval [-0.58,+3.53] pp, also inconclusive.

Intervals resample whole questions with both samples and all policy outcomes
kept together. They condition on fitted out-of-fold models, do not refit during
bootstrap, and do not capture training instability or adjust for inspecting
multiple preferences. The pilot partly informed protocol selection, and its
50-response human audit is still pending. Keep all conclusions provisional.

## DART comparison boundary

The [official DART code](https://github.com/js-lee-AI/DART) supports agreement
routing followed by thinking. This comparison uses K_init=K_max=2, our strict
numeric equivalence parser, and the fixed local generation allowances. It
charges two direct calls even when they agree; disagreement adds one thinking
call. We average the two possible draft orders within each question, without
treating those orders as independent observations.

The repository's default allows a third draft, and full DART additionally uses
budget probing. Those stages need uncached generations. **This result is a
clearly labelled adaptation, not a complete published-method reproduction.**

## Next decision

1. Finish the existing 50-response human scoring audit. It is the outstanding
   prerequisite for accepting the calibrated pilot, not something an agent
   review can substitute for.
2. Freeze the learnability criterion, cost preferences and held-out protocol.
   Begin with the planned common 32–50-question training seed set and disjoint
   validation responses. Report learning curves as training data increases;
   do not spend the whole acquisition budget on the strength of an oracle gap.
3. Compare the same architecture and all baselines on disjoint data; add DART's
   missing stages with their full generation cost. Preserve the official test
   questions until the policies and preferences are frozen.
4. Advance to adaptive trace acquisition only after a useful held-out routing
   signal appears. If it remains weak, investigate predefined SVAMP/procedural
   diagnostics or response-assisted routing as separate hypotheses. Neither
   should be sold as novelty merely because this pilot controller failed.

At 80 outer-training questions, 387 features, and only two samples per mode,
this check cannot distinguish limited signal from insufficient data or noisy
targets. All but one of the 20 fitted targets selected the strongest available
regularization. That is a reason for a controlled learning-curve study, not
post-hoc architecture or benchmark searching.

## Tracking

- [Full report](../artifacts/routing/e1dd762743e19f93fb7d/report.md)
- [Accuracy–cost figure](../artifacts/routing/e1dd762743e19f93fb7d/accuracy-cost.png)
- [Machine-readable study](../artifacts/routing/e1dd762743e19f93fb7d/study.json)
- [Human audit to complete](../artifacts/runs/d00485799f1c8932bafa/audit.json)
- Implementation: `src/reasoning_budget/controller.py` and `routing.py`.
- Command: `rb routing artifacts/runs/d00485799f1c8932bafa`.

Verification: 84 offline tests pass, plus Ruff and whitespace checks. Tests cover
held-out label invariance, training-only scaling, long-input chunk coverage,
saved-model routing, complete probe costs, paired statistics and refusal of test
data. The actual artifact's source hashes and fold partitions were verified; a
saved fold model was loaded and used to route a new question without its answer.
