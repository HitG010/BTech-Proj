# Claim-to-source map for manuscript v0.2

Date: 10 October 2026. Revision pass: **R1**.
Source checkpoint: `fda3dfa`; manuscript baseline: v0.1 at `1695a1f`.

## 1. How to use this map

This map controls the claims used in R2–R4 of the
[revision plan](revision-plan-2026-10-10.md). It does not change a study result.
Use the claim ID when writing the revision response. Each row specifies the
evidence role, comparison, source, units, and required limit. Numerical registers
below supply the exact report values for the corresponding claims.

Evidence roles:

- **Primary:** the original predeclared repeat study and its progression tests.
- **Descriptive:** counts or policy behavior on a completed panel.
- **Post-hoc:** a separately reported diagnostic designed after primary results.
- **Exploratory:** a later bounded study on reused questions.
- **Fresh diagnostic:** questions separate from development, under a frozen rule.
- **Selected intervention:** new responses on selected old question groups.
- **Deduction:** arithmetic or interpretation from a stated contract and count.
- **Synthesis:** a scoped reading of multiple results; not another estimate.

Unless a row says otherwise, utility is scorer-defined correctness minus
`.05 × charged output tokens / 1000`. Output cost includes inserted closure.
Escalation pays for both the direct draft and the new thinking call. Scored
accuracy is a percentage; utility differences are fractions, not percentage
points. Variance and mean squared error use utility squared.

Repeat and later router intervals are recorded conditional 90% whole-question
bootstrap intervals. Sparse and cap intervals are 95%. Fitted policies/actions
are held fixed; these intervals do not cover refitting, research selection, or
simultaneous comparisons. A direction or repeated state is not a new question.

No new effect, interval, subgroup, fit, or scoring result is computed here.

## 2. Central claim and evidence roles

**C00 — Candidate synthesis for the abstract, Introduction, and Conclusion**

> On this 50-question GSM8K/Qwen3-1.7B panel, observed rescues and limited
> post-hoc evidence of repeated question-level structure coexist with failure
> of the specified learners to improve held-out-question utility over their
> stated simple comparators. Bounded controls do not resolve that failure.
> Separate follow-ups limit transfer of these observations to other solver
> settings and policy definitions.

Dependencies: C01–C10 for the main finding; C12–C18 for the supporting scope
checks. This synthesis is permitted only with those qualifiers. It does not
show that the learner could use the measured structure, identify why it failed,
or prove that repeated supervision has no value. Novelty remains a reviewer
judgment. The source papers do not establish priority for this synthesis.

### Main repeat evidence

