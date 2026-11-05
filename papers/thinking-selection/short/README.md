# Short paper (workshop length)

**Learned Deferral Did Not Beat Confidence in a Same-Model Thinking Cascade.**
Draft, 2 November 2026. Phase 4, step 13 of the
[project review](../../../docs/project-review-and-publication-plan-2026-10-29.md).

- PDF: [`output/main.pdf`](output/main.pdf), 8 pages: about 5.5 pages of main
  text, then references and three short appendices.
- Source: [`main.tex`](main.tex) and [`references.bib`](references.bib).
  [`short-source.zip`](short-source.zip) is a self-contained bundle (source,
  `.bbl`, figure) that compiles on Overleaf or arXiv with pdfLaTeX.
- Build here: `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=output main.tex`.

## Relation to the long report

This is a rewrite, not an excerpt, of [manuscript v0.7](../manuscript.md), which
remains the complete technical report and thesis chapter. Every number in the
short paper comes from v0.7 or the tracked result records it cites; the only
derived value is the agreement rule's lift over random (marked †, from
[the results record](../../../docs/deferral-curves-results.md)). The short
paper moves the guard, cap, CLM, and control details to appendices or to the
long report, and drops the September studies, Box 1, and the sparse-design
bounds, which the long report keeps.

[`references.bib`](references.bib) is generated from `../references.bib` with
the internal retrieval notes removed. Edit the parent file and regenerate it.

## Figure

Figure 1 was rendered once from the frozen
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
authors and endorsement, the full texts of the cascade citations, the venue's
template and anonymity rules, supervisor and peer feedback, and the release
decisions.
