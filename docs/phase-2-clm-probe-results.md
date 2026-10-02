# Phase 2d results: cached released CLM and matched encoder control

Completed 2026-10-03 on `codex/research-data-efficiency`. Implementation/tests
checkpoint **`5d40fa8`**, verified launcher/protocol checkpoint **`ce1c7e6`**,
and plan `270718aa…22a88c` preceded all real encoding and fitting. The one local
worker completed **402/402 inputs**, zero retries; all **450 Ridge / 75 PCA fits**
completed. Docker stayed running. No new solver responses or references.

**None of the four diagnostic policies passes the exploratory screen.** At the
preselected λ=.05, confidence remains the stronger reference. Close this bounded
recipe; it supplies no evidence for CLM deployment, acquisition scaling or RL.

## Scope and main independent-half comparison

The [frozen protocol](phase-2-clm-probe-protocol.md) uses actual released heads
with pinned 4-bit MLX Qwen3-8B last-token embeddings on all 400 existing direct
drafts. The encoder receives question/draft text and fixed decision metadata,
never thinking text, correctness labels, future thinking cost or confidence.
Both learned families use the same embeddings, training-only preprocessing,
alphas/thresholds and continuous incremental-gain target. The supervised raw
control uses PCA8; CLM calibration uses the released scalar margin. Neither
family adds auxiliary draft statistics or finetunes the released heads.

The 50 questions, five outer folds, independent A4/B4 halves and cached v7
outcomes are unchanged. Results average both directions at question level.
These are reused-development results. Fixed-fit 90% intervals omit refitting,
researcher selection and multiplicity; no independent confirmation is claimed.

| Policy | Average accuracy | Tokens/question | Utility | Difference vs confidence | 90% averaged interval |
|---|---:|---:|---:|---:|---|
| Confidence | **92.75%** | 628.47 | **.896076** | — | — |
| Released CLM, zero-shot | 94.75% | 1,550.53 | .869973 | **−.026103** | [−.058826, +.016513] |
| Released CLM, calibrated | 88.50% | 443.71 | .862815 | **−.033262** | [−.053818, −.015171] |
| Matched raw encoder, PCA8/Ridge | 89.00% | 330.81 | .873460 | **−.022617** | [−.043758, −.004464] |
| Training-selected family | 88.75% | 406.34 | .867183 | **−.028893** | [−.049575, −.010922] |

Calibrated CLM minus the matched raw control is **−.010645**, interval
**[−.018190, −.004292]**, on the same averaged endpoint. The raw control is also
below confidence. This does not isolate a contrastive-loss effect: pretrained
head capacity, prior training and feature dimensions differ despite a matched
backbone. Full-precision equivalence and pretraining disjointness are unresolved.

| Policy | A4→B4 utility difference | B4→A4 utility difference |
|---|---:|---:|
| Zero-shot CLM | −.016470 | −.035737 |
| Calibrated CLM | −.035706 | −.030817 |
| Raw encoder control | −.035706 | −.009527 |
| Training-selected family | −.035706 | −.022080 |

Every point comparison is negative in both directions. All policies fail the
minimum averaged gain ≥.01, positive-direction and leave-one-question-out
screen components. The zero-shot interval crosses zero: it remains imprecise,
not evidence of a proven population disadvantage. The failed original Phase 2
gates are unchanged; this diagnostic cannot replace them.

## Behavior and secondary full8

Zero-shot CLM recommends thinking for **380/400 drafts (95%)**. It captures all
30 positive-gain paired opportunities, but also 350 nonpositive decisions and
nine harmful escalations. Its higher accuracy is purchased with near-always-
thinking cost. The fixed cost preference does not reward that tradeoff.

In A4→B4, both calibrated families select zero escalations: training favors
accepting drafts while the other half has more rescue opportunities. In B4→A4,
calibrated CLM escalates 61 times, captures zero positive gains and harms four
drafts; the raw control escalates 31 times, captures zero and harms two.
Confidence captures 12/5 positive gains in the respective directions, with
35/65 escalations. This is consistent with unstable transfer of rare rescue
supervision, but does not identify a causal explanation or reject every CLM
adaptation. Scalar utility calibration and a small PCA control are limited tests.

The eight-draw endpoint is secondary and lacks an independent same-question
eight-draw replica. Do not mix its confidence costs with the four-draw table.

| Secondary full8 policy | Accuracy | Tokens/question | Escalations | Positive-gain escalations |
|---|---:|---:|---:|---:|
| Confidence | **92.50%** | **466.88** | 58 | 16 |
| Zero-shot CLM | 94.75% | 1,550.53 | 380 | 30 |
| Calibrated CLM | 89.50% | 221.14 | 0 | 0 |
| Raw control / nested selected | 89.50% | 267.24 | 11 | 1 |

