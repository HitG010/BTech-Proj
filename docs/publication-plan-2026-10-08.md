# Publication plan for the completed research and the new question

Date: 2026-10-08. Status: proposed writing and evidence plan.
No manuscript was submitted. No editor was contacted. No artifact was published.
The [main research plan](novelty-plan-2026-10-08.md) sets the method experiment.
The [literature assessment](novelty-literature-2026-10-08.md) records the sources checked.

## 1. Recommended order

Prepare one empirical manuscript first. Develop the acquisition idea through the bounded gates in parallel with writing.
Use a focused review as a conditional second project if the literature coding produces a distinct contribution.
Keep a technical report and artifact package as useful outputs regardless of journal acceptance.

| Output | What can be reused | What is still required | Effort estimate, not acceptance time |
|---|---|---|---|
| Empirical paper | Completed studies, controlled comparisons, prospective failures, accounting, and preservation checks. | Exact contrast with prior audits; a coherent scientific claim; independent evidence for any broad claim. | Draft in 7–10 focused working days. Submission readiness may need 2–4 weeks or longer. |
| Method paper | Generation system, confidence features, scorers, acquisition motivation, and proposed simulator. | A distinct acquisition mechanism, strong equal-budget comparisons, and independent evidence. | Feasibility decision in 10 working days. A supported paper may require 4–8 weeks or longer. |
| Focused review | Literature knowledge, experiment-derived coding questions, and examples. | Reproducible search, explicit screening, systematic extraction, and a new synthesis. | Scope pilot in 3 days. A full draft may require 4–6 weeks. |
| Technical report and artifact | Most completed documentation and code. | A clean narrative, release manifest, license checks, and exclusion of protected material. | A private release candidate in 5–7 working days. |

These schedules assume concentrated work and successful data access and runtime checks.
They cannot predict peer-review decisions. Do not make the calendar a reason to relax evidence standards.

## 2. Empirical paper: preferred first route

Proposed title:

**When More Supervision Does Not Improve Thinking Selection: A Controlled Study of Small Hybrid Language Models**

Main question:

> Under the tested solver and cost settings, which sources of supervision improve thinking selection beyond confidence?
> Which apparent improvements persist across independent response draws and prospective follow-up?

The paper should have three connected contributions, if the final evidence supports them:

1. A controlled comparison of supervision and representation choices under one explicit accept-or-think contract.
2. An account of which development findings survived the specified follow-up tests.
3. A reproducible measurement package for costs, scorer identity, repeated outcomes, and deviations.

These are proposed contributions. Generic negative results, scorer warnings, and noisy oracles already have prior work.
Compare directly with literature items L15–L17. The new value must be more precise than “complex routers can fail.”

### Manuscript outline

| Section | Content | Evidence source |
|---|---|---|
| Motivation and contract | The accept/fresh-thinking decision; sunk draft cost; fixed lambda; observed-input boundary. | Updated problem statement and frozen protocols. |
| Research questions | Useful thinking opportunities, transfer across draws, representation contribution, prospective stability. | Questions set out explicitly without pretending they were all original preregistered hypotheses. |
| Methods | Solver identities, question roles, confidence controls, scorers, grouping, cost accounting. | Original study records and source pins. |
| Main evidence | Repeat-panel controls and matched representation/objective results. | Frozen repeat, CPU, neural, and CLM reports. |
| Solver dependence | Matched 0.6B/1.7B opportunities and practical direct baseline. | Two-solver panel; restrict conclusions to these sizes and settings. |
| Follow-up | Failed fresh parser rule and bounded cap intervention. | Prospective sparse validation and selected cap study, reported separately. |
| Limits | Reuse, sparse events, conditional intervals, one family, scorer limits, and runtime deviations. | Existing limitations and full deviation record. |
| Reproduction | Exact table inputs, cached-only commands, code and artifact manifest. | Additive export of completed artifacts. |

Use a small number of scientific figures. Avoid a chronological list of every engineering checkpoint.
Suggested figures are policy utility with matched controls, rescue/harm counts, and a development-to-follow-up evidence diagram.
Put recovery details in an appendix, with their effect on cost and interpretation in the main text.

