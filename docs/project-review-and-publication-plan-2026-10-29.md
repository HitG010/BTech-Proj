# Project review and publication plan

Date: 2026-10-29. Branch: `codex/confidence-acquisition-plan` at `15f5b3c`.
This is an analysis and a proposed plan. It runs no experiment, opens no
reference answer or sealed role, and changes no study artifact. The test suite
was not run for this review, and the ignored `artifacts/` directory, which holds
the raw responses, is not present in this cloud checkout.

## 1. Summary

- **Best branch:** `codex/confidence-acquisition-plan`. It contains all the
  work from `master`, `research/router-studies` and
  `codex/research-data-efficiency`, plus the G0/G1 study and the manuscript.
  The only material it lacks is the `research/pilot-v2` reports and
  `analysis.py` (Section 3).
- **What was built:** a careful, reproducible measurement harness for Qwen3
  direct-versus-thinking experiments, and about a dozen studies. Each study
  was frozen before it ran. Together they ask whether a learned router can
  decide when thinking is worth its cost, and whether its training data can
  be collected more cheaply.
- **What was found:** thinking sometimes rescues a direct answer (30 rescues and
  10 harms in 400 pairs). However, no tested learned router beat a simple
  confidence threshold, and the original contribution (cost-aware acquisition)
  failed both on real data and in synthetic tests.
- **The paper:** `papers/thinking-selection/manuscript.md` (v0.3, 24-page PDF)
  is an **empirical negative-results paper**, not a review (survey) paper.
  Its numbers and provenance are carefully checked. The review in Section 6
  finds that it is **not yet ready for a peer-reviewed venue**. The main
  reasons are:
  1. It omits the closest prior work: confidence-based cascade deferral.
  2. Its central evidence is 50 questions from one near-saturated dataset.
  3. It reports one cost operating point and no accuracy-versus-cost curves.
  4. It omits standard deferral baselines.
  5. It is written like an audit report rather than a paper.
- **Recommended route:** first, a short, reframed paper built from the existing
  data plus cheap CPU analyses, aimed at a negative-results workshop and arXiv.
  Second, if the stronger journal route (for example TMLR) is wanted, run one
  prospective, adequately powered confirmation on a free GPU with a second,
  harder dataset. Section 8 gives the steps.

## 2. What was built

### 2.1 Infrastructure (`src/reasoning_budget/`, `scripts/`, `tests/`)

About 24,000 lines of source and scripts and 9,000 lines of tests (per the
2026-10-07 project record: 720 offline tests). The main components:

| Component | What it does |
|---|---|
| Two-stage generation backend | Direct and thinking modes of Qwen3 with exact token/time accounting, forced closure at the reasoning cap, full EOS list, pre- and post-warper confidence |
| Resumable runner | Per-job seeds, atomic checksummed records, token and time reservations, failure policy, run identities |
| Gold-free scorer lineage | Exact rational numeric parser (numeric-v5, then opt-in v7); the parser never sees the reference answer |
| Frozen data roles | Disjoint GSM8K allocations: bridge, repeat panel, 1,200 acquisition pool, 200 validation, 2,000 sealed confirmation, 548 reserve (256 still unclaimed), sealed official test |
| Study executors and reviewers | One frozen executor per study, plus an independent re-verification script for each |
| Router families | Ridge on MiniLM plus lexical and draft features, PCA/capacity controls, compact contrastive heads, released CLM heads on a 4-bit Qwen3-8B encoder |
| Paper tooling | Evidence ledger, frozen figure renderers, LaTeX build |

All computation ran locally on an M2 Pro at batch size one, with $0 cloud
spend. Local throughput was about 17–23 tokens/s. This throughput, more than
any scientific choice, kept every study small: the 800-response repeat panel
took 8.4 hours.

### 2.2 Study sequence

| Period | Studies | Result |
|---|---|---|
| Sep 9–13 (`master`) | Smoke, pilot v1 | Thinking looked 17 points worse; caused by 256-token answer truncation |
| Sep 9–10 (`research/pilot-v2`) | Protocol v2 pilot | Direct 83.5%, thinking 93.0%, oracle 96%, confidence AUROC .83; recommended adding MATH |
| Sep 13–22 (`research/router-studies`) | Calibration, question-only routers, stronger routers, continuation router, power analysis, 3,100-question confirmation (prepared, never run) | Question-only routers did not beat cost-matched random; continuation router vs confidence +.008 [−.020, +.044], inconclusive |
| Oct 1–7 (`codex/research-data-efficiency`) | Protocol reconciliation and bridge, parser v7, 50-question repeat panel (800 responses), CPU/neural/CLM controls, two-solver panel, 0.6B pilot, fresh 228-question sparse guard test, 1.7B cap study | Primary learner fails 4/5 criteria; every control fails; 0.6B has more opportunities than 1.7B; guard and cap follow-ups show no supported gain |
| Oct 8–28 (`codex/confidence-acquisition-plan`) | Novelty/literature review, G0 prior-art review, G1 synthetic acquisition study, manuscript v0.1 to v0.3, six revision passes, figures, LaTeX | G1 fails all four primary contrasts, so the acquisition recipe is closed; paper drafted and revised |

