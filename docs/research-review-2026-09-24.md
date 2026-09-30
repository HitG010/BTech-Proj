# Research review — 24 September 2026

**Implementation update, 2026-10-01:** the standalone-thinking accounting defect
in section 2.A is corrected in a new v2 development artifact; v1 is preserved.
All six other policies and the shared-versus-confidence comparison are unchanged.
See the [Phase 1 evidence-repair record](phase-1-evidence-repair.md) and the
[active research roadmap](research-roadmap.md). The review below records the
evidence and proposals as inspected on September 24.

This review covers the current router-studies worktree, its saved development and diagnostic reports, and the sibling pilot-v2 protocol. Sol and Luna agents assisted with read-only code and evidence inspection. Primary literature and TypeSafe's official Jev documentation were checked on the review date. This is a review and proposed experimental program, not a new experiment or an exhaustive novelty clearance.

**Assessment:** the project has a useful, unusually explicit experimental record, but has not established a new router that beats its strongest simple baseline. The best next investment is protocol repair followed by a small test of learnable, reproducible reasoning benefit. A Jev-inspired decision model is reasonable to investigate; adding Jev or reinforcement learning does not itself establish novelty.

The existing worktree was already dirty when reviewed. This review adds only this document. No solver generations, Jev API requests, confirmation runs, or changes to frozen artifacts were made. The existing offline suite passed: **116 tests in 42.08 seconds**. Passing tests do not validate the scientific claims or exclude the reporting defect below.

## 1. What the evidence supports

| Question | Evidence | Assessment |
|---|---|---|
| Does thinking help this solver? | Calibrated pilot: direct 84%, thinking 92%; later development pool: 86%, 91.5%. | Yes, on average under these protocols; the first pilot's reversal was largely truncation. |
| Does the question-only router outperform random allocation? | Ridge's illustrated gain over cost-matched random was +0.24 percentage points, interval −2.58 to +3.13. | Not established. This is a result for the tested representations/data, not an impossibility result. |
| Does the original continuation router beat confidence? | Fresh diagnostic: utility difference +0.008188, interval −0.020329 to +0.044029. | Inconclusive; it also trails gain-ridge at the primary preference. |
| Does shared correctness fix that? | Development: shared 90.25% at 622.0175 tokens; confidence 90.25% at 589.375. | It improves the other learned models but does not beat confidence at λ=.05. |
| Is acquisition more sample-efficient? | An acquisition proposal exists; no completed equal-budget acquisition comparison. | Not tested. |
| Is there independent confirmation? | The 3,100-question run is prepared but has not generated responses. | No. Its frozen policy is the older joint router. |

Sources: [routing learnability](routing-learnability.md), [continuation report](../artifacts/probe/continuation-v1/report.md), [shared-router report](../artifacts/router-dev/shared-base-v1/report.md), [confirmation design](confirmation-design.md). The numerical diagnostic and shared-policy differences were checked against saved per-question results during this review.

## 2. Gaps and repairs, in priority order

### A. Correct the always-thinking baseline in the latest development report

This is a concrete implementation/reporting defect. `router_dev.py:298–302` labels `rows[:, :, 2]` as always-thinking. But `probe.py:58–59` defines that action as **first generate a direct draft, then think**, charging both calls. A standalone always-thinking policy never needs the direct draft. The original diagnostic handles this correctly in `probe_study.py:329–334`.

Using the saved development rows, retaining thinking accuracy and subtracting only the first draft's tokens and elapsed time gives:

| Standalone thinking quantity | Reported | Corrected calculation |
|---|---:|---:|
| Accuracy | 91.50% | 91.50% |
| Charged tokens/question | 1,654.47 | **1,430.69** |
| Utility at λ=.05 | 0.8322765 | **0.8434655** |
| Shared minus thinking utility | +0.039122625 | **+0.027933625** |

The shared-versus-confidence result is unchanged. The corrected cached generation time is 60.1361 seconds/question; it is still not a live end-to-end latency measurement.

**Repair:** derive standalone thinking from the original thinking array, or subtract the first-draft cost/time from the continuation row without subtracting accuracy. Add a semantic test that standalone thinking charges exactly one thinking generation. Regenerate the development table, plot and relevant intervals into a versioned corrected report, preserving the original artifact and explaining the correction. Do not silently replace frozen evidence.

