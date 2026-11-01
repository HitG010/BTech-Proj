# Empirical paper draft

## Read the paper

[Manuscript, version 0.6](manuscript.md)

**Token-level deferral added, 1 November 2026:** v0.6 adds Section 4.4 and three
Table 3 rows for an adapted token-level deferral check (all three rules fail), and
updates the abstract, introduction, related work, Table 1, Section 3.5, discussion,
limitations, conclusion and Appendices A and B, which had called the recipe untested.
Other tables, Box 1, figures and equations are unchanged. See the
[results record](../../docs/token-deferral-results.md).

**Confidence–gain audit added, 30 October 2026:** v0.5 adds Section 5.2 and
Table 5, a post-hoc descriptive check of whether lower confidence means higher
deferral gain (yes for Qwen3-0.6B, not in general for Qwen3-1.7B). Discussion,
limitations, conclusion, Appendix A seeds and Appendix B are updated; later
Section 5 subsections are renumbered 5.3–5.5. All earlier tables, Box 1, figures,
and equations are unchanged. See the [results record](../../docs/confidence-gain-shape-results.md).

**Cascade reframing, 29 October 2026:** v0.4 recasts the accept-or-think
decision as a same-model cascade, with a new title, abstract, introduction,
related work (cascades first), and discussion. Eight sources were added at
abstract level; their full texts could not be retrieved in this session.
All tables, Box 1, figures, and appendices are unchanged. The PDF/LaTeX copy
below still reflects v0.3. See the [reframing record](cascade-reframing-2026-10-29.md).

**Reviewer copy of v0.3, 28 October 2026:** [PDF](latex-v2/output/pdf/main.pdf),
[editable LaTeX](latex-v2/main.tex), and
[portable source ZIP](thinking-selection-review-source-v2.zip).
Four illustrative figures explain the decision, sample design, utility
comparisons, and policy costs. The independent critic's substantive findings
are addressed in the [legibility response](legibility-response-2026-10-28.md).
Humanizer is installed and was used for plain scientific prose. Scientific
results and limits are preserved. See [build instructions](latex-v2/README.md).

**Reviewer LaTeX copy, 27 October 2026:** [editable source](latex/main.tex),
[compiled PDF](latex/output/pdf/main.pdf), and
[portable source ZIP](thinking-selection-review-source.zip).
See [build and Overleaf instructions](latex/README.md). This is a single-column
review layout with line numbers. Scientific wording, values, and figure captions
retain v0.2; a source-record inventory is added for portability. Author details
and endorsement remain pending. No new experiment or literature search was run.

**Title (v0.4):** Learned Deferral Did Not Beat Confidence When Escalating to
Thinking: A Same-Model Cascade Study of Small Qwen3 Models on GSM8K. The v0.3
title was *Confidence and Learned Thinking Selection on GSM8K: A Controlled
Study of Small Qwen3 Models*.

The draft contains an abstract, introduction, related work, methods, results,
discussion, limitations, conclusion, references, and reproducibility appendices.
It includes four main tables, appendix accounting and cap tables, and a post-hoc
diagnostic box, plus four figures in PDF/SVG/PNG. R1–R6 are complete. The
scoped empirical report has an author-facing scientific assessment; human
author endorsement remains pending. It has not been submitted.

## Author scientific review, 12 October 2026

Read the [author scientific review](author-scientific-review-2026-10-12.md).
It recommends retaining v0.2 as a scoped empirical report and explains the
claim, scientific strengths, evidence gaps, and responses to likely objections.
No substantive manuscript correction was identified. Novelty remains modest.

The written assessment is complete. The next step is human author endorsement
of the scoped claim or a specific scientific correction. This AI-assisted
review does not record endorsement on the authors' behalf. Manuscript text,
results, and figures are unchanged. Author identities, venue, and submission
details remain deferred.

## R6 final decision, 11 October 2026

**Scoped empirical draft is coherent.** Read the [final scientific review](revision-review.md)
and [complete concern responses](revision-response.md). The paper now states one
limited, traceable finding. The underlying limits remain: reused questions,
conditional uncertainty, unidentified failure mechanism, sparse follow-ups,
and no faithful external-system comparison. Broader novelty remains modest.

The next step is author scientific review when resumed. No new experiment,
submission, or public release follows from this decision. R6 preserves all
scientific prose, tables, figures, and captions from `0689433`; only the draft
status line and review/progress records change.

## R5 figures, 11 October 2026

[View the three figures and provenance](figures/README.md). The evidence map,
utility contrasts, and two-solver diagnostic are embedded in the manuscript.
The display plan, inputs, and renderers froze at `655094d` before export.
All reported values and original numerical tables remain unchanged. Source,
output-hash, and PNG/PDF visual checks pass; no statistic was re-estimated.
Next is R6, the final methods and contribution review.

## R4 scope and prior work, 11 October 2026

