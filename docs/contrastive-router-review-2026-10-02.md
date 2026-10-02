# Research checkpoint: contrastive representations for reasoning routing

Decision date: **2026-10-02**. Reviewed repository checkpoint `3221093` on
`codex/research-data-efficiency`, the completed repeat-panel results, and the
primary sources linked below. This is a research decision record: **no candidate
was fitted, no new generation or reference access occurred, and no model was
downloaded in this review**. Cloud expenditure remains $0.

## Decision

Add a **bounded contrastive-representation investigation** to the roadmap after
parser compatibility and cheap confidence/capacity controls. Keep confidence as
the mandatory comparator. Do not replace the router with CLM-8B, start RL, or
scale acquisition on the current evidence.

We are building a router that sees a question and a completed direct draft, then
decides whether paying for a fresh thinking solve is worthwhile. The research
target is **incremental benefit for this solver**, rather than an intrinsic
easy/hard label. The thinking solver currently receives the question, not the
draft; changing that would define another action and require new data.

The promising publication hypothesis is whether **allocating supervision across
new questions and repeated action outcomes can teach this decision more cheaply**.
Contrastive learning is one candidate component, whose value must be isolated.
Neither this hypothesis nor the combination is an established novelty claim.

## What the completed experiment establishes

The [Phase 2 result record](phase-2-repeat-results.md) remains authoritative.
Collection completed all 800 responses on 50 questions, charging 644,519 tokens
and 8.39463 cumulative local hours including failed attempts and setup. Four of
five predeclared progression gates failed. The four-draw average combined-minus-
training-selected-baseline utility is **−0.016204**, with 90% interval
**[−0.033276, −0.000635]**. This blocks acquisition scaling.

The eight-draw secondary analysis makes the failure mechanism easier to inspect:

| Policy | Accuracy | Generated tokens/question | Escalations / 400 | Positive-gain escalations |
|---|---:|---:|---:|---:|
| Accept direct draft | 89.5% | 221.1 | 0 | 0 |
| Tuned confidence | **92.5%** | **466.9** | 58 | 16 |
| Combined learned router | 89.0% | 799.5 | 174 | 5 |
| Always escalate after draft | 94.5% | 1,611.0 | 400 | 30 |

This is reused-development evidence, not independent confirmation. The final row
includes the direct draft; it is not the cost of standalone thinking.

There are 30 positive-gain paired outcomes on only 11 questions. Repeats yield
400 paired states, but only **50 independent question groups**. The combined
model uses 387 question features plus four draft statistics, with 40 training
questions per outer fold and 30 per inner fit. Excess capacity, representation
mismatch and poor decision calibration are plausible explanations. None is
causally established. Solver-only ridge also loses to confidence, so deleting
question embeddings alone is not a demonstrated fix.

The gold-free syntax audit found five presentation candidates. Fixed-policy
bounds cannot reverse the router comparison on those cases. Parser work matters
for measurement, but does not explain away the failed gate. Hindsight oracle
headroom and same-question label transfer use information unavailable to an
unseen-question router; they are not deployable gains.

## What the linked CLM actually offers

The user's [Sanity glossary](https://www.sanity.io/glossary/contrastive-language-model-clm)
describes the Contrastive-LM release. Technical assessment here uses its primary
repository, model card and implementation rather than the glossary's claims.

