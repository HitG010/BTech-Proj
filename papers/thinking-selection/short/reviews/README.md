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

8. Citations checked against their full texts, done from the Mac the same day
   because the cloud session could not reach arXiv. See the
   [record](../../full-text-check-2026-11-07.md). Section 4's cascade paragraph
   was rewritten and split, and the Lewis-Lim et al. description corrected.

## Applied on 9 November 2026

- Figure 1 revision 2 (framing P1-3): see [`figures/plan-r2.md`](../figures/plan-r2.md).
- Related work (framing P1-4): 30 added sources in five paragraphs (learning to
  defer and selective prediction, cascades and routing, adaptive thinking,
  confidence and agreement, evaluation). Each was checked against its arXiv
  record (title, authors, abstract) or, for Narasimhan et al. 2022, OpenAlex.
  Venues appear only when the arXiv comment or OpenAlex states one; eight are
  cited as preprints. Skipped from the critic's list: RouterBench, faster
  cascades via speculative decoding, token-budget-aware reasoning, Nadeau and
  Bengio 2003, and Dodge et al. 2019.
- Bibliography (part of framing P1-5): Qwen3 and other long author lists
  shortened in the short paper; SBERT and MiniLM now cited.
- Limitations: untested confidence measures, the thinking call never seeing the
  draft, and the GSM8K caveat, each tied to the new citations.

The other should-fix items in both reports remain open.
