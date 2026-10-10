# Critical scientific review

Date: 10 October 2026. Reviewed manuscript: version 0.1 at `1695a1f`.

## 1. Decision

**Revise with the existing evidence first. The paper is not ready for submission
on scientific grounds. No new experiment is recommended at this stage.**

The numerical and provenance checks support an accurate account of the completed
studies. They do not establish that the paper makes a sufficient research
contribution. The main problem is the gap between a careful experiment history
and a clear finding that changes what a reader knows.

This is a reviewer judgment, not a prediction of a venue decision. The present
evidence can support a narrow empirical case study. It does not yet support a
general explanation of router failure or a new routing method.

Author details, venue choice, and submission formatting are deferred.

## 2. What is strong

- The decision is explicit: pay for one direct draft, then accept it or buy a
  fresh thinking solve. Extra thinking does not revise the direct draft.
- Question folds keep evaluation questions outside fitting and tuning. Repeated
  response halves allow separate checks of response variation.
- Simple controls remain visible. Later controls include a matched encoder.
- The study retains failed criteria, scorer identities, and runtime deviations.
- Fresh questions, reused questions, and selected cap cases are distinguished.
- Sparse evaluation correctly identifies a policy difference without claiming
  absolute policy accuracy.

These features make the work credible and inspectable. Most are good research
practice. Their presence alone is not a novelty claim.

## 3. What prior work already establishes

This is a targeted primary-source comparison, not a systematic review. External
results were read, not reproduced. The differences below are our assessment of
the designs.

| Closest work | Established overlap | Our possible addition and its limit |
|---|---|---|
| Chen, *What Does a Routing Oracle Measure Under Stochastic Decoding?*, v3 | Distinguishes stochastic routing ceilings from hindsight unions; studies scorer and finite-draw sensitivity. | We evaluate a draft-conditioned learned policy. Repeated observations and warnings about hindsight are already established. No new ceiling result is shown. |
| Garg and Sagtani, *Unsolvability Ceiling in Multi-LLM Routing* | Studies scoring, formatting, truncation, and router collapse, including shuffled-label and random-feature controls. | Our frozen-label sensitivity and matched cap intervention have different contracts. We have not isolated a failure mechanism with comparable diagnostic controls. |
| Yang et al., *LLMs Can Predict Failure Risk, But Struggle to Predict Which Collaboration Protocol Pays Off* | Separates failure risk from protocol value; includes cheap confidence and learned controls, plus broader task/solver checks. | Our stochastic response halves and paid direct-draft setting differ. Their post-answer risk analysis means that observing a draft is not, by itself, a new idea. |
| DART, v4 | Uses observed direct drafts to accept an answer or request a fresh thinking solve; also reports supervised-router failures. | One draft and a fixed reasoning allowance differ from its two-draft/adaptive-budget recipe. A post-draft decision alone is not distinctive. No faithful DART comparison was run here. |