Code: [router_dev.py](../src/reasoning_budget/router_dev.py), [probe.py](../src/reasoning_budget/probe.py), [probe_study.py](../src/reasoning_budget/probe_study.py).

### B. Separate a useful router from an established research contribution

At the primary λ=.05, the latest shared model is weakly dominated by confidence in aggregate accuracy and generated-token cost. The higher-accuracy result at λ=0 is exploratory after multiple curves and method revisions. It cannot replace the primary endpoint retrospectively.

The original diagnostic's +1.5 percentage-point accuracy advantage over confidence comes from only **five of 100 questions** with differing accuracy: +1, +1, +0.5, −0.5 and −0.5 after orientation averaging. In the shared development comparison, only two questions have different accuracy, with net zero. A few cases therefore drive the apparent differences.

**Repair:** freeze one practically meaningful endpoint and strongest comparator before fresh evaluation. If the application needs near-thinking accuracy, define an accuracy non-inferiority margin and a token/latency reduction target in advance. Keep λ=.05 as the historical primary endpoint, and give a newly chosen endpoint a new protocol identity. Retain negative results.

### C. Do not confuse cross-validation with fresh confirmation

The current grouped folds and training-only transformations are appropriate. Both orientations remain with their question, and held-out-outcome perturbation tests protect the deployed decision inputs. No obvious gold/future-response leakage was found in that path.

However, these 200 questions have repeatedly influenced the research direction. Nested cross-validation prevents direct fold leakage; it cannot undo human/agent method selection across experiments. Bootstrap intervals condition on saved fitted policies and do not capture that selection or retraining instability.

**Repair:** label current results as development; use new questions for confirmation; report variability across training/acquisition seeds separately from question-level sampling intervals. Resample by question, or by parent/template when testing related perturbations. Freeze representation, prompt, parser, threshold, preference, comparator and stopping rule before opening a new holdout.

### D. Establish that the target is learnable before increasing architecture complexity

Most pilot questions tie between modes. Four of five shared-router folds selected response-only features instead of MiniLM question embeddings. The current conditional models have only 56 wrong first-draft states, and five/thirteen harm states for the two continuation actions. These are correlated states, not that many independent questions. Only 11 development questions have wrong direct-draft agreements.

Moreover, the shared router shares first-correctness but fits separate rescue/harm heads per action. Its Beta-rate shrinkage uses state counts; it is not a cluster-aware posterior over independent questions. The reported first-correctness Brier score does not demonstrate calibration of rare rescue probabilities or action-value differences.

**Repair:** compare one-sample and repeated-sample training labels, preserving an independent evaluation set. Also split repeated draws on the same questions into selection and evaluation halves to test whether apparent mode advantage reproduces; that check alone is not unseen-question generalization. Use a small predetermined learning curve, strong shrinkage, and question-level uncertainty. Report decision regret/utility and calibration of action outcomes, not only correctness AUROC. Avoid training a large neural policy on 11 consensus failures.

Sources: [shared results](router-dev-results.md), [research proposal](router-research-proposal.md), [shared implementation](../src/reasoning_budget/router_dev.py).

### E. Reconcile protocol and scorer identities

The worktrees differ in prompt, reasoning/answer caps, closure text, EOS handling and confidence signals. Both use the name `numeric-v4` for different parsers. A result under one protocol is not an interchangeable replication of another. Re-scoring can reconcile extraction, but cannot remove differences in the generated responses.

The current confidence feature is a mean log probability after temperature/top-k/top-p processing (`backend.py:215–222`). It depends on the decoder and is not a calibrated correctness probability. The sibling records raw-logit confidence as well; transporting a threshold between those signals would be invalid.

The read-only dual-parser check covered 900 existing responses (400 calibrated-pilot and 500 continuation-diagnostic records). Correctness changed on **zero of 900**; one parser status changed while remaining incorrect. Thus the scorer-name collision is an actual provenance hazard, but this check provides no evidence that it changes the present diagnostic accuracy. EOS changes, by contrast, require generation to measure their effect.

Direct and thinking modes also use different temperature/top-p settings. That is valid for comparing the configured strategies, but a claim that reasoning alone causes the accuracy gap needs an additional decoder-controlled experiment. The sibling pilot-v2 confidence threshold was chosen on the same 100 questions used for its reported result, so that number remains an in-sample diagnostic.

