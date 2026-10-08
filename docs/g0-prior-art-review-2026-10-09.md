# G0 prior-art review: acquisition for a confidence threshold

Date: 2026-10-09. Review branch observed: `codex/confidence-acquisition-plan`,
HEAD `a68a27a`; initial `git status --short --branch` was clean. The sibling
worktree and detached legacy checkout were present as recorded in `AGENTS.md`.

**Decision: proceed, if useful, as an empirical adaptation. A distinct method
contribution is unsupported.** The October 8 [focused plan](novelty-plan-2026-10-08.md)
did not specify a purchase rule sufficiently precisely to establish
algorithmic non-equivalence. The subsequent [algorithm specification](g0-threshold-algorithm-2026-10-09.md)
defines an adaptation whose ingredients have close predecessors. G1 may
test a frozen adaptation and its mechanism; passing simulation screens cannot
turn this review into proof of priority.

This additive review accessed planning documents, primary papers, authors'
public repository metadata, and selected algorithm source files. It accessed no
external response datasets, project outcomes, references, model assets, or
sealed roles. No downloaded source was imported or executed. Temporary public
source copies were stored under `/private/tmp/g0-prior-art-20261009/`. No
experiments, old executors, model calls, or commits were performed.

## Retrieval and fidelity record

| Item | Material actually inspected | Unresolved retrieval boundary |
|---|---|---|
| L1 | AAAI nine-page full paper, Algorithms 1–3, cost/noise assumptions, guarantee discussion; pinned `alg.py` and adaptive information-gain code in `simulation_rideshare.py`. | The paper refers to a separate proof appendix which is absent from the retrieved nine-page proceedings PDF. Searches of the proceedings, author publications page, and repository did not locate it. Its detailed constants/proofs remain unverified. |
| L2 | AAAI eight-page full paper, impact algorithm, expected/optimistic variants, pseudo-lookahead, threshold theorem statement, implementation restrictions and runtime discussion. | Separate supplementary proofs are referenced but were not recovered through the proceedings or author-hosted discovery paths. Do not claim independent proof verification. |
| L3 | [arXiv v1 full text](https://arxiv.org/html/2503.07824v1), including setting, TaS-FG, and appendices C/D on lower bounds, tracking, stopping and sample complexity; pinned algorithm/model/optimizer code. | Proceedings PDF direct retrieval failed. The identified arXiv version supplies the accessible full algorithm and appendices; no claim that its bytes equal the proceedings PDF. |
| L4 | Author README and pinned selection, learner, and router source. | No full paper or supplement was located by exact-title searches, ACL discovery, or repository inventory. EMNLP 2026 Findings status is author-reported in the repository, not independently established from a proceedings record. |
| L5 | [arXiv v2 full text](https://arxiv.org/html/2505.16037v2), Sections 2–3 and appendices A/D, including assumptions, estimator and surrogate proofs. | No code was required to establish the estimator/assumption mapping. This review does not reproduce empirical claims or certify general neural optimization convergence. |

Thus this is sufficient to reject an unsupported novelty claim and specify
transparent controls. It does **not** complete every requested supplement
equivalence check. Those access gaps must be closed before describing G0 as an
exhaustive proof/implementation audit or publishing a priority claim.

## Exact overlap and limits

### L1: cost-aware near-optimal policy learning

The setting receives IID contexts and observes the selected action's stochastic
reward. Acquisition costs are known, deterministic and positive. Static S-P
cost uses feature uncertainty divided by cost. Adaptive IG cost selects
information about the current context's optimal action per cost (Equation 5,
Algorithm 3). The algorithms run for a specified number of observations; the
paper reports conditional near-optimal-policy guarantees with bounded cost
ratios, not minimum acquisition cost. [Full paper](https://ojs.aaai.org/index.php/AAAI/article/view/35027/37182).

Released `SP_cost.pi`/`pi_offline` square the quadratic feature uncertainty,
whereas Algorithm 1 uses the quadratic itself divided by cost. The adaptive
code computes the joint posterior distribution of the optimal action and
binary outcome, then its mutual information/cost. Preserve the discrepancy;
do not label a silent code transplant a faithful paper reproduction.
[Pinned static source](https://github.com/joyheyueya/cost-aware-policy-learning/blob/58b4bc462f71275faef231cf5a4f89a1db7aa4ce/alg.py),
[pinned adaptive source](https://github.com/joyheyueya/cost-aware-policy-learning/blob/58b4bc462f71275faef231cf5a4f89a1db7aa4ce/simulation_rideshare.py).

Our selectable pool, global best threshold and stochastic token reservation
are extensions of its contract. They do not establish a new information-per-cost
principle. Use a named adaptation, as specified below.

### L2: re-active learning

L2 purchases another noisy annotation or a new example at fixed unit cost to
learn a latent binary concept. Algorithm 1 evaluates hypothetical labels by
the fraction of predictions that change; EXP averages by label probabilities,
OPT takes maximal impact. Pseudo-lookahead forces an aggregate-label change
and divides by the annotations needed to produce it. Main-text implementation
restricts candidates to two or seven recommendations. Its noiseless
one-dimensional threshold equivalence requires separability, uniform inputs
and monotonic prediction probabilities. It supplies no token-budget guarantee
for stochastic solver utility. [Full paper](https://ojs.aaai.org/index.php/AAAI/article/view/10315/10174).

Our correctness draws are real response variability, rather than noisy reports
of one latent thinking answer. Majority relabeling would change the estimand.
An expected change in threshold decisions after a hypothetical utility draw is
a useful **utility-impact adaptation**. It should retain the purchased-only
posterior, measure pool-weighted action changes, and disclose any omission of
pseudo-lookahead and candidate restrictions. New-versus-repeat selection and
threshold specialization cannot supply priority by themselves.

### L3: pure exploration with feedback graphs

TaS-FG identifies the best stationary vertex with fixed confidence. Its model
uses independent reward draws from one-parameter exponential families and
Bernoulli graph activation. It estimates means/graph, tracks an optimal
allocation with forced exploration, and stops through a generalized likelihood
ratio. Appendix D supports correctness and asymptotic sample-count optimality.
[Full algorithm and appendices](https://arxiv.org/html/2503.07824v1#S4).

The pinned implementation supports Gaussian reward models and characteristic
time optimization. It has no token-cost objective or finite-cache repeat limit.
[Pinned model](https://github.com/rssalessio/Pure-Exploration-with-Feedback-Graphs/blob/485e47990a5f0a72a6dca78cb103cff015137b2c/baifg/model/reward_model.py),
[pinned optimizer](https://github.com/rssalessio/Pure-Exploration-with-Feedback-Graphs/blob/485e47990a5f0a72a6dca78cb103cff015137b2c/baifg/utils/characteristic_time.py).

A purchased state outcome is not an independent draw from each threshold's
population reward: its distribution depends on the chosen state and the
threshold values are correlated transformations of the same observation.
Vertices-as-states also fail because the target is a weighted sum policy,
rather than the state with greatest gain. A structured observation or
combinatorial identification extension is required. Do not import TaS-FG's
guarantee into a fixed-token heuristic or claim one response updating multiple
thresholds is new.

### L4: targeting exceptions in active retrieval routers

The author repository describes streaming acquisition for a retrieval support
corpus using predicted performance sparsity. The pinned selector learns KL
divergence from uniform over model performances, compares predicted KL with a
percentile of selected KL values, and updates on selected items. It has an
annotation-count budget, cold start and degraded-validation-loss guardrail.
[Author record](https://github.com/wikit-ai/online-active-learning-llm-routers/tree/73cbd7e7edaa83c407ac643b6f1e09ae4b15fbcb),
[selector](https://github.com/wikit-ai/online-active-learning-llm-routers/blob/73cbd7e7edaa83c407ac643b6f1e09ae4b15fbcb/src/sampling_strategies/sparsity_learning/base_inferred_sparse_performance.py).

`should_select` computes true KL from `item["models_performance"]` before the
decision. The usual prediction branch does not use it in its decision; cold
start/guardrail are unconditional and selected updates use it. This is an
interface exposure, not evidence here of outcome-dependent selection. Our
simulator must segregate hidden outcomes until purchase.

The target, representation, stream and annotation-count contract differ from
our global threshold and thinking-repeat contract. Active routing acquisition
is nevertheless direct prior art. No faithful full-paper comparison or theory
claim is possible without the missing paper; treat it as an external system
reference, rather than inventing a matched threshold reproduction.

### L5: causal LLM routing

L5 learns from IID observational records containing the assigned model's
quality/cost. It assumes no interference, conditional ignorability and positive
support for all treatments, then uses doubly robust counterfactual utility
scores. Its two surrogate objectives train routing decisions from estimated
utilities; Appendix A discusses their properties, and Appendix D records
clipping and estimation details. It specifies no active purchase or repeated
state allocation rule. [Full paper and appendices](https://arxiv.org/html/2505.16037v2).

For our prospectively randomized acquisition, probabilities can be logged
rather than estimated. Repeated decisions condition on acquisition history;
an IID observational estimator theorem does not automatically apply. Unknown
pool coverage and adaptive repeat counts must be handled explicitly. Positive
exploration, inverse weighting, doubly robust scores and decision-regret
optimization are established ingredients. Independent evaluation is still
needed, and naive averages of acquired draws overweight repeatedly selected
questions. No theorem in the reviewed paper certifies our adaptive budget stop.

## Our algebraic reduction and remaining technical obligations

The following deductions are from the project's fixed utility contract; they
are not claims made by the prior papers.

For finite states `i`, pool weights `w_i`, and threshold action vectors
`a_tau(i)`, put `mu_i = E[G_i]`. Threshold value, up to its common direct term,
is `V_tau = sum_i w_i a_tau(i) mu_i`. A response is a noisy observation of one
coordinate of `mu`; every pair contrast has coefficient
`w_i (a_tau(i) - a_eta(i))`. This is finite linear policy identification with
ordered binary targets. Order makes computation convenient; it does not make
the gain curve monotonic, warrant binary search, or identify a new feedback
model by itself.

Let `beta = .05/1000`. Joint correctness–length dependence obeys:

```text
E[G_i] = E[Y_think_i] - Y_direct_i - beta E[C_i]
Var(G_i) = Var(Y_think_i) + beta^2 Var(C_i)
           - 2 beta Cov(Y_think_i, C_i)
```

At matched marginal distributions, covariance changes uncertainty and learning
but not expected utility. It can also change the acquisition history through
realized charges. A joint-model removal must preserve marginals; changing
expected utility confounds the intended mechanism. Maximizing expected
information divided by expected tokens does not establish optimality under
random costs, reservation caps or a finite remaining budget.

Repeating a state reduces conditional response uncertainty. It adds no new
independent question. Equal weighting of state means is essential for a finite
pool target, but conditional sample means with outcome-dependent adaptive
counts still need justification. Posterior acquisition scores can be labeled
heuristics; propensity-based utility estimators need the correct history and
stopping assumptions. Distinguish sampled-pool and unseen-question targets.

## Exact implementable closest comparator for G1

Use **global information gain per expected token, an L1-inspired adaptation**.
Do not call this the original IG cost algorithm or a faithful reproduction.
Use the same purchased-only joint predictive model and posterior update as the
candidate. Freeze the prior, discrete outcome support or quadrature, particle
count, seeds, ties and exploration before synthetic execution.

For posterior particles `theta_m`, `m=1..K`, calculate the best global threshold
`T_m` using the fixed pool weights and deterministic tie rule. For the finite
cache implementation, retain exact observed-cell contributions and apply
particle means only to remaining cells, as in the algorithm specification. Let
`q_mi(o)` be the particle's predictive probability of a future joint
correctness/length observation `o` on eligible state `i`. Compute:

```text
p(k)       = mean_m 1[T_m = k]
p_i(o)     = mean_m q_mi(o)
p_i(k,o)   = mean_m 1[T_m = k] q_mi(o)
IG_i       = sum_{k,o} p_i(k,o) log[p_i(k,o)/(p(k) p_i(o))]
score_i    = IG_i / E[C_i | purchased history]
```

Zero joint-probability terms contribute zero. Predictive costs must come from
purchased information or the frozen prior, never the hidden future cost. The
controller filters jobs using their public full reservation cap, draws from the
same explicitly logged exploration mixture as the candidate, purchases one
draw, updates its posterior and ledger, and repeats. No next reservation fits:
return the current threshold. Exhausted cache states are ineligible. All common
direct/seed responses remain charged. Posterior optimum computations must use
purchased outcomes and predictions for remaining gains, never hidden simulator truth.

This construction carries the information calculation into a chosen-state,
global-policy, repeat-eligible setting. Its difference from local-context IG is
explicit. If the candidate uses the same objective, they are the same algorithm
after bookkeeping; remove a separate method claim. If the candidate uses
pairwise variance reduction instead, compare purchases and performance under
the matched model, while describing both as adaptations. Their uncertainty
criteria need not rank purchases identically.

Keep the planned seven acquisition controls: uniform new states, uniform fixed
repeats, confidence strata, policy disagreement, the global IG/cost adaptation,
utility-impact re-active adaptation, and the candidate. Original TaS-FG is
inapplicable under the actual observation law; do not replace the closest
cost-aware control with a mislabeled TaS-FG surrogate. Its structural comparison
is already a G0 requirement. Seed-only and historically learned confidence
remain reference policies with their acquisition costs disclosed.

## What a different-purchase example can establish

Consider two eligible states, where a cheap one changes the posterior about
several plausible thresholds and an expensive one changes only the best action
at its own state. A global policy criterion can favor the cheap state even when
a local action criterion would favor sampling at the other state. This is a
contract-level illustration, not an executed numeric fixture or priority proof:
the original contextual algorithm receives its state rather than selecting
between these states.

Before execution, the specification should provide a deterministic synthetic
fixture with exact purchased history, predictive distributions, costs, plausible
thresholds and the two computed scores. A purchase difference from uniform,
disagreement, utility-impact or a global IG control demonstrates behavior.
It does not show that existing experimental-design or policy-identification
methods fail to prescribe that purchase. No concrete novel purchase is
established by the current prose proposal.

## Gate recommendation

G0 closes the **method-priority hypothesis as unsupported** for this recipe.
Retain an empirical acquisition study only if the frozen G1 simulator answers
the useful question: do targeted thinking purchases improve threshold-learning
utility per total revealed token over these matched controls, including null
and adverse settings? Label posterior uncertainty and adapted controls honestly.
Report full physical cache cost separately. Preserve all earlier failed study
gates. No G2 collection or role/reference access follows from this review.

For a later distinct method claim, first recover the missing supplements/paper,
formalize the structured observation and random-budget target, and demonstrate
a substantive difference beyond changing the target, adding repeats, predicting
costs or applying existing inverse weighting. A guarantee needs assumptions and
a proof for this protocol; inherited terminology is insufficient.

### Source identity pins

| Repository | Revision | Selected source SHA-256 |
|---|---|---|
| L1 | `58b4bc462f71275faef231cf5a4f89a1db7aa4ce` | `alg.py`: `152a3240ef3156ad8db9a9d74dd6bc4388d6dd3327872396d60e1d12251ccb89`; `simulation_rideshare.py`: `1570fb241ac683425ca3bb54af71834c562291b7e715f1677243d442d2d1a350` |
| L3 | `485e47990a5f0a72a6dca78cb103cff015137b2c` | `baifg/algorithms/tas_fg.py`: `f0040c6db0ce9d68813d28e8a85a3879644c12d116d3e9e10867c312cbee69ba`; `baifg/utils/characteristic_time.py`: `a0029209464ace8de6c86bc9277016631a161bd3c794272db87065f58a0c9b96` |
| L4 | `73cbd7e7edaa83c407ac643b6f1e09ae4b15fbcb` | `src/sampling_strategies/sparsity_learning/base_inferred_sparse_performance.py`: `a0e5b2251ac903ac7b97b7100a60d766642caf6435b2bc784c2a35d2c5ee5522`; `README.md`: `1d2871b7f4de987516c994e1150316a2ad5dad6a7d64cbcedbdd02a281791c33` |

These pins identify inspected public source, not reproduced experimental
results. The review introduced only this document.
