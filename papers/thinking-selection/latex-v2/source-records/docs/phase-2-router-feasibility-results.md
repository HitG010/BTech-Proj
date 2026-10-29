# Phase 2b–2c results: capacity and contrastive controls

Completed 2026-10-03 from implementation/protocol checkpoint **`1886bd4`**.
Both bounded exploratory studies fail their promotion screens. Confidence remains
the reference policy; these results provide no basis for CLM-8B deployment,
acquisition scaling or a superiority/novelty claim.

The [parser compatibility preflight](phase-2-parser-compatibility.md) completed
first: 56 syntax fixtures and 1,900 cached responses, with one narrow formatting
repair and no accepted-answer regressions. The candidate remains separate from
frozen v7; **all router experiments use unchanged cached v7 labels**.

## Experimental boundary

The [CPU protocol](phase-2-cpu-feasibility-protocol.md) and
[representation protocol](phase-2-contrastive-protocol.md) were checkpointed
before any real fitting. Phase 2b completed exactly the fixed 1,035 Ridge and
75 PCA fit grid. Phase 2c completed 600 small-head fits and 150 PCA transforms,
with 400 direct drafts embedded once using the existing pinned local MiniLM.

The 50 questions, eight paired draws, five outer question folds, four inner
question folds, generation protocol, v7 labels and λ=.05 are unchanged.
A4→B4 and B4→A4 use independent draw halves and question-held-out evaluation.
Each fold selects settings/families only from acquired training-half labels.
Full8 remains secondary, with no independent same-question eight-draw replica.

All data have influenced research design, so these are development results even
with grouped nested evaluation. Intervals resample 50 question groups with fixed
fitted policies; they omit refitting uncertainty, multiplicity and researcher
selection effects. Neither study changes the failed primary Phase 2 report.

## Main four-draw comparison

These values average the two independent-half directions. Their confidence
policy differs from the full8-trained confidence policy in the earlier report.
Do not mix their costs or endpoints.

| Policy | Average accuracy | Tokens/question | Average utility | Difference versus confidence | 90% fixed-fit interval |
|---|---:|---:|---:|---:|---|
| Confidence | **92.75%** | 628.47 | **0.896076** | — | — |
| CPU family selected within training folds | 90.75% | 514.22 | 0.881789 | **−0.014287** | [−0.025680, −0.004425] |
| Neural family selected within training folds | 89.25% | 604.82 | 0.862259 | **−0.033817** | [−0.052515, −0.017266] |

Both selected policies fail all three exploratory screen components: average
gain ≥.01, positive means in both directions, and positive averaged means after
deleting each question in turn. These screens only prioritize a fresh test and
cannot restore the original progression gate.

## Capacity and calibration controls

| New family | A4→B4 difference | B4→A4 difference | Average difference | Average 90% interval |
|---|---:|---:|---:|---|
| Strongly regularized draft-feature Ridge | −0.035707 | −0.016369 | −0.026038 | [−0.043751, −0.009692] |
| PCA8 question features + lexical/draft blocks | −0.035707 | −0.012907 | −0.024307 | [−0.042723, −0.008291] |
| Confidence with conservative draft-model corrections | −0.027005 | −0.002362 | −0.014684 | [−0.026135, −0.004588] |
| Training-selected new family | −0.027005 | −0.001569 | −0.014287 | [−0.025680, −0.004425] |

All 21 configurations and their outer actions are retained in the artifact;
none was added after seeing an outer score. Each historical accept/escalate/
confidence/solver-only/combined action reproduced the primary report exactly.

In A4→B4, both standalone new Ridge families select zero escalations. Conservative
correction captures two positive-gain cases in four escalations, while confidence
captures 12 in 35. The B4→A4 comparison also favors confidence on utility.
This pattern suggests collapse toward accepting drafts in one direction and
unstable transfer of rare rescue supervision. It does not prove that stronger
regularization or all compressed representations are inherently unsuitable.

For secondary full8, the selected correction is identical to confidence:
92.5% accuracy, 466.8825 tokens, utility .901655875. This secondary equality does
not counter the failed independent-half screen.

## Representation and objective controls

All objectives use the same 120-parameter normalized state/action head, fixed
initialization, optimizer and 100-epoch schedule. Question-plus-draft uses a
normalized mean of separate frozen question and draft vectors. This is one
specific fusion strategy, rather than an exhaustive CLM or draft-conditioning
test. Ordinary binary CE, regret-weighted forward CE and gain MSE provide controls
for the bidirectional multi-positive contrastive term.

