# Prospective broader signal study: design and power review

Design date: 2026-10-03, following the completed [2a–2c experiments](phase-2-router-feasibility-results.md).
This is a proposed design and reproducible budget/precision sensitivity review.
It does **not** allocate questions or authorize collection by itself. The user
requested continued research and local experiments; cloud spending is deferred,
and Docker remains running. Existing question roles and sealed data are preserved.

## Research question and decision

Keep the current question-plus-direct-draft decision: accept the draft or pay for
a fresh question-only thinking solve. Its target is solver-specific incremental
utility, not an inherent thinking/nonthinking category. Confidence remains the
mandatory comparator. The failed primary gates and negative compact pilot remain
unchanged; additional architecture search on the 50 questions is closed.

Investigate two distinct explanations prospectively:

1. **Representation transfer:** pretrained released CLM heads may expose useful
   draft-conditioned signal missing from MiniLM. The completed small-head pilot
   never tested these pretrained representations. A separately frozen local
   engineering probe precedes a matched-backbone cached diagnostic. Neither
   stage establishes novelty or fresh-question superiority.
2. **Solver-specific opportunity:** a second, smaller solver may produce a
   different rescue/harm pattern. A limited new-question panel could measure
   opportunity rates and confidence performance before training another router.
   Comparing two solvers does not establish generalization across model families.

These are separate hypotheses. Do not spend new generation tokens merely to
repeat a failed learner, conflate extra backbone capacity with contrastive loss,
or add RL before a supervised signal and complete inference cost are established.

## Proposed diagnostic panel, conditional on a new frozen protocol

Propose **64 new questions, two solvers, two independent draws per mode**:
512 responses / 256 paired outcomes, but only **64 question groups**. The first
solver is unchanged Qwen3-1.7B; the second candidate is Qwen3-0.6B, whose
[official model card](https://huggingface.co/Qwen/Qwen3-0.6B) supports both modes.
No new model generation or 0.6B download is launched by this planning report.

Questions would come from a separately versioned subrole of the **548 reserve**,
not acquisition/validation/confirmation. Preserve the parent allocation and
record a child manifest with exact source revision, deterministic selection,
parent hash, exclusions, normalized prompt deduplication and folds. No IDs are
selected now. Prepare using questions only. The collection/scoring protocol must
freeze both solver revisions/tokenizers, decoder settings, prompt, closure,
caps, independent seeds, endpoint, scorer and full accounting before launch.

Use this panel principally to estimate direct/thinking correctness, rescue/harm
rates, token/latency costs and confidence calibration. Prespecify question-group
intervals and independent draw-half diagnostics. Two draws do not justify a
high-dimensional learner or strong claims about repeated-label reliability.
Any task-trained candidate must be selected using acquired training-half labels
and grouped inner folds. Freeze a small eligible policy set only after the
separate representation probe; no post-hoc expansion on the new outer scores.

A second task is still needed for broader empirical claims. Numeric MATH requires
its own split-preserving source, eligibility rule and parser coverage study.
If eligibility uses a reference answer, make that reference access explicit in a
separate protocol; do not describe it as question-only preparation. Do not open
original-test references to design the filter or silently pool task endpoints.

## Precision and budget calculation

`scripts/signal_study_power.py` reads only the completed cached reports, frozen
protocol metadata and role counts. It fits no candidate and never calls scoring,
generation or allocation APIs. Its plan freezes source hashes, hypothetical
question-level SDs [.05, .10, .16, .25, .32], effects [.01, .02, .03], sample sizes
[64, 128, 200, 548, 2000], two-sided α=.05 and 80%/90% normal-approximation power.
The calculation uses both normal tails and solves the minimum integer sample
size. This is sensitivity under known SD, not exact small-sample power.

The current selected CPU/neural means are negative. Their question-level SDs
describe fixed fitted policies averaged across two halves; they are **not**
prospective single-draw variance estimates. Repeats do not multiply independent
sample size. This planning calculation does not size the roadmap's learning-curve
AULC endpoint, whose training/acquisition-seed uncertainty needs another design.

At hypothetical SD=.16, a +.01 paired utility effect needs approximately **2,010
independent questions** for 80% power. A 64-question study instead detects effects
around **.056** at that power. Therefore the proposed panel is diagnostic, not a
well-powered confirmation of the .01 minimum meaningful gain. Narrow a future
paper's claims if independent confirmation is unaffordable.

The frozen generation caps reserve **3,074 tokens per pair**, including two forced
closure tokens: two 512-token answers plus 2,048 reasoning tokens plus closure.
The proposed response-only maximum is **786,944 tokens** across both solvers.
Setup, retries and router encoding need separately frozen additional ceilings.
The current measured 1.7B pair profile is about 1,611 tokens and 65.82 seconds;
applying it to the proposed 128-pair **1.7B slice only** gives about 206k tokens
and 2.34 hours. The second solver and any MATH runtime remain unmeasured.

## Local released-CLM boundary and possible advancement

The [released CLM heads](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B) require
Qwen3-8B last-token embeddings. Their pretrained weights distinguish this
hypothesis from fitting the earlier 120-parameter MiniLM heads. The
[MLX 4-bit conversion](https://huggingface.co/mlx-community/Qwen3-8B-4bit) provides
a feasible local candidate, but quantization and a different pooling runtime are
an adaptation, not a faithful full-precision reproduction. See the separately
frozen [local preflight](clm-local-preflight.md).

If engineering passes, freeze a **single cached diagnostic** before reading its
scores: fixed question/draft state text; fixed accept/fresh-thinking action text;
released heads without finetuning; scalar calibration on training halves only;
confidence and a low-capacity supervised head on the **same 8B embeddings**.
Use the existing five question folds and independent halves; retain all results
as reused-development evidence. Measure encoding, truncation, transfer and head
latency; live co-resident solver/router latency remains a separate requirement.
Relative CLM action probabilities are not calibrated solver-correctness values.

Potential advancement remains a precise acquisition mechanism that chooses
new-question versus repeat observations from uncertainty in **incremental solver
utility**, wins equal-token-budget curves, and survives component ablations and
independent settings. The [prior-art review](contrastive-router-review-2026-10-02.md)
rules out novelty from contrastive routing, sparse labels, a cost penalty or RL
alone. Until these tests pass, the publishable contribution is unestablished.

## Execution order

1. Complete this power/budget review and the synthetic local CLM preflight.
2. If engineering is feasible, freeze and run the one matched-backbone cached
   diagnostic; keep the earlier negative experiments closed.
3. Choose the best-supported fresh hypothesis, then implement and freeze the
   reserve-subrole diagnostic protocol. Do not launch the acquisition pool.
4. Only positive fresh evidence and affordable independent precision justify
   the acquisition experiment, optional RL/Jev, and final confirmation.
