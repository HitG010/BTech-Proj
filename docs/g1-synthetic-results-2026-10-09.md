# G1 result: close the threshold-acquisition recipe

Date: 2026-10-09. Branch: `codex/confidence-acquisition-plan`.
Frozen source: `0042134e762f07c9a8d2ae503a182bac0f8a44dd`.
Status: full endpoint complete; all four practical comparison screens fail.
Independent completed-artifact review passes. The executor and reviewer have exited.

## 1. Decision

**Do not start the proposed real-data pilot for this recipe.**

The [G0 review](g0-prior-art-review-2026-10-09.md) did not support a distinct
method claim. The [G1 protocol](g1-synthetic-protocol-2026-10-09.md) then tested
the proposed empirical adaptation on synthetic data. It did not meet its
predeclared requirements. Keep the rule, settings, results, and failed screens
unchanged. Do not widen the grid or tune the same recipe after this result.

This decision closes one bounded acquisition recipe. It does not show that all
active acquisition methods fail, or that acquisition cannot help real solvers.
No real solver data were used in this study.

The preferred publication work now uses the completed empirical evidence.
The [manuscript outline](empirical-paper-outline-2026-10-09.md) has a draft
abstract, research questions, claim table, figure plan, and primary-paper
comparison. A focused review remains a separate project with its own search
and screening requirements.

## 2. What was built and checked

The additive implementation contains:

- A hidden-outcome purchase interface with full-cap reservations.
- A fixed confidence-threshold class and seven acquisition controls.
- Two candidate component removals, with their limits stated explicitly.
- A random-audit estimator that corrects finite-pool sampling after adaptive
  purchases and random-cost stopping.
- Independent synthetic evaluation questions.
- Immutable preparation, invocation, traces, summaries, and terminal records.
- A separate result reviewer that imports no executor arithmetic helpers.

The focused suite passed **68 tests** before source freeze: 27 implementation
tests and 41 independent tests. Ruff passed for all four new Python files.
The historical full repository test suite was not rerun.
The [pre-execution review](g1-independent-review-2026-10-09.md) records the
design corrections and remaining scientific limits.

Source and protocol were committed before preparation and the full study.
The actual-input check verified seven committed source pins, runtime identity,
the fixed dimensions and seeds, the four comparison rules, budget reservations,
and learning-curve weights. The largest common direct/seed/audit reservation
was 63,512 tokens, below the first 64,000-token checkpoint.

## 3. Complete endpoint

| Item | Completed value |
|---|---:|
| Synthetic settings | 8 |
| Paired seeds per setting | 30 |
| Methods, including two removals | 9 |
| Acquisition trajectories | 2,160 |
| Recorded checkpoint metric rows | 6,480 |
| Recorded purchases across trajectories | 201,606 |
| Full-run invocations / retries | 1 / 0 |
| Elapsed wall time | 337.17 seconds |
| Artifacts before terminal record | 188,257,110 bytes |

The process exited with code 0. Terminal status is `complete_gate_failures`.
This is a completed study with failed scientific screens, not a runtime failure.
The run stayed below its 1,200-second and 512-MiB limits.

Each seed used 64 training groups and 512 separate evaluation groups, with two
thinking draws per group and one fixed direct state. The eight settings are
controlled distributions, not eight real tasks. The finite two-draw cache
limits conclusions about repeated sampling.

The executor checked every recorded trajectory. Its small exact audit check
covered 16 pre-audit histories. The largest floating-point residual from the
unbiasedness identity was `1.11e-16`. This checks each fixed threshold's
finite-cache estimate. It does not prove that a selected maximum is unbiased
or that a policy generalizes to real questions.

The separate reviewer checked seven source pins and 242 output pins. It
independently checked 2,160 trajectories, 158,766 adaptive decisions, 201,606
purchases, 6,480 metric rows, and all 64 paired contrasts. It reproduced the
failed screens, held-out metrics, audit estimates, accounting, and timing
summaries without re-executing acquisition. Engineering reproduction passed;
the practical scientific screen remains failed.

## 4. Predeclared comparison screens

The score is normalized area under the utility learning curve, or **AULC**.
It combines the 64k, 128k, and 256k allowed-budget checkpoints with weights
`1/6, 1/2, 1/3`. Utility subtracts `.05` per thousand synthetic output tokens.
A positive difference favors the candidate.

Each of the following four contrasts required a mean difference of at least
`+.005` and a positive difference on at least 20 of 30 paired seeds.
All four had to pass.