The zero-shot full8 token cost is **3.32× confidence**. Its point behavior suggests
an accuracy/cost tradeoff, not a justified switch of λ or promotion endpoint after
observing results. No adaptive prompt, alpha, fusion or finetuning rerun is made.

## Real input and resource measurements

The encoder worker wall time is **575.67 seconds**. Model loading took 2.149 s;
the 400 states average **345.65 input tokens**, maximum 659, with **zero truncation**
at the frozen 2,047-token cap. Mean state tokenization/forward/host-copy time is
**1.427 s**, p95 **2.244 s**. Peak MLX allocation is **4.895 GiB**; separately
polled worker RSS is .972 GiB and excludes some GPU/unified-memory allocation.
Both observation gates pass; the allocator guideline is not a hard memory cap.

CPU released-head loading after library import took .0781 s; cached action
projection .0140 s; mean warm state projection/two-action score **.621 ms**.
The fixed preprocessing/fit/evaluation grid took **2.70 s**, excluding encoding
and released-head setup. Generation expenditure remains the old frozen ledger.

Secondary full8 zero-shot sums 63.389 historical solver seconds with measured
router work to a **64.818 s proxy**, versus confidence's 19.200 historical solver
seconds. Calibrated CLM's analogous proxy is 10.903 s at lower accuracy. These
are sums from different runs and omit co-resident scheduling, cold setup and a
complete live implementation; they are not causal speed comparisons or proof
of deployment advantage. Generated-token utility does not charge encoder work.

## Reporting deviation and additive correction

The fresh-process review found that the imported CPU summary helper uses its
own **bootstrap seed 20261002** for per-condition policy intervals, rather than
this protocol's **20261006**. All point metrics, actions, fits, model selection,
screens and **primary averaged intervals** are unaffected; those averaged and
CLM-minus-control intervals already use 20261006.

Preserve the original source and report. The separate
`repeat-clm-review-v1/conditional-intervals.protocol-seed.json` verifies all **75**
original per-condition intervals against their actual helper seed and provides
their recomputed protocol-seed versions from cached decisions. Use that sidecar
when quoting conditional intervals; it replaces no primary artifact and invokes
no fitting, encoder or scorer. The deviation and its correction are explicit.

## Verification and artifacts

The independent functional head implementation reproduces all recorded logits
**exactly**. Fresh-process accounting checks **20,000 decisions**, all grouped
partitions, inner-only setting/family selection, accuracy/cost/utility/counts,
primary averaged intervals, screens and inclusion of measured timing overhead.
The original verifier confirms all **2,319 protected originals** unchanged.

Validation: full **533-test** offline suite passed before launch; four separate
reviewer tests pass, including the interval-deviation regression. Ruff and
whitespace checks pass. The native worker and analysis have exited. No official
test/reference access, allocation changes, new generation, cloud/API spend or
Docker interruption. Both confirmations remain unstarted.

All artifact paths are under `artifacts/research/data-efficiency-v1/`:

| Artifact | Payload SHA-256 |
|---|---|
| `repeat-clm-probe-v1/analysis-plan.json` | `270718aaaf58daed8c39f3b0e4decab428ea8b77082a7f80320a3702f022a88c` |
| `repeat-clm-probe-v1/report.json` | `5c05f6552c1c33ba7f5f426be1a23d4b053688fec008380792aef30ae907f117` |
| `repeat-clm-review-v1/verification.json` | `8d7392b5e3d29f38bfc619b6f640f9641addb030531dc66b56ce64556b88524e` |
| `repeat-clm-review-v1/conditional-intervals.protocol-seed.json` | `ea1c92264d370c668062ca54ba45101855db2a40b96f863b76e0d446b9faaaf6` |

Plots: `repeat-clm-review-v1/utility-comparison.png` and `.pdf`, generated by
`scripts/review_repeat_clm_probe.py` and visually inspected. Completed preparation,
invocation, encoding, fitting and review use exclusive writes; do not restart
or overwrite them. Preserve all existing sources, protocols, assets and outcomes.

## Research decision

Close this fixed CLM recipe. Retain confidence and all negative findings; adding
released contrastive heads currently provides no supported advancement at λ=.05.
A publication contribution and novelty remain unestablished.

The next useful hypothesis is the separately proposed **broader opportunity-rate
diagnostic**, measuring a second solver's direct/thinking rescue/harm structure
before another learner. The [design/power review](broader-signal-design.md)
proposes 64 reserve-subrole questions and two solvers, explicitly diagnostic
and currently unallocated/unstarted. It needs a frozen child role, solver/source,
scorer, endpoint and full local budget before generation. It is not an approved
fresh superiority test for any failed candidate. Acquisition, Jev/RL, MATH and
confirmation remain stopped pending new signal evidence and adequate precision.