Primary sources: [Chen, Sections III–VI and Appendix C](https://arxiv.org/html/2607.03436v3),
[Garg and Sagtani, Sections 3–8](https://arxiv.org/html/2605.07395), and
[Yang et al., Sections 2–5](https://arxiv.org/html/2608.14927), and
[DART, Sections 2.2/4.2 and Appendix E.1](https://arxiv.org/html/2606.23181v4).
DART's full v4 text was accessible for this review; this extends the earlier
abstract-only comparison. Its main reported runs do not provide the repeated
stochastic evaluation used here. This difference does not establish priority.

**Assessment:** “confidence can beat a learned router,” “failure risk differs
from action value,” and “scorers and budgets matter” are insufficient central
claims. A different experiment contract can add useful evidence, but the paper
must state the actual observation gained from that contract.

## 4. Ranked weaknesses and required changes

### 1. Major: the contribution is a list of procedures

The Introduction lists a controlled account, separation of evidence, and an
audit trail as contributions. These describe how the research was done. The
reader still needs a precise result and a reason to care about it.

**Revision:** center the paper on the difference between observed thinking
opportunities, repeated question-specific signal, and successful learned
selection on other questions. State only what these experiments measure.
Treat the release and audit trail as support for that empirical claim.

### 2. Major: the main evidence is small and repeatedly reused

The original model has 391 features and only 40 unique outer-training questions.
Later controls still reuse the same 50 groups. The thousands of fits do not
constitute thousands of independent experiments. The bounded low-capacity
controls help, but do not exclude sample size, objective mismatch, feature loss,
or tuning limits as explanations.

**Revision:** use “the tested learners did not improve” throughout. Do not use
“routing is unlearnable” or infer a general data requirement. Separate the
original predeclared study from each later exploratory control in the main
display. Do not describe all failures as independent replication.

### 3. Major: the value of the repeated-draw design is not demonstrated directly

Holding questions out already prevents their labels from entering fitting.
Opposite response halves provide a specified evaluation over independent draws;
they do not add another independent set of questions. The two directions share
questions and exchange training/evaluation roles. They are not two independent
replications of the full learning procedure.

The manuscript has no matched experiment that varies only single-draw versus
repeated-draw evaluation while keeping the scientific target fixed. Thus it
cannot claim that this evaluation design causes a better conclusion or that
additional labels cause the observed performance change.

**Revision:** explain the two distinct uses of repeated draws: same-question
gain reproducibility, and held-out-question policy evaluation. Report the
recorded k=1/2/4 conditions as diagnostics, without claiming a general learning
curve or a demonstrated advantage from repetition.
Each draw also has a different direct response. These data do not isolate
thinking-response noise for one identical observed draft state.

### 4. Major: fixed-fit intervals do not cover the full learning procedure

The question bootstrap resamples stored outcomes with fitted actions held fixed.
It omits retraining, threshold selection, optimization-seed variation, and
research reuse. Outer-fold training sets overlap. Grouping by question is
necessary, but does not resolve these other sources of dependence and variation.

**Revision:** describe intervals as the recorded conditional summaries. Keep
the original confidence levels and criteria. Avoid presenting an interval below
zero as proof that an algorithm is inferior across future training sets.
Do not claim simultaneous coverage across all displayed controls.

### 5. Major: the fresh guard result is sparse and tests a refitted policy

The development result uses a cross-fitted threshold and has three added
rescues. The prospective rule uses a new threshold fitted on all 128 development
states; it changes two training actions. Its fresh evaluation changes one
action in 228 questions. This is a valid prospective test of the frozen rule,
but not an exact replication of the earlier cross-fitted policy.

There is also a specific interval problem to explain. The observed differences
contain one negative value and 227 zeros. Resampling these values cannot create
a rescue that was not observed. The upper endpoint of zero is therefore a
property of this empirical resampling support. It does not exclude positive
population benefit from rare, unobserved rescue events.

**Revision:** say “the frozen follow-up rule had one activation and no scored
rescue.” Preserve the interval and failed screen, with this interpretation next
to them. Do not call this proof of population harm or a general failed replication.

An elementary reviewer deduction clarifies the bottleneck. Since a changed
direct answer is rejected by the fixed scorer, and thinking correctness is at
most one,

\[
\Delta U_i=z_i(Y_{T,i}-.05C_{T,i}/1000)\le z_i.
\]

With the observed eligibility mask held fixed, even a rescue on the single
changed state cannot produce a panel mean gain above 1/228, before charging
thinking. This is below the required .01. It explains why the realized panel
could not pass that point-gain criterion once eligibility was known. It is a
finite-panel bound, not a population bound, a new statistical estimate, or a
reason to change the original screen.

### 6. Major: the most useful existing diagnostic evidence is underused

The [completed repeat diagnosis](../../docs/phase-2-repeat-results.md) contains
three results largely absent from the draft:

- A signed between-question gain-variance estimate of .03233 utility squared, with a
  conditional 90% interval [.00541, .06530].
- Same-question transfer from A to B of +.04413, with interval
  [.00563, .08845], and B to A of +.01572, with interval [−.02019, .05908].
- Fixed-policy bounds under the flagged presentation cases leave the primary
  four-draw contrast unchanged at −.016204.

These provide a more informative account than a sequence of failed screens.
They suggest that some repeated question structure can coexist with failure of
the tested policies on held-out questions. They also limit one specific scorer
explanation for the recorded comparison.

**Revision:** add a clearly labeled post-hoc diagnostic box. Keep its limits:
the variance interpretation assumes exchangeable within-question draws; one
transfer interval crosses zero; same-question transfer consumes prior labels
and omits their acquisition cost; flagged-case bounds do not cover unflagged
scorer errors or refitted policies. These are not causal explanations or
evidence that the failed primary reproducibility criterion passed.

### 7. Moderate: the controls support narrower conclusions than their names suggest

The compact objective comparison changes small heads after compression and
uses one optimization seed. Draft truncation and mean-vector fusion may discard
signal. The released CLM test uses a quantized encoder, with no full-precision
equivalence result. Its matched raw control does not isolate the effect of
contrastive pretraining.
CLM also excludes confidence and the auxiliary draft statistics. It tests a
specific semantic-transfer recipe, not whether its features add value when
combined with confidence. This limit does not justify reopening that search.

**Revision:** call these recipe checks. Retain them as bounded tests of plausible
alternatives. Do not add a larger search on the reused panel merely to obtain a
positive result. A faithful DART or other external implementation is required
only if the claim depends on comparison with that method; it is not a remedy
for the present contribution gap by itself.

### 8. Moderate: utility and operational cost need a sharper boundary

The fixed .05 token penalty is a legitimate study choice. It does not establish
the preferred operating point for another application. Token counts omit router
encoding and full deployment latency. Cross-size tokens are not equal compute.

**Revision:** retain accuracy and token counts beside utility. Describe .05 as
the frozen preference. Any new sensitivity display must have a separate export
or analysis plan and cannot replace the primary endpoint. Existing collection
charges belong in the appendix; they are not deployed-policy costs.

### 9. Moderate: the cap result adds breadth of history more than depth of explanation

The matched prefixes are a strong engineering control. However, 18 pairs on 11
selected groups and one rescue do not explain why learned routing failed.
The cap study also concerns 1.7B; the parser guard concerns 0.6B. They are not
successive tests of one fixed mechanism.

**Revision:** shorten these follow-ups in the main text. Give them explicit,
separate questions. Move full cap accounting and parser details to appendices.
Do not draw a causal chain from router failure to formatting to insufficient
reasoning budget.

The two-solver opportunity count also needs a precise label: positive realized
gain in at least one of two draws. It is not a count of questions with positive
expected gain. Counts using different numbers of draws are not directly
comparable as intrinsic opportunity rates. The shared 64-question comparison
is descriptive; a general size effect was not tested.

## 5. Recommended central claim

> On the studied GSM8K/Qwen3-1.7B panel, observed rescues and some post-hoc
> evidence of repeated question-level structure did not translate into gains
> for the specified learners on held-out questions. Bounded capacity and
> representation controls also failed their recorded criteria. Separate
> diagnostic and follow-up studies show the limits of transferring these
> observations across solver settings and policy definitions.

This is a candidate empirical claim, not a first-in-literature claim. Its
added value is the explicitly separated levels of evidence under the stated
decision contract. It remains modest relative to the closest papers.

The claim must retain the failed primary reproducibility test. Post-hoc
variance and transfer diagnostics cannot be used to reverse it.

## 6. Next work and decision rule

### Immediate work: a bounded manuscript revision

1. Replace the procedural contribution list with the central empirical claim.
2. Add the existing repeat-diagnosis box with all its limits.
3. Explain the sparse interval and the change in threshold-fitting procedure.
4. Separate primary, exploratory, and fresh evidence in one study map.
5. Prepare a fixed cached-report figure export plan. Keep original numbers,
   intervals, comparators, and weights. The plan is not executed by this review.
6. Review the revised argument again. Ask what a reader can infer beyond the
   closest papers, including DART, and which observation supports that inference.

This work needs no new solver response, label, model, or statistical fit.
Improved figures will make the evidence readable; they will not create novelty.

### Conditional follow-up: only if a broader empirical claim is retained

The most relevant extra study would test **one frozen simple learned rule versus
confidence and fixed-action controls on fresh question groups**, with a training
and evaluation contract chosen before outcomes. A second preselected task or
solver family could address breadth. It would not automatically identify why
the original learner failed.

Before collection, specify the exact claim, target population, permitted
features, scorer, cost model, training sample size, independent training/response
replicates, primary contrast, and precision target. Freeze one rule and its
selection procedure; do not carry forward a large winner search. Plan costs
and precision jointly. If the claim concerns retraining, a single fitted policy
on a fresh test set is insufficient to measure that uncertainty.

There is no defensible universal “small extra panel” at present. The existing
[power sensitivity](../../docs/local-clm-and-power-results.md) needed about
2,010 question groups for a +.01 effect at 80% power under the hypothetical
SD=.16. That assumption is not an estimate for a new task or the sparse guard.
The 256 unclaimed reserve questions do not guarantee adequate precision.

**Decision rule:** if the bounded revision gives only another instance of an
established caution, retain it as a scoped empirical report and design a new
scientific question before spending on collection. If a specific uncertainty
is both important and answerable within local resources, write a separate
prospective protocol for it. This review allocates no questions and launches
no study. Closed G1 and reused-panel searches stay closed.

## 7. Review scope

Two GPT-6.1-sol/xhigh agents supplied separate
[methods](reviewer-methods-2026-10-10.md) and
[contribution](reviewer-contribution-2026-10-10.md) critiques. Root inspected the
key records and primary sources, then reconciled their findings in this report.
Agreement between agents is not independent empirical confirmation.

The review uses the manuscript, tracked result/protocol documents, and primary
literature. It includes mathematical reasoning about the recorded estimands.
It does not re-estimate effects or intervals. No raw response, score cache,
training reference, sealed outcome, executor, fitting, scoring, or test suite
was opened or run. Original studies and manuscript v0.1 are preserved.

The prose uses short technical English. Formal ASD-STE100 conformity is not
certified. This review does not reinstate the waived human answer-scoring audit.