| ID and supported wording | Role and comparison | Recorded support and units | Source and proposed placement | Required limit |
|---|---|---|---|---|
| **C01. The predeclared learner fails four of five progression criteria.** | Primary; combined Ridge minus a simple baseline selected inside training from accept/escalate/confidence | Mean Δutility −.016204; 90% interval [−.033276, −.000635]. Gate details in N1. | [Repeat protocol, terminal result](../../docs/phase-2-repeat-panel.md), [repeat results](../../docs/phase-2-repeat-results.md); abstract, main Results | Fifty question groups; fixed-fit uncertainty. Do not silently replace the comparator with confidence or the learner with a later policy. |
| **C02. Thinking has observed rescues and higher average scored accuracy on this panel.** | Descriptive; paired direct versus standalone thinking outcomes | 358/400 direct correct (89.5%); 378/400 thinking correct (94.5%); 30 rescues, 10 harms, 348 both correct, 12 both wrong. | [Repeat results](../../docs/phase-2-repeat-results.md), paragraph before full8 table; opening Results | Four hundred states reuse 50 questions. These are realized outcomes, not expected gains or a deployable oracle. Standalone thinking omits the already-paid direct cost. |
| **C03. Primary gain reproducibility is inconclusive under its declared criterion.** | Primary; each question's source-half mean gain predicts its opposite half, compared with the other questions' source-half mean | Symmetrized MSE improvement +.01158 utility²; 90% interval [−.01744, +.04848]. | [Repeat protocol](../../docs/phase-2-repeat-panel.md), [results gate table](../../docs/phase-2-repeat-results.md); main gate table | The criterion fails. An interval crossing zero is not evidence of no repeated structure. This statistic is not C04's variance estimate. |
| **C04. A separate post-hoc estimate suggests between-question gain variation.** | Post-hoc; signed variance decomposition, not a learner comparison | .03233 utility²; conditional 90% interval [.00541, .06530]. Reported components: question-mean variance .04066 minus within-question variance .06668/8. | [Repeat diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation); new diagnostic box | Approximate IID/exchangeable within-question draws; conditional on cached labels; estimate deliberately unclipped. Does not reverse C03, establish stable gains for each question, or show learnability. Do not recompute from rounded components. |
| **C05. Same-question label transfer has different directional point estimates and differs from unseen-question learning.** | Post-hoc; choose an action using four draws of each known question, evaluate the other half; gain over accepting direct | A→B +.04413 [.00563, .08845]; B→A +.01572 [−.02019, .05908], utility with 90% intervals. | [Repeat diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation); same diagnostic box | One interval crosses zero; no formal directional-difference test is reported. Prior labels concern the evaluation questions themselves. Acquisition expenditure is omitted: 322,882 tokens for A and 321,508 for B. These are not net acquisition gains or unseen-question performance. |
| **C06. The flagged presentation cases cannot reverse the primary fixed-policy point contrast.** | Post-hoc bounded sensitivity; change correctness of flagged rejected outputs, keep actions/costs fixed | Five cases leave averaged four-draw Δutility exactly −.016204. Full8 ranges [−.054130, −.049130]. Including the sixth unmarked case cannot improve the four-draw difference. | [Parser triage and bounds](../../docs/phase-2-repeat-results.md#gold-free-parser-triage-and-bounded-sensitivity); robustness paragraph | These ranges are point bounds, not confidence intervals. No unflagged error, refitted policy, or general scorer-validity conclusion. Human mathematical scoring remains waived. |

For C03, the protocol uses “prediction half.” The earlier
[ledger's final editorial review](evidence-ledger.md#final-editorial-review)
records the implementation check establishing that this is the source half.
No source code was executed or reinspected for R1.

### Reused-panel controls

All C07–C11 use the same 50 questions. Utility comparisons in C07–C10 average
A4→B4 and B4→A4. Their reference is the **four-draw confidence policy**, with
92.75% accuracy, 628.47 tokens/state, and utility .896076. N2 gives all selected
policy rows. The original C01 comparator has a different selection definition.

| ID and supported wording | Role and comparison | Recorded support and units | Source and proposed placement | Required limit |
|---|---|---|---|---|
| **C07. The selected bounded CPU family does not improve utility over confidence.** | Exploratory; training-selected new CPU family minus confidence | Δ −.014287 [−.025680, −.004425]; 1,035 Ridge and 75 PCA fits; all three screens fail. | [Feasibility results](../../docs/phase-2-router-feasibility-results.md#main-four-draw-comparison); main control table | Fits do not add independent question groups. Does not exhaust all low-capacity learners. |
| **C08. The compact neural recipes fail their recorded screens.** | Exploratory; two representations × four objectives, each compared with confidence | Selected Δ −.033817 [−.052515, −.017266]; all eight family average point differences negative; some family intervals include zero. 600 head and 150 PCA fits. | [Feasibility results](../../docs/phase-2-router-feasibility-results.md#representation-and-objective-controls); main control table | One optimization seed, one mean-vector fusion, compressed inputs; 111/400 draft encodings truncated at 256 tokens. Does not establish failure of neural or contrastive learning as classes. |
| **C09. The released quantized CLM recipe does not pass its screens.** | Exploratory; zero-shot, calibrated, raw control, and selected family versus confidence | Four averaged rows in N2; zero-shot Δ −.026103 [−.058826, +.016513]; all screens fail. | [CLM results](../../docs/phase-2-clm-probe-results.md#scope-and-main-independent-half-comparison); main control table | Zero-shot interval crosses zero. Four-bit transfer, unknown full-precision equivalence/pretraining overlap. No population disadvantage established for zero-shot. |
| **C10. Scalar CLM calibration is below its matched raw-encoder control on this endpoint.** | Exploratory; calibrated CLM minus PCA8/Ridge on the same 8B encoder | Δ −.010645 [−.018190, −.004292], utility; 90% averaged interval. | [CLM results](../../docs/phase-2-clm-probe-results.md#scope-and-main-independent-half-comparison); control interpretation | Shared backbone does not match head capacity or prior training. Both learned families exclude auxiliary draft statistics. This does not isolate a contrastive-pretraining effect or test adding CLM features to confidence. |
| **C11. Near-always-thinking CLM incurs additional encoder work.** | Descriptive behavior and separate runtime measurement; no causal speed comparator | Thinks on 380/400 drafts; mean state encoding 1.427 s, p95 2.244 s. Maximum input 659 tokens; zero truncation at 2,047-token cap. | [CLM behavior and resources](../../docs/phase-2-clm-probe-results.md); cost paragraph/appendix | Generated-token utility excludes encoder work. Timing is not live co-resident router/solver latency. Keep MLX allocation and RSS separate if used. |

### Separate diagnostic and follow-up

| ID and supported wording | Role and comparison | Recorded support and units | Source and proposed placement | Required limit |
|---|---|---|---|---|
| **C12. Observed opportunity and confidence utility differ across the two solver settings.** | Separately collected diagnostic; same 64 questions, two draws/mode/solver; confidence minus direct within each solver | 0.6B: 24 positive-gain questions, Δ +.152677 [+.085535, +.220375]. 1.7B: four, Δ −.030540 [−.056066, −.006071]. Policy metrics in N3. | [Two-solver results](../../docs/opportunity-panel-results.md#fixed-policy-results); supporting result | Positive count means at least one positive realized draw, not positive expected gain. No population size interaction, model-family generalization, or direct comparison with eight-draw opportunity counts. |
| **C13. The fixed 0.6B learned pilot fails two of four checks.** | Exploratory reuse; three-feature Ridge minus frozen confidence decisions on 64 questions | Δ +.003516 [−.031959, +.037163]. Directions +.002458 / +.004573. Below required .01 and below parser control. | [Pilot results](../../docs/qwen06-router-pilot-results.md#recorded-policies); brief supporting result | Positive point estimate is not a passed screen. Do not promote the parser control as a replacement primary learner. |
| **C14. The cross-fitted parser control's development gain rests on three rescued groups.** | Exploratory; confidence OR rejection minus original confidence decisions | Three extra escalations (87 versus 84); Δ +.022493 [+.007453, +.044905]. Accuracy 81.250%→83.594%; tokens 1,062.52→1,081.41. | [Pilot control](../../docs/qwen06-router-pilot-results.md#what-the-simple-control-shows); guard motivation | Reused development; three supporting groups. This is not the later all-data threshold or fresh confirmation. |
| **C15. The prospective guard uses a newly fitted and frozen common threshold.** | Training/protocol fact; full-128-state plain versus guard policy | Cutoff −.07951707680497253; 64 training groups/128 states; 85 versus 87 escalations, hence two changed training states. | [Sparse preparation](../../docs/sparse-validation-preparation-results.md#frozen-cutoff); transition to fresh test | The earlier cross-fitted comparison had three changes. A prospective diagnostic of this refit is not an exact replication of those three rescues. |
| **C16. The fresh frozen contrast has one activation and no scored rescue.** | Fresh diagnostic; parser guard minus plain confidence, fixed common cutoff | 228 direct + one thinking response; Δutility −.000312061, 95% interval [−.000936184, 0]; scored accuracy increment 0; extra call 1,423 tokens. | [Sparse results](../../docs/sparse-validation-results.md); fresh result | Only incremental policy difference is identified. Absolute accuracy/utility and always-thinking outcomes are not identified. Scorer rejection is not a new mathematical audit. |
| **C17. The observed mask cannot meet the .01 point-gain screen, even with a rescue.** | Retrospective deduction from the frozen sparse contract and observed mask | ΔU_i ≤ z_i; panel mean ≤1/228 before thinking costs. Proof in Section 6. | [Sparse protocol](../../docs/qwen06-sparse-validation-protocol.md), [critical review](critical-review-2026-10-10.md); beside C16 | Finite-panel bound with observed mask fixed, not a population event-rate bound or prospective power claim. Do not change the original criterion. |
| **C18. The selected cap extension gives one rescue but does not establish positive utility.** | Selected intervention; 4k minus 2k on 18 matched pairs/11 old questions, question-weighted | Accuracy +4.55 percentage points; tokens +1,662.45; utility −.037668 [−.094767, +.061647]. Full values and intervals in N4. | [Cap results](../../docs/qwen17-cap-bridge-results.md#result-at-the-frozen-cost-weight); short main summary/full appendix | Selected by prior forced-closure metadata, not correctness. Thinking-call costs; direct cost cancels. Interval crosses zero. No whole-panel, fresh-task, or general cap conclusion. |

## 3. Numerical registers

Each register inherits the question grouping, cost contract, role, and limitations
of its claim IDs. These are transcriptions, not recalculations.

### N1. Original tests and secondary full8 endpoint

Sources: [repeat results](../../docs/phase-2-repeat-results.md) and the
[protocol's terminal result](../../docs/phase-2-repeat-panel.md) for six-decimal
primary precision. All intervals below are conditional 90%.

| Primary criterion | Value | Decision |
|---|---|---|
| Positive reproducibility improvement and positive lower bound | +.01158 utility² [−.01744, +.04848] | Fail |
| Positive four-draw gain in both directions | −.02679 / −.00562 utility | Fail |
| Mean gain ≥.01 and positive lower bound | −.016204 [−.033276, −.000635] | Fail |
| No reversal at secondary full8 | −.05163 [−.07286, −.03204] | Fail |
| At least ten informative questions | 14/50 have a correctness difference | Pass |

Informative means rescue **or** harm here. It is different from C12's positive
utility-gain count. The k1 directional differences are −.02016 / +.00641; k2
are −.02812 / +.02257. Their full intervals remain in the source's seven-condition
table and [ledger Section 3](evidence-ledger.md#3-repeat-learner-frozen-fitting-and-all-five-gates).
Do not invent higher precision or interpret these points as a monotone curve.

Secondary full8 policy values, from the same result document:

| Policy | Accuracy (%) | Charged output tokens/state | Utility |
|---|---:|---:|---:|
| Accept direct | 89.50 | 221.14 | .88394 |
| Escalate after direct | 94.50 | 1,610.98 | .86445 |
| Confidence | 92.50 | 466.88 | .90166 |
| Combined Ridge | 89.00 | 799.49 | .85003 |

Full8 has no independent same-question eight-draw replica. Its selected simple
baseline happened to be confidence in all five folds. Post-hoc combined
escalations: 174, with five positive and 169 nonpositive gains, including seven
harms; 25 positives missed. Confidence: 58, with 16 positive and 42 nonpositive,
including four harms; 14 positives missed. These overlapping categories must
not be added as disjoint counts. See the source's post-hoc explanation.

### N2. Later averaged four-draw controls

All differences are against four-draw confidence, except C10's separate contrast.
Sources: [CPU/neural table](../../docs/phase-2-router-feasibility-results.md#main-four-draw-comparison)
and [CLM table](../../docs/phase-2-clm-probe-results.md#scope-and-main-independent-half-comparison).

| Policy | Accuracy (%) | Tokens/state | Utility | Δutility | Conditional 90% interval |
|---|---:|---:|---:|---:|---|
| Confidence | 92.75 | 628.47 | .896076 | Reference | — |
| Selected CPU family | 90.75 | 514.22 | .881789 | −.014287 | [−.025680, −.004425] |
| Selected compact neural family | 89.25 | 604.82 | .862259 | −.033817 | [−.052515, −.017266] |
| CLM zero-shot | 94.75 | 1,550.53 | .869973 | −.026103 | [−.058826, +.016513] |
| CLM calibrated | 88.50 | 443.71 | .862815 | −.033262 | [−.053818, −.015171] |
| Raw encoder PCA8/Ridge | 89.00 | 330.81 | .873460 | −.022617 | [−.043758, −.004464] |
| Selected CLM/raw family | 88.75 | 406.34 | .867183 | −.028893 | [−.049575, −.010922] |

The exploratory screen requires average gain ≥.01, positive directional means,
and positive averaged gains after deleting each question. All selected screens
fail. Full family/directional rows are retained in the linked result documents
and ledger Section 4. Do not select a favorable direction as a new endpoint.

The CLM report's 75 per-condition intervals had a bootstrap-seed deviation.
The recorded additive sidecar supplies planned-seed versions. N2 and C10 use
the **averaged** intervals, which were unaffected. R1 does not open the sidecar
or approve new per-condition interval transcription from raw artifacts.

### N3. Two-solver and reused 0.6B pilot metrics

Role: diagnostic for the first table; exploratory for the second. Source:
[two-solver fixed policies](../../docs/opportunity-panel-results.md#fixed-policy-results).
Each solver has 128 paired states grouped in 64 questions.

| Solver / policy | Accuracy (%) | Tokens/state | Utility |
|---|---:|---:|---:|
| 1.7B direct | 84.375 | 228.01 | .832350 |
| 1.7B escalate | 87.500 | 1,586.79 | .795661 |
| 1.7B confidence | 83.594 | 682.56 | .801809 |
| 0.6B direct | 61.719 | 209.80 | .606697 |
| 0.6B escalate | 80.469 | 1,409.52 | .734211 |
| 0.6B confidence | 81.250 | 1,062.52 | .759374 |

The availability screen requires ≥10 positive-gain questions. The confidence
screen requires gain ≥.01 and positive means in both directions. 0.6B passes
both; 1.7B fails both. Intervals in C12 condition on fixed thresholds/actions.
The comparison of the larger direct model with smaller confidence routing is
descriptive; no cross-size compute, latency, or energy advantage is measured.

Source for the following retained pilot rows:
[0.6B recorded policies](../../docs/qwen06-router-pilot-results.md#recorded-policies).
The reference remains the original confidence decisions, not the later refit.

| Policy | Accuracy (%) | Tokens/state | Utility | Δutility vs confidence and 90% interval |
|---|---:|---:|---:|---|
| Confidence | 81.250 | 1,062.52 | .759374 | 0 [0, 0] |
| Confidence OR parser rejection | 83.594 | 1,081.41 | .781867 | +.022493 [+.007453, +.044905] |
| Confidence-only Ridge | 79.688 | 1,254.07 | .734171 | −.025203 [−.057842, +.007138] |
| Three-feature Ridge | 82.031 | 1,148.45 | .762890 | +.003516 [−.031959, +.037163] |

The learned candidate passes positive-direction and matched-learner checks,
but fails the .01 and parser-control checks. Its recipe uses confidence,
`log(1 + answer tokens)`, v7 rejection, training-only scaling, α=10, and predicted
gain >0, with no inner grid. Source:
[pilot protocol](../../docs/qwen06-router-pilot-protocol.md).

### N4. Selected cap comparison

Source: [cap results](../../docs/qwen17-cap-bridge-results.md).
Each of 11 questions receives equal weight after averaging its selected cells.
The comparator is 2k thinking; cost and utility below are for the thinking call.

| Outcome | 2k | 4k | Difference | Paired 95% interval |
|---|---:|---:|---:|---|
| Scored accuracy (%) | 36.36 | 40.91 | +4.55 percentage points | [0, +13.64] percentage points |
| Tokens/call | 2,430.59 | 4,093.05 | +1,662.45 | [1,225.67, 1,996.95] |
| Call utility | .242107 | .204439 | −.037668 | [−.094767, +.061647] |

The source writes the accuracy interval in fractions [0, .136364]; the display
above converts units and rounds to two decimal places. This is a presentation
conversion, not a new interval calculation. Do not subtract rounded column
means to replace the reported token difference.

All 18 paired reasoning prefixes match; new 2k streams replay old controls.
Observed: one rescue, no harms. Secondary cell counts are 6/18 versus 7/18 and
are not the question-weighted accuracy. Eight accepted 4k outputs are scored
incorrect and three rejected. These extraction categories do not explain
mathematical errors or the original learner's failure.

## 4. Methods and appendix source registry

These are protocol or accounting facts, not independent scientific effects.
The [existing ledger](evidence-ledger.md) retains exact hashes and additional
settings. New wording must follow the primary linked document, with its scope.

| ID / manuscript content | Fixed facts or evidence | Primary source and limit |
|---|---|---|
| **M01. Decision equation** | U(a)=Y_D+a(Y_T−Y_D)−.05(C_D+aC_T)/1000; incremental target G=Y_T−Y_D−.05C_T/1000. | [Repeat protocol](../../docs/phase-2-repeat-panel.md), [results](../../docs/phase-2-repeat-results.md). Thinking is a fresh solve; future thinking information cannot enter features. |
| **M02. Repeat grouping and features** | 50 questions, eight draws/mode, 800 responses/400 pairs; five outer folds of ten; four inner folds; 40 outer/30 inner training questions; A indices 0–3, B 4–7. 387 question + four draft features; α {1,10,100}. | [Repeat protocol](../../docs/phase-2-repeat-panel.md). Different D/T seeds, index pairing only, no 8×8 expansion. Two directions are not two independent cohorts. |
| **M03. CPU settings** | α {100,1000,10000}; gain thresholds {0,.02,.05}; confidence-correction margins {.02,.05,.10}. | [CPU protocol](../../docs/phase-2-cpu-feasibility-protocol.md). Training-only preprocessing/selection. |
| **M04. Compact neural settings** | Two representations × four losses; PCA8 + four statistics; 120-parameter 12→8/two-prototype head; Adam .01, decay .001, 100 epochs, one seed 20261004; margins {−.1,0,.1}, cosine temperature .1. | [Representation protocol](../../docs/phase-2-contrastive-protocol.md), [results](../../docs/phase-2-router-feasibility-results.md). One fusion/compression/optimization recipe. |
| **M05. CLM settings and assets** | 4-bit 8B encoder, 4,096-dimensional last-token representation, frozen released heads, scalar calibration and raw PCA8 controls; 400 states + two action encodings; 450 Ridge/75 PCA fits. | [CLM protocol](../../docs/phase-2-clm-probe-protocol.md), [results](../../docs/phase-2-clm-probe-results.md), [local preflight](../../docs/clm-local-preflight.md). No auxiliary confidence/draft statistics in learned families. Exact revisions/MLX versions in ledger Section 4. |
| **M06. Generation identities** | Qwen3-1.7B/0.6B pinned revisions; qwen3-boxed-budget-v3; MPS float16 SDPA batch one; direct T=.7/top-p=.8/top-k=20; thinking T=.6/top-p=.95/top-k=20; 2,048 reasoning/512 answer cap; closure [151668,271], EOS [151643,151645]. | [Protocol reconciliation](../../docs/phase-1-protocol-reconciliation.md), [opportunity protocol](../../docs/opportunity-panel-protocol.md), [ledger Section 2](evidence-ledger.md#2-data-generation-and-scoring-identities). No model asset read for R1. |
| **M07. Scorer and roles** | Frozen numeric-v7 for main routing studies; GSM8K upstream training rows with fixed roles; official-test allocation and confirmation outcomes absent. | [Parser preflight](../../docs/parser-preflight.md), [repeat protocol](../../docs/phase-2-repeat-panel.md), [opportunity protocol](../../docs/opportunity-panel-protocol.md), [sparse preparation](../../docs/sparse-validation-preparation-results.md). Normalized-prompt exclusions do not prove pretraining or semantic-family disjointness. |
| **M08. Engineering bridge** | 25 questions, 200 responses, matching token sequences in tested cells; primary v5. | [Bridge record](../../docs/phase-1-bridge.md). References materialized after role freeze; workers did not read them; comparative scoring waited for completion. Do not impose later reference-first-open rules on this bridge. |
| **M09. Parser compatibility** | 56 fixtures, 1,900 cached outputs, one additional extraction, zero accepted-answer regressions. | [Compatibility record](../../docs/phase-2-parser-compatibility.md). Gold-free syntax check; primary v7 labels unchanged. |
| **M10. Bootstrap identities** | 2,000 question resamples; repeat/CPU seed 20261002; neural 20261004; averaged CLM 20261006; opportunity 20261009; pilot 20261012; sparse 20261018; cap 20261020. | Respective [repeat](../../docs/phase-2-repeat-panel.md), [CPU](../../docs/phase-2-cpu-feasibility-protocol.md), [neural](../../docs/phase-2-contrastive-protocol.md), [CLM](../../docs/phase-2-clm-probe-protocol.md), [opportunity](../../docs/opportunity-panel-protocol.md), [pilot](../../docs/qwen06-router-pilot-protocol.md), [sparse](../../docs/qwen06-sparse-validation-protocol.md), and [cap](../../docs/qwen17-cap-bridge-protocol.md) protocols. CLM deviation rule in N2 applies. |

If an appendix retains exact model/source hashes, copy the existing ledger
and primary protocol identity, rather than shortening a hash as if it were
the full value. Existing source digests are identities, not new verification
of underlying files in this writing pass.

### A01. Operational charges

Role: recorded collection accounting. Unit: charged tokens across attempts,
including inserted tokens, failures, and unresolved reservations where applicable.
There is no policy-performance comparator.

| Study | Tokens | Recorded attempts/setups | Source and required qualification |
|---|---:|---|---|
| Repeat | 644,519 | 806 attempts: 800 completed/six failures; three setups | [Repeat results](../../docs/phase-2-repeat-results.md); original failure retained. |
| Two-solver | 384,552 | Four setups/invocations | [Opportunity results](../../docs/opportunity-panel-results.md#runtime-and-preservation); expired original wall budget and unresolved charges retained. |
| Sparse | 43,448 | 229 completed attempts; one setup | [Sparse results](../../docs/sparse-validation-results.md); no unresolved reservation. |
| Cap | 127,171 | 38 reservations; three setups/invocations | [Cap results](../../docs/qwen17-cap-bridge-results.md#accounting-and-boundaries), [completion protocol](../../docs/qwen17-cap-bridge-completion-protocol.md), [ledger accounting](evidence-ledger.md#8-accounting-and-retained-deviations); failed/unknown charges retained. |

These are not deployed-policy costs. Do not sum reused reports into a new
efficiency metric. The cap report says new calls completed below the old
600-second deadline; recovery does not identify the cause of earlier stalls.
The completed result records report $0 cloud/API experiment spending. This
does not imply free local computation or energy.

## 5. Prior-work and contribution mapping

These are literature-context claims, not project outcomes. They rely on the
dated primary-source checks in [related-work notes](related-work-notes.md) and
the [10 October contribution review](reviewer-contribution-2026-10-10.md).
R1 adds no new literature search or external benchmark comparison.

| ID / permitted context | Source record | Required limit and revision use |
|---|---|---|
| **L01. Repeated solver supervision and contrastive routing have prior work.** | RouterDC, CSCR, SEMIROUTER entries in the related-work notes and bibliography. | No priority for these components. No faithful reproduction or superiority result here. |
| **L02. Post-draft accept-or-think routing already exists.** | DART v4 full-text check, Sections 2.2/4.2/E.1, in the contribution review. | Explain our one-draft/fixed-budget setting; do not call post-draft routing new. Add a dated correction to the old abstract-only retrieval limit. |
| **L03. Stochastic ceilings and hindsight unions differ.** | Chen v3, Sections III–VI/Appendix C, in both source reviews. | No new oracle theorem; no hindsight score as deployable ceiling. |
| **L04. Scoring artifacts and router collapse are established evaluation concerns.** | Garg and Sagtani, Sections 3/5/8, in the source reviews. | C06 excludes reversal by flagged cases only. Do not imply our diagnostics reproduce their mechanism tests. |
| **L05. Failure risk and protocol value are already distinguished.** | Yang et al., Sections 2–5, in the source reviews. | Our stochastic outcome evidence is local; the general distinction is not the new claim. |
| **L06. CLM is cited as an author release; exact MiniLM already has contrastive sentence training.** | Official CLM/model-card and all-MiniLM-L6-v2 checks in related-work notes. | No invented proceedings claim, full-precision fidelity claim, or contrastive-pretraining-versus-none experiment. |
| **L07. Dataset/model and adaptive-reasoning context** | GSM8K, Qwen3, Thinkless, BEST-Route entries in related-work notes and `references.bib`. | Retain only verified design descriptions. Do not import external efficiency percentages into project comparisons. |

C00 is an inference about the conjunction C01–C18. L01–L07 constrain its
novelty language; they do not establish that this conjunction is first or
sufficient for publication.

## 6. Deductions and claims that must remain separate

### D01. Sparse contrast and finite-panel ceiling

By the frozen rule, changed states are accepted by plain confidence and rejected
by v7. Their direct correctness is zero under that scorer, without a reference
lookup. On unchanged actions, the shared-action contrast is zero. Thus:

\[
\Delta U_i=z_i(Y_{T,i}-.05C_{T,i}/1000)\le z_i.
\]

C16 reports `Σz_i=1` for 228 questions. Therefore the realized-mask ceiling is
`1/228 < .01` before nonnegative token cost. This is C17's reviewer deduction.
It is not an estimate of the population activation rate or expected policy gain.

### D02. Sparse bootstrap support

C16's 227 zeros and one negative contribution imply that resampling those
observations cannot generate a positive rescue. Preserve the reported 95%
interval and explain this empirical support limit. Its upper endpoint zero
does not establish that future population benefit is nonpositive.

Source for both deductions: the [sparse protocol](../../docs/qwen06-sparse-validation-protocol.md),
[completed result](../../docs/sparse-validation-results.md), and
[methods review](reviewer-methods-2026-10-10.md). These are written algebra and
interpretation; no bootstrap or analysis is run for this map.

### Unsupported extensions

| Do not write | Reason / evidence boundary |
|---|---|
| Repeated supervision is useless; routing is unlearnable. | C01/C07–C10 test specified learners, small training sets, and selected endpoints. |
| The positive variance proves the primary reproducibility test passed. | C03 and C04 are different statistics with different roles. |
| Same-question transfer proves useful acquisition or unseen-question prediction. | C05 uses prior labels of those questions and omits their acquisition cost. |
| Half splitting is a new anti-leakage method or two independent replications. | M02's question folds already exclude evaluation questions; halves reuse groups. |
| Formatting cannot explain any router failure. | C06 concerns only flagged cases with actions and costs fixed. |
| CLM or contrastive learning has no useful signal. | C09/C10 are limited recipes; no full-precision or feature-addition control. |
| Smaller models benefit more from thinking in general. | C12 is a two-checkpoint, one-panel descriptive comparison. |
| The fresh test proves population harm or exactly replicates the three rescues. | C15 refits the policy; C16/D02 have one event and limited bootstrap support. |
| A larger cap reduces population utility. | C18's interval crosses zero on a selected 11-question cohort. |
| The paper measures deployment efficiency. | C11/M06/A01 do not include complete live router/solver compute. |

## 7. Manuscript coverage and R1 completion

| Planned v0.2 section/display | Claim/source coverage |
|---|---|
| Abstract, Introduction, Conclusion | C00 with C01–C10; bounded scope from C12–C18 and L01–L07 |
| Decision and Methods | M01–M10; grouping/interval rules in Section 1 |
| Original gate table and repeat behavior | C01–C03, N1 |
| New post-hoc box and robustness paragraph | C04–C06; keep C03 adjacent |
| Bounded-control table and interpretation | C07–C11, N2 |
| Two-solver table | C12, N3 |
| Pilot/refit/fresh follow-up | C13–C17, N3, D01–D02 |
| Cap summary and appendix table | C18, N4 |
| Identities, bridge/parser history, charges and deviations | M05–M10, A01, existing ledger |
| Figure 1: study map | M02, C07–C18; explicit 50-question reuse, cap subset, fresh separation |
| Figure 2: utility contrasts | C01/N1 versus its selected baseline; C07–C10/N2 versus confidence, in separate panels |
| Figure 3: two-solver descriptive plot | C12/N3; separate model symbols and draw-dependent availability counts |

Precision checks:

- C01's six-decimal interval comes from the tracked repeat protocol's terminal
  result; the main result table displays fewer digits. This is a documented
  precision difference, not a contradiction or a new raw-data extraction.
- C18's accuracy interval is explicitly converted from a fraction to percentage
  points. Rounded means are not used to reconstruct differences.
- Reported point values, intervals, and source-specific rounding are retained.
  Any newly requested value absent from these records remains unavailable
  until a separate permitted export; it is not filled by inference.

R1 maps all planned central numerical claims and routes retained method,
secondary-table, and appendix details to their protocol/ledger sources. It
does not certify formal statistical coverage, mathematical scoring validity,
novelty, or publication readiness. No substantive source conflict is resolved
by changing outcomes. Missing full-refit uncertainty and other research gaps
remain limits, rather than transcription tasks.

**R1 complete.** Document checks found no missing local source/section links or
duplicate claim IDs. A separate GPT-6.1-sol/xhigh methods review found no blocking
number/comparator/qualifier mismatch in the central claims and registers.
Its wording correction is applied to C05: different directional point estimates
do not establish a statistically tested asymmetry. This was document review,
not an independent reproduction of the experiments.

Manuscript v0.1 remains unchanged. R2–R6 are pending. The next task is the central
text revision using C00–C06, followed by the other scheduled passes. No raw
response, score cache, training reference, sealed outcome, model asset, executor,
test suite, statistical analysis, or figure export was accessed or run for R1.
