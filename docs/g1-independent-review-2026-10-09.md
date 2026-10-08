# Independent G1 design and implementation review

Date: 2026-10-09. Status: pre-execution review complete; no unresolved engineering
blocker in the reviewed implementation. The root agent must still freeze these
files and review the actual preparation record before starting the one allowed
invocation. No full study simulation was run by this reviewer.

This review is independent of the simulator implementation. It uses the G0
algorithm and prior-art records, the G1 specification prepared before freeze, and
small synthetic fixtures. It reads no old question, response, score, reference,
model, allocation, or protected outcome. It runs no study simulation grid.

## Design findings

The implemented reserved random-audit estimator is conditionally unbiased for each fixed
threshold's finite-cache value. Condition on the complete adaptive purchase
history, fixed cache, frozen acquired and remaining cell sets, and frozen
purchased-only predictions. Each remaining cell then has inclusion probability
`L/m`. The expected expanded residual correction equals the remaining residual
total. This remains true when observed costs or labels determined the adaptive
stop. It needs independent audit randomization and a complete, frozen sample;
it does not require independent cache outcomes or inverse one-step acquisition
probabilities. Maximizing these estimates does not preserve unbiasedness and
does not give selected-policy coverage. Held-out synthetic evaluation is
therefore required.

Unequal purchased repeat counts must retain `1/(N*R)` weight per finite-cache
cell. Repeats keep the same question and direct-state identities. They do not
create new independent question groups. Nested checkpoints retain every
earlier purchase and its charge; an earlier audit becomes ordinary purchased
data at the next checkpoint.

Two pre-execution clarifications were requested and implemented:

1. Removing the covariance term from the within-state uncertainty also changes
   a Gaussian posterior mean if it is used throughout the mean update. The
   agreed removal uses the full joint model for gain means, cost means,
   plausible policies and audit predictions at a fixed history, and uses the
   alternate uncertainty only in the candidate's purchase-reduction score.
   Different purchase trajectories can subsequently produce different means.
2. The global information control must select particle-best policies using
   exact acquired-cell gains plus latent predictions for remaining cells.
   This aligns its finite-cache target with the candidate. Its categorical
   observation law and Gaussian update remain heuristic surrogates; it is an
   L1-inspired adaptation, not a faithful reproduction or inherited guarantee.

The initial implementation also checked identity uniqueness without requiring
the identity tuple to have exactly one entry per state. Extra entries could
therefore conceal duplicate identities in the used prefix. This was corrected
before execution. Direct and thinking integer validation now occurs before
casting; fractional correctness or lengths cannot silently change an outcome
or cross the token cap. Independent tests cover both repairs.

Singleton plausible-set stopping is shared by the scored methods and candidate
removals. The three random controls spend their affordable budget. Their
comparison therefore includes selection and stopping behavior. The matched
candidate-versus-information comparison shares the stopping contract. Reports
must include stop reasons and actual revealed expenditure; fixed-checkpoint
learning curves describe a policy available by each allowed budget.

## Independent checks

`tests/test_threshold_acquisition_review.py` contains **41 passing independent
tests**. They check:

- Exhaustive audit expectation and design covariance over all fixed-size
  samples, with unequal purchased repeats and observed-cost-dependent stops;
  full remaining-pool exactness and absence of estimator clipping.
- Full-cap reservations before reveal, the entire audit batch reserved before
  its first reveal, exact settlement/refunds, nested checkpoint histories,
  repeat identities and conditional cell probabilities.
- Strict confidence ties, duplicate action removal, endpoints and the declared
  minimum-escalation utility tie rule.
- Identical fixed-history mean/cost predictions under covariance removal,
  changed uncertainty scores, and independently computed global information
  tables with exact acquired-cell contributions.
- First scored-selection invariance when all unpurchased labels and costs are
  swapped; malformed-input rejection, AULC arithmetic and immutable-file bytes.
- Independent read-only trace review detecting ledger, frozen-prediction,
  repeat-identity, audit-estimate and AULC tampering.
- Exact restoration of seeded synthetic training/evaluation arrays for all
  eight distribution contracts, without acquisition or a simulation screen.
- Independent arithmetic for recorded acquisition timing means, minima,
  maxima, counts and scope; tampered timing means are rejected.

Focused command:
`.venv/bin/python -m pytest -q tests/test_threshold_acquisition_synthetic.py tests/test_threshold_acquisition_review.py`
passed **68 tests**: 27 implementation tests and 41 independent reviewer tests.
Ruff passed for all four dedicated Python files. The full repository
suite and full simulation grid were not run by this reviewer.

The independent `scripts/review_threshold_acquisition_synthetic.py` imports no
implementation helper. After the study finishes, it reads only the new G1
artifacts and their source pins; restores seeded synthetic arrays; reconstructs
recorded purchased-only mean and cost arithmetic; verifies raw reservations,
charges, repeat identities, frozen audit corrections/covariances and checkpoint
prefixes; and recomputes held-out metrics, AULCs, descriptive intervals, all 64
paired contrasts and the four fixed practical screens. It checks the one
invocation, prelaunch marker, original inventory, runtime ceiling and all 6,480
metric rows. It does not re-execute acquisition. Its optional output uses
exclusive creation; omitting `--output` gives a read-only stdout review.
It recomputes recorded acquisition-time summaries without retiming work; these
are descriptive CPU measurements including trace construction, with no causal
speed claim.

Completed-artifact review is pending the frozen invocation and actual-input
prelaunch check.
Its passing result would establish engineering reproduction of this synthetic
study, separately from whether the practical scientific screen passes.

## Scope and limitations

The design is an empirical acquisition adaptation. A useful synthetic mechanism
would not establish method priority, real-solver superiority, calibration,
anytime coverage, or an unrestricted repeat-allocation advantage. An audit of
four cells can be noisy. The eight fixed synthetic settings and separate
evaluation groups must be retained even if the practical screen fails.

This review creates no real role or reference endpoint and starts no model,
collector, training, fitting, download, or network job. Docker remains running;
API and cloud expenditure remain zero.
