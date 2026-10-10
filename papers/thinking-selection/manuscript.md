# Confidence and Learned Thinking Selection on GSM8K: A Controlled Study of Small Qwen3 Models

**Authors:** [Author names and affiliations to be supplied]

**Draft:** 0.2 working draft, 10 October 2026 — R2–R3 revised; R4–R6 pending

## Abstract

When do repeated thinking outcomes support useful selection on new questions? We study this question on GSM8K with small Qwen3 models. After one paid direct draft, a policy accepts the draft or requests a fresh thinking solve. Utility charges both calls when thinking is selected. On 50 questions with 800 responses, thinking produces 30 scored rescues and 10 harms across 400 paired states. The predeclared learner nevertheless fails four of five progression criteria. Its average utility difference is −0.016204 against a simple baseline selected within training. The conditional 90% interval is [−0.033276, −0.000635]. Separate post-hoc diagnostics suggest between-question gain variation and report positive same-question transfer point estimates, although one transfer interval crosses zero. These diagnostics neither reverse the failed primary reproducibility test nor establish useful selection on unseen questions. Bounded capacity, objective, and quantized representation controls also fail their screens. The flagged presentation cases alone cannot reverse the primary fixed-policy point comparison. A separate two-solver diagnostic and sparse parser-guard and cap follow-ups have narrower outcomes and limited supporting events. The main finding is the coexistence of observed thinking opportunities, limited repeat-structure evidence, and unsuccessful held-out-question selection by the tested learners. This is evidence about specified recipes on reused panels. Conditional uncertainty, one task, one model family, and scorer-based correctness limit its interpretation.

**Keywords:** adaptive reasoning; model routing; repeated supervision; confidence; evaluation; computational cost

## 1. Introduction

An extra thinking response can correct a direct answer, repeat its error, or replace a correct answer with an incorrect one. A useful selector must predict whether the added response is worth its cost from information available before that response.

Three levels of evidence bear on this decision. Observed rescues show that an extra call sometimes corrects a draft. Repeated outcomes on the same questions can reveal question-level variation in gain. A learned policy must then use permitted features to select actions on questions excluded from fitting. Success at one level does not establish success at the next.

We study a specific decision. A small Qwen3 model first produces a direct draft. A router then accepts that draft or requests a fresh thinking solve from the same model. The thinking call receives the question; it does not continue or revise the observed draft. The direct cost has already been incurred. This contract makes escalation more expensive than using a thinking response alone.

