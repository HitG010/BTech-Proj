# Frozen prospective two-solver opportunity diagnostic

Protocol date: 2026-10-04. This is a new local study. It uses the existing
question-only `opportunity64-v1` child. Keep its 64 questions, folds, source
indices and parent roles unchanged. Extra data requires a separate prospective
child and protocol after this diagnostic. This study is not confirmation of a
new router or a +.01 performance gain.

## Questions, solvers and jobs

Use 64 upstream-training questions, two solver sizes, two independent draws per
mode and both direct/thinking modes: **512 responses / 256 pairs / 64 groups**.
The five prepared folds contain 13/13/13/13/12 questions.

| Solver | Frozen model/tokenizer revision | Base seed |
|---|---|---:|
| Qwen3-1.7B | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | 20261010 |
| Qwen3-0.6B | `c1899de289a04d12100db370d81485cdf75e47ca` | 20261011 |

Preparation resolves only local tokenizers/configs. It pins model files with
SHA-256, source/tests/document/package hashes, stable package environment,
decoder metadata and every exact job identity/seed. Assert 512 different job IDs
and seeds. The unchanged job builder does not include model identity in its seed
hash, so the two base seeds must differ. No weight loading or reference access
occurs during preparation. Refuse partial or repeated preparation.

Keep `qwen3-boxed-budget-v3`, MPS, float16, SDPA and local-only model loading.
Keep the unchanged bridged prompt suffix and mode-specific sampling settings.
Answer cap is 512 tokens; thinking cap is 2,048 tokens. Actual closure IDs are
`[151668,271]`; EOS IDs are `[151643,151645]`. Both solvers use the same answer
and reasoning limits. The **786,944-token** response maximum includes inserted
closure and EOS tokens. It excludes failed attempts and setup.

Run solver arms sequentially, 1.7B then 0.6B. Separate processes release model
memory between arms. This fixed order cannot identify causal speed differences.
Keep Docker running. Do not change system preferences or stop other services.
Use the existing process-scoped macOS activity guard and process-scoped
`caffeinate -i`. No cloud/API execution, downloads or package changes.

## One global ledger and bounded execution

The entire new collection uses a **1,000,000-token** ceiling and a **12-hour**
time ceiling. Token use covers both arms and all failed/unresolved attempts.
The time measure is the larger of summed setup/attempt charges and collection
wall age from the first invocation. Gaps between invocations count. A durable
end marker stops wall-age accounting before scoring/analysis. This conservative
time rule is stricter than summing model calls alone. It is a stop boundary, not
a completion-time guarantee.

Reserve one initial invocation per solver. Permit at most one explicit resume
per solver, four collector invocations/setup sessions globally. A resume is
eligible only after a runtime failure, never after integrity failure or budget
exhaustion. There is no automatic resume. Limit the supervisor to three launches
and 14 hours per launch. Each launch/start is durable and one-time.

Before constructing the backend, reserve setup time, at most 900 seconds.
Before each generation, reserve the complete job token allowance and up to
600 seconds, capped by the remaining global time. A single collection writer
lock protects all reservations, attempts and results. The global ledger uses
immutable reservation/settlement files; it never grants a full budget per arm.
Unresolved operations keep their full token/time reservations. Corruption
blocks further work. Record actual elapsed overruns; do not clip charges.

Write a completed result before its final settlement. Preserve failed outputs
under unique attempt IDs. Never replace completed results or failed attempts.
A crash after the result write retains a conservative full reservation. The
same frozen job and seed may run again only if no completed result exists and
the bounded runtime resume is eligible. No prompt, seed or decoder changes.

The supervisor samples its own child RSS every two seconds and checks the
active setup/job deadline with five seconds of polling/termination grace.
The observed RSS ceiling is 9 GiB. Missing live RSS telemetry stops collection.
Timeouts are cooperative inside the generator; the supervisor can terminate
only its own child and then escalate to kill after five seconds. Neither
sampling nor deadlines guarantee instantaneous memory/time enforcement.
RSS is not total unified-memory accounting.

