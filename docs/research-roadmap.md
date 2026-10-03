# Research roadmap: budgeted trace acquisition

**Decision record, updated 2026-10-03.** The original target was an 8–12-week, evidence-first study on the local M2 Pro with a **$100 total cloud ceiling**. The failed signal gate adds the bounded feasibility phases below; historical week labels are not a renewed completion promise. Work on `codex/research-data-efficiency` starts from `15a4d2d`; `1b67fbc` is the first checkpoint. This document is an execution checklist, not a claim of a new method or a record of completed experiments.

The [October checkpoint and contrastive-router review](contrastive-router-review-2026-10-02.md)
adds a controlled representation/objective investigation. First establish value
beyond confidence with cheap models; treat released CLM-8B as an optional,
separately costed probe. Contrastive routing, cost-aware contrastive routing and
sparse-data routing all have direct prior work. The acquisition hypothesis
remains conditional on fresh evidence of useful routing signal.

**Phases 2a–2c completed on 2026-10-03.** The narrow parser candidate passes
compatibility while v7 labels remain unchanged. The CPU capacity/calibration
and compact representation/objective studies both fail their exploratory
promotion screens. The training-selected policies average −0.014287 and
−0.033817 utility versus confidence, respectively. All eight neural families
have negative average point differences. [Results and verification](phase-2-router-feasibility-results.md).
Do not expand the completed architecture search or scale acquisition on this
evidence. The subsequent user-authorized **local** released-head synthetic
preflight passes with a 4-bit MLX Qwen3-8B encoder; it tests engineering, not
routing quality. The [power/design review and local results](local-clm-and-power-results.md)
are complete. The subsequent [cached released-CLM diagnostic](phase-2-clm-probe-results.md)
also completed and failed every exploratory screen: calibrated CLM averages
−.033262 versus confidence, raw encoder control −.022617. Zero-shot CLM chooses
thinking on 95% of drafts and loses utility at λ=.05. Close this bounded recipe.
Next is a separately frozen broader opportunity-rate diagnostic; new generation
still needs its own protocol and question roles.
The [deep CLM assessment and cached score audit](clm-research-assessment-2026-10-03.md)
find weak positive-gain ranking in the tested released score (AUROC .500450),
with imprecise intervals. CLM remains a conditional representation/control,
not an established method contribution. The
[64-question reserve child](opportunity-panel-preparation.md) is now prepared and
verified with no outcomes/references: second-solver local assets/closure,
collection/scorer/analysis endpoints and global budgets remain pending.
The user's latest preference keeps experiments local; the earlier cloud ceiling
is not an instruction to launch cloud work.

The main hypothesis is that choosing **which question, continuation action, and independent repeat to observe** can train a calibrated router to reach a held-out utility target with fewer *acquired generation tokens* than strong acquisition baselines. The solver remains frozen at Qwen3-1.7B. GSM8K and a numeric-answer MATH subset are the two core tasks. If the proposed acquisition rule does not win, report the strongest reproducible empirical result or a well-controlled negative result. Do not add a neural architecture or reinforcement-learning claim to compensate for a failed acquisition comparison.

## Evidence and preservation boundary

- The shared-correctness router has only reused-question development evidence: at the historical primary preference `λ = 0.05`, it achieved 90.25% accuracy at 622.0175 charged tokens per question, while tuned confidence achieved the same accuracy at 589.375. Its apparent high-accuracy advantage at other preferences is exploratory. The original continuation router's fresh diagnostic advantage over confidence was +0.008188 utility with a paired interval crossing zero. Neither result establishes superiority. See [the research review](research-review-2026-09-24.md) and [development report](router-dev-results.md).
- Keep `artifacts/router-dev/shared-base-v1/` as the uncorrected historical artifact. Its “always-thinking” row charged a first direct draft; the [first Phase 1 checkpoint](phase-1-evidence-repair.md) corrected this in `shared-base-v2/` and verified v1 remained unchanged. The corrected standalone thinking result is 91.50% accuracy, 1,430.69 charged tokens per question, utility 0.8434655 at `λ = 0.05`, and 60.1361 cached generation seconds per question. Shared minus standalone thinking utility is +0.027933625. Shared minus confidence is unchanged.
- Keep `artifacts/confirmation/frozen-router-v1/` intact. Its 3,100 upstream GSM8K training questions, models, source snapshot, analysis plan, and 15,500 planned jobs belong to the **unchanged old joint router**; its status is `prepared` with generation not started. Do not reuse those IDs or relabel that protocol as a test of a revised policy. The separate official 500-question GSM8K test allocation stays sealed **until the final model and analysis protocol are frozen**; any later official-test result is reported separately from the new upstream-training confirmation.
- The human scoring audit was explicitly waived. Record agent and automated reviews as such; do not describe them as human validation or silently reopen the waiver.