| Intended setting | Comparator | Mean candidate difference | Approximate 90% simulation interval | Positive seeds | Screen |
|---|---|---:|---|---:|---|
| High response noise | Uniform coverage | −.002423 | [−.008898, +.004053] | 14/30 | Fail |
| High response noise | Global information per cost | +.002488 | [−.002853, +.007830] | 12/30 | Fail |
| Negative correctness–length association | Uniform coverage | −.015927 | [−.027984, −.003869] | 9/30 | Fail |
| Negative correctness–length association | Global information per cost | −.009114 | [−.019674, +.001446] | 10/30 | Fail |

Intervals describe simulation variation. They are not real-data confidence
intervals and were not used to change the pass rule. The one positive primary
mean is below the required margin and does not satisfy the positive-seed rule.

The information-per-cost control is an L1-inspired adaptation with the same
fixed-history prediction target and stopping rule. It is not a reproduction
of the original contextual algorithm. Random controls use their affordable
budget, while scored methods can stop on a singleton heuristic plausible set.
Those random-control comparisons include both selection and stopping behavior.

### All settings remain in the record

| Setting | Candidate minus uniform coverage | Candidate minus information per cost |
|---|---:|---:|
| No thinking benefit | .000000 | .000000 |
| Zero correctness–length association | −.007095 | +.002715 |
| High response noise | −.002423 | +.002488 |
| Heterogeneity and nonmonotonic gain | −.009298 | −.004902 |
| Rare rescues and frequent harms | −.013945 | +.000391 |
| High common direct cost | −.002591 | +.006715 |
| Positive correctness–length association | −.004277 | +.001378 |
| Negative correctness–length association | −.015927 | −.009114 |

These are descriptive means from the frozen summary. The favorable high-cost
comparison is not a replacement endpoint. All 64 candidate contrasts, the
component removals, and every seed/checkpoint remain in `summary.json`.
No result-dependent search or cause-of-failure analysis was added.

## 5. Cost and interpretation limits

All direct states, initial thinking samples, adaptive purchases, and audits
count toward each strategy's revealed-token budget. The report also stores
complete-cache cost and deployment cost separately. Complete synthetic caches
contain 39,662,336 training token units and 317,999,360 evaluation token units.
**These are simulated lengths. No language model generated these tokens.**

The report stores local acquisition time by method and setting. For the two
primary settings, mean candidate acquisition times were about .029/.034
seconds per trajectory; the information control took .164/.170 seconds.
Timing includes trace construction and excludes evaluation, verification, and
compression. Fixed method order and machine contention prevent a causal speed
claim. Lower CPU time does not reverse failed utility screens.

The mean model, plausible set, information particles, and purchase scores are
heuristics. The four-cell audit can have high variance. Correctness–length
association has matched expected marginals, not identical finite realizations.
The experiment cannot isolate a general cause of failure or establish a
population result for language models. No general novelty follows from the
audit identity, repeated samples, shared feedback, or cost division.

## 6. Provenance and safe read paths

Artifact directory: `artifacts/research/confidence-acquisition-g1-v1/`.

| Record | SHA-256 |
|---|---|
| Preparation | `7b0b8734142c6f8ee337158eb53626885f38487aa2d5371ff7a7b424ddd2074c` |
| Actual-input prelaunch review | `0de15c03fc1d4cd2bd8d092de5d4c732dbfdbd4984f135cb1bce655c5ab6f8e4` |
| Invocation | `92a803e0d44d3cba1b0a754c4b217c20363c918f062148438a2aaf65bbc495a7` |
| Terminal record | `5347c26928607a4827c95fec50e201cd1d14747f07f96fd4b5ddbd072ec13928` |
| Summary | `61b26d22a8da16f3abf04c48205dbed556b9a4251bf6cc5ea1c883ac2b0ff22c` |
| Independent completed-artifact review | `4a8ca4ab388135288f56c2a5938ff3cf934d610cc89e118b7c7b2ba7f06d63b6` |

Do not call `prepare` or `run` again. Keep the source, tests, protocol,
preparation, invocation, all 240 compressed trace files, and completed reports.
The independent review command reads these records without selecting or buying
responses. Omit its `--output` option for a later read-only repeat check.

## 7. Next work

1. Close G2 for this recipe. Keep real training/validation roles unchanged.
2. Turn the empirical outline into Methods and Results prose. Use the completed
   reports and retain their original gates, endpoints, and uncertainty limits.
3. Freeze a small cached-report export and the already proposed cap-error audit
   before making new tables, figures, or error-cause claims. Do not reopen references.
4. Assess the manuscript's narrow contribution against L15–L17. Choose a
   separate replication only if a broader claim needs it, before seeing outcomes.
5. For a review paper, complete the scoped literature-coding pilot and logged
   search first. Do not describe the existing targeted review as systematic.

The official test remains sealed. Both confirmation studies and acquisition
scaling remain unstarted. Reserve256 is unchanged. Docker was not stopped.
Cloud/API experiment spend is zero. No completed real-data study was rerun.
