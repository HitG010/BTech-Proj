# Focused plan: reduce the cost of learning a confidence router

**Execution update, 2026-10-09:** G0 found no supported distinct-method claim.
The frozen G1 simulation completed and failed all four practical comparison
screens. [Results and independent review](g1-synthetic-results-2026-10-09.md)
close this recipe. Do not start its G2 pilot or expand the same search.
Continue the [empirical manuscript](empirical-paper-outline-2026-10-09.md).
The original proposal below is retained as the pre-execution planning record.

Date: 2026-10-08. Branch: `codex/confidence-acquisition-plan`.
Base: `ee88d64` on `codex/research-data-efficiency`.
Status: researched proposal. No new experiment, allocation, fit, or reference access has occurred.

Read this with the [literature assessment](novelty-literature-2026-10-08.md),
[evidence map](research-evidence-map-2026-10-08.md), and
[publication plan](publication-plan-2026-10-08.md).

## 1. Decision

Focus on the cost of learning a useful confidence threshold.
Keep the solver and the confidence signal fixed.
Use Qwen3-0.6B as the first candidate setting.
It has observed direct-to-thinking opportunities on the completed development panel.
Retain Qwen3-1.7B direct as a practical system control.

The fastest credible route has two outputs:

1. An original empirical paper from the completed studies, with a narrow additional analysis or replication.
2. A conditional method paper about collecting the responses needed to learn a confidence threshold.

Start the empirical manuscript immediately. Give the method hypothesis a short, fixed feasibility period.
A general survey is a separate, slower option. Existing surveys already cover broad routing and adaptive reasoning.

Novelty is a hypothesis at this stage. Neither a new name nor a combination of existing methods establishes it.
The first deliverable is a decision about a specific technical difference from prior work.

## 2. New research question

> Can targeted collection of thinking responses reduce the training-token cost of learning a useful confidence threshold?
> Can it retain utility on unseen questions under a fixed solver, scorer, and cost preference?

Proposed working title:

**Learning When to Think with Fewer Thinking Samples**

The operational question is narrower than the previous question/action/repeat proposal.
We first learn one scalar threshold. We do not change the representation or train another large router.
The new method need not exceed an expensive confidence policy's final accuracy.
Its intended benefit is to learn a comparable policy with less training expenditure.

This changes the earlier progression requirement. An acquisition method can be useful without a new router beating confidence.
It still needs evidence that targeted acquisition improves on strong acquisition controls.
The failed historical learner gates remain failed. This document does not reopen them.

## 3. Why this is the preferred experiment

The repeat, neural, and released-CLM studies did not establish benefit over confidence.
The 0.6B learned pilot also failed. The fresh parser rule did not confirm its development gain.
The longer 1.7B cap gave lower point utility. These facts favor a simpler policy class.
See the [evidence map](research-evidence-map-2026-10-08.md).

Threshold acquisition has several practical advantages:

- The deployed policy needs no new encoder.
- Policy differences can be computed from the same purchased outcomes.
- A CPU simulator can expose faults before any new generation.
- Existing collectors, cost ledgers, and confidence records can support a new implementation.
- Failure still gives a clear answer about the cost of calibrating an established baseline.

There are also reasons it may fail. A few random samples may already identify a good threshold.
Direct-draft collection may dominate the total training cost.
The expected gain may vary irregularly with confidence.
Additional thinking draws may add less information than new questions.
The plan tests these possibilities explicitly.

## 4. Decision and cost definitions

Let `s = (question, fixed direct draft, confidence)` be a router state.
Let `a_tau(s) = 1` mean that confidence is below threshold `tau`.
Action 1 buys a fresh question-only thinking response. Action 0 accepts the draft.
The thinking solver does not receive the draft in this contract.

For scored correctness `Y` and charged output tokens `C`, define:

```text
G(s, draw) = Y_think - Y_direct - 0.05 * C_think / 1000
U_tau(s, draw) = Y_direct - 0.05 * C_direct / 1000 + a_tau(s) * G(s, draw)
U_tau - U_eta = (a_tau - a_eta) * G
```

The direct cost is common to threshold comparisons, but remains in total utility and acquisition cost.
The last identity shows where two policies need different evidence. It is standard algebra, not a new theorem.
One observed response informs several threshold comparisons. This is also related to established feedback-graph methods.

Use a finite threshold set derived from training confidence values only.
Include always-accept and always-escalate. Fix tie handling before outcomes are exposed.
Do not assume that gain is monotonic in confidence. A binary search would require additional justification.

