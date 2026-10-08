# Empirical manuscript outline: thinking selection under sparse supervision

Prepared 2026-10-09 on `codex/confidence-acquisition-plan`, starting from
`a68a27a`. This is a writing artifact based on completed result records and a
targeted primary-paper comparison. It reports no new analysis or experiment.
The [publication plan](publication-plan-2026-10-08.md) and
[evidence map](research-evidence-map-2026-10-08.md) define its scope.

## 1. Working title, argument, and abstract

**Thinking Selection Beyond Confidence: Controlled Evidence from Two Small
Hybrid Solvers on GSM8K**

This title makes the task and solver scope visible. The earlier proposed title,
“When More Supervision Does Not Improve Thinking Selection,” can be retained
only with wording that does not imply a general causal result about supervision
quantity. The completed studies test specified draw counts and recipes; they do
not exhaust the benefits of additional data.

The central empirical argument is that, under the tested post-direct decision
contract, identifying useful thinking opportunities is harder than showing that
thinking improves average accuracy. The tested learners and transferred
representations did not pass their declared gates on the repeat panel. A
separate matched two-solver diagnostic found substantially different opportunity
patterns, and two bounded follow-ups failed to establish useful improvements.
These linked observations are a candidate narrow contribution. Their scientific
value beyond the closest prior studies remains a manuscript judgment, rather
than an established novelty claim.

### Working abstract

Hybrid language models can answer directly or spend additional tokens on a
fresh thinking solve. We study whether supervision and representation choices
improve this decision beyond direct-answer confidence under a fixed
accept-or-think contract. All policies pay for the initial draft, and utility
subtracts 0.05 per thousand generated tokens. On a 50-question GSM8K panel with
800 responses, independently sampled draw halves and held-out question folds,
the predeclared learner failed four of five progression gates. Its averaged
four-draw utility difference against a training-selected simple baseline was
−0.016204 (conditional 90% interval [−0.033276, −0.000635]). Bounded capacity,
objective, and quantized released-CLM controls also failed their exploratory
screens. A separate 64-question, 512-response diagnostic found positive
confidence-minus-direct utility for Qwen3-0.6B (+0.152677), but negative utility
for Qwen3-1.7B (−0.030540). A parser-aware development control motivated a
prospective sparse evaluation on 228 fresh questions; only one action changed,
and it yielded no scored accuracy gain. A matched reasoning-cap intervention
on 11 selected development questions produced one rescue but lower point
utility. We report these findings with frozen scorer identities, grouped
uncertainty, generation charges, and preserved runtime deviations. The evidence
supports scoped conclusions about the tested recipes and solver settings;
reused panels, conditional intervals, sparse follow-up, and a waived human
scoring audit limit broader claims.

Abstract numbers come directly from the result records linked in Section 4.
“Independent” describes the response draws and specified question separation;
it does not turn the reused-panel studies into independent confirmations.

## 2. Decision contract and research questions

The paper should define the decision before discussing router architectures.
After a completed direct draft, the policy observes the question, permitted
draft information, and its own available features. It chooses to accept that
draft or request a fresh thinking solve of the question. Thinking is not a
continuation of the draft. Correctness labels, future thinking text, and future
thinking costs are unavailable at the decision.

For scored correctness `Y_D`, `Y_T`, direct tokens `C_D`, thinking tokens `C_T`,
and escalation action `a ∈ {0,1}`, report:

```text
U(a) = Y_D + a × (Y_T − Y_D) − .05 × (C_D + a × C_T) / 1000
G    = Y_T − Y_D − .05 × C_T / 1000
```

Direct cost cancels from the incremental action gain `G` because it is already
spent; it remains in total policy cost. A correctness rescue and a positive
utility gain are distinct events. Standalone thinking costs also differ from
thinking after a paid direct draft. Generated-token utility is not complete
deployment cost: encoder work, setup, research acquisition, failures, and live
contention need separate accounting.

The following questions organize the manuscript retrospectively. Only the
individual studies' original hypotheses, grids, endpoints, and gates should be
called predeclared.

