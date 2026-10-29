# Confidence–gain shape audit protocol

Prepared 2026-10-29 on `codex/confidence-acquisition-plan`. This is check 1 of
Phase 2 in the [cascade reframing record](../papers/thinking-selection/cascade-reframing-2026-10-29.md#5-analyses-this-framing-calls-for-phase-2).
It is **post-hoc and descriptive** on reused development data. All outcomes
of the studied panels were already known when it was written. The code,
tests, and this protocol must be committed, and the `prepare` plan must be
written, before `execute` runs.

## Question

Does lower direct-draft confidence go with higher expected gain from deferring
to thinking? Section 3.1 of the manuscript states that a confidence threshold
can approach the optimal deferral rule only to the extent that this holds.
Confidence predicting direct errors is not enough: hard questions may also
defeat the thinking stage or make it longer, which lowers the gain.

## Inputs (read-only, cached)

| Panel | Solver | Shape | Loader |
|---|---|---|---|
| Repeat panel | Qwen3-1.7B | 50 questions × 8 draws | `scripts.repeat_cpu_feasibility.load_panel` on the completed repeat study |
| Two-solver panel | Qwen3-0.6B | 64 questions × 2 draws | `scripts.qwen06_router_pilot.closed_inputs` and `scripts.opportunity_panel_analysis.paired_rows` |
| Two-solver panel | Qwen3-1.7B | 64 questions × 2 draws | Same as above |

Both loaders verify the completed endpoints and use cached numeric-v7 labels.
The audit never calls a scorer, fetches a reference answer, fits a model,
chooses a threshold, encodes text, generates a response, or edits a completed
study file. It writes only to
`artifacts/research/data-efficiency-v1/confidence-gain-shape-v1/`, with
exclusive file creation. A completed audit is not restarted.

## Quantities

For each paired state (one direct draft and its sample-index-paired fresh
thinking response):

- \(c\): the direct draft's post-warper mean generated log probability, the
  frozen primary confidence feature.
- \(G = Y_T - Y_D - 0.05\,C_T/1000\), where \(C_T\) counts the thinking call's
  reasoning, answer, and inserted closure tokens. This is the manuscript's
  incremental gain at the frozen \(\lambda = .05\).

## Statistics, per panel and solver

1. **Confidence bins.** Five equal-count bins of the pooled states by
   confidence quantile, with bin 1 holding the lowest confidence. Edges are
   fixed on the observed states. Per bin: states, distinct questions,
   confidence range, direct accuracy, thinking accuracy, mean thinking tokens,
   mean gain with a 90% interval, and counts of positive-gain states, rescues,
   harms, and pairs where both responses are wrong. The number of adjacent
   bins in which mean gain *rises* with confidence is reported as a
   descriptive count of monotonicity violations.
2. **Pooled rank trend.** Spearman correlation between \(c\) and \(G\) over all
   states, with a 90% interval and the share of bootstrap draws in which the
   correlation is negative. A negative value means lower confidence goes with
   higher gain.
3. **Between and within questions.** Spearman correlation of question-mean
   confidence with question-mean gain (between questions), and of
   question-demeaned confidence with question-demeaned gain pooled over states
   (within questions), each with a 90% interval. This separates whether
   confidence tracks which questions benefit from whether it tracks which draws
   of a question benefit.
4. **Escalation curve.** For escalation fractions 0, 0.1, …, 1.0, the gain per
   state, relative to always accepting the draft, from escalating the
   lowest-confidence states. It is shown beside the expectation under random
   escalation and the hindsight oracle, which escalates the states with the
   largest realized gains. The largest in-sample confidence gain and its share
   of the oracle's total positive gain are reported. Both are optimistic
   in-sample values, not a deployable threshold.

## Uncertainty

Intervals use 2,000 whole-question bootstrap resamples, seed 20261029, and
central 90% intervals, matching the repeat-study convention. Each resample
keeps all draws of a question together. Bin membership stays fixed at the
observed confidence values; a resample with no state in a bin is skipped and
counted. Intervals are descriptive, have no simultaneous coverage across bins,
statistics, or panels, and omit the research path that produced these panels.
The two solvers share the same 64 questions, so their results are not
independent.

## Reading rule, fixed before execution

For each panel and solver:

- **Consistent with the threshold premise:** the pooled Spearman interval lies
  entirely below zero, and bin 1 has the highest mean gain of the five bins.
- **Inconsistent:** the pooled Spearman interval lies entirely above zero.
- **Inconclusive:** anything else.

The reading describes these reused panels only. It does not test a deferral
rule, change any failed criterion or endpoint, select a new threshold or
\(\lambda\), or support a population claim.

## Related evidence already recorded

The completed [CLM signal audit](clm-research-assessment-2026-10-03.md) reports
that negative confidence ranks positive-gain states on the repeat panel with
pooled AUROC .705045, 90% interval [.495686, .921726], and ranks direct errors
with AUROC .595238. That is ranking evidence for a binary event. This audit adds
the shape of the expected gain, its decomposition, and the between/within split.

## Preservation

`execute` reruns the frozen repeat-study verifier
(`scripts.verify_phase2_repeat.verify`) and requires the two-solver study file
inventory digest recorded at `prepare` to be unchanged.

## Commands (on the machine holding `artifacts/`)

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_confidence_gain_shape prepare
```

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_confidence_gain_shape execute
```

`execute` writes `report.json` and a readable `report.md`. Synthetic tests are
in `tests/test_audit_confidence_gain_shape.py`; they read no study data.