A repeated thinking response keeps the direct draft fixed and uses a new independent seed.
A new direct draft creates a new state. It must not be counted as another observation of the old state.
If a question's thinking response is reused across its draft states, record that dependence explicitly.
Never count reused observations as independent responses.

Keep three costs separate:

1. **Revealed acquisition cost:** all direct states and response outcomes made available to a strategy.
2. **Physical research cost:** every response generated to build a cache, including unused responses and failures.
3. **Deployment cost:** solver work, routing work, model loading, latency, and memory.

Replay savings describe the first cost. They do not erase the second cost.
Equal tokens across different model sizes do not mean equal compute.

## 5. Candidate technical contribution

Test a rule that allocates thinking samples to reduce uncertainty in differences between plausible thresholds.
Compare a first observation on a new state with another draw on an observed state.
Normalize the expected information benefit by predicted generation cost.
Retain a randomized exploration component and log its exact probabilities.

The candidate must address three coupled issues:

- A purchased outcome affects multiple policies that share an action.
- Response cost is random and can be associated with correctness.
- Repeating one state reduces response noise but does not add another independent question.

This is a design specification, not a finished algorithm.
Before implementation, write its estimator, acquisition rule, update rule, and budget stop as explicit pseudocode.
Specify how unobserved outcomes and response lengths are estimated from purchased information only.
Account for both finite-pool weights and unequal repeat counts.

Do not use unweighted averages of adaptively selected states to estimate population utility.
Choose and validate an appropriate sampling-weight or model-based estimator.
If it claims coverage under adaptive sampling or stopping, provide the required assumptions and proof.
Otherwise call the uncertainty score a heuristic, and assess it on independent evaluation data.

**Novelty kill test:** compare the rule line by line with cost-aware policy learning, re-active learning,
and feedback-graph pure exploration. If it is a direct specialization, report that honestly.
Proceed as an empirical adaptation only if the experiments answer a useful unanswered question.
Do not add a contrastive loss or RL stage to restore a method claim.

## 6. Ordered work and decision gates

Durations are effort estimates from the start of execution. They are not publication or acceptance dates.
The human research lead owns the scientific decisions. The coding agent can prepare implementations and evidence.

| Stage | Target effort | Work product | Gate and stop rule |
|---|---:|---|---|
| G0: technical distinction | Days 1–2 | Exact prior-method comparison, one algorithm specification, empirical paper outline | State a concrete difference or classify the method as an adaptation. If neither adds useful knowledge, close the method track. |
| G1: CPU feasibility | Days 3–5 | Frozen synthetic protocol, baseline implementations, estimator checks, cost and precision report | Pass engineering checks and show a mechanism benefit in predefined synthetic cases. Failure closes this recipe; it does not trigger a wider grid. |
| G2: prospective pilot | Days 6–10, conditional | New source/role/endpoint freeze, bounded local cache, locked replay and evaluation | Pass the scientific screen below. Any runtime failure follows the new protocol's stop rule. |
| G3: independent evidence | Weeks 3–4 or longer, conditional | New task or independent archive setting, matched controls, fresh evaluation | Establish the declared effect with adequate precision and report acquisition-seed variation. Otherwise reduce the claim. |
| G4: paper and artifact | Draft begins on day 1 | Manuscript, evidence tables, reproducible package, deviation record | Every claim maps to evidence. Choose one archival submission route. |

At day 10, make one explicit decision: continue the method, write an empirical adaptation, or close the recipe.
Do not extend the method search because the result is nearly positive.

### G0 work

Read the full algorithms and supplements for literature items L1–L5.
The desk review established overlap; exact algorithm equivalence is still pending.
Record the available feedback, cost assumptions, stopping criterion, and guarantee for each.
Write a one-page comparison with an example on which the proposed rule makes a different purchase.
If that purchase is already prescribed by an existing method, remove the priority claim.

Prepare the cached cap-error review as a bounded companion task.
Separate eight accepted-but-wrong extended outputs from three parser rejections.
Use cached data and scores. Mark unsupported error causes as unknown.
This task supports the empirical paper. It is not a prerequisite for threshold acquisition or permission for LoRA training.

### G1 work

Freeze synthetic settings before execution. Include:

