# Display plan: short-paper Figure 1, accuracy and cost

Frozen 2 November 2026, before the export. The renderer
[`render_curves.py`](render_curves.py) and this plan are committed first; the
export follows in a later commit and is not regenerated afterwards. A
correction needs a new, separately versioned figure.

## Source

Only the tracked user-run report
[`docs/deferral-curves-report.md`](../../../../docs/deferral-curves-report.md),
SHA-256 `92863d455eeeb03092dc1974835768b1e732ec5af347ad25dc2f52ec396b8316`.
The renderer refuses to run if the hash differs. It parses the report's
tables; no value is typed by hand, re-estimated, or read from `artifacts/`.

Checks before drawing: the five anchor values (always direct, always escalate,
oracle, confidence, and combined on the repeat panel) equal the report; the
repeat panel has 20 points (ten recomputed policies, nine Table 3 rows, and
agreement); every λ sweep has the ten frozen values; the λ = .05 sweep point
equals the policy-table point to the report's rounding.

## Encoding

Three panels, each with its own axes because the solvers' accuracy ranges
differ: A, repeat panel (Qwen3-1.7B, 400 states); B and C, two-solver panel
(Qwen3-0.6B and Qwen3-1.7B, 128 states each).

- x: output tokens per state, including the paid draft and any thinking call;
  y: scored accuracy (%).
- Dashed gray line: random escalation at equal cost, between always direct and
  always think (black diamonds).
- Black square: hindsight oracle (escalates exactly the realized rescues).
- Blue line: confidence refitted at each λ in {0, .01, .02, .03, .05, .075, .1,
  .15, .2, .3}; large blue dot at λ = .05.
- Orange line (panel A only): combined learner refitted at each λ; large
  orange dot at λ = .05.
- Gray dots (panel A only): other rules at λ = .05 (question-only,
  solver-only, training-selected baseline, the nine Table 3 rows, and
  two-draft agreement, which carries the only direct label).

Colors: categorical slots 1 and 2 of the reference palette (`#2a78d6`,
`#eb6834`), validated with the palette script (all checks pass in light mode);
neutral ink for references. One legend below the panels. Static print figure:
no interactive layer. Outputs PDF (fonts embedded), SVG, and 300-dpi PNG,
plus `output/manifest.json` with source, renderer, plan, and output hashes and
every plotted value.

## Caption (for the short paper)

Accuracy and output cost of the tested deferral rules. Each panel's dashed
line is random escalation at equal cost between always accepting the draft
and always thinking; the square is the hindsight oracle. Lines trace rules
refitted at ten cost preferences from λ = 0 to .3; large dots mark the
primary λ = .05. Panels use different axes. Values are post-hoc, from reused
development panels, and carry no intervals.
