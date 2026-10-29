# Author scientific review

Date: 12 October 2026. Manuscript: version 0.2 at `f2c5b6e`.

**Recommendation: retain the scoped empirical paper.** Its evidence supports a
useful account of the tested selection methods and their limits. It does not
support a new routing method, an identified failure mechanism, or a general
claim about the value of repeated supervision.

This is an AI-assisted assessment prepared for the authors. Human author
endorsement remains pending. The [R6 review](revision-review.md) closed the
reporting revision. This review assesses the scientific argument that the
authors would take responsibility for. Author identities, venue selection,
and submission details remain deferred.

## 1. Scientific summary

The paper asks whether observed thinking gains and repeated question outcomes
support useful action selection on held-out questions. Its decision is precise:
accept a completed direct draft, or pay for a fresh thinking solve. The second
call receives the question, not the direct draft. Policy utility includes the
cost of both calls when thinking is selected.

The main panel contains 50 questions and 800 responses. It yields 30 scored
rescues and 10 harms across 400 paired states. These events show that thinking
can change correctness. They do not show that a policy can predict the useful
changes before buying the extra response.

The primary learner fails four of five progression criteria. Its average
four-draw utility difference against a simple baseline selected within training
is −.016204, with a conditional 90% interval of [−.033276, −.000635]. Later
bounded capacity, objective, and representation controls also fail their
screens on the same questions. Their comparator is confidence.

Separate post-hoc results suggest some repeated question-level structure.
Same-question transfer has positive point estimates in both directions, but
one interval crosses zero. It uses labels from the evaluated questions and
omits the cost of acquiring those labels. The primary reproducibility criterion
still fails. These qualifications belong in the main argument.

Sources: [manuscript, Sections 3–4](manuscript.md),
[repeat results](../../docs/phase-2-repeat-results.md), and
[claim map](revision-evidence-map.md).

## 2. The claim worth retaining

The following statement is suitable as the authors' central scientific claim:

> On the studied GSM8K/Qwen3-1.7B panel, observed scored rescues and limited
> post-hoc evidence of repeated question-level structure coexist with failed
> held-out-question selection by the specified learners. The result concerns
> these recipes, data, and cost contract. The study does not identify the cause
> of the failure.

This claim connects the evidence in the paper. It also gives the reader a
concrete distinction to inspect: a useful outcome observed after collection
does not itself establish useful selection before that outcome is known.
The distinction is already present in prior work. The contribution here is
the measured case and its documented limits.

The supporting studies should retain their separate roles:

| Evidence | What the authors can conclude | Remaining limit |
|---|---|---|
| Primary repeat learner | The specified learner misses its progression criteria. | Fixed-fit intervals do not establish inferiority across future training datasets. |
| Same-question diagnostics | Some post-hoc statistics suggest repeated question structure. | Changing direct drafts, omitted acquisition cost, and a failed primary criterion prevent a claim of useful repeat acquisition. |
| Capacity, objective, and CLM controls | The bounded tested recipes do not establish improvement over confidence. | Reused questions and restricted implementations leave other recipes unresolved. |
| Flagged presentation cases | The specified label changes cannot reverse the primary fixed-policy point contrast. | Unflagged scorer errors and refitted policies remain outside the bound. |
| Two-solver panel | The two settings show different observed opportunity and confidence-utility patterns. | Two sizes from one family do not establish a general model-size effect. |
| Fresh parser guard | The refitted frozen contrast changes one action, with no scored rescue. | Sparse observations do not exclude rare population benefits or identify absolute policy performance. |
| Selected cap intervention | The larger cap yields one rescue and lower point utility in the selected cohort. | Eleven selected groups cannot settle a general reasoning-budget question. |

Source locations and exact endpoints are in
[manuscript Tables 1–4, Box 1, and Table C1](manuscript.md) and the
[evidence map](revision-evidence-map.md).

## 3. Scientific strengths

**The decision and cost contract are explicit.** A paid direct draft changes
the value of escalation. The paper retains this cost in each policy result.
It distinguishes output-token utility from training acquisition, collection
charges, encoder work, and complete deployment cost.

**The evaluation separates question groups.** Fitting and tuning exclude the
outer evaluation questions. Opposite response halves supply different draws.
The manuscript also states that the halves reuse questions and change direct
drafts. This makes the evaluation boundary inspectable.

