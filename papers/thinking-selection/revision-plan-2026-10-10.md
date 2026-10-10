# Plan: revise the paper using existing evidence

Date: 10 October 2026. Status: **R1–R2 complete; R3–R6 pending**.
Base: manuscript v0.1 at `1695a1f`; critical review at `79a6cdd`.
Branch: `codex/confidence-acquisition-plan`.

## 1. Objective

Produce manuscript v0.2 with one clear empirical claim, a traceable evidence
table, and an answer to each major reviewer concern. Revise the presentation
and interpretation of the evidence. Preserve the original study results.

Use short technical sentences. Define technical terms when first used.
Retain equations and exact statistical qualifications where needed.
Do not claim certified ASD-STE100 compliance.

Author details, venue selection, submission formatting, and public release
remain deferred. This is a writing and report-export plan. New experiments are
outside this revision.

## 2. Main research question and candidate claim

**Question:** In the studied GSM8K/Qwen3 setting, what do observed thinking
rescues and repeated question-level outcomes tell us about the performance of
the specified learned selectors on held-out questions?

**Candidate claim:**

> On the 50-question Qwen3-1.7B panel, observed rescues and limited post-hoc
> evidence of repeated question-level structure coexist with failure of the
> specified learners to improve held-out-question utility over their simple
> comparators. Bounded capacity and representation checks do not resolve that
> failure. Separate diagnostic and follow-up studies limit how far these
> observations can be transferred to other solver settings and policy rules.

This is a local empirical finding. It does not identify the cause of failure.
It does not establish a new algorithm, a general impossibility result, or
priority for repeated supervision or post-draft routing.

Keep GSM8K and Qwen3 visible in the title, abstract, and conclusion. Do not
choose a broader title to compensate for limited evidence.

## 3. Execution order

Complete R1–R4 before figure export. R5 uses a frozen display specification.
R6 reviews the resulting paper. Each pass produces a concrete deliverable.

| Pass | Work | Deliverable | Completion check |
|---|---|---|---|
| R1. Fix the claim — complete | Build a claim-to-source table from the records below. Mark primary, post-hoc, exploratory, and fresh evidence. | [Revision evidence map](revision-evidence-map.md) | Source links and central number/comparator/qualifier checks passed; no experiment reproduction. |
| R2. Rebuild the central argument — complete | Rewrite the abstract, Introduction, repeat Results, and Conclusion. Add the repeat-diagnosis box. | [v0.2 working manuscript](manuscript.md), [revision response](revision-response.md) | Targeted methods/argument reviews passed; failed primary gates retained; original outcome/accounting table rows unchanged. |
| R3. Repair interpretation | Clarify halves, bootstrap scope, sparse policy refit, event support, opportunity counts, and control limits. | Updated Methods, captions, and follow-up sections | All interpretation requirements in Section 5 are met beside the relevant result. |
| R4. Tighten scope and prior work | Update the DART comparison. Shorten cap/parser history. Move operational detail to appendices. | Coherent main paper plus appendices | Main text has one argument. No unsupported first, causal, population, or deployment claim remains. |
| R5. Prepare displays | Freeze source/transcription/render specifications, then create three figures from reported values. | `figure-export-plan.md`, display inputs, SVG/PDF/PNG files | Inputs and output paths are fixed before export; no effect or interval is re-estimated; captions preserve endpoints. |
| R6. Review and close | Check methods and contribution separately. Record a response to each reviewer concern. | `revision-response.md`, `revision-review.md`, final v0.2 | Each concern is addressed or explicitly remains unresolved. Final scientific decision is recorded. |

Root coordinates the work and edits the manuscript. If delegated, the methods
reviewer checks inference and numbers; the contribution reviewer checks the
claim against the already reviewed primary papers. They do not independently
edit the same manuscript at the same time.

## 4. Evidence to add or retain

Use the following records as the initial R1 source list. Copy reported values
at their existing precision. Do not reconstruct missing values from raw data.

