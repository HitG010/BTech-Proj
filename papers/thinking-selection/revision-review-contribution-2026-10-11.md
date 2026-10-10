# R6 final contribution review — 11 October 2026

Reviewed baseline: `0689433` on `codex/confidence-acquisition-plan`; clean before
this memo. Review scope: manuscript v0.2, its three existing PNG figures and
captions, revision response, original critical and contribution reviews, dated
literature notes, and revision-plan acceptance conditions.

## Scientific decision

**Status 1: Scoped empirical draft is coherent.** The revised paper identifies
a useful local result and can proceed to human author review when the deferred
author details are resumed. I found no must-fix contribution or reporting issue
within that scope. This is not a judgment of submission readiness, substantial
general novelty, or likely acceptance.

The contribution remains incremental relative to the closest work. The revision
has made the empirical claim clearer and better supported; it has not increased
the number of independent questions, established a failure mechanism, or
demonstrated external-method superiority. Earlier R2–R5 checks are editorial
evidence, not a reason to upgrade that scientific assessment.

## What the reader can now learn

The paper no longer offers only a catalogue of unsuccessful recipes. It puts
three distinct observations together on one fixed panel:

1. Thinking sometimes rescues a scored incorrect draft: 30 rescues and 10 harms
   occur in the 400 recorded pairs.
2. Separate post-hoc diagnostics suggest question-level gain variation and give
   positive same-question transfer points. These are qualified by draw
   assumptions, one interval crossing zero, and omitted label-acquisition cost.
3. The predeclared learner and bounded later recipes do not establish a utility
   improvement on held-out questions over their specified simple comparators.

The useful finding is this coexistence, rather than a claim that one level
causes the next to fail. A reader can infer that the measured opportunities and
known-question diagnostics did not justify promoting these selectors under
this protocol. The observations do not establish that suitable feature-level
signal existed, that routing is unlearnable, or that more repeated labels are
generally ineffective.

Box 1 supplies a further narrow result: the flagged presentation candidates
alone cannot reverse the primary point comparison with actions and costs fixed.
That makes this particular failure record more informative. It does not
validate every mathematical score or exclude all scoring explanations.

The abstract, Introduction, Section 4.1, Discussion, and Conclusion consistently
state these limits. In particular, the positive post-hoc variance interval is
not used to reverse the failed primary reproducibility criterion.

## Contribution against the checked primary papers

The final related work represents the previously checked sources accurately.
No new claim required another web retrieval for this review.

