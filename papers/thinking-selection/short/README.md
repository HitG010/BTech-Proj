# Short paper (workshop length)

**Learned Deferral Did Not Beat Confidence in a Same-Model Thinking Cascade.**
Draft, 2 November 2026; revised 7 November after two critic reviews
([reviews](reviews/README.md)). Phase 4, step 13 of the
[project review](../../../docs/project-review-and-publication-plan-2026-10-29.md).

- PDF: [`output/main.pdf`](output/main.pdf), 12 pages: 7 pages of main text,
  then references and two short appendices.
- Source: [`main.tex`](main.tex) and [`references.bib`](references.bib).
  [`short-source.zip`](short-source.zip) is a self-contained bundle (source,
  `.bbl`, figure) that compiles on Overleaf or arXiv with pdfLaTeX.
- Build here: `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=output main.tex`.

## Relation to the long report

This is a rewrite, not an excerpt, of [manuscript v0.8](../manuscript.md), which
remains the complete technical report and thesis chapter. Every number in the
short paper comes from v0.8 (whose numbers are unchanged from v0.7) or the tracked
result records it cites. Derived by
subtraction from those records: the agreement rule's lift over random (marked
†, from [the results record](../../../docs/deferral-curves-results.md)), the
three added Table 1 rows' differences against confidence (from the utilities
in the [deferral-curve report](../../../docs/deferral-curves-report.md)), and
the Qwen3-0.6B always-think gains +0.128 and +0.025 (from the
[two-solver results](../../../docs/opportunity-panel-results.md)). Since
9 November, [`derive_values.py`](derive_values.py) computes from the published
cache the follow-up rules' escalation rates in Table 1 (marked ‡) and the 11
questions with a rescue (14 with a rescue or harm; fewer than nine per training
fold on average, 11 × 40/50 = 8.8). It cross-checks with the records: zero-shot
CLM 380, calibrated CLM 61, and the encoder control 31 escalations out of 400.
The training-selected comparator's 29.8% is 119/400; the report prints 0.297
because 0.2975 rounds down in binary floating point. Other values added on
9 November come from tracked records: refit means and bounds and the 1.7B
agreement result from the [deferral-curve report](../../../docs/deferral-curves-report.md),
the between-question variance from manuscript v0.8, and 12 of 18 cap hits from the
[1.7B diagnosis](../../../docs/qwen17-diagnosis-results.md). The short
paper moves the guard, cap, CLM, and control details to appendices or to the
long report, and drops the September studies, Box 1, and the sparse-design
bounds, which the long report keeps.

[`references.bib`](references.bib) is generated from `../references.bib` by
[`make_references.py`](make_references.py), which removes the internal retrieval
notes and shortens author lists longer than six names. Edit the parent file and
rerun it.

## Figure

The paper uses revision 2 of Figure 1
([plan](figures/plan-r2.md), [renderer](figures/render_curves_r2.py), outputs in
`figures/output-r2/`), frozen and exported on 9 November 2026. It changes only
the presentation: tighter axes with the oracle marked off scale, direct labels,
and current names. Its renderer refuses to draw unless every value equals the
first export's manifest. The first export is kept unchanged.

The first Figure 1 was rendered once from the frozen
[display plan](figures/plan.md) and [renderer](figures/render_curves.py),
committed before the export. The renderer parses only the tracked
[deferral-curves report](../../../docs/deferral-curves-report.md), pinned by
hash; [`figures/output/manifest.json`](figures/output/manifest.json) records
every plotted value and the output hashes. A correction needs a new, separately
versioned figure.

## Reproducing the numbers

[`scripts/reproduce_paper.py`](../../../scripts/reproduce_paper.py) rebuilds
Tables 1–2, the Figure 1 points, and the quoted values from one cache file and
compares each with the published value; see the
[guide](../../../docs/reproduce-from-cache.md). Run on the real cache, all 195
checks pass ([report](../../../docs/reproduction-report.md)).

## Before submission

See the [submission and release checklist](submission-checklist.md). In short:
authors and endorsement, the venue's
template and anonymity rules, supervisor and peer feedback, and the release
decisions.
