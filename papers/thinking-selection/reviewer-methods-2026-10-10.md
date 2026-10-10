# Independent methods review

Date: 2026-10-10. Reviewed manuscript v0.1 and tracked protocol/result documents
on `codex/confidence-acquisition-plan`, initially at `1695a1f` with a clean
worktree. This is a scientific critique, separate from the earlier transcription
audit. No raw outcomes, references, score caches, source execution, tests or new
statistical calculations were used. The manuscript is unchanged.

## Recommendation

Revise the existing evidence first. Do not start another experiment to make the
current narrative look stronger. The records support a careful empirical case
study of specified recipes and endpoints. They do not yet support a general
finding about repeated supervision, contrastive representations or learning
thinking decisions. Submission readiness depends on making the narrow insight
useful beyond the already familiar observation that complex routers can fail.

The strongest scientific distinction available is between repeated structure
in known questions and useful selection on questions excluded from fitting.
Some structure can exist while these learners fail to exploit it. The current
draft reports the failure well, but largely omits the existing evidence for
structure. A short post-hoc diagnostic box would make the argument more balanced.

## Ranked weaknesses

### 1. The central inference is still broader than the design

Failing four progression gates is a valid stop decision for the frozen recipe.
It is not four independent demonstrations of an underlying phenomenon. The
gates reuse outcomes and related utility comparisons. Later fit counts also do
not supply new evidence units.

The original learner has 40 unique outer-training questions and 391 features.
The later controls change capacity, representations and losses, but remain
small, restricted recipes on the same 50 groups. Failure can coexist with
learnable signal that these recipes, training samples or features do not capture.
The studies do not identify which explanation is correct. Use “did not establish
an improvement under the recorded endpoint,” rather than implying that more
supervision or a representation class is ineffective. [Repeat results](../../docs/phase-2-repeat-results.md),
[feasibility results](../../docs/phase-2-router-feasibility-results.md).

### 2. Opposite halves are a robustness check, not an established design advance

Question folds already keep a test question's response outcomes out of its
fitting and tuning. Training and test questions also have distinct seeded calls.
For unseen-question utility, sending training to A and evaluation to B therefore
does not establish an additional independence property that ordinary question
separation lacked.

The two directions are still useful. They show sensitivity to different
realizations of training and evaluation draws, and prevent a favorable single
direction from becoming the result. They are two evaluations of reused question
groups, not two independent confirmations. No matched comparison shows that
using halves improves inference or policy quality.

