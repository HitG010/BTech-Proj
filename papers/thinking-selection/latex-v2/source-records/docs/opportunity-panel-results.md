# Two-solver opportunity diagnostic results

The 64-question panel is complete: **512/512 responses**, followed by unchanged
v7 scoring and the frozen analysis. The completion worker finished at
**2026-10-05 18:14:48 UTC** (23:44:48 Asia/Kolkata). Collector and finalizer exited
with code zero. The 60-job continuation had no failed attempt or retry.

The smaller solver passes both predeclared further-study checks. The larger
solver fails both. This is a diagnostic result on 64 question groups with two
draws per mode and solver. It is not a publication novelty claim, deployment
validation, or superiority confirmation of a learned router.

## Fixed policy results

Values below average the two draw directions. Accuracy uses 128 scored
outcomes per solver; uncertainty is grouped by the 64 questions. Each confidence
threshold was selected on the other draw and other question folds. The primary
feature is post-warper direct-answer confidence; raw confidence remains
secondary and does not select or replace the primary.

| Solver | Policy | Accuracy | Generated tokens/question | Utility at lambda .05 |
|---|---|---:|---:|---:|
| Qwen3-1.7B | Accept direct draft | 84.375% | 228.01 | .832350 |
| Qwen3-1.7B | Think after every draft | 87.500% | 1,586.79 | .795661 |
| Qwen3-1.7B | Confidence routing | 83.594% | 682.56 | .801809 |
| Qwen3-0.6B | Accept direct draft | 61.719% | 209.80 | .606697 |
| Qwen3-0.6B | Think after every draft | 80.469% | 1,409.52 | .734211 |
| Qwen3-0.6B | Confidence routing | 81.250% | 1,062.52 | .759374 |

Escalation cost includes the already generated direct draft plus the thinking
response. The table's always-thinking policy is therefore a sequential routing
cost, not a standalone-thinking generation cost.

| Solver | Questions with positive thinking gain in either draw | Confidence minus direct utility | Conditional 90% interval | Availability / confidence checks |
|---|---:|---:|---|---|
| Qwen3-1.7B | 4 | -.030540 | [-.056066, -.006071] | Fail / fail |
| Qwen3-0.6B | 24 | +.152677 | [+.085535, +.220375] | Pass / pass |

The availability check requires at least ten distinct positive-gain questions.
The confidence check requires average utility improvement of at least .01 and
positive point estimates in both independent-draw directions. Positive gain
charges thinking tokens at the preselected lambda .05. It is not merely a
correct answer after an incorrect draft.

For 1.7B, thinking fixes 4/3 direct errors and introduces 2/1 errors in the two
draws. For 0.6B, it fixes 15/17 and introduces 4/4. The reported intervals use
2,000 shared whole-question resamples with the fixed protocol seed. Actions
remain fixed during resampling; these intervals omit threshold-refit uncertainty.
The point difference between confidence and always thinking is not a proven
population advantage.

## Runtime and preservation

The original run's **12-hour wall-budget failure remains failed**. Its 452
completed responses and two unresolved reservations were preserved. The user
authorized a separate four-hour completion child for the remaining original
60 jobs. No question, seed, model revision, prompt, decoder, token cap, scorer
or analysis grid changed. No new questions were allocated.

The completion charged **42,505 tokens / 1,432.82 operation seconds**, with
**1,466.61 collection wall seconds**. Combined charges are **384,552 tokens /
16,134.02 operation seconds**, including both old unresolved charges. Aggregate
setup and invocation counts are four each. These are accounting records, not
a causal speed comparison. The finalizer verifies both the frozen parent-study
inventory and the separate 2,319 historical protected originals; the latter
passes before and after analysis.

Exactly the selected 64 training references were permitted only after the
complete combined endpoint and collector exit. The question-only dataset still
has no gold file. Official-test gold stays sealed. Docker was kept running;
cloud/API spend is $0.

## Artifacts and next boundary

Frozen source: `b7c3b1e`. Completion plan: `387e139c…a71b1d`.
Report payload: `f3f0d33c…ac6fd`. Cached-score payload: `f1326bf3…01283`.
All records are under
`artifacts/research/data-efficiency-v1/opportunity-panel-v1/completion-v1/`.
Its `status.json` and immutable supervisor finish record `complete`.

Preserve the frozen protocols, inputs, sources, results and scores. Do not
restart collection, rerun scoring/finalization, or reopen references. Independent
completion review uses cached scores and recorded actions only.

Independent endpoint review **passed**, payload `b67d4e0a…5dfcc` in
`completion-v1/completion-review-verification.json`. It verifies 2,319 parent
study hashes, four new source pins, 52 original pins, all 512 cells and score/
record/report identities, costs and slot counts. It reproduces 107 metric
payloads and their fixed-action paired intervals from cached scores without
fitting, scoring or opening references. Worker PIDs are absent and all five
checked locks are free.

The next design should focus on the 0.6B opportunity regime and retain
confidence as its main baseline. This result permits a prospective design
review. It does not itself authorize extra allocation, adaptive fitting on this
panel, CLM/RL promotion, acquisition scaling or sealed confirmation. The earlier
negative router/CLM results and failed gates remain unchanged.
