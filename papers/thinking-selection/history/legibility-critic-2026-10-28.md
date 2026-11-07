# Independent legibility critique — 28 October 2026

**Status:** Final v0.3 legibility review complete. No substantive legibility blocker remains in the 25-page reviewer PDF. The initial rankings below describe the earlier v0.2 version; the final assessment at the end records their resolution and the remaining optional cuts. This is an AI-assisted editorial critique, not human peer review or a new scientific audit.

**Scope:** Read `manuscript.md`, `latex/main.tex`, and `figures/display-inputs.json`; visually inspected all 22 rendered PDF pages in `/private/tmp/thinking-selection-latex-review/checked-pages/`. Checked the current branch/worktree state and the relevant repository instructions. No tests, experiments, fitting, scoring, statistical reanalysis, reference retrieval, raw outcomes, score caches, or sealed material were used. This critique changes no manuscript, figure, or study artifact.

## Assessment

The paper's main argument is understandable after careful reading: thinking sometimes rescues direct answers, some post-hoc question-level structure appears in repeated outcomes, and the tested learners nevertheless fail to improve held-out-question selection under the specified cost contract. The manuscript also preserves the important distinction between that result and the narrower follow-ups.

The reading cost is unnecessarily high. The abstract introduces almost the entire research history. The first main result arrives near the bottom of PDF page 7. Readers encounter several kinds of evidence, comparators, and restrictions before receiving a simple picture of the decision or sampling design. Three graphics largely duplicate neighboring material while printing much smaller text than the body. The PDF is technically tidy, but its explanatory hierarchy needs work.

The main body text, equations, and most tables are comfortably readable. I found no clipped text, missing glyphs, conspicuous overlap, or incorrect figure numbering in this version. The problems below concern comprehension and chart readability at ordinary page size, rather than compilation defects.

## Ranked changes

### Must fix 1: Give the abstract one center of gravity

**Location:** Abstract, PDF page 1; Introduction, pages 1–2.

The abstract moves through the primary learner, post-hoc transfer, capacity/objective controls, flagged presentation cases, two solvers, parser guards, and caps. Terms such as “primary reproducibility test” and “primary fixed-policy point comparison” appear before the reader knows what they mean. The main finding is stated only after most of this inventory.

Lead with the concrete problem and result: an extra thinking solve sometimes rescues a draft, but the tested learner did not turn those opportunities into better selection on held-out questions. Then give the decision contract, the 50-question/800-response sample, the 30 rescues/10 harms, and the primary contrast with its exact conditional interval. Explain the limited post-hoc structure in a short sentence. The separate supporting studies can receive one collective sentence or remain in the introduction.

Preserve −0.016204, [−0.033276, −0.000635], the training-selected simple comparator, and the conditional nature of the interval wherever the full result is reported. Do not rewrite the conclusion as a population finding that learning cannot work. Do not describe the same-question result as confirmed reproducibility.

### Must fix 2: Show the decision and evaluation split before cataloging studies

**Location:** Sections 3.1 and 3.4, pages 3–5 and 7; Figure 1, page 6.

The current study map explains which panels influence later studies. It does not show the actual decision: question → paid direct draft → accept, or buy a fresh question-only thinking solve. Nor does it visually distinguish a question split from a response-half split. Those are the two concepts the reader needs most.

Add a simple decision diagram with the incurred direct cost on both branches. Show that the thinking branch starts a fresh solve from the question, rather than revising the draft. A second small schematic can show 50 question groups, eight draws in each mode, 800 responses/400 sample-index pairs, and A/B response halves. Mark that an evaluation question is excluded from fitting and tuning. Label the opposite-half directions without implying independent study replications.

Keep the existing study map if useful, but make its job distinct from Table 1. The map's 64 → 11 subset relation is useful. Its design-influence arrows do not substitute for the decision diagram or the training/evaluation boundaries.

### Must fix 3: Redesign figures for their final embedded size

**Location:** Figures 1–3, PDF pages 6, 10, and 12.

The figures' internal type is substantially smaller than the surrounding text. Figure 1's explanatory lines and arrow labels require close inspection. Figure 2 is the weakest: its long subtitles, six-decimal point/interval annotations, footer qualifications, and four forest-plot rows occupy a relatively small graphic. Figure 3 is easier to decode because shapes and direct policy labels help, but its exact accuracy/token pairs and small opportunity-rate labels still need enlargement.

For any additive replacement display:

- Set a legible minimum label size at the final manuscript width, then simplify the composition to fit it. Enlarging the raster preview alone does not solve the embedded PDF scale.
- Remove duplicated sentences from inside graphics; retain the relevant restrictions in the adjacent caption. Essential comparator labels must stay visible within each panel.
- Let tables or a clearly readable numeric column carry the exact six-decimal values. The forest marks do not need a second tiny transcription of every interval endpoint if the same values are immediately available in a table.
- Keep a prominent zero line and the explanation that negative utility differences favor the stated comparator. Keep the original learner and later controls in separate panels with their different comparators.
- Preserve Figure 3's shared axes, distinct marker shapes, and direct policy names. Do not connect the three policies as though they formed an estimated frontier. Keep the reported opportunity count separate from expected gain, and keep output tokens separate from equal compute across sizes.

Page 6 also has substantial white space around its centered figure. A wider, simpler composition could use the page more effectively. Review revised graphics at normal page scale as well as zoomed in.

### Must fix 4: Reduce the vocabulary a reader must learn at once

**Location:** Abstract; Sections 2.2, 3.3–3.5, 4, and 5.

The manuscript moves rapidly among “paired state,” “response half,” “four-draw,” “training-selected family,” “screen,” “reproducibility,” “released CLM,” “refitted guard,” and “observed eligibility mask.” Several have precise local meanings that are not obvious from their familiar English words.

Define a paired state once as a direct response and its sample-index-paired fresh thinking response for one question/draw. Spell out Contrastive Language Models (CLM) on first use. Introduce the phrase “predeclared progression criteria” before shortening it to “criteria” or “screens.” Explain that selecting a family within training means choosing a member using training data, rather than selecting a new dataset.

The word “reproducibility” needs special care: here it names an opposite-half mean-gain prediction/MSE criterion, rather than rerunning code or reproducing the paper. Use a descriptive phrase beside that criterion, and distinguish it from same-question action-transfer utility. Retain the original named criterion in the detailed table/protocol reference.

The manuscript can keep the mathematical definitions, but put the plain-language interpretation immediately before or after them. In particular, “finite-panel bound with the observed action-change mask held fixed” is easier to follow after “only one of 228 questions changes action.”

### Must fix 5: Make every figure part of the argument and make references robust

**Location:** All three figure insertions; `latex/main.tex`.

Figures 1–3 are locally introduced by their captions; the prose does not explicitly tell the reader to consult them or state what to see. Table callouts are more consistent. A reader can treat the graphics as optional decoration even though they should reduce the burden of the text.

Add a short prose callout before each figure: what the map separates, what the forest plot says about the primary comparison and later controls, and how the two solver panels differ. A callout should interpret a feature of the display, not repeat the full caption.

The LaTeX currently uses `\caption*` with literal figure numbers and no figure-specific `\label` anchors. No numbering error is present now, but adding figures makes this fragile. Use a consistent reference scheme, and check Markdown/LaTeX captions, labels, prose references, and data/code-availability text together after additions. Preserve source-record and original-display identities; new figures need their own explicit provenance.

### Must fix 6: Make comparator and uncertainty distinctions easy to retrieve

**Location:** Table 2, Box 1, Table 3/Figure 2, pages 8–10.

The primary combined learner is compared with a baseline chosen within training from accept, escalate, and confidence. Later families are compared directly with confidence. The secondary full-eight confidence values are different again. The manuscript states these distinctions accurately, but a reader must remember them across paragraphs and displays.

Use the same short comparator wording every time each endpoint appears. Keep four-draw and full-eight labels explicit beside their values. Keep conditional intervals labeled as fixed-fit/fixed-action summaries, with the full explanation in Section 3.5. Do not compress the caption so far that readers could read a below-zero bar as algorithm-level population inferiority or as a jointly covered comparison.

For Box 1, preserve the failed primary criterion above it and the statement that post-hoc diagnostics do not replace it. The positive transfer rows must not become the visual headline of the primary-results page. The variance statistic and MSE reproducibility statistic measure different quantities; their names should make this visible before the reader compares their signs.

## Strongly recommended, but optional

### 7. Shorten the path through supporting studies

Section 5 asks readers to understand a two-solver diagnostic, a reused learned pilot, a refitted parser policy, sparse identification, a finite-panel bound, and an enriched cap intervention. Sections 6.2–6.4 then revisit much of that material. This creates the feeling of several papers arranged chronologically.