The separate same-question half diagnostic adds a different question: whether
a question's estimated average gain carries across draws. It does not directly
measure whether `E[G | question, observed draft]` is predictable on unseen
questions. Direct drafts change across draws, so disagreement also does not
isolate noise for one fixed decision state. [Repeat protocol](../../docs/phase-2-repeat-panel.md),
[repeat diagnosis](../../docs/phase-2-repeat-results.md#separate-post-hocdevelopment-explanation).

### 3. The sparse follow-up has little information about population benefit

The 228-question endpoint correctly identifies the realized contrast between
two fixed policies. Shared actions cancel; a changed state's parser-rejected
direct answer has scorer-defined correctness zero. Missing references for
unchanged actions do not invalidate that contrast.

Only one action changes. Its failed thinking call cannot estimate rescue yield
reliably. Moreover, an empirical percentile bootstrap can resample only the
observed zeros and the single negative contribution. It cannot introduce an
unseen rescue. The upper endpoint of zero is consequently not proof that the
population gain is nonpositive. Merely calling the interval conditional does
not resolve this lack of event support. Preserve the recorded interval, but
explain its empirical support explicitly. [Sparse results](../../docs/sparse-validation-results.md).

The follow-up also tests a refitted policy, not literal transfer of the old
cross-fitted actions. The all-128-state threshold has two changed training
states; the earlier control had three. Call this a prospective diagnostic of
the newly frozen guard contrast, rather than an exact replication of the three
development rescues. [Sparse preparation](../../docs/sparse-validation-preparation-results.md).

### 4. The intervals do not cover the whole learning claim

The bootstrap resamples recorded question-level differences while preserving
fits, tuning decisions and actions. It does not repeat model fitting, training
draws, optimization or the research path. Out-of-fold models also share training
questions. The published intervals should be read as resampling summaries of
the fixed recorded decisions, rather than coverage statements for a newly
trained algorithm or the whole research workflow.

Nested selection is valuable protection for each specified fit. It does not
erase the later use of these outcomes to choose new studies. The many negative
point comparisons narrow the tested recipes; they do not prove that all nearby
recipes lack value. A future algorithm-level claim needs prospective training
replicates and an uncertainty plan that includes them. [Repeat protocol](../../docs/phase-2-repeat-panel.md),
[control protocol](../../docs/phase-2-cpu-feasibility-protocol.md),
[CLM protocol](../../docs/phase-2-clm-probe-protocol.md).

### 5. The comparisons are fair for narrower questions than the headline suggests

The original learner and simple comparator use the same acquired training
labels, and the comparator is chosen inside training. The later studies also
retain a strong confidence control and training-only selection. These are real
strengths; there is no reason to weaken the baseline to obtain a gain.

However, released CLM excludes confidence and auxiliary draft statistics. Its
failure tests semantic transfer through one state format, not whether CLM can
add value when combined with the strongest cheap signal. The raw control shares
its backbone, but not head dimensions, prior training or capacity. That contrast
does not isolate a contrastive-pretraining effect.

The compact objective study matches head capacity and initialization more
tightly. Even there, one fusion rule, one seed, compression and truncated drafts
limit the scope. Different losses also target different quantities. Interpret
their decision utility, not their scores as comparable calibrated probabilities.
[MiniLM protocol](../../docs/phase-2-contrastive-protocol.md),
[CLM protocol](../../docs/phase-2-clm-probe-protocol.md).

### 6. Opportunity counts are sample-dependent

The shared 64-question, two-draw diagnostic supports different observed patterns
between the tested solver checkpoints. It does not isolate a causal model-size
effect. A question positive in at least one draw is not necessarily a question
with positive expected gain. “Any positive draw” availability also depends on
the number of draws, so counts from the eight-draw and two-draw panels cannot
be compared as if they measured an intrinsic opportunity rate.

The different 1.7B confidence results on the 50- and 64-question panels could
reflect question composition, realized outcomes or threshold fitting. The paper
does not separate those explanations. The shared two-solver comparison is the
cleaner descriptive contrast. [Two-solver protocol](../../docs/opportunity-panel-protocol.md),
[results](../../docs/opportunity-panel-results.md).

### 7. Scoring and cap evidence need precise limits

Frozen scoring protects the comparison from silent label replacement. It does
not prove that the labels represent mathematical correctness. The waived human
audit and bounded lexical parser remain substantive limits.

The cap intervention is well matched on recorded questions/seeds and verified
prefixes. It identifies the recorded 4k-minus-2k contrast on the selected cohort.
One rescue and an interval crossing zero do not establish a useful general cap
effect. The cohort was selected by forced-closure metadata, independently of
correctness; it must not be described as selected mathematical failures.
[Parser preflight](../../docs/parser-preflight.md),
[cap results](../../docs/qwen17-cap-bridge-results.md).

### 8. Utility is an operating-point result, not a deployment result

The fixed `.05` token preference is defensible because it precedes the reported
comparisons. It is still one preference over correctness and output tokens.
The paper provides no complete latency, energy or co-resident router/solver
evaluation. Token counts across model sizes are not equal compute costs.
No practical deployment recommendation follows from these tables alone.
[CLM results](../../docs/phase-2-clm-probe-results.md),
[two-solver results](../../docs/opportunity-panel-results.md).

## A useful arithmetic observation about the fresh panel

For the added-thinking guard, let `z_q` indicate a changed action. Since
correctness is at most one and token cost is nonnegative,

```text
ΔU_q ≤ z_q
mean realized-panel gain ≤ number of changed actions / number of questions.
```

The recorded mask has one changed action among 228 questions. Its realized
panel ceiling is therefore at most `1/228`, already below the predeclared `.01`
target before any positive thinking cost. Even a rescue from that single call
could not have passed the point-gain screen on this panel.

This is elementary arithmetic from the frozen contract and published count,
not a new statistical analysis, power calculation or population bound. It helps
explain why the observed event availability, rather than just the unsuccessful
call, matters. It supplies no bound on the event rate of future questions.
The original score, interval and failed endpoint remain unchanged.

## Existing evidence worth adding

Use one short box titled “Post-hoc question structure and bounded sensitivity.”
All values already appear in the [repeat result record](../../docs/phase-2-repeat-results.md).

| Existing finding | Why it helps | Required limit |
|---|---|---|
| Signed between-question gain variance `.03233`, 90% interval `[.00541,.06530]` | Prevents a failed reproducibility gate from being read as proof of zero repeated structure. | Utility²; post-hoc; assumes approximately IID/exchangeable independent draws within a question; conditional on cached labels. |
| Same-question A→B gain `+.04413` `[+.00563,+.08845]`; reverse `+.01572` `[−.02019,+.05908]` | Separates known-question label transfer from unseen-question feature learning. | One direction crosses zero; acquisition cost omitted; no unseen-question or net acquisition claim. |
| Five flagged presentation candidates leave the fixed four-draw comparison exactly `−.016204` | Shows those specific flagged cases cannot reverse the observed point comparison. | Fixed actions/costs only; no guarantee about unflagged scorer errors, refitted policies or mathematical correctness. |

Do not promote this box to a new primary result or causal explanation. Avoid
claiming that the positive variance establishes a successful router. The useful
observation is that repeated question structure and useful unseen-question
selection are different evidence requirements.

## Revision versus new evidence

The current manuscript can improve substantially without new computation:

1. State the recipe-specific empirical claim early and keep progression decisions
   separate from population conclusions.
2. Explain the limited added role of opposite halves, rather than treating their
   presence as a methodological contribution by itself.
3. Add the post-hoc box above, alongside the failed primary gate.
4. Explain the fresh mask ceiling, bootstrap support and changed refit. Do not
   call this a powered replication or a full-policy accuracy evaluation.
5. Distinguish matched objective tests, semantic transfer tests and comparisons
   with confidence; they answer different questions.

If the narrow case-study insight is still insufficient, the smallest useful
prospective block is **one second-setting replication of one frozen comparison**,
not another grid on these panels. Choose the setting for its scientific question
before observing outcomes. Use one specified low-capacity recipe and accept,
always-think and confidence controls, with parser-aware confidence where its
predeclared contract applies. Keep training and evaluation questions separate,
fix the scorer/cost contract, and preserve complete endpoint/reference rules.

For a fixed-policy claim, train once on declared training data and evaluate the
frozen policies on fresh questions. A conditional test-set estimate can then
answer that particular policy question. For an algorithm-level claim, add
predeclared training-draw/optimization replicates and include that variation in
the inference. These are different study sizes and resource requirements.

Specify the minimum useful effect and precision before selecting a question
count. The existing hypothetical SD `.16` calculations require 2,010 question
groups for a `+.01` effect at 80% power; the small panels are diagnostics, and
that scenario is not a measured variance for a new setting. There is no justified
universal “smallest N” in the current reports. [Precision record](../../docs/local-clm-and-power-results.md#prospective-power-and-budget-results).

If the desired claim instead concerns repeat usefulness, hold one observed
direct draft fixed while collecting independently seeded thinking outcomes,
and distinguish conditional state variability from changed-draft variability.
That is a different prospective diagnostic. It still would not establish an
acquisition benefit without equal-acquired-budget new-question/repeat controls.

These are design recommendations only. They allocate no questions, authorize
no new fitting/generation or sealed access, and do not reopen the completed
studies. My recommendation for the present task is revision and internal
scientific review first.