### Minimum claim discipline

- Report the original failed gates alongside later exploratory results.
- Keep the four-draw and full8 comparisons separate.
- Distinguish independent draws from independent question groups.
- Call CLM results a test of the quantized, pinned recipe.
- Do not infer general failure of contrastive learning or routing.
- Do not report sparse validation as full-policy accuracy.
- Do not infer mathematical correctness from syntax acceptance.
- Do not treat automatic or agent review as a human scoring audit.
- Do not state that a longer runtime allowance fixed the earlier stalls.

The [evidence map](research-evidence-map-2026-10-08.md) supplies the claim-to-source table.
All new analyses need their own versioned plan before execution. No closed executor needs to run again.

### What adds value most efficiently

First finish the cached error/presentation audit and the comparison to the closest empirical papers.
Then decide whether the paper has a useful narrow single-setting claim.
If it needs broader evidence, freeze one second-setting replication of an existing comparison.
Choose that setting from task requirements and feasibility before seeing outcomes.
Do not add another model search on the 50-question panel.

Full DART and other external comparisons are required only for claims that depend on beating those systems.
If they are unavailable, scope the paper to the tested controls and document that limitation.
An exact reproduction claim requires matching the original method's protocol, not its name.

## 3. Review paper: possible, with a different contribution

Proposed title:

**Evidence and Cost in Adaptive LLM Reasoning: A Focused Review of Supervision and Evaluation**

Review question:

> What evidence supports compute-saving claims in adaptive reasoning, and what costs or sources of uncertainty remain unmeasured?

Existing routing and reasoning surveys make a broad method catalogue a weak choice.
The proposed review would code the evidence behind each claim.
Our experiments supply examples and useful questions. They do not replace a systematic literature sample.

### Scope pilot before a full review

Code 15–20 primary studies and the closest surveys from the literature assessment.
This is a scope pilot. Do not claim saturation, completeness, or publishable coverage from that count.
Ask whether the new table answers a question that the current survey tables cannot answer.
If it adds only familiar terminology, merge the useful material into the empirical paper's related work.

Proposed extraction fields:

| Field | Information to record |
|---|---|
| Decision | Model choice, reasoning-mode choice, sample count, early stop, or a sequential combination. |
| Available inputs | Question only, direct answer, partial trace, hidden states, or external verification. |
| Learning target | Direct correctness, action gain, cost-adjusted gain, preference, or another stated target. |
| Supervision unit | Question, response, action pair, independent repeat, or human annotation. |
| Acquisition | Uniform, active, repeated, partial, or not reported. |
| Costs | Training generation, annotation, cache building, tuning, inference, latency, memory, failures. |
| Evaluation unit | Unique questions, draws, tasks, seeds, and any shared dependencies. |
| Information boundary | What was available before each decision; separation of acquisition, tuning, and evaluation. |
| Measurement | Scorer, truncation, parsing, rejection rules, and independent scoring checks. |
| Controls | Confidence, direct, always-think, random, strong fixed policy, and closest external method. |
| Uncertainty | Fixed-policy intervals, refits, seed variation, multiplicity, and prospective confirmation. |
| Reproduction | Public code, model revisions, data identities, protocol deviations, and access limits. |

Use “not reported” when the paper is silent. Silence does not prove that an operation was not performed.
Distinguish author claims from our interpretation. Link each extracted field to a page, section, or code location.
Do not assign a single quality score that hides these different dimensions.

### Proposed review protocol

1. Freeze the research questions and extraction form before the full search.
2. Search ACL Anthology, arXiv, OpenReview, and relevant proceedings. Add citation searches from included surveys.
3. Use a main search period of 2023 through 2026-10-08, with older acquisition theory as background.
4. Include empirical methods that allocate LLM calls, reasoning tokens, or response supervision and report costs or budgets.
5. Exclude internal mixture-of-experts routing, unrelated networking, and unsupported product claims from the main corpus.
6. Record the date, exact query, source, retrieved identifier, version, and inclusion decision.
7. Deduplicate preprints and published versions. Retain version changes that affect an empirical claim.
8. Screen title/abstract, then full text. Record a reason for each full-text exclusion.
9. Have two readers code a predefined subset independently. Resolve disagreements and retain the original decisions.
10. If only one reader is available, disclose that limit and retain a reproducible extraction audit.
11. Synthesize matched evidence categories. Avoid pooling accuracy or token gains across incompatible models and tasks.
12. Repeat the dated search before submission and publish the final screening counts and extraction table.

