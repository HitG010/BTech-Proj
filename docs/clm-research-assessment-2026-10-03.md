# CLM: research assessment and next experimental decision

Reviewed 2026-10-03 against the official release/code, relevant routing papers,
our completed cached experiment and a new descriptive score audit. **Keep CLM as
a candidate representation and an explicit baseline. Do not promote the tested
recipe or claim that adding it establishes novelty.** A useful adaptation must
learn solver-specific incremental utility and justify its complete inference cost.

## What the release actually changes

The release combines a frozen Qwen3-8B encoder with trainable state/action
projection heads and bidirectional InfoNCE. It independently embeds states and
candidate actions. The model card describes Q&A/hard-negative/agent-trajectory
training, and says its coding-verifier results require task-specific head
finetuning. It also states that the heads are encoder-locked, generate no text,
and return probabilities relative to supplied candidates. These are the
authors' descriptions, not independent evidence for reasoning-mode routing.
[Official model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B).

This is a new released decision-model package built on an existing transformer
and familiar contrastive machinery. Its release recency does not make our use
of it an architectural contribution. The published head implementation maps
4,096-dimensional encoder states to 512-dimensional projections and compares
normalized state/action vectors using a learned temperature scale.
[Official head implementation](https://github.com/Contrastive-LM/CLM/blob/main/src/clm/heads.py).

For our fixed two-action set, let the normalized projected state be `z(s)` and
the two action vectors be `v_accept` and `v_think`. Then

`margin(s) = scale × z(s) · (v_think − v_accept)`

and `P(think | supplied actions) = sigmoid(margin(s))`. Thus the action decision
depends on one direction in the projected state space. A useful pretrained state
head is still possible; the contrastive form alone provides no extra decision
information beyond that margin. A positive score need not mean that thinking
will repair this solver's draft or justify its cost. This is algebra for the
two-action case, not a claim that every CLM has only one useful feature.

Action caching remains convenient, but with two static options it amortizes only
two action encodings. Our changing question/draft still requires the 8B state
encoder. Jev's release describes typed decisions and RLCD, but supplies neither
a local reproduction of that training method nor evidence for our endpoint.
It is a related system, rather than a reproducible local RL recipe for this study.
[TypeSafe release](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

## What we have established locally

The completed [Phase 2d experiment](phase-2-clm-probe-results.md) used the actual
released heads, pinned 4-bit MLX Qwen3-8B, 400 direct-draft states from 50 question
groups, five question folds and independent four-draw halves. No head finetuning
was performed. All point comparisons below use the same averaged-half endpoint
at the preselected λ=.05; the separate full8 endpoint is not mixed into this table.

| Policy | Accuracy | Generated tokens/question | Utility minus confidence |
|---|---:|---:|---:|
| Confidence | 92.75% | 628.47 | — |
| Released CLM, zero-shot | 94.75% | 1,550.53 | −.026103 |
| Scalar-calibrated CLM | 88.50% | 443.71 | −.033262 |
| Same encoder, PCA8/Ridge control | 89.00% | 330.81 | −.022617 |

Zero-shot chooses thinking 380/400 times. It captures all 30 positive paired-gain
opportunities, alongside 350 nonpositive decisions and nine harmful escalations.
Its positive-gain precision is only 7.89%. Calibration captures no positive gains
in either direction. Every predeclared exploratory screen fails. This closes the
particular fixed state/action/calibration recipe; it does not test every possible
task-trained CLM or establish a population-wide architecture disadvantage.

The new [score audit protocol](clm-signal-audit-protocol.md) distinguishes an
offset/threshold problem from a ranking problem without fitting or changing
actions. It uses tie-aware AUROC and 2,000 whole-question bootstrap draws, keeping
all eight samples together. These are post-hoc descriptive scores on reused data.

| Cached score | Positive-gain AUROC | 90% interval | Direct-error AUROC |
|---|---:|---|---:|
| Released CLM margin | .500450 | [.257735, .718199] | .478585 |
| Negative direct confidence | .705045 | [.495686, .921726] | .595238 |

The paired positive-gain AUROC difference is **−.204595**, interval
**[−.606961, +.195547]**. It is imprecise and crosses zero. Within-question
positive-gain AUROC is .523690 for CLM versus .668393 for confidence, using only
10 groups with both classes; this subset is not a population summary. CLM's
question-mean score in one half has Spearman correlation −.023193/−.081585 with
mean gain in the opposite half. These correlations have no interval and imply
neither causation nor deployable same-question label transfer.

The point evidence suggests weak ranking as well as over-escalation. Increasing
monotonic recalibration preserves AUROC, so changing an offset or temperature
cannot by itself repair these rankings. A newly trained representation could
change them, but that remains a different experiment. Wide intervals prevent a
claim that confidence has a statistically established population ranking advantage.

For the *fixed* zero-shot/confidence actions, the extra .02 accuracy costs
922.0625 tokens/question. Their generated-token utility ties at λ≈.021691,
below our frozen .05. This sensitivity excludes encoder cost and holds the
confidence actions selected at .05 fixed. It does not justify choosing a new λ
after seeing results, and is not an optimized accuracy/cost curve.

Engineering is feasible: mean state encoding is 1.427 s, p95 2.244 s, peak MLX
allocation 4.895 GiB, maximum input 659 tokens, zero truncation. That is measurable
work for every draft even when we accept it. Generated-token utility omits this
work. Historical solver seconds plus measured encoder time are descriptive sums;
live co-resident latency, cold setup, contention and full memory accounting remain
untested. Docker has stayed running.

## Gaps and concrete adaptations worth testing conditionally

1. **Target mismatch.** We need expected *benefit of the extra solve*, conditional
   on the solver and actual direct draft. A general state/action relevance score
   and `P(positive gain)` are different targets. Use
   `E[g | state]`, where `g = correct_T − correct_D − .05 × T_tokens/1000`.
   Direct cost is already spent, so it cancels from this action difference but
   remains in policy cost. One interpretable formulation separately predicts
   rescue probability, harm probability and expected thinking tokens. Their
   difference yields utility; predictions still need held-out assessment.
2. **Insufficient supervision and noisy outcomes.** Four hundred drafts are only
   50 independent question groups, with 30 positive pairs on 11 questions.
   Finetuning approximately 18.9M released-head parameters here is poorly
   supported. Start any future adaptation with a tightly bounded small adapter,
   confidence input, and matching supervised controls after obtaining fresh
   opportunity evidence. Do not expand prompts, heads or grids on this panel.
3. **Repeated-action objective.** Naive diagonal in-batch InfoNCE treats duplicate
   action texts as distinct matches. For our two common actions that introduces
   false negatives and ambiguous reverse matches. The **current official choice
   trainer already deduplicates actions and supplies multi-positive reverse
   targets**. Its forward part with two options reduces to soft-target binary
   cross-entropy. Retain that distinction; our synthetic check is not a detected
   upstream bug. Compare any reverse regularizer against forward-only training.
   [Official training code](https://github.com/Contrastive-LM/CLM/blob/main/train/finetune.py).
4. **Regret rather than event majority.** A useful objective control is BCE with
   label `1[g>0]` and weight `abs(g)`. Its population optimum is
   `E[max(g,0)|s]/E[abs(g)|s]` when the denominator is positive; threshold .5 then
   matches the sign of expected gain. It is not a correctness probability.
   This elementary derivation and cost weighting are not novelty. Test paired
   utility and appropriate calibration, rather than calling action softmax
   probabilities calibrated correctness.
5. **Deployment cost.** A conditional CLM stage or distillation into a smaller
   encoder could reduce overhead. These are candidate engineering approaches.
   They require matched quality/cost evaluation, teacher/student and gate
   ablations, and all router calls charged. Distillation or adding a confidence
   gate alone should not be presented as a new contribution.

Other unresolved explanations include quantization/full-precision mismatch,
prompt/action sensitivity, pooled representation limitations and pretraining
overlap. No ablation currently identifies these as causes. Do not attribute the
negative results to quantization or promise that finetuning will fix them.

## Problem statement and defensible novelty boundary

Proposed wording for the project problem statement:

> Given a solver, a question and its completed direct draft, determine when a
> fresh thinking solve has positive expected incremental utility under limited
> supervision. Investigate action-compatible representations, including CLM,
> together with solver confidence and repeated-outcome uncertainty. Develop and
> evaluate a method for allocating supervision between new questions and repeat
> observations, accounting for generation and router inference costs.

This admits CLM while keeping the research question valid if a cheaper control
wins. It avoids assuming that questions have an intrinsic binary thinking label,
or promising gains from the latest release before evidence exists.

The prior-art boundary is substantial:

| Prior work | Overlap that limits our claim |
|---|---|
| [RouterDC](https://arxiv.org/html/2409.19886v1) | Already learns query/model representations with two contrastive losses; its open-ended-query scores average multiple sampled solver responses. Contrastive routing **and repeats** are already present. |
| [CSCR](https://arxiv.org/html/2508.12491v3) | Already trains cost-aware contrastive prompt/model selection. Adding a token penalty to contrastive routing is insufficient. |
| [SEMIROUTER](https://aclanthology.org/2026.eacl-long.228/) | Already targets data-sparse routing and adaptive model integration. Sparse supervision alone is insufficient. |
| [Beyond Repeated Sampling](https://arxiv.org/abs/2609.26704) | Trains an RL concept/search generator against downstream solver success. Its decision problem differs from ours, but RL for directing reasoning compute is not novel by itself. |

Our strongest **candidate** advancement is a specific estimator that decides
whether buying another observation for an uncertain incremental-action value is
more useful than buying a new question, measured by expected decision-regret
reduction per acquired token. The estimator must distinguish sampling noise from
model uncertainty and use only acquired labels. This principle is familiar; its
precise construction, comparison with prior acquisition work and empirical benefit
must establish the contribution. No claim of unique novelty is made yet.

Required evidence: fixed-router equal-token acquisition curves versus uniform,
fixed-repeat, uncertainty and regret/cost baselines; repeat-uncertainty and
representation/objective ablations; multiple acquisition seeds; fresh question
evaluation; full router overhead; replication on another task. If a supervised
control matches CLM, remove the contrastive-specific claim. RL is conditional on
a partially observed or genuinely sequential acquisition problem, with supervised
and contextual-bandit controls where appropriate.

## Tests completed and next action

The full **557-test offline suite** passes. New synthetic tests cover binary
score algebra, duplicate-action ambiguity, regret targets, costs, rank/interval
arithmetic, question disjointness, immutable child preparation, duplicate response
coverage and opposite-draw/held-out-label leakage. An independent automated Luna
review reproduces all six AUROC values, all three paired intervals and the
break-even arithmetic with scikit-learn, plus child provenance. This is not the
waived human scoring audit.

The first audit launcher hit an integration schema error before saving a report.
Its original source and plan remain unchanged. The separately checkpointed
[completion record](clm-audit-completion.md) uses the correct cached summary keys
and exactly the same rank calculations/endpoints. No policy trial, label, original
interval or progression gate changes.

Source checkpoint `b2e4de8`; completion checkpoint `a266621`. Ignored artifacts
under `artifacts/research/data-efficiency-v1/`:

| Artifact | Payload SHA-256 |
|---|---|
| `clm-signal-audit-v1/plan.json` | `048687b3dc9fb5e13fc5f48c8c0eda8638e82972535fd55ca411739b69350846` |
| `clm-signal-audit-v1/completion-v1/plan.json` | `4e0a58e68d04dfa0020287d7d61751f1197f6b944b9fd92fe9e397f12564ba29` |
| `clm-signal-audit-v1/completion-v1/report.json` | `d5010392c5d9560bc2920164d591b9c16ff98635517d0acf1a7b229ed61a26f7` |
| `clm-signal-audit-v1/completion-v1/independent-review.json` | `57604e81493444e723e418453c74ca666078e1fa025c85b97cf50dad54ad1710` |
| `reserve-children/opportunity64-v1/child-manifest.json` | `6d31e6e239fb84313bb6e4a01ca247f443430299cbab1eb83f68c2deeb50c230` |
| `reserve-children/opportunity64-v1/preparation-plan.json` | `300bfbcde120a79c59e20ee3fd3d3c2fe97514b325dd408eae051c321903ee10` |

The [64-question reserve child](opportunity-panel-preparation.md) is now prepared
and verified, superseding its earlier unallocated status. The parent manifest,
source/exclusions and all other roles remain unchanged. Five folds contain
13/13/13/13/12 question groups; `gold_sha256` stays null. This is preparation,
not a completed solver experiment or a sufficiently powered +.01 confirmation.

Next complete Qwen3-0.6B's pinned local asset/tokenizer/closure preflight, then
freeze a separate two-arm collection/scoring/analysis protocol with unique
independent seeds, exact jobs, both-arm completion before reference access,
question-level intervals, and global setup/retry/token/time limits. Generation
remains unstarted. The 786,944-token prospective reservation covers responses
only and assumes two closure tokens; the second solver must verify that assumption.
Primary diagnostic outcomes are rescue/harm structure, accuracy and costs, with a
secondary grouped confidence comparison. Do not spend this panel to confirm a
failed CLM candidate. Acquisition, Jev/RL and confirmation stay stopped pending
fresh evidence and adequate precision; official test stays sealed, Docker runs,
and cloud/API spend remains $0.
