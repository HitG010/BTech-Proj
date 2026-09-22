# Research direction after the pilot

Analysis date: 2026-09-14. This is a proposed revision, not an implemented
experiment or an established novelty claim. Existing pilot records remain frozen.

## What the results support

The [verified pilot](pilot-results.md) measures Qwen3-1.7B under a specific
generation and scoring protocol: direct accuracy is 63%, thinking accuracy is
46%, and thinking uses approximately 6.6 times the generated tokens and 6.8 times
the response time. The paired accuracy difference is -17 percentage points
(95% question-bootstrap interval: -25.5 to -8.5 points).

Final-answer truncation affects 31.5% of direct responses and 52.5% of thinking
responses. Of 182 recorded answer failures, 168 are truncated responses. This
does not imply that extending them would make them correct. It establishes that
the comparison is strongly affected by completion under the configured cap.
Only 15% of thinking responses exhaust the reasoning allowance. Investigate the
final-answer stage before increasing the 2,048-token reasoning allowance.

Our protocol already separates reasoning and answer allowances. Nevertheless,
the final-answer stage frequently contains a lengthy explanation despite the
boxed-answer instruction. Consequently, this is not a direct replication of a
shared reasoning/answer budget experiment.

An exploratory analysis averages the two correctness observations per mode for
each question. Thinking has the higher observed average on 6 questions, direct
on 27, and 67 tie. Retrospectively choosing the higher observed average gives
67% accuracy, versus 63% for always-direct. This four-point observed headroom
uses labels and just two samples per mode; it is neither a deployable router nor
a bound on true population performance. It warns against investing heavily in a
controller before checking whether useful mode complementarity persists under
a better calibrated protocol. Selecting a mode from one labeled pair and
evaluating on the other, averaged in both directions, gives 64.5%; this still
uses labels from the same questions and is not unseen-question evaluation.

The corresponding paired outcomes across 200 sample pairs are: both wrong 65,
only thinking correct 9, only direct correct 43, both correct 83. Seventeen
questions change their paired correctness pattern between the two samples.
These exploratory quantities are saved in
`artifacts/runs/af1f1e56c5d453bbfd5e/report/exploratory_routing_diagnostics.json`.

## Novelty boundaries from current related work