- No thinking benefit, where an early stop is appropriate.
- A clear confidence threshold with many independent questions.
- High response noise, where some repeats can help.
- Strong differences between questions, where repeats can waste budget.
- A nonmonotonic gain curve with multiple plausible thresholds.
- Rare beneficial changes and frequent harmful changes.
- Positive, zero, and negative correctness–length association at matched marginal scales.
- A high common direct-draft cost that can eliminate total savings.

Use 30 paired synthetic seeds per setting and one fixed configuration per method.
Cap the experiment at eight settings, seven acquisition methods, two component removals, and three budget checkpoints.
The removals disable repeat selection and joint correctness–length modeling, respectively.
Keep every other candidate setting fixed. They are diagnostic comparisons, not extra candidate families.
Allow correctness repairs with a documented new source pin. Do not tune on synthetic evaluation outcomes and report them as untouched tests.

Required checks include hidden-label access, hidden-cost access, budget reservations, sampling weights,
question grouping, repeated-state identity, and all reported arithmetic.
Check that the candidate reduces to the intended simple rule in deterministic fixtures.
These tests are planned work; none ran in this planning change.

Promotion requires no unexplained estimator bias on controlled cases and no budget/leakage failures.
The candidate must improve on uniform allocation and the closest cost-aware control in the intended mechanism cases.
Retain null and adverse cases. Simulation benefit alone cannot support a real-data claim.

### G2 proposed pilot

The following numbers are a concrete planning envelope. They are not a prepared collection protocol.

| Proposed component | Questions | Responses | Response-only maximum |
|---|---:|---:|---:|
| Acquisition child: one fixed direct state and two independent thinking draws | 64 | 192 | `64 * (512 + 2 * 2562) = 360,704` tokens |
| Validation child: one direct and one thinking response | 64 | 128 | `64 * (512 + 2562) = 196,736` tokens |
| Total | 128 distinct groups | 320 | **557,440 tokens** |

Proposed source roles are a child of the existing 1,200-question acquisition pool and a child of the 200-question validation role.
This deliberately changes the progression decision for those unstarted roles and needs a new reviewed protocol before selection.
Audit current manifests and sibling children first. Do not infer availability from this document alone.
The remaining 256 reserve questions, 2,000 new confirmation questions, old 3,100-question confirmation, and official test stay untouched.

Use the pinned 0.6B solver, existing confidence definition, prompt, caps, decoder, and v7 scorer.
Propose a **650,000-token / 12-hour** global ceiling, including setup and conservative failure charges.
Response headroom is 92,560 tokens. It is not permission for additional scientific jobs.
Measure throughput and freeze setup/job timeouts before launch. A failed attempt stops collection; no automatic retry is proposed.
Preserve partial output and charges if the endpoint cannot complete. Any completion needs a separate prospective decision.

Collect the fixed pilot cache without adaptive label access.
Require all 320 responses, exited collectors, and accounting/preservation checks before the first reference access.
Expose exactly the 64 selected training references through a new private training endpoint.
Expose validation references only after all acquisition runs have written immutable policies and logs.
That later endpoint accesses exactly the 64 selected validation references.
Keep references out of question snapshots and acquisition-policy inputs. Use separate score sidecars.
The simulator reveals only purchased training outcomes. It must not read future response cost before reserving the job cap.
No executor from a completed study may be reused to bypass its old endpoint rules.

Use paired acquisition seeds, five initially. Five seeds measure strategy variation, not five independent datasets.
Use total revealed-token checkpoints of **64k, 128k, and 256k**, including all common direct-state costs.
An eight-state thinking seed set plus all direct states reserves at most 53,264 tokens and fits the first checkpoint.
Charge this common seed set to every method. Freeze its question-only selection rule.
Stop a strategy when the next full reservation cannot fit. Carry its current policy to later reporting checkpoints if its eligible cache is exhausted.

Required acquisition comparisons:

1. Uniform new-state acquisition before repeats.
2. Uniform allocation with a fixed repeat schedule.
3. Confidence-stratified random acquisition.
4. Policy-disagreement acquisition without cost normalization.
5. A faithful, documented cost-aware policy-learning adaptation.
6. A documented re-active-learning adaptation.
7. The proposed rule.

Also report seed-only calibration and the existing frozen confidence policy as reference policies.
The latter used historical supervision. It is not a zero-cost training baseline.
Compare a feedback-graph method in G0; replace a weaker acquisition control if it is the closest applicable method.
Freeze that decision before G1/G2 results. The seven-method limit must remain fixed.