The closest empirical papers now lead Related work. The revised comparison
states DART's direct overlap and retains the local GSM8K/Qwen3 contribution.
The [literature addendum](related-work-notes.md#r4-full-text-addendum--10-october-2026)
closes the earlier DART retrieval limit. Control settings and CLM timing move
to Appendix A.3; pilot history and the full cap table move to Appendix C.
Their outcomes and limits remain in the main text. Separate methods and
literature/contribution reviews passed. All numerical table rows and Box 1
are preserved. See the [revision response](revision-response.md).
Next is R5, starting with a separately frozen figure-export specification.

## R3 interpretation repairs, 10 October 2026

Methods and captions now state the limits of fixed-fit intervals and shared
training. The fresh guard section distinguishes the refit, explains the sparse
bootstrap, and includes the observed-mask ceiling with its limits. Opportunity
counts, CLM comparisons, and policy/collection costs are clarified. The methods
review passed; all prior table and Box 1 rows are unchanged. See the
[revision response](revision-response.md). R4 is next.

## R2 central revision, 10 October 2026

The abstract, Introduction, main repeat result, discussion, and Conclusion now
separate observed rescues, limited same-question structure, and unsuccessful
held-out-question selection. Box 1 adds existing variance/transfer diagnostics
and flagged-case scorer bounds, with their limits. The failed primary criteria
remain visible. Two targeted reviews passed; original table rows are unchanged.
See the [revision response](revision-response.md) for changes and pending work.

## Critical review, 10 October 2026

Read the [critical scientific review](critical-review-2026-10-10.md), with
separate [methods](reviewer-methods-2026-10-10.md) and
[contribution](reviewer-contribution-2026-10-10.md) critiques.

**Decision:** revise the scientific argument with existing evidence before
considering new collection. The draft is not ready for submission. Its central
claim needs to distinguish observed rescues, repeated question-specific signal,
and failed learned selection on held-out questions. The sparse follow-up needs
an explicit rare-event interval limit. Full DART v4 also narrows the post-draft
novelty claim. These are reviewer judgments, not new experiment results.

The critical review preserved v0.1; the subsequent R2 writing pass creates the
current v0.2 working draft. Author details and submission formatting are
deferred. Neither pass reopened raw outcomes, score caches, training references,
or sealed roles, or ran experiments or statistical analyses.

## Supporting files

- [Revision plan](revision-plan-2026-10-10.md): six ordered passes for v0.2,
  exact evidence additions, interpretation repairs, figure specifications, and
  final review criteria. R1–R6 are complete.
- [Figure export plan](figure-export-plan.md) and [display package](figures/README.md):
  frozen source/input/render specification, nine outputs, and artifact review.
- [Revision response](revision-response.md): completed changes and the final
  source-linked disposition of root and specialist concerns.
- [Final review](revision-review.md): scientific decision, separate methods and
  contribution memos, acceptance checks, and remaining research questions.
- [Revision claim-to-source map](revision-evidence-map.md): numbered claims,
  reported values, comparators, units, evidence roles, source sections, and
  required limits. Source/section links and central claims were reviewed.
- [Evidence ledger](evidence-ledger.md): facts, comparators, units, source links,
  protocol identities, and details that the tracked documents do not supply.
- [Bibliography](references.bib): 17 verified primary-source entries, including
  the 13 sources cited in the manuscript and optional supporting references.
- [Related-work notes](related-work-notes.md): comparison with the closest
  papers, source versions, and retrieval limits.
- [Original outline](../../docs/empirical-paper-outline-2026-10-09.md).

## Scope of this draft

The paper reports completed real-solver studies on GSM8K. It retains original
failed criteria and distinguishes reused development data from fresh questions.
Confidence is a strong control in several comparisons; the paper also reports
the separate setting where it performs worse than direct acceptance.

The later [synthetic acquisition failure](../../docs/g1-synthetic-results-2026-10-09.md)
is not pooled with this evidence. It remains a separate feasibility result.
The manuscript makes no new-method priority or external-system superiority claim.

Tables were transcribed from tracked result documents. No raw result, score,
reference, or sealed outcome was opened to write them. No model generation,
fitting, scoring, statistical reanalysis, or test run was performed. R5 adds
the separately frozen report-only figure export. The frozen experiment code
and artifacts remain unchanged.

Methods and literature were reviewed separately with GPT-6.1-sol at xhigh effort.
Review corrected the cap-selection description, the sparse contrast's
identification argument, the bridge reference timeline, and cost/accuracy units.
This was an editorial and provenance review, not a new human scoring audit.

## Remaining author work

1. Supply author names, affiliations, contributions, funding, and conflicts.
2. Review the completed v0.2 claim and decide whether to retain this scoped
   empirical report. All six revision passes are complete. A stronger claim
   needs a separately assessed question and prospective evidence plan.
3. Choose a venue and apply its current format and disclosure requirements.
   This draft is venue-neutral.
4. Review the completed R5 figures for the eventual venue. Any display change
   must follow the additive correction rule; do not rerun closed experiments.
5. Prepare a public artifact manifest only after checking licenses and access
   boundaries. A public release is not yet available or promised.

The error-taxonomy audit remains separate. The draft reports existing scorer
categories and avoids causal explanations that would require that audit.
It preserves the historical waiver of human answer scoring.