| Work | Remaining overlap and distinction |
|---|---|
| [DART v4](https://arxiv.org/html/2606.23181v4), Sections 2.2–2.3, 4.2, E.1 | Observed-draft acceptance, fresh thinking, adaptive budgets, and supervised-router failures already appear there. The final text names its two drafts and single-run main evaluation, then states our one-draft, fixed-allowance, repeated-outcome contract. It explicitly says that a faithful DART comparison is absent. This is a design distinction, not priority or evidence against full DART. |
| [Chen v3](https://arxiv.org/html/2607.03436v3), Sections III–VII and Appendix C | Stochastic ceilings, hindsight distinctions, scorer/coupling sensitivity, and a held-out archived-policy illustration are established. Our local learned-selection result is not a new oracle theorem; repeated outcomes and held-out fitting are correctly acknowledged as prior ingredients. |
| [Garg and Sagtani v1](https://arxiv.org/html/2605.07395v1), Sections 3, 5, 8 | Scoring artifacts and router-collapse controls already exist. The final draft limits its flagged-case bounds and selected cap intervention instead of claiming a comparable mechanism decomposition. |
| [Yang et al. v1](https://arxiv.org/html/2608.14927v1), Sections 2–5 and Appendices A/B | Fixed-solver comparisons, post-answer failure probes, and the failure-risk/protocol-value distinction substantially overlap. The stochastic halves and same-question diagnostics are a narrower empirical extension; they have less task/family breadth. The general caution is corroborated, not newly discovered. |
| [RouterDC](https://arxiv.org/html/2409.19886v1) and the other method context | Repeated solver supervision and contrastive routing are not claimed as new. MiniLM's prior contrastive training and the released CLM's author-release status are retained. A failed quantized transfer recipe is not presented as a failure of contrastive learning. |

The conjunction supplies useful evidence about these small-model recipes. Its
broader message remains familiar. No verified literature comparison establishes
that this conjunction is first, and no such claim is needed for the scoped
status chosen here.

## Disposition of the original concerns

“Addressed” below means that the reporting problem is repaired. It does not
mean that the underlying evidence limitation has disappeared.

| Original concern | Final assessment and remaining limit |
|---|---|
| 1. Procedures substituted for a finding | Addressed. The three evidence levels now organize a measured local result. Novelty remains modest; provenance supports the finding rather than serving as its scientific content. |
| 2. Small, repeatedly reused evidence | Addressed in the text and study map; unresolved in the evidence. Fifty groups and many reused fits remain a limited learning comparison, not independent confirmations or a general data requirement. |
| 3. Unproven value of response halves | Addressed. The draft says the halves reuse questions, exchange roles, and change direct drafts. No design-advantage experiment, fixed-draft noise study, or causal repeated-label learning curve is claimed. |
| 4. Conditional uncertainty | Addressed. Recorded intervals omit refitting, optimization, research selection, joint coverage, and overlapping-training dependence. Algorithm performance across new training sets remains unmeasured. |
| 5. Sparse guard and policy refit | Addressed. The refitted rule is distinguished from the earlier cross-fitted control. One changed state, no rescue, empirical-bootstrap support, and the observed-mask ceiling are visible. Population benefit and absolute policy performance remain unidentified. |
| 6. Underused repeat diagnostics | Addressed. Box 1 reports both transfer directions, signed variance, and fixed-policy parser bounds beside the failed primary tests. Directional point differences are not called a tested asymmetry. |
| 7. Restricted controls and missing external comparison | Addressed as scope. Compression, truncation, fusion, one optimization seed, quantization, head differences, and omitted CLM/confidence fusion remain unresolved. The paper cannot describe the strongest available selectors or defeat an external system. |
| 8. Utility versus complete cost | Addressed. Frozen lambda, policy output tokens, acquisition charges, encoder work, and deployment costs are distinguished. No complete latency, energy, or cross-size compute recommendation follows. |
| 9. Cap and follow-up narrative | Addressed. Supporting studies have separate targets; main text retains failed criteria, sparse support, lower cap point utility, and cohort limits. Full details remain in appendices. They do not explain the central learner failure or replicate one mechanism. |

The specialist concerns about scorer robustness, causal explanations, and
limited independent support also remain explicit. Human mathematical scoring
was waived; automated preservation and syntax checks are not described as its
replacement. Deferred authorship and release details are outside this review's
scientific reporting decision.

## Figures and supporting evidence

I inspected the three existing PNGs, without rerendering or recalculating.
Figure 1 exposes panel reuse, the overlapping cap subset, and the refitted fresh
guard. Its arrows signify design influence, not causal identification or
independent replication. Figure 2 separates the original selected baseline
from later confidence comparisons and labels conditional uncertainty. It does
not imply pooled evidence. Figure 3 shows all six policy points, draw-dependent
realized-gain counts, and the cross-size compute limit.

The figures make the evidence easier to assess. They do not create new
precision, scientific independence, or novelty. The sparse and cap results are
still visible in the main text, and moving their full details does not hide
unfavorable findings.

## Exact unresolved scientific question

The current evidence leaves open whether one frozen feature-based selection
procedure can turn repeated question-level outcomes into utility gains over
confidence on new questions and new training realizations. It also leaves open
which mechanism, if any, explains the failed recipes. Neither the positive
post-hoc diagnostics nor this revision answers those questions.

A broader claim therefore remains too incremental and insufficiently supported
by the present evidence. Any attempt to answer that narrower unresolved
question needs a separately prospective design and resource/precision review.
This memo recommends no renewed fitting, larger reused-panel search, or new
collection. The coherent local report can be retained without claiming a
broader result.

## Review boundary

Only this new memo was written. No manuscript, root review, study source,
protocol, figure, or existing result was changed. No raw project outcome, score
cache, training reference, sealed allocation, model asset, test, experiment,
statistical estimate, renderer, or study executor was accessed or run. Literature
interpretations rely on the recorded primary-source checks; external results
were not independently reproduced. Root must reconcile this contribution
assessment with the separate final methods review.
