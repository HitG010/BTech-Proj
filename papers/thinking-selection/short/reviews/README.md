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

## Should-fix items applied on 9 November 2026

- Table 1: escalation column, grouped rows, plain row names, integer tokens
  (framing P1-2). Accuracy keeps two decimals because every value is a multiple
  of 0.25 points; one decimal would round half the rows.
- Effective sample: 11 questions carry the 30 rescues, 14 carry any rescue or
  harm; the introduction frames the 40-question setting (methods 6, framing P1-1).
- Oracle caveat in the abstract and Section 4 (methods 7); refit shrinkage and
  the +0.01 margin in Section 3.3 (methods 5); the comparator's −0.028 as
  evidence of selection noise (methods 9).
- Fairness disclosures in Appendix A: CLM rules see no confidence or draft
  statistics; compact neural rules see the last 256 draft tokens (111 of 400
  truncated) with one seed; token quantiles are pre-warper (methods 8, 9).
- Restored findings: 1.7B two-solver agreement +0.008 over confidence;
  between-question variance (results do not show deferral is unlearnable);
  mixed September agreement results (methods 10). Agreement's +1.40 lift in
  Section 3.2 (methods 11). Section 3.2 retitled (methods 12).
- Limitations: contamination, fewer than nine rescue questions per fold, one
  prompt and decoding configuration, unequal compute across model sizes, no
  multiplicity adjustment (methods 13).
- Bibliography: FrugalGPT now TMLR 2024 (OpenReview), BEST-Route ICML 2025
  (arXiv comment), Lewis-Lim et al. dated to first posting (2025), CLM model
  card cited (framing P1-5). Thinkless has no stated venue and stays a preprint.
- Appendix B removed and Appendix C shortened (framing P1-6); the
  availability statement now names the cache SHA-256 and says which values the
  195 checks cover.

Not done, by decision:

- Title scope ("…on GSM8K"), suggested by methods 12: the authors' call.
- A learning curve over 1, 2, and 4 training draws (framing P1-1): the tracked
  records do not report those conditions in a citable form; it would need a new
  cached analysis under its own frozen protocol.
- The Figure 1 caption keeps "post-hoc, from reused development panels" rather
  than the shorter wording framing P1-3 suggests.
- P2 polish items in both reports, except where they overlapped the above.
- The long report still omits agreement's lift in its Section 4.5 sentence
  (methods 11); it was left at v0.8.
