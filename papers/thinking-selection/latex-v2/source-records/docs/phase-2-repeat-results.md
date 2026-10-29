# Phase 2 repeat panel: completed diagnostic, progression stopped

The fixed repeat panel completed **800/800 responses** on 50 allocated upstream-training questions, with eight independent draws in each of direct and thinking mode. The frozen primary analysis failed **four of five** progression gates, so adaptive acquisition does **not** scale on this evidence. This is one model, one task, and 50 question groups; it is a diagnostic result, not independent confirmation or a new acquisition contribution.

The study uses the allocation and source frozen at `272403f` and protocol `8b01db2cbb7b8d1777c40aa0a873f4626e4c6b2a04e9135a377a085a76f3c812`. The supervisor recorded completed analysis and verification at **2026-10-02 05:20:08 UTC**. Its durable ledger records **644,519 charged tokens**, **806 attempts** (six failed), **three setup sessions**, and **8.39463 cumulative hours** including attempts and setup. Cumulative ledger time is distinct from calendar wall time. Cloud spend was **$0**; the official test remains sealed. A fresh CPU reconstruction using the unchanged original analysis reproduced its entire statistics payload exactly (SHA-256 `3eeb01293d16408d0be1db8af6d200d455930383fbd16ca515f1401cae47ca40`). The independent endpoint verifier also checked accounting and policy arithmetic. The old bridge and all 2,319 protected originals remain unchanged; [completion review proof](../artifacts/research/data-efficiency-v1/repeat-panel-v1/recovery-v1/completion-review-verification.json) records the checks.

The fixed utility is correctness minus `0.05 × generated tokens / 1,000`. Escalation happens **after** a direct draft: choosing thinking charges both the sunk direct cost and the additional thinking call. The selected comparator in each outer fold came from accept, escalate, or a confidence threshold chosen on inner training folds. Whole-question 90% bootstrap intervals use 2,000 draws and condition on the fixed out-of-fold fits; they do not reflect refitting uncertainty or adjust for the seven conditions.

| Predeclared progression gate | Observed statistic | Result |
|---|---:|:---:|
| Four-draw independent-half reproducibility: MSE improvement and lower interval bound > 0 | `+0.01158` utility²; 90% CI `[-0.01744, +0.04848]` | Fail |
| Four-draw combined gain positive in both directions | A→B `−0.02679`; B→A `−0.00562` | Fail |
| Four-draw mean gain ≥ `+0.01` with lower interval bound > 0 | `−0.01620`; 90% CI `[-0.03328, −0.00063]` | Fail |
| Full-eight combined gain does not reverse | `−0.05163`; 90% CI `[-0.07286, −0.03204]` | Fail |
| At least ten informative distinct questions | `14/50` | Pass |

All seven frozen combined-minus-inner-selected-baseline comparisons are below. A and B are disjoint draw halves; outer evaluation questions were held out from fitting. `k8_full` has held-out **questions** but no independent same-question eight-draw replica.

| Training draws | Evaluation | Utility difference | 90% grouped CI |
|---|---|---:|---:|
| 1 | A→B | −0.02016 | [−0.03665, −0.00535] |
| 1 | B→A | +0.00641 | [−0.01648, +0.02445] |
| 2 | A→B | −0.02812 | [−0.04975, −0.00857] |
| 2 | B→A | +0.02257 | [−0.00552, +0.05804] |
| 4 | A→B | −0.02679 | [−0.04973, −0.00714] |
| 4 | B→A | −0.00562 | [−0.02724, +0.01357] |
| 8 | Full, held-out questions | −0.05163 | [−0.07286, −0.03204] |

Across the 400 paired draws, direct was correct on **358/400 (89.5%)**, using **221.14 generated tokens** and **9.47 cached generation seconds** per call. Standalone thinking was correct on **378/400 (94.5%)**, using **1,389.83 tokens** and **56.35 seconds** per call. Paired states were 348 both correct, 30 direct-wrong/thinking-correct rescues, 10 harms, and 12 both wrong. Standalone thinking cost differs from *escalate after direct*, which pays for both calls.

| Full-eight held-out-question policy | Accuracy | Tokens/question-draw | Utility at λ=.05 |
|---|---:|---:|---:|
| Always accept direct | 89.50% | 221.14 | 0.88394 |
| Always escalate after direct | 94.50% | 1,610.98 | 0.86445 |
| Tuned confidence | 92.50% | 466.88 | 0.90166 |
| Question-only ridge | 88.25% | 815.82 | 0.84171 |
| Solver-only ridge | 91.50% | 555.50 | 0.88722 |
| Combined ridge, predeclared learner | 89.00% | 799.49 | 0.85003 |
| Inner-selected baseline | 92.50% | 466.88 | 0.90166 |

The [`primary-utility-deltas.png`](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/figures/primary-utility-deltas.png) figure displays every frozen comparison and its grouped interval. The selected full-eight baseline happened to be confidence in all five folds; that choice was made within training data, not from these held-out utility values.

## Separate post-hoc/development explanation

The [diagnosis report](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/report.json) (digest `4278a314ec91f5a5f088e0598d3690657f1948ca8d11bfc6bc2d6e8a49d9aedf`) and [immutable analysis plan](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/analysis-plan.json) (digest `ae71e7276d94dd0d27d7d60fdb3874d54ae8f52f73f43597d8547397500a5c87`) use cached scores only. The diagnostic script was frozen at `51530f2`; seven diagnostic tests passed in addition to the preceding 386-test suite. These analyses explain the failure; they cannot change the primary result or its gates.

