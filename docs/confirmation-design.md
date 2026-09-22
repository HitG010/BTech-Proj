# From development evidence to a confirmatory study

Status, 2026-09-19: the user selected confirmation of the unchanged router.
The **3,100-question study is now locally frozen and verified**, with no new GPU
generation started. This is not an external preregistration. The authoritative
specification is `artifacts/confirmation/frozen-router-v1/protocol.json`; its
readable companion is `protocol.md`. The completed 100-question diagnostic is
preserved unchanged, including its inconclusive primary result.

Models and comparator thresholds were copied byte-for-byte, alongside source
snapshots and the dependency lockfile. The source pool has 6,873 eligible unique
questions; 3,100 were selected using seed 20260919 after excluding 1,110 allocated
IDs and normalized prompt matches. Collection comprises 31 batches of 100, with
three direct and two thinking generations each: 15,500 responses. Expected
duration is about 125–142 local hours. Total ceilings are 21.7 million charged
tokens and 217 cumulative stage hours. No cloud spending is authorized by this
preparation step.

## What the evidence supports

At the prespecified lambda=.05, joint routing minus confidence continuation has
mean utility difference +.008188 and a whole-question paired bootstrap interval
[-.020329, .044029]. The estimated paired standard deviation is .160844.

Under that uncertain effect and variance, a normal approximation gives **3,029
new questions for 80% power** at a two-sided .05 threshold, or 4,055 for 90%.
These are planning estimates, not guarantees. At 500 questions the probability
of crossing the positive rejection boundary is only about 21% under the same
assumptions. Adding repeats on the same questions does not create independent
questions or automatically deliver the same power.

Our router's utility difference against gain regression is **-.002536**.
That comparison is not an established loss, but it provides no observed positive
effect to power a superiority claim. Enlarging the sample cannot be assumed to
fix a method that may genuinely be weaker.

The matching five-response cache would take approximately **122–139 local
hours** for 3,029 new questions at measured throughput, including the upper
estimate with previous overhead. Only 250 unused questions remain in the
reserved non-test pool. The official 500 test questions remain sealed. A study
of this scale therefore needs a new disjoint data manifest and a deliberate
compute decision; it is not a routine extension of the completed diagnostic.

Reproduce the calculation:

```sh
uv run --locked rb power artifacts/probe/continuation-v1
```

The checksummed `power-analysis.json` verifies report, model, protocol and source
identities and records sensitivity to smaller effects and larger variance.
`power-analysis.md` is its readable companion. This operation uses no GPU and
does not read official test labels or change the original report.

## Alternative considered before the user's choice

Improve the effect before buying thousands of traces. Any further model or
feature selection must use the existing pilot/validation development data, with
question-grouped folds and preprocessing fit only on fold training data. Keep
the completed diagnostic out of subsequent fitting; it already informed the
research direction and cannot provide a new confirmatory result.

Include the simpler gain-regression method as a required competitor. A change
that beats confidence only by spending more, or merely recovers the simpler
baseline's performance, is insufficient evidence for the proposed contribution.
The target is a practically useful utility improvement, robustness across
training seeds, and a credible mechanism in the ablations. Do not declare a
development gain significant after selecting the best candidate on those data.

Full ReASC and DART SC-Budget comparisons remain missing. Reproducing those
methods is required before asserting superiority over their full algorithms;
current mean-log-probability gating and capped SC-3 are explicitly adaptations.

## Selected protocol: confirm the current method without modification

Freeze the existing `models.json` checksum, every comparator, numeric-v4 parser,
lambda=.05, Qwen/tokenizer revisions, decoding settings and token allowances.
Choose a fixed **3,100 new question** study before any of its outcomes are
observed. This rounding covers the point-estimate 80% calculation only; it does
not insure against a smaller true effect or larger variance.

Select the new sample deterministically from unused upstream GSM8K training
questions, excluding every previously allocated question and normalized prompt,
including the official reserved test manifest. Never select questions by model
outcome. Record source revision, seed, full IDs, and normalized duplicate checks
before generation. Keep gold in a separate scoring artifact. This is a new
confirmation sample from the upstream training pool, not an official benchmark
test result or a claim that Qwen has never seen those questions in pretraining.

Collect the same three direct/two thinking responses per question so comparison
with the existing SC-3 adaptation and the observed variance is meaningful.
Generation may resume in fixed batches. Progress checks inspect completion,
errors, tokens and runtime only. Analyze comparative outcomes once after all
3,100 questions complete. A resource stop produces an incomplete study, not an
opportunity to inspect significance and decide whether to continue. Retry only
failed jobs with their original identities; do not drop hard or truncated cases.

Primary endpoint: whole-question mean difference in accuracy-minus-token-cost
utility between the frozen joint router and frozen confidence continuation.
Average both orientations inside each question. Use a prespecified two-sided
paired mean test at alpha=.05 and report its effect/interval, plus the
whole-question paired bootstrap interval as a robustness summary. A favorable
primary result requires a positive difference; a significant negative
difference establishes the opposite direction. A non-rejection is inconclusive,
not equivalence.

Predeclare gain regression, always-direct, always-thinking, and the SC-3
adaptation as secondary utility comparisons with Holm adjustment within this
family. Positive rejection of the primary comparison gates confirmatory claims
for this secondary family; all effects and adjusted p-values are still reported.
Full published methods must be added and frozen **before** collection
if broader claims are intended. Report all comparisons, all directions, token
cost and accuracy separately. Do not substitute a favorable secondary comparison
for the primary endpoint after seeing results. Keep the current 100-question
diagnostic separate; combining it post hoc would make the pooled analysis
exploratory. Replication on another task/model/seed remains separate work.

## Implemented commands and verification

```sh
uv run --locked rb confirm prepare
uv run --locked rb confirm status artifacts/confirmation/frozen-router-v1
# Collection is a separate operation; it has NOT been launched:
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  caffeinate -i uv run --locked rb confirm run artifacts/confirmation/frozen-router-v1
```

`--batches 1` on `run` collects one unfinished batch and pauses. Resume with the
same command or omit the limit to collect the remaining sample automatically.
Scoring and comparative reporting remain locked until all 15,500 responses are
complete. `rb confirm report` also rejects incomplete samples. Status reports
completion and expenditure only, without intermediate accuracy or comparisons.

113 offline tests pass. Tests cover deterministic disjoint selection, byte-exact
model preservation, frozen-code/data checks, batch pause/resume, failed-job
retry, no refitting, no early scoring, freeze-before-generation timestamps,
paired t-test agreement with SciPy, and the Holm correction/primary gate.
`verification.json` records checks of the actual prepared 3,100-question study.

## Interpretation and references

An interval or small p-value does not establish originality or practical
importance. The [ASA guidance](https://www.amstat.org/news-listing/2021/10/08/editorial-calls-time-on-statistically-significant-in-research)
supports reporting effects and uncertainty rather than treating a significance
label as the research conclusion.

The [Center for Open Science](https://www.cos.io/blog/10-preregistration-tips)
recommends specifying sample size, analysis decisions and the treatment of
already-inspected data in advance. We will freeze these decisions before the
new study, report deviations, and publish negative or inconclusive results too.