Consider a compact main-text supporting-results table with columns for question/policy target, decisive observation, and inference limit. Keep the two-solver plot because it shows a distinct pattern. Give the fresh guard result and its identification limit a short main-text paragraph, with the detailed bound and cap matching in Appendix C. Such relocation is editorial judgment; retain the complete failed endpoints and source-linked details. It must not hide an unfavorable result.

### 8. Consolidate repeated caveats without weakening them

The same cautions recur in the abstract, introduction, methods, captions, result prose, discussion, limitations, and conclusion: reused data, fixed actions, omitted refitting, no promotion of failed criteria, scorer-defined correctness, and costs excluded from token utility. Each caution matters. Their repeated full wording makes the reader spend effort distinguishing what is new from what was already stated.

Keep one complete uncertainty account in Section 3.5, local restrictions that are essential to interpreting a display, and a concise limitations summary. Elsewhere, refer to the established restriction in a short phrase. In the conclusion, lead with the result rather than reciting the entire safeguard inventory. Keep the sparse bootstrap's inability to create unseen rescues and the fixed-mask bound's non-population scope locally explicit; those are easy to misread if relegated to a distant footnote.

### 9. Polish lower-priority presentation details

- The title is accurate but broad. A title or subtitle that points to rescues versus selection would help signal the actual finding without implying a universal failure.
- The four discussion subsections can likely become two connected arguments: what the tested learners establish, and what limits transferring that observation. They currently repeat results and limitations more than they synthesize them.
- Appendix A's model hashes are useful provenance but dominate the table. A shorter readable identifier plus an exact machine-readable manifest reference could improve scanning if repository/package requirements permit. Do not discard the full identities.
- Bibliography entries retain long author lists and retrieval notes, which take nearly two pages. This is secondary to the main-text fixes and should follow the eventual venue style; do not invent dates or stronger source verification.

## Questions sent to the revising author/agent

1. What one sentence should a reader remember after closing the paper? Is it the coexistence of rescues, limited repeated structure, and failed held-out selection?
2. Should Figure 1 explain the decision/evaluation design or the history of panels? Its current information primarily serves the latter purpose.
3. Can a new reader explain why 800 responses produce 400 paired states, and why opposite halves are not independent replications, without rereading Section 3.4?
4. Is “reproducibility” recognizable as a specific MSE prediction criterion rather than a claim about independent replication?
5. Can a reader identify the comparator for every utility number from its immediate label, including the secondary full-eight results?
6. Can a reader read all figure labels when the A4 page is shown at normal size? In the present version, the small detailed text is the limiting factor.
7. Are the parser/cap results necessary to understand the central claim, or can their main-text treatment become a concise supporting check with full appendix details?
8. After adding graphics, have the figure numbers, prose callouts, captions, source records, and Markdown/LaTeX versions all been checked together?

## Acceptance criteria for the next legibility pass

The revised version should let a reader identify the decision, sample units, comparator, central negative result, and principal inference limit from the abstract, one early schematic, and the main results figure. Every figure should be readable at its actual PDF size and explicitly called out in prose. The original failed criteria, exact reported values, scorer-based endpoint, conditional uncertainty, same-question/held-out distinction, sparse identification, and non-population bounds must remain intact. The next review should inspect the actual revised pages, rather than infer success from larger source-font settings.

## Revision pass: v0.3 prose and four new PNG figures

Reviewed the current v0.3 text diff and all four `figures-v2/output/png/` graphics. This pass also used the available Humanizer skill as a prose-review guide; scientific distinctions and supported qualifiers take precedence over stylistic simplification. No manuscript or figure was edited by this reviewer.

The opening now gives the result first. The new definitions address the paired-state, progression-screen, training-selection, CLM, and reproducibility ambiguities. All four figures receive substantive prose callouts. The decision graphic clearly separates the choice from the future thinking outcome, and its retrospective matrix labels all four scored categories correctly. The sampling graphic makes the excluded evaluation questions and opposite draw halves visible. The larger forest plot keeps comparator panels separate while leaving exact values in tables. Row-aligned accuracy and token displays are much easier to scan than the original scatter labels.

Two already identified graphic corrections remain necessary: Figure 2's arithmetic line must explicitly read “50 questions × 8 draws × 2 modes = 800 responses”; Figure 4 should use the neutral title “Policy accuracy and output cost,” since the larger solver's confidence policy has lower point accuracy than direct acceptance. The root author/agent reported that both additive corrections were in progress.