A **nondeployable hindsight oracle** that sees both outcomes before deciding to escalate reaches utility **0.95290**, a mean gain of **+0.06896** over accepting direct (90% question-bootstrap CI `[+0.03216, +0.11275]`) and escalates 30/400 pairs. Its escalation cost includes both the already-paid direct draft and the thinking call. It is an upper bound on this two-action decision, not a learnable policy estimate.

Using four A draws to choose an action for each **same question** and evaluating on B gives gain **+0.04413** (CI `[+0.00563, +0.08845]`); B→A gives **+0.01572** (CI `[−0.02019, +0.05908]`). Those evaluations omit the cost of acquiring selection labels: A used **322,882 tokens** and **13,306.81 generation seconds**, B **321,508 tokens** and **13,021.93 seconds**, each for 200 paired draws/400 responses. Their positive conditional evaluation gains are therefore **not net acquisition utility**, and same-question transfer says nothing about routing unseen questions.

The signed between-question gain-variance estimate is **0.03233** (post-hoc grouped 90% CI `[0.00541, 0.06530]`), formed from question-mean sample variance **0.04066** minus mean within-question sample variance **0.06668/8**. It is deliberately not clipped at zero. Its interpretation assumes approximately IID/exchangeable independent draws within each question under the fixed decoder; the interval resamples 50 questions and is conditional on these cached labels.

The learner had **387 question features plus four draft features** but only **40 unique outer-training questions** (30 in an inner-training fold). At eight draws, 320 rows reuse those same 40 groups; they are not 320 independent questions. On full-eight held-out questions, combined ridge escalated 174/400 draws: **5** with positive realized gain, **169** nonpositive, including **7** direct-correct/thinking-wrong harms, while missing **25** positive opportunities. Confidence escalated 58/400: **16** positive, **42** nonpositive, including **4** harms, and missed **14** positives. Harm counts overlap the nonpositive category. See the separately labeled [`posthoc-escalation-counts.png`](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/figures/posthoc-escalation-counts.png).

The conservative next **CPU-only learner feasibility study** is a baseline-anchored, low-capacity residual gate with nested question-grouped validation and explicit action/acquisition cost, plus question-feature capacity/scaling controls. It is a candidate to test, not established novelty, a gate rescue, or permission to spend on the 1,200-question acquisition pool. The measurement preflight below comes first. Cached generation seconds omit live router feature, prefill, selection, and deployment overhead, so no live latency improvement is claimed. Replication on another task and fresh held-out evidence would be needed for broader claims.

## Gold-free parser triage and bounded sensitivity

The fixed v7 scorer rejected **11/400 direct** responses (eight conflicting, two incomplete, one invalid-number) and **16/400 thinking** responses (11 conflicting, three incomplete, two invalid-number). A separate [syntax audit](../artifacts/research/data-efficiency-v1/repeat-parser-audit-v1/report.json), digest `a09af2cd37d9bcc683060b84d2df320be7c3465653f1ba3edc1280367ea59061`, reviewed only these answer texts and the existing extraction decisions. It opened no references, changed no correctness label and assessed no mathematical correctness. This is agent review; the human audit remains waived.

| Gold-free category | Calls | Implication |
|---|---:|---|
| Incomplete generation at the answer limit | 5 | Keep rejection; do not salvage an intermediate answer. |
| Two distinct component quantities in the final answer | 16, all on one question | No unique scalar answer. Keep rejection; picking the last box would hide ambiguity. |
| Explicit terminal claim with a presentation limitation | 5 | Review separately: one dollars/cents equivalence, one contextual digit quantity, two written quantity descriptors, one emphasis spanning the final label and boxed value. |
| Terminal claim without an explicit final marker, after intermediate boxes | 1 | Accepting it requires a broader claim-boundary policy, not a repair within v7's explicit-marker rule. |

An identifiable terminal number is not proof of a correct solution. The five presentation candidates motivate a **separately versioned gold-free compatibility preflight** before new learner fitting: define claim/format rules without using gold, test valid and adversarial alternative/negation/unit/context fixtures, and require compatibility on historical and new cached outputs. Do not edit frozen v7 or relabel the completed primary result. Any later correctness sensitivity requires its own pinned endpoint and sidecar; it remains reused-data sensitivity.

The [fixed-policy bounds](../artifacts/research/data-efficiency-v1/repeat-parser-audit-v1/fixed-policy-bounds.json), digest `2f1dde4fe924996ff8666a37452d0fe30c9dba7c240c0bf2e669212a499b4a10`, ask what happens if any subset of the five currently rejected presentation candidates becomes correct, **while all existing actions and costs remain fixed**. The four-draw average utility difference remains exactly **−0.016204**, because both policies choose the same final mode on each affected draw. Full8 remains between **−0.054130 and −0.049130**. Including the sixth, unmarked-terminal candidate can only worsen the four-draw difference; the full8 upper bound is still −0.049130. Exhaustive binary enumeration verifies these point bounds. They read no gold and are not a new scoring result, confidence interval, or guarantee for refitted policies. They do show that these flagged presentation cases alone cannot reverse the observed fixed-policy comparison.

Reproduce the isolated diagnosis and figures from cached reports:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/diagnose_repeat_signal.py
.venv/bin/python scripts/plot_repeat_results.py
```

These commands fetch no reference answers or solver outputs. Diagnosis refuses incomplete collection and changed plan/input/source identities; its plan and report are immutable under a directory lock. The plotting command writes only the separate derived figures. The primary report/scorer and parser audit stay unchanged.

Sources: frozen [primary report](../artifacts/research/data-efficiency-v1/repeat-panel-v1/report.json), [diagnostic report](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/report.json), and [diagnostic plan](../artifacts/research/data-efficiency-v1/repeat-diagnosis-v1/analysis-plan.json). The plotting recipe is [`scripts/plot_repeat_results.py`](../scripts/plot_repeat_results.py); figure hashes are recorded alongside its outputs.