**Repair:** create unique protocol and scorer fingerprints; port justified fixes into a new protocol version; cross-score common raw responses with both parsers and report disagreements; retain source hashes. Run a small paired protocol bridge before attributing any gain to a new router. Collect both raw and decoder confidence prospectively, and calibrate on separate data. The human audit waiver remains in force; automated differential checks and a disclosed residual validity limitation can proceed without reopening it.

Sources: [protocol comparison](README.md#3-two-lines-of-work-read-this-before-comparing-numbers), [backend](../src/reasoning_budget/backend.py), [scorer](../src/reasoning_budget/scoring.py).

### F. Strengthen baselines, cost measurements and generalization

The present DART comparators are explicitly limited adaptations. Full DART SC-Budget and ReASC have not been reproduced. The literature also includes RL-based thinking selection, so a new RL policy needs more than an always-direct/always-thinking comparison.

Generated-token cost correctly charges consumed drafts and inserted closure tokens for the main continuation policies, but omits prompt-prefill work and routing overhead. Cached elapsed generation time includes model execution/prefill; it still excludes feature extraction and live orchestration. Jev would add API latency, input cost and an external model whose compute is not represented by Qwen output tokens.

**Repair:** compare against tuned confidence, gain regression, DART's full supported procedure, and ReASC with an explicitly matched protocol. Include a simple prompt-only classifier and a solver-aware representation probe when evaluating Jev. Measure full request latency, including router, prefill, all calls and retries. Report acquisition expenditure separately from deployment cost, and estimate deployment break-even volume. Do not convert a vendor's advertised API speedup into a speedup for this system.

Evaluate a second solver and a predefined second task or distribution shift. GSM-Plus is useful for perturbation robustness, but its parent GSM8K items must be grouped and checked against the sealed IDs; it is not automatically an independent dataset. A numeric-answer competition-math subset is another option, with an appropriate frozen scorer. Freeze selection criteria before inspecting comparative results. [GSM-Plus paper](https://arxiv.org/abs/2402.19255).

### G. Reconsider the 3,100-question expenditure only after a candidate survives

The 3,029-question power estimate assumes the old router's noisy +0.008188 utility effect and observed standard deviation persist. The saved sensitivity analysis needs 8,123 questions for an effect of .005 at the same variance. More evaluation cannot rescue a truly zero or negative advantage.

**Repair:** retain the existing frozen confirmation intact. For a new candidate, choose the minimum worthwhile effect first, estimate variance with conservative sensitivity, and prepare a new confirmation identity. Do not spend 125–142 local hours merely because a run is already prepared. [Power analysis](../artifacts/probe/continuation-v1/power-analysis.md).

## 3. What Jev contributes, and what it does not establish

The user's link refers to **TypeSafe's Jev**, announced September 15, 2026, not JEPA. TypeSafe describes parallel structured decisions with probabilities and a training approach called Reinforcement Learning for Calibrated Decisions (RLCD). These are vendor descriptions; this review did not benchmark them. [Official announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

Its public interface accepts state plus typed Choice/Score/Noul questions. This fits a routing component well. In the official materials inspected, I did not find a reproducible layer-level architecture or RLCD training recipe that would let this project faithfully recreate or fine-tune Jev. An open implementation should be called **Jev-inspired**, with its own fully specified method. [Official interface](https://docs.typesafe.ai/introduction), [training overview](https://docs.typesafe.ai/introduction/machine-learning-primer).

Two caveats matter directly here. First, Jev's `confidence` summarizes concentration of its output distribution; it is not an independent measurement that Qwen will answer correctly. Second, TypeSafe documents weaknesses in numerical precision and multi-step indirection, and warns that separately phrased probabilities need not satisfy expected structural identities. Schema validity is not semantic correctness. These limitations do not prove Jev cannot route math, but rule out assuming it is an oracle math verifier. [Confidence documentation](https://docs.typesafe.ai/confidence), [known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

There are two sensible experiments:

1. **Hosted Jev as a frozen signal:** supply question and solver/protocol identity, optionally the already-paid direct draft. Use a small fixed set of semantic judgments, such as whether the draft appears to omit a stated constraint. Fit a local calibrated router against actual Qwen outcomes. Compare with and without the Jev signals under the same data budget. Cache versioned requests/responses; count all costs. Jev judgments are features or surrogate predictions, never ground-truth rewards.
2. **Open decision model:** a frozen small encoder or solver prompt representation feeding small probability and cost heads. No autoregressive explanation is needed to output these numbers. The repository already follows much of this pattern. Train/calibrate it on solver-specific outcomes; establish whether a better representation adds information before unfreezing a backbone.

Merely returning structured probabilities is not new architecture in this project. The research question must concern what is learned, how cheaply it is learned, or a rigorously demonstrated reliability/efficiency improvement.

## 4. The correct routing target and where RL fits

“Thinking problem” is not an intrinsic binary property. It depends on solver, prompt, budget, decoder and the value assigned to computation. A hard question that both modes miss may have no positive thinking benefit; a simple-looking question can expose a systematic direct-mode error.

For a question-only state x, predict solver-specific expected correctness and cost for each mode:

```text
Q(x, a) = P(correct | x, a) − λ E[charged tokens | x, a] / 1000
choose thinking when Q(x, thinking) > Q(x, direct)
```

Keep calibrated outcome probabilities separate from the policy's probability of selecting an action. The latter is an exploration/control quantity and need not mean correctness.

For a state s after a direct draft, use the existing coherent decomposition:

```text
incremental value(a | s)
  = (1 − p_first_correct(s)) × P(rescue | first wrong, s, a)
    − p_first_correct(s) × P(harm | first right, s, a)
    − λ E[additional charged tokens | s, a] / 1000
```

This equation is standard expected utility. Its practical benefit is that “likely wrong” does not automatically imply “worth spending more on.” If accepting costs zero additional tokens, buy a continuation only when its estimated incremental value is positive. Add separate latency or monetary objectives only with defined units and preregistered tradeoffs.

For one decision, **contextual bandits are the appropriate lightweight RL formulation**: observe context, choose a mode, receive verified correctness minus computation cost. With both action outcomes already cached, supervised outcome/value learning is a strong and usually simpler baseline; applying PPO/GRPO is not required. With only chosen-action feedback, use randomized exploration and log action probabilities, model versions, costs and verifiable outcomes. Thompson sampling or an uncertainty-based bandit is a baseline, not a novelty claim. A doubly robust or propensity-weighted analysis requires adequate action support and correct logging; neither can recover unobserved actions with zero support.

RL becomes more substantively sequential if the policy can accept, buy another draft, then decide again after observing agreement. The current replay hard-codes that second decision. Raw cached records permit a small experiment that reopens agreeing answers, but changing prompts, adding budgets, or conditioning thinking on drafts changes the action distribution and requires new traces. The current thinking fallback is a fresh solve of the question, not a learned critique of the draft.

Calibration should be trained/evaluated with proper probability losses such as log loss or Brier loss, separately from final policy utility. Rewarding a model simply for reporting high confidence would encourage overconfidence. Optimizing routing reward alone does not guarantee calibrated probabilities. In deployment, absent gold labels, define what verified feedback is actually available; do not treat a confidence score as correctness.

## 5. Novelty options and the prior-art boundary

| Direction | Prior-art overlap | Reviewer assessment |
|---|---|---|
| Jev chooses thinking/non-thinking | Generic routing and Jev's own routing interface | Useful integration experiment; weak standalone research novelty. |
| RL learns when to think | Thinkless and Root-token Policy Optimization | Established direction; require a narrower distinction. |
| Confidence or draft agreement triggers more sampling | DART, ReASC, Learning When to Sample | Necessary comparators, not a fresh contribution. |
| Buy a more informative routing signal when worthwhile | Pandora's Router | Generic value-of-information is already covered. |
| Use Jev predictions to improve a bandit | Correlation-aware bandits with surrogate rewards | A direct comparator is needed; a surrogate plus bandit is insufficient. |
| Learn rare, recoverable agreement failures with fewer purchased traces | Overlaps active acquisition and adaptive verification | Best project-aligned hypothesis if a specific acquisition algorithm wins strong ablations. |

Relevant primary sources: [Thinkless](https://arxiv.org/abs/2505.13379), [RPO](https://aclanthology.org/2026.acl-long.816/), [DART](https://arxiv.org/abs/2606.23181), [ReASC](https://aclanthology.org/2026.findings-acl.1085/), [Learning When to Sample](https://arxiv.org/abs/2603.08999), [Pandora](https://arxiv.org/abs/2608.20316), [surrogate-reward bandits](https://arxiv.org/abs/2607.09015). These works differ in tasks and training contracts; their reported scores are not comparable to this repository's scores.

**Recommended main hypothesis:** can a small calibrated router learn when additional thinking will rescue an answer using fewer acquired generation tokens, by choosing which question, action and independent repeat to observe?

**Recommended focused extension:** apply that acquisition strategy to the rare cases where direct drafts agree but are wrong. A Jev signal is an optional feature source; the contribution should survive substitution with a reproducible open signal, or explicitly be scoped to Jev-assisted routing.

A concrete prototype would:

1. Maintain a small ensemble/posterior of action outcome and cost predictors; resample at question level to represent uncertainty.
2. Consider candidate purchases `(question, action, repeat)` under a fixed acquisition budget.
3. Approximate each purchase's expected improvement in deployed policy utility across a fixed, unlabeled training-reference pool, divided by expected acquisition cost. Preserve quality and length together when sampling hypothetical outcomes.
4. Include randomized exploration so low-confidence or systematically mispredicted regions are not permanently excluded. Keep a prospective ledger of propensities and stopping decisions.
5. Fit exactly the same final router for every acquisition strategy, then evaluate on untouched questions with independent response draws.

The novelty would have to lie in a specific treatment of rare correlated failure regions, stochastic quality/cost and the effect of new observations on policy decisions. The expected-value formula, Bayesian shrinkage, calibration loss and bandit machinery are established tools. Compare against uniform allocation, random acquisition, uncertainty sampling, error-targeted acquisition, regret-per-cost, a new-versus-repeat baseline, and relevant router-specific active acquisition/surrogate-bandit methods. If it reduces to an existing method with tokens substituted for cost, describe it as an empirical adaptation.

For the agreement extension, measure wrong-consensus detection at fixed verification spending, actual rescue rate, regression rate on correct agreements, total utility and latency. Compare “never verify agreement,” “always verify agreement,” confidence-only verification and the learned selector. A classifier that detects errors which thinking cannot fix has not solved the routing problem.

An eventual, conditional contribution statement could be:

> We introduce a trace-acquisition method for training a calibrated continuation router around a frozen reasoning model. By allocating independent samples to uncertain, decision-relevant rescue and regression regions, it reaches a specified held-out utility with fewer acquired generation tokens than competing acquisition strategies.

That sentence is a proposed claim to test, not a result currently supported. A possible working title is **Learning When Thinking Helps: Budgeted Acquisition for Calibrated Reasoning Routing**. The narrower agreement extension could be titled **When Agreement Is Wrong: Learning the Value of Verification Under a Trace Budget**.

## 6. A staged execution plan

| Stage | Work | Decision gate |
|---|---|---|
| 1. Repair evidence | Correct thinking baseline; reconcile scorer/protocol identities; preserve archived reports; inspect policy-differential cases using frozen scoring rules. | Tables reproduce from an explicit protocol and costs mean the same thing across policies. |
| 2. Diagnose information | Small predetermined repeated-generation panel; one-vs-many label experiment; confidence, question-only and solver-aware features. | Reproducible benefit exists on independent draws and unseen questions. |
| 3. Test Jev's value | Frozen Jev features versus the same learner without them; optional open decision model; supervised baseline before bandit optimization. | Extra signal improves held-out utility or target-quality cost after its own overhead. |
| 4. Test acquisition | Hold architecture fixed; compare acquisition strategies at equal cumulative budgets and several independent acquisition seeds. | Improvement survives strong acquisition baselines and component removal. |
| 5. Test scope | Predetermined second task/solver and distribution shift; full DART/ReASC comparisons; live latency. | Claims hold within the stated scope, with failures reported. |
| 6. Confirm | New frozen candidate/protocol, minimum meaningful effect and uncertainty plan; untouched evaluation questions. | Confirmed result justifies a method claim. |

A small repeated panel can start with a predeclared 40–60 development questions and four independent draws per mode, extending toward eight only under a specified diagnostic rule. This is a proposed feasibility design, not a power guarantee. It should include the target population rather than only retrospectively selected failures; any deliberate enrichment needs sampling weights and separate population evaluation. Existing frozen confirmation IDs and sealed test IDs remain unavailable for development unless explicitly released into a new documented allocation.

Do not expand into a large neural architecture search, solver fine-tuning and sequential RL simultaneously. First locate the information that improves decisions; then test whether Jev, a trainable representation, or acquisition is responsible. If no representation predicts useful mode advantage beyond confidence, a carefully replicated negative result remains more defensible than adding architectural complexity.
