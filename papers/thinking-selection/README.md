# Empirical paper draft

## Read the paper

[Manuscript, version 0.1](manuscript.md)

**Title:** Confidence and Learned Thinking Selection on GSM8K: A Controlled Study
of Small Qwen3 Models.

The draft contains an abstract, introduction, related work, methods, results,
discussion, limitations, conclusion, references, and reproducibility appendices.
It includes five main tables and one accounting table.
It is a complete prose draft for author review, not a submitted paper.

## Supporting files

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
2. Review the scientific argument against the closest empirical papers.
   The evidence supports a narrow GSM8K/Qwen3 paper; broader claims need broader
   evidence under a separate protocol.
3. Choose a venue and apply its current format and disclosure requirements.
   This draft is venue-neutral.
4. Decide which verified cached-report figures would help. Freeze an additive
   export plan before creating them. Do not rerun closed experiments.
5. Prepare a public artifact manifest only after checking licenses and access
   boundaries. A public release is not yet available or promised.

The error-taxonomy audit remains separate. The draft reports existing scorer
categories and avoids causal explanations that would require that audit.
It preserves the historical waiver of human answer scoring.
