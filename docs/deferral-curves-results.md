# Deferral curves, refit uncertainty, and agreement: results

Run on the Mac on 2026-11-01 under the frozen
[protocol](deferral-curves-protocol.md), with four worker processes; the
generated [report](deferral-curves-report.md) is the authoritative output. This
is a **post-hoc** analysis of cached, reused development data. It generated no
response and opened no reference answer. No recorded criterion, screen, or
decision changes.

## Integrity

- Every historical repeat decision (seven policies, three conditions) and every
  two-solver confidence action and threshold was reproduced before analysis.
  The copied two-solver crossfit matched the frozen function on the real
  questions.
- Values that also appear elsewhere agree: confidence 92.75% at 628.47 tokens
  (Table 3), combined minus the selected baseline −.016204 and its fixed-action
  interval (Table 2), and confidence minus accept +.152677 and −.030540 for the
  two solvers (Table 4).
- Only the `platform` field of the runtime environment differed from the
  two-solver collection; cached bytes were verified by hash.

Values marked † below are derived from the report's accuracy and token columns
with the protocol's cost-matched random formula. The same arithmetic reproduces
the report's own lifts for confidence (+.0178, +.0620, −.0183).

## A. Accuracy–cost curves

**Repeat panel, Qwen3-1.7B, λ = .05 (400 states).**

| Policy | Accuracy | Tokens/state | Lift over random | Oracle share |
|---|---:|---:|---:|---:|
| Always direct | 89.50% | 221.14 | 0 | 0 |
| Always escalate | 94.50% | 1,610.97 | 0 | −.283 |
| Hindsight oracle | 97.00% | 342.02 | +.0707 | 1 |
| **Confidence** | **92.75%** | **628.47** | **+.0178** | **+.176** |
| Two-draft agreement (Part C) | 92.25% | 597.69 | +.0140† | — |
| Minimum-token threshold (Table 3) | 91.00% | 483.20 | +.0056 | +.028 |
| Released CLM zero-shot (Table 3) | 94.75% | 1,550.53 | +.0047 | −.203 |
| Training-selected CPU family (Table 3) | 90.75% | 514.22 | +.0020 | −.031 |
| Training-selected baseline | 90.25% | 683.06 | −.0091 | −.226 |
| Solver-only Ridge | 89.75% | 621.67 | −.0119 | −.254 |
| Combined Ridge (primary learner) | 89.00% | 757.13 | −.0243 | −.461 |
| Question-only Ridge | 88.75% | 794.10 | −.0281 | −.524 |

Lift is accuracy minus random escalation at the same token cost. Oracle share is
the fraction of the oracle's utility gain over always-direct that a policy
captures; a negative share means lower utility than always-direct.

- **Confidence is the best tested rule and still far from the oracle.** It is
  1.78 points above cost-matched random and captures 17.6% of the hindsight
  gain. Of its 100 escalations, 17 are rescues, 4 harms, 4 both wrong, and 75
  both correct; it misses 13 of the 30 rescues.
- **The learned rules sit at or below the random line.** Combined Ridge
  escalates 162 states and rescues 4; question-only Ridge is the worst policy
  tested. Among the Table 3 rows, only the minimum-token threshold, zero-shot
  CLM, and the CPU family are slightly above random. Apart from confidence,
  only the minimum-token threshold and two-draft agreement have higher utility
  than always-direct.
- **The comparison does not depend on λ = .05.** With every rule refitted at
  each λ from 0 to .3, combined Ridge has lower utility than confidence at all
  ten values (−.006 to −.054) and lower utility than the training-selected
  baseline at all ten (−.012 to −.048).

**Two-solver panel, λ = .05 (128 states per solver).**

| Solver | Always direct | Always escalate | Oracle | Confidence | Confidence lift | Oracle share |
|---|---|---|---|---|---:|---:|
| Qwen3-0.6B | 61.72% / 209.80 | 80.47% / 1,409.52 | 86.72% / 546.63 | 81.25% / 1,062.52 | +.0620 | +.655 |
| Qwen3-1.7B | 84.38% / 228.01 | 87.50% / 1,586.79 | 89.84% / 291.06 | 83.59% / 682.56 | −.0183 | −.593 |

Cells give accuracy / tokens per state.

- For 0.6B, confidence captures 65.5% of the oracle gain. It beats accepting the
  draft at every λ up to .2 and loses only at .3.
- For 1.7B, confidence is **below cost-matched random**. Of its 34 escalations,
  1 is a rescue, 2 are harms, and 8 are both wrong. Confidence minus accept is
  negative at every λ from 0 to .3 (−.0077 to −.0312).

## B. Refit-inclusive uncertainty

| Endpoint | Point | Fixed-action 90% | Refit-inclusive 90% | Width ratio | Fold repartition 5th–95th | Reading |
|---|---:|---|---|---:|---|---|
| Repeat: combined − selected baseline (primary) | −.016204 | [−.033276, −.000635] | [−.042296, +.020701] | 1.93 | [−.036404, −.004875] | no longer excludes zero |
| Repeat: combined − confidence | −.043933 | [−.064068, −.025246] | [−.057621, +.007865] | 1.69 | [−.050609, −.029268] | no longer excludes zero |
| Repeat: confidence − accept | +.012133 | [−.007486, +.034069] | [−.026994, +.027814] | 1.32 | [+.002526, +.015153] | both include zero |
| Two-solver 0.6B: confidence − accept | +.152677 | [+.085535, +.220375] | [+.068168, +.219945] | 1.13 | [+.130551, +.167709] | sign robust |
| Two-solver 1.7B: confidence − accept | −.030540 | [−.056066, −.006071] | [−.050563, +.009868] | 1.21 | [−.036918, −.016126] | no longer excludes zero |