We use GSM8K, a dataset of mathematical word problems introduced by [Cobbe et al. (2021)](https://arxiv.org/abs/2110.14168v2), and the thinking and non-thinking modes of [Qwen3 (Yang et al., 2025)](https://arxiv.org/abs/2505.09388v1). Our question is: **what do observed rescues and repeated question-level outcomes tell us about the specified selectors' performance on held-out questions?** We compare these evidence levels under one fixed decision and cost contract.

The central study collects eight responses per mode on 50 Qwen3-1.7B questions. Question folds exclude evaluation questions from fitting and tuning. Two disjoint response halves supply different realizations of training and evaluation outcomes. Separate same-question diagnostics examine gains across those halves. The halves reuse question groups, and each draw has a different direct draft. They do not supply two independent study replications or repeated thinking outcomes for one identical draft state.

The original learner fails its criteria, including the primary reproducibility criterion. Later post-hoc estimates suggest some between-question gain variation and positive same-question transfer points. One transfer interval includes zero. These observations concern labels from already measured questions and omit their acquisition cost. At the same time, the tested learner does not improve selection on held-out questions. Later bounded controls also fail their screens on this reused panel.

The paper reports three scoped findings:

1. Observed rescues and limited post-hoc repeat structure coexist with a negative primary learned-policy comparison. The repeat diagnostics do not establish a successful router or reverse the failed primary tests.
2. The bounded capacity, compact objective, and released-representation recipes do not establish an improvement over confidence. These results restrict those recipes under the recorded training conditions.
3. The flagged presentation cases cannot reverse the primary fixed-policy point contrast. This narrows one possible scorer explanation while leaving unflagged errors and refitted policies unresolved.

Supporting studies test different questions. A separate 64-question diagnostic finds different opportunity and confidence-utility patterns for Qwen3-0.6B and Qwen3-1.7B. A parser guard motivated by development results is refitted and frozen before a 228-question test; only one fresh action changes, with no scored rescue. A cap intervention on 11 selected development questions produces one rescue and lower point utility. These are scope checks with distinct endpoints, rather than replications of the central learner comparison.

Prior work already studies repeated supervision, contrastive and post-draft routing, stochastic ceilings, and the difference between failure risk and action value. Our contribution is a local empirical account of the three evidence levels under this protocol. The studies do not identify why the learners fail or establish a new general principle. Their preserved criteria and records support inspection of that limited finding.

## 2. Related work

### 2.1. Routing and adaptive reasoning

[RouterDC (Chen et al., 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7a641b8ec86162fc875fb9f6456a542f-Abstract-Conference.html) learns query/model and query/query contrastive objectives. Its open-ended supervision averages sampled responses. Repeated solver labels and contrastive routing therefore precede this study. [Cost-Spectrum Contrastive Routing (Shirkavand et al., 2025)](https://arxiv.org/abs/2508.12491v3) adds cost-sensitive selection in a shared representation space. [SEMIROUTER (Wang et al., 2026)](https://aclanthology.org/2026.eacl-long.228/) studies sparse supervision and adaptation to changing model pools.

Adaptive reasoning methods also change the decision space. [Thinkless (Fang et al., 2025)](https://arxiv.org/abs/2505.13379v2) uses reinforcement learning to select reasoning behavior. [DART (Lee et al., 2026)](https://arxiv.org/abs/2606.23181v4) uses agreement between two direct drafts and predicts a reasoning budget when they disagree. [BEST-Route (Ding et al., 2025)](https://arxiv.org/abs/2506.22716v1) selects a model and an inference sample count. Our main comparison fixes one paid direct draft and two subsequent actions. The controls in this paper do not reproduce these full systems.

Our compact representation uses the released [all-MiniLM-L6-v2 model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), which already has contrastive sentence-level training. The objective study changes a small routing head; it does not compare contrastive pretraining with its absence. The separate released-CLM diagnostic uses state/action heads documented in the [official CLM release](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B). We cite that system as an author release and implementation. We do not assign it an unverified proceedings publication.

### 2.2. What routing evaluations identify

The closest empirical work limits several possible novelty claims. [Chen (2026)](https://arxiv.org/html/2607.03436v3) distinguishes stochastic routing ceilings from hindsight unions and examines coupling and scorer choices. [Garg and Sagtani (2026)](https://arxiv.org/html/2605.07395) study judging, truncation, formatting, and routing collapse. [Yang et al. (2026)](https://arxiv.org/html/2608.14927) hold a solver fixed and distinguish failure-risk prediction from the payoff of a collaboration protocol.

We share these concerns. Our comparison supplies evidence under a different operational contract and a specified repeated-draw evaluation. Later follow-ups have narrow targets: one estimates a policy difference from changed actions, and one estimates a cap effect on a selected cohort. These designs do not turn reused data into confirmation. Their value is to state what each comparison identifies and retain its result when progression fails.

## 3. Decision contract and evaluation

### 3.1. Accept a draft or buy a fresh solve

Let \(D\) be a completed direct response and \(T\) a fresh thinking response. Let \(Y_D,Y_T\in\{0,1\}\) denote correctness under the frozen scorer. Let \(C_D,C_T\) denote charged output tokens, including inserted closure tokens. An action \(a=1\) requests thinking; \(a=0\) accepts the draft. We use

\[
U(a)=Y_D+a(Y_T-Y_D)-\lambda(C_D+aC_T)/1000,\qquad \lambda=0.05.
\]

The incremental gain target is

\[
G=Y_T-Y_D-\lambda C_T/1000.
\]

The direct cost cancels in \(G\), but remains in total policy utility. A rescue means that a scored incorrect draft is replaced by a scored correct response. A harm is the reverse. Positive utility gain is a cost-dependent event. It is not a general label that a question “needs thinking.”

The value \(\lambda=.05\) is the frozen cost preference for these studies. Utility counts generated and inserted output tokens used by a policy. It excludes input processing, router encoding, energy, and complete latency. Collection-ledger charges in Appendix A also include failed attempts and unresolved reservations; they measure a different expenditure.

The router can use the question, the permitted features of the observed direct draft, and fixed model information. It cannot use the future thinking text, thinking correctness, thinking length, or reference answer. Confidence is the mean direct-answer token log probability after temperature and sampling filters. It is a ranking feature, not a calibrated probability of correctness. Lower confidence can trigger escalation. Raw model confidence is retained as a separate measurement and does not replace the primary feature.

### 3.2. Data, solvers, and scoring

All reported new question panels come from eligible GSM8K upstream training rows. Roles are frozen and checked for identity and normalized-prompt overlap. The project's official-test allocation is sealed. Neither reserved confirmation study contributes results to this paper. Question separation in these experiments does not establish separation from model pretraining.

The primary repeat study uses Qwen3-1.7B. The two-solver diagnostic adds Qwen3-0.6B. Both retain the same boxed-answer prompt and the specified mode interface. The normal reasoning allowance is 2,048 tokens, followed by an answer allowance of 512 tokens. Forced closure, when needed, is charged. Exact revisions and study contracts are listed in Appendix A.

The main routing studies use the frozen numeric-v7 scorer. Incomplete or rejected outputs count as incorrect under that endpoint. Parser acceptance alone does not certify mathematical correctness. A separate gold-free compatibility study examined presentation handling without replacing primary labels. Human answer scoring was explicitly waived. Consequently, our reported correctness is scorer-based correctness.

For the repeat, two-solver, sparse, and cap studies, selected training references were accessed only after the applicable full endpoint and required completion checks. Later manuscript preparation uses completed reports. The earlier engineering bridge has a different reference-materialization history, stated in Appendix A.

### 3.3. Evidence units and chronology

Table 1 separates unique questions, responses, and the use of each panel. A fit is not a new dataset. A repeated draw is not a new independent question. The paper's organizing research questions were formulated retrospectively; the individual studies' recorded grids, endpoints, and progression criteria were specified before their respective execution.

**Table 1. Evidence blocks and their scope.** The control studies reuse the repeat panel; their fit counts do not add independent questions. The cap questions are a subset of the two-solver panel. The fresh guard contrast uses a separately fitted and frozen policy.

| Block | Questions and responses | Evaluation or use | Main limit |
|---|---|---|---|
| Repeated supervision | 50 questions; 800 responses; eight draws per mode | Five question folds; independent response halves | Small diagnostic panel |
| Capacity, MiniLM, and CLM controls | Same 50 questions and cached responses | Later bounded development studies with the same folds/halves | Research reuse; no new confirmation |
| Two-solver diagnostic | 64 separate questions; 512 responses | Two draws per mode and solver; thresholds fitted on other questions and the opposite draw | One model family; two draws |
| 0.6B learned pilot and parser control | Same 64 questions; 128 paired outcomes | Fixed candidate and controls; training-only fitting | Reused development panel |
| Fresh sparse parser-guard contrast | 228 disjoint questions; 228 direct and one activated thinking response | Policies frozen before fresh collection | Only the policy difference is identified |
| Matched cap intervention | 11 selected questions from the 64-question panel; 18 pairs and 36 new responses | Same question/seed, 2k versus 4k reasoning allowance | Enriched development cohort |

### 3.4. Independent response halves and grouped selection

In the repeat panel, each question has eight independently seeded responses in each mode. Direct and thinking seeds differ. Responses are paired by sample index for replay; we do not form all \(8\times8\) combinations. Half A contains indices 0–3 and half B contains indices 4–7.

For \(k\in\{1,2,4\}\), the learner fits on the first \(k\) draws of training questions from one half. It is evaluated on all four draws of held-out questions from the opposite half. We report both A→B and B→A. Five outer folds each contain ten questions. Four inner question folds select settings using only the allowed training-half outcomes.

All outcomes for an outer evaluation question are excluded from its model fitting and tuning. The opposite halves check sensitivity to different realizations of training and evaluation draws. Both directions reuse the same question groups and exchange their draw roles. They are not independent study replications, and no matched comparison establishes an advantage from the half-split design itself.

A separate reproducibility diagnostic predicts each question's opposite-half mean gain from its own source-half mean. Its comparator uses the mean gain of the other 49 questions in that source half. We average the reduction in mean squared error across both directions. This diagnostic concerns repeated question-level signal; it is distinct from router utility on held-out questions.

Direct drafts change across draws. Thus the same-question diagnostics concern repeated outcomes for a question, rather than repeated thinking outcomes conditioned on one identical draft. Neither these diagnostics nor the k=1/2/4 comparisons isolate the causal effect of acquiring more repeated labels.

The predeclared learner is combined Ridge regression on 387 question features and four draft features. The question block consists of 384 MiniLM coordinates and three lexical features. The draft block consists of confidence, log answer length, parser validity, and truncation. Standardization is fitted within training folds. The original Ridge penalty grid is \(\{1,10,100\}\). The learner escalates when predicted incremental gain is positive. Question-only and draft-only variants are diagnostics.

The original simple comparator is selected within training from always accept, always escalate, and a confidence threshold. This differs from later controls, which compare directly with confidence. A secondary full-eight analysis trains on all eight draws of training questions and tests on all eight draws of held-out questions. It has no independent same-question eight-draw replica.

### 3.5. Uncertainty and progression

Repeat and router-control intervals use 2,000 whole-question bootstrap resamples and two-sided 90% intervals under each study's frozen seed. Actions and fitted policies remain fixed. These are resampling summaries of the recorded question-level policy differences. They omit variation from refitting, threshold selection, new training draws, optimization seeds, and the research path. They provide no simultaneous coverage across the displayed comparisons. The fresh sparse and cap studies retain their original 95% interval convention.

Outer-fold models share training questions. Resampling whole evaluation questions preserves their repeated-outcome groups, but does not reproduce the dependence created by overlapping training sets. Nested selection controls which labels enter each specified fit. It does not remove later research reuse. Consequently, an interval below zero does not by itself establish inferiority of the learning algorithm across future training sets. Sparse-event limitations require an additional qualification in Section 5.3.

The primary repeat study requires all five criteria in Table 2. CPU, MiniLM, and CLM screens require average utility gain of at least .01, positive means in both directions, and a positive averaged mean after deleting each question in turn. The two-solver diagnostic requires at least ten positive-gain questions, plus confidence gain of at least .01 and positive points in both directions. Its positive-gain count differs from the repeat study's count of any correctness difference. Sparse validation requires gain of at least .01 and a positive lower 95% interval bound.

The progression criteria are related decisions on the same outcomes, rather than independent tests of one mechanism. Later screens cannot replace a failed primary endpoint. We report all original decisions. A favorable secondary result does not promote a different candidate after outcomes.

## 4. Repeated supervision and representation controls

### 4.1. Observed rescues and a failed primary learner

Across the 400 paired states, direct accuracy is 89.5% and standalone thinking accuracy is 94.5%. There are 30 rescues, 10 harms, 348 pairs where both responses are correct, and 12 where both are wrong. These counts establish realized opportunities on the 50 measured questions. A selector must still predict useful actions without observing the future thinking outcome.

The combined learner's averaged four-draw difference against the training-selected simple comparator is −0.016204, with a conditional 90% interval of [−0.033276, −0.000635]. Four of five progression criteria fail.

**Table 2. Original repeat-study criteria.** The interval for reproducibility measures squared utility units. Other gain rows measure utility. Intervals are conditional 90% summaries on the same 50 questions. Learner utility is compared with the simple baseline selected within training, not an assumed confidence policy in every condition.

| Criterion | Recorded result | Decision |
|---|---|---|
| Positive four-draw reproducibility improvement with positive interval lower bound | MSE improvement +.01158; 90% interval [−.01744, +.04848] | Fail |
| Positive combined-minus-baseline gain in both four-draw directions | A→B −.02679; B→A −.00562 | Fail |
| Average four-draw gain at least +.01 with positive interval lower bound | −.016204; [−.033276, −.000635] | Fail |
| No reversal in the secondary full-eight comparison | −.05163; [−.07286, −.03204] | Fail |
| At least ten informative questions with a correctness difference | 14 of 50 | Pass |

The smaller training conditions also vary across directions. With one draw, differences are −.02016 and +.00641. With two draws, they are −.02812 and +.02257. These conditional point estimates do not establish a monotonic learning curve or show that repeated supervision is generally harmful.

**Box 1. Post-hoc question structure and bounded scorer sensitivity.** These separately reported diagnostics reuse the completed repeat panel and its recorded labels. The intervals are conditional whole-question summaries. The scorer sensitivity is a point bound, not an interval. These diagnostics do not replace Table 2 or change its decisions.

| Diagnostic | Recorded result | Interpretation limit |
|---|---|---|
| Signed between-question gain variance | .03233 utility²; conditional 90% interval [.00541, .06530] | Suggests between-question variation under approximately IID/exchangeable within-question draws. It is a different statistic from the failed primary MSE test. |
| Same-question action selection using A, evaluated on B | Gain over accepting direct +.04413; 90% interval [.00563, .08845] | Uses prior labels of those same questions; label-acquisition expenditure is omitted. |
| Same-question action selection using B, evaluated on A | Gain over accepting direct +.01572; 90% interval [−.02019, .05908] | The interval crosses zero. Different directional point estimates do not establish a statistically tested directional difference. |
| Fixed-policy sensitivity to five flagged presentation cases | Averaged four-draw learner-minus-baseline point difference stays −.016204 | Keeps actions and costs fixed. It does not cover unflagged scorer errors or refitted policies. |

The variance estimate subtracts estimated within-question sampling variation from variation in question means and is deliberately left unclipped. Its interpretation depends on the stated draw assumptions. The same-question comparisons use four draws to select an action and evaluate it on the opposite half. Acquiring the labels in A and B used 322,882 and 321,508 tokens, respectively. Those costs are absent from the reported transfer gains. The comparisons therefore provide neither net acquisition utility nor performance on unseen questions.

The scorer bound asks whether any subset of five flagged rejected outputs becoming correct could reverse the primary comparison. Both policies choose the same final mode on those affected draws, so the primary point difference is unchanged. Including a sixth unmarked-terminal case can only worsen that difference. These are fixed-policy point bounds, not confidence intervals or general validation of mathematical scoring. The [completed diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation) and [syntax-bound record](../../docs/phase-2-repeat-results.md#gold-free-parser-triage-and-bounded-sensitivity) supply these results.

Taken together, the observations suggest some structure on measured questions while the primary learner fails on held-out questions. The data do not establish that the permitted features can recover that structure, or identify the reason for the gap. The failed primary reproducibility criterion remains part of this conclusion.

#### Secondary full-eight behavior

The full-eight results help describe the failure. Combined Ridge escalates on 174 of 400 states, with five positive-gain decisions and 169 nonpositive decisions. The latter include seven harms. Confidence escalates on 58 states, with 16 positive-gain decisions and 42 nonpositive decisions, including four harms. Combined Ridge misses 25 positive opportunities; confidence misses 14. These are descriptive counts on the reused panel.

The full-eight confidence policy reaches 92.50% accuracy at 466.88 tokens per state. Combined Ridge reaches 89.00% at 799.49 tokens. This secondary confidence endpoint must not be substituted for the four-draw confidence endpoint below.

### 4.2. Bounded capacity and objective controls

The capacity study tests stronger regularization, compressed question features, and conservative corrections to confidence. Its fixed grid contains 1,035 Ridge fits and 75 PCA fits across the two four-draw directions and secondary full-eight condition. All preprocessing and configuration selection remain within training questions.

The compact neural study crosses two representations with four objectives. The representations are the question vector and a normalized mean of separate question and direct-draft vectors. Training-only PCA produces eight coordinates. Four draft statistics are added. Every objective uses the same 120-parameter head: an affine 12→8 projection and two learned eight-dimensional action prototypes, with normalized cosine scores.

The objectives are gain mean-squared error, regret-weighted forward cross entropy, a bidirectional contrastive loss, and ordinary binary cross entropy. Full-batch Adam runs for 100 epochs at learning rate .01 and weight decay .001, with one fixed optimization seed. The grid contains 600 head fits and 150 PCA fits. This is a compact objective comparison, not an unrestricted architecture search.

The losses target different quantities. We compare the utility of their selected actions; their scores are not interchangeable calibrated probabilities. The shared head controls this particular architecture and optimization recipe.

Neither training-selected family improves on confidence (Table 3). All eight neural family point differences are negative, although some individual intervals include zero. Draft encoding retains the final 256 tokens; 111 of 400 drafts are truncated. Mean-vector fusion, compression, truncation, and one optimization seed constrain the result.

### 4.3. Released CLM with a matched encoder control

We separately evaluate released CLM heads on pinned 4-bit Qwen3-8B last-token representations. The heads are not fine-tuned. The state includes the question, direct draft, and fixed decision metadata. It excludes thinking output, outcome labels, future thinking cost, and confidence.

The comparison includes zero-shot released scores, scalar gain calibration, and a PCA8/Ridge control on the same encoder representations. The learned families do not add draft statistics. They use the same permitted training data and grouped selection rules. A matched backbone controls the encoder identity; differing head capacity, training history, and feature dimensions prevent isolation of a contrastive-pretraining effect.

The CLM state and learned families exclude confidence and auxiliary draft statistics. This tests the specified representation-transfer recipes. It does not test whether adding CLM features to confidence improves selection.

**Table 3. Average across A4→B4 and B4→A4 on the same 50 questions.** Tokens include the paid direct draft and any inserted closure. Differences are against the four-draw confidence policy, distinct from the secondary full8 policy. Intervals keep fits and actions fixed and do not provide joint coverage or refitting uncertainty. All listed learned/transfer screens fail.

| Policy | Accuracy | Tokens/state | Utility difference | Conditional 90% interval |
|---|---:|---:|---:|---|
| Confidence | 92.75% | 628.47 | Reference | — |
| Training-selected CPU family | 90.75% | 514.22 | −.014287 | [−.025680, −.004425] |
| Training-selected compact neural family | 89.25% | 604.82 | −.033817 | [−.052515, −.017266] |
| Released CLM, zero-shot | 94.75% | 1,550.53 | −.026103 | [−.058826, +.016513] |
| Released CLM, calibrated | 88.50% | 443.71 | −.033262 | [−.053818, −.015171] |
| Same encoder, PCA8/Ridge | 89.00% | 330.81 | −.022617 | [−.043758, −.004464] |
| Training-selected CLM/raw family | 88.75% | 406.34 | −.028893 | [−.049575, −.010922] |

Calibrated CLM minus the raw encoder control is −.010645, with interval [−.018190, −.004292]. Both remain below confidence. Zero-shot CLM chooses thinking for 380 of 400 drafts. Its higher accuracy therefore comes with near-always-escalating cost. The interval for its utility difference includes zero; this is not proof of a population disadvantage.

The encoder processes all 400 states without truncation at the specified cap. Mean state encoding time is 1.427 seconds and the 95th percentile is 2.244 seconds. Output-token utility does not charge this work. These separate encoder measurements are not end-to-end router/solver latency. Full-precision equivalence, pretraining overlap, and live solver/router co-residence remain untested. The finding concerns this quantized transfer recipe.

## 5. Solver dependence and prospective follow-up

### 5.1. Opportunities differ across the two tested solver sizes

The separate diagnostic uses the same 64 questions for both solvers, with two draws per mode. Confidence thresholds are selected on other question folds and the opposite draw. Table 4 reports average outcomes across the two directions.

**Table 4. Two-solver diagnostic.** Each solver has 128 scored paired states grouped in the same 64 questions. Values average the two directions; reported contrasts use conditional 90% question-bootstrap intervals with actions fixed. They omit threshold-refit uncertainty. Always escalate includes direct plus thinking cost. Tokens from the two solver sizes are not equal compute units.

| Solver | Policy | Accuracy | Tokens/state | Utility |
|---|---|---:|---:|---:|
| Qwen3-1.7B | Accept direct | 84.375% | 228.01 | .832350 |
| Qwen3-1.7B | Always escalate | 87.500% | 1,586.79 | .795661 |
| Qwen3-1.7B | Confidence | 83.594% | 682.56 | .801809 |
| Qwen3-0.6B | Accept direct | 61.719% | 209.80 | .606697 |
| Qwen3-0.6B | Always escalate | 80.469% | 1,409.52 | .734211 |
| Qwen3-0.6B | Confidence | 81.250% | 1,062.52 | .759374 |

Qwen3-0.6B has 24 questions with positive realized gain in at least one of its two draws. Confidence-minus-direct utility is +.152677, with conditional 90% interval [+.085535, +.220375]. Qwen3-1.7B has four such questions. Its confidence-minus-direct difference is −.030540, with interval [−.056066, −.006071]. The smaller solver passes the diagnostic's availability and confidence screens; the larger solver fails both.

The positive-gain count depends on the number of sampled draws. It does not count questions known to have positive expected gain. Counts from this two-draw panel and the eight-draw repeat panel cannot be treated as directly comparable intrinsic opportunity rates.

The comparison establishes different observed opportunity patterns in these settings. It does not establish a general model-size law or a tested population interaction. It also limits a broad endorsement of confidence: confidence helps on one solver/panel combination and harms point utility on another.

Accepting the larger model's direct draft also has higher point accuracy and fewer generated tokens than the smaller model's confidence policy. These token counts are useful context, but tokens from different model sizes are not equal units of compute. No live cross-size latency or energy advantage is established.

### 5.2. A small learned pilot and a sparse favorable control

On the reused 0.6B panel, a fixed Ridge candidate uses confidence, log(1 + answer-token count), and v7 parser rejection. It uses training-only standardization, penalty α=10, and escalation at predicted gain greater than zero. There is no inner parameter search. Its average utility difference is +.003516 against the frozen confidence decisions, with conditional 90% interval [−.031959, +.037163]. Its two directional means are positive, and it beats a matched confidence-only Ridge learner. It fails the required .01 margin and loses to the parser-aware confidence control. Two of four criteria fail.

The parser-aware control escalates when confidence calls for thinking or the frozen parser rejects the direct draft. It adds three escalations on three questions, all scored rescues. Accuracy rises from 81.250% to 83.594%, tokens from 1,062.52 to 1,081.41, and utility by .022493. The fixed-action 90% interval is [+.007453, +.044905].

This is sparse development evidence. The interval keeps the original confidence actions fixed and omits refitting and research-selection uncertainty. It does not promote the failed Ridge learner or establish a new router. The subsequent fresh experiment freezes a separate plain-confidence cutoff fitted on all 128 development states. Both prospective policies share that cutoff, −.07951707680497253. This refit has two changed training states, rather than the earlier cross-fitted control's three. The fresh study therefore tests the newly frozen policy contrast; it is not an exact replication of the earlier cross-fitted control.

### 5.3. Fresh sparse evaluation identifies only the policy difference

The fresh panel contains 228 disjoint questions. Let \(a_0\) denote the frozen plain-confidence action and \(a_1\) the parser-aware action. Define \(z=1[a_1\ne a_0]\). Changed states are drafts that plain confidence accepts and v7 rejects. They have \(Y_D=0\) by the fixed scoring rule without a direct-reference lookup. The guard only adds thinking, so its question-level utility difference is

\[
\Delta U=z(Y_T-Y_D-\lambda C_T/1000).
\]

When the actions agree, their difference is exactly zero. Therefore the fixed policy contrast can be evaluated by generating thinking only for changed states. The endpoint requires every direct response and every activated thinking response. This design does not identify either policy's absolute accuracy or utility.

Only one of 228 states changes action. Its extra thinking response uses 1,423 tokens, is rejected by numeric-v7, and is scored incorrect. There is no scored accuracy increment. The mean utility difference is −.000312061, with a 95% question-bootstrap interval of [−.000936184, 0]. The observed contributions are 227 zeros and one negative value. Resampling them cannot create an unobserved rescue. Thus the interval's upper endpoint of zero does not exclude positive population benefit from rare rescue events absent from this panel.

An elementary retrospective bound clarifies the role of the observed activation count. On changed states, \(Y_D=0\), \(Y_T\le1\), and thinking cost is nonnegative. Therefore

\[
\Delta U_i=z_i(Y_{T,i}-.05C_{T,i}/1000)\le z_i,
\qquad
\overline{\Delta U}\le\frac{1}{228}<.01
\quad\text{for the observed eligibility mask}.
\]

Even a rescue on the single activated call could not meet the .01 point-gain criterion on this panel, before charging thinking cost. This is a finite-panel bound with the mask held fixed. It does not estimate future activation rates, population gain, or statistical power. It leaves the completed endpoint and failed screen unchanged.

The frozen follow-up contrast supplies one activation without a scored rescue. One event cannot establish a general disadvantage for parser-aware routing. Most shared-action outcomes and 227 references were deliberately not observed. Reporting absolute policy accuracy for this panel would exceed what the design identifies.

### 5.4. A matched reasoning-cap intervention

The cap study selects 18 cells on 11 development questions using prior forced-closure metadata. It collects matched 2,048- and 4,096-token reasoning allowances, with the same question, solver, seed, and answer allowance. All 18 paired reasoning prefixes match. Every new 2k control also exactly replays its corresponding cached token streams.

Primary means weight the 11 questions equally after averaging selected draws within each question. They describe the enriched cohort. Table 5 reports thinking-call costs; it does not add a new direct draft. Common direct cost cancels from the cap difference.

**Table 5. Matched cap result on 11 selected question groups.** Intervals are paired 95% question-bootstrap summaries conditional on the selected cohort and recorded responses. Each question has equal weight after averaging its selected cells. Costs are for thinking calls; common direct cost cancels. The intervals do not cover cohort-selection uncertainty or general-task performance.

| Outcome | 2k reasoning | 4k reasoning | Difference and interval |
|---|---:|---:|---|
| Scored accuracy | 36.36% | 40.91% | +4.55 percentage points [0, +13.64] |
| Thinking-call tokens | 2,430.59 | 4,093.05 | +1,662.45 [1,225.67, 1,996.95] |
| Thinking-call utility | .242107 | .204439 | −.037668 [−.094767, +.061647] |

There is one rescue and no harms. The secondary cell-weighted count is 6/18 correct at 2k and 7/18 at 4k. It is not the primary question-weighted accuracy. The extra allowance gives lower point utility and does not support changing the default at the frozen cost preference. Its interval includes zero.

The cap result has two further limits. The cohort was selected by prior forced-closure metadata in the development panel, independently of correctness. It supplies no whole-panel or fresh-task accuracy estimate. In addition, eight accepted extended outputs are scored incorrect and three are parser-rejected. These categories distinguish extraction status; they do not provide a mathematical error taxonomy.

## 6. Discussion

### 6.1. Repeated structure and learned selection

The main observation joins three different results: scored rescues, limited post-hoc evidence of repeated question structure, and unsuccessful selection by the tested learners on held-out questions. A positive variance estimate and same-question transfer points concern the measured question distributions. A deployable learner must infer an action from permitted features on other questions. The present results leave that step unresolved.

This interpretation retains the failed primary reproducibility test. The post-hoc diagnostics measure different quantities and have their own assumptions. They cannot rescue the primary decision or prove that useful feature-level signal was available to the learner.

With 40 unique outer-training questions, the original 391-feature combined representation has many more coordinates than independent training groups. Repeated rows add response information while reusing those groups. This is a plausible constraint on learning, but the present studies do not identify it as the cause.

The capacity controls matter because they test a simple response to that concern. Stronger regularization, PCA compression, and confidence corrections also fail their bounded screens. The representation controls similarly show that this compact objective change and this released transfer recipe do not supply a demonstrated improvement. The combined evidence narrows these recipes. It does not exhaust larger datasets, other features, other fusion methods, or other model families.

### 6.2. Confidence is a required control, not a universal solution

Confidence is inexpensive and competitive on the repeat panel. It remains a necessary reference for the studied routers. The separate 1.7B diagnostic nevertheless gives lower confidence utility than direct acceptance. Thus the evidence does not justify recommending confidence routing in every setting.

The smaller solver has more observed opportunities, but this does not automatically yield a successful learned improvement over its confidence baseline. The three-feature pilot illustrates this distinction. A system-level choice must also consider the stronger direct solver, with full compute and latency accounting rather than only token counts.

### 6.3. Follow-up must retain its own estimand

The parser control and cap study answer different questions. The fresh guard test measures the incremental effect of one frozen policy modification. It deliberately leaves shared-action outcomes unmeasured. The cap intervention measures the effect of a larger allowance on previously selected cells. It has tighter token-stream matching but a narrow cohort.

Neither study can replace the repeat learner's failed endpoint. Their contribution is to prevent a favorable development count from becoming a broad improvement claim. The absence of a supported gain is informative for these decisions, even when sparse events prevent a strong population conclusion.

### 6.4. Scoring and cost are part of the result

Frozen scoring makes comparisons interpretable across stages. Gold-free presentation checks can identify compatibility issues, but cannot decide mathematical correctness. Replacing primary labels after inspecting outcomes would define a different study. We therefore retain original labels and separate syntax sensitivity from the policy results.

Output-token utility expresses the frozen preference at λ=.05. It charges generated and inserted tokens for the direct draft and extra thinking where required. It does not price input processing, encoder work, energy, or complete latency. Training acquisition, collection-ledger charges, and deployment cost are distinct. The measured CLM encoding overhead reinforces the need to report them separately. The tables retain accuracy and token counts so that the utility result is tied to its stated preference.

## 7. Limitations

The study uses one mathematical dataset and two small solver sizes from one family. All panels use eligible upstream training questions. Question-role checks protect project splits but cannot rule out pretraining exposure. We do not claim cross-task generalization.

The principal learner and representation results reuse 50 questions. Later study designs were informed by earlier results. Nested fitting protects the specified fit, but does not remove that research exposure. The bootstrap keeps fits and actions fixed, omits new training and optimization realizations, and does not reproduce overlapping-fold training dependence. It does not provide joint coverage across comparisons. The organizing paper-level hypotheses were not a single prospective registration.

Only one optimization seed is used in the compact neural study. Some drafts are truncated. The released CLM test is quantized and uses a particular state format, calibration, and small raw-feature control. Its pretraining overlap and full-precision equivalence are unknown. The comparison does not test adding CLM features to confidence.

The refitted parser follow-up has one changed event. Its empirical bootstrap cannot represent unseen rescue events, and its finite-panel ceiling does not bound population benefit. The cap study has 11 selected groups and one rescue. These observations cannot settle broad hypotheses about parser guards or reasoning budgets. Human scoring was waived, so scorer mistakes remain a limit even where extraction is accepted.

Finally, runtime recoveries and local resource contention prevent causal speed claims. No complete co-resident deployment benchmark, external-method superiority test, or sealed confirmation is reported.

## 8. Conclusion

On the studied GSM8K/Qwen3-1.7B panel, scored rescues and limited post-hoc evidence of repeated question-level structure coexist with failed learned selection on held-out questions. The primary learner and later bounded controls do not establish utility gains over their specified simple comparators. Same-question transfer omits acquisition cost, one directional interval crosses zero, and the primary reproducibility criterion remains failed. The flagged presentation cases alone cannot reverse the primary fixed-policy point comparison.

The separate two-solver diagnostic, fresh guard contrast, and selected cap intervention have different targets. They constrain transfer of the development observations without confirming a common failure mechanism. This evidence supports a scoped account of the tested recipes and their limits. A broader claim requires prospective evidence that separates repeated question structure from useful feature-based selection across new training and evaluation conditions.

## Data and code availability

The project retains versioned source, protocols, aggregate reports, score sidecars, and independent verification records. This manuscript is drafted from the tracked result records listed in Appendix B. No new experiment, scoring, reference access, or statistical reanalysis was performed for the manuscript. A public artifact release and its licensing review are pending. Sealed allocations and protected material are not part of a promised release.

## Author declarations

Author names, affiliations, contributions, funding, and conflicts of interest must be completed by the authors. AI assistance was used for drafting and research support. The authors must check the claims and references and assume responsibility for the submitted version. Automated engineering verification is not a human answer-scoring audit.

## Appendix A. Reproducibility and deviations

### A.1. Model and protocol identities

| Component | Fixed identity or contract |
|---|---|
| Qwen3-1.7B | Revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e |
| Qwen3-0.6B | Revision c1899de289a04d12100db370d81485cdf75e47ca |
| Question/draft encoder | all-MiniLM-L6-v2, revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 |
| Released CLM encoder | mlx-community/Qwen3-8B-4bit, revision 545dc4251c05440727734bcd94334791f6ab0192 |
| Released CLM heads | CLM-v0.1-8B, revision e939398d4556fcd9400c76fa8c5a513202f42b0a |
| CLM head implementation | Commit bb42c6c5bf914fd449bed2f6ca65be80602cb1f7; isolated MLX 0.32.3 / mlx-lm 0.32.0 |
| Main generation implementation | qwen3-boxed-budget-v3; local batch one; MPS, float16, SDPA |
| Direct sampling | Temperature .7; top-p .8; top-k 20 |
| Thinking sampling | Temperature .6; top-p .95; top-k 20 |
| Forced closure / EOS | Closure IDs [151668, 271]; EOS union [151643, 151645] |
| Main scoring | Numeric-v7; implementation digest c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964 |
| Normal allowance | 2,048 reasoning tokens and 512 answer tokens; forced closure charged |
| Cap intervention | 2,048 versus 4,096 reasoning tokens; unchanged answer allowance and matched seeds |
| Cost preference | λ=.05 per 1,000 charged output tokens, including inserted closure |
| Repeated-response grouping | Five question folds; A indices 0–3, B indices 4–7 |

The prompt suffix is: “In your final response, give only the numerical answer in \boxed{}.” The complete chat-template and state formatting remain defined by the frozen implementations. This suffix alone is not a reconstruction of those templates.

The CPU grid uses Ridge penalties {100, 1000, 10000} and thresholds {0, .02, .05}; conservative confidence-correction margins are {.02, .05, .10}. The compact heads select among margin thresholds {−.1, 0, .1}; their cosine temperature is .1 and optimization seed is 20261004. Learned CLM/raw controls use Ridge penalties {100, 1000, 10000} and thresholds {0, .02, .05}. The released zero-shot CLM margin threshold is zero. All stated choices follow the study-specific training boundaries.

Bootstrap seeds are 20261002 for repeat/CPU, 20261004 for compact neural controls, 20261006 for averaged CLM comparisons, 20261009 for the two-solver diagnostic, 20261012 for the 0.6B pilot, 20261018 for sparse validation, and 20261020 for the cap comparison. The linked protocols and evidence ledger retain the remaining operational and source identities.

The 25-question protocol bridge supplied 200 responses and matched token sequences across its two generation arms. This is an engineering check on those cells, not universal protocol equivalence. Its primary scoring uses numeric-v5. Bridge training references were materialized after roles froze, while workers did not read them and comparative scoring waited for all responses. The later routing studies use their separate complete-endpoint reference rules and numeric-v7 labels.

The parser compatibility preflight considered 56 fixtures and 1,900 cached outputs. It added one narrow extraction without accepted-answer regressions. It did not replace frozen v7 labels in the router studies.

### A.2. Operational accounting

**Table A1. Recorded study charges.** These collection ledgers include generated and inserted tokens, failed attempts, and conservative unresolved reservations where applicable. They are not sums of deployed-policy costs. Operation time differs from calendar wall time.

| Study | Charged tokens | Attempts or reservations | Preserved operational qualification |
|---|---:|---|---|
| Repeat panel | 644,519 | 806 attempts: 800 complete, six failures | Three setup sessions; original stop retained |
| Two-solver diagnostic | 384,552 | Four setups and invocations | Original wall-budget failure retained; separate completion child |
| Fresh sparse validation | 43,448 | 229 completed attempts | One setup; no unresolved reservation |
| Cap intervention | 127,171 | 38 reservations | Failed/unknown charges and original stops retained |

The cap completion used a larger permitted deadline, but every new call completed below the original 600-second limit. This does not establish why the earlier stalls ceased. Local cloud/API experiment expenditure was zero; local computation and energy were still required.

A CLM reporting deviation affected the bootstrap seed for 75 per-condition intervals. An additive sidecar provides the planned-seed versions. Point results, actions, selection, screens, and the averaged intervals used in Table 3 are unchanged. The original report and correction are both retained.

## Appendix B. Claim-to-source map

This table links each evidence block to the project records used to draft the paper. It is a provenance map, not a new analysis.

| Manuscript evidence | Authoritative project record |
|---|---|
| Repeat contract and original criteria | [Repeat protocol](../../docs/phase-2-repeat-panel.md) |
| Table 2 and repeat behavior | [Repeat results](../../docs/phase-2-repeat-results.md) |
| Box 1: post-hoc structure and fixed-policy scorer bounds | [Repeat diagnosis and syntax sensitivity](../../docs/phase-2-repeat-results.md) |
| Capacity and compact neural controls | [Feasibility results](../../docs/phase-2-router-feasibility-results.md) |
| Released CLM and matched encoder | [CLM results](../../docs/phase-2-clm-probe-results.md) |
| Table 4 and solver diagnostics | [Two-solver results](../../docs/opportunity-panel-results.md) |
| 0.6B candidate and parser control | [Pilot results](../../docs/qwen06-router-pilot-results.md) |
| Prospective cutoff and question roles | [Sparse preparation](../../docs/sparse-validation-preparation-results.md) |
| Fresh policy contrast | [Sparse results](../../docs/sparse-validation-results.md) |
| Table 5 and matched token streams | [Cap results](../../docs/qwen17-cap-bridge-results.md) |
| Extended evidence and extraction audit | [Evidence ledger](evidence-ledger.md) |
| Revision claim IDs, units, comparators, and limits | [Revision evidence map](revision-evidence-map.md) |

The later synthetic acquisition study is a separate feasibility result. It is not pooled with the real-solver evidence in this manuscript.

## References

The linked citations above identify the primary sources used in the text. Complete machine-readable metadata, including checked versions, are in [references.bib](references.bib). Related-work retrieval limits are recorded in [related-work-notes.md](related-work-notes.md).

1. Cobbe et al. (2021). *Training Verifiers to Solve Math Word Problems*. [arXiv:2110.14168v2](https://arxiv.org/abs/2110.14168v2).
2. Yang et al. (2025). *Qwen3 Technical Report*. [arXiv:2505.09388v1](https://arxiv.org/abs/2505.09388v1).
3. Chen et al. (2024). *RouterDC: Query-Based Router by Dual Contrastive Learning for Assembling Large Language Models*. [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7a641b8ec86162fc875fb9f6456a542f-Abstract-Conference.html).
4. Shirkavand et al. (2025). *Cost-Aware Contrastive Routing for LLMs*. [arXiv:2508.12491v3](https://arxiv.org/abs/2508.12491v3).
5. Wang et al. (2026). *SEMIROUTER: Sparse-Data Enhanced Routing for Adaptive Multi-LLM System*. [EACL](https://aclanthology.org/2026.eacl-long.228/).
6. Fang, Ma, and Wang (2025). *Thinkless: LLM Learns When to Think*. [arXiv:2505.13379v2](https://arxiv.org/abs/2505.13379v2).
7. Lee et al. (2026). *DART: Draft-Agreement Routing for Training-Free Adaptive Thinking Budgets in Hybrid Reasoning Models*. [arXiv:2606.23181v4](https://arxiv.org/abs/2606.23181v4).
8. Ding et al. (2025). *BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute*. [arXiv:2506.22716v1](https://arxiv.org/abs/2506.22716v1).
9. Sentence Transformers (undated). *all-MiniLM-L6-v2: Official Model Card*. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
10. Kwok et al. (2026). *Contrastive Language Models: A System One Model for Fast and Generalizable Decision-Making*. Author blog and released implementation; [official model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B).
11. Chen (2026). *What Does a Routing Oracle Measure Under Stochastic Decoding? Coupling, Scorer Choice, and Single-Commit Ceilings*. [arXiv:2607.03436v3](https://arxiv.org/abs/2607.03436v3).
12. Garg and Sagtani (2026). *Unsolvability Ceiling in Multi-LLM Routing: An Empirical Study of Evaluation Artifacts*. [arXiv:2605.07395v1](https://arxiv.org/abs/2605.07395v1).
13. Yang et al. (2026). *LLMs Can Predict Failure Risk, But Struggle to Predict Which Collaboration Protocol Pays Off: Cost-Aware Protocol Routing Across Reasoning Tasks*. [arXiv:2608.14927v1](https://arxiv.org/abs/2608.14927v1).
