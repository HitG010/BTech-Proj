# R5 figure export plan

Date: 11 October 2026. Scope: additive display export for manuscript v0.2.
Source checkpoint: `d1287e65ebf0fcea2ae2ad54f7e5ae47a9795d16` (completed R4).

## Freeze before rendering

Commit this plan, `figures/display-inputs.json`, the two renderers, and
`figures/frozen-export.json` before creating any figure. The manifest pins the
plan, inputs, renderers, and every source document by SHA-256. The renderer
verifies these identities before exporting. Source documents are read from the
stated Git checkpoint; this preserves the manuscript source even after figure
links are added to the working draft. At preparation, verify that those source
bytes also match the live files. Record the actual freeze commit and output
hashes in `figures/export-record.json`.

No raw response, score cache, question file, training reference, sealed role,
model asset, old executor, or old artifact is an export input. No effect,
interval, policy, opportunity rate, or power value is estimated. No study or
implementation test is run. The export uses existing Matplotlib and native
macOS PDF rendering; no model download, experiment, or environment change is
needed. Docker stays running.

## Source and transcription rules

Every displayed data item has an input record with source path, section/table,
evidence role, units, comparator, and precision. Numeric strings preserve the
reported digits. Floating-point conversion is used only to position marks.
Do not subtract rounded means or infer missing precision. Utility is in units
of scorer-defined correctness minus `.05 × charged output tokens / 1000`.
Costs include the paid direct draft and any inserted closure when applicable.

| Display | Source at the fixed checkpoint | Transcription |
|---|---|---|
| Figure 1 | Manuscript Table 1, Sections 3.3–3.4, Box 1, Sections 5.2–5.4; revision map C01–C18 | 50 repeat questions/800 responses; controls and post-hoc diagnostics reuse them; separate 64/512 two-solver panel and reused pilot; selected cap subset 11/18 pairs/36 new responses; fresh guard 228 direct/one thinking response. |
| Figure 2A | `docs/phase-2-repeat-panel.md`, terminal result; manuscript Table 2; map N1 | Original averaged four-draw combined Ridge contrast, six-decimal mean and interval. The result document's five-decimal summary is coarser; use the recorded six-decimal protocol value, not reconstructed digits. |
| Figure 2B | `docs/phase-2-router-feasibility-results.md`, Main four-draw comparison; `docs/phase-2-clm-probe-results.md`, Scope and main independent-half comparison; manuscript Table 3; map N2 | Three training-selected family contrasts, six decimal places. CPU, compact neural, and CLM/raw are the prespecified display rows. All other individual policy rows stay in Table 3. The averaged CLM interval is unaffected by its per-condition seed deviation. |
| Figure 3 | `docs/opportunity-panel-results.md`, Fixed policy results; manuscript Table 4/Section 5.1; map N3/C12 | All three policies for each solver. Accuracy has three decimals; charged output tokens have two. Positive-gain question counts are 4 and 24 out of the shared 64 groups. |

An unresolved mismatch stops export. Resolve it from tracked reports and record
the resolution before a new freeze. Do not open raw data to resolve it.

## Fixed display design and output names

All figures use white backgrounds, DejaVu Sans, vector text in PDF/SVG, and
240-dpi PNG. Shapes and labels supplement color. Sizes are 12 × 7.5 inches
(Figure 1), 12 × 6.8 (Figure 2), and 12 × 6.5 (Figure 3). These are manuscript
working figures; venue-specific sizing remains deferred.

### Figure 1: Study and evidence map

One enclosing block identifies reuse of the 50-question repeat panel. It
contains the primary learner, later controls, and separately labeled post-hoc
same-question diagnostics. The 64-question diagnostic is a separate block.
Its selected 11-question cap subset and the fresh 228-question guard have
separate lower blocks. Dashed arrows show design influence; explicit text
identifies the cap overlap and the guard's refitted policy. Boxes are not
scaled to sample size. Arrows do not represent pooled estimates or replication.

### Figure 2: Recorded utility contrasts

Two vertically separated panels share a utility-difference scale from −.06 to
+.02. Panel A shows the original learner minus its training-selected simple
baseline. Panel B shows three training-selected families minus four-draw
confidence. Each row shows its recorded point and conditional 90% interval,
plus an exact six-decimal text label. Include a zero reference. No pooled
effect, trend, superiority star, or comparison between training algorithms is
added. Both panels average A4→B4 and B4→A4 on the same 50 questions. Fits and
actions stay fixed; refitting, research-selection uncertainty and joint
coverage are absent. The original failed gates remain unchanged.

### Figure 3: Two-solver diagnostic

Two panels have the same axes: 0–1,850 charged output tokens/state and 55–95%
scored accuracy. Use one labeled mark for accept direct, always escalate, and
confidence. Do not connect the policies into a curve. Every mark includes the
reported accuracy and token value. Separate badges state positive realized
gain in at least one of two draws: 4/64 for 1.7B and 24/64 for 0.6B. These are
draw-dependent counts, not positive expected-gain rates. No intervals are
invented for the accuracy/token marks. Cross-size tokens are not equal compute.

### Outputs

For stems `figure-01-study-map`, `figure-02-utility-contrasts`, and
`figure-03-two-solver-diagnostic`, write:

- `figures/output/pdf/<stem>.pdf`
- `figures/output/svg/<stem>.svg`
- `figures/output/png/<stem>.png`

The nine files are new paper artifacts, separate from frozen study outputs.
The renderer refuses to overwrite them. Its receipt lists their hashes and
environment versions. No other scientific display is part of R5.

## Captions and manuscript placement

Store the exact captions in `display-inputs.json` and copy them to the
manuscript. Place Figure 1 after Table 1, Figure 2 after Table 3, and Figure 3
after the diagnostic Table 4 interpretation. Each figure links its PDF and SVG
and embeds its PNG. Retain every existing numerical table and Box 1. Keep the
sparse/cap results in their existing text/table form; do not join development
and fresh guard estimates as one fitted policy.

## Review and permitted rendering corrections

Before export, a documentary review checks every input against its source and
confirms comparators, roles, precision, and captions. After export, inspect all
three PNGs and render all three PDFs to PNG with native PDFKit/Quartz because
Poppler is unavailable. Review clipping, collisions, glyphs, marker labels,
axes, and footnotes. Inspect SVG structure and output identity. This is artifact
QA, not an implementation test or a statistical reproduction.

Record the review in `figures/review.md`. If layout fails, preserve the first
export. Use an additive renderer/manifest revision, committed before a new
export directory, and record the visual-only change. A data/caption correction
also requires a new input version and review before rendering. Do not silently
edit frozen inputs or scientific source files. R5 completes only after the
final displays pass inspection and are linked in the manuscript. R6 remains
the final methods and contribution assessment.