The four studies reported in the paper charged about 1.2 million tokens in
total.

### 2.3 Strengths worth keeping

- Explicit decision and cost contract. Escalation pays for both calls.
- Question-grouped evaluation, with held-out questions excluded from fitting.
- Pre-specified criteria with failures retained, plus independent
  verification of every reported number.
- Reference answers opened only after collection completed; sealed splits
  never touched.
- Complete provenance: commit pins, hashes, deviations.

These qualities are rarer in student work than in published work. They are
also a selling point for an artifact or reproducibility-focused venue.

## 3. Branch analysis

| Branch | Commits | Relation to current branch | Unique content |
|---|---:|---|---|
| `master` | 2 | Ancestor (0 behind, 73 ahead) | None |
| `research/router-studies` | 4 | Ancestor (0 behind, 71 ahead) | None |
| `research/pilot-v2` | 10 | **Side branch**: 9 commits never merged | `docs/pilot-v2-report.md`, `docs/pilot-v2-prescreen.md`, `docs/project-status.md`, `configs/pilot_v2.yaml`, `configs/smoke_v2.yaml`, `src/reasoning_budget/analysis.py` |
| `codex/research-data-efficiency` | 59 | Ancestor (0 behind, 16 ahead) | None |
| `codex/confidence-acquisition-plan` | 75 | **Current; superset of all others except the pilot-v2 files** | G0/G1, manuscript, reviews, figures, LaTeX |

Pilot-v2's backend fixes were re-implemented in the protocol reconciliation
(`eabcbf3`, numeric-v5 and `qwen3-boxed-budget-v3`). Its results used a
different protocol (4,096/1,024 caps, model-card prompt) and are not
interchangeable with later studies.

Recommended housekeeping (needs your approval; none of it is done here):

1. Tag the old tips before any cleanup, for example `archive/pilot-v2` and
   `archive/router-studies`.
2. Copy the three pilot-v2 documents into a history folder, such as
   `docs/history/pilot-v2/`, so the main line holds the complete record.
3. Fast-forward `master` to `codex/confidence-acquisition-plan`, or merge it
   through a pull request. `master` is a direct ancestor, so no conflicts
   are possible. Anyone following a code link from the paper will otherwise
   land on the September 13 snapshot.
4. Before making the repository public, move the 74 KB agent log in
   `AGENTS.md` (which contains local machine paths) to a history file. Then
   write a short human README for the paper.
5. **Back up `artifacts/` from the Mac now.** The raw responses and score
   caches behind every reported number exist only in that ignored directory.
   If it is lost, the paper cannot be verified or released.

## 4. What the research shows, in plain terms

On GSM8K with Qwen3-1.7B, the direct mode is already right about 90% of the
time, and thinking adds about 5 points. In 400 sampled pairs, thinking
rescues 30 wrong drafts and breaks 10 right ones. A router that knew the
outcomes in hindsight would reach 97.0%: (348 + 10 + 30)/400, from the
paper's Figure 1 counts. The four-draw confidence threshold reaches 92.75% at
628 tokens per question.

Every learned router (Ridge, PCA, compact contrastive heads, released CLM)
lost utility relative to confidence on the same 50 questions. With Qwen3-0.6B,
direct accuracy falls to 62% and confidence routing helps substantially
(+.153 utility). With 1.7B, confidence is slightly worse than always
accepting the direct answer (−.031). The fresh guard test and the cap study
each produced at most one rescue.

The honest scientific reading is: **for a strong-enough small hybrid model on
an easy dataset, there are few rescue opportunities, and the cheap confidence
signal already captures most of the value that the tested learners can find.**
This is a coherent finding. It needs (a) the right prior work to interpret
it, and (b) more data or a harder setting to be convincing.

## 5. The paper today

- File: `papers/thinking-selection/manuscript.md` v0.3. LaTeX and PDF:
  `papers/thinking-selection/latex-v2/`.