| Research question | Existing comparison | Answer currently supported |
|---|---|---|
| RQ1. When does thinking offer useful incremental opportunities at the fixed cost weight? | Direct/thinking outcomes in the repeat panel and matched two-size diagnostic. | Opportunity availability and practical confidence utility differ across the tested settings. A question does not have an intrinsic, deterministic “needs thinking” label. |
| RQ2. Does repeated supervision transfer across independent response draws and held-out questions? | Repeat-panel `k=1/2/4` directions, with full8 reported separately. | The combined learner fails its progression gates; the independent-half reproducibility interval crosses zero. Same-question transfer is a separate nondeployable diagnostic. |
| RQ3. Do capacity, objectives, or released representations improve selection beyond confidence? | Bounded Ridge controls, matched MiniLM heads/objectives, and quantized CLM versus a matched-backbone raw control. | The tested recipes fail their screens. These comparisons do not establish general failure of contrastive learning or identify quantization as the cause. |
| RQ4. Which favorable development observations survive a specified follow-up? | Parser-aware development control versus the separately frozen fresh sparse contrast; selected 2k/4k cap pairs. | The fresh guard contrast changes one action with no scored gain. The cap study observes one rescue, higher cost, and no confirmed utility benefit on its enriched cohort. |

No completed experiment answers whether active acquisition learns a threshold
more efficiently. That is the separate pending method question in the
[focused plan](novelty-plan-2026-10-08.md).

## 3. Concrete manuscript structure

### 1. Introduction

Open with the decision contract and why average thinking accuracy does not
identify when to escalate. State the GSM8K/Qwen3 scope immediately. Present
three proposed contributions: the controlled supervision/representation
comparison, the separation of development findings from follow-up evidence,
and the auditable measurement and accounting package. Acknowledge L15–L17
before presenting these as added value. Avoid a chronological checkpoint log.

### 2. Related work and what this study adds

Use the comparison in Section 6 to explain overlap with oracle audits,
evaluation-artifact studies, and failure-risk versus action-value routing.
Briefly cover RouterDC, CSCR, SEMIROUTER, and adaptive-thinking methods using
the [literature assessment](novelty-literature-2026-10-08.md). The paper does
not introduce contrastive routing, repeated solver supervision, or confidence
thresholds. A historical two-draft adaptation must not be called a full DART
reproduction. No external method is beaten by the evidence in this outline.

### 3. Experimental contract and evidence hierarchy

Define the equations above, model revisions, generation/scoring pins, roles,
observed-input boundaries, folds, cost units, and uncertainty. State that
GSM8K rows come from eligible upstream training roles and that the official
test and both confirmation studies remain unopened/unstarted as recorded.
Selected references were accessed only at each permitted scoring endpoint;
this manuscript uses completed reports and requires no reference reopening.

Use the following design matrix as the methods table's starting content.

| Evidence block | Unique question groups and observations | Separation and use | Essential qualification |
|---|---|---|---|
| Protocol bridge | 25 questions; 200 responses across two generation-protocol arms. | Matched generation bridge before the repeat study. | Engineering equivalence on these cells, not universal equivalence or router confirmation; primary bridge uses v5. |
| Repeat panel | 50 questions; eight draws per mode; 800 responses / 400 paired states. | Five outer question folds; disjoint A/B response halves; training-only tuning. | Repeat modes use distinct seeds; draw-index pairing is specified replay bookkeeping. Full8 has no independent same-question eight-draw replica. |
| CPU/MiniLM/CLM controls | Same 50 questions and 400 direct states. | Reuse the question folds and independent four-draw directions. | Later bounded development studies; fit counts are not extra datasets or independent evidence. |
| Two-size diagnostic | 64 new reserve-child questions; two draws per mode and solver; 512 responses. | Shared questions, distinct jobs/seeds; opposite-draw and other-question fitting. | Prospective diagnostic collection, subsequently reused for the 0.6B pilot; two sizes from one family do not supply two-family replication. |
| 0.6B learner and parser control | Same 64 questions / 128 paired outcomes; 20 fits. | Fixed training-draw/held-out-question pilot. | Development data; three extra parser-control rescues motivate rather than confirm follow-up. |
| Fresh sparse guard test | 228 disjoint fresh questions; 228 direct responses and one changed-action thinking response. | A separately frozen cutoff and guard rule precede fresh outcomes. | Identifies the incremental policy contrast, not either policy's absolute accuracy or utility. |
| Matched cap intervention | 11 selected questions from the existing 64-group development panel; 18 cells / 36 new responses. | Paired inherited seeds, new 2k and 4k controls, exact prefix gates. | Enriched by prior forced closure; primary means weight 11 questions equally, secondary means weight 18 cells. |

