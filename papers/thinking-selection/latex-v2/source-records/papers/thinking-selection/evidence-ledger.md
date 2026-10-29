# Evidence ledger for the empirical thinking-selection manuscript

Prepared 2026-10-09 from tracked protocol and result documents on
`codex/confidence-acquisition-plan` (`70b1c25` at the initial branch check).
This is a documentation audit for drafting. It reads no raw run, outcome,
reference, cached-score, model or sealed artifact and performs no analysis,
fitting, scoring, inference or test execution. Numerical precision below is the
precision published in the linked documents; missing detail is identified at
the end. The manuscript outline is a writing guide rather than an additional
experimental source.

## 1. Decision, labels and units

| Claim / Methods fact | Exact supported statement | Source / qualification |
|---|---|---|
| M1: post-direct contract | After paying for a completed direct draft D, accept it or request a fresh question-only thinking solve T. Thinking is not continuation of the draft. | [Repeat protocol](../../docs/phase-2-repeat-panel.md#frozen-estimands); [CLM protocol](../../docs/phase-2-clm-probe-protocol.md#encoder-heads-and-one-input-recipe); [opportunity protocol](../../docs/opportunity-panel-protocol.md#fixed-diagnostic-analysis). |
| M2: policy utility | `U(a)=Y_D+a(Y_T−Y_D)−.05(C_D+aC_T)/1000`, for a binary escalation action a and scored correctness Y. | The direct draft remains in every policy's total cost. λ=.05 means .05 utility per 1,000 generated/inserted tokens, not per token. [Repeat protocol](../../docs/phase-2-repeat-panel.md#frozen-estimands). |
| M3: training/action gain | `G=Y_T−Y_D−.05C_T/1000`. Direct cost is sunk and cancels from the incremental choice. | Rescue (`Y_D=0,Y_T=1`), harm (`Y_D=1,Y_T=0`) and positive utility gain (`G>0`) are distinct definitions. [Opportunity protocol](../../docs/opportunity-panel-protocol.md#fixed-diagnostic-analysis). |
| M4: standalone modes | Standalone thinking-minus-direct utility is `Y_T−Y_D−.05(C_T−C_D)/1000`. | This is a different estimand from escalation after a direct draft. Do not label sequential always-escalate costs as standalone thinking costs. [Repeat protocol](../../docs/phase-2-repeat-panel.md#frozen-estimands); [two-solver results](../../docs/opportunity-panel-results.md#fixed-policy-results). |
| M5: token basis | Charged output includes generated and inserted tokens; prompt/prefill tokens are separate. | The reconciliation document separately defines stage/result/setup time. Policy token utility excludes router encoding, setup, research acquisition, failed attempts and live contention. Operational ledgers include setup/failures/unknown reservations. [Reconciliation](../../docs/phase-1-protocol-reconciliation.md#accounting-recovery-and-source-provenance). |
| M6: observational unit | Question groups receive equal weight in repeat/control, opportunity and sparse means/uncertainty. | Draws, state rows, folds and fit counts are not additional independent question groups. Cap primary means first average selected cells within each question and then weight the 11 questions equally. [Repeat protocol](../../docs/phase-2-repeat-panel.md#frozen-estimands); [cap runtime](../../docs/qwen17-cap-bridge-runtime-protocol.md). |
| M7: scorer-defined correctness | Incomplete and parser-rejected outputs count as incorrect under the pinned scorer. Extraction receives no reference; correctness comparison follows extraction of one value. | Scorer acceptance is not an independent correctness guarantee, and rejection does not prove mathematical error. Human scoring audit was waived. [Parser policy](../../docs/parser-preflight.md#gold-independent-extraction-policy); [repeat results](../../docs/phase-2-repeat-results.md). |
| M8: confidence | Primary confidence is mean generated log probability after temperature/top-k/top-p decoder warping. Raw pre-warper likelihood is a separately recorded quantity. | Neither is a calibrated probability of correctness. Repeat and all later main comparisons retain post-warper confidence; raw confidence is secondary in the two-solver protocol. [Reconciliation](../../docs/phase-1-protocol-reconciliation.md#new-generation-and-scoring-identities); [opportunity protocol](../../docs/opportunity-panel-protocol.md#fixed-diagnostic-analysis). |

The cap table below reports **thinking-call** tokens and utility, unlike the
post-direct routing tables. Direct costs cancel in its paired 4k−2k contrast.
Any optional total post-direct cap metric must identify the reused cached
direct cost charged identically to both arms. [Cap protocol](../../docs/qwen17-cap-bridge-protocol.md).

## 2. Data, generation and scoring identities

### Shared real-data contract

| Item | Frozen value / rule | Primary document |
|---|---|---|
| Source task | Cached GSM8K upstream training question column, revision `740312add88f781978c0658806c59bc2815b9866`; 7,473 source rows. Arrow raw SHA-256 `6146bca074f4c6c5e07de7e96cc968adab3833dbdafeda21830f27558eea3d9b`. | [Bridge allocation](../../docs/phase-1-bridge.md#frozen-allocation). |
| Original roles | 25 bridge, 50 repeat, 1,200 acquisition, 200 validation, 2,000 new sealed confirmation, 548 reserve. Selection uses question ID/normalized prompt hashes; source indices support later selected-reference access. | Same source; parent payload `c2b28b3d32612517f549a054ae2107185f26181e487b22d027ed59c207d3a4fd`. No outcome was used to allocate roles. |
| Exclusion boundary | Historical IDs and normalized prompts are excluded; roles have unique IDs and normalized prompts. | Normalized deduplication is not a semantic-template-family exclusion claim. The project's 500-question official-test allocation is distinct from the size of GSM8K's full official test split. [Bridge allocation](../../docs/phase-1-bridge.md#frozen-allocation). |
| Solver 1 | `Qwen/Qwen3-1.7B`, model/tokenizer revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`. | [Reconciliation](../../docs/phase-1-protocol-reconciliation.md#new-generation-and-scoring-identities). |
| Solver 2 | Qwen3-0.6B, model/tokenizer revision `c1899de289a04d12100db370d81485cdf75e47ca`. | [Opportunity protocol](../../docs/opportunity-panel-protocol.md#questions-solvers-and-jobs). |
| Main generation identity | `qwen3-boxed-budget-v3`, local batch one, MPS / float16 / SDPA. | [Reconciliation](../../docs/phase-1-protocol-reconciliation.md#new-generation-and-scoring-identities); [opportunity protocol](../../docs/opportunity-panel-protocol.md#questions-solvers-and-jobs). |
| Prompt suffix | `In your final response, give only the numerical answer in \boxed{}.` | [Reconciliation](../../docs/phase-1-protocol-reconciliation.md#new-generation-and-scoring-identities). This is the suffix, not a transcription of the whole chat template. |
| Main caps | 2,048 reasoning tokens, 512 answer tokens. Direct mode uses the answer allowance; thinking may insert forced closure. | Same source. Cap intervention changes only the reasoning allowance to 4,096. |
| Direct sampler | Temperature .7, top-p .8, top-k 20. | Same source. |
| Thinking sampler | Temperature .6, top-p .95, top-k 20. | Same source. These are sampled runs, not greedy results. |
| Closure / EOS | Forced closure `</think>\n\n`, IDs `[151668,271]`; EOS union `[151643,151645]`. | Same source; later actual tokenizer inspection in [repeat protocol](../../docs/phase-2-repeat-panel.md#actual-preparation-checkpoint). Inserted closure is charged. |
| Primary later scorer | Opt-in `numeric-v7`, implementation digest `c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964`, with dependencies pinned by each study. | [Parser preflight](../../docs/parser-preflight.md); [repeat protocol](../../docs/phase-2-repeat-panel.md#actual-preparation-checkpoint). Ordinary CLI remains v5. |

V7 uses an explicit anchored final-answer section when present, permits
explanatory prose around an explicit numeric anchor, requires binding/final
claims and additional numerals to agree, and uses exact rational arithmetic for
fractions/repeating decimals. It conservatively rejects malformed/unclosed
claims, conflicting alternatives, specified negation/relationship language,
incomplete flagged generations and unsupported formats. Without an explicit
final section it preserves v5 extraction/ambiguity rules. These are bounded
lexical rules, not a semantic verifier. [Parser preflight](../../docs/parser-preflight.md#gold-independent-extraction-policy).

### Evidence blocks and reference access

| Block | Questions / observations | Role, pairing and reference endpoint |
|---|---|---|
| Engineering bridge | 25 questions; 2 draws/mode; 100 responses per protocol arm, 200 total. | Same questions and matched seeds across legacy/v3 arms. Legacy source `6999eb5`, one EOS `151645`; v3 source `bbcaac2`, EOS union. **Bridge training answers were materialized after roles froze; workers never opened gold, and comparative v5 scoring waited for 200 responses.** Do not apply the later “references first opened after collection” claim to this bridge. [Bridge](../../docs/phase-1-bridge.md#fixed-bridge-design). |
| Repeat | 50 questions; 8 draws/mode; 800 responses / 400 paired states. | Unique deterministic seeds for each question/mode/draw; D/T paired by index only, with different seeds. Reference access restricted to 50 selected training rows after full endpoint. [Repeat protocol](../../docs/phase-2-repeat-panel.md#fixed-data-and-inference). |
| CPU / MiniLM / released CLM | The same 50 questions / 400 direct states and paired outcomes. | Later bounded development reuse of unchanged cached v7 scores; no new solver responses or reference access. [Feasibility](../../docs/phase-2-router-feasibility-results.md#experimental-boundary); [CLM](../../docs/phase-2-clm-probe-results.md#scope-and-main-independent-half-comparison). |
| Two-solver opportunity diagnostic | 64 reserve-child questions; 2 draws/mode/solver; 512 responses / 256 pairs total, 128 pairs per solver. | Selection seed 20261007; five folds 13/13/13/13/12. Base seeds 20261010 (1.7B), 20261011 (0.6B); all 512 jobs/seeds distinct. Both arms complete plus exit/accounting gates before 64 selected training references. [Preparation](../../docs/opportunity-panel-preparation.md); [protocol](../../docs/opportunity-panel-protocol.md). |
| 0.6B Ridge/guard pilot | Reuses 64 questions / 128 paired 0.6B states; 20 Ridge fits. | Development only. No scoring/reference reopening. [Pilot protocol](../../docs/qwen06-router-pilot-protocol.md). |
| Fresh sparse guard | 228 disjoint reserve-child questions; 228 direct plus all eligible changed-action thinking responses, realized 1 thinking / 229 responses. | Policy fitted/frozen before fresh questions. Selection seed 20261018, job seed 20261019. Only eligible reference rows after full activated endpoint; realized 1 reference, other 227 unopened. [Preparation](../../docs/sparse-validation-preparation-results.md); [runtime](../../docs/qwen06-sparse-runtime-protocol.md); [results](../../docs/sparse-validation-results.md). |
| Cap bridge | 11 old opportunity-panel questions / 18 selected thinking cells; 36 new 2k/4k thinking responses. | All old forced-closure cells selected by metadata, not correctness. Identical inherited seed per new pair; 36 job IDs, 18 repeated per-cell seeds. Exactly 11 training references reopened under this new full endpoint; old labels unchanged. [Cap protocol](../../docs/qwen17-cap-bridge-protocol.md); [runtime](../../docs/qwen17-cap-bridge-runtime-protocol.md). |

Question snapshots in the later studies remain question-only with null gold
hash and no gold file. The manuscript uses tracked result records; reference
access in the completed studies is provenance, not a new action during writing.
Official-test and sealed confirmation outcomes contribute no result here.

## 3. Repeat learner: frozen fitting and all five gates

The repeat protocol froze at source `272403f`, protocol
`8b01db2cbb7b8d1777c40aa0a873f4626e4c6b2a04e9135a377a085a76f3c812`.
Its root seed is 20261002. [Repeat protocol](../../docs/phase-2-repeat-panel.md).

| Methods component | Frozen definition |
|---|---|
| Draw halves | A: indices 0–3; B: 4–7. At k=1,2,4, train on first k acquired draws of one half and evaluate all four draws of the opposite half. Reverse A→B and B→A. No 8×8 cross-pair expansion. |
| Reproducibility statistic | Compare a question's gain estimate from one half with its opposite-half estimate, versus the pooled mean from the other 49 questions in the prediction half; report symmetrized question-level MSE improvement and grouped interval. This is distinct from the held-out-question router utility comparison. |
| Outer split | Five question-only hash folds, 10 questions each. All draws of held-out questions are excluded from fitting/tuning. An outer fit has 40 distinct training questions; inner fits have 30. |
| Inner split | Four question folds using only acquired training-half labels. Opposite-half outcomes cannot choose settings or baselines. |
| Features | Frozen 50×387 question features: MiniLM 384-dimensional embedding plus 3 lexical features. Draft inputs: post-warper mean log probability, log answer length, v7 parse validity, truncation. Correctness and future thinking cost supply training targets; gold and thinking text do not enter decision features. |
| Learned families | Question-only, solver-only and combined Ridge; shared alpha `{1,10,100}`; training-only standardization; alpha selected by inner held-out utility, larger alpha on exact ties. Combined is the predeclared progression learner; no switch to the best diagnostic family. |
| Comparator | Strongest eligible accept / escalate-after-draft / fitted confidence baseline chosen within inner validation. It is **not automatically confidence in every condition**. Full8 happened to select confidence in all five folds. |
| Secondary full8 | Train all eight draws on outer-training questions, evaluate all eight on held-out questions. No independent same-question eight-draw replica exists. |
| Uncertainty | 2,000 paired whole-question bootstrap draws, seed 20261002, two-sided 90% intervals, fixed OOF fits. No full-training refit uncertainty or correction across seven conditions. |

Sources: [repeat protocol](../../docs/phase-2-repeat-panel.md#independent-halves-and-held-out-questions),
[models and gates](../../docs/phase-2-repeat-panel.md#models-acquisition-accounting-and-gates),
[repeat results](../../docs/phase-2-repeat-results.md).

| Predeclared gate | Published observation | Outcome |
|---|---|---|
| Four-draw split-half MSE improvement >0 and lower interval bound >0 | +.01158 utility²; 90% CI [−.01744,+.04848] | Fail |
| Combined-minus-inner-selected-baseline positive in both four-draw directions | A→B −.02679; B→A −.00562 | Fail |
| Direction-averaged per-question difference ≥+.01 and lower bound >0 | **−.016204**, 90% CI **[−.033276,−.000635]** | Fail |
| Secondary eight-draw comparison does not reverse direction | −.05163; 90% CI [−.07286,−.03204] | Fail |
| ≥10 distinct questions with any direct/thinking correctness difference | 14/50 | Pass |

The informative-question gate counts correctness differences (rescues **or**
harms), unlike the later two-solver availability screen, which counts positive
utility-gain questions only. Four of five fail; acquisition scaling stopped.
[Repeat results](../../docs/phase-2-repeat-results.md).

| Training draws / evaluation | Combined minus selected baseline | 90% grouped interval |
|---|---:|---|
| k1 A→B | −.02016 | [−.03665,−.00535] |
| k1 B→A | +.00641 | [−.01648,+.02445] |
| k2 A→B | −.02812 | [−.04975,−.00857] |
| k2 B→A | +.02257 | [−.00552,+.05804] |
| k4 A→B | −.02679 | [−.04973,−.00714] |
| k4 B→A | −.00562 | [−.02724,+.01357] |
| full8 held-out questions, secondary | −.05163 | [−.07286,−.03204] |

These rows retain the result document's rounded precision. Do not fabricate
additional digits for the directions or k1/k2 intervals. [Repeat results](../../docs/phase-2-repeat-results.md).

### Distinct full8 and mode-only descriptives

Across all 400 paired states: direct 358/400 (89.5%), 221.14 tokens/call;
standalone thinking 378/400 (94.5%), 1,389.83 tokens/call. States comprise 348
both-correct, 30 rescues, 10 harms, 12 both-wrong. Cached generation seconds
are 9.47 direct and 56.35 thinking, not measured live router latency.
[Repeat results](../../docs/phase-2-repeat-results.md).

| Secondary full8 OOF policy | Accuracy | Tokens / question-draw | Utility |
|---|---:|---:|---:|
| Accept direct | 89.50% | 221.14 | .88394 |
| Escalate after every direct | 94.50% | 1,610.98 | .86445 |
| Tuned confidence / inner-selected baseline | 92.50% | 466.88 | .90166 |
| Question-only Ridge | 88.25% | 815.82 | .84171 |
| Solver-only Ridge | 91.50% | 555.50 | .88722 |
| Combined Ridge | 89.00% | 799.49 | .85003 |

Post-hoc full8 combined escalates 174/400: 5 positive gain /169 nonpositive,
including 7 harms, and misses 25 positives. Confidence escalates 58/400:
16 positive /42 nonpositive, including 4 harms, and misses 14. These are
descriptive counts. Hindsight oracle and same-question label-transfer gains
are nondeployable and exclude label-acquisition expenditure; do not use them
as net acquisition gains. [Repeat diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation).

## 4. Bounded capacity, MiniLM objective and released-CLM controls

All reuse the 50 repeat question groups, fixed outer folds and unchanged v7
labels. A4→B4 / B4→A4 are the main endpoint; full8 is secondary. Nested
training-only evaluation does not erase research reuse. Confidence is the
mandatory comparator, with averaged four-draw **92.75% accuracy /628.47 tokens
/utility .896076**. Do not substitute full8 confidence's 92.50% /466.88.
[Feasibility results](../../docs/phase-2-router-feasibility-results.md#main-four-draw-comparison).

| Control block | Frozen recipes, fitting and screen | Main results |
|---|---|---|
| CPU capacity/calibration | Draft4 Ridge; PCA8 of question embeddings +3 lexical +4 draft features; conservative confidence corrections. New alphas `{100,1000,10000}`, thresholds `{0,.02,.05}`, correction margins `{.02,.05,.10}`. PCA fits unique permitted training questions; block scaling is training-only, divided by square root of dimension. Four inner folds select settings/family; ties favor larger alpha/threshold/margin, then listed family order. Exactly 1,035 Ridge /75 PCA fits. | Selected −.014287 vs confidence, 90% CI [−.025680,−.004425]; 90.75% /514.22 tokens /utility .881789. All 3 screen components fail. [CPU protocol](../../docs/phase-2-cpu-feasibility-protocol.md); [results](../../docs/phase-2-router-feasibility-results.md). |
| Compact MiniLM | `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU float32. Question-only versus normalized mean fusion with direct-draft vector; tail-256 draft encoding, masked mean pooling. PCA8 on permitted training states +4 draft statistics, no lexical features. Every family shares 120 parameters: affine 12→8, normalized state, 2 normalized learned 8-d action prototypes, cosine temperature .1. | Nested selected −.033817 [−.052515,−.017266]; 89.25% /604.82 tokens /utility .862259. All 3 screen components fail. 111/400 drafts (27.75%) truncated. [MiniLM protocol](../../docs/phase-2-contrastive-protocol.md); [results](../../docs/phase-2-router-feasibility-results.md). |
| MiniLM optimization/objectives | Gain MSE; `abs(g)`-weighted forward CE for `g>0`; mean of forward loss and action-to-state multi-positive reverse CE; unweighted binary CE. Full-batch Adam lr .01, decay .001, 100 epochs, seed 20261004, no early stopping/backbone updates. Eight families select margin from `{−.1,0,.1}` inside four inner folds; larger threshold then frozen family-order ties. Exactly 600 head /150 PCA fits. | All eight averaged family point differences negative; some intervals include zero. One seed and one fusion recipe limit conclusions. Weighted CE is not calibrated event/correctness probability. [MiniLM protocol](../../docs/phase-2-contrastive-protocol.md#fixed-objective-and-optimization-grid). |
| Released CLM | Pinned 4-bit MLX Qwen3-8B encoder, last normalized token state (4,096 components; float32 L2 normalization), actual frozen released projection heads, no finetuning. 400 question/direct-draft states +2 static actions, batch one; plain tokenization, no special tokens, tail-2,047 allowance. State excludes confidence/parser status/labels/future thinking text/cost. | Every diagnostic family fails its exploratory screen. All 402 encodings and 450 Ridge /75 PCA fits complete. No actual state truncation (maximum 659 tokens). [CLM protocol](../../docs/phase-2-clm-probe-protocol.md); [results](../../docs/phase-2-clm-probe-results.md). |
| CLM matched control/calibration | Zero-shot margin `>0`; scalar-margin standardized Ridge; raw same-backbone PCA8/Ridge. Learned alphas `{100,1000,10000}`, thresholds `{0,.02,.05}`, four inner folds; larger alpha/threshold ties, frozen family order. Neither learned family includes auxiliary draft statistics. | Backbone matched, but feature dimension, pretrained head capacity and prior training differ: no causal isolation of contrastive pretraining. [CLM protocol](../../docs/phase-2-clm-probe-protocol.md#policies-and-bounded-supervision). |

CPU screen: selected average gain ≥.01, positive directional means, all
leave-one-question-out average gains positive. MiniLM and CLM retain this screen.
All are further-study screens, not original gate replacements. Fixed-fit 90%
question bootstrap uses 2,000 resamples: seed 20261002 CPU, 20261004 MiniLM,
20261006 CLM averaged comparisons. [Protocols linked above](../../docs/phase-2-clm-probe-protocol.md#questiondraw-splits-reporting-and-exploratory-screen).

| CPU family | A4→B4 | B4→A4 | Average Δ vs confidence | 90% averaged interval |
|---|---:|---:|---:|---|
| Draft4 Ridge | −.035707 | −.016369 | −.026038 | [−.043751,−.009692] |
| PCA8 combined | −.035707 | −.012907 | −.024307 | [−.042723,−.008291] |
| Conservative confidence correction | −.027005 | −.002362 | −.014684 | [−.026135,−.004588] |
| Nested selected new family | −.027005 | −.001569 | −.014287 | [−.025680,−.004425] |

| MiniLM representation / objective | Average Δ vs confidence | 90% averaged interval |
|---|---:|---|
| Question / gain MSE | −.036638 | [−.054962,−.019883] |
| Question / weighted forward CE | −.020187 | [−.040105,−.003085] |
| Question / bidirectional contrastive | −.025404 | [−.046890,−.006620] |
| Question / ordinary CE | −.014283 | [−.034851,+.004813] |
| Question+draft / gain MSE | −.038739 | [−.056249,−.022177] |
| Question+draft / weighted forward CE | −.013584 | [−.031964,+.001479] |
| Question+draft / bidirectional contrastive | −.027085 | [−.047376,−.009062] |
| Question+draft / ordinary CE | −.013854 | [−.034496,+.005116] |

Both tables are copied from [feasibility results](../../docs/phase-2-router-feasibility-results.md).
Selected CPU full8 equals confidence; selected MiniLM full8 is 88.75% /550.65
tokens, capturing no positive-gain paired opportunities and harming 3 drafts.
These secondary observations do not change the main failed screens.

### Released-CLM outcome and cost detail

Assets: `mlx-community/Qwen3-8B-4bit` revision
`545dc4251c05440727734bcd94334791f6ab0192`;
`Contrastive-LM/CLM-v0.1-8B` revision
`e939398d4556fcd9400c76fa8c5a513202f42b0a`; official head code commit
`bb42c6c5bf914fd449bed2f6ca65be80602cb1f7`. Isolated MLX 0.32.3 /mlx-lm 0.32.0.
[Local protocol](../../docs/clm-local-preflight.md#frozen-identities-and-isolation),
[task protocol](../../docs/phase-2-clm-probe-protocol.md#encoder-heads-and-one-input-recipe).

| Averaged four-draw CLM policy | Accuracy | Tokens / question-draw | Utility | Δ vs confidence | 90% averaged interval |
|---|---:|---:|---:|---:|---|
| Confidence | 92.75% | 628.47 | .896076 | — | — |
| Zero-shot | 94.75% | 1,550.53 | .869973 | −.026103 | [−.058826,+.016513] |
| Scalar calibrated | 88.50% | 443.71 | .862815 | −.033262 | [−.053818,−.015171] |
| Raw encoder PCA8/Ridge | 89.00% | 330.81 | .873460 | −.022617 | [−.043758,−.004464] |
| Nested selected family | 88.75% | 406.34 | .867183 | −.028893 | [−.049575,−.010922] |

Calibrated-minus-raw is −.010645 [−.018190,−.004292] on this same averaged
endpoint. Directional CLM deltas are: zero-shot −.016470 /−.035737;
calibrated −.035706 /−.030817; raw −.035706 /−.009527; selected
−.035706 /−.022080. [CLM results](../../docs/phase-2-clm-probe-results.md#scope-and-main-independent-half-comparison).

Zero-shot chooses thinking 380/400, with 30 positive /350 nonpositive choices
and 9 harms; positive-gain precision 7.89%. Post-hoc tie-aware AUROC is .500450
for CLM versus .705045 for negative confidence, paired difference −.204595
(90% interval [−.606961,+.195547]). Audit bootstrap: 2,000 whole-question
resamples, seed 20261007, all 8 draws together; rank comparisons are descriptive
on reused data. The wide interval prevents population ranking-inferiority claims.
[CLM assessment](../../docs/clm-research-assessment-2026-10-03.md#what-we-have-established-locally);
[audit protocol](../../docs/clm-signal-audit-protocol.md).

Task encoder worker: 575.67 s, mean state encoding 1.427 s /p95 2.244 s,
peak MLX 4.895 GiB, separately sampled RSS .972 GiB. CPU warm state projection
/two-action scoring .621 ms; fitting/evaluation 2.70 s. These are separate-run
observations; token utility excludes them. No full-precision equivalence,
pretraining disjointness, live co-resident latency or total unified-memory
accounting was established. [CLM results](../../docs/phase-2-clm-probe-results.md#real-input-and-resource-measurements).

**Reporting deviation:** 75 original per-condition policy intervals used CPU
helper seed 20261002 rather than CLM protocol seed 20261006. Primary averaged
intervals and calibrated-minus-raw interval already used the planned seed.
Use `repeat-clm-review-v1/conditional-intervals.protocol-seed.json`
(`ea1c9226…faaaf6`) for per-condition intervals; preserve the original report.
No sidecar numerical values were read for this ledger.
[CLM deviation record](../../docs/phase-2-clm-probe-results.md#reporting-deviation-and-additive-correction).

## 5. Two-solver diagnostic and 0.6B development pilot

The opportunity diagnostic fits 40 scalar cutoffs: 2 confidence features ×2
solvers ×2 draw directions ×5 folds. Training is one draw of other question
folds; evaluation is the opposite draw on held-out questions. Strict `<`
escalation and ties toward fewer calls are retained. Raw confidence is secondary;
the mandatory screens use post-warper confidence. Bootstrap: 2,000 shared
whole-question draws, seed 20261009, 90% intervals, actions/cutoffs fixed.
[Opportunity protocol](../../docs/opportunity-panel-protocol.md#fixed-diagnostic-analysis).

| Solver / policy | Accuracy over 128 scored outcomes | Tokens / question-draw | Utility |
|---|---:|---:|---:|
| 1.7B / accept | 84.375% | 228.01 | .832350 |
| 1.7B / escalate after every draft | 87.500% | 1,586.79 | .795661 |
| 1.7B / confidence | 83.594% | 682.56 | .801809 |
| 0.6B / accept | 61.719% | 209.80 | .606697 |
| 0.6B / escalate after every draft | 80.469% | 1,409.52 | .734211 |
| 0.6B / confidence | 81.250% | 1,062.52 | .759374 |

| Solver | Positive-gain questions (either draw) | Confidence−direct | Conditional 90% CI | Screens |
|---|---:|---:|---|---|
| 1.7B | 4/64 | −.030540 | [−.056066,−.006071] | Both fail |
| 0.6B | 24/64 | +.152677 | [+.085535,+.220375] | Both pass |

Availability requires ≥10 positive-gain groups; confidence screen requires
mean gain ≥.01 and positive points in both directions. Rescues /harms by draw:
1.7B 4/3 rescues, 2/1 harms; 0.6B 15/17 rescues, 4/4 harms. These data do not
establish a size-law or a formal population interaction. Two draws do not
identify a stable intrinsic question label. [Two-solver results](../../docs/opportunity-panel-results.md#fixed-policy-results).

The later 0.6B pilot fixes α=10 and training-only `StandardScaler` for two Ridge
families: post-warper confidence +`log1p(answer tokens)` +gold-free v7 rejection,
and matched confidence-only. Escalate at predicted gain `>0`; no inner search.
Ten folds/directions per family give 20 fits. Fixed controls: original confidence
actions, confidence OR rejection, accept, always escalate. Bootstrap seed
20261012, 2,000 question resamples, 90% fixed-action intervals.
[Pilot protocol](../../docs/qwen06-router-pilot-protocol.md).

| 0.6B development policy | Accuracy | Tokens / question-draw | Utility | Δ vs frozen confidence | 90% interval |
|---|---:|---:|---:|---:|---|
| Accept | 61.719% | 209.80 | .606697 | −.152677 | [−.224883,−.087749] |
| Always escalate | 80.469% | 1,409.52 | .734211 | −.025163 | [−.069654,+.018038] |
| Frozen confidence | 81.250% | 1,062.52 | .759374 | 0 | [0,0] |
| Confidence OR rejection | 83.594% | 1,081.41 | .781867 | +.022493 | [+.007453,+.044905] |
| Confidence-only Ridge | 79.688% | 1,254.07 | .734171 | −.025203 | [−.057842,+.007138] |
| Primary three-feature Ridge | 82.031% | 1,148.45 | .762890 | +.003516 | [−.031959,+.037163] |

The primary candidate passes positive directional points (+.002458 /+.004573)
and comparison with matched Ridge, but fails average ≥.01 and comparison with
parser control: **2 of 4 checks fail**. The guard's 3 extra escalations rescue
3 distinct questions, adding 2,419 tokens over 128 states. Its favorable
development interval is not fresh confirmation or a promoted novel method.
Positive-gain question sets differ across **different direct drafts**, not
repeated outcomes from one fixed state. [Pilot results](../../docs/qwen06-router-pilot-results.md).

## 6. Follow-up contrasts: sparse guard and cap extension

### Fresh sparse fixed-policy contrast

One plain-confidence threshold was fitted on all 128 cached 0.6B states, from
`−∞`, unique confidences and `+∞`, maximizing training incremental utility;
ties choose fewer escalations then lower threshold. The shared frozen cutoff
is **−.07951707680497253**. Plain policy escalates 85 training states, guard 87:
two changed states in this refit, rather than the old cross-fitted control's
three. Both prospective policies share this cutoff. [Sparse preparation](../../docs/sparse-validation-preparation-results.md#frozen-cutoff).

Fresh generation completes all 228 directs before freezing eligibility
(`v7 rejection AND plain-confidence accept`), then all eligible thinking jobs;
more than 32 is a hard resource stop. Shared actions contribute exactly zero.
For changed states, scorer-defined `Y_D=0`, so `Δ_q=Y_T−.05C_T/1000`.
Only the incremental contrast is identified. Bootstrap: 2,000 whole-question
draws, seed 20261018, 95% intervals. Screen: point ≥.01, lower bound >0.
[Sparse protocol](../../docs/qwen06-sparse-validation-protocol.md);
[activated runtime](../../docs/qwen06-sparse-runtime-protocol.md).

| Fresh outcome | Published value |
|---|---:|
| Changed actions | 1/228 |
| Extra thinking response tokens | 1,423 |
| Scored accuracy increment | 0 |
| Extra tokens per original question | 6.24123 |
| Mean incremental utility | −.000312061 |
| 95% question-bootstrap interval | [−.000936184,0] |
| Further-study screen | Fail |

Only the eligible thinking output is scored; v7 rejects it (`invalid_number`
in the repository orientation) and scores it incorrect. The result document
supports rejection/incorrectness without a mathematical audit. Absolute policy
accuracy/utility, 228-question direct accuracy and always-thinking counterfactual
are **not identified**. One changed event neither replicates the three old
rescues nor disproves all parser-aware routing. [Sparse results](../../docs/sparse-validation-results.md).

### Matched 1.7B cap contrast

The cohort comprises all 18 old forced-closure cells on 11 opportunity-panel
questions: seven contribute two cells, four one. Metadata-only enrichment,
not fresh sampling. New 2,048 and 4,096 reasoning arms retain per-cell seed,
question, sampler, 512 answer cap and all other inference settings. Arm order
alternates by cell parity. All 18 shared new reasoning prefixes match, and new
2k token streams exactly replay the old streams. [Cap protocol](../../docs/qwen17-cap-bridge-protocol.md);
[runtime](../../docs/qwen17-cap-bridge-runtime-protocol.md);
[results](../../docs/qwen17-cap-bridge-results.md).

| Equal-question thinking-call means (11 groups) | New 2k | New 4k | 4k−2k |
|---|---:|---:|---:|
| Scored accuracy | 36.36% | 40.91% | +4.55 percentage points |
| Generated/inserted tokens | 2,430.59 | 4,093.05 | +1,662.45 |
| Utility at .05 | .242107 | .204439 | −.037668 |

Paired 95% question-bootstrap intervals: accuracy [0,+.136364], extra tokens
[1,225.67,1,996.95], utility [−.094767,+.061647]. Exactly 1 rescue on 1 question,
no harms. Secondary 18-cell result is 6/18→7/18 correct; utility difference
−.033025. Both accuracy and utility intervals include zero. Use published
differences rather than subtracting rounded table means. Bootstrap uses Python
`random.Random(20261020).choices(groups,k=11)` with sorted question IDs,
2,000 replicates and linearly interpolated 2.5th/97.5th percentiles.
[Cap results](../../docs/qwen17-cap-bridge-results.md#result-at-the-frozen-cost-weight);
[runtime analysis](../../docs/qwen17-cap-bridge-runtime-protocol.md).

The matched prefixes support the intervention on these cells. They do not
establish general MPS determinism, whole-panel cap effectiveness, fresh
generalization or a default cap change. The longer allowance changes actual
reasoning **and potentially answer** token counts; +2,048 is not a fixed actual
cost. This study has no learned-router promotion gate and cannot replace the
earlier failed screens.

## 7. Parser and provenance evidence: narrowly permitted claims

| Claim | Published evidence | Boundary |
|---|---|---|
| Bridge engineering match | 200/200; every one of 100 matched cells has identical token sequences/terminations/extracted answers; both v5 modes 80% direct /94% thinking; both arms 81,593 charged tokens. Six engineering gates pass. | EOS 151643 was not emitted. Serial arm timing is not causal equivalence/speed evidence; observed cell identity is not universal protocol equivalence. [Bridge results](../../docs/phase-1-bridge.md#collection-result). |
| Parser v7 compatibility | Rejected v6 caused 44 gold-free prose regressions. Frozen v7 changes only the same final-180 case in each bridge arm among 1,100 responses; 900 historical extracts unchanged. Separate bridge sensitivity 82% direct /94% thinking. | Primary v5 bridge remains 80%/94%; one duplicated case, not two independent rescues. No model improvement. [Parser preflight](../../docs/parser-preflight.md#validation-sequence-and-result). |
| Bounded later wrapper | 56 syntax fixtures /1,900 cached responses; one balanced-bold declaration repair, no accepted-answer regression. | No correctness sensitivity/relabeling; primary/control labels stay v7. Compatibility does not certify numeric correctness. [Compatibility](../../docs/phase-2-parser-compatibility.md). |
| Repeat syntax bounds | 11 direct /16 thinking v7 rejections. Gold-free triage flags 5 presentation candidates, 5 incomplete outputs, 16 two-component answers on one question, 1 unmarked-terminal claim. Flagged fixed-action sensitivity cannot reverse combined-vs-baseline point comparison. | No gold/correctness audit; no claim about unflagged errors, refitted policies or new intervals. [Repeat syntax audit record](../../docs/phase-2-repeat-results.md#gold-free-parser-triage-and-bounded-sensitivity). |
| Independent arithmetic/preservation | Independent cached-only reviews reproduce recorded actions/metrics/intervals and verify frozen input/output hashes. | Reproduction supports arithmetic/provenance, not causal explanations, semantic scorer validation, new independent observations or the waived human audit. Sources: each linked result document. |

## 8. Accounting and retained deviations

Operational charges below are not realized average policy tokens and should not
be summed with reused policy tables into a new efficiency endpoint.

| Block | Recorded acquisition/runtime expenditure | Retained deviation / caveat |
|---|---|---|
| Repeat | 644,519 charged tokens; 806 attempts (800 completed /6 failed); 3 setups; 8.39463 cumulative operation hours. | Original supervisor stopped; additive recovery completed unchanged protocol/jobs/seeds/scorer. Cumulative hours are not calendar wall time. Docker correlation does not identify stall cause. [Repeat result](../../docs/phase-2-repeat-results.md). |
| Opportunity | 384,552 combined charged tokens; 16,134.02 operation seconds; 4 setups/invocations. Completion: 42,505 tokens /1,432.82 operation seconds /1,466.61 wall seconds. | Original 12-hour wall-budget failure remains failed; 452 originals +60-job child complete endpoint. Two old unresolved reservations remain charged. [Two-solver results](../../docs/opportunity-panel-results.md#runtime-and-preservation). |
| Sparse | 43,448 tokens /1,498.07 operation seconds /1,611.79 collection wall seconds; 229 completed attempts /1 setup, no failure/retry/unknown reservation. | Activated endpoint opens 1 training reference only. [Sparse results](../../docs/sparse-validation-results.md). |
| Cap | 127,171 combined tokens /7,262.9591 operation seconds; 38 reservations /3 setups and invocations. Child: 99,136 tokens /4,641.4133 operation seconds /4,655.2292 wall seconds. | Preserve both stopped parent launches, 2,814 failed tokens and unknown 4,610-token/600-second charge. New child has own 8-hour wall/charged limit and 1,800-second external job deadline, rather than parent's 4h/600s. All new calls finish below 600s, so the deadline extension does not establish recovery cause. [Cap results](../../docs/qwen17-cap-bridge-results.md#accounting-and-boundaries); [completion protocol](../../docs/qwen17-cap-bridge-completion-protocol.md). |

All recorded model experiments are local; Docker remained running and cloud/API
experiment spend is $0. No completed real-data acquisition-learning curve,
finetuning, RL, sealed confirmation or MATH replication supports this paper.
The G1 synthetic work belongs in a separately labeled appendix if included;
synthetic purchased lengths are not model-generated tokens.

## 9. Claim-to-record manifest for drafting

Digests are copied as published, including abbreviated digests where the tracked
document supplies only abbreviations. All artifact locations are provenance
pointers only; their contents were not opened for this ledger. Prefix paths are
under `artifacts/research/data-efficiency-v1/`.

| Claim ID / defensible wording | Tracked supporting record | Frozen result / plan identity |
|---|---|---|
| C1: combined repeat learner fails 4/5 gates | [Repeat results](../../docs/phase-2-repeat-results.md) and [protocol](../../docs/phase-2-repeat-panel.md) | `repeat-panel-v1/report.json`, payload `e4d17cc5…6d56` in [outline evidence table](../../docs/empirical-paper-outline-2026-10-09.md#4-claim-to-evidence-table); source `272403f`. |
| C2: tested CPU/MiniLM recipes fail their screens | [Feasibility results](../../docs/phase-2-router-feasibility-results.md) | CPU report `42e95eaa38bce5719ebcf700e6c0bf4527617ec7b8704cdd7a48034024502e01`; MiniLM report `e8ddebe38f211359eda4a60742e5cd388ea6a823981b60f7461293b21004a5eb`; source `1886bd4`. |
| C3: quantized released-CLM recipe fails screens; calibrated below matched raw control | [CLM results](../../docs/phase-2-clm-probe-results.md) | Report `5c05f6552c1c33ba7f5f426be1a23d4b053688fec008380792aef30ae907f117`; plan `270718aaaf58daed8c39f3b0e4decab428ea8b77082a7f80320a3702f022a88c`; source/test `5d40fa8`, launcher/protocol `ce1c7e6`. |
| C4: over-escalation / weak ranking descriptives are imprecise | [CLM assessment](../../docs/clm-research-assessment-2026-10-03.md) | Completed audit report `d5010392c5d9560bc2920164d591b9c16ff98635517d0acf1a7b229ed61a26f7`; additive source `a266621`. |
| C5: opportunity and confidence utility differ across the tested two sizes | [Two-solver results](../../docs/opportunity-panel-results.md) | `opportunity-panel-v1/completion-v1/report.json`, `f3f0d33c…ac6fd`; cached scores `f1326bf3…01283`; completion source `b7c3b1e`. |
| C6: failed learned 0.6B pilot plus sparse favorable development guard | [0.6B pilot results](../../docs/qwen06-router-pilot-results.md) | `qwen06-router-pilot-v1/report.json`, `ccdd2a2a…20ccf`; plan `1d0f145a…460a0`; source `8413e9e`. |
| C7: frozen fresh guard changes 1 action, with zero scored gain | [Sparse results](../../docs/sparse-validation-results.md) | `qwen06-sparse-validation-v1/runtime-v1/report.json`, `ee07790d…a98ed`; score cache `4e545a59…1b690`; plan `e7479290…bff9b`. |
| C8: enriched cap extension has one rescue and lower point utility, with interval crossing zero | [Cap results](../../docs/qwen17-cap-bridge-results.md) | `qwen17-cap-bridge-v1/completion-v1/report.json`, `11e61657…e1622`; scores `38a91695…0ca47`; source `dd4d733`. |

## 10. Details unavailable under this documentation-only audit

Do not supply guessed values for the following. They are recorded in frozen
source/manifests according to the protocols, but are not fully transcribed in
the audited tracked protocol/result documents.

- Exact full chat template and special-token placements for direct/thinking
  generation; the prompt suffix and sampler/cap identities above are documented.
- Exact confidence averaging implementation, including any EOS/special-token
  inclusion convention. The documented signal is post-warper mean generated
  log probability; avoid claiming entropy, calibrated probability or an alternate
  length normalization.
- Names/formulas of the three lexical features and the repeat panel's exact
  answer-length/truncation transforms. The 0.6B pilot explicitly documents
  `log1p(answer tokens)`; do not silently transfer it to every earlier feature.
- Exact repeat confidence tie enumeration, ridge action threshold/intercept
  details, fold hash algorithm and package versions beyond values explicitly
  cited here. Later sparse and cap protocols are more explicit.
- Exact CLM plain-text state/action template, full official head architecture,
  all dependency versions and quantizer settings beyond the pinned model
  revision. State semantics and the tested processing are documented.
- Full-precision CLM fidelity, pretraining overlap, live end-to-end latency,
  complete memory usage, full-refit uncertainty and semantic-family separation
  are **untested**, not merely missing transcription.
- Unrounded repeat directional/per-condition numbers and corrected CLM
  per-condition intervals are unavailable without an approved frozen cached
  export. Use the documented precision and keep the planned-seed sidecar rule.
- Sparse absolute policy performance is **unidentified by design**; a future
  report export cannot recover the missing reference/counterfactual observations.

The smallest defensible narrative is recipe-specific failure under a fixed
post-direct cost contract, differing opportunity regimes in two Qwen3 sizes,
and carefully limited follow-up of development observations. Describe the
original studies' gates as predeclared; describe the manuscript's overall
research questions and cross-study narrative as retrospective. No result
identifies a universal failure of learning/contrastive representations, a
causal reason for the failures, an acquisition benefit or superiority over an
external contemporary method.

## Final editorial review

The methods reviewer checked the corrected draft against the tracked records
and found no remaining numerical, endpoint, cost, selection, or interval
mismatch. The literature reviewer checked the 13 cited sources against the
verified bibliography. Four additional bibliography entries remain optional.

Root also inspected two small portions of the tracked implementation without
execution: `repeat_stats.py` uses a positive predicted-gain threshold for the
original Ridge policy; `_reproducibility` uses the other questions' mean from
the source half to predict the opposite half. This confirms the manuscript's
clarification of the protocol's phrase “prediction half.” The original
docs-only extraction limits above remain a record of that audit's scope.

No raw score, response, reference, or sealed data were read for this manuscript.
No experiment, statistical analysis, or test suite was run. This review does
not certify formal ASD-STE100 compliance; technical terms and equations are
retained for scientific precision.
