# G1: bounded synthetic acquisition study

Date: 2026-10-09. Branch: `codex/confidence-acquisition-plan`.
Status: preparation. Execution is locked until the source and protocol are frozen.

## 1. Purpose

Test whether the proposed acquisition rule has a useful mechanism in controlled data.
This is an engineering and feasibility study. It cannot establish a new algorithm or
an advantage on real model responses.

The [focused plan](novelty-plan-2026-10-08.md) defines the research question.
The G0 review must record overlap with existing work. A simulation may test an
explicit adaptation even if no new method claim survives that review.

## 2. Data boundary

Generate all data from the frozen synthetic distributions and seeds.
Read no existing question, response, score, reference, model, or allocation artifact.
Use no network request in the executor. Use CPU only.

Each training question has one fixed direct state and two possible thinking draws.
All direct states are observed and charged before acquisition starts.
The acquisition process can read thinking correctness and length only after purchase.
The evaluator owns a separate set of synthetic questions. Its outcomes must not
enter acquisition, fitting, stopping, tie resolution, or configuration choice.

Use 64 training groups and 512 evaluation groups per seed. Use 30 paired seeds.
Keep question identity and direct-state identity fixed when a second draw is bought.
This is a two-draw diagnostic. It cannot test unrestricted repeat allocation.

## 3. Budget and utility

Use `lambda = 0.05` and charge output tokens. Synthetic tokens are units in the
simulation; no language model generates them.

```text
gain = thinking_correct - direct_correct - 0.05 * thinking_tokens / 1000
utility = direct_correct - 0.05 * direct_tokens / 1000 + action * gain
```

Set direct and thinking reservation caps to 512 and 2,562 tokens respectively.
Budget checkpoints are 64,000, 128,000, and 256,000 total revealed tokens.
They include every common direct state, the eight-state initial thinking sample,
adaptive purchases, and random audits. Reserve the full thinking cap before each
purchase. Use the observed length only after that purchase.

Retain a fixed audit reservation before adaptive selection at each checkpoint.
Freeze predictions and the remaining cell set before the audit. Select at most four
remaining cells uniformly without replacement. Do not use a partial audit to
change the rest of that audit. Do not spend audit refunds on additional purchases
at the same checkpoint. Earlier audit observations can enter later checkpoints.

The protocol must distinguish the fixed-threshold unbiased estimate from the
selected threshold. Maximizing an estimate can introduce selection optimism.
Assess the selected threshold only on the separate evaluation groups.

## 4. Comparisons and analysis

Use seven acquisition methods and two fixed candidate component removals.
All comparisons use the same direct states, initial sample, response cache,
evaluation groups, threshold class, utility, and checkpoint estimator.
Call altered external methods adaptations. Do not call them reproductions.

All scored methods stop adaptive purchases when their common heuristic plausible
set has one policy. They still perform the audit. The three random controls
continue until no reservation fits or the cache is exhausted. Thus the random
comparisons test purchase selection and stopping together. Candidate versus
information gain has the same stop rule. Record the stop reason and actual
expenditure at each checkpoint. The budget curve measures policy quality
available by each allowed budget; an early stop can leave that budget unused.

Report each setting, method, seed, and checkpoint. Preserve adverse and null cases.
Report selected threshold, evaluation utility, direct and thinking accuracy,
deployment tokens, total acquisition tokens, number of distinct purchased questions,
repeat count, and audit count where the implementation supports those fields.
Record elapsed acquisition time per trajectory, including trace construction
and excluding evaluation, verification, and compression. Report its mean for
each method and setting. This is descriptive local CPU timing. Fixed method
order and machine contention prevent a causal speed claim. Do not add seconds
to token utility or treat synthetic lengths as measured solver computation.

The primary summary is normalized area under the utility learning curve (AULC).
Use the predeclared checkpoints and trapezoid weights `1/6, 1/2, 1/3`.
Compare paired seeds. Seeds measure simulation variation; they are not real datasets.
Report uncertainty as descriptive simulation uncertainty only. For paired mean
differences, use the approximate 90% normal interval
`mean +/- 1.6448536269514722 * sample_SD / sqrt(30)`, with SD denominator 29.
This interval is not part of the pass rule. Retain individual seed results.

### Fixed settings

Let `c` be uniform on `[.02,.98]`. Sample one direct correctness value with
probability `pD`. Each thinking cell has its own uniform random value `UY` and
is correct when `UY < pT`. A question-specific offset, if used, stays fixed
across its two thinking cells. Direct length is 128 except in the high-cost case.