Keep original bridge v5 results and later unchanged-v7 router labels distinct.
Rejected/incomplete outputs count as incorrect under the applicable scorer.
Gold-free parser compatibility does not certify mathematical correctness.
Human answer scoring was explicitly waived; automated arithmetic, agent syntax
review, and preservation checks must be described by those names.

Report the 90% fixed-fit grouped intervals for the repeat/control studies and
the 95% intervals for sparse/cap follow-up with their original conventions.
Do not harmonize them after outcomes. Resampling question groups with actions
fixed omits refitting, research selection, and multiplicity. Question-held-out
fitting protects a specified fit; it does not erase earlier research exposure.

### 4. Repeat supervision and matched controls

Lead with all five original gates, including the sole passing informative-group
gate, before the later control results. Give both four-draw directions and their
average; reserve the full8 endpoint for a separately labeled table. Use rescue,
harm, and nonpositive escalation counts to explain policy behavior without
claiming a causal diagnosis.

Then present the capacity and MiniLM objective controls. State the matched
120-parameter head, one optimization seed, mean-vector fusion, and 111/400
tail-truncated drafts. Present the released CLM as a pinned 4-bit MLX
Qwen3-8B recipe with unfine-tuned heads. Its PCA8/Ridge control shares the
backbone, but head capacity, prior training, and feature dimensions differ;
the result does not isolate a contrastive pretraining effect.

The CLM audit may explain over-escalation descriptively. Its positive-gain
AUROC difference is imprecise. Keep the frozen `.05` cost preference and avoid
promoting the post-hoc break-even cost weight. Encoder timing belongs beside
the policy results so token utility is not mistaken for measured live savings.

### 5. Solver-size dependence and the 0.6B development pilot

Show direct, always-escalate, and confidence policies for both solvers on the
same 64 questions. Include positive-gain group availability and rescue/harm
counts by draw. The result supports dependence on these settings; no formal
population interaction or monotonic model-size law has been established.

Report the failed 0.6B Ridge candidate before the favorable parser-aware
control. Explain that three extra development rescues are sparse support.
The fresh study subsequently fits one plain-confidence cutoff on all 128
development rows and freezes both prospective policies around that cutoff.
It is a new fitted guard contrast, not literal transfer of every old
cross-validation threshold or a follow-up of the failed Ridge learner.

### 6. Follow-up with limited identified outcomes

For fresh validation, derive why unchanged actions contribute exactly zero to
the policy difference and why only changed states require thinking outcomes.
The guard changes one of 228 actions. Its thinking answer is v7-rejected and
scored incorrect; report zero scored accuracy increment and negative
incremental token utility. Do not report accuracy on 228 questions: most
references and shared-action counterfactuals were deliberately not observed.
One event cannot reject every parser-aware rule.

For the cap study, show the selected-cohort contrast, equal-question weighting,
one rescue, added tokens, and intervals containing zero. All 18 new reasoning
prefixes match; new 2k streams also replay the old streams. Those checks support
the matched intervention on these cells, not general cap effectiveness. Retain
the old watchdog failures and explicit completion-runtime deviation. Every
completion call finished below the old 600-second limit, so a longer allowed
deadline did not establish why the stalls ceased.

### 7. Discussion, limits, and reproducibility

Discuss the specific gap between outcome opportunity and learnable action
value. Label scarcity, rare rescues, representation mismatch, parser behavior,
and runtime contention remain possible explanations with different evidence;
do not state that any one is the demonstrated cause. Keep all original failed
gates and subsequent stop decisions visible.

State the principal limits together: one arithmetic task, two small sizes in
one family, repeated research reuse, sparse event counts, conditional intervals,
one neural optimization seed, truncated MiniLM drafts, quantized CLM and unknown
pretraining overlap, no full-precision equivalence, no live co-resident latency,
and the waived human scoring audit. Scorer acceptance is not a correctness
guarantee; scored rejection is not an independent proof of mathematical error.

