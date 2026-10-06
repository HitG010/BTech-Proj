# Cached 1.7B solver-performance diagnosis

This is a post-hoc descriptive audit of the completed 64-question/two-draw
opportunity panel. It uses only the 256 frozen 1.7B responses, the separate
numeric-v7 score cache and completed report. The original run's 12-hour budget
failure, the completion deviation, all primary labels and all earlier negative
router/CLM results remain unchanged. No model is trained or run, no response is
rescored, and no reference or official-test answer is opened.

The additive script `scripts/qwen17_solver_diagnosis.py` first freezes source,
test and document hashes, the original protocol/completion/score/report digests,
all 2,652 current closed-study file hashes, and the exact paired rows into a
plan outside the frozen study. One descriptive execute is permitted, with a
durable start marker and cached-report return. The report contains exact
counts and fixed-action arithmetic, without confidence intervals or a
statistical superiority screen. It retains only hashes and lengths of
parser-rejected final-answer strings; these are gold-free syntax observations,
not a human or mathematical correctness audit.

The following six policies are fixed before this audit: accept the direct
draft; always generate thinking after the draft; reuse the completed report's
confidence decisions; confidence OR a direct v7 parser rejection; and two
post-thinking fallbacks that return the already available direct draft when
confidence chose thinking but the thinking answer is parser-rejected or hit
forced closure, respectively, provided the direct answer parsed. Both fallback
rules **still charge the entire thinking call**. They are post-hoc diagnostic
rules, not tested deployable policies. Counts include their changed cells,
recovered harms and lost rescues. No threshold, feature, family or score is
fit or selected.

The read-only pre-audit found 108/128 correct direct answers and 112/128
thinking answers. Seven rescue cells occur on four questions, three harm cells
on two questions, and 13 both-wrong cells on seven questions. Thinking adds a
mean 1,358.78 generated tokens after a 228.01-token draft. At λ=.05, accepting
direct has utility .832350; always thinking after the draft has .795661. Frozen
confidence escalates 34 times, catches one rescue and two harms, and has utility
.801809. The confidence OR direct parser-rejection rule escalates 36 times,
catches no extra rescue, and has .799913 utility. The post-thinking syntax
fallback changes five cells, recovers one harm and loses no rescue, yielding
.809622; forced-closure fallback changes nine, recovers two harms and loses no
rescue, yielding .817434. Both remain below direct acceptance. These are
descriptions of the same cached labels, not fresh evidence for a router.

Thinking hits the 2,048-token reasoning cap with forced closure in 18/128
responses. Nine of 13 both-wrong cells and all three harms are among those
cap hits; this is correlation, not proof that a longer cap fixes them. Five
thinking answers reach the 512-token answer cap. Four thinking outputs are
incomplete/answer-limited and two are classified `invalid_number` by the
unchanged v7 policy, despite visible boxed numerals in those outputs. Their
mathematical correctness was not checked. Six thinking parser rejects in all,
five selected by confidence, supply only a highly optimistic fixed-action
bound: if every rejected thinking answer became correct, the always-thinking
utility difference versus direct could move from −.036689 to +.010186, and
the frozen confidence difference from −.030540 to +.008523. This is not a
justification for relabeling or replacing the scorer.

The frozen generation config uses sampled non-thinking temperature .7/top-p
.8/top-k20 and thinking temperature .6/top-p .95/top-k20. These agree with the
[official Qwen3-1.7B model card](https://huggingface.co/Qwen/Qwen3-1.7B),
which warns against greedy thinking decoding. The frozen prompt requests a
numeric boxed final answer. A plausible next engineering hypothesis is a
**separately frozen matched bridge** of the existing 2,048-token thinking cap
against 4,096 on cases selected by a gold-free cap trigger, with the same
model, prompt, sampling, seeds, v7 parser and explicit extra-token charges.
This cannot be interpreted as an unbiased whole-panel or fresh-question
accuracy gain; a later prospective protocol would be necessary. Do not change
frozen sources or rerun their collector/finalizer for this diagnosis.

After source/test/document review and checkpoint, the operator commands are:

```sh
.venv/bin/python -m scripts.qwen17_solver_diagnosis prepare
.venv/bin/python -m scripts.qwen17_solver_diagnosis verify
.venv/bin/python -m scripts.qwen17_solver_diagnosis execute
```

Do not repeat execute after a failed attempt. The output lives at
`artifacts/research/data-efficiency-v1/qwen17-solver-diagnosis-v1/`.
