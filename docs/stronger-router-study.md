# Disjoint stronger-router study

Completed and verified 2026-09-18: all 500 responses and automatic router
fitting/evaluation finished successfully. This study implements the next baseline step of
the [research proposal](router-research-proposal.md), not the proposed novel
acquisition method.

The user explicitly instructed us to ignore the scoring audit. That gate is
waived for this study; no human review is claimed. The original pending audit
worksheet and strict numeric-v4 scoring are preserved.

## Completed results and interpretation

All numbers below use the 50-question diagnostic validation holdout, averaging
the two response samples within each question. Learned routers shown here use
50 training questions and the predeclared primary lambda=.05. No policy or
preference was selected from these diagnostic outcomes.

| Policy | Accuracy | Charged output tokens/question |
|---|---:|---:|
| Always-direct | 88% | 236.91 |
| Always-thinking | 92% | 1,599.75 |
| Original ridge-MSE | 87% | 862.56 |
| Utility-tuned ridge | 87% | 791.98 |
| Retrieval/shrinkage | 87% | 582.38 |
| Decision-focused | 88% | 270.72 |
| Confidence escalation | 90% | 404.85 |
| Two-draft DART adaptation | 95% | 759.33 |

The predeclared decision-versus-ridge comparison improves mean utility by
0.039592, with paired whole-question 95% interval [0.006630, 0.077631]. This is
a utility difference, not a 3.96-percentage-point accuracy gain. Accuracy rises
one point while inference token cost falls substantially.

However, the decision router chooses thinking on just 1/50 questions. It has
the same observed accuracy as always-direct at higher cost. Its accuracy
advantage over cost-matched random is -0.10 percentage points, interval
[-0.51,+0.05]. Therefore, **the improved primary comparison does not establish
useful learned question-only routing**. It mainly avoids ridge's unnecessary
thinking calls. Retrieval and utility-tuned ridge do not resolve this limitation.

The DART adaptation accepts matching direct answers on 43 questions and escalates
7. It uses 52.5% fewer charged output tokens than always-thinking, while scoring
95% versus 92% on this sample. Its predefined report comparison to cost-matched
random is +5.47 percentage points, interval [+2.24,+8.40]. This is a secondary
comparison on one small development holdout, not a multiplicity-adjusted or
cross-seed result. A subsequent descriptive paired comparison to always-thinking
is +3 points with interval [0,+6], which does not establish strict accuracy
superiority. Full DART's third draft and budget probing are not evaluated here.

Selected settings at n50: original ridge alphas all 100; utility-tuned ridge
alpha .1; retrieval k=20 with zero shrinkage; decision full features with inverse
regularization 1. The selected retrieval grid therefore provides no evidence
that shrinkage itself helped. These settings were chosen on tuning data before
diagnostic generation.

Actual acquisition expenditure: **431,026 charged tokens, 5.064 local hours,
$0 cloud**. Training used 79,824 tokens, tuning 167,536, diagnostic 183,666.
The study's process exited successfully; no GPU job remains active for it.
Answer truncations were 2/50 direct and 2/50 thinking in training, 1/100 and
2/100 in tuning, and 1/100 and 0/100 in diagnostic. Such responses remain
incorrect under the unchanged strict scorer.

## Next research decision

The evidence favors investigating response-assisted routing before committing
to a large question-only acquisition study. A focused hypothesis is whether a
learned policy can decide when paying for a second direct draft is worthwhile,
while preserving the benefit of agreement-based escalation. Full DART,
confidence routing and an appropriate optional-probe baseline must remain
comparators; this hypothesis is not itself a novelty claim.

This would be a new development study with a declared evaluation protocol.
Do not tune a new policy on this diagnostic holdout and present its resulting
score as independent confirmation. Keep official test questions sealed until
the final policy is frozen. Adaptive training acquisition remains a candidate
contribution, but its question-only learnability prerequisite is not met by
these results.

## Frozen design

| Role | Questions | Samples per mode | Responses |
|---|---:|---:|---:|
| Training | 50 from reserved training split | 1 | 100 |
| Tuning | 50 from reserved validation split | 2 | 200 |
| Diagnostic holdout | Remaining 50 reserved validation questions | 2 | 200 |

Questions are selected and ordered by a seeded hash of question identity,
without labels or outcomes. Seed: 20260918. The first 32 and all 50 training
questions give two nested learning-curve points. No official test question is
used. Diagnostic validation is development evidence, not a final official-test
result; its results must not be used to select a reported winner or preference.

