# Illustrative reviewer LaTeX package

Manuscript v0.3, 28 October 2026. This is the current 24-page internal review
copy. Author information and endorsement remain pending. The older v0.2
package and 22-page PDF remain in `../latex/`.

## Build or edit

Edit `main.tex`. From this directory, run:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=output/pdf main.tex
```

`make` runs the same command. Output: `output/pdf/main.pdf`.
For Overleaf, upload `thinking-selection-review-source-v2.zip` as a new project,
select `main.tex`, and use pdfLaTeX. The source bundle has all four vector
figures, the bibliography, and the cited project documentation. It does not
need this repository or an experiment environment to compile.

## What changed

- Four illustrative figures replace the previous three: decision/outcome matrix,
  question/draw design, utility contrasts, and aligned accuracy/output-cost rows.
- Figures use automatic numbers, cross-references, and full column width.
- The abstract and conclusion are clearer; technical terms are defined before use.
- Tables 2 and 3 remain intact. Their original rows and all other scientific
  table rows are unchanged.
- `review-notes/` contains the critic's questions and the response. The critic
  accepted the 25-page build; root reviewed the final pagination-only reduction
  to 24 pages. The first 17 page PNGs are identical between those builds.

`source-manifest.json` pins current manuscript/report inputs; `layout-review.json`
records build, preservation, and visual checks. `figures/` contains unchanged
copies of the final additive figure export. `source-records/` contains the 13
project records identified in Appendix D. Links within those records may need
the full repository. They contain documentation, not raw study data or sealed
outcomes. This local bundle is not a public artifact release.

## Known editorial limits

The paper remains detailed. Table 1 continues across pages with repeated
headers; some float pages have generous whitespace; minor paragraph transitions
could improve in a venue-specific layout. These did not block the internal
legibility review. Scientific scope, scorer-based correctness, conditional
uncertainty, failed criteria, sparse limits, and modest novelty remain intact.

The original bibliography is unchanged. BibTeX emits one empty-year warning for
the intentionally undated MiniLM model card; its existing undated/access-date
note prints correctly. No publication date was invented.

Keep scientific LaTeX changes synchronized with `../manuscript.md`. No source
has been uploaded, submitted, or sent to reviewers by this task.