| Setting ID | Direct probability `pD` | Thinking probability `pT` | Thinking length |
|---|---|---|---|
| `null_no_benefit` | `.45+.45*c` | `0` | 800 |
| `threshold_cost_zero` | `.25+.70*c` | `.88` if `c<.5`, else `.55` | 384 or 2304, equally likely, independent of `UY` |
| `high_noise_repeat` | `.30+.60*c` | `.72` if `c<.5`, else `.42` | 256 or 2048, equally likely and independent |
| `heterogeneous_nonmonotonic` | `.30+.60*c` | Base `[.88,.45,.90,.30]` at fixed confidence cuts `.25/.50/.75`, plus a question offset `-.25` or `+.25`, equally likely; clip to `[.02,.98]` | 256 or 2304, equally likely and independent |
| `rare_rescue_harms` | `.90` | `.98` if `c<.1`, else `.78` | 1024 |
| `high_direct_cost` | Same as `threshold_cost_zero` | Same as `threshold_cost_zero` | Same as `threshold_cost_zero`; direct length is 512 |
| `threshold_cost_positive` | Same as `threshold_cost_zero` | Same as `threshold_cost_zero` | 2304 when `UY<.5`, else 384 |
| `threshold_cost_negative` | Same as `threshold_cost_zero` | Same as `threshold_cost_zero` | 2304 when `UY>=.5`, else 384 |

The heterogeneity and nonmonotonic stress tests share one setting to retain the
eight-setting cap. This resolves the eight-family planning list before outcomes.
The three association settings have the same expected marginal correctness and
length distributions. Finite realized marginals can differ. Association changes
variance and budget history; it does not change the linear expected gain formula.

Use seeds `2026100900` through `2026100929`. Separate streams with NumPy
`SeedSequence([seed, setting_ordinal, stream])`: training 0, evaluation 1,
common initial sample 2, acquisition 3, and fixed particle normals 4.
Use the setting order in the table as zero-based ordinals. All methods share
the same underlying data and initial sample within each setting and seed.

Use the exact equations and deterministic tie rules in the
[algorithm specification](g0-threshold-algorithm-2026-10-09.md).
The policy class has at most nine members from training confidence only.
The fixed values are four strata, audit size four, exploration `.1`, plausibility
width `.03`, 32 particles, shrinkage strength two, variance priors `.10/.20`,
and variance floor `1e-4`. No configuration search is permitted.

### Method identities and screen

The seven controls are `uniform_coverage`, `uniform_repeat`,
`confidence_stratified`, `disagreement`, `closest_cost_aware`,
`reactive_impact`, and `candidate`. The two removals are `candidate_no_repeat`
and `candidate_no_joint_covariance`. The closest control is global information
gain per predicted token, explicitly an L1-inspired adaptation. Re-active impact
is also an adaptation. No original-paper guarantee transfers to these controls.

No-repeat removes adaptive repeats; mandatory random audits may still repeat a
state. The covariance removal changes only purchase uncertainty. At the same
history, preserve the full-model gain and cost means, plausible set, and audit
predictions. Different purchase histories can produce different later means.

The intended mechanism settings are `high_noise_repeat` and
`threshold_cost_negative`. For **each** setting and **each** comparator
(`uniform_coverage` and `closest_cost_aware`), require both:

- Mean paired candidate-minus-comparator normalized AULC of at least `+.005`.
- Positive paired difference on at least 20 of the 30 seeds.

All four contrasts must pass. All engineering checks must also pass. This is a
practical simulation screen, not a significance test or a claim of real-data
superiority. The margin and case choice are fixed before any simulation result.
Report all other comparisons and removals descriptively. A failed screen closes
this recipe; it does not justify changing the cases, margin, or priors.

## 5. Required checks before execution

1. Check that acquisition sees only purchased outcomes and costs.
2. Check full-cap reservations and total charges at all checkpoints.
3. Enumerate a small finite pool to check the audit correction exactly.
4. Check unequal repeat counts and fixed state identity.
5. Check all threshold actions, strict confidence ties, and extreme thresholds.
6. Check the no-benefit and deterministic limiting cases.
7. Check that the covariance removal preserves marginal mean predictions.
8. Check normalized AULC arithmetic independently.
9. Check that immutable preparation and execution records reject replacement.

Freeze source and tests in Git. Then write a preparation record with source hashes,
the exact specification, runtime identity, and output location. An independent review
must find no unresolved engineering blocker before the full simulation starts.

Use `scripts/threshold_acquisition_synthetic.py` and the two dedicated synthetic
test modules. Use `scripts/review_threshold_acquisition_synthetic.py` for separate
read-only arithmetic and accounting review. Its calculations must not import
the executor's estimation or summary helpers. The machine-readable experiment
specification must agree with this document.
The planned output is `artifacts/research/confidence-acquisition-g1-v1/`.
Limit the full study to one invocation and 1,200 seconds. Preserve its start
marker and any incomplete output. Do not replace or silently resume a failed
invocation. Report a runtime failure separately from a scientific screen failure.
Limit total artifact size to 512 MiB. Store complete traces in compressed form.

## 6. Stop rule and next step

Use one configuration per method. Do not expand the search after a failed screen.
A correctness repair requires a new documented source pin. Preserve any failed run.

If G1 fails, close this acquisition recipe and continue the empirical manuscript.
If G1 passes, prepare G2 under a separate protocol. G1 does not select real question
IDs, open references, allocate reserve rows, or start model generation.
The official test and both confirmation studies stay sealed or unstarted.
Docker remains running. Cloud and API spend remain zero.