Stop at the first timeout, generation exception or invalid accounting result.
Preserve reservations, outputs, process exit and failure reasons. Incorrect or
incomplete model answers are completed outcomes. In particular, valid
`answer_limit`, `early_eos` and `reasoning_in_answer` outputs are scored by the
unchanged v7 rejection policy. Do not retry to obtain a better answer.

## Reference and scoring endpoint

Before opening references, verify all 512 distinct frozen completed cells, exact
job/seed/source/solver identities, token-ID lengths, closure/EOS accounting,
finite direct raw and post-warper confidence, ledger links, global limits and
exited collectors. Acquire the collection lock for the scoring transaction.
The supervisor remains the only active coordinator.

Fetch exactly the child's 64 selected references from the pinned upstream
training Arrow source. Project the answer column and select indices before
materializing values. Record one score-start marker before fetching. A failed
reference/score invocation cannot silently restart. Keep the child dataset's
`gold_sha256` null. Do not add a gold file or call ordinary `rb score`.

Use unchanged `numeric-v7` and its pinned dependencies. Write one separate
score sidecar binding protocol, selected rows, records, reference digest and
scorer. Subsequent analysis/review must validate and reuse that sidecar without
reopening references. Preserve every old v7 label and primary report.

## Fixed diagnostic analysis

Keep lambda .05 and the post-direct decision: accept the first draft or pay for
a fresh question-only thinking solve. Always accepting charges direct tokens.
Escalating charges direct plus thinking tokens. Direct cost is sunk when
comparing the two actions. Do not call an action probability a correctness
probability or a question intrinsically thinking/nonthinking.

Report direct/thinking accuracy, rescue, harm, positive incremental utility,
generated tokens and distinct positive-gain questions by solver and draw. A
rescue is direct wrong/thinking correct. Harm is direct correct/thinking wrong.
Positive gain is `thinking_correct - direct_correct - .05*thinking_tokens/1000 > 0`.

Controls are accept, escalate and scalar confidence cutoffs. Retain existing
post-warper confidence as the mandatory comparator. Report raw confidence as a
separate predeclared secondary control. No model selection between those two
controls; no learned embeddings, CLM finetuning, fusion or architecture grid.
There are 40 scalar cutoff fits: two features × two solvers × two draws × five
folds. Train on one draw of other question folds and evaluate the opposite draw
of held-out questions; reverse draws. Keep strict `<` cutoff comparisons and
the existing tie rule toward fewer thinking calls. Held-out and opposite-draw
labels cannot select thresholds.

Use 2,000 whole-question bootstrap resamples with seed **20261009**, sharing
each resample across both solvers and draws. Report 90% intervals and paired
solver opportunity-rate differences. Thresholds/actions remain fixed during
this bootstrap, so the intervals omit training/refit uncertainty. Two draws
cannot establish stable question-level gain labels. Draws and solvers do not
create 256 independent evaluation units.

Availability screen: at least ten distinct positive-gain question groups per
solver; harms cannot satisfy it. Confidence further-study screen: average
confidence-minus-accept utility at least .01, with positive points in both draw
directions. The mandatory screen uses post-warper confidence. Raw confidence is
reported separately. Neither screen is a superiority claim or permission to
launch acquisition, RL or confirmation. Keep both solver results; do not select
the successful solver post hoc and call it the primary result.

More data is conditional on these results and a new precision/target review.
Audit sibling reserve children before selecting more questions. The existing
parent has 484 unclaimed reserve rows. Do not silently extend this panel, reuse
its outcomes as independent confirmation, or open sealed test/confirmation data.

## Checkpoint and commands

Freeze source, tests and this protocol before native preparation and launch.
Preparation needs Metal access for the actual tokenizer/backend metadata; it
loads no model weights. The ordinary environment remains unchanged.

```bash
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_panel_collect prepare
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_panel_collect launch
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_panel_collect status
```

Use `launch --resume` only for a reviewed eligible runtime stop within the fixed
journals/limits. Do not restart completed preparation, arms or analysis. Preserve
all immutable files and logs. A final automated review must confirm original
2,319-file preservation and exact cached arithmetic. The human audit remains
waived. No publication novelty is established by preparation or collection.
