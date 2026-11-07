# Critic reviews, 7 November 2026

Two AI critic reviews of the short paper as drafted on 2 November (line numbers
refer to that version of `main.tex`):

- [critic-methods-2026-11-07.md](critic-methods-2026-11-07.md): methods and
  claims. Soundness 3/4, overall 6/10 at a workshop.
- [critic-framing-2026-11-07.md](critic-framing-2026-11-07.md): framing,
  related work, presentation, venue. Overall 5/10 now, about 6/10 after fixes.

## Applied on 7 November 2026

The must-fix items, all text changes in `main.tex`:

1. Evaluation sentence: fitted on draws 0–3 of the 40 training questions,
   evaluated on draws 4–7 of the 10 held-out questions, and vice versa;
   "state" defined as a draft–thinking pair.
2. Qwen3-0.6B: lead with the 6.2-point lift over random escalation; say that
   always thinking already gains +0.128 over accepting the draft and confidence
   leads always thinking by +0.025 (no interval).
3. Refit conclusion scoped to the predeclared learner; follow-up rules were
   not refitted.
4. Table 1 gains the training-selected comparator and the draft-only and
   question-only Ridge rows from Figure 1A (values from the deferral-curve
   report); the text notes that draft features alone, including confidence,
   also lose.
5. Abstract and contribution paragraph rewritten from the framing critic's
   text; oracle share given as 17.6% throughout; utility scale explained once.
6. Plainer terms: "main panel", "state", "success criteria", "follow-up
   rules", "intervals that include refitting"; the combined learner in
   Figure 1 is named as the predeclared learner.
7. Anonymous author block, no draft date, no spending line; a code and data
   availability statement with licences; the technical report reference is
   safe for anonymous review. The AI-assistance sentence is unchanged.

Not done: must-fix 8 (read the full texts of Jitkrittum et al., Gupta et al.,
Lewis-Lim et al., and Fanconi and van der Schaar; the session network blocks
arXiv). Section 4's cascade-conditions paragraph now says "on our reading".
The should-fix items in both reports remain open.
