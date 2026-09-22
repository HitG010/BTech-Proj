# Router improvement before the long confirmation run

Research note, 2026-09-22. This is a proposed development path, not a measured
improvement or a novelty claim. It uses only saved responses and published work;
no new generation, fitting, or GPU experiment was run for this note.

## Decision

Develop a **shared-base continuation router** on the existing 200 development
questions, with the current gain-ridge and confidence routers as mandatory
comparators. Defer the 3,100-question run. The prepared confirmation study in
`artifacts/confirmation/frozen-router-v1/` is for the *unchanged* joint router;
its model, protocol, and question allocation must not be silently repurposed for
a revised policy. Its `status.json` remains `prepared`, with generation not
started. The official 500-question test set remains sealed.

## Why the current router needs work

The [100-question continuation diagnostic](../artifacts/probe/continuation-v1/report.md)
gave the joint router 88% accuracy at 728 generated tokens/question. The simpler
gain-ridge router gave 89% at 877; tuned confidence continuation gave 86.5% at
592. At the preselected preference `lambda=0.05` (five percentage points of
accuracy per 1,000 generated tokens),
joint minus confidence utility is +0.008188 with a paired whole-question 95%
bootstrap interval of [-0.020329, 0.044029]. Joint minus gain-ridge utility is
-0.002536. None of this establishes that the joint router is better.

The replay has 100 independent questions, each evaluated in two correlated
first-draft orientations. Across those 200 states, a second direct draft followed
by thinking on disagreement rescued six initially wrong answers and harmed none;
thinking immediately rescued 15 and harmed three. These rare outcome classes
are a difficult target for two separate four-class classifiers trained on only
100 questions. At the primary preference, the joint policy chose accept/probe/
think 65/89/46 times, versus gain-ridge's 54/78/68. Action selection is
sensitive to the fitted model. These are descriptive development observations,
not independent 200-question estimates.

Agreement is useful but unsafe as a certainty rule. In the fresh diagnostic,
89/100 pairs of valid direct drafts agreed, and eight of those 89 agreements were
wrong. One corresponding thinking sample corrected five of those eight, but
verifying every agreement also buys an expensive generation and can damage a
correct answer. In the pilot and validation development sets, only 11 wrong
agreements occur in 200 questions combined. Any model for this event needs
strong shrinkage and careful uncertainty reporting.

Numbers above come from the checksummed [report](../artifacts/probe/continuation-v1/report.json)
and source records named in its [protocol](../artifacts/probe/continuation-v1/protocol.json).
The two orientations were never counted as independent questions for inference.

## First candidate: share the first-answer correctness estimate

The current joint router separately fits four-way outcomes for buying a direct
draft and for thinking now. Both heads implicitly estimate the same event:
whether the already observed first draft is correct. A smaller model should
estimate that event once, then estimate action-conditional rescue and regression
with pooling across actions. For each action `a`:

```text
p0(x)       = P(first answer correct | observed question and first response)
r_a(x)      = P(action a correct | first wrong, x)
h_a(x)      = P(action a wrong | first correct, x)
gain_a(x)   = (1 - p0(x)) r_a(x) - p0(x) h_a(x)
value_a(x)  = gain_a(x) - lambda * E[additional tokens | x, a] / 1000
```

Here `x` contains only fields available after the first direct response.
Estimate the conditional rates with a deliberately small, regularized model and
partial pooling or prior shrinkage; allow an intercept-only fallback when event
counts are too small. Fit costs separately and enforce positive predictions.
The shared `p0` eliminates contradictory estimates of first-draft correctness
from the two action heads. It does **not** create extra rescue examples or make
the factorization original research. Cost, action frequency, and actual utility
matter more than probability fit alone.

Use the same action set and charged-token accounting as the frozen diagnostic:
accept, buy a second direct draft and think on disagreement, or think now. Do
not alter generation settings, parser, or answer caps while attributing changes
to the router. Compare with the original joint model, gain-ridge, a tuned
confidence gate, and the DART SC adaptation under identical cached outcomes.
The current SC adaptation is not DART's full SC-Budget method.