| Evidence | Placement in v0.2 | Interpretation to retain |
|---|---|---|
| Original four-draw learner difference −.016204, conditional 90% interval [−.033276, −.000635]; four of five criteria fail | Main repeat result, before post-hoc diagnostics | Original comparator is selected within training from accept, escalate, and confidence. |
| Primary reproducibility MSE improvement +.01158, interval [−.01744, +.04848] | Beside the original gate table | The primary reproducibility criterion failed. |
| Signed between-question gain variance .03233 utility², post-hoc interval [.00541, .06530] | New post-hoc diagnostic box | Approximate IID/exchangeable within-question draws; conditional on recorded labels. A different statistic from the primary MSE test. |
| Same-question A→B gain +.04413 [.00563, .08845]; B→A +.01572 [−.02019, .05908] | Same diagnostic box | One interval crosses zero. Selection uses labels from those same questions. Acquisition cost is omitted. No unseen-question or net acquisition claim. |
| Five flagged presentation cases leave primary fixed-policy difference −.016204 unchanged; the sixth cannot improve it | Short robustness paragraph | Fixed actions and costs only. This does not cover unflagged errors or refitted policies. |
| Bounded CPU, compact neural, and released-CLM comparisons | Main control table, marked exploratory | Reuse the same 50 questions. Later comparator is confidence. These are tests of specified recipes. |
| Shared 64-question, two-solver diagnostic | Supporting result | Positive-gain counts mean at least one positive realized draw out of two. They are not counts of positive expected gain. |
| Cross-fitted parser control, all-128-state refit, and fresh 228-question contrast | One compact follow-up subsection | Three changed development actions, two changed refit training actions, and one changed fresh action refer to different policy/evaluation conditions. |
| Matched 2k/4k cap contrast on 11 selected question groups | Short main summary; full table in appendix | Cohort selected by forced-closure metadata. Equal-question means differ from raw cell means. No general cap effect is established. |

Sources:

- [Repeat results and post-hoc diagnosis](../../docs/phase-2-repeat-results.md).
- [Bounded controls](../../docs/phase-2-router-feasibility-results.md) and
  [released-CLM results](../../docs/phase-2-clm-probe-results.md).
- [Two-solver diagnostic](../../docs/opportunity-panel-results.md).
- [0.6B pilot](../../docs/qwen06-router-pilot-results.md),
  [sparse preparation](../../docs/sparse-validation-preparation-results.md), and
  [sparse results](../../docs/sparse-validation-results.md).
- [Cap results](../../docs/qwen17-cap-bridge-results.md).
- [Existing evidence ledger](evidence-ledger.md).

The separate synthetic G1 result remains outside the real-solver comparisons.

## 5. Required interpretation changes

### Repeated draws and fitting

- Explain that question folds exclude evaluation questions from fitting.
- Explain that opposite halves check different response realizations. Both
  directions reuse the same question groups; they are not independent study
  replications.
- Keep same-question reproducibility separate from prediction on held-out
  questions. Changing direct drafts means this is not a fixed-draft noise study.
- Retain k=1/2/4 results without inferring a general learning curve or a causal
  benefit or harm from additional supervision.
- State that recorded intervals keep fits/actions fixed. They omit retraining,
  threshold-selection and optimization variability, research reuse, and joint
  coverage across comparisons. Do not recompute intervals in this revision.

### Fresh sparse contrast

- Identify the frozen all-128-state threshold as a refit. Do not call it an
  exact replication of the cross-fitted development control.
- Retain the formula for the policy difference and explain why unchanged
  actions contribute zero. Absolute policy accuracy remains unidentified.
- State the observed counts next to the interval: 227 zero contributions and
  one negative contribution. An empirical bootstrap cannot create unseen rescue
  events; its upper endpoint zero is not a population no-benefit bound.
- Add the review's elementary finite-panel bound:
  `ΔU_i ≤ z_i`, hence mean gain is at most `1/228` with the observed mask fixed,
  before thinking costs. This is below .01 even if the single call rescues.
  Label it a retrospective arithmetic observation. Keep the failed screen.
- Do not extrapolate the observed activation rate to future questions or change
  the sample size, cutoff, scoring rule, or original endpoint.

### Controls and costs

- State that CLM excludes confidence and auxiliary draft statistics. Its test
  does not answer whether CLM adds value when combined with confidence.
- Retain MiniLM compression/truncation, single-seed, and fusion limits; retain
  CLM quantization and unmatched head-training/capacity limits.
- Distinguish utility at λ=.05, generated/inserted output tokens, router work,
  and collection-ledger charges. Cross-size tokens are not equal compute.
- Keep original and later baselines separate. Never substitute the full8
  confidence endpoint for the averaged four-draw endpoint.

### Prior work and scope

Use the [contribution review](reviewer-contribution-2026-10-10.md) for the
updated full-text comparison with DART v4, Chen, Garg and Sagtani, and Yang et
al. DART already uses observed drafts and fresh thinking. Explain our one-draft,
fixed-budget, repeated-outcome setting without calling post-draft routing new.
Update the earlier abstract-only retrieval note with a dated addendum.

Keep the contribution as a measured, scoped separation between evidence levels.
Do not claim that juxtaposing known concerns establishes a new general principle.
A faithful external method comparison remains absent. This revision does not
implement one. Optional new literature is unnecessary unless a new claim needs
it; any such claim must receive a primary-source check.

## 6. Proposed manuscript structure

1. **Abstract and Introduction:** question, scoped finding, and why it matters.
2. **Related work:** closest empirical overlap, then method context.
3. **Decision and evidence design:** utility, scoring, question roles, folds,
   halves, and interval scope.