- Type: empirical study with negative primary results. It is **not** a review
  paper. The 2026-10-08 publication plan considered a survey separately and
  noted that TMLR no longer accepts surveys from 2026-09-01.
- Previous AI-assisted reviews (critical review, R1–R6, author assessment,
  legibility critique) already fixed numerical consistency, interval wording,
  sparse-test interpretation, DART overlap and figure legibility. Their own
  conclusion was that the paper is coherent but its novelty is modest. None
  of these reviews counts as human peer review.
- Pending: author names and affiliations, human endorsement, venue formatting,
  and public artifact release.

## 6. Gaps for publication, ranked

### 6.1 Critical: the closest prior work is missing

The decision studied (pay for a cheap draft, then accept it or escalate to an
expensive model) is a **two-stage cascade**. The cascade-deferral literature
is absent from the manuscript, its bibliography and the repository's
literature notes:

- Jitkrittum et al., *When Does Confidence-Based Cascade Deferral Suffice?*,
  NeurIPS 2023 ([arXiv:2307.02764](https://arxiv.org/abs/2307.02764)). They
  characterize the optimal deferral rule and show that learned post-hoc
  deferral beats confidence mainly when the second model specializes, labels
  are noisy, or the distribution shifts. This is almost exactly the paper's
  research question.
- Gupta et al., *Language Model Cascades: Token-Level Uncertainty and Beyond*,
  ICLR 2024 ([proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/file/11f5520daf9132775e8604e89f53925a-Paper-Conference.pdf)).
  They show that **mean sequence log-probability**, the paper's confidence
  feature, suffers from length bias. They also show that learned deferral on
  token-level quantiles outperforms it.

A reviewer in this area will cite both immediately. Other relevant, unverified
candidates to check before citing: FrugalGPT (Chen, Zaharia and Zou, 2023);
AutoMix (2023/24); LLM cascades with mixture-of-thought consistency (Yue et
al., ICLR 2024); RouteLLM (Ong et al., 2024); Hybrid LLM (Ding et al., ICLR
2024); test-time compute scaling (Snell et al., 2024); budget forcing in s1
(Muennighoff et al., 2025) and L1 (Aggarwal and Welleck, 2025) for the cap
study; overthinking (Chen et al., 2024); GSM1k contamination (Zhang et al.,
2024) for the pretraining-exposure limitation; and evaluation statistics
(Miller, 2024, *Adding Error Bars to Evals*; Bates, Hastie and Tibshirani on
cross-validation intervals; Nadeau and Bengio, 2003). Only 13 works are
cited now. A workshop paper typically cites 25–40.

**Why this helps:** the cascade lens turns "our routers failed" into a testable
statement. The "large model" here is the *same* model in thinking mode, so it
is not a specialist, and the errors are strongly shared (only 40 of 400
pairs disagree). Theory predicts confidence should be hard to beat in exactly
this regime. The 0.6B versus 1.7B contrast then shows how the opportunity rate
changes the picture.

### 6.2 Critical: the central evidence is small, and the dataset is near ceiling

The main panel has 50 questions and 40 discordant pairs. The primary interval
upper bound is −.000635, essentially touching zero. The project's own power
analysis needed about 2,010 question groups to detect +.01. GSM8K at 1.7B
leaves very little to route, as the September pilot-v2 report already warned
when it recommended adding a harder numeric set (the Qwen3 report suggests
about a 20-point thinking gap on MATH-500 for this size). Reviewers will
attribute the null result to the ceiling and the sample size, not to the
routers.

The bottleneck was compute: batch-one local inference at about 20 tokens/s.
The 1,200-question acquisition pool, 200 validation questions and 2,000 sealed
confirmation questions are already frozen and unused. That is enough for a
properly powered test once generation is batched (Phase 5).

### 6.3 Major: one operating point, no curves

Every result is utility at λ = .05. Cascade and routing papers report
**accuracy-versus-cost (deferral) curves** for every policy, with always-direct,
always-think, cost-matched random and the hindsight oracle as reference
points. A single λ makes the conclusions depend on one operating point. All
the numbers needed for the curves already exist in cached scores, so this is
a cheap CPU analysis.

### 6.4 Major: standard baselines are missing

The paper compares mostly its own learner families with mean-log-probability
confidence. Missing baselines:

| Baseline | Why reviewers expect it | Feasible with existing data? |
|---|---|---|
| Token-level confidence (min, quantiles) with a threshold or learned post-hoc deferral (Gupta et al.) | Direct prior method; addresses length bias | Yes. Recompute per-token log-probs by teacher-forcing the cached direct drafts (forward passes only, about 1,000 drafts). Records store text, not token IDs, so check that re-tokenization reproduces `answer_tokens` |
| Draft agreement (accept if two drafts agree; DART-style) | Closest adaptive-thinking method | Approximately. The repeat panel has eight direct draws per question, so the cost of a second draft can be simulated. Label it an adaptation, not DART |
| Cost-matched random, hindsight oracle | Reference points for any curve | Yes |
| Earlier September routers (question-only, continuation) | Consistent prior evidence that is currently unused | Yes, as an appendix under its different protocol |

### 6.5 Major: the writing reads like an audit report

The current text hedges almost every sentence. It uses internal vocabulary
("A4→B4", "full8", "v7 sidecar", "screen", "frozen", "progression criteria",
"eligibility mask") and spends more words on what is not claimed than on what
is found. The legibility critique of v0.2 noted that the first result arrived
on PDF page 7, and v0.3 is still dense. At 24 pages it is too long for a workshop (usually 4–8 pages plus
appendix).

The text was also largely drafted by AI agents. Venues require that the
authors write and verify the paper and disclose AI assistance. Reviewers
increasingly notice agent-style prose. The fix is a rewrite in your own words:
a crisp title and claim, one consolidated limitations section, and the long
v0.3 kept as the technical report or thesis chapter.

### 6.6 Moderate: intervals omit refit variance

All repeat-study intervals hold fitted policies fixed. The paper says so
honestly, but reviewers will ask for uncertainty that includes refitting.
Ridge fits on 40 questions take milliseconds, so repeated cross-fitting with
several fold seeds, or a bootstrap that refits on each resample, is cheap.
Report it next to the frozen intervals; do not replace them.

### 6.7 Moderate: no human check of the scorer

Correctness is defined by the numeric-v7 parser alone; the human audit was
waived on 2026-09-18. A small blind audit would answer a near-certain reviewer
question: about 200 responses, covering all discordant pairs plus a random
sample, ideally with a second rater for Cohen's kappa. It needs a few hours
of your time. It reverses an earlier waiver, so it is your decision.

### 6.8 Moderate: release and reproducibility are incomplete

Code is on GitHub, but responses and scores are local only. A public
release needs:
- a dataset archive (Zenodo or Hugging Face) of responses and score caches;
- license checks (GSM8K is MIT and Qwen3 is Apache-2.0; check the CLM release
  terms);
- removal of local paths;
- one command that reproduces every table from cached scores.

### 6.9 Required before any submission: authorship and AI disclosure

Agree on authors with your supervisor and check your institution's rules on
AI-assisted writing. Describe the AI assistance in the venue's required form.
The current declarations section says this but leaves it unfilled. Do not
present the AI review passes as independent review.

## 7. Venue options

Check each call's current dates and page limits yourself; none is selected
here.

| Route | Fit | Needs |
|---|---|---|
| arXiv preprint | Any time; check whether your category requires endorsement for first-time submitters | Phases 1–4 |
| Negative-results workshop (for example *Insights from Negative Results in NLP*, *I Can't Believe It's Not Better*) or a student research workshop | Good fit for the existing data once reframed | Phases 1–4 |
| Efficient-reasoning or test-time-compute workshop at a major conference | Good fit | Phases 1–4 |
| TMLR | Values well-supported claims over novelty; a powered null with equivalence bounds fits | Phases 1–5 |
| Main conference (ACL/EMNLP/NeurIPS) | Unlikely without a new method or much broader evidence | Beyond this plan |

## 8. Step-by-step plan

Effort figures are rough estimates in focused working days, not promises.
Following the repository's own discipline, write and commit a short analysis
plan before each new analysis in Phases 2, 3 and 5. Report every result,
including unfavorable ones.

### Phase 0: Decide and secure (1–2 days)

1. Back up `artifacts/` (responses, scores, journals) from the Mac to two
   places.
2. Meet your supervisor. Settle authorship, affiliation, the AI-use policy,
   and target A (workshop and arXiv) versus B (TMLR).
3. Approve the branch housekeeping in Section 3. Then run
   `uv run --locked pytest` once on the Mac to confirm the suite still passes.

### Phase 1: Reframe around cascade deferral (3–5 days)

Status 2026-10-29: steps 5–6 done in manuscript v0.4; step 4 done at
abstract level only, because full texts were blocked. See the
[reframing record](../papers/thinking-selection/cascade-reframing-2026-10-29.md).


4. Read Jitkrittum et al. 2023 and Gupta et al. 2024 in full. Then verify and
   read the other candidates in Section 6.1, and add only what you have read.
5. Restate the contribution in one sentence. For example: *in hybrid
   reasoning models, escalation to thinking is a same-model cascade; with
   Qwen3 on GSM8K, cheap confidence deferral was not beaten by any tested
   learned deferral rule, consistent with theory for non-specialist second
   stages, and the value of routing depends strongly on solver strength.*
6. Pick a title that states the finding, and list at most three
   contributions. Recast Related Work around cascades first, adaptive
   thinking second, and routing evaluation third.

### Phase 2: Cached-data analyses, no new generation (4–7 days, CPU)

Status 2026-10-30: the confidence–gain shape check is complete; see its
[results](confidence-gain-shape-results.md). Steps 7–11 remain.


7. Draw accuracy-versus-tokens curves for all repeat-panel and two-solver
   policies, with always-direct, always-think, cost-matched random and the
   hindsight oracle. Keep λ = .05 as the primary point.
8. Add refit-inclusive uncertainty (Section 6.6) beside the original
   intervals.
9. Recompute token-level log-probs for the cached direct drafts and evaluate
   Gupta-style quantile thresholds and one learned post-hoc deferral rule,
   using the same folds and halves.
10. Evaluate a simulated two-draft agreement baseline on the repeat panel,
    charging the second draft.
11. Add an appendix table of the September studies, labeled with their
    different protocol.

Decision gate: if a Phase 2 baseline beats confidence on the reused panel,
report it as exploratory and make it the single pre-registered candidate for
Phase 5. Do not claim it as a result.

### Phase 3: Human scoring audit (1–2 days)

12. Blind-audit about 200 stratified responses. Report agreement with v7,
    and kappa if a second rater joins. Record it as a deliberate deviation
    from the earlier waiver.

### Phase 4: Write and release the short paper, milestone A (5–8 days)

13. Write a 6–8 page version in your own words: introduction and claim,
    setup, curves and main table, why (opportunity rate, oracle gap,
    0.6B vs 1.7B), related work, limitations. Move the guard, cap and CLM
    details to the appendix. Keep v0.3 as the long report or thesis chapter.
14. Get supervisor and peer feedback; revise.
15. Prepare the release: public repository, dataset archive with DOI, a
    reproduce-from-cache command, license notes.
16. Post to arXiv and submit to the chosen workshop.

### Phase 5 (optional, for TMLR): one powered prospective confirmation (3–5 weeks)

17. Implement the batched vLLM backend that has been planned since September.
    Run it on the free Kaggle GPU (verify the current GPU types and weekly
    quota). Check a small distributional bridge against the existing backend;
    token identity is not expected, so treat it as a new protocol version.
18. Pre-register: the confidence baseline versus at most one frozen candidate
    from Phase 2, at λ = .05, with an equivalence/superiority margin of ±.01
    (two one-sided tests) and the curve as a secondary endpoint.
    - Training: the frozen 1,200-question acquisition pool.
    - Test: the 2,000 sealed confirmation questions, which give roughly ±.006
      precision under the project's SD = .16 assumption.
19. Add a harder dataset with a larger thinking gap, such as the numeric
    subset of MATH (training split to fit, MATH-500 numeric to test). The
    current numeric scorer works for that subset. MATH thinking traces are
    much longer, so calibrate a larger reasoning cap (for example 4k–8k) on a
    small pilot first. Optionally add Qwen3-4B.
20. Upload questions only to Kaggle. Fetch reference answers only after the
    full collection is complete, as in earlier studies. A rough generation
    estimate is 10–20 million tokens, depending on draws and the MATH share.
    That is a few GPU-hours with batching (measure throughput in a pilot),
    versus one to two weeks of continuous local running.
21. Analyze exactly as pre-registered. A tight null result and a confirmed
    effect both strengthen the paper. Then submit the extended version.

### Do not

- Do not reopen the closed searches (G1 acquisition recipe, the 50-question
  model search, CLM fine-tuning), and do not tune on the 50-question panel to
  get a positive result.
- Do not touch the official 500-question test split unless a final,
  pre-registered evaluation calls for it.
- Do not submit the same results to two archival venues at once.

## 9. Open decisions for you

1. Target A only, or A then B?
2. Reinstate a small human scoring audit (reverses the 2026-09-18 waiver)?
3. Use the free Kaggle GPU for Phase 5 (requires building the vLLM backend)?
4. Who are the authors, and does the supervisor co-author?
5. Approve the branch housekeeping, including fast-forwarding `master`?