- [The Coupling Tax](https://arxiv.org/abs/2605.07686) already investigates
  direct/thinking reversals under token limits and proposes split budgets and
  strengthened answer extraction. Reserving answer tokens is not a sufficient
  contribution by itself.
- [DART](https://arxiv.org/abs/2606.23181) uses agreement between two direct
  drafts and draft entropy to route and allocate thinking budgets without
  labeled training. Basic adaptive direct/thinking routing is already covered.
- [Targeting the Exceptions, authors' implementation](https://github.com/wikit-ai/online-active-learning-llm-routers)
  builds a retrieval router's support corpus through active learning under a
  finite annotation budget. Generic active learning for routers is insufficient
  as a novelty claim.
- [Pandora's AI Model Routing Box](https://arxiv.org/abs/2608.20316) studies
  whether more expensive inference-time value estimation is worth its cost.
  Generic value-of-information routing also has close prior work.

This is a targeted literature check, not an exhaustive novelty clearance.

## Recommended contribution to investigate

Working title: **Learning When to Think with Fewer Generated Training Tokens**.

Research question: Can a training-data collector learn a useful question-only
reasoning router more cheaply by choosing among three acquisition actions?

1. Obtain observations for a new training question.
2. Draw another independent response for a previously observed question/mode.
3. Extend an unfinished trajectory to observe an answer at a larger allowance.

The candidate contribution is the joint choice of question, independent
replication, and trajectory completion under a generation budget. The pilot
motivates this because unfinished outputs and variation between independent
samples create different information needs. Existing results do not establish
that this proposed approach will help or that the exact combination is new.

Keep deployment inexpensive: the deployed controller sees only question
embeddings and question-derived features. Output text, correctness, and
completion status may guide training acquisition but must not become hidden
deployment features.

Score acquisition actions by estimated *reduction* in downstream routing regret
after observing their outcome, divided by marginal acquisition cost. The original
plan's current posterior regret divided by pair cost is a useful baseline, but
it is not automatically expected information gain: high uncertainty may be
irreducible, and additional repetitions may not improve the learned router.
A bootstrap ensemble with hypothetical observation updates is one approximation
to investigate in synthetic tests before spending model compute.

For a capped response, success at the current allowance is observed under the
locked scorer. Its outcome at a larger allowance remains unknown. Do not treat
all capped outputs as missing labels, impute eventual correctness, or discard
failures. Extending the same trajectory does not create an independent
Beta–Bernoulli trial. Track trajectory identity and budget-specific outcomes.
Continuations also have input-processing costs; recomputing a prefix is not free.
Faithful resumable sampling needs an explicit RNG-state policy, beyond a seed.

Evidence needed for a contribution: better held-out utility at equal acquired
training-token budgets, or fewer training tokens to reach a predefined utility
target, across multiple acquisition seeds. Use the same controller architecture
for every acquisition strategy. Compare uniform, random, uncertainty-only,
original regret-per-cost, and a clearly documented adaptation of a relevant
active-learning router baseline. Ablate continuation, completion information,
cost normalization, and expected learning gain. Account separately for actual
cache-building expenditure and each strategy's revealed observations.

## Insert Milestone C.5 before controller training

1. Deterministically choose 25 pilot questions without selecting for observed
   successes or failures. Use two samples per mode. Hold the model, prompt,
   precision, sampling settings, and reasoning allowance fixed; compare final
   answer allowances of 256, 512, and 1,024 tokens.
2. To reduce generation cost, test whether one 1,024-token trajectory can supply
   valid capped prefixes. This requires that allowance does not enter the prompt
   or otherwise change earlier generation. Verify prefix equivalence and
   correctly reconstruct termination/scoring states before relying on it.
   Prefixes are correlated measurements, not independent samples. Estimate
   runtime from initial jobs before scheduling the full calibration.
3. Evaluate stronger answer-format instructions or a separate non-thinking
   answer-extraction pass as distinct experimental arms. Do not change prompt
   and cap together and attribute the difference to either one. For extraction,
   include a question-only control and count all calls and processing overhead.
   Treat extraction as a prior-work baseline, not the proposed contribution.
4. Preserve current strict completion-aware accuracy. If adding a metric that
   accepts an unambiguous completed answer before later truncation, define it
   before rerunning, report it separately, and never choose a candidate using
   the gold label or an arbitrary number from reasoning text.
5. Once truncation is substantially reduced and the protocol is selected, rerun
   the 100-question pilot and recalculate paired accuracy, costs, and observed
   routing headroom. Obtain a human audit of a stratified subset; the existing
   51 formal reviews are agent reviews.
6. Freeze the protocol before training and validation; preserve the 500-question
   official test split. Evaluate accuracy against total inference cost, counting
   both drafts or both generations when a baseline escalates.

If useful complementarity remains small, add a predeclared diagnostic set from
the planned procedural tasks or SVAMP before scaling acquisition. Do not select
test examples because thinking wins on them. A robust negative finding is
preferable to forcing a learned router into a setting with little benefit.

## Other changes to the original plan

| Proposed change | Reason and constraint |
|---|---|
| Start acquisition with the same 32–50-question seed set for all strategies | Buying a pair on all 400 questions first removes the chance to demonstrate savings at small budgets; charge the common seed set and retain full initialization as an ablation. |
| Build the union of requested traces lazily | An eight-pair cache for 400 questions contains 6,400 responses, approximately 4.74 million charged tokens and 55 local hours at pilot rates. Longer answer caps can increase this. |
| Add DART as an inference baseline | A learned router must justify its training expenditure against a strong training-free alternative; count both draft calls. |
| Retain the simple MiniLM/ridge controller initially | A stronger acquisition comparison needs controlled router capacity. Defer extra actions and reinforcement learning until binary routing has demonstrated value. |
| Add uncertainty over acquisition runs | Start with at least three independent acquisition seeds, expand if variance requires it, and bootstrap whole evaluation questions with policies paired. |
| Keep generation tokens and measured time distinct | The current thinking answer call recomputes the prefix; direct confidence calculation also has overhead. Any optimization creates a separately identified backend configuration. |
| Defer the 4B confirmation until the main method works | Two Qwen sizes support scale replication, not cross-family generalization. Add another family only if a broader claim is intended and the budget permits. |

The $100 ceiling remains unchanged. The earlier 37.78-hour projection covers
1,100 questions with two samples per mode, not the full repeated acquisition
cache. No cloud pricing or throughput equivalence should be inferred from local
timings. No additional model generations or cloud jobs were launched for this
analysis.
