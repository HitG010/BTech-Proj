# Display plan: short-paper Figure 1, revision 2

Frozen 9 November 2026, before the export. This plan and
[`render_curves_r2.py`](render_curves_r2.py) are committed first; the export
follows in a later commit into `output-r2/` and is not regenerated afterwards.
The first export (`output/`, [plan](plan.md)) is unchanged. A further change
needs a new, separately versioned figure.

## Why a revision

Presentation only, after the [critic reviews](../reviews/README.md) of
7 November and the author's request for clearer figures:

- the hindsight oracle stretched every y-axis, compressing the curves;
- the thirteen gray reference dots could not be told apart;
- the labels "Repeat panel" and "Combined learner" no longer matched the text,
  which now says "main panel" and "predeclared learner";
- the direction of the λ sweep was not visible.

## Source and checks

Same source as the first export: only the tracked report
[`docs/deferral-curves-report.md`](../../../../docs/deferral-curves-report.md),
SHA-256 `92863d455eeeb03092dc1974835768b1e732ec5af347ad25dc2f52ec396b8316`.
The renderer imports the frozen parser and checks from `render_curves.py`
unchanged. It then refuses to draw unless every extracted value equals the
`values` block of the first export's `output/manifest.json`, so the plotted
numbers are identical to the reproduced first figure. No value is typed by hand,
re-estimated, or read from `artifacts/`.

## Encoding

Three panels at the paper's text width (6.5 in), each with its own axes:
A, main panel (Qwen3-1.7B, 50 questions × 8 draws); B and C, two-solver panel
(Qwen3-0.6B and Qwen3-1.7B, 64 questions × 2 draws).

- x: output tokens per state, draft included; y: scored accuracy (%). Axis
  ranges fit the plotted rules: A 87.4–95.6, B 59–84.5, C 82–88.6.
- Hindsight oracle: a black triangle on the top edge at its token cost, labelled
  with its accuracy, because it lies above each axis.
- Dashed gray line: random escalation at equal cost between always direct and
  always think (black diamonds), labelled "random" on the line.
- Blue line: confidence refitted at each λ in {0, .01, .02, .03, .05, .075, .1,
  .15, .2, .3}; large dot at λ = .05; "λ=0" marks the end where the sweep starts.
- Orange line (panel A): the predeclared learner, refitted the same way.
- Hollow gray circles (panel A): the other rules in Table 1 at λ = .05. Only
  two-draft agreement and zero-shot CLM carry labels.
- Direct labels for the curves; a two-row legend for marker meanings.

Colors as in the first export (`#2a78d6`, `#eb6834`, neutral inks). Fonts:
DejaVu Sans, 6–7.6 pt at print size. Outputs PDF (fonts embedded), SVG, and
300-dpi PNG, plus `output-r2/manifest.json` with source, first-manifest,
renderer, plan, and output hashes and every plotted value. Rendered on the
author's Mac with matplotlib 3.11.1 from the project environment.

## Caption (for the short paper)

Accuracy and output cost of the deferral rules. Lines trace rules refitted at
ten cost preferences (λ from 0 to 0.3; large dots at λ = 0.05), and hollow
circles are the other rules in Table 1. The dashed line is random escalation at
equal cost; triangles mark the hindsight oracle, above each axis. Panels use
different axes. Values are post-hoc, from reused development panels, and carry
no intervals.
