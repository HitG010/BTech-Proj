# Phase 2c: bounded representation and objective pilot

Protocol decision: 2026-10-03, before any real feature extraction or fitting.
This exploratory study uses the completed repeat panel and unchanged cached v7
labels. It follows the completed Phase 2a parser preflight and Phase 2b CPU study.
Completion of 2b is required; its promotion screen need not pass, because this
pilot tests the separately specified representation/objective hypothesis. The
grid below was specified before observing either study's fitted results.

The implementation is `scripts/repeat_contrastive_pilot.py`. This is a compact
CLM-inspired action-scoring experiment using cached MiniLM, with no released
CLM-8B weights or backbone fine-tuning. It cannot establish novelty, restore the
failed primary gate, or authorize acquisition scaling.

## Freeze and input boundary

`--freeze-only` writes a new immutable analysis plan before encoding or fitting.
It binds source/test/protocol hashes, dependency versions, the completed CPU
report and its input identity, the frozen endpoint, scores, primary report,
question features, and all files in the pinned local MiniLM snapshot. `--execute`
requires that exact identity, holds an output lock, and refuses an existing
feature or result output. Results and features live outside the frozen study.

Only the completed 800-response endpoint is eligible. Cached correctness and
thinking cost supply training/evaluation targets; no reference answers are
opened and no scorer is called. Feature construction selects direct answer text
only. Thinking text, opposite-half outcomes and held-out labels are excluded
from representation construction and fitting. Frozen package/config sources,
roles, v7, primary reports and completed collectors remain unchanged.

## Representations and matched head

The local encoder is `sentence-transformers/all-MiniLM-L6-v2` at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU float32. Loading uses the pinned
local snapshot with offline flags and `local_files_only=True`.

- **Question only:** unchanged cached first 384 embedding coordinates.
- **Question plus draft:** normalized mean of the question vector and a separately
  normalized direct-draft vector. The draft keeps the final 256 tokens including
  special-token allowance, with masked-mean pooling. Record original lengths,
  truncation frequency, cold load and warm draft-encoding times. This mean-vector
  fusion is one narrow representation test, not exhaustive draft conditioning.

For each training split, PCA8 fits only permitted training state rows, with equal
draw counts per question. Training-only scalers standardize the PCA8 and existing
four draft statistics; divide these blocks by sqrt(8) and sqrt(4). Exclude lexical
features from both representation arms. All draws of a question remain together.

Every objective uses the same 120-parameter head: affine 12→8 projection,
normalized projected states, two learned normalized eight-dimensional action
prototypes, and cosine logits divided by temperature 0.1. Actions are accept and
fresh thinking. This matches capacity and initialization across objectives.

## Fixed objective and optimization grid

The target is `g = T_correct − D_correct − .05 × T_generated_tokens/1000`.
The margin is `logit_think − logit_accept`.

1. **Gain MSE:** mean squared error between the margin and g.
2. **Regret-weighted forward CE:** binary CE with label `g>0`, weighted by `abs(g)`
   and divided by total weight.
3. **Bidirectional contrastive:** average of that forward loss and reverse
   action-to-state CE. Within each action, all matching states are positives,
   with target weights proportional to `abs(g)`. Average only present actions.
   Duplicate action labels are not treated as mutually exclusive negatives.
4. **Ordinary binary CE:** unweighted CE for `g>0`, as an event-label control.

These scores have different estimands. Weighted CE scores are not probabilities
of positive gain or correctness; compare their decision utility. With two actions,
the forward loss alone is binary classification. The reverse term is the specific
objective ablation here.

Optimization is full-batch Adam, learning rate .01, weight decay .001, exactly
100 epochs, fixed seed 20261004, no early stopping, no backbone updates. Numerical
libraries use at most two CPU threads. Only one optimization seed is tested;
its variability is a limitation rather than a reason for outcome-driven retries.

## Evaluation, selection and bound

Use the five frozen outer question folds and four inner folds with seed
20261002+outer_fold. Conditions are A4→B4, B4→A4 and full8 secondary. All inner
tuning uses acquired training-half labels. Outer questions and opposite halves
remain evaluation-only. Full8 has no independent same-question eight-draw replica.

Each of eight families (two representations × four objectives) chooses a margin
threshold from {−.1, 0, .1} by mean inner question utility; ties prefer the higher
threshold. Select a family by inner utility; ties follow the frozen family order.
Report every family and the nested selected policy. Outer scores never select
the family, threshold, optimization schedule or additional variants.

The fixed bound is **600 head fits**:
3 conditions ×5 outer folds ×(4 inner+1 outer) ×8 families. PCA transforms are
shared across objectives within a representation/split. There are 150 PCA fits.
Feature encoding processes 400 direct drafts once. No new solver generation.

Report individual directions, average whole-question utility differences against
confidence, 2,000-draw fixed-fit question bootstrap 90% intervals (seed 20261004),
accuracy, generated tokens, escalations, rescues, harms and missed opportunities.
Confidence actions must reproduce the primary report. Router encoding time stays
separate from historical generated-token utility; the cached question embedding
cost and live head/PCA latency are not measured, so these timings cannot establish
complete deployment latency.

The exploratory promotion screen for the nested selected policy requires average
utility gain ≥.01, positive point differences in both directions, and positive
averaged mean differences after deleting each question in turn. Passing can only
prioritize a separately frozen fresh-question test. Bootstrap intervals condition
on fixed fits and do not correct for repeated research use or model selection.

Stop after the fixed grid. A negative outcome narrows evidence for this specific
mean-vector representation and small-head objective setup; it does not disprove
all contrastive architectures. Released CLM, RL and acquisition scaling remain
conditional on new signal and resource evidence.