## Data and cost ledger

The current upstream GSM8K training pool has **4,023 unused, nonfrozen questions**: 250 unused IDs in the original reserved training split and 3,773 unallocated IDs outside that split and the old confirmation. Reserve new roles by a recorded deterministic hash order, check IDs and normalized prompts against every prior allocation, and freeze the role manifests **before** reading new outcomes. The 100 pilot, 100 validation, 50 prior training, and 100 prior diagnostic questions have already influenced design; reuse those 350 questions for development only. The counts below are maximum allocations, not permission to generate every response at once.

| New GSM8K role | Questions | Source and boundary |
|---|---:|---|
| Protocol bridge | 25 | From the 250 unused reserved-training IDs; pair protocol variants on the same questions. |
| Repeat and label-noise panel | 50 | From the same 250, disjoint from the bridge; collect up to eight independent draws per mode and compare the fixed 1/2/4/8-draw training conditions. |
| Acquisition pool | 1,200 | 175 remaining reserved-training IDs plus 1,025 of the 3,773 unallocated IDs; **one shared question pool** for all strategies and three acquisition seeds. |
| Tuning/calibration holdout | 200 | From the unallocated IDs; used for model/threshold selection, excluded from trace-training observations and purchase candidates. |
| New confirmation | Up to 2,000 | From the unallocated IDs, selected and sealed before generation; evaluate only a frozen candidate and endpoint. |

At the maximum allocation, 548 GSM8K training IDs remain unused. The new role manifests must contain exact IDs, source revision and checksums, selection seed, prompt-deduplication check, role, permitted generation settings, and any parent/template grouping. Keep gold in a separate scoring artifact; the first allocation and integrity check need only question IDs and prompts. Do not call the old confirmation runner to prepare these roles.

The unchanged parent reserve contains 548 rows. A separate child now earmarks
64 for the opportunity diagnostic, leaving 484 unclaimed by that child. Future
children must audit sibling conflicts; the parent manifest is not rewritten.
No response or reference has been collected for these 64 questions.

