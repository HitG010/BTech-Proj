# Full-text check of the cascade citations, 7 November 2026

This closes the check listed in the
[reframing record](cascade-reframing-2026-10-29.md#4-retrieval-limits-and-what-to-read-before-submission)
and must-fix item 8 of the [critic reviews](short/reviews/README.md). The cloud
sessions could not reach arXiv; this was done from the author's Mac.

The reading was targeted at the claims we make, not cover to cover. It is an
AI-assisted check, so the authors should still read the first three sources
themselves before endorsing Section 4 of the short paper. It changed no study,
number, table, figure, or equation.

## What was checked

| Source | Version and parts read | Confirmed | Corrected in our text |
|---|---|---|---|
| Jitkrittum et al. 2023 | arXiv v2: introduction, Sections 3.3–4.4 | Proposition 3.1 (optimal rule depends on both models); three settings where post-hoc rules help; our learner is close to their Diff-01 estimator | "Improve on confidence *mainly* when" had no support. We omitted Lemma 4.1 and their two caveats on when post-hoc rules may not help. See below |
| Gupta et al. 2024 | arXiv v1: Sections 3–4, post-hoc model appendix | Length bias; learned deferral on quantiles performs best, on FLAN-T5 models | Averaging *over-corrects* toward short outputs, so our mean confidence is their Chow-Average, not simply "length-biased". Their rule is a five-layer MLP predicting "large right, small wrong" on accuracy tasks, which we did not reproduce |
| Lewis-Lim et al. 2026 | arXiv v3 (8 January 2026): method, evaluation, results; released `analysis/budget_analysis.py` | Confidence gating, random and oracle references, dataset and model dependence. Qwen3-8B/32B, GPT-OSS-20B, GPT-5.1; seven benchmarks including GSM8K | See below |
| Fanconi and van der Schaar 2025 | arXiv v3: abstract, introduction, framework overview | Base answer, verification, regeneration by a larger model, abstention to a human. "Accept-or-regenerate before human escalation" stands | None. NeurIPS 2025 per OpenAlex |
| Self-Route (He et al. 2025) | arXiv v1: abstract, router section | Linear router on hidden states from a pre-inference stage | None |
| AutoMix | arXiv v5: abstract | Self-verification and a POMDP router; NeurIPS 2024 | None |
| Yue et al. 2024 | arXiv v3: abstract | Answer consistency as the deferral signal; ICLR 2024 | None |
| FrugalGPT | arXiv v1: abstract, cascade section | Learned scoring function and router | None |

## Corrections that change the argument

**"The cascade conditions were absent" was too simple.** Three things were
missing from it.

1. Lemma 4.1 gives the actual condition: confidence traces the optimal deferral
   curve when it orders inputs the same way as the gain from deferring. Our own
   [confidence–gain audit](../../docs/confidence-gain-shape-results.md) suggests
   an analogue holds roughly for Qwen3-0.6B and not for Qwen3-1.7B. So we have no
   reason to call confidence near-optimal on the larger solver. The hindsight
   oracle still overstates the usable headroom, because it sees the realized
   thinking response.
2. Their label-noise mechanism is both models failing on *low-confidence* inputs,
   which wastes deferrals. That matches the 1.7B two-solver panel, where 10 of
   the 13 both-wrong pairs sit in the two lowest bins. The short paper mentioned
   only the main panel, where 8 of 12 sit in the highest bin.
3. "Not specialized on an identifiable subset" went further than our evidence.
   On the 1.7B two-solver panel, 12 of the 18 thinking responses that hit the
   reasoning cap are wrong, against 4 of the other 110
   ([diagnosis](../../docs/qwen17-diagnosis-results.md)). A rule cannot see a cap
   hit before paying for thinking, and we did not test whether features predict it.

Their caveats fit better than the "absent conditions" story: post-hoc rules may
devolve to plain confidence deferral when the second model's outputs are not
strongly predictable, and their excess-risk bound (Lemma 4.2) has an estimation
term that shrinks with the fitting sample. Our predeclared reproducibility test
of question-level gain did not pass, and each fold trains on 40 questions. This
remains an interpretation that we did not test directly.

**Lewis-Lim et al. do not simply "beat random gating".** For Qwen3-8B and GPT-5.1
no measure consistently beats random across budgets, and mathematical tasks such
as GSM8K show limited benefit. Three related points:

- Their direct mode outputs only a final answer, whereas our direct drafts average
  221 tokens, so the settings are not directly comparable.
- Held-out evaluation is not something we add over them: their Pareto analysis
  sets thresholds on a calibration split.
- Charging both calls is a real difference. Their released code uses
  `np.where(use_cot, c_len, d_len)`, which counts only the reasoning response when
  a query is routed to reasoning.

## Still open

- **Venues.** arXiv does not state Gupta et al.'s ICLR 2024; a FrugalGPT journal
  version is unconfirmed. Thinkless and BEST-Route were not part of this check.
- **Token-level target.** Our primary token-level score predicts draft error, while
  Gupta et al. predict "large right, small wrong". Both papers now state this. A
  closer test would be a new cached CPU analysis under its own frozen protocol. It
  would have only 30 positive states, so it would be weak, and it is not required.
- **Related work.** Done 9 November 2026: Jiang et al. 2025 and Chuang et al.
  (confidence tokens) are now cited, with the rest of the
  [framing review's](short/reviews/critic-framing-2026-11-07.md) list; see
  [reviews](short/reviews/README.md). Yue et al. 2025 is a survey, so the short
  paper cites Sui et al. 2025 instead.