| Representation / objective | Average difference versus confidence | Average 90% interval |
|---|---:|---|
| Question / gain MSE | −0.036638 | [−0.054962, −0.019883] |
| Question / regret-weighted forward CE | −0.020187 | [−0.040105, −0.003085] |
| Question / bidirectional contrastive | −0.025404 | [−0.046890, −0.006620] |
| Question / ordinary binary CE | −0.014283 | [−0.034851, +0.004813] |
| Question + draft / gain MSE | −0.038739 | [−0.056249, −0.022177] |
| Question + draft / regret-weighted forward CE | −0.013584 | [−0.031964, +0.001479] |
| Question + draft / bidirectional contrastive | −0.027085 | [−0.047376, −0.009062] |
| Question + draft / ordinary binary CE | −0.013854 | [−0.034496, +0.005116] |

All eight point differences are negative. Adding draft vectors improves the
forward regret-weighted head's average relative to its question-only counterpart,
but neither beats confidence. That component difference was not separately
confirmed; do not treat it as an established effect.

The question-plus-draft forward head has +.006463 utility in B4→A4 but −.033632
in A4→B4. Its positive single direction is not reproducible advantage. Adding
the reverse contrastive term does not improve the point comparison to forward
regret-weighted CE for either representation.

For secondary full8, nested selection achieves 88.75% at 550.65 tokens, versus
confidence's 92.5% at 466.88. The chosen neural policy captures zero of the 30
positive-gain paired opportunities and harms three correct drafts. These are
diagnostic policy counts, not an estimate that every neural architecture fails.

## Runtime and verification

Observed fit/prediction time for Phase 2b is 3.48 seconds; Phase 2c training and
evaluation is 17.19 seconds. These measurements are local execution observations,
not guaranteed runtimes. Draft encoder loading took .203 seconds and 400-draft
encoding took 4.12 seconds; mean warm draft encoding was 10.31 ms, p95 13.46 ms.
Question encoding and complete live routing latency were not measured.

**111/400 drafts (27.75%) exceeded the 256-token encoder allowance.** The frozen
recipe retained the tail. Input truncation, eight-component compression, one
optimization seed and limited unique questions constrain interpretation. No
adaptive length/seed/architecture rerun was made after observing the scores.

A separate fresh-process review recalculated **24,000 CPU and 9,600 neural policy
decisions** from cached paired outcomes. It checked per-question and aggregate
accuracy/cost/utility/counts, bootstrap differences, inner/outer partitions and
training-only family selection. It fitted no model and opened no reference.
The existing endpoint/preservation verifier again confirmed all **2,319 protected
originals**, the failed primary report and completed collection unchanged.

Validation: the full 500-test offline suite passed after the experiment changes;
two additional independent accounting tests passed. Ruff and whitespace checks
passed. Docker remained running. Cloud/model API spend is $0; no new solver
responses, new references or sealed-label access occurred.

## Artifact identities and reproduction

All paths below are under `artifacts/research/data-efficiency-v1/` and ignored by
Git. Source and protocol checkpoints are committed; preserve completed artifacts.

| Artifact | Payload SHA-256 |
|---|---|
| `repeat-cpu-feasibility-v1/analysis-plan.json` | `f46323f09157babec3aa6bb5d7d86053fa2848e18e92201929626fa2759e346c` |
| `repeat-cpu-feasibility-v1/report.json` | `42e95eaa38bce5719ebcf700e6c0bf4527617ec7b8704cdd7a48034024502e01` |
| `repeat-contrastive-pilot-v1/analysis-plan.json` | `bb3c6a76e2afdf0fea9d6306c5b3c2c2e751b9d21cb4501c9706a994610f9a2a` |
| `repeat-contrastive-pilot-v1/report.json` | `e8ddebe38f211359eda4a60742e5cd388ea6a823981b60f7461293b21004a5eb` |
| `router-feasibility-review-v1/verification.json` | `b55e921ef69c4e4059812e873ecb3b8e9a44e27d2d810d48f66a989e6c6a97e3` |

The cached CPU command returns its completed report without refitting. The neural
executor deliberately refuses existing feature/results files. Do not restart
either study to reproduce a table; use the cached report and independent review.
The review script also uses exclusive creation; a new verification run needs a
separately named directory or a read-only calculation. Its chart recipe is
`scripts/review_router_feasibility.py`; exports are
`router-feasibility-review-v1/utility-comparison.png` and `.pdf`.

## Decision and next research boundary

Close the bounded 2a–2c milestone. Keep confidence as the strongest reference
policy and retain every negative outcome. Neither candidate screen supplies
evidence to launch a fresh superiority test, acquisition scaling, released CLM
or RL. A publication contribution is still unestablished.

The next useful research work is a **prospective design and power review for a
broader signal study**, rather than another unbounded search on these 50 questions.
That design should distinguish a different hypothesis/task distribution from
extra architecture capacity; calculate affordable question-level precision;
include confidence and matched objective controls; and preserve the old reserved
roles. Any new generation requires its own frozen question-role, endpoint and
analysis protocol. If pursuing a methodological gain, first identify concrete
new signal evidence. If pursuing an empirical negative result, scope its claims
and collect independent second-setting evidence under a separate protocol.
