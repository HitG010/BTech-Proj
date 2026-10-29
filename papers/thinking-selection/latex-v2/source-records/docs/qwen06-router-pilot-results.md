# Fixed 0.6B router pilot: the learned candidate does not pass

The single frozen CPU execution completed all **20 fits**. The primary
three-feature Ridge improves utility over frozen confidence by only **.003516**,
with conditional 90% interval **[-.031959, +.037163]**. It fails the required .01
gain and loses to the parser-aware confidence control. Two of four predeclared
checks fail. Close this learned recipe; do not expand alpha, features or the grid.

## Recorded policies

The values average the two opposite-draw evaluations on 64 reused question
groups. Confidence decisions are the exact original recorded decisions. All
learned scaling and coefficients use only training questions and the training
draw. Escalation charges the direct draft plus the additional thinking response.

| Policy | Accuracy | Tokens/question | Utility | Difference from confidence | Conditional90% interval |
|---|---:|---:|---:|---:|---|
| Accept draft |61.719%|209.80|.606697|-.152677|[-.224883,-.087749]|
| Think after every draft |80.469%|1409.52|.734211|-.025163|[-.069654,+.018038]|
| Frozen confidence |81.250%|1062.52|.759374|0|[0,0]|
| Confidence OR parser rejection |83.594%|1081.41|.781867|+.022493|[+.007453,+.044905]|
| Matched confidence-only Ridge |79.688%|1254.07|.734171|-.025203|[-.057842,+.007138]|
| Primary three-feature Ridge |82.031%|1148.45|.762890|+.003516|[-.031959,+.037163]|

The full candidate's two direction differences are +.002458 and +.004573.
Both are positive, and the candidate beats its matched confidence-only learner.
Those two checks pass. Its average gain is below .01, and its utility is below
confidence OR parser rejection; these two checks fail. No different policy is
selected post hoc as the original primary candidate.

## What the simple control shows

The fixed heuristic escalates when either the original confidence policy says
to think **or** gold-free v7 parsing rejects the direct response. It has 87
escalations versus 84 for confidence. All three extra actions, on **three distinct
question groups**, change an incorrect scored draft to a correct thinking
answer. They add 2,419 generated tokens over 128 scored outcomes: +18.90 tokens
per question, for +2.344 percentage points of scored accuracy.

This is development evidence for a stronger baseline. It is not a nominated
novel router, a deployment claim, or fresh confirmation. Only three groups
support its incremental gain, and this panel has influenced design. The 90%
intervals resample 64 whole questions with actions fixed; they omit refit,
selection and repeated-research uncertainty. Do not promote the control by
replacing the failed primary endpoint.

Separately, positive thinking gain occurs on 15/17 questions in the two draws,
with 8 positive in both and 16 positive in only one. Direct drafts differ across
draws. This descriptive disagreement does not establish same-state label noise
or prove that purchasing more repeats is useful.

## Accounting, identity and next boundary

Source/tests/protocol froze at `8413e9e`; full 653 offline tests and independent
preexecution review pass. Plan `1d0f145a…460a0`, rows `1864fa8c…c3dfc`, report
`ccdd2a2a…20ccf`. CPU fit/analysis took about .045 seconds; cached preprocessing
about .011 seconds. These are idle cached measurements, not live router/solver
latency. No solver response, embedding, download, scoring/reference access,
role change or cloud/API spend occurred. Docker remained running.

The [prospective power report](qwen06-next-experiment.md) is complete, payload
`fc2c4c5d…7734c9`, under `qwen06-next-design-v1/`. It verifies 484 reserve rows
remain unclaimed. Its 228-question/700872-response-token proposal was conditional
on **all four learned-candidate gates**. That condition failed. No questions are
selected or allocated, and no fresh collection is started for this candidate.
At hypothetical SD .16, the proposed 228 groups would have only 15.66% power for
a +.01 learner-minus-confidence effect; approximately 2,010 groups are needed for
80% under that scenario. This does not size a new parser-control comparison.

Independent postrun review **passed**, payload `4316c492…4cb2f` in
`qwen06-router-pilot-v1/completion-review-verification.json`. All 2,652 closed
study files and source pins match. The reviewer verified all 20 Ridge solutions
against their normal equations without refitting, reconstructed 256 learned
predictions and 768 policy decisions, and reproduced policy means, intervals,
direction results and gates. The power review independently reproduced 12
minimum-sample cells, 72 powers and 24 detectable effects. It confirms all 484
reserve questions remain unclaimed. No scoring, reference, generation or
allocation action occurred during review.

Preserve the finished pilot and planning payloads. Do not prepare/execute the
pilot again, adapt its grid or reopen references. The next design should make
parser-aware confidence a mandatory cheap baseline, with any fresh baseline
validation separately specified before collection. A claim about acquisition
still requires equal-acquired-token learning curves, new-question/repeat/action
controls and independent evaluation. CLM/RL/MATH, acquisition and confirmation
are not promoted by this result. Earlier negative evidence remains unchanged.
