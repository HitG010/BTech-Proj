# Phase 2b bounded CPU feasibility protocol

This separate **post-hoc/development** analysis uses the completed 50-question
repeat panel and cached numeric-v7 scores. It cannot replace the primary report,
restore failed progression gates, authorize acquisition scaling, or establish
novelty. No new generation, references, model download, or gold is used. The
completed Phase 2a compatibility report is a mandatory immutable prerequisite;
the unchanged cached v7 labels remain authoritative.

## Frozen inputs and execution boundary

`scripts/repeat_cpu_feasibility.py prepare` checks the complete 800-response
endpoint and freezes `analysis-plan.json` in a new output directory. It fits
nothing. The plan binds source, synthetic tests, this protocol, package versions,
Python version, complete endpoint rows, cached scores, primary report, question
features, and the Phase 2a report. `run` requires that exact plan, verifies all
identities before fitting, holds an exclusive output lock, and checks identities
again before publishing an immutable report. An existing valid report is returned
without fitting. Root review and checkpointing happen between preparation and
execution. Frozen study files remain immutable.

## Fixed controls and candidates

Evaluate A4→B4, B4→A4, and secondary full8, using the five frozen question folds.
All inner tuning uses four grouped question folds and the acquired training
draws only. Outer-held-out correctness and opposite-half outcomes never enter
tuning, transforms, or family selection. Full8 has no independent same-question
eight-draw replica. Utility is correctness minus `.05 × generated tokens /1000`;
the direct draft is always charged, and escalation also charges fresh thinking.

Historical accept, escalate, confidence, solver-only, and combined controls use
the original pure fold fitter and original seeds/alphas. Every held-out action
must reproduce the cached primary action exactly for all three conditions.

The fixed new grid contains:

- **Draft4 ridge:** existing four deployable draft features, standard scaling,
  ridge alpha `{100,1000,10000}` and escalation threshold `{0,.02,.05}`.
- **Compressed combined ridge:** PCA8 of the 384 frozen question embedding
  coordinates, three preserved lexical features, and four draft features. PCA
  fits unique training questions only. PCA, lexical and draft blocks each fit
  training-only standard scalers, then divide by square root of block dimension.
  It uses the same alpha and threshold grid.
- **Confidence correction:** the inner-selected draft4 alpha/threshold supplies
  an escalation recommendation. Override the independently training-tuned
  historical confidence action only where absolute predicted gain reaches the
  chosen margin `{.02,.05,.10}`. Smaller predictions retain confidence's action.

Inner utility is averaged equally over validation question groups. Ties prefer
larger alpha, threshold, or correction margin; family ties use the listed order.
For each outer fold select one new family by inner utility. Outer results never
select the family or expand the grid. All candidate configurations' outer actions
and summaries are recorded for transparency, regardless of inner selection.

## Bound, reporting and promotion screen

There are 15 outer fits. Each uses 39 historical Ridge fits, 24 new inner Ridge
fits, and six new outer Ridge fits: **1,035 Ridge fits maximum**. Four inner and
one outer PCA per fold give **75 PCA fits maximum**. Thresholds and correction
margins reuse predictions, with no extra fitting. The count is derived from the
fixed grid and checked by instrumented synthetic tests. Numerical libraries use
one CPU thread. Report elapsed fit/prediction time; this is not router latency.

Record fold configs and grouped pair counts; all candidate actions and utility,
accuracy, token/second costs, escalation counts, positive/nonpositive and harmful
escalations, and missed positive opportunities. For each new family and the
inner-selected new policy report individual directions and averaged per-question
deltas against confidence, a fixed-fit question-cluster 90% bootstrap interval
(2,000 draws; seed 20261002), and leave-one-question-out mean deltas. No bootstrap
refitting, multiplicity correction, or significance claim is made.

The exploratory promotion screen requires the selected policy's averaged utility
gain to be at least `.01`, both directional means to exceed zero, and every
leave-one-question-out averaged mean to exceed zero. Passing permits considering
a separately frozen fresh signal test; it does not restore any primary gate.
Stop after the fixed grid regardless of the result.
