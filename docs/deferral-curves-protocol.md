# Deferral curves, refit uncertainty, and agreement baseline: protocol

Prepared 2026-11-01 on `codex/confidence-acquisition-plan`. This covers items
7, 8, and 10 of Phase 2 in the
[project review](project-review-and-publication-plan-2026-10-29.md#phase-2-cached-data-analyses-no-new-generation-47-days-cpu),
and check 4 of the
[cascade reframing record](../papers/thinking-selection/cascade-reframing-2026-10-29.md#5-analyses-this-framing-calls-for-phase-2).
It is a **post-hoc** CPU analysis of cached data. Code, tests, and this
protocol must be committed, and the `prepare` plan written, before `execute`
runs.

It generates no response, calls no scorer, and opens no reference answer.
It reads the cached repeat panel and two-solver panel through the existing
guarded loaders, plus the extracted answers already stored in their cached
score files. The only fitting is a rerun of the historical rules (the
repeat study's confidence threshold and Ridge learners, and the two-solver
confidence threshold) on resampled, repartitioned, or re-weighted questions.
No new rule is fitted or tuned, and λ = .05 remains the primary operating point.
All original decisions and failed criteria stay as recorded.

## Inputs

| Panel | States | Policies reproduced before analysis |
|---|---|---|
| Repeat, Qwen3-1.7B | 50 questions × 8 draws = 400 paired states | accept, escalate, confidence, question-only, solver-only, combined, and the training-selected baseline, for A4→B4, B4→A4, and full8 |
| Two-solver, Qwen3-0.6B | 64 × 2 = 128 | crossfit confidence, both draw directions |
| Two-solver, Qwen3-1.7B | 64 × 2 = 128 | crossfit confidence, both draw directions |

**Reproduction gate.** Before any statistic is computed, `execute` reruns the
historical fits at λ = .05 and requires:

- Repeat panel: every decision of all seven policies, in all three conditions,
  equals the primary repeat report. The combined-minus-baseline means, and the
  four-draw average with its interval, equal the report.
- Two-solver panel: every crossfit confidence action and threshold equals the
  closed report, and confidence-minus-accept equals the report for both solvers.
- The reduced fit used for resampling (combined learner only; see below)
  reproduces the same combined, confidence, and selected-baseline decisions.

## Part A: accuracy–cost curves (item 7)

Units: four-draw policies are pooled over both directions (each of the 400
repeat states is evaluated once, which equals the average of the two
directional means). Two-solver policies are pooled over both draws (128 states
per solver). Tokens include the paid direct draft and any thinking call, as in
the original studies.

For each panel:

1. **References.** Always direct, always escalate, and the hindsight oracle,
   which escalates exactly the states with positive realized gain at λ = .05.
   The oracle is not a deployable rule.
2. **Cost-matched random.** Escalating each state independently with
   probability \(p\) has expected accuracy
   \(\mathrm{acc}_D + p(\mathrm{acc}_E - \mathrm{acc}_D)\) and expected tokens
   \(\mathrm{tok}_D + p\,\overline{T}\). For each policy, **lift over random**
   is its accuracy minus the random accuracy at the same token cost. **Oracle
   share** is \((U - U_D)/(U_{\mathrm{oracle}} - U_D)\) at λ = .05.
3. **Policies at λ = .05.** Accuracy, tokens, utility, escalation rate, lift,
   oracle share, and the composition of escalations: rescues, harms, both
   correct, both wrong, plus missed rescues. The full8 repeat policies are
   reported as secondary. The Table 3 rows already in the manuscript (CPU,
   compact neural, CLM, token-level families) are placed on the same axes from
   their reported accuracy and tokens. They are not recomputed.
4. **λ sweep.** At each λ in {0, .01, .02, .03, .05, .075, .1, .15, .2, .3},
   every historical rule is **refitted at that λ** with the original folds,
   halves, and selection procedure, and evaluated on held-out questions. This
   traces each rule's operating curve. It selects nothing: λ = .05 stays the
   primary point, and no policy or endpoint changes. Reported per λ: accuracy,
   tokens, and utility of each rule and of the oracle; for the repeat panel,
   combined minus confidence and combined minus the selected baseline; for the
   two-solver panel, confidence minus accept.
5. **In-sample envelopes, descriptive only.** Escalating the lowest-confidence
   fraction \(f\) of states, for \(f = 0, .05, \dots, 1\), gives the best curve
   any single confidence threshold could reach in hindsight. Escalating rescues
   in increasing order of thinking cost gives the hindsight accuracy frontier.
   Both use realized labels and are not deployable.

## Part B: refit-inclusive uncertainty (item 8)

The original intervals hold fitted actions fixed. This part adds uncertainty
from refitting the rules on different training questions.

| Endpoint | Original value and fixed-action 90% interval |
|---|---|
| Repeat: combined minus training-selected baseline, four-draw average (primary) | −.016204 [−.033276, −.000635] |
| Repeat: combined minus confidence, four-draw average | recomputed under the original convention |
| Repeat: confidence minus accept, four-draw average | recomputed under the original convention |
| Two-solver 0.6B: confidence minus accept, average of draws | +.152677 [+.085535, +.220375] |
| Two-solver 1.7B: confidence minus accept, average of draws | −.030540 [−.056066, −.006071] |

Fixed-action intervals are recomputed with each study's original seed (repeat
20261002, two-solver 20261009) and must equal the reported values where these
exist.

1. **Refit-inclusive question bootstrap.** 2,000 resamples of whole questions
   with replacement (seed 20261102 for the repeat panel, 20261103 for the
   two-solver panel, whose resample is shared by both solvers). Each
   resampled question keeps its original outer fold, so copies of a question
   never sit in both training and evaluation. Within training, the repeat
   study's inner question folds are formed over **distinct** questions and
   then expanded to their copies. When no question is duplicated, this equals
   the original inner split exactly. Every rule is then refitted with its
   original procedure, and the endpoint is recomputed. Reported: the central
   90% percentile interval, bootstrap mean and standard deviation, share below
   zero, and the ratio of refit to fixed-action interval width.
2. **Fold repartition.** 200 random repartitions of the original questions
   into five folds of the original sizes (seed 20261104 repeat, 20261105
   two-solver), with full refitting on the original data. This isolates the
   variation due to fold assignment. Reported: minimum, 5th, 50th, and 95th
   percentiles, maximum, and share below zero.

The two-solver threshold search is a line-for-line copy of the frozen
crossfit with λ as an argument. Its only difference is that a fold left
without held-out questions by a resample is skipped; the frozen function
rejects that case, which has roughly a 0.7% chance of occurring somewhere in
2,000 resamples. Tests compare the copy with the frozen function at several λ
values, and `execute` requires equality on the real questions before any
statistic is computed.

Repeat resampling refits only the combined learner, the confidence threshold,
and the training-selected baseline, because these are the only rules in the
three endpoints. The baseline selection and each learner's alpha choice are
computed separately in the historical code, so dropping the question-only and
solver-only learners changes none of these decisions. The reproduction gate
checks this on the real data.

**Reading, fixed before execution, per endpoint.**

| Fixed-action interval | Refit-inclusive interval | Reading |
|---|---|---|
| Excludes zero | Excludes zero on the same side | `sign_robust` |
| Excludes zero | Includes zero | `no_longer_excludes_zero` |
| Includes zero | Includes zero | `both_include_zero` |
| Includes zero | Excludes zero | `refit_excludes_zero` |
| Excludes zero | Excludes zero on the other side | `sign_reversed` |

These readings describe uncertainty only. They do not change any recorded
criterion, screen, or decision. A bootstrap of a cross-fitted pipeline is an
approximation: copied questions reduce the number of distinct training
questions, so the refit distribution can be shifted as well as widened. The
bootstrap mean is reported beside the original point for this reason.

## Part C: simulated two-draft agreement baseline (item 10)

A self-consistency gate: draw a second direct draft; accept the first draft if
both drafts give the same answer, otherwise escalate to a fresh thinking solve.
**Both drafts are charged**, and the thinking call is charged on escalation.
The September studies tested the same two-draft adaptation under an older
scorer and gave mixed results: highest utility on one 50-question holdout,
below confidence on 200 development questions (see the
[September appendix draft](../papers/thinking-selection/september-studies-appendix-draft.md)).
That motivates this check; it is not evidence for either outcome here.

Two drafts agree when both have parser status `ok` and their extracted answers
are numerically equal under the v5 normalization that v7 uses. An unparsed
draft never agrees. Answers come from the cached score files; correctness is
not used to decide agreement. Equal answers must have equal cached correctness,
and the analysis stops if they do not.

- **Repeat panel (primary).** In each four-draw direction, every evaluation
  state is paired with each of the other three draws in its evaluation half,
  and the results are averaged over partners. This is the expected value
  over a random second draft. The full8 condition pairs each state with the
  other seven draws (secondary). The rule needs no training, so the folds play
  no role, but the comparison uses the same evaluation halves as the frozen
  four-draw confidence policy.
- **Two-solver panel (secondary).** Each state is paired with the other draw of
  the same question, and the comparator is the reproduced crossfit confidence
  action for that draw.

**Screen, fixed before execution** (the same as the CPU, neural, CLM, and
token-level screens): versus the frozen four-draw confidence policy, the
average utility difference is at least .01; both directional means are
positive; and every leave-one-question-out average is positive. Intervals use
2,000 whole-question bootstrap resamples with seed 20261101 and central 90%
intervals. The two-solver screen is secondary and uses the two draws as its
directions.

Also reported, descriptively: agreement minus accept; the expected composition
of escalations; the utility cost of the second draft; and the difference that
would result if the second draft were free. The free-draft value is not a
policy and is not screened.

**Decision gate** (from the project review): if the agreement baseline passes
its primary screen, it is reported as exploratory and becomes the single
pre-registered candidate for any later prospective confirmation. It is not a
result. A failure is evidence against this rule on this panel only.

## Outputs, preservation, and runtime

Everything is written to
`artifacts/research/data-efficiency-v1/deferral-curves-v1/` with exclusive
file creation: `plan.json`, `report.json`, and `report.md`. A completed
`execute` is not restarted. `execute` reruns the frozen repeat-study verifier
and checks that the two-solver study inventory is unchanged. The two-solver
collection environment may differ from the audit machine. As in the
confidence–gain audit, this is recorded rather than required to match, because
cached bytes are verified by hash.

Resampling runs in worker processes, each limited to one BLAS thread. Results
do not depend on the number of processes, and the report records it. Expect
roughly 10–20 minutes on four cores.

## Commands (on the machine holding `artifacts/`)

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_deferral_curves prepare
```

```bash
caffeinate -i env PYTHONPATH=src .venv/bin/python -m scripts.audit_deferral_curves execute
```

`execute` accepts `--processes N` (default: the smaller of 4 and the CPU
count). Synthetic tests are in `tests/test_audit_deferral_curves.py`; they read
no study data.