One local prose correction is needed in Section 3.4. The sentence beginning “This differs from later controls” now follows the newly inserted definition of training selection. Its intended contrast is the original simple comparator versus the later confidence comparator. Move that sentence directly after the original-comparator sentence, then give the training-selection definition. This removes an ambiguous antecedent without changing the method.

The abstract's flagged-presentation sentence remains hard to interpret without reading the results. Cutting it from the abstract while retaining the complete result elsewhere would improve focus; this is optional. Retaining the detailed sparse/cap sections with a route sentence is a defensible choice, although their length remains a secondary reading burden.

No additional blocker was found in the standalone figures. The final pass still needs to inspect the actual embedded PDF: nominal font sizes and large PNGs do not establish printed-size legibility. In particular, verify that the figures are embedded at the intended width without a height constraint shrinking them, that captions stay with their graphics, and that the new figure numbering agrees across all prose and captions.

## Preliminary embedded-PDF pass: 24-page v0.3 build

Visually inspected all 24 pages rendered in `/private/tmp/thinking-selection-legibility-pages/` and read the corresponding `latex-v2/main.tex` figure references and placement commands. Figures 1–4 appear on pages 4, 7, 11, and 13. They are clearly more readable than the original displays. The corrected 50-question product, neutral Figure 4 title, comparator-paragraph order, and simplified abstract are present.

The figures use `width=\linewidth` with no height cap. The renderer specifies a 6.6-inch canvas with a 10-point minimum normal text size; the A4 layout has approximately 6.38 inches of text width. That implies approximately 9.66-point labels after uniform scaling. This is a source/layout calculation, not an extracted PDF-font measurement. The actual page views also show readable labels, including Figure 4's exact point values and Figure 3's comparator headings. Captions remain with their figures, and automatic figure references display the expected numbers. No clipping, overlap, missing glyph, or broken figure callout was found.

One remaining pagination issue should be corrected before delivery: short central Tables 2 and 3 split across pages. Table 2's caption and first two criteria are on page 8, while the primary average contrast and remaining criteria start page 9. Table 3 leaves only the confidence and CPU rows on page 10, with the other policies on page 11. Keeping these tables intact would help readers compare rows and retain the caption's endpoint/uncertainty definition. The root author/agent agreed and added space reservations outside the preserved table blocks; a rebuilt layout is pending. The larger Table 1 inventory can reasonably continue across pages.

Other findings are optional polish: page 17 contains only the author-declarations paragraph before a forced appendix break; the bold research question splits across pages 1–2 after the word “what”; and the discussion's opening paragraph splits after two lines across pages 14–15. These do not obscure the result. The longer supporting-study discussion and repeated cautions remain possible future cuts, not requirements for this scoped readability revision.

No further substantive prose or graphical objection was identified. This assessment does not certify the statistical analysis, numerical source audit, or author endorsement.

## Final assessment: 25-page reviewer PDF

Visually inspected all 25 final rendered pages in `/private/tmp/thinking-selection-legibility-final/`, corresponding to `latex-v2/output/pdf/main.pdf`. Table 2 now appears intact with its caption on page 9, and Table 3 appears intact with its caption on page 11. The primary failed criteria remain visible before the post-hoc diagnostics. All four figures remain readable at their embedded size, on pages 4, 7, 12, and 14, with their captions attached. Figure numbers and prose callouts agree. I found no clipping, overlap, unreadable chart annotation, or missing figure reference in this final build.

**Verdict:** The revision resolves the substantive readability objections raised in this critique. A reader can now identify the paid-draft decision, the retrospective scored outcomes, the distinction between question folds and draw halves, the separate comparators, and the central negative selection result without reconstructing the research chronology. The wording retains the distinction between post-hoc same-question structure and held-out-question performance. Conditional intervals, failed criteria, scorer-defined correctness, sparse identification, and cost exclusions remain explicit. This is a satisfactory internal reviewer copy from a legibility perspective.

The paper is still dense and could be shorter. Optional future work is to consolidate repeated cautions and discussion passages, shorten the main-text treatment of the sparse/cap follow-ups, and improve minor page transitions. The final build retains the split research question across pages 1–2, an almost empty author-declarations page 18, and generous white space on some float pages. Table 1 continues across pages 5–6 with repeated headers; that is acceptable for an inventory. These are presentation refinements, not grounds to block this scoped revision or remove inference limits.

This verdict concerns the final prose and visual presentation. It does not constitute a new statistical audit, a mathematical scoring audit, human peer review, author endorsement, or a claim about publication readiness. The reviewer changed only this critique file.
