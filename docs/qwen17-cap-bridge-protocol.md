# Development-only matched 1.7B cap bridge

This is a proposed local engineering diagnostic after the fresh 0.6B sparse
validation is **terminal complete and independently reviewed**. Preparation is
locked until that ordered boundary; a negative 0.6B result does not block
investigating a different solver. The prep-only module has no generation,
reference, scoring or training command. No actual plan or question snapshot
has been prepared by writing this code.

The original 64 development questions contain 18 thinking cells with forced
closure at 2,048 reasoning tokens, spanning 11 questions: seven questions have
two capped draws and four have one. Select all such cells solely by the cached
generation metadata. Do not select by correctness, harm, parser result or
confidence. These are cap-enriched development cells, not fresh questions or
an unbiased sample of the original panel. No reserve role is allocated or
changed. Old sources, logs, responses, scores and labels remain immutable.

For each cell, collect **two new** thinking responses: a 2,048-token control
and a 4,096-token arm. Preserve the original question metadata, draw index and
explicit per-cell generation seed in both arms. Do not derive a new seed from
the arm identity or new directory. Keep the pinned Qwen3-1.7B weights/tokenizer,
MPS/float16/SDPA, prompt, sampling, answer cap 512, closure `[151668,271]`, EOS
handling and v7 parser. Only the reasoning cap differs as an inference setting.
The question snapshot declares development reuse and contains no gold.

Thirty-six new responses reserve `18 × (2,562 + 4,610) = 129,096` tokens. A
future separately frozen executor should use one **global** 160,000-token and
four-hour wall/charged-time budget for both arms, including setup, failures,
interruptions and retries. Proposed setup/job ceilings are 900/600 awake
monotonic seconds, at most two invocations/setups, first-failure stop, one
explicit resume at most and no automatic resume. The 4k job allowance fits
within the job timeout only if actual throughput supports it; the time cap is
not a completion guarantee. Keep the laptop open/on AC, the native temporary
activity/sleep guards and Docker running. No Kaggle inference or paid API/cloud
is used in this bridge.

Alternate paired arms in a fixed balanced order to reduce order confounding;
freeze that order and every attempt/setup admission before collection. Record
actual reasoning, answer and inserted token IDs/counts and all elapsed charges.
Do not borrow old timing or old output labels as the new control arm. Compare
new 2k tokens with the cached original per seed as a replay diagnostic. Compare
the two new arms' shared reasoning prefix through their first close/EOS or the
shorter cap as an engineering gate. Final answer streams after the old forced
close may legitimately differ. No bitwise MPS determinism is promised. A
failed prefix gate must remain an engineering failure; no silent retry or
seed search may repair it. Freeze its effect on reference eligibility before
launch; do not decide that after observing outcomes.

Only the complete 36-response endpoint, exited collectors, engineering,
accounting and preservation checks may permit fetching **exactly the 11
selected upstream-training references under this new endpoint**, for the new
outputs only. This is an explicit authorized reopening of selected development
references, not a rerun of the old 64-question scorer. Keep the question
snapshot gold-free and write separate reference-digest/score sidecars. Do not
change the old v7 labels or reopen the remaining 53 references. No reference
function belongs to `scripts/qwen17_cap_bridge_plan.py`.

Report paired thinking accuracy, generated tokens and utility at unchanged
λ=.05. Direct drafts are already spent: they cancel in the cap-arm difference.
If reporting total post-direct utility, use the unchanged cached direct cost
for both arms and identify that reused input. Primary descriptive differences
average within each selected question and then equally over the **11 groups**;
also show the separate 18-cell average. A predeclared 2,000-draw whole-question
bootstrap with seed 20261020 and 95% intervals conditions on these selected
cells and cached trigger. It is imprecise development evidence; it cannot
establish whole-panel accuracy, fresh generalization, live latency advantage,
acquisition promotion or novelty. Higher correctness can lose token utility.

After source/test/doc freeze and ordered validation review, the preparation
commands for the user-authorized next stage are:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.qwen17_cap_bridge_plan prepare
PYTHONPATH=src .venv/bin/python -m scripts.qwen17_cap_bridge_plan verify
```

The ordering gate expects the sparse runtime's `status.json` to be `complete`
with its report hash, and `completion-review-verification.json` to contain
`checks_passed: true` and the same `report_sha256`. This checks reviewed
completion, not the scientific guard screen. The resulting cap plan still
says `generation: unimplemented_locked`. A separate executor/protocol review
is required before any model response, scoring or reference access.