For MATH, pin a revision of the [split-preserving source](https://huggingface.co/datasets/EleutherAI/hendrycks_math) and a numeric-answer selection rule before inspecting model outcomes. Preserve its train/test boundary: the defaults are 600 acquisition, 100 validation, and 50 calibration questions from training, plus 500 original-test questions where the predefined numeric filter permits. Record eligible counts, parent/template relationships, and parser coverage before sampling. Do not select examples by model wins or pool cross-protocol scores. The separate manifest and pilot must confirm feasibility before generation.

Every acquisition strategy gets the same router architecture, initial examples, available actions, shared 1,200-question pool, and **revealed** token budget. Run **three acquisition seeds** on that common pool and compare 100k, 200k, and 400k acquired-token checkpoints. The preselected primary endpoint is **normalized area under the held-out utility learning curve (AULC) at `λ = 0.05`** over those checkpoints: integrate the three utility points by the trapezoid rule and divide by the 300k-token span. Freeze the strongest eligible comparator on tuning data before confirmation. A gain of **0.01 normalized utility** is the minimum meaningful primary effect. Report seed variation separately from uncertainty over evaluation questions; the shared pool does not make seeds independent datasets. Record the full cache-building expenditure separately from the tokens actually revealed to each strategy. Report inference generated tokens, prompt/prefill work, end-to-end latency, retries, and any external API cost separately.

The hard cloud envelopes are **$10 foundation / $15 signal / $30 main experiment / $30 replication and confirmation / $15 conditional extensions and buffer**, totaling $100. The $30 replication-and-confirmation allocation must cover both; the $15 reserve is not a second confirmation budget. Unused funds are not assumed to buy more compute. First measure a small cloud-versus-local throughput and price pilot, including input tokens and overhead, before any larger cloud spend. Local M2 Pro generation remains the default.

## Phases, gates, and deliverables

| Phase and target weeks | Deliverable and checklist | Gate before advancing | Cloud envelope |
|---|---|---|---:|
| **1. Foundation — week 1** | [x] Preserve checksums of the old development report and frozen confirmation. [x] Fix standalone always-thinking accounting, add a one-thinking-call test, and write the corrected report/curve/figure into `artifacts/router-dev/shared-base-v2/` without replacing v1. **First implementation checkpoint complete:** 118 tests and preservation checks passed. [x] Merge the scorers as `numeric-v5`; define prompt, caps, closure, EOS, confidence measurement, backend and runner as `qwen3-boxed-budget-v3`, with session/response source provenance and frozen-study identity checks. **Second checkpoint complete:** 195 tests; [protocol record](phase-1-protocol-reconciliation.md). [x] Freeze all disjoint GSM8K roles and enforce source/index/pool/exclusion checks. [x] Implement the paired 25-question bridge collector with matched seeds, fixed caps and endpoint-locked scoring; [checkpoint 3](phase-1-bridge.md), 212 offline tests. [x] Complete the local bridge and its engineering gates: 200/200 responses, all six gates passed. A bounded cloud pilot remains conditional if later compute requires it. | Corrected costs reproduce; original artifacts remain byte-identical; source and scorer provenance are unambiguous before new generation. | Up to $10 foundation |
| **2. Signal — weeks 2–3** | [x] Resolve intermediate-box scoring with opt-in v7, preserving bridge v5 results/source; [parser preflight](parser-preflight.md), 341 tests and 1,100 gold-free extracts checked. [x] Freeze a separate repeat-panel protocol pinning v7 and the unchanged allocation; [Phase 2 preparation](phase-2-repeat-panel.md), 363 tests, 800 jobs, deferred gold. [x] Generate eight independent draws per mode for the fixed 50-question panel. [x] Compare 1/2/4/8-draw labels, independent-draw reproducibility, confidence, question-only and solver-aware features with grouped uncertainty. **Complete: four of five progression gates fail; acquisition scaling stopped.** [Results](phase-2-repeat-results.md). [x] Separate CPU-only post-hoc diagnosis of oracle headroom, variance and policy decisions. | A useful rescue or mode-advantage signal reproduces on independent draws and unseen questions; otherwise narrow the claim or stop acquisition scaling. | Up to $15 signal |
| **2a. Measurement compatibility preflight** | [x] Freeze a separate gold-free parser policy and fixtures for the five presentation candidates. Keep frozen v7 and primary labels unchanged; check cached-output compatibility and adversarial negation/alternative/context/unit cases. Treat the unmarked terminal claim as a separate broader-policy decision. | No regressions or ambiguity acceptance under the defined policy; retain v7 if the candidate fails. A rejected candidate completes this bounded preflight. Any correctness sensitivity needs a separately pinned endpoint/sidecar and is exploratory. This does not restore the failed progression gate. | $0; no generation or new gold |
| **2b. Bounded feasibility after failed signal gate** | [x] Freeze a small CPU-only candidate grid for capacity and decision calibration around confidence. Keep the existing solver-only and combined learners as controls; test stronger regularization, training-fold-only question-feature compression/scaling and conservative thresholds. Use cached development labels with the same grouped draw-half boundaries; record all variants and failures. | Exploratory reused-data evidence only. Freeze exact grid and fit budget before fitting; no outcome-driven expansion. | $0; no new generation |
| **2c. Representation/objective controls** | [x] Compare question-only and question-plus-direct-draft MiniLM features at matched capacity. On identical representations, compare supervised gain, ordinary classification and a small contrastive action head with utility-aware supervision. [Review and proposed design](contrastive-router-review-2026-10-02.md). | A selected candidate must add value beyond confidence; distinguish new input information from training-objective gains. All preprocessing, pair construction and calibration stay within training folds/halves. No novelty or confirmation claim from reused data. | $0; cached data and encoder |
| **2d. Released-CLM probe** | [x] Synthetic engineering preflight. [x] Frozen cached diagnostic: 402 encodings, 450 Ridge/75 PCA fits, all screens fail; calibrated −.033262 vs confidence. Actual state encoding mean 1.427 s, peak 4.895 GiB, zero truncation. [x] Independent decision/head verification and additive conditional-interval seed correction. | Close the tested recipe; no source/report overwrite or adaptive prompt/fusion/finetuning expansion. No full-precision, contrastive-objective causality or live deployment claim. | Complete; local spend $0 |
| **2e. Broader signal diagnosis; superiority test conditional** | [x] Prospective power/budget review; 64-question/two-solver panel is diagnostic. [x] Freeze and verify question-only reserve child, disjointness/folds and synthetic analysis/leakage tests. [ ] Verify second-solver local assets/tokenizer/closure. [ ] Freeze solver/source/scorer/endpoint/analysis and global setup/retry budget before generation. [ ] Only subsequent positive signal justifies an eligible candidate and fresh superiority protocol. | Failed CLM/primary gates do not authorize scaling. SD=.16 sensitivity needs 2,010 questions for +.01 at 80% power; AULC power remains separate. Preserve all sealed roles. | Local only; no new cloud budget |
| **3. Harness — weeks 3–5** | [ ] Build a replay/acquisition ledger that hides unrevealed outcomes, charges actual tokens, records selection rules/seeds and randomized-action propensities where applicable, and resumes deterministically. [ ] Freeze the common 1,200-question pool, one final router architecture, the three acquisition seeds, baselines, ablations and normalized-AULC analysis. [ ] Verify the harness on synthetic and existing development traces before purchases. | Equal-budget policy comparisons are reproducible and cannot inspect hidden cache outcomes. | Local work; no new cloud envelope |
| **4. Main experiment — weeks 5–7** | [ ] Compare the 100k/200k/400k acquired-token curves on the one shared pool across three seeds against uniform/random, uncertainty, error-targeted, regret-per-cost, new-versus-repeat, cost-aware policy learning and active-router baselines. [ ] Ablate action choice, repeats, cost normalization and quality–length dependence. [ ] Report normalized AULC at `λ = 0.05`, accuracy/cost curves, seed variability and full cache expenditure. | Primary improvement survives strong baselines and component removal; negative results remain reportable. | Up to $30 main experiment |
| **5. Conditional Jev/RL extension — weeks 7–8** | [ ] Only if the signal and cost gates justify it, evaluate frozen Jev features against an otherwise identical no-Jev learner, or a lightweight contextual-bandit extension against supervised value learning. [ ] Charge API, exploration and routing overhead; do not treat Jev confidence as verified Qwen correctness. | Any added signal or sequential policy improves held-out utility after its full cost and supports a distinct mechanism. | Up to $15 extensions/buffer, conditional |
| **6. Locked replication and confirmation — weeks 9–10** | [ ] Test the predefined numeric MATH task with split-preserving manifests and a frozen scorer; compare faithful DART SC-Budget and ReASC before broad claims and measure live latency. [ ] Freeze the model, strongest tuned comparator, **already specified normalized AULC at `λ = 0.05`**, stopping rule, parser, source IDs and analysis plan; size confirmation conservatively for the 0.01 meaningful gain. [ ] Analyze up to 2,000 new GSM8K upstream-training questions and the separate MATH replication under their locked plans. [ ] Open the official GSM8K 500-test split only after final freeze, and report it separately if used. | A fresh result supports the predeclared claim; if power or cost requires more than the cap, disclose the limitation rather than borrow the old 3,100 or inspect test outcomes early. | Up to $30 **shared by replication and confirmation** |
| **7. Paper and release — weeks 11–12** | [ ] Write a manuscript with the primary endpoint, all baselines, negative results, uncertainty, acquisition and inference costs, and limits on task/model generalization. [ ] Package versioned protocols, checksums, manifests, scorer/runner code, selection ledgers, seeds, figures, reproduction commands and a deviation log without exposing sealed outcomes prematurely. | Independent readers can reproduce every table and distinguish planned, exploratory and confirmatory results. | No new cloud envelope |

The 8–12 weeks are a target contingent on the gates and measured M2 Pro/cloud throughput. A small or negative effect may end the method branch earlier. The old +0.008188 estimate does not justify this new sample size; even 2,000 questions are only near the previous normal-approximation 80%-power requirement for a true +0.01 effect, and the new variance may differ. The primary AULC endpoint is fixed here; changing it requires a documented new protocol, not a favorable development curve.

## Immediate first slice and next boundary

The accounting correction, semantic tests, versioned CPU report, and preservation checks are **complete as the first implementation checkpoint of the full authorized roadmap**. See the [checkpoint record](phase-1-evidence-repair.md). Protocol/scorer/EOS/runner integration is complete as [checkpoint 2](phase-1-protocol-reconciliation.md). Replay the earlier CPU result with pinned legacy source:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=artifacts/legacy/router-studies-6999eb5/src \
  .venv/bin/python -m reasoning_budget.router_dev \
  --source artifacts/probe/continuation-v1 \
  --output artifacts/router-dev/shared-base-v2
```

Protocol/scorer/EOS/runner integration, the 25-question bridge, parser preflight,
and the 50-question repeat panel are **complete**. Roles and inference settings
remain frozen. The repeat endpoint has 800 responses, 644,519 charged tokens,
8.39463 cumulative local hours and $0 cloud spend after the documented runtime
recovery. The original report, bridge and 2,319 protected files are unchanged.
Only the selected repeat training references were fetched after completion;
official test remains sealed and both confirmations remain unstarted.

**The Phase 2 gate failed.** The predeclared combined learner's four-draw average
utility difference is −0.016204 (90% CI −0.033276 to −0.000635); the independent-
half reproducibility interval crosses zero and full8 reverses. Only the
informative-question count passes. [Results and separate post-hoc diagnosis](phase-2-repeat-results.md)
record this without switching the gate learner or cost preference. Some repeated
question-level structure and hindsight headroom exist, but the combined learner
makes poorly targeted escalations. More repeats alone did not improve it.

The completed measurement boundary addressed compatibility: gold-free triage
found five presentation candidates among 27 rejected outputs, with 16 rejects
being multiple component answers on one question and five incomplete outputs.
Fixed-action point bounds cannot reverse the observed router comparison on
those candidates. The [separate compatibility preflight](phase-2-parser-compatibility.md)
passes for balanced whole-line bold final declarations: one changed extraction
in 1,900 outputs, no regressions. Broader context/units and unmarked terminal
claims remain outside the candidate. No real labels were changed.

The completed bounded slice is **CPU-only feasibility on existing development traces**:
test low-capacity, conservative corrections to confidence and question-feature
capacity/scaling controls. Then separate representation from objective: compare
question-plus-draft embeddings against question-only inputs, and small
contrastive heads against matched supervised heads. Our current MiniLM encoder
already has contrastive pretraining. Released CLM uses an encoder-locked 8B
backbone, so its optional probe needs matched-backbone controls and full runtime
accounting. See the [detailed October review](contrastive-router-review-2026-10-02.md).

The [2b–2c results](phase-2-router-feasibility-results.md) find no promoted
candidate after the fixed 1,035 Ridge and 600 neural fits. Retain the evidence
and stop this reused-panel search. The separately authorized local released-head
engineering preflight now passes, and the broader design/power review is complete.
The cached released-head test is now complete and negative at the fixed preference;
full-precision transfer and live deployment remain untested. Both bounded grids
are closed. Next is a separately frozen broader opportunity diagnostic, not
confirmation of a failed policy. A question-only child is now prepared and
verified; no new generation has begun. Its collector/scorer/resource protocol
and second-solver asset/closure preflight are the next implementation boundary.

Freeze the limited candidate grid and evaluation boundaries before fitting;
keep all outcomes exploratory because these questions have influenced design.
Even a positive development result needs a separate frozen fresh-question signal
protocol. Do not borrow sealed validation/confirmation labels or launch the
1,200-question pool on the failed gate. Acquisition, Jev/RL, MATH and confirmation
phases stay **pending**; a paper contribution and novelty are not established.

Additional direct novelty boundaries are [RouterDC](https://arxiv.org/abs/2409.19886),
[Cost-Spectrum Contrastive Routing](https://arxiv.org/abs/2508.12491), and
[SEMIROUTER](https://aclanthology.org/2026.eacl-long.228/). The candidate advancement
is a specific noise-aware allocation of new-question/action/repeat supervision
that improves equal-budget learning curves. A contrastive loss, a cost term or
sparse labels alone cannot supply that novelty. If contrastive heads add no
measured value, drop that component and retain the stronger supervised method.

The novelty boundary is narrow: direct-draft agreement and budgeted thinking are already in [DART](https://arxiv.org/abs/2606.23181), confidence stopping and evidence accumulation in [ReASC](https://aclanthology.org/2026.findings-acl.1085/), continuation selection in [Learning When to Sample](https://arxiv.org/abs/2603.08999), and optional information pricing in [Pandora's Router](https://arxiv.org/abs/2608.20316). RL-based thinking selection has close prior work in [Thinkless](https://arxiv.org/abs/2505.13379) and [RPO](https://aclanthology.org/2026.acl-long.816/). **Direct acquisition boundaries** include [Cost-Aware Near-Optimal Policy Learning](https://ojs.aaai.org/index.php/AAAI/article/view/35027), the [Targeting the Exceptions active-router implementation](https://github.com/wikit-ai/online-active-learning-llm-routers), and [Pure Exploration with Feedback Graphs](https://proceedings.mlr.press/v258/russo25a.html) for side observations across actions. The repository's [research proposal](router-research-proposal.md) and [September review](research-review-2026-09-24.md) discuss the overlapping routing and acquisition work; feedback graphs add a separate side-observation boundary. None of those cross-protocol scores is a direct comparator here. The proposed contribution depends on a specific, reproducible acquisition rule winning equal-budget tests and ablations, not on naming a router, using a confidence value, or applying generic RL.
