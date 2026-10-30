# Phase 1: cascade reframing

Date: 29 October 2026. Manuscript: [v0.4](manuscript.md), revised from v0.3 at
`15f5b3c`. Plan: Phase 1 of the
[project review](../../docs/project-review-and-publication-plan-2026-10-29.md).

This pass changes framing and related work only. It runs no experiment,
fitting, scoring, or statistical analysis. It opens no raw response, score
cache, reference answer, or sealed role. All tables, Box 1, figures, captions,
display equations, and appendices are byte-identical to v0.3 (checked by
script). The LaTeX reviewer copy in `latex-v2/` still reflects v0.3.

## 1. The reframed claim

**One sentence.** Escalating from a paid direct draft to a fresh thinking
solve is a two-stage cascade whose stages are the same model. On GSM8K, none
of the tested learned post-hoc deferral rules established an improvement over
its simple confidence-based or training-selected comparator on held-out
questions, and the value of confidence deferral itself differed sharply
between Qwen3-0.6B and Qwen3-1.7B.

**Title adopted in v0.4.** *Learned Deferral Did Not Beat Confidence When
Escalating to Thinking: A Same-Model Cascade Study of Small Qwen3 Models on
GSM8K.*

The title is a summary, so check one nuance before endorsing it. The primary
learner's comparator was selected within training from accept, escalate, and
confidence, not confidence alone. The 0.6B development learner had a positive
point estimate against confidence (+.003516, interval [−.031959, +.037163])
but failed its criteria. "Did not beat" is accurate in the sense of the
predeclared criteria. Alternatives:

- *When Escalating to Thinking, Learned Deferral Did Not Beat Confidence: A
  Same-Model Cascade Study of Small Qwen3 Models on GSM8K*
- *Is Confidence Enough to Decide When a Hybrid Model Should Think? Evidence
  from a Same-Model Cascade*
- *Tested Learned Deferral Rules Did Not Improve on Confidence for Escalating
  Small Qwen3 Models to Thinking*

**Three findings** (Introduction, v0.4):

1. Learned deferral did not use the observed opportunities: 30 rescues and
   10 harms in 400 pairs, and a failed primary learned rule on held-out
   questions, despite some post-hoc question-level gain variation.
2. Three plausible improvements also fail: capacity and compression, a compact
   contrastive objective, and released contrastive representations with a
   matched-encoder control.
3. The value of the cascade depends on the solver, and narrow follow-ups add
   little: confidence deferral helps 0.6B and lowers point utility for 1.7B;
   the guard and cap follow-ups each produce at most one rescue.

These replace the v0.3 list. The v0.3 scorer-bound finding is kept as the last
sentence of finding 1.

## 2. Term mapping

| Project term (v0.3) | Cascade term (v0.4) |
|---|---|
| Direct mode, direct draft \(D\) | First stage and its output |
| Fresh thinking solve \(T\) | Second stage (same model, thinking mode) |
| Selector, router, policy | Deferral rule |
| Escalate, \(a=1\) | Defer |
| Incremental gain \(G\) | Cost-adjusted gain from deferring |
| Escalate when \(E[G\mid x,D]>0\) | Optimal deferral rule, cost-adjusted form |
| Confidence threshold | Confidence-based deferral (Chow-style rule) |
| Combined Ridge on question and draft features | Post-hoc deferral rule |
| Rescues and harms | Hindsight deferral opportunities and losses |

Figure 1 is frozen and still says "selector"; the Section 3.1 callout now
links that word to "deferral rule". The equations are unchanged. The new
Section 3.1 paragraph states that, because utility is linear in the action,
a rule that knew the expected gain would escalate exactly when it is positive.
This is elementary decision theory, presented as paralleling the optimal rule
of Jitkrittum et al., not as a result taken from their paper.

## 3. Novelty boundary

Already established, so not claimed:

- **Confidence-gated thinking in hybrid models.** Lewis-Lim et al.
  ([arXiv:2510.21007](https://arxiv.org/abs/2510.21007)) gate chain of thought
  on direct-answer confidence, compare training-free measures with random
  gating and an oracle, and find that the best measure varies by dataset and
  model. This is the closest prior work to the confidence rule.
- **Deferral after observed drafts.** DART v4.
- **Mode choice before generation.** Self-Route.
- **When confidence deferral suffices.** Jitkrittum et al., NeurIPS 2023.
- **Length bias of sequence-level confidence and token-quantile deferral.**
  Gupta et al., ICLR 2024.
- **Repeated supervision, contrastive routing, failure risk versus action
  value.** RouterDC, CSCR, Chen 2026, Yang et al. 2026.

The paper's addition is therefore a measured case: learned post-hoc deferral
evaluated with repeated draws, held-out question folds, and a cost charging
both calls, read against the cascade analysis. The search on 29 October 2026
found no paper that evaluates *learned* deferral against confidence in a
same-model direct-to-thinking cascade with repeated draws. That is a
search-based observation, not a priority claim.

## 4. Retrieval limits and what to read before submission

The session network policy blocked arxiv.org, openreview.net,
proceedings.neurips.cc, and proceedings.iclr.cc. Every new source was
therefore checked through abstracts, official listings, and secondary
summaries returned by web search. **No new full text was read.** The
manuscript's statements about these works stay at the level of their
abstracts. Before submission, read the full texts and check:

| Source | What to confirm |
|---|---|
| Jitkrittum et al. 2023 | The exact statement of the optimal deferral rule (reported as Proposition 3.1), the precise conditions under which confidence-based deferral is optimal, and how the label-noise case works. Section 6.1's "label noise analogue" relies on the summary that confidence sends noisy samples to a second model that also fails |
| Gupta et al. 2024 | Which quantiles and features the post-hoc rule uses, the model class (reported as small MLPs), and whether the length-bias finding applies to *mean* (length-normalized) log probability, which is our feature, as well as to the sum |
| Lewis-Lim et al. 2026 | Exact models (whether Qwen3 is in the experiments, not only named), datasets, the four confidence measures, the cost metric, whether any learned gating is compared, and the current version and venue |
| Fanconi and van der Schaar 2025 | That the first stage is a confidence-based accept-or-regenerate decision |
| Self-Route, AutoMix, Yue et al., FrugalGPT | The one-sentence descriptions in Section 2 |

All new BibTeX entries carry a note recording this limit.

## 5. Analyses this framing calls for (Phase 2)

The reframing exposes four cheap checks on cached data. Each needs its own
frozen plan, per project practice. None was run here.

1. **Is confidence monotone in expected gain?** Bin the repeat-panel states
   by confidence and estimate the mean gain per bin with question-grouped
   intervals. A threshold rule can approach the optimal rule only if lower
   confidence means higher expected gain. This directly tests the premise of
   Section 3.1.
   *Status 2026-10-30:* done ([results](../../docs/confidence-gain-shape-results.md)).
   The premise holds for Qwen3-0.6B but not for Qwen3-1.7B: only the lowest
   confidence tail benefits on the repeat panel, and no threshold helps on the
   two-solver panel. Added to the manuscript as Section 5.2 and Table 5 (v0.5).
2. **Token-level quantile deferral (Gupta et al.).** Recompute per-token log
   probabilities for the cached direct drafts by teacher forcing. Evaluate
   quantile thresholds and one learned rule on the same folds and halves.
   *Correction 2026-10-30:* records do store `answer_token_ids`, so no
   re-tokenization is needed. *Status:* protocol, script, and tests are ready
   ([protocol](../../docs/token-deferral-protocol.md)); not yet run.
3. **Where does confidence spend escalations?** Among low-confidence drafts,
   count rescues versus both-wrong pairs. This is the label-noise analogue in
   Section 6.1.
4. **Deferral curves.** Accuracy versus tokens for all rules, with
   always-direct, always-think, cost-matched random, and the hindsight oracle
   (97.0% accuracy from Figure 1's counts, (348 + 10 + 30)/400; it is not a
   deployable rule).

## 6. What did not change

- Every reported value, interval, criterion, and decision.
- Sections 3.2–5.4, apart from the Section 4 heading (now "Learned deferral
  on the repeat panel"), one clause in Section 3.4, and two sentences in
  Section 5.1. Section 3.1 gains one paragraph and one callout clause.
- Author declarations, the AI-assistance disclosure, and the deferred author
  and venue details.
- All frozen study files, sources, figures, and the `latex-v2/` package.