**The report retains failed criteria.** Later diagnostic observations do not
replace the primary endpoint. The paper records limited positive observations
beside negative results. This reduces ambiguity about which question each
analysis answers.

**The evidence has a traceable record.** Claims link to completed reports,
protocols, and documented deviations. Figures retain the reported values and
comparators. This supports inspection; it does not independently reproduce
the experiments or certify the labels.

## 4. Main scientific weaknesses

**The central evidence is small and reused.** The later fits use the same 50
questions. They add comparisons but do not add independent question coverage.
The intervals condition on recorded fits and actions. They omit retraining,
threshold selection, optimization, and research-selection variation.

**The cause of failure remains open.** Limited training groups, feature loss,
model capacity, objectives, and optimization are plausible explanations.
The controls test specific recipes. Their failures do not isolate one cause
or establish that the decision is unlearnable.

**The repeat-acquisition question remains unanswered.** Direct drafts change
between draws. Same-question transfer uses outcomes from those questions.
There is no equal-acquisition-budget comparison showing that repeated thinking
labels for a fixed draft improve selection on new questions.

**The correctness endpoint has an unresolved limitation.** Numeric-v7 supplies
the reported labels. Human scoring was waived. The flagged-case bound narrows
one explanation but cannot validate every accepted or rejected answer.

**The contribution is incremental.** The existing
[R4 literature assessment](related-work-notes.md#r4-full-text-addendum--10-october-2026)
and [R6 contribution review](revision-review-contribution-2026-10-11.md) record
substantial overlap with post-draft routing, repeated supervision, stochastic
evaluation, and failure-risk versus payoff studies. This review adopts that
dated assessment. It makes no new literature-completeness or priority claim.
A faithful external-method comparison is absent.

These weaknesses are already stated in the manuscript. More confident wording
cannot resolve them. A broader scientific claim would require new evidence.

## 5. Likely scientific objections and defensible responses

### “What do the negative results add?”

They document a specific failure under an explicit contract, with observed
rescues, limited repeat structure, bounded controls, and a restricted scorer
sensitivity result. The value is the inspectable empirical case. Its breadth
and novelty are limited. Whether that contribution meets a publication's
standard remains an external judgment.

### “Could the learner simply have too little data?”

Yes. The current evidence leaves that explanation open. The paper should
retain its recipe-specific conclusion. It cannot infer a general data
requirement or promise that scaling would recover a gain.

### “Do several failed controls establish that confidence is best?”

No. The controls cover bounded choices on reused data. The separate 1.7B
two-solver diagnostic also reports lower confidence-policy utility than direct
acceptance. The evidence supports using confidence as a serious comparator
within these studies, without establishing universal optimality.

### “Do the repeat diagnostics justify buying more labels?”

No. Same-question transfer omits acquisition cost and does not test transfer
to unseen questions. The acquisition decision remains open.

### “Does the fresh guard study confirm that guards cannot help?”

No. The refitted rule changes one action. Resampling its recorded outcomes
cannot create a rescue that was never observed. The finite-panel ceiling
applies to the observed activation mask and does not bound population benefit.

These responses follow the existing evidence and limits. They do not propose
new experiments merely to answer a hypothetical reviewer.

## 6. Author decision and next action

My scientific recommendation is to retain version 0.2 under its current title
and scope. No substantive manuscript correction was identified in this pass.
The paper can report the completed studies without collecting more data to
make the outcomes favorable.

The next decision belongs to the human authors: endorse this limited empirical
contribution, or request a specific scientific correction. Endorsement should
cover the central claim, the conditional nature of the intervals, scorer-based
correctness, and the distinction between primary and supporting studies.
This document does not record that endorsement on their behalf.

If stronger novelty remains the objective, preserve this paper and assess a
separate question about fixed-draft repeat acquisition under a matched label
budget. That assessment must establish prior-work overlap, an identifiable
comparison, and local feasibility before any collection plan. The current
review supplies no sample size, allocation, or execution protocol.

## 7. Review record

This pass read the manuscript and existing methods, contribution, and final
reviews. It used their linked claim and source records. It did not perform
a fresh literature search or independently reproduce historical results.

The manuscript, numerical tables, frozen figures, and study records are
unchanged. No raw response, score cache, reference answer, sealed outcome, or
model asset was opened. No experiment, statistical reanalysis, figure export,
or implementation test was run.

The prose uses short technical English. Certified ASD-STE100 conformity is
not claimed.