4. **Main repeat result:** observed rescues; failed primary tests; separately
   labeled post-hoc structure; bounded learned controls; flagged-case bounds.
5. **Limits of transfer:** two-solver diagnostic; refitted sparse guard;
   concise cap result. Each has a separate question and endpoint.
6. **Discussion and limitations:** unresolved explanations, limited breadth,
   and evidence needed for a broader claim.
7. **Conclusion:** answer the scoped question with no population impossibility
   or deployment recommendation.
8. **Appendices:** full original criteria, secondary conditions, cap table,
   operational accounting, parser details, identities, and deviations.

Moving content must not hide unfavorable results. The main text must still
report the direction and scope of each follow-up, with a link to its full table.

## 7. Figure preparation contract

R5 is an additive export, after the text and claim map settle. Freeze its
separate plan and source/display-input hashes before running the renderer.
Use standard plotting tools for scientific plots. Use only transcribed values
from the listed tracked reports and the existing manuscript tables.

| Figure | Content | Required caption |
|---|---|---|
| 1. Study and evidence map | The 50-question repeated/control block, separate 64-question diagnostic, its 11-question cap subset, and fresh 228-question sparse block. Show where same-question diagnostics fit. | Arrows show design influence. The control fits reuse data; the cap cohort overlaps the 64; fresh guard evaluation concerns a refitted rule. |
| 2. Recorded utility contrasts | Separate panels for the original four-draw learner versus its training-selected baseline, and later selected controls versus confidence. Include zero and original intervals. | Same 50 questions; conditional 90% intervals; different comparators; no pooled effect or common causal interpretation. |
| 3. Two-solver diagnostic | Direct, always-escalate, and confidence accuracy/token points for each solver. Label 24/64 and 4/64 positive-realized-gain question counts separately. | Two draws per mode; shared questions; counts are draw-dependent; output tokens are not equal compute across sizes. |

Keep sparse and cap results in tables. Do not connect the development and fresh
guard utility estimates as if they were the same fitted policy.

Display inputs must retain source path, table/section, units, rounding,
comparator, and interval convention. Missing precision stays missing. A source
disagreement triggers a documented unresolved item; it does not trigger raw
data access. No rescoring, rebootstrap, new fit, subgroup search, new λ curve,
or executor rerun is part of export. Verify every displayed value against its
source and inspect each rendered figure for clipping, labels, and legibility.

## 8. Final review and acceptance conditions

R6 produces one response table with: concern, manuscript location, action,
evidence source, and remaining limit. It covers all nine root-review weaknesses
and the additional points in the two specialist memos.

The revision is complete when:

- The abstract, Introduction, and Conclusion state the same scoped claim.
- Every number and interval resolves to the evidence map.
- Primary failures and post-hoc diagnostics are visible together.
- The sparse interval and finite-panel bound have the required limits.
- Figures preserve question counts, comparators, weights, and uncertainty.
- No new first, causal, cross-task, mathematical-correctness, or deployment
  claim appears without supporting evidence.
- Local links and document formatting are checked; frozen experiment files
  remain unchanged. No implementation tests or study commands are needed.
- Methods and contribution reviews each give a clear final assessment.

Choose one final scientific status:

1. **Scoped empirical draft is coherent:** proceed to author review when those
   details are resumed. This does not predict acceptance.
2. **Contribution remains too incremental:** retain an honest empirical report
   and record the exact unanswered question. Any new evidence requires a
   separate prospective design and resource/precision review.

Do not keep adding analyses until a favorable result appears. The revision
can succeed as a clear report even if its novelty remains limited.

## 9. Preservation and current status

Git retains v0.1 at `1695a1f` and the review at `79a6cdd`. Future execution will
update `manuscript.md` to v0.2 and record changes in `revision-response.md`.
There is no need for a new branch for this documentation-only revision.

This plan reads tracked documents only. It opens no raw outcomes, score caches,
training references, sealed roles, or model assets. It allocates no questions
and runs no generation, fitting, scoring, statistical reanalysis, figure export,
or tests. Existing experiment protocols and outputs remain fixed. The waived
human scoring audit stays waived. Closed G1 and reused-panel searches stay closed.

**Progress, 10 October 2026:** R1–R2 are complete. The
[claim-to-source map](revision-evidence-map.md) defines 19 research/synthesis
claims, ten method records, seven literature-context records, four numerical
registers, and the sparse arithmetic deductions. R2 rewrites the central
argument in v0.2, adds the recorded post-hoc diagnostic box, and aligns the
discussion and conclusion. The [revision response](revision-response.md)
records changes and the remaining concerns. Separate methods/argument reviews
passed; original outcome/accounting table rows are unchanged.

**Next executable task:** R3, interpretation repairs in Methods, captions, and
the follow-up sections. R3–R6 have not started. The completed writing passes do
not establish publication novelty or submission readiness.
