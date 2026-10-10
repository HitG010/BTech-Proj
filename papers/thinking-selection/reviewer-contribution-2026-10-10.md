# Independent contribution review — 10 October 2026

**Assessment:** the current draft supports a careful, narrow empirical case
study. It has not yet established a distinct general scientific result. The
independent-draw design improves the credibility and scope of its negative
comparisons, but a sound procedure is not by itself a new finding. The most
promising contribution is the measured separation between observed thinking
opportunities, limited same-question repeat structure, and unsuccessful learned
selection on unseen questions.

This review used the manuscript, literature notes, and tracked
[repeat result record](../../docs/phase-2-repeat-results.md). It opened no raw
project response, cached outcome file, reference answer, or model asset and ran
no experiment or analysis. Primary papers were read on 2026-10-10. The
assessment below distinguishes verified overlap from reviewer inference.

## Verified overlap with the closest papers

| Primary work | What its full text establishes | What remains distinct here |
|---|---|---|
| [Chen, v3](https://arxiv.org/html/2607.03436v3), especially Sections III–VII and Appendix C | Separates stochastic single-commit ceilings from hindsight unions; audits scorer, coupling, pool, and finite-draw sensitivity. Appendix C also evaluates a learned policy on held-out questions using repeated archived outcomes, while acknowledging historical exposure. | A draft-conditioned two-action policy, independent response halves, and the particular failed learner/control comparisons. Repeated outcomes, held-out fitting, and hash-bound audits are not unique ingredients. |
| [Garg and Sagtani, v1](https://arxiv.org/html/2605.07395), Sections 3, 5, and 8 | Examines judge, truncation, and formatting artifacts and investigates router collapse with random-feature, shuffled-label, and balanced-objective checks. | The narrow fixed-policy parser bounds and matched cap intervention can refine this specific failure record. Parser effects and failed routers alone are already covered. |
| [Yang et al., v1](https://arxiv.org/html/2608.14927), Sections 2–5 and Appendices A/B | Holds the solver fixed, compares confidence with learned/frozen routers, and separates failure-risk prediction from protocol payoff. Includes post-answer probes. Outcomes are one deterministic realization per problem/protocol pair. | Independent stochastic draw halves and the same-question versus unseen-question distinction are concrete differences. “A wrong answer does not imply profitable escalation” and “confidence can beat elaborate routers” are not new findings. |
| [DART, v4](https://arxiv.org/html/2606.23181v4), Sections 2.2, 4.2 and Appendix E.1 | Already observes direct drafts, accepts an extracted answer or requests fresh thinking, and reports supervised-router failures. It uses two drafts and adaptive budgets; main results are single-run. | One observed draft, fixed-budget utility, and repeated-draw learner evaluation differ. Post-draft routing itself is not a distinctive contribution. No faithful DART comparison exists in this project. |
| [RouterDC](https://arxiv.org/html/2409.19886v1), Sections 3.2 and 4.1 | Averages repeated open-ended solver outputs to supervise contrastive model selection. | Testing transfer across independent halves in this particular accept-or-think contract is different; using repeated supervision or contrastive routing is not new. |

An additional nearby source is
[Fowler et al., *The Capability Frontier*](https://arxiv.org/html/2606.26836),
Sections 3–4. It models independent generations and distinguishes expected
performance from maxima of noisy outcomes. It is relevant if the revised draft
emphasizes stochastic headroom or sample noise. I did not reproduce its
calculations or verify its broader empirical headline. It should not become a
claim that the present study supplies a new oracle correction.

## Ranked weaknesses

1. **The main contributions currently name procedures, not a discriminating
   result.** A fixed contract, independent halves, controls, and an audit package
   explain why to trust the findings. They do not say what was learned that the
   closest papers leave unresolved. The current central message largely
   corroborates Yang et al.'s risk/value mismatch in a smaller setting.

2. **The strongest existing diagnostic conjunction is absent from the draft.**
   The tracked repeat report has a signed between-question variance estimate
   of .03233, post-hoc conditional 90% interval [.00541, .06530], and
   same-question A→B/B→A utility gains of +.04413/+.01572. These coexist with
   the negative unseen-question learner comparison. That is more informative
   than reporting only rescues and failed screens. It still does not prove
   stable generalizable signal: the predeclared reproducibility interval
   crosses zero, transfer is asymmetric, and its acquisition cost is omitted.
   These outcomes concern repeated question distributions, not repeated
   thinking draws conditioned on one identical direct draft.

3. **The negative recipes have several unresolved explanations.** Fifty groups,
   high initial feature dimension, truncation, one neural optimization seed,
   and a specific quantized transfer recipe limit interpretation. The bounded
   controls narrow plausible implementations; they do not identify why
   supervised selection fails or establish a failure of representation
   learning. Fixed-policy intervals omit refitting and research selection.

4. **The evidence sequence is broad in procedures but narrow in independent
   scientific support.** Hundreds of fits reuse the same 50 questions. The
   64-question solver diagnostic is informative, but does not test a population
   size interaction. One fresh guard event and one cap rescue cannot serve as
   broad confirmation of the repeat-panel explanation. They are secondary
   boundary checks, not independent replications of one central hypothesis.

5. **Scoring robustness is only partly addressed.** The existing fixed-policy
   parser bounds are useful: the five flagged presentation candidates cannot
   change the four-draw point contrast, and the sixth cannot improve it. This
   excludes those cases as a reversal explanation, with actions/costs fixed.
   It does not exclude unflagged scorer errors, refitted-policy changes, or
   mathematical errors; the human audit was waived. The stronger statement
   “formatting does not explain the failure” would be unsupported.

6. **There is no contemporary external system comparison.** This is not fatal
   to a scoped empirical paper, but prevents claims that the reported failures
   describe the strongest available thinking selectors. DART is operationally
   close enough that the distinction must be concrete. Contrastive-head and
   cost/accounting controls do not substitute for such a comparison.

## Candidate central claim

> On a fixed 50-question GSM8K/Qwen3-1.7B panel, scored thinking rescues and a
> post-hoc estimate of question-level gain heterogeneity coexist with asymmetric
> same-question transfer across draw halves. Yet the predeclared learner and
> bounded capacity, objective, and transfer controls do not improve utility on
> held-out questions and independent response draws beyond their specified
> simple comparators. The flagged presentation cases alone cannot reverse the
> fixed primary point comparison.

This wording states a measured tension. It does not assert that additional
supervision is generally useless, that all signal is noise, that a specific
cause has been identified, or that the design is first. Its scientific value
would be an explicit example of the gap between detecting repeatable structure
on measured questions and learning an action rule for new questions. That
general distinction is familiar; the added evidence is local to this protocol.

## Recommendation and remaining gaps

Reorganize the manuscript around the three evidence levels: observed rescues,
post-hoc within-question repeat diagnostics, and held-out learned selection.
Label their different endpoints and conditioning together. Use the existing
fixed-policy parser bounds as a narrow robustness argument. Keep the two-size
diagnostic and sparse/cap follow-ups as supporting scope checks. This can be
done from existing tracked result records, without reopening studies.

**Reviewer inference:** this organization yields a more useful empirical case
study than the current catalogue of failed recipes. It still does not establish
a substantial new general result or a publication outcome. A stronger claim
would need separately prospective evidence that distinguishes a mechanism or
shows the tension across another setting; this review authorizes no such work.

The literature check is targeted, not exhaustive. It cannot establish priority.
DART's full v4 HTML is now accessible, superseding the earlier abstract-only
retrieval limit for this review. No missing acquisition supplement was resolved.
The CLM author blog remains unverified beyond the accessible release materials;
it must not be presented as a checked peer-reviewed paper. Primary-paper designs
were inspected, not independently reproduced. No manuscript file was edited.