The [official CLM repository](https://github.com/Contrastive-LM/CLM) describes a
frozen Qwen3-8B encoder and separate trainable state/action projection heads.
It contrasts a state with candidate actions and can cache action embeddings.
Its reported agentic speed and quality results are author-reported results on
different workloads, not evidence for our two-action GSM8K router.

The [released model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)
specifies encoder-locked, last-token-pooled Qwen3-8B representations. The heads
cannot simply be attached to our MiniLM or Qwen3-1.7B embeddings. Candidate
probabilities are relative scores, not verified probabilities that our solver
will be correct. Some task performance requires task-specific fine-tuning.

The [head implementation](https://raw.githubusercontent.com/Contrastive-LM/CLM/main/src/clm/heads.py)
uses normalized projected vectors and scaled dot products. The
[training code](https://raw.githubusercontent.com/Contrastive-LM/CLM/main/train/finetune.py)
supports per-choice cross-entropy and a bidirectional contrastive objective;
its choice path deduplicates option texts and supports distributions over
targets. A local adaptation must preserve correct multiple-positive handling,
rather than treating other examples with the same action as negatives.

For two fixed actions, our mathematical observation is:

`P(think | state) = sigmoid(score_think − score_accept)`.

Thus the binary choice interface alone does not establish a different learning
capability. Any gain must come from the representation, supervision, training
objective, or acquisition rule. A calibrated scalar margin and a supervised
head on identical embeddings are essential controls.

There is also an important existing baseline: our
[`all-MiniLM-L6-v2` encoder](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
already underwent contrastive sentence-pair training. It is a 384-dimensional
semantic encoder, with a default 256-wordpiece input limit. The proposed change
is to align representations with action utility and include draft content;
it is not the project's first use of contrastive pretraining. New draft
features need a pinned truncation policy that preserves relevant answer text.

### Feasibility and full inference cost

An 8B backbone is a substantial evaluator for a 1.7B solver. At two bytes per
parameter, roughly eight billion weights alone occupy roughly 16 GB, before
activations, the solver and other applications. This is a storage estimate,
not a benchmark. It makes unquantized simultaneous deployment inappropriate as
the default on this 16 GB Mac, especially with Docker kept running.

Cached action vectors still leave state encoding on every new draft. Head size
and generated-output-token count do not capture that cost. Quantization, an
alternative runtime or remote evaluation would need its own pinned compatibility
and resource preflight; none is launched here. The
[embedding recipe](https://raw.githubusercontent.com/Contrastive-LM/CLM/main/train/embed_utils.py)
also makes pooling and input formatting part of reproducibility.

Keep the frozen generated-token utility for historical comparability. Report
router encoder work, input tokens, cold/warm latency, memory, training cost and
API expenditure separately. Do not convert milliseconds or evaluator FLOPs into
solver output tokens without an explicitly frozen conversion. A deployment
claim needs measured end-to-end advantage, including router overhead.

## Prior art that restricts the novelty claim

| Primary source | Relevant overlap | Implication for this project |
|---|---|---|
| [RouterDC, NeurIPS 2024](https://arxiv.org/abs/2409.19886) | Query–model and query–query contrastive routing; its methodology includes repeated sampled responses for quality supervision and multiple positives. | Contrastive routing and using repeats to supervise routing are already established ideas. |
| [Cost-Spectrum Contrastive Routing, 2025 preprint](https://arxiv.org/abs/2508.12491) | Shared prompt/model representations with a cost-sensitive contrastive objective and cost-banded positives. | Adding a token penalty to contrastive routing is insufficient novelty. Its dynamic model-pool setting differs from our draft-conditioned two-action problem. |
| [SEMIROUTER, EACL 2026](https://aclanthology.org/2026.eacl-long.228/) | A fully observed anchor-model dataset plus sparse observations for additional models; an adapter combines contrastive and prediction losses. | Sparse-data contrastive routing already exists. Its anchor-data assumption and new-model adaptation differ from acquiring noisy repeated outcomes for one solver's modes. |
| [Jev / System One](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | Structured decisions and probability outputs; vendor workflow evaluations use other models' probabilities as references. | Relevant decision-system inspiration, but that evaluation does not establish calibration for our solver's incremental correctness. |

These differences identify comparisons to investigate, not proof that our
combination is new. The [September research review](research-review-2026-09-24.md)
and [roadmap](research-roadmap.md) retain additional boundaries from thinking
selection, confidence stopping, active routing and cost-aware policy learning.
For example, [DART](https://arxiv.org/abs/2606.23181) uses direct-draft agreement
and adaptive thinking budgets; a later matched comparison must charge its extra
drafts. Do not compare its published numbers directly with our protocol.

CLM's repository/model card/code are accessible primary release materials. The
linked Notion write-up could not be retrieved during this review. We have not
independently reproduced CLM's benchmark claims or established training-data
disjointness with GSM8K. Pretraining exposure is an additional confound when
comparing its larger backbone with MiniLM.

## Revised execution sequence

The phase order below replaces immediate acquisition scaling. Detailed protocols
must be frozen before execution; these are proposed study boundaries, not new
results or permission to alter existing allocations.

| Phase | Concrete deliverable | Decision boundary |
|---|---|---|
| **2a. Parser compatibility** | One separately versioned gold-free preflight, with valid and adversarial fixtures for units, context, emphasis, negation and alternatives. Preserve rejection of incomplete and multi-answer outputs. | Retain v7 if a generic compatible improvement cannot be demonstrated. A failed candidate is a completed preflight, not a reason for an indefinite parser search. Preserve all primary labels; any later sensitivity is a separate authorized sidecar. |
| **2b. Cheap capacity and calibration** | Freeze a bounded CPU grid around confidence, solver-only gain prediction, question-feature compression/scaling and conservative corrections. | Check whether capacity/calibration changes improve targeted interventions on existing data. All results remain exploratory. |
| **2c. Representation versus objective** | Compare question-only with question-plus-draft features, then compare supervised and contrastive action heads on identical frozen representations. | Advance at most one prespecified selected candidate. If useful signal is absent, stop architecture expansion. |
| **2d. Optional released CLM probe** | Only with a feasible resource plan: frozen CLM action margin, plus a matched raw-Qwen3-8B embedding/supervised-head control. | Separate a better backbone from a better contrastive head. Count complete runtime overhead; no default 8B local deployment or fine-tuning. |
| **2e. Fresh signal test** | Freeze candidate, comparator, scorer, endpoints, sample-size calculation and new question-role protocol before outcomes. | A genuinely fresh result must support practical value before acquisition scaling. Preserve the 200 validation, 2,000 confirmation, official test and old confirmation roles. |
| **3–4. Acquisition method** | Equal-budget comparison of which question/action/repeat to buy, using the selected fixed router architecture. | Demonstrate the stated learning-curve benefit against strong acquisition baselines and component ablations. |
| **6. Replication and paper** | A second task and, for cross-model claims, a second solver; frozen final comparison and full cost accounting. | Scope claims to what replicates. A careful negative result is possible; publication is not guaranteed. |

Do not treat the earlier week labels as a renewed completion promise. New data
and CLM feasibility can change the schedule; the $100 total cloud ceiling does
not increase. Phase 2d is optional and must not block the cheap investigation.

### Proposed bounded CPU grid

Before fitting, freeze exact configurations, seeds, feature recipes and maximum
fit count in an additive protocol. Suggested small family set:

1. Always accept, always escalate, and the original tuned confidence policy.
2. The frozen solver-only and combined ridge learners as historical controls.
3. A four-draft-feature gain ridge with three fixed stronger regularization
   settings, selected within training folds, and a conservative threshold.
4. The same model with question embeddings reduced to eight components using
   training-fold-only PCA and a fixed feature-block scale.
5. For the representation slice, replace question-only text with a fixed
   question-plus-draft representation using the existing cached MiniLM encoder.
   Keep head capacity and all other inputs matched; record truncation rates.
6. On that same representation, compare a low-capacity gain head with a
   parameter-matched two-action contrastive head. Include ordinary binary
   cross-entropy as the objective control; do not train the released large CLM
   heads on these 50 question groups.

Items 5–6 are a separately recorded slice, not an open-ended expansion after
each disappointing score. A new feature extractor can read permitted direct
text, but never thinking text, future token counts or correctness as inputs.
Predeclare any confidence fallback rule, margin threshold or action wording;
tune only on acquired training-half labels. Avoid outcome-selected paraphrase
searches over action descriptions.

The decision target remains

`g = correct_thinking − correct_direct − 0.05 × thinking_tokens / 1000`.

Direct tokens are already spent, so they cancel in the action difference but
remain in total policy cost. At inference, actual thinking correctness and cost
are unknown. Estimate expected gain from available state.

A useful supervised control is regret-weighted binary cross-entropy with label
`1[g > 0]` and weight `abs(g)`. At the population optimum, its decision threshold
corresponds to the sign of expected gain: the difference of positive and negative
weighted mass is `E[g | state]`. This is our elementary objective calculation,
not a novelty claim or a guarantee of finite-sample calibration. A probability
of positive gain alone ignores the magnitude of harm and cost.

More precisely, the optimal weighted score is
`E[max(g, 0) | state] / E[abs(g) | state]` when the denominator is nonzero.
It is not `P(g > 0 | state)` or a correctness probability. Use ordinary event
calibration diagnostics only for heads targeting that event, and evaluate
weighted action scores through their stated weighted loss and decision utility.

For repeated labels, estimate quantities only from the acquired training half.
All combinations of direct and thinking draws are not independent samples.
Keep all draws, text augmentations and related features of a question in one
outer fold; fit PCA, normalization, calibration and thresholds inside each
training fold. The opposite draw half remains evaluation-only for that direction.

Report both A→B and B→A results, their average, whole-question uncertainty,
accuracy, tokens, escalation rate, rescued/harmed drafts and missed positive
gains. Keep full8 secondary. Include fold-level results and influential-question
diagnostics; do not remove inconvenient questions. If reporting calibrated
probabilities, include held-out proper scoring and calibration diagnostics, with
the limitation of only 50 question groups.

Suggested exploratory promotion screen: average utility improvement of at least
0.01 over confidence, positive point differences in both four-draw directions,
and no obvious single-question or cost-accounting dependence. Freeze the precise
rule before fitting. This screen only prioritizes a fresh test: retrospective
question-held-out evaluation and its intervals cannot restore the failed Phase 2
gate, remove researcher selection effects or establish confirmation.

Fresh sample size must follow a question-level variance/power calculation and
a compute budget. Do not assume another 50 or 100 questions can detect a
one-point utility effect. A subset of the 548 reserve questions is a possible
source only through a new versioned role protocol preserving the old manifest;
no IDs are allocated or references opened here. If adequate precision is
unaffordable, report the limitation and stop short of a superiority claim.

## Candidate contribution and required evidence

The strongest current candidate is **noise-aware acquisition of supervision for
incremental thinking benefit**. Specifically, test whether uncertainty in
action-value rankings can determine when another repeat is more useful than a
new question, and whether reliable rankings improve a small action-compatible
representation. The acquisition score would estimate expected reduction in
decision regret per purchased token. This generic principle overlaps prior work;
the repeat-allocation estimator and its empirical benefit must supply the actual
advancement.

A credible method result needs all of the following:

- The router beats confidence on fresh questions after reporting full overhead.
- Equal acquired-token comparisons beat uniform, fixed-repeat, uncertainty and
  regret-per-cost acquisition, with the same router and initial data.
- Removing repeat uncertainty or the contrastive objective reduces the claimed
  benefit. If supervised heads work equally well, drop the contrastive claim.
- Adaptations of RouterDC/CSCR-style objectives are distinguished from faithful
  reproductions; the richer anchor assumptions of SEMIROUTER are disclosed.
- Gains survive the planned three acquisition seeds and a second task. Additional
  solver evidence is required before claiming general reasoning-mode routing.

The existing normalized-AULC endpoint at λ=.05 remains the main acquisition
proposal; it is not replaced post hoc by whichever accuracy/cost metric improves.
If no acquisition method wins, a narrower empirical contribution could explain
when semantic/action representations fail to predict stochastic reasoning gain
beyond confidence, using repeated outcomes and multiple settings. That would
require broader evidence than this single 50-question panel.

RL remains deferred. This is currently one decision with paired supervised
outcomes, so supervised action-value learning is the necessary comparator.
Contextual bandits become relevant if only purchased actions are observed;
sequential RL requires a genuinely sequential decision problem. Neither adds
novelty merely by replacing the optimizer. Jev remains an optional separately
costed comparator, not the central method.

## Immediate implementation boundary

Next implement **2a**, then freeze **2b** before fitting. Keep work traceable on
the current research branch with separate protocol/code/result checkpoints.
No edits to frozen package sources, completed collectors, journals, scorer v7 or
primary reports. No ordinary scoring command, new references, sealed labels,
large model download, external API call or new solver generation is part of
this checkpoint. Docker stays running.
