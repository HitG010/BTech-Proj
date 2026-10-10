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

## Response to the critical-review concerns

Concern numbers refer to Section 4 of the
[critical review](critical-review-2026-10-10.md). “Addressed in R2” means a text
change was made; the final scientific assessment remains R6.

| Concern | Response so far | Manuscript location | Status / next pass |
|---|---|---|---|
| 1. Procedures replace a clear contribution | Replaced the contribution list with scoped findings and a common research question. | Abstract; Introduction; Conclusion | Addressed in R2; contribution sufficiency assessed again in R6. |
| 2. Small, repeatedly reused evidence | Makes the 50-question reuse and limited learner inference explicit in the central argument. | Introduction; Sections 4.1 and 6.1 | Partly addressed; R3 checks all comparisons/captions. |
| 3. Added value of response halves | Explains reuse of question groups and changing draft states. Does not treat directions as independent studies. | Introduction; Box 1 | Partly addressed; R3 completes Methods wording. |
| 4. Fixed-fit uncertainty | Retains conditional intervals and avoids an algorithm-wide superiority/inferiority conclusion. | Abstract; Box 1 | R3 still needs the full adjacent interval/dependence explanation. |
| 5. Sparse follow-up and refit | Introduction names the refit and the single fresh changed action. | Introduction; current Section 5.3 | R3 must add bootstrap-support and finite-panel-ceiling explanations; not complete. |
| 6. Underused repeat diagnostics | Adds the existing signed variance, both transfer directions, and flagged-case point bounds beside the failed primary tests. | Box 1 and following paragraphs | Addressed in R2; no new calculation. |
| 7. Restricted controls | Central claim refers to specified recipes and recorded training conditions. | Abstract; Introduction; Section 6.1 | R3 must make the CLM feature-addition boundary explicit; R4 retains appropriate related work. |
| 8. Utility versus complete cost | Adds the omitted label-acquisition token counts to the transfer interpretation. | Section 4.1 | Partly addressed; R3 checks all utility/runtime/cost distinctions. |
| 9. Cap and follow-up narrative | States that supporting studies answer separate questions and do not replicate the central learner comparison. | Introduction; Conclusion | R4 must shorten/reorganize follow-up detail and appendices. |

The full DART comparison and dated retrieval addendum remain R4 work. No new
literature claim was introduced during R2. Figure specification/export remains
R5. Final methods and contribution assessment remains R6.

## Execution boundary

R2 uses the completed claim map and tracked result records. No raw response,
score cache, training reference, sealed outcome, model asset, generation,
fitting, scoring, statistical reanalysis, figure export, or implementation test
is used. Documentary checks compare wording, links, and retained tables.
Author identity and submission details remain deferred.
