# Illustrative figure revision v2

Date: 28 October 2026. User request: more illustrative figures and an independent
legibility critic. Preserve the original R5 export and the 27 October PDF/ZIP.

## Evidence boundary and freeze

This is an additive display revision. All numerical marks use the original
reported values. No fit, scoring, statistical estimate, raw response, reference,
sealed allocation, or experiment is needed. The source manuscript v0.2 is saved
here before any readability edits. Original report inputs are pinned by hash.
Commit this plan, the display inputs, source snapshot, renderer, and manifest
before rendering. The renderer verifies hashes and refuses to overwrite output.
Any correction retains earlier outputs and uses an additive pinned revision.

## Design

1. **Decision and observed outcomes.** Show the paid direct draft, selection,
   acceptance, and question-only fresh thinking. Show the 348/10/30/12 scored
   outcomes in an explicitly labeled 2×2 matrix. Each of the 400 paired states
   contributes once. Cells are equal size; counts are not utility-gain labels.
   The selector does not observe the future thinking outcome.
2. **Sampling and study roles.** Show 50 questions, eight draws per mode, 800
   responses and 400 pairs. Separate question exclusion (40 fit / 10 evaluation)
   from the draw-half choice (A / B). The four-draw sketch shows one outer fold;
   both directions and all five folds remain in the caption. Show later reuse,
   the separate 64-question panel, its 11-question cap subset, and the separate
   228-question guard. The guard's refit uses 128 development states. The dashed
   arrow denotes design influence, not shared questions or replication.
3. **Utility comparisons.** Preserve original primary versus training-selected
   simple baseline and exploratory versus confidence panels. Use the same means,
   intervals, and axis. Remove tiny duplicate numerical strings; exact values
   remain in Tables 2 and 3. Explicitly retain conditional fixed-fit intervals,
   omitted retraining/research uncertainty, no joint coverage, and failed screens.
4. **Two-solver comparison.** Use aligned policy rows with accuracy dots and
   output-token bars. Preserve all six points and the 4/64 and 24/64 observed
   opportunity counts. Include the two-draw condition, point-estimate status,
   and unequal compute per token across solver sizes. Add no uncertainty bars,
   frontier, statistical size interaction, or recommendation to deploy a policy.

## Printed legibility

Design at 6.6 inches wide with labels at least 10 points (mathematical subscripts
excepted). The reviewer PDF's 162mm text width scales this to about 9.66 points.
Embed at full column width without a height limit that silently shrinks text.
Avoid exact interval text inside plots; retain exact values in numerical tables.
Use consistent blue, teal and orange with direct labels and shape distinctions.
Use vector PDF/SVG and 220-dpi PNG. Illustrations are schematic, not generated
photos or invented data. Build all figures with Matplotlib.

## Review and manuscript integration

The critic's initial questions and findings are in
`../legibility-critic-2026-10-28.md`. In response, add prose callouts and introduce
paired state, CLM, training-selected family, and progression screens. Simplify
opening prose using the loaded Humanizer skill while retaining scientific scope,
primary failures, uncertainty, scorer limits, and AI-assistance disclosure.
Use automatic LaTeX figure numbers and cross-references in a separate `latex-v2/`
package. The current Markdown manuscript becomes v0.3 after integration; v0.2
remains available here and in Git. Retain all nine original table blocks.

Inspect every figure at print size and every compiled PDF page. Ask the critic
to challenge the revised pages and record responses to each substantive point.
No new-method, mechanism, novelty, or human endorsement claim follows from this
legibility pass. Humanizer is editorial support, not a scoring or evidence tool.