End with the supported scoped finding and the prospective evidence needed for
broader claims. Acquisition, finetuning, RL, and sealed confirmation contribute
no completed result to this paper. Put source hashes, deviations, accounting,
parser fixture details, and all secondary conditions in appendices.

## 4. Claim-to-evidence table

The table fixes draftable claims, not new statistical hypotheses. Intervals
retain their original endpoints and condition on fixed recorded fits/actions.
Artifact paths are under `artifacts/research/data-efficiency-v1/`; exact digests
are recorded in the linked result documents.

| ID and permitted claim | Existing quantitative evidence | Source and frozen artifact | Boundary to carry into the manuscript |
|---|---|---|---|
| C1. The predeclared repeated-supervision learner did not satisfy its progression criteria. | Four of five gates fail; averaged four-draw difference −.016204, 90% CI [−.033276, −.000635]; only informative questions pass (14/50). | [Repeat results](phase-2-repeat-results.md); `repeat-panel-v1/report.json`, payload `e4d17cc5…6d56`. | Comparator is selected within training from accept/escalate/confidence. Reproducibility CI crosses zero; full8 difference −.051630 is secondary. |
| C2. The bounded capacity and MiniLM objective recipes did not improve the averaged four-draw confidence endpoint. | Selected CPU −.014287 [−.025680, −.004425]; selected neural −.033817 [−.052515, −.017266]; all eight neural family point differences negative. | [Feasibility results](phase-2-router-feasibility-results.md); `repeat-cpu-feasibility-v1/report.json`, `repeat-contrastive-pilot-v1/report.json`. | Same reused 50 groups; 1,035 Ridge and 600 head fits do not multiply evidence. Some individual family intervals include zero; these are recipe-specific failures. |
| C3. This quantized released-CLM transfer recipe did not pass its screens, including against a backbone-matched raw control. | Zero-shot −.026103 [−.058826,+.016513]; calibrated −.033262 [−.053818,−.015171]; raw control −.022617 [−.043758,−.004464], all versus confidence. Calibrated-minus-raw −.010645. | [CLM probe results](phase-2-clm-probe-results.md); `repeat-clm-probe-v1/report.json`, payload `5c05f655…7f117`. | Four-draw confidence is 92.75% / 628.47 tokens; full8 is 92.5% / 466.88. Keep endpoints distinct. No full-precision or universal CLM conclusion. |
| C4. Near-always-thinking CLM behavior and weak ranking are descriptive features of the recipe. | Thinking 380/400 times; positive-gain precision 7.89%. AUROC .500450 versus .705045 for negative confidence; paired difference −.204595, 90% CI [−.606961,+.195547]. Mean state encoding 1.427 s, p95 2.244 s. | [CLM assessment](clm-research-assessment-2026-10-03.md); `clm-signal-audit-v1/completion-v1/report.json`, `repeat-clm-probe-v1/report.json`. | Wide interval prevents population ranking-inferiority claim. Encoder timing is measured separately; token utility excludes it. Use the additive protocol-seed sidecar for CLM conditional intervals. |
| C5. Thinking availability and confidence utility differ between the tested solver sizes on the shared panel. | 0.6B: 24 positive-gain groups; confidence-minus-direct +.152677 [+.085535,+.220375]. 1.7B: four groups; −.030540 [−.056066,−.006071]. | [Two-solver results](opportunity-panel-results.md); `opportunity-panel-v1/completion-v1/report.json`, payload `f3f0d33c…ac6fd`. | 64 groups / two draws, one model family. Conditional fixed-action intervals omit cutoff refits; this is a diagnostic, not learned-router superiority confirmation. |
| C6. The 0.6B learned pilot failed; a favorable cheap development control supplied only sparse motivation for follow-up. | Ridge-minus-confidence +.003516 [−.031959,+.037163], two of four checks fail. Parser-control gain +.022493 [+.007453,+.044905] from three extra rescues on three groups. | [0.6B pilot](qwen06-router-pilot-results.md); `qwen06-router-pilot-v1/report.json`, payload `ccdd2a2a…20ccf`. | Preserve the failed primary candidate. Parser-aware confidence is a development baseline, not a newly promoted method. Draws have different direct states, so disagreement does not prove same-state noise. |
| C7. The specified fresh guard contrast did not yield scored improvement at its sparse endpoint. | One changed state / 228; accuracy increment 0; utility −.000312061, 95% CI [−.000936184,0]; extra call 1,423 tokens. | [Sparse results](sparse-validation-results.md) and [preparation](sparse-validation-preparation-results.md); `qwen06-sparse-validation-v1/runtime-v1/report.json`, payload `ee07790d…a98ed`. | Only one eligible reference opened. No absolute full-policy metric is identified. One event neither confirms development rescues nor establishes general guard failure. |
| C8. The selected 1.7B cap extension did not establish positive utility at `.05`. | Equal-question accuracy 36.36%→40.91%; one rescue, no harms; tokens +1,662.45; utility −.037668, 95% CI [−.094767,+.061647]. | [Cap results](qwen17-cap-bridge-results.md); `qwen17-cap-bridge-v1/completion-v1/report.json`, payload `11e61657…e1622`. | Enriched 11-group development cohort / 18 pairs. Interval includes zero; raw 6/18→7/18 is secondary. No whole-panel or fresh accuracy claim. |
| C9. The numerical findings have preserved protocol, accounting, and endpoint evidence. | Complete endpoints and independent cached arithmetic/preservation reviews; old failures and unknown reservations remain charged. | Original result records and their linked independent verification payloads; [bridge](phase-1-bridge.md), [parser preflight](parser-preflight.md), [compatibility](phase-2-parser-compatibility.md). | This is reproducibility evidence, not a human mathematical audit, universal scorer validation, or causal claim about recovery/runtime. |