The primary comparison is decision-focused versus original ridge-MSE expected
utility on the diagnostic holdout, trained on 50 questions, at lambda=.05.
Utility is strict correctness minus .05 times charged output tokens / 1,000.
Settings for each new learner family are selected once on the tuning partition
at that lambda, with stable first-setting tie breaking. Remaining lambda values
and the n32 results are predefined secondary curves.

## Learners

- **Ridge-MSE:** the existing four independent ridge predictors with
  training-only inner-CV selection of alpha, retained as the original comparator.
- **Utility-tuned ridge:** the four-output linear model with a shared alpha
  chosen by separate tuning utility, separating the selection-objective effect.
- **Retrieval/shrinkage:** cosine neighbors on frozen MiniLM embeddings; shrink
  local correctness/cost means toward training population means. Neighborhood
  sizes {3,10,20}, shrinkage pseudo-counts {0,5,20}. Lexical features do not enter
  cosine distance. Stored memory contains only acquired training observations.
- **Decision-focused:** a binary logistic head for each fixed cost preference,
  trained on the sign of observed utility advantage and weighted by its absolute
  magnitude. No class rebalancing. Ties carry zero weight; degenerate targets
  produce an explicit constant policy. Compare 16/32/full embedding dimensions
  and inverse regularization {0.1,1,10}. PCA/scaling use training questions only;
  the three lexical features are retained alongside reduced embeddings.

These are baseline adaptations, not complete CARROT/Causal LLM Routing
reproductions or novel methods. Final comparisons also include always-direct,
always-thinking, expected random allocation, tuned confidence escalation, and
the existing two-draft DART adaptation. Full DART remains future work.

The training labels have only one draw per mode: stochastic label noise remains
a limitation. Shrinkage improves pooling but does not establish a reliable
per-question ground-truth mode preference. This run establishes a disjoint
baseline before any adaptive replication study.

## Execution and limits

Qwen3-1.7B stays pinned to the existing checkpoint, FP16/MPS/SDPA, with unchanged
mode decoders, 2,048 reasoning tokens and 512 answer tokens. Generation uses the
existing atomic records, per-job seeded decoding, reservations, and resume logic.
MiniLM and the small router models use CPU. The command inhibits idle sleep while
running; no system sleep settings are changed permanently.

Training ceiling: 170,000 charged tokens and 2 hours. Each validation partition:
340,000 tokens and 3 hours. Combined ceiling: 850,000 tokens and 8 hours; 600
seconds per job. These are limits, not expected usage. At the completed pilot's
rates, 250 response pairs should take roughly 4–5 hours. No cloud jobs or charges.
Closing the laptop or interrupting the process can still pause computation.

Pipeline order is enforced: generate train, generate tune, freeze policies, then
generate diagnostic data and evaluate. The generated artifacts include a frozen
source/code/package identity and explicit audit waiver. Unfinished or failed
generation prevents fitting/evaluation from being reported as complete.

## Track or resume

- [Execution log](../artifacts/learnability/baselines-v1/execution.log)
- [Live stage and process status](../artifacts/learnability/baselines-v1/status.json)
- [Run directory mapping](../artifacts/learnability/baselines-v1/runs.json)
- [Frozen protocol](../artifacts/learnability/baselines-v1/protocol.json)
- Initial training run: `artifacts/runs/496228862bd511f17dd5`.

The completed study directory contains [models](../artifacts/learnability/baselines-v1/models.json),
the [full report](../artifacts/learnability/baselines-v1/report.md),
`report.json`, `curve.csv`, and the [accuracy–cost figure](../artifacts/learnability/baselines-v1/accuracy-cost.png).
Acquisition spending is
reported separately from each policy's inference-token costs. Paired intervals
resample whole diagnostic questions and condition on the fitted training set;
they do not measure training-seed variability.

```sh
tail -f artifacts/learnability/baselines-v1/execution.log
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  uv run --locked rb learnability run artifacts/learnability/baselines-v1
```

Do not start a second writer while the first is running. The study lock rejects
it. Use the same command after an interruption to resume verified work.

## Verification

94 offline tests pass, including the full 500-response fake-backend study,
freezing before diagnostic generation, preserving models on resume, stale-score
rejection, exclusion of official test data, training-only PCA/scaling, portable
model round trips, regret-weighted decisions, and degenerate-label cases.
Ruff and whitespace checks pass. Real generation was launched after these checks;
the tests themselves never load Qwen or use the GPU.

Completion verification checked the frozen code/package identity, training and
tuning source checksums, diagnostic source checksum, model checksum, 150 unique
question IDs across the three roles, 500 successful attempts, and policy-freeze
time preceding the first diagnostic generation. The actual accuracy–cost figure
was visually inspected. No source code was changed to obtain these results and
no scoring audit was performed; the user's waiver remains in force.