- **Refitting widens the intervals 1.1 to 1.9 times.** Three intervals that
  excluded zero with actions held fixed now include it. Only the 0.6B benefit
  of confidence deferral stays clearly positive.
- **The fold assignment is not driving the signs.** Across 200 random
  repartitions, each endpoint's 5th–95th percentile range stays on the side
  of its original point.
- **The bootstrap means are shrunk toward zero** (for example −.012 against
  −.016 for the primary endpoint, and +.002 against +.012 for repeat
  confidence minus accept). Copied questions reduce the number of distinct
  training questions, which weakens every refitted rule. This is the shift the
  protocol warned about; the refit intervals should be read as approximate.

**What this changes in the claims.** The primary learner still fails its
criterion. That criterion required a gain of at least +.01 with a positive
lower bound; the refit upper bound is +.021, so the data neither show the
required gain nor rule it out. Statements that a learned rule *lost* utility,
or that confidence *harmed* the 1.7B two-solver panel, rest on fixed-action
intervals. With refitting included they become negative point estimates with
intervals that include zero. On the repeat panel, confidence deferral itself is
not clearly better than always accepting the 1.7B draft (+.012, both intervals
include zero). The Table 3 intervals for the other families were not
recomputed with refitting and would likely widen as well.

## C. Two-draft agreement baseline

| Panel | Accuracy / tokens | Escalation | Difference vs confidence [90%] | Directions | Free second draft | vs accept [90%] | Screen |
|---|---|---:|---|---|---:|---|---|
| Repeat 1.7B (primary) | 92.25% / 597.69 | .085 | −.003461 [−.021222, +.011806] | −.015173, +.008251 | +.007596 | +.008672 [−.005264, +.024367] | **Fail** |
| Two-solver 0.6B (secondary) | 78.12% / 997.94 | .406 | −.028021 [−.079512, +.017542] | −.062330, +.006288 | −.017531 | +.124656 [+.060736, +.191424] | Fail |
| Two-solver 1.7B (secondary) | 84.38% / 678.90 | .094 | +.007996 [−.015234, +.032537] | +.004168, +.011823 | +.019396 | −.022545 [−.030778, −.015073] | Fail |

- **The primary screen fails.** On the repeat panel, agreement is essentially
  tied with confidence (−.0035), with directional means of opposite sign. It
  escalates only 8.5% of states, a third of confidence's rate, and reaches
  92.25%.
- **The second draft is what it costs.** The extra draft costs .011 utility per
  state. If that draft were free, agreement would lead confidence by +.0076 on
  the repeat panel and +.0194 on the 1.7B two-solver panel. Charged honestly,
  neither lead survives. The free-draft values are descriptive, not policies.
- **0.6B:** agreement improves on accepting the draft (+.125) but trails
  confidence (−.028). Its lift over random is +.0409† against +.0620 for
  confidence.
- **1.7B two-solver:** agreement is slightly ahead of confidence (+.008, both
  directions positive) but fails the .01 minimum and one leave-one-out average.
  It is still below accepting the draft (−.023 [−.031, −.015]). Nothing tested
  beats always-direct for this solver.
- The secondary full8 agreement result is 92.64% at 617.81 tokens, −.006118
  against full8 confidence.

**Decision gate.** The agreement baseline fails its primary screen, as did the
token-level rules. No Phase 2 baseline beat confidence, so Phase 2 nominates
**no candidate** for a prospective confirmation. Any Phase 5 study would
compare confidence with always-direct (and could add agreement as a secondary
arm) rather than test a new rule.

## Interpretation

1. **The negative result holds across costs.** The primary learned rule has
   lower utility than confidence at every tested λ, and most learned rules are
   no better than random escalation at equal cost. This answers the review's concern about a
   single operating point.
2. **The negative result is weaker than the fixed-action intervals suggested.**
   With refitting, "did not beat confidence" stands, but "was worse than
   confidence" becomes a negative point estimate with an interval that
   includes zero. The manuscript should say this plainly.
3. **The solver-dependence result is the robust one.** Confidence deferral
   helps 0.6B under every check here (fixed and refit intervals, all fold
   repartitions, every λ up to .2). For 1.7B, confidence is below random on the
   two-solver panel and not clearly above always-direct on the repeat panel.
4. **Agreement is a near-tie, priced out by the second draft.** It escalates
   much less than confidence and nearly matches it, which fits the mixed
   September result. It does not justify a new candidate.

## Limits

Post-hoc analysis of the same reused panels. Lambda curves report refitted
rules without selecting a λ. The refit bootstrap duplicates questions, which
shrinks effects and makes the interval approximate. Agreement is simulated from
cached independent drafts and is an adaptation, not DART. Tokens from the two
solver sizes are not equal compute units.

## Manuscript integration

At the author's request, manuscript v0.7 (2 November 2026) reports this
analysis as Section 4.5 with a new Table 5 (fixed-action and refit-inclusive
intervals) and an agreement row in Table 3; the confidence–gain table is
renumbered Table 6. The abstract, introduction findings, related work, Sections
3.1, 3.5, 4.1, and 5.1, the discussion, limitations, conclusion, data
availability, and Appendices A and B now state that the primary learner trails
confidence at every tested λ, that its refit-inclusive interval includes zero,
and that only the 0.6B confidence gain stays clear of zero. Table 5 and the
agreement row were checked by script against the generated report. Earlier
tables, Box 1, figures, figure captions, and equations are unchanged. The
September studies are now Appendix D.
