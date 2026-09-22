# Better routers and a defensible research direction

Literature review: 2026-09-17. This is a research proposal, not an accepted
implementation change, experiment result, or exhaustive novelty clearance.
No code, generation runs, or router training were performed for this review.

## Recommendation

First improve the routing baseline using decision-focused learning and stronger
small-data inductive biases. Then investigate **selective acquisition of
stochastic reasoning outcomes under a training-token budget**. Keep the solver
frozen and deployment question-only for the main study.

A possible paper question is:

> Can we learn when thinking is worth its cost with fewer generated training
> tokens by jointly choosing the question, reasoning mode, and repetition to
> observe, according to their expected effect on future routing decisions?

The novelty would have to reside in a specific acquisition algorithm, its
handling of stochastic quality and cost, and demonstrated improvement over
close acquisition baselines. Neither a new router name nor combining familiar
components establishes a contribution.

## What our evidence does and does not say

The [current study](routing-learnability.md) has 100 questions, two responses per
mode, and 80 training questions in each outer fold. There are 387 input features.
Nineteen of twenty fitted ridge targets selected the strongest regularization.
Ridge has not demonstrated improvement over cost-matched random allocation.

The completed pilot's retrospective per-question averages show thinking better
on 12 questions, direct better on 3, and ties on 85. The sample-estimated oracle
is 94%, versus 92% always-thinking. These quantities use the same noisy outcomes
to choose and score an action; they are not reliable population labels or a
deployable performance ceiling. Cost savings at comparable accuracy may matter
more here than an absolute accuracy increase.

Possible explanations are insufficient data, unsuitable features, noisy targets,
or a weak link between visible question properties and mode advantage. We cannot
select one explanation from this pilot. The modest DART-adaptation result also
does not establish that response-based routing is superior.

## Closest work and the boundary it sets

