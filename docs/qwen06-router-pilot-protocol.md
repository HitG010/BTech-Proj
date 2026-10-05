# Bounded cached 0.6B router pilot

The completed 64-question opportunity panel found 24 Qwen3-0.6B questions
with positive incremental thinking utility in at least one draw. Its frozen
post-warper confidence policy outperformed accepting every direct draft at
λ=.05. This permits one small development test of whether direct-output
information adds useful decisions beyond confidence. The panel and solver
choice already influenced this design, so its cross-fitted result remains
exploratory. No new questions are allocated and no model response, reference,
embedding, CLM or RL call belongs to this pilot.

`scripts/qwen06_router_pilot.py` reads only the closed 512-response opportunity
endpoint, the separate completion report, its cached numeric-v7 scores and
the original frozen jobs/folds. Preparation verifies the closed collector and
finalizer, all score/record/report identities and the full study file
inventory. It freezes source/test/document hashes, dependency versions, all
128 paired 0.6B rows, features, labels, folds and settings in new artifacts at
`artifacts/research/data-efficiency-v1/qwen06-router-pilot-v1/`. The source
question-only child and all completed study files remain unchanged. Execute
has one durable start marker and no retry. A valid cached report returns without
refitting or opening references.

The action remains accept the direct answer or pay for one fresh thinking
response. Training target is net incremental utility
`g = thinking_correct − direct_correct − .05 × thinking_tokens/1000`; the direct
draft's generated tokens are already spent by either action. Evaluation cost
charges direct tokens plus thinking tokens only on escalation. At inference,
the candidate sees exactly three direct-time features: post-warper mean
generated log probability, `log1p(direct answer tokens)`, and a gold-free
numeric-v7 parser-rejection indicator. It sees no correctness label, thinking
trace, thinking tokens, opposite-draw outcome or question embedding. The 0.6B
cache has 128 finite direct confidences, only nine parser rejections and four
truncated answers; the limited signal discourages a larger architecture.

Exactly two fixed Ridge families are fit, both with α=10, training-only
`StandardScaler`, and escalation when predicted `g>0`:

1. The primary three-feature candidate.
2. A matched confidence-only Ridge control with identical loss, penalty,
   preprocessing and split.

The remaining fixed controls are accept every draft, think after every draft,
the **original frozen confidence actions and thresholds** from the completed
report, and confidence OR direct parser rejection. No threshold or family is
selected from held-out results. Five frozen question folds are crossed with
train draw 0 → test draw 1 and the reverse. Training uses only that draw and
questions outside the held-out fold; test uses the opposite draw on held-out
questions. This yields ten fits per Ridge family, **20 total**, with no alpha
grid, inner selection, extra embedding or optional refit.

Report each fit's training/test question IDs, feature columns, scaler moments,
coefficients, intercept, prediction and action. For every policy report utility,
accuracy, generated tokens, escalations, escalated rescues/harms and both draw
directions. The predeclared gate for *further study only* requires the primary
candidate's average utility difference versus frozen confidence to be at least
+0.01, positive points in both directions, and nonnegative average differences
versus matched confidence Ridge and confidence OR parser rejection. All four
checks must pass; the other controls cannot be selected post hoc as the
candidate. At λ=.05, bootstrap 2,000 times with seed 20261012 over whole
question groups, sharing the sampled 64 indices across both draws and all
policies. The 90% intervals condition on fixed fitted actions and omit
refitting, model-choice and repeated-research uncertainty. CPU feature,
prediction and fit times are reported separately from generated tokens; they
are not co-resident solver/router latency.

After review and a source/test/doc checkpoint, the operator commands are:

```sh
.venv/bin/python -m scripts.qwen06_router_pilot prepare
.venv/bin/python -m scripts.qwen06_router_pilot verify
.venv/bin/python -m scripts.qwen06_router_pilot execute
```

Do not repeat execute after a failure. A favorable cached development result
would justify only a separately frozen fresh-question child and test. It does
not establish superiority, architecture novelty, or permission to scale
acquisition, CLM/RL, MATH or the sealed confirmation. The previous negative
1.7B router/CLM results and original opportunity wall-budget failure remain
unchanged.
