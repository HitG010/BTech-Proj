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

## R4. Scope, prior work, and supporting detail — complete

Completed 11 October 2026; primary-source recheck began 10 October.

| Location | Change | Evidence boundary |
|---|---|---|
| Section 2.1 | Leads with DART, Chen, Garg and Sagtani, and Yang et al.; gives the concrete design overlap and the local distinction. | L02–L05; no post-draft/repeated-supervision priority, new general principle, or faithful external-system comparison. |
| Section 2.2 | Keeps router/representation context after the closest empirical work. | L01, L06–L07; existing citations and CLM release status retained. |
| Literature notes, BibTeX, and claim map | Adds a dated full-text retrieval correction and updates DART's source note. | DART v4 checked directly; older abstract-only record retained as history. No external numerical results reproduced. |
| Section 4.2 and Appendix A.3 | Moves architecture, optimization, and fit counts to the appendix; keeps objectives, results, and recipe limits in the main text. | C07–C10, M05–M07; compact heads remain distinct from CPU Ridge controls. |
| Section 4.3 and Appendix A.3 | Moves separate CLM timing detail beside implementation settings. | C11; encoder identity named, output-token utility still excludes this work, no live deployment timing claim. |
| Sections 5.2–5.3 and Appendix C.1 | Shortens development pilot history; keeps failed criteria, favorable sparse control, refit, and fresh-result interpretation visible. | C14–C17, D01–D02; Section 5.3 unchanged, no broader sparse-event inference. |
| Section 5.4 and Appendix C.2 | Keeps one rescue, added cost, lower point utility, interval, and cohort limit in the main text; moves the full cap table to Table C1. | C18, N4; original Table 5 rows/caption retained under the new label. |

### Review and preservation

The source check used the four cited primary full texts and the earlier
contribution review. The targeted methods check identified two relocation
ambiguities: the shared head applies to the compact objectives, and the timing
paragraph concerns CLM. Both are corrected. Separate GPT-6.1-sol/xhigh methods
and literature/contribution reviews pass R4. Their sign-off is limited to this
revision; R6 remains the final scientific assessment.

Document comparison preserves all outcome/accounting table rows and Box 1.
Table 5 is now Table C1; only its label and the Appendix B location pointer
change. The full sparse interpretation in Section 5.3 remains unchanged.
Local links, section anchors, and whitespace are checked before the checkpoint.
This pass does not decide publication novelty or replace the final R6 review.

## R5. Frozen report-to-figure export — complete

The [display plan](figure-export-plan.md), inputs, and renderers froze at
`655094d` before export, using source documents from `d1287e6`. The independent
methods review passed the freeze. The single completed export creates three
figures, each in PDF, SVG, and PNG. [Figure files and provenance](figures/README.md)
include exact input precision, source locations, comparator/interval metadata,
source/renderer/output hashes, and the final artifact review.

| Figure and location | What it shows | Limits retained |
|---|---|---|
| 1, after Table 1 | Study roles, repeated/control reuse, separate diagnostic, cap subset, fresh refitted guard. | Design influence does not mean independent replication; no pooled sample count. |
| 2, after Table 3 | Original learner contrast and three later training-selected families. | Separate comparators; same 50 groups; conditional 90% intervals; no new effect, refit uncertainty, or joint coverage. Other individual policies remain in Table 3. |
| 3, after Table 4 interpretation | All six two-solver accuracy/token points and 4/64 versus 24/64 opportunity counts. | Point estimates only; draw-dependent realized gain; escalation pays both calls; cross-size tokens are not equal compute. |

All original numerical table rows, Box 1, and sparse Section 5.3 are unchanged.
The figure captions are exact copies of the frozen input text. Root visual
review inspected all PNGs and all PDF pages rendered independently through
native PDFKit/Quartz. SVG text and all nine output hashes pass artifact checks.
No correction or second export was required. See the
[review record](figures/review.md) and [verification](figures/review-verification.json).

This is a display export. It uses no raw project outcome, score cache, reference,
sealed role, new fitting/scoring/generation, statistical reanalysis, or test run.
R6 remains the final scientific assessment.

## Response to the critical-review concerns

Concern numbers refer to Section 4 of the
[critical review](critical-review-2026-10-10.md). “Addressed in R2–R4” means a
text change was made; the final scientific assessment remains R6.

| Concern | Response so far | Manuscript location | Status / next pass |
|---|---|---|---|
| 1. Procedures replace a clear contribution | Replaced the contribution list with scoped findings and a common research question. | Abstract; Introduction; Conclusion | Addressed in R2; contribution sufficiency assessed again in R6. |
| 2. Small, repeatedly reused evidence | Makes reuse explicit in the argument, Methods, and table captions; conditions learned-policy inference on the recorded fits. | Introduction; Sections 3.3–3.5; Tables 1–3 | Addressed in R2/R3; the small-data research limit remains. |
| 3. Added value of response halves | Explains shared question groups, changing drafts, and the distinction from a fixed-state or independent-study replication. | Introduction; Section 3.4; Box 1 | Addressed in R2/R3; no design-advantage test claimed. |
| 4. Fixed-fit uncertainty | Adds omitted training/refit/optimization variability, overlapping-fold dependence, and lack of joint coverage beside the method and captions. | Section 3.5; captions; Limitations | Addressed in R3; full-training uncertainty remains unmeasured. |
| 5. Sparse follow-up and refit | Distinguishes the refitted rule, explains bootstrap support, and derives the observed-mask ceiling without changing the screen. | Sections 5.2–5.3; Limitations | Addressed in R3; population benefit and absolute policy metrics remain unresolved. |
| 6. Underused repeat diagnostics | Adds the existing signed variance, both transfer directions, and flagged-case point bounds beside the failed primary tests. | Box 1 and following paragraphs | Addressed in R2; no new calculation. |
| 7. Restricted controls | Retains recipe limits and makes CLM's omitted confidence/feature-addition contrast explicit. | Sections 4.2–4.3; Limitations | Addressed in R3/R4; faithful external-method comparison remains absent. |
| 8. Utility versus complete cost | Separates policy tokens, omitted acquisition charges, encoder observations, and ledger costs; retains cross-size compute limit. | Sections 3.1, 4.1, 4.3, 5.1, 6.4; Appendix A | Addressed in R2/R3; full deployment cost remains unmeasured. |
| 9. Cap and follow-up narrative | Shortens supporting results and moves implementation/pilot/cap detail to appendices while retaining directions, failures, and limits in the main text. | Section 5; Appendices A.3/C | Addressed in R4; final coherence assessed in R6. |

The full DART comparison and dated retrieval addendum are complete in R4.
No external-method experiment was added. R5 figure specification/export is
complete. Final methods and contribution assessment remains R6.

## Execution boundary

R2–R4 use the completed claim map and tracked result records. R4 also checks
the cited primary literature. No raw project response,
score cache, training reference, sealed outcome, model asset, generation,
fitting, scoring, statistical reanalysis, figure export, or implementation test
is used in R2–R4. Documentary checks compare wording, links, and retained
tables. R5 separately runs the frozen report-only renderer and artifact QA;
its boundary is recorded above. It performs no scientific re-estimation.
Author identity and submission details remain deferred.