| Primary source | Relevant idea | Implication for this project |
|---|---|---|
| [RouteLLM](https://arxiv.org/abs/2406.18665) | Learns model selection from preference data. | A learned two-option router is established prior work. |
| [CARROT](https://arxiv.org/abs/2502.03261) | Predicts performance and cost, including nearest-neighbor and learned-encoder variants. | Our four-predictor utility router is a baseline in this family; add a retrieval adaptation. |
| [Causal LLM Routing](https://arxiv.org/abs/2505.16037) | Learns routing through regret objectives and corrects partial observational feedback. | Decision-focused learning and single-action feedback are not independently novel. |
| [Think When Needed](https://arxiv.org/abs/2601.18146) | Uses model-aware features and a compute-adjusted reasoning-advantage target for ranking. | Predicting the benefit of thinking is already explored, even though the task differs. |
| [DART](https://arxiv.org/abs/2606.23181), [reference implementation](https://github.com/js-lee-AI/DART) | Direct-draft agreement and adaptive thinking budgets. | Disagreement routing is a required inference baseline, not our contribution. |
| [Pandora's AI Model Routing Box](https://arxiv.org/abs/2608.20316) | Pays for better value estimates only when useful; includes partial reasoning evidence. | Optional probes and generic value-of-information routing have direct prior art. |
| [Multi-Head Latent Control](https://arxiv.org/abs/2607.14277) | Reads partial hidden-state trajectories of a frozen backbone for control decisions. | A hidden-state probe is a possible feature improvement, not sufficient novelty. |
| [Targeting the Exceptions: authors' repository](https://github.com/wikit-ai/online-active-learning-llm-routers) | Actively builds a retrieval router's support set using predicted performance sparsity. | Active acquisition for router training needs a stronger comparator than random alone. |
| [How Much of the Routing Gap Is Real?](https://arxiv.org/abs/2607.03436) | Separates reproducible advantage from stochastic single-draw oracle effects. | Finding noisy routing labels or an inflated empirical oracle is already studied. |
| [Re-Active Learning](https://ojs.aaai.org/index.php/AAAI/article/view/10315) | Chooses between new examples and independent relabeling. | New-question-versus-repeat acquisition is not new by itself. |
| [Cost-Aware Near-Optimal Policy Learning](https://ojs.aaai.org/index.php/AAAI/article/view/35027) | Studies the resource cost of acquiring observations for a near-optimal contextual policy. | Cost-aware policy acquisition is another direct algorithmic comparator. |
| [Correlation-Aware Contextual Bandits with Surrogate Rewards](https://arxiv.org/abs/2607.09015) | Uses correlated-arm information and potentially misspecified surrogate rewards. | If we add cheap proxy labels, we must compare against this approach rather than claiming surrogate sharing as new. |

These studies use different tasks, models, feedback, and costs. Their reported
numbers do not rank them on our task. Some are recent preprints; inclusion means
relevant prior art, not independent verification of their empirical claims.

## Track 1: make the baseline stronger

### A. Retrieval and shrinkage

Adapt CARROT's nearest-neighbor estimator using the same frozen MiniLM features
and exactly the same acquired observations. Predict each mode's correctness and
cost from neighboring training questions, shrinking estimates toward training
population means when local evidence is sparse. Choose the neighborhood and
shrinkage strength on inner validation only.

This tests whether a local nonlinear relationship is easier to learn than our
global linear predictor. It may also fail if semantic neighbors have different
arithmetic structure. This is an engineering/benchmark improvement, not novelty.

### B. Train for the routing decision

For a question x and cost preference lambda, define

    Delta_lambda(x) = E[Y_think - Y_direct | x]
                      - lambda * E[C_think - C_direct | x] / 1000.

Y is strict correctness and C is charged output tokens. Thinking is preferred
when Delta is positive. A question where both modes perform equally is useful
as evidence for saving compute, not as an arbitrary class label.

Compare the current predictor-MSE approach against a regularized, regret-weighted
classification or soft policy objective, inspired by Causal LLM Routing. Errors
on large utility differences should matter more than errors on near-ties. Use
soft/shrunken outcome estimates and validation calibration, not confident labels
from two samples. Do not blindly upweight rare thinking wins: that can distort
the expected deployment utility.

Test a small, predefined feature-reduction grid, fitted within training folds.
Do not launch a wide neural-architecture search on 100 questions. Simply
regressing the difference is not automatically an improvement: linear ridge
with the same design and regularization is linear in its targets, so subtracting
two un-clipped predictions can equal regressing their difference directly.
The meaningful changes are objective, regularization, representation, or pooling
of evidence. Decision-focused learning itself is prior work.

### C. Model-aware features, only if needed

If both question-text baselines remain weak with more data, test a small probe
over frozen Qwen prompt representations. Alternatively test a direct-prefix
probe. These are different inference contracts: prompt representations incur
prefill work; prefix representations additionally require generated tokens.
Count their compute, and never call them free or compare their cost as though
they were MiniLM-only routers. Partial-output and hidden-state routing already
have close prior work, as the table shows.

## Track 2: candidate contribution—buy the observations that change decisions

The original collector buys direct/thinking pairs. Our proposed collector may
purchase a single mode on a selected question, including an independent repeat.
An expensive thinking sample need not accompany every cheap direct sample.
This matters when one mode's expected outcome is already well estimated.

Maintain a shared, regularized uncertainty model over expected correctness and
cost. It must distinguish uncertainty about the expected mode advantage from
variation in individual generations. Repeating an inherently variable response
does not make that model deterministic; it only improves estimation of its mean.

For each allowable acquisition a = (question, mode), approximate:

    priority(a) = expected reduction in future routing regret after observing a
                  / expected charged generation cost of a.

Critically, estimate regret reduction across a fixed, unlabeled reference pool
from the training distribution. Observing one question may improve decisions on
similar questions. A high current regret on an isolated question is not itself
evidence that resampling it will improve generalization.

For a first prototype, use the existing seeded 512 posterior draws, hypothetical
observation updates, and a small Bayesian linear model or bootstrap ensemble.
For every candidate observation, simulate the revealed outcome, refit/update the
same learner, and estimate how its decisions change across the reference pool
and the fixed cost-preference grid. This is an approximation to expected value
of information; it does not inherit an optimality guarantee merely by using that
name. Never use validation/test labels inside the acquisition score.

The concrete additional modeling question is whether the joint quality–cost
distribution matters. With K = C/1000, utility is Z = Y - lambda K, and

    Var(Z) = Var(Y) + lambda^2 Var(K) - 2 lambda Cov(Y, K).

Generation length and correctness may be associated. A collector based solely
on Bernoulli correctness uncertainty divided by average cost can miss this
interaction. Model or resample (Y,C) jointly within a generated response and
compare against an otherwise identical covariance-ignoring variant. This
variance identity is standard mathematics, not a new theorem. Whether exploiting
it improves acquisition is the empirical hypothesis.

Stop acquiring when the token ceiling is reached, a per-question cap is reached,
or expected benefit is too small under a predefined stopping rule. Preserve the
maximum-token reservation before launching each response. Keep a small randomized
exploration component, log acquisition probabilities and all actual costs, and
test bias from adaptive stopping; do not assume adaptively stopped empirical
means or ordinary confidence intervals remain unbiased/valid.

### What could be claimed, if supported

An algorithm for jointly choosing question coverage, mode-specific replication,
and stopping under stochastic generation costs that improves held-out routing
utility per training token. The closest alternatives above must be adapted and
tested. The review does not establish that this exact formulation is absent
from all prior work. If it reduces to a straightforward existing algorithm with
token costs substituted, frame it as an empirical adaptation, not a new method.

The deployed router remains question-only. Generation-derived information is
used to acquire and train it, not smuggled into deployment features.

Compared with the earlier acquisition proposal, demote trajectory completion
from the main contribution: truncation is now only 1.5% per mode after answer-cap
calibration. Preserve it as an optional ablation if later data justify it.
The sharper changes are mode-specific purchases instead of mandatory pairs,
learning value across questions, and joint stochastic quality/cost modeling.

## Track 3: optional-probe routing as a separate branch

A practical alternative is to decide among immediate direct generation,
immediate thinking, and buying a short probe before deciding. The probe could
be a short direct prefix; after observing it, either continue that direct
trajectory or restart in thinking mode. Learn the value of the probe, not just
the correctness of the partial answer. Charge sunk probe work, continuation,
prefill, and the router itself.

This is a meaningful extension of the question-only study, but Pandora and
latent-control methods already cover much of the idea. A possible narrower
question is whether learned probe length and reuse of the exact same direct
trajectory reduce total cost compared with fixed probes and full DART. Do not
assume a direct prefix can be freely reused in a thinking-mode prompt: that
changes conditioning. KV-cache reuse and stochastic continuation equivalence
need implementation-specific verification.

This branch needs new prefix/state traces and a separate policy contract, so
it is secondary to the cheaper question-only learnability check.

## Experiments that could falsify the proposal

1. Finish the pending human scoring audit, freeze the scorer, and preserve the
   official test set. The pilot is exploratory and has already influenced design.
2. Compare ridge, retrieval/shrinkage and a decision-focused learner on the same
   disjoint training/validation sets and a small predefined configuration grid.
   Use training-size curves to separate inadequate data from weak features.
3. Establish stability with independent response seeds on a training diagnostic
   subset. If selecting a mode from one group of responses fails on independent
   responses to the same question, treat the apparent headroom cautiously. This
   diagnostic is not unseen-question evaluation.
4. Only if a useful signal appears, hold the learner fixed and compare acquisition:
   uniform pairs, random pairs, uncertainty-only, current-regret/cost, a
   re-active-learning adaptation, a cost-aware policy-learning adaptation,
   router-specific active acquisition, and the proposed mode-selective method.
   Use equal charged budgets, at least three independent acquisition seeds,
   and the common charged initial seed set. Acquisition-specific comparisons
   must not receive unrevealed cached outcomes.
5. Ablate mode selection, repeat selection, cross-question information sharing,
   and quality–cost dependence separately. If removing the proposed component
   does not hurt, it is not supported as the source of improvement.
6. Evaluate frozen policies with paired whole-question intervals and a separate
   view of training-seed variability. Report accuracy versus inference tokens,
   held-out utility versus acquired training tokens, latency with all overhead,
   and actual cache-building cost. Include full DART for the inference comparison;
   the current two-draft adaptation is insufficient to claim a DART improvement.

We should also report amortization: for a common quality target, if training
costs T extra tokens and deployment saves s tokens per question relative to a
baseline, the token-only break-even volume is T/s when s > 0. This is accounting,
not novelty, and excludes CPU time unless modeled separately. A trained router
may be inappropriate for low deployment volume even when its per-query curve
looks good.

If only the stronger learner wins, report a baseline improvement. If acquisition
wins at equal data-generation cost across seeds and a second predefined task,
we have evidence for the intended method contribution. If neither wins, retain
the negative result and do not manufacture novelty through benchmark selection.

## Recommended reading order

Start with CARROT and RouteLLM for the basic estimation/selection problem.
Then read Causal LLM Routing for the difference between prediction loss and
decision regret, and DART for the strongest directly relevant training-free
comparison. Read the routing-gap paper before interpreting empirical oracles.
For the proposed acquisition contribution, read Re-Active Learning, Cost-Aware
Near-Optimal Policy Learning, and the Targeting the Exceptions implementation.
Read Pandora and Multi-Head Latent Control if pursuing the optional-probe branch.