## 5. Proposed scientific figures and tables

These are specifications for a later versioned cached-report export. No figure
or table calculation was performed for this outline. Preserve every original
report; any additional transformation or analysis needs an additive plan.

| Display | Exact proposed content and source | Caption requirement |
|---|---|---|
| Figure 1. Utility under the repeated-draw contract | Three clearly separated panels: original learner's seven frozen conditions versus its inner-selected simple baseline; averaged four-draw CPU and eight MiniLM objective families versus confidence; averaged four-draw CLM policies versus confidence and calibrated-minus-raw contrast. Use original intervals and mark declared failed gates. Sources: repeat, feasibility, CLM reports and existing plotting recipes. | All panels reuse 50 question groups. Separate comparators and full8; no pooled effect or ranking across unmatched estimands. State fixed-fit 90% intervals. |
| Figure 2. Opportunity and cost in the shared two-size diagnostic | Left: positive-gain groups, 24/64 and 4/64; rescue/harm counts shown by draw (0.6B rescues 15/17, harms 4/4; 1.7B rescues 4/3, harms 2/1). Right: direct, always-escalate, and confidence accuracy/token points for each size. Source: two-solver report. | Group availability differs from response-level rescue counts. Costs include the direct draft. Avoid claiming a tested size interaction or connecting points into a transferable frontier. |
| Figure 3. Development and follow-up evidence | Diagram showing the 50-group reused control block, the separately collected 64-group block, the 0.6B development guard observation, its 228-group sparse prospective contrast, and the 11-group cap subset within the 64-group block. Annotate failed gates and identified outcomes. | Arrows denote design influence, not statistical independence or successful replication. Explicitly show that the 11 groups overlap the 64 and that only one fresh action changed. |
| Table 1. Contracts and evidence units | Expand the Section 3 design matrix with exact model/scorer/protocol revisions, answer/reasoning caps, available features, fold/half rules, and interval conventions from frozen protocols. | Separate question count, response count, paired-state count, and fit count. |
| Table 2. Main repeat/control outcomes | Original gate table plus selected four-draw capacity/neural/CLM rows with accuracy, total generated tokens, utility difference, interval, and screen status. Full8 moves to an appendix table. | Original predeclared primary versus later exploratory studies; no best-recipe replacement. |
| Table 3. Two-size policy results and 0.6B pilot | Reproduce direct/always-escalate/confidence rows for both sizes and the fixed six-policy 0.6B pilot block, visually separated. | Diagnostic collection versus subsequent reuse; cite three-event support for the parser guard. |
| Table 4. Follow-up contrasts | Two separate blocks: sparse guard incremental outcomes and enriched cap paired outcomes, including group/cell counts, extra tokens, exact uncertainty level, and identifiability. | Do not fill sparse absolute-accuracy cells; label them “not identified.” Keep cap question means distinct from raw cell counts. |
| Table 5. Costs and deviations | Repeat collection: 644,519 charged tokens / 806 attempts / three setups. Two-solver: 384,552 tokens / four setups and invocations, retaining the expired parent budget. Sparse: 43,448 tokens / 229 completed attempts / one setup. Cap: 127,171 tokens / 38 reservations / three setups and invocations, retaining both stops and unknown charges. Include separate CLM encoder timing and head/fit work. | Distinguish operational charges, realized policy tokens, acquisition expenditure, cumulative operation time, and calendar wall time. Do not sum reused studies into a new net efficiency metric. |

