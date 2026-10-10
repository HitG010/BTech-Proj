# Manuscript figures: R5 report-only export

Freeze checkpoint: `655094d`. Source checkpoint: `d1287e6` (R4).
The figures use transcribed report values. They add no scientific estimates.

| Figure | PDF | SVG | PNG |
|---|---|---|---|
| 1. Study and evidence map | [PDF](output/pdf/figure-01-study-map.pdf) | [SVG](output/svg/figure-01-study-map.svg) | [PNG](output/png/figure-01-study-map.png) |
| 2. Recorded utility contrasts | [PDF](output/pdf/figure-02-utility-contrasts.pdf) | [SVG](output/svg/figure-02-utility-contrasts.svg) | [PNG](output/png/figure-02-utility-contrasts.png) |
| 3. Two-solver diagnostic | [PDF](output/pdf/figure-03-two-solver-diagnostic.pdf) | [SVG](output/svg/figure-03-two-solver-diagnostic.svg) | [PNG](output/png/figure-03-two-solver-diagnostic.png) |

## Provenance and checks

- [Frozen plan](../figure-export-plan.md): source, transcription, rendering,
  output paths, captions, and correction rules.
- [Display inputs](display-inputs.json): reported values, precision, roles,
  comparators, source locations, and exact manuscript captions.
- [Frozen manifest](frozen-export.json): eight source and four export-file hashes.
- [Pre-export review](pre-export-review.md): root transcription checks and the
  independent methods review before rendering.
- [Export receipt](export-record.json): actual freeze commit, environment,
  and SHA-256 identities of all nine outputs. Its visual-review field records
  the state at export; the later [artifact review](review.md) is authoritative
  for final inspection.

The source hashes refer to Git bytes at `d1287e6`. Later manuscript figure
insertions and revision-status updates do not replace that source snapshot.
Study reports and original experiment artifacts remain unchanged.

## Preservation

The one completed Matplotlib export used `render_figures.py` with the project's
existing Python environment. It refuses to overwrite the completed files.
`render_pdf_preview.swift` renders a one-page PDF through native PDFKit/Quartz
for artifact QA. The PDF previews are temporary review files, separate from
the deliverables. Poppler was unavailable; no dependency was installed.

Preserve the completed inputs, manifest, renderers, receipt, and outputs.
Do not rerun the exporter in place. Any required correction follows the
additive revision rule in the frozen plan. R6 is the final scientific review;
venue-specific sizing, author information, and public release remain deferred.
