# Manuscript revision response

Date: 10 October 2026. Working manuscript: v0.2.
Original manuscript: v0.1 at `1695a1f`; reviewed baseline at `79a6cdd`.
Claim map: R1, `cac52c1`.

This record tracks the [revision plan](revision-plan-2026-10-10.md).
It distinguishes completed writing changes from pending revision passes.
It is not a new study result or a statement of submission readiness.

## R1. Claim-to-source map — complete

The [map](revision-evidence-map.md) assigns IDs to the scientific claims,
reported values, methods, prior-work context, and sparse arithmetic deductions.
Source/section links resolve. A separate methods review found no blocking
number/comparator/qualifier mismatch. It corrected “asymmetric” transfer to
different directional point estimates, since no directional-difference test
was reported.

## R2. Central argument — complete

### New organizing claim

Observed rescues and limited post-hoc question-level structure coexist with
unsuccessful selection by the specified learners on held-out questions. The
paper describes that local finding under the recorded contract. It does not
identify a failure mechanism, establish useful acquisition, or claim priority
for repeated supervision or post-draft routing.

### Changed manuscript sections

| Location | Change | Evidence IDs and remaining limits |
|---|---|---|
| Abstract | Replaces the experiment catalogue with the three evidence levels and the negative primary comparison. Includes the interval and failed reproducibility boundary. | C00–C10. Scoped to tested recipes and conditional uncertainty. |
| Introduction | States the research question; distinguishes rescues, repeated known-question outcomes, and held-out-question selection. Replaces procedural contribution bullets with three measured findings. | C00–C06. No general principle or cause claimed. |
| Section 4.1 | Retains the original criterion table and result. Adds Box 1 with signed variance, both same-question transfer directions, and flagged-case point bounds. | C01–C06, N1. Primary failure is not reversed; one transfer interval crosses zero. |
| Section 4.1, diagnostic explanation | States draw assumptions, label-acquisition expenditure omitted from transfer, and fixed-action limits of the scorer bounds. Labels full8 behavior as secondary. | C04–C06. No net acquisition gain, unseen-question transfer claim, or universal scorer validation. |
| Section 6.1 | Aligns the discussion with the three evidence levels. Retains small training-group count as a possible constraint. | C00, C03–C10, M02. Does not identify sample size or representation as the cause. |
| Conclusion | Answers the scoped question and separates the later follow-ups from a common-mechanism claim. | C00–C18. Different targets remain different evidence. |
| Appendix B | Adds direct pointers for Box 1 and the revision map. | Existing tracked records; no raw outcome access. |

The title retains GSM8K and small Qwen3 models. The draft label identifies v0.2
as a working draft with R3–R6 pending. Original outcome tables, criteria,
cost preference, scorer identities, and experiment records remain unchanged.

### Targeted review and document checks

Separate GPT-6.1-sol/xhigh methods and argument reviews passed R2 without a
blocking correction. They checked the revised sections against the claim map
and tracked repeat records. These are editorial reviews, not new empirical
confirmation or the final R6 assessment.

Document comparison confirms that Tables 1–5 and Table A1 have unchanged rows.
The new Box 1 transcribes existing post-hoc records. Local file/section links
resolve, and whitespace checks pass. No implementation tests were run.

## R3. Interpretation repairs — complete

R3 adds explanations from the completed claim map and critical review. It
preserves all numerical outcome rows, intervals, thresholds, and decisions.

| Location | Interpretation change | Evidence boundary |
|---|---|---|
| Sections 3.1 and 6.4 | Separates output-token utility at λ=.05 from router work, acquisition, and full collection-ledger charges. | M01, A01; no deployment latency, energy, or cross-size compute claim. |
| Sections 3.4–3.5 | Explains shared questions across halves, changing draft states, and overlapping outer-training folds. Lists omitted training/refit/optimization/research variation and lack of joint coverage. | M02, M10; recorded conditional intervals remain unchanged. |
| Table 1–3 and Box 1 captions | Identifies data reuse, source-specific comparators, interval conditioning, and secondary full8 separation. | C01–C11, N1–N2; no independent-replication or primary-gate reversal claim. |
| Sections 4.2–4.3 | Compares objective decision utility without treating scores as calibrated probabilities. States that the CLM test excludes confidence and does not test feature addition to confidence. | C08–C11; head/fusion/quantization limits remain. |
| Section 5.1 and Table 4 caption | Defines opportunity counts as positive realized gain in at least one of two draws; explains draw dependence and threshold-refit uncertainty. | C12, N3; no expected-gain count, size law, or comparable cross-size compute unit. |
| Section 5.2 | Names the all-128-state cutoff refit and distinguishes it from the original cross-fitted control. | C14–C15; two changed training states versus the earlier three. |
| Section 5.3 | Places 227 zeros/one negative contribution beside the sparse interval. Explains why empirical resampling cannot produce unseen rescues. Adds the retrospective observed-mask ceiling ≤1/228<.01. | C16–C17, D01–D02; no population bound, power estimate, absolute policy metric, or changed endpoint. |
| Table 5 caption and Limitations | Clarifies selected-cohort/equal-question cap weighting and conditional inference; carries the sparse and CLM limits into the summary. | C18, N4; no cohort-selection coverage or general cap result. |

