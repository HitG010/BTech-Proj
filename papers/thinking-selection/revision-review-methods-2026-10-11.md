# R6 final methods review

Date: 11 October 2026. Reviewed baseline: `0689433` on
`codex/confidence-acquisition-plan`; the worktree was clean at the start.
Reviewed manuscript: v0.2 with R1–R5 complete and R6 pending.

## Recommendation

**The scoped empirical draft is scientifically coherent on methods grounds.**
The revision addresses the earlier reporting and inference concerns. I found no
substantive number, endpoint, comparator, selection, cost or caption blocker.
No further experiment is needed to report the completed studies honestly.

This assessment supports author review of a scoped empirical report. It does
not establish a confirmed learning algorithm, a failure mechanism, population
inferiority, publication novelty or submission readiness. The contribution
review and root assessment must decide whether the local empirical insight is
sufficiently useful beyond the closest prior work.

## Review scope

I read the current manuscript, captions, revision response, evidence map,
revision-plan acceptance criteria, the original critical review and methods
memo, and the completed figure review. The earlier documentary checks of
tracked protocols/results and the R5 artifact review were reused. I inspected
the full main narrative and appendices, rather than only the revision diff.

No raw outcome, score cache, training reference, sealed role, model asset,
study executor, test suite or new statistical calculation was accessed or run.
No figure was rerendered. Only this new specialist memo was written; the
manuscript and root review are unchanged.

## Response to the nine original concerns