## Second candidate: verify selected direct-draft agreements

After two direct drafts, add a decision to accept agreement or buy a thinking
response. Estimate the *remaining* probability of a wrong consensus and the
conditional chance that thinking fixes or harms it; purchase verification only
when its expected incremental utility is positive. This uses already cached
thinking outcomes for offline replay. It is a separate policy contract with a
second decision point, so charged-token cost must include both direct drafts
and thinking when requested. Measure routing overhead separately in live time.

This is less ready than the shared-base model. Wrong agreements are sparse;
per-question classifiers could overfit badly. Start with a pooled or
intercept-only risk estimate and at most a few predefined features. Report
whether the policy's benefit survives shrinkage and whether it beats the
simple alternative of thinking immediately on low-confidence first drafts.
Do not use the inspected 100-question diagnostic to choose its threshold or
present its eventual replay score as an independent test.

## Development protocol before spending more model compute

1. Pool the existing pilot and validation traces as **development data only**.
   Use question-grouped folds, keeping both direct-draft orientations and all
   responses to one question in the same fold. Fit PCA, scaling, calibration,
   and hyperparameters inside training folds. Restrict the candidate grid in
   advance; 200 questions do not support a broad architecture search.
2. Compare out-of-fold accuracy–token curves and utility at the already chosen
   `lambda=0.05`. Include gain-ridge, joint, confidence, and simple fixed
   actions. Report rescue/harm calibration, action counts, and whole-question
   paired uncertainty; fold-selection scores remain exploratory because these
   data informed the method design.
3. Advance a candidate only if its improvement is robust to reasonable
   shrinkage and question-grouped folds, and it has a credible advantage over
   gain-ridge as well as confidence. Freeze one revised policy and its
   comparators before collecting a **new, disjoint** evaluation sample. Do a
   new power/cost calculation from its observed development effect rather than
   assuming the old 3,029-question estimate applies.
4. Keep the existing prepared confirmation frozen or explicitly retire it in
   the research record. A revised router needs a new protocol. Do not use the
   official test set for further model selection. Include full DART SC-Budget
   and ReASC only after reproducing their actual confidence and budget rules;
   saved mean decoder log-probability is not ReASC's group-confidence signal.

The development comparison and candidate selection need CPU fitting and cached
traces only. There is no
reason to launch the 125–142-hour MPS collection before a better candidate is
selected and frozen.

## Where a research contribution could be

Probability factorization, confidence gating, and buying another draft are
baseline engineering, not standalone novelty. [CARROT](https://arxiv.org/abs/2502.03261)
already predicts quality and cost; [Causal LLM Routing](https://arxiv.org/abs/2505.16037)
trains directly for routing regret; [DART](https://arxiv.org/abs/2606.23181)
uses direct-draft agreement; [ReASC](https://aclanthology.org/2026.findings-acl.1085/)
uses confidence for single-sample gating and evidence accumulation;
[Pandora's Router](https://arxiv.org/abs/2608.20316) prices optional
information; and [Too Consistent to Detect](https://aclanthology.org/2025.emnlp-main.238/)
studies repeated wrong consensus. These papers set a high bar for a novelty
claim. Their reported numbers are from different tasks and protocols and are
not directly comparable with ours.

A potentially distinctive, **still unproven** question is whether a small-data
router can learn the *counterfactual value of changing reasoning mode after
correlated same-model drafts*, while preserving a coherent shared estimate of
first-answer correctness and charging every additional token. The mechanism
would need to beat direct gain regression, calibrated confidence, DART, and
ReASC at matched inference quality/cost on fresh questions, with an ablation
showing that modeling rescue, harm, and wrong agreement actually matters.
If the effect is small or absent, use the stronger router as a baseline and
consider the separate [training-trace acquisition question](router-research-proposal.md)
for a method contribution. Do not claim an edge by exaggerating a development
curve or a weak baseline comparison.