Use one policy estimator across acquisition controls where possible.
If a baseline requires its own estimator, disclose this and add a matched-estimator comparison.
An active retrieval router can be an external system control if feasible; it cannot isolate threshold acquisition by itself.

### G2 scientific screen

Primary proposed endpoint: difference in normalized utility learning-curve area at lambda .05.
Use the three total-token checkpoints above and trapezoid weights `1/6, 1/2, 1/3`.
This is a new budget range. It does not replace the historical roadmap's 100k/200k/400k endpoint.
Name the primary cost-aware comparator from G0/G1 before any new real outcomes are accessed.
Report all controls. Require the point screen against every acquisition control, not only that named comparator.
For a final claim involving several comparisons, freeze an appropriate simultaneous analysis.

Proposed progression requirements are all of the following:

- Mean primary difference at least **+.01 utility** over each acquisition control.
- Positive primary difference in at least four of five paired acquisition seeds.
- A positive direction after removing each validation question in turn.
- Evidence that the proposed component matters relative to its matched removal.
- A feasible independent precision and resource plan.

These are pilot screens, not a superiority claim or a calibrated hypothesis test.
Freeze them in the actual analysis protocol. Changes before execution require a dated reason.
After evaluation, do not relax them or nominate another method as the original primary.

Secondary target: comparable held-out utility with **50% fewer training tokens**.
Proposed tolerance is .005 utility. This is a target, not an observed saving.
Assess whether simpler methods already reach that target at the same small budget.
Do not claim a unique saving if they do.
Report equal-budget curves even if the secondary target looks favorable.

Two thinking draws permit only a limited repeat test. They cannot establish a general repeat-allocation advantage.
Do not run new fits on the closed 50-question or 64-question development studies to select this algorithm.
Their published summaries provide motivation; synthetic data and the new protocol provide development evidence.

## 7. Independent evidence and statistics

Choose the second setting before seeing G2 validation outcomes. Make only its execution conditional.
Preferred option: the same 0.6B direct/thinking contract on a separately prepared numeric MATH training subset.
Specify source revision, answer eligibility, parser coverage, and train/test boundaries before collection.
Any reference-based eligibility filter needs declared reference access.
If local feasibility fails, narrow the paper. Do not search tasks for a positive result.

A public routing archive is an alternative for acquisition mechanics if it exposes the required costs and outcomes.
It may not contain direct drafts, confidence, or repeat draws. In that case it cannot confirm this full question.
Inspect metadata and licenses first. Audit overlaps before downloading outcome-bearing files.
Public GSM8K/MATH archives may contain protected test items. Public access does not remove the project's sealed-data boundary.

Report uncertainty over evaluation question groups and acquisition seeds separately.
Do not multiply the sample size by the number of methods, draws, or seeds.
For a final claim, define the procedure-level estimand and use a justified hierarchical or independent replication design.
Intervals with a fixed policy must be identified as conditional.

The earlier SD=.16 calculation requires about 2,010 groups for a +.01 paired effect at 80% power.
That calculation does not size the new learning-curve endpoint or the .005 noninferiority target.
Recalculate precision for the new estimand before G3. A small pilot cannot certify these margins.
The 2,000 confirmation cap is binding; insufficient precision requires narrower claims or a new prospective data plan.

Keep lambda .05 primary. Any additional cost preferences are frozen secondary analyses.
Count harmful changes as well as rescues. Include direct, always-thinking, confidence, and a faithful DART control
when making a broader deployment claim. A two-draft adaptation is not a full DART reproduction.
Measure actual end-to-end costs for cross-size comparisons before a practical superiority claim.

## 8. Immediate deliverables and execution boundary

The next implementation slice is **G0 plus a frozen synthetic G1 protocol**.
Expected files are an algorithm specification, a synthetic acquisition simulator, its meaningful tests,
a bounded analysis protocol, and an additive result directory. Exact names and hashes are fixed before execution.

The publication slice can start from existing reports. It requires a claim-to-evidence table,
an explicit development/confirmation distinction, and the literature map in this branch.

This planning change authorizes no collection by itself. It allocates no questions and creates no worker.
Do not relaunch completed collectors, reopen old references, refit closed grids, or change frozen sources.
Keep Docker running. Local execution remains the default. Free Kaggle is an optional existing resource, not a required step.
Paid cloud, RL, Jev, CLM retraining, and solver fine-tuning are outside this focused plan.

The [publication plan](publication-plan-2026-10-08.md) defines how to retain value if the method gate fails.