Concern numbers refer to the [critical review](critical-review-2026-10-10.md#4-ranked-weaknesses-and-required-changes).
“Addressed” means the manuscript now makes a defensible claim; it does not mean
the underlying evidence limitation has disappeared.

| Concern | Location and action | Evidence source | Final status and remaining limit |
|---|---|---|---|
| 1. Procedural contribution list | Abstract, Introduction and Conclusion now state the same local finding: rescues and limited repeated-question structure coexist with failed selection by specified learners. | [Repeat results](../../docs/phase-2-repeat-results.md); map C00–C06. | Addressed. The argument is coherent; its novelty and external value remain modest judgments, not established facts. |
| 2. Small, repeatedly reused panel | Introduction, Sections 3.3–3.5, Table 1 and Figures 1–2 explicitly retain 50 question groups, 40 unique outer-training questions and later development reuse. | [Repeat protocol](../../docs/phase-2-repeat-panel.md); [feasibility results](../../docs/phase-2-router-feasibility-results.md). | Addressed. The failure is recipe-specific. No universal data requirement or claim of unlearnability appears. |
| 3. Added inference from response halves | Section 3.4 distinguishes outer question separation, draw-realization checks, same-question diagnostics and changing direct drafts. | [Repeat protocol](../../docs/phase-2-repeat-panel.md); [repeat diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation). | Addressed. No anti-leakage novelty, causal benefit of splitting, independent study replication or fixed-draft noise result is claimed. |
| 4. Fixed-fit uncertainty | Section 3.5 and captions explain fixed actions/fits, overlapping training folds, omitted retraining/threshold/optimization/research variation and lack of simultaneous coverage. | Repeat/control protocols; map M02/M10. | Addressed in interpretation. Full-learning-process uncertainty remains unmeasured; negative conditional intervals are not promoted to algorithm-level inferiority. |
| 5. Fresh guard sparsity and refit | Sections 5.2–5.3 distinguish the full-128-state cutoff from old cross-fitted actions, state 227 zeros/one negative contribution, and explain empirical bootstrap support plus the observed-mask ceiling. | [Sparse preparation](../../docs/sparse-validation-preparation-results.md); [sparse results](../../docs/sparse-validation-results.md); map C15–C17/D01–D02. | Addressed. The endpoint identifies the realized fixed-policy difference. Population benefit, rescue yield and absolute policy metrics remain unresolved. |
| 6. Underused existing diagnostics | Box 1 places signed variance, both same-question transfer directions and flagged-case point bounds beside the failed primary tests. Acquisition expenditure and draw assumptions are explicit. | [Repeat diagnosis and syntax sensitivity](../../docs/phase-2-repeat-results.md). | Addressed. One transfer interval crosses zero. The box does not reverse the original gate, establish feature learnability or supply net acquisition gain. |
| 7. Restricted controls | Sections 4.2–4.3, Limitations and Appendix A.3 retain fusion/compression/truncation/single-seed limits; CLM excludes confidence and does not test feature addition to confidence. | [MiniLM protocol](../../docs/phase-2-contrastive-protocol.md); [CLM protocol](../../docs/phase-2-clm-probe-protocol.md). | Addressed. Matched encoder identity does not isolate contrastive pretraining. Full-precision fidelity and faithful external-system comparison remain absent. |
| 8. Utility and complete cost | Sections 3.1/6.4, Tables 3–4, Figure 3 and Appendix A separate policy output tokens, acquired labels, encoder observations, collection charges and live compute. | [Reconciliation](../../docs/phase-1-protocol-reconciliation.md); [CLM results](../../docs/phase-2-clm-probe-results.md); [two-solver results](../../docs/opportunity-panel-results.md). | Addressed. λ=.05 remains the frozen operating preference. No equal cross-size compute, deployment latency, energy or causal speed result is claimed. |
| 9. Supporting cap and follow-up narrative | Section 5 now assigns different targets to diagnostic, guard and cap studies. Full pilot/cap detail moves to Appendix C while failed results remain visible. | [Pilot results](../../docs/qwen06-router-pilot-results.md); [sparse results](../../docs/sparse-validation-results.md); [cap results](../../docs/qwen17-cap-bridge-results.md). | Addressed. No common causal chain or replication of the main learner is inferred. Cap conclusions remain limited to 11 metadata-selected groups. |

## Additional methods points

The [earlier methods memo](reviewer-methods-2026-10-10.md) raised several points
that do not fit exactly into the nine concern labels. They are covered as follows.

- **Gates are related decisions.** Section 3.5 says the gates reuse outcomes;
  four failures are not four independent demonstrations of a mechanism.
- **Opportunity counts depend on draws.** Section 5.1 and Figure 3 label the
  4/64 and 24/64 counts as positive realized gain in either of two draws. They
  are not expected-positive labels or directly comparable to eight-draw counts.
- **Scoring remains a substantive limit.** Section 3.2 and Limitations retain
  scorer-defined correctness and the waived human audit. Syntax acceptance is
  not mathematical validation; flagged-case bounds do not cover all errors.
- **Cap selection and weighting are correct.** Section 5.4 and Table C1 use
  forced-closure metadata, not correctness, with equal question weights and
  thinking-call costs. The 18-cell summary remains secondary.
- **Comparator fairness has a narrow target.** The original comparator is
  training-selected accept/escalate/confidence; later controls use confidence.
  Four-draw and secondary full8 confidence endpoints remain distinct. Nothing
  implies that an untested feature-fusion or external method has been defeated.
- **Sparse missing outcomes are handled correctly.** Parser rejection fixes
  changed-state direct correctness at zero under v7; shared actions cancel.
  Missing common outcomes prevent absolute metrics but do not invalidate the
  realized policy contrast.

The finite-mask inequality is valid elementary arithmetic:
`ΔU_i ≤ z_i` and, for the recorded single activation, mean gain
`≤1/228<.01`. The text holds the observed mask fixed and supplies no population
or prospective power claim. The empirical bootstrap explanation also correctly
distinguishes its observed support from rare unseen rescues.

## Numbers, figures and acceptance conditions

The current numerical rows and narrative values resolve to the
[revision evidence map](revision-evidence-map.md). The six-decimal primary
repeat interval uses the tracked repeat protocol's terminal record; rounded
directional values remain rounded. Cap accuracy differences/intervals are
labeled in percentage points, and rounded column means are not used to
reconstruct token differences. I found no new numerical contradiction in the
main text or appendices.

Figures 1–3 keep the approved evidence units and exact frozen captions. Figure 1
shows 50-question reuse, the separate 64-question panel, its 11-question cap
subset and the fresh 128-state-refitted guard. Figure 2 separates the original
selected simple comparator from later confidence contrasts. Figure 3 charges
both calls on escalation and avoids an invented frontier or uncertainty bars.
The prior [R5 artifact review](figures/review.md) closes PNG/PDF/SVG inspection;
this R6 review makes no new render or output mutation.

The methods-related acceptance conditions in
[revision plan Section 8](revision-plan-2026-10-10.md#8-final-review-and-acceptance-conditions)
are satisfied: aligned scoped claim, mapped values, primary failures adjacent
to post-hoc diagnostics, properly limited sparse arithmetic/intervals, and
figures preserving comparators/weights/uncertainty. No unsupported first,
causal, cross-task, mathematical-correctness or deployment claim was found.

Prior documentary reviews checked local links and preserved original table
rows. The full experiment/artifact identities are source provenance, not new
verification of historical files during R6. The method review does not replace
root's document-preservation checks or the contribution specialist's assessment.

## Residual limits and the next scientific decision

No substantive methods correction is required to complete this scoped report.
The remaining weaknesses require new evidence if the authors retain a broader
claim: new training realizations with appropriate uncertainty, prospective
question/task/family replication, stronger scorer validation, complete live
cost measurement, or a faithful external comparator for a superiority claim.
They cannot be repaired by more careful prose alone.

Those gaps do not justify reopening the closed searches or collecting data
merely to obtain a favorable result. If the authors later choose one broader
question, specify the precise estimand, rule, population, precision and resource
contract before a separate prospective study. A fixed trained policy on a fresh
test set and a learning algorithm across training replicates require different
inference plans. The present report confirms neither.

My final methods status is **scoped empirical draft is coherent**. Proceed to
author and contribution review under that scope; retain the existing failures
and limits. Do not interpret this sign-off as novelty, confirmation or a
recommendation to deploy or scale a failed policy.