Existing figure sources include `scripts/plot_repeat_results.py`,
`scripts/review_router_feasibility.py`, and
`scripts/review_repeat_clm_probe.py`. Completed executors must not be rerun to
produce manuscript tables. The planned export should use immutable aggregate
reports and cached-only verification contracts.

Appendices should carry all original gate definitions, full8 and per-direction
results, full objective rows, parser fixtures and bounded syntax sensitivity,
CLM interval-seed deviation/sidecar, ledger deviations, and source/artifact
manifests. Do not include sealed roles, credentials, private machine details,
or unapproved raw text in a candidate public package.

## 6. Closest primary-paper overlap: L15–L17

Primary HTML full texts and arXiv version records were checked on 2026-10-09.
This is a targeted comparison, not a systematic search or reproduction. The
assessment below concerns stated designs; external numerical findings were
not reproduced or imported into our evidence.

| Work and primary location | Established overlap | Concrete difference available in this manuscript | Remaining constraint |
|---|---|---|---|
| L15: Chen, *What Does a Routing Oracle Measure Under Stochastic Decoding? Coupling, Scorer Choice, and Single-Commit Ceilings*, v3, 2026-09-27. [Full text](https://arxiv.org/html/2607.03436v3), Sections III–VI and Appendix C. | Separates single-commit ceilings from hindsight unions, states coupling assumptions, and audits scorer/pool/finite-draw sensitivity. Its fixed archive has 11 models and 30 draws per cell across three tasks; a retrospective policy illustration does not establish fresh generalization. | Our operational action is accept an observed direct draft or pay for a fresh same-solver thinking solve. The main learned-policy tests combine question-held-out fitting with independent stochastic draw halves; later follow-up has explicit prospective/sparse boundaries. | Oracle cautions and hash-bound evidence are already covered. The cached hindsight and same-question transfer results cannot be promoted as deployable ceilings or net acquisition gains. We offer no new oracle theorem. |
| L16: Garg and Sagtani, *Unsolvability Ceiling in Multi-LLM Routing: An Empirical Study of Evaluation Artifacts*, v1, 2026-05-08. [Full text](https://arxiv.org/html/2605.07395), Sections 3, 5, and 8. | Studies judge disagreement, truncation, format mismatch, and router collapse, with exact-match and random-feature/shuffled-label controls. It uses greedy multi-tier generation across six benchmarks. | Our primary labels stay frozen while gold-free syntax compatibility is assessed separately. We report an actual matched cap intervention and a fresh guard contrast with limited identification, embedded in a repeated-supervision study. | Parser/cap failure and majority-policy collapse alone add no new finding. We have neither replicated its artifact decomposition nor performed a human scoring audit. Our bounded syntax checks do not measure all scorer errors. |
| L17: Yang et al., *LLMs Can Predict Failure Risk, But Struggle to Predict Which Collaboration Protocol Pays Off*, v1, 2026-08-14. [Full text](https://arxiv.org/html/2608.14927), Sections 2–5 and Appendices B.3/C.2–C.3. | Holds a solver fixed while comparing four collaboration protocols, confidence, and trained/frozen routers; directly distinguishes failure risk from protocol value. Each problem–protocol pair supplies one deterministic realized outcome, with broader paired task/solver checks. | Our draft-conditioned two-action setting uses sampled token log-confidence, independent stochastic response halves, matched small-head/objective controls, and a quantized backbone-matched transfer diagnostic. The sparse fresh guard test identifies a fixed incremental contrast with one changed action. | Neither fixed-solver routing nor confidence efficiency is our novelty. We have less task/family breadth. Repeated-draw evaluation is a concrete design difference, but its added scientific insight must be shown rather than asserted. |

The most defensible added claim is the conjunction of a specific post-draft
contract, independent-draw learner evaluation, matched representation controls,
and explicitly limited prospective follow-up. That conjunction is a candidate
empirical contribution; merely combining familiar audits is insufficient.
The discussion should say what the observations teach beyond each prior paper,
and acknowledge when they corroborate established cautions.

The current L15 title replaces “How Much of the Routing Gap Is Real?”; count it
once. A full DART comparison is missing and becomes necessary for a claim about
outperforming that system. It is not necessary to write the present narrower
comparison of tested controls.

## 7. Missing evidence and draft decisions

| Gap | Needed for the scoped draft | Needed for a broader claim |
|---|---|---|
| Precise value beyond L15–L17 | Human authors should review the comparison above and commit to the narrow independent-draw/control/follow-up argument. Avoid priority language. | Evidence showing that the insight carries beyond these recipes/settings, with explicit contrasts to the closest papers. |
| Cached error/presentation audit | Complete the separately planned cached audit before presenting a fuller error taxonomy. The outline can report only existing scored counts and gold-free syntax findings; cached associations do not establish causes. | A causal explanation needs a justified intervention or identification argument. New scoring validation requires its own policy/protocol and must not silently replace primary labels. The historical human-audit waiver remains in force. |
| Task/model breadth | Name GSM8K and the Qwen3 sizes in title, abstract, and conclusion. | A task-relevant second setting chosen before outcomes, frozen replication, and adequate group-level precision. Two sizes within Qwen3 are not independent families. |
| Uncertainty for learning | State every interval's conditioning and retain failed gates. | A separately specified analysis of repeated fitting/training/selection uncertainty and relevant optimization/acquisition seeds; none is supplied by the current fixed-action bootstrap. |
| External method comparison | State that results compare the tested internal controls and matched recipe variants. | A faithful, pinned contemporary comparator, especially full DART, for claims depending on defeating it. |
| Deployment recommendation | Report encoder observations and generated-token policy utility separately. | Full live router/solver cost, setup/prefill/selection, latency under co-residence, and complete memory accounting. No current CLM deployment recommendation follows. |
| Reproducible paper package | Prepare an additive private report export and claim-to-artifact manifest using completed caches. Reconcile table units and source identities without closed-executor reruns. | License/access review and an approved public release; raw datasets, model material, and sealed roles require their applicable boundaries. |
| Supervision-acquisition claim | Keep the pending acquisition algorithm out of empirical-result claims. | Equal-acquired-token learning curves, new-versus-repeat controls, multiple seeds, and independent evaluation under a separate prospective protocol. |

The existing evidence is sufficient to write an internally reviewed, narrowly
scoped manuscript now. It is insufficient for universal router failure, an
acquisition-method benefit, external-method superiority, or a deployment
recommendation. A broader replication should be chosen for its scientific
question and feasibility before seeing outcomes; this outline allocates no
questions and starts no job.

## 8. Immediate writing deliverables

1. Draft Methods from the decision equations and evidence-unit matrix, using
   each original protocol for exact revisions, decoder settings, and references.
2. Draft Results in the order above: failed repeat gates, matched controls,
   solver-size diagnostic, sparse and cap follow-up. Retain every failed primary
   or promotion decision rather than selecting a favorable recipe.
3. Prepare the private table/figure export specification and manuscript
   claim-to-artifact manifest. Freeze any new cached transformation or audit
   before execution; no scoring/reference reopening is needed.
4. Draft related work using the primary-paper overlap table, then assess whether
   the narrow empirical contribution is sufficiently useful for submission.
5. Write limitations and deviations alongside Results, and identify the smallest
   separately authorized evidence block if the authors choose a broader claim.

No tests were run for this writing task. No existing study file, protocol,
score, reference, model asset, or executor was changed or reopened.