No independent second reader participated in this planning review.
The historical human-scoring waiver is separate from literature coding.
This plan does not quietly reinstate a human answer-scoring requirement.

Possible synthesis products are an evidence matrix, a cost-coverage map, and a list of unresolved causal questions.
A statistical meta-analysis is not the default. Different tasks, tokenizers, action sets, and scoring rules may prevent it.

## 4. Artifact and thesis route

Create a clean, documented export of the experiment harness and permitted evidence.
Include a machine-readable study manifest, versioned scorers, synthetic fixtures, aggregate tables, and a reproduction guide.
Keep the selected paper tables reproducible from cached scores without fetching references.

Release value comes from usability outside this repository.
Add one synthetic example that runs without model downloads or private artifacts.
Explain the data contracts and failure-accounting rules.
Check licenses before selecting any raw text or model material.
Exclude all sealed roles, credentials, local machine details, and unapproved raw datasets from the export.

The BTech thesis can contain the full research history and failed hypotheses.
The paper should focus on one contribution. A private artifact candidate can be prepared before any public release decision.

## 5. Venue fit checked on 2026-10-08

| Route | Assessment and source |
|---|---|
| TMLR empirical or method paper | Scope includes empirical and reproducibility studies. The paper needs supported findings of interest. A new algorithm is not mandatory. See [scope](https://www.jmlr.org/tmlr/editorial-policies.html) and [criteria](https://www.jmlr.org/tmlr/acceptance-criteria.html). |
| TMLR pure survey | Ineligible under the current FAQ: surveys are no longer considered from 2026-09-01. See [FAQ](https://www.jmlr.org/tmlr/faq.html). |
| Computational Linguistics survey | A plausible route for a substantial NLP-focused synthesis. Guidance describes a proposal stage. Check the current portal because the informal page has an old footer. See [guidance](https://cljournal.org/submissions.html) and the [newer editorial](https://direct.mit.edu/coli/article/51/1/1/127780/Opening-a-New-Chapter-for-Computational). |
| TACL focused survey or empirical paper | Requires substantial original insight and the same technical standard as regular submissions. See [guidelines](https://direct.mit.edu/tacl/pages/submission-guidelines). |
| Relevant workshop | Useful for focused feedback if a current call fits. No open call or deadline is selected here. Verify archival status before submission. |
| Preprint and technical report | Useful for sharing a complete, checked study. A preprint is not peer-reviewed acceptance. Public release remains a separate action. |

Do not submit the same results simultaneously to overlapping archival routes.
TMLR's originality policy is strict about overlap with archival papers, including the authors' own prior publications.
A later method paper and an earlier empirical paper need distinct claims and evidence.
If both contributions mature together, one stronger paper may be preferable.

Human authors must check the arguments, sources, and final manuscript, and take responsibility for the work.
Record AI assistance according to the selected venue's current policy.
This plan is a research aid. It does not substitute for the authors' scientific judgment.

## 6. First ten working days

| Time | Publication work | Method work |
|---|---|---|
| Days 1–2 | Freeze the empirical claim table; compare L15–L17; prepare manuscript outline. | Complete G0 technical distinction and one algorithm specification. |
| Days 3–5 | Write methods and existing results; prepare artifact inventory; complete review scope pilot only if useful. | Implement and verify the frozen synthetic study. |
| Days 6–7 | Write limitations and discussion; reconcile every number with its source. | Prepare G2 only if G1 passes and the full new protocol is reviewed. |
| Days 8–10 | Complete an internal manuscript draft; identify the smallest missing evidence block. | Finish the bounded pilot if runtime permits; make a recorded continue/stop decision. |

The immediate useful output is a checked manuscript draft plus a falsifiable acquisition hypothesis.
Acceptance and novelty remain outcomes to establish through evidence and review.
