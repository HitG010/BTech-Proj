# R5 final artifact review

Date: 11 October 2026. Root artifact review: **pass**.

## Export identity

The plan, display inputs, and both renderers froze at `655094d` before the
single completed export. The source documents are pinned to `d1287e6`.
The [pre-export review](pre-export-review.md) records the independent methods
freeze pass. The [receipt](export-record.json) records all nine outputs and
their hashes. The [verification record](review-verification.json) checks those
hashes, all frozen inputs, source identities, captions, and preserved text.

Independent GPT-6.1-sol/xhigh final artifact review: **pass**. Eight source
pins, four export pins, manifest/receipt identities, and all nine output hashes
match. SVG labels, exact captions, placements, and original tables pass. The
reviewer also inspected all three PNGs with no clipping or collisions. Root
review separately completed the PDF page inspection below.

## Visual inspection

All three 240-dpi PNG outputs were inspected at readable size. All three PDFs
were separately rasterized through native macOS PDFKit/Quartz with the frozen
Swift renderer and inspected. Poppler was unavailable. Each PDF has one page
and extractable text. The PDF page sizes are 864 × 540, 864 × 489.6, and
864 × 468 points. The temporary preview hashes are in the verification record.

| Figure | Inspection result |
|---|---|
| 1. Study map | Text fits inside the boxes; design arrows and labels are separate. Same-panel reuse, selected cap overlap, and the 128-state refit are visible. |
| 2. Utility contrasts | Separate comparators and panels; zero reference and all four points/intervals visible. Exact numerical labels match the inputs. No clipped labels or overlap. |
| 3. Two-solver diagnostic | All six policy labels and point values are readable. Axes match across panels; opportunity counts remain separate from accuracy. No connecting frontier or inferred interval. |

No clipping, collisions, missing glyphs, or unreadable labels were found in
either raster path. All SVGs parse, retain vector text, and contain no embedded
raster image. Visible SVG labels preserve all transcribed numerical values.
No display correction or second export was needed. Venue-specific sizing is
still deferred; the review concerns these working manuscript figures.

## Manuscript and scientific preservation

All three captions are exact copies of the frozen input text. Existing
numerical tables, Box 1, and the sparse interpretation remain unchanged.
The new figure locations follow the plan: evidence map after Table 1, utility
contrasts after Table 3, and diagnostic after the Table 4 interpretation.

No effect, confidence interval, opportunity rate, fit, label, or power value
was recomputed. No raw project response, score cache, training reference,
sealed outcome, model asset, or original executor was opened. No study command
or implementation test was run. Existing experiment reports are unchanged.

## Tool notes

Matplotlib emitted font-cache permission warnings, then completed normally
using the temporary cache. The first root artifact-check command used system
Python and stopped at its missing Pillow import, before checking or writing
records. The same check completed in the existing project Python environment.
No dependency was installed and the exporter was not rerun. The export receipt
is preserved with its original `visual_review: pending` state; this later review
and its verification record close that pending inspection.

Git's whitespace checker flags spaces at the ends of Matplotlib-generated SVG
path lines. Those are valid separators inside XML path attributes. Preserve
the exported bytes and their receipt hashes; no formatting rewrite is applied
to the SVG artifacts. The document, JSON, and renderer whitespace checks pass.

R6 remains the final methods and contribution assessment. Artifact QA does not
establish novelty, generalization, or submission readiness.
