# Empirical paper draft

## Read the paper

[Manuscript, version 0.2 working draft](manuscript.md)

**Title:** Confidence and Learned Thinking Selection on GSM8K: A Controlled Study
of Small Qwen3 Models.

The draft contains an abstract, introduction, related work, methods, results,
discussion, limitations, conclusion, references, and reproducibility appendices.
It includes four main tables, appendix accounting and cap tables, and a post-hoc
diagnostic box. R1–R4 are complete. Figures and final review remain R5–R6 work. This is a working draft, not a submitted paper.

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
  final review criteria. R1–R4 are complete; R5–R6 remain pending.
- [Revision response](revision-response.md): completed text changes, targeted
  review outcomes, and unresolved concerns assigned to later passes.
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
fitting, scoring, statistical reanalysis, figure export, or test run was performed.
The frozen experiment code and artifacts remain unchanged.

Methods and literature were reviewed separately with GPT-6.1-sol at xhigh effort.
Review corrected the cap-selection description, the sparse contrast's
identification argument, the bridge reference timeline, and cost/accuracy units.
This was an editorial and provenance review, not a new human scoring audit.

## Remaining author work

1. Supply author names, affiliations, contributions, funding, and conflicts.
2. Complete R5 figures and R6 final review. The central argument, interpretation,
   prior-work comparison, and supporting-section revision are complete. Broader
   claims need broader evidence under a separate protocol.
3. Choose a venue and apply its current format and disclosure requirements.
   This draft is venue-neutral.
4. Decide which verified cached-report figures would help. Freeze an additive
   export plan before creating them. Do not rerun closed experiments.
5. Prepare a public artifact manifest only after checking licenses and access
   boundaries. A public release is not yet available or promised.

The error-taxonomy audit remains separate. The draft reports existing scorer
categories and avoids causal explanations that would require that audit.
It preserves the historical waiver of human answer scoring.