The sparse inequality is a written deduction from the existing contract and
count. R3 does not calculate a new effect, confidence interval, or power value.
The change leaves all original study criteria and outcomes intact.

### Targeted review and document checks

A GPT-6.1-sol/xhigh methods review passed R3 without a blocking correction.
It checked the uncertainty wording, sparse bound and bootstrap interpretation,
policy refit, comparators, costs, CLM scope, and captions against the evidence map.
This is an editorial check, separate from the final R6 assessment.

Tables 1–5, Table A1, and Box 1 retain all their prior rows. Captions and prose
changed. Local file/section links and whitespace checks pass. No implementation
tests, raw-data analysis, or interval calculations were run.

## Response to the critical-review concerns

Concern numbers refer to Section 4 of the
[critical review](critical-review-2026-10-10.md). “Addressed in R2/R3” means a
text change was made; the final scientific assessment remains R6.

| Concern | Response so far | Manuscript location | Status / next pass |
|---|---|---|---|
| 1. Procedures replace a clear contribution | Replaced the contribution list with scoped findings and a common research question. | Abstract; Introduction; Conclusion | Addressed in R2; contribution sufficiency assessed again in R6. |
| 2. Small, repeatedly reused evidence | Makes reuse explicit in the argument, Methods, and table captions; conditions learned-policy inference on the recorded fits. | Introduction; Sections 3.3–3.5; Tables 1–3 | Addressed in R2/R3; the small-data research limit remains. |
| 3. Added value of response halves | Explains shared question groups, changing drafts, and the distinction from a fixed-state or independent-study replication. | Introduction; Section 3.4; Box 1 | Addressed in R2/R3; no design-advantage test claimed. |
| 4. Fixed-fit uncertainty | Adds omitted training/refit/optimization variability, overlapping-fold dependence, and lack of joint coverage beside the method and captions. | Section 3.5; captions; Limitations | Addressed in R3; full-training uncertainty remains unmeasured. |
| 5. Sparse follow-up and refit | Distinguishes the refitted rule, explains bootstrap support, and derives the observed-mask ceiling without changing the screen. | Sections 5.2–5.3; Limitations | Addressed in R3; population benefit and absolute policy metrics remain unresolved. |
| 6. Underused repeat diagnostics | Adds the existing signed variance, both transfer directions, and flagged-case point bounds beside the failed primary tests. | Box 1 and following paragraphs | Addressed in R2; no new calculation. |
| 7. Restricted controls | Retains recipe limits and makes CLM's omitted confidence/feature-addition contrast explicit. | Sections 4.2–4.3; Limitations | R3 interpretation addressed; R4 prior-work comparison remains. |
| 8. Utility versus complete cost | Separates policy tokens, omitted acquisition charges, encoder observations, and ledger costs; retains cross-size compute limit. | Sections 3.1, 4.1, 4.3, 5.1, 6.4; Appendix A | Addressed in R2/R3; full deployment cost remains unmeasured. |
| 9. Cap and follow-up narrative | States that supporting studies answer separate questions and do not replicate the central learner comparison. | Introduction; Conclusion | R4 must shorten/reorganize follow-up detail and appendices. |

The full DART comparison and dated retrieval addendum remain R4 work. No new
literature claim was introduced during R2–R3. Figure specification/export remains
R5. Final methods and contribution assessment remains R6.

## Execution boundary

R2–R3 use the completed claim map and tracked result records. No raw response,
score cache, training reference, sealed outcome, model asset, generation,
fitting, scoring, statistical reanalysis, figure export, or implementation test
is used. Documentary checks compare wording, links, and retained tables.
Author identity and submission details remain deferred.
