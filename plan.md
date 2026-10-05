# Research repository implementation checklist

**Active roadmap, 2026-10-03:** [data-efficient trace acquisition](docs/research-roadmap.md).
The historical milestone decisions below remain an execution record. The new
roadmap governs current scope, phase gates, and the $100 cloud allocation.
Work continues on `codex/research-data-efficiency`; see the
[Phase 1 evidence-repair record](docs/phase-1-evidence-repair.md).
The [Phase 2 results](docs/phase-2-repeat-results.md) stop acquisition scaling
after four failed progression gates. The bounded parser, CPU capacity/calibration
and representation/objective studies are now complete; both router promotion
screens failed. [Results](docs/phase-2-router-feasibility-results.md).
The [October contrastive-router review](docs/contrastive-router-review-2026-10-02.md)
defines the earlier design. Released CLM and a fresh signal test remain
conditional; next is a prospective broader-study design/power review.

## Scope and first deliverable

Implement Milestones A–C in this first pass. Run 10 arithmetic questions through
Qwen3-1.7B in direct and thinking modes, save and score 20 responses, then inspect
them before running a resumable 100-question GSM8K pilot with two samples per mode.
Target: M2 Pro, 16 GB shared memory; explicit CUDA support for later experiments.

## A — Bootstrap and offline pipeline

- [x] Initialize Git, Python 3.11 / uv project, local environment, dependency lock.
- [x] Add setup documentation and ignore environments, models, data, and traces.
- [x] Implement strict YAML configuration and `rb doctor`.
- [x] Add 10 arithmetic fixtures with separate scoring-only answers.
- [x] Test numeric parsing and scoring with fabricated responses offline.

## B — Real local inference

- [x] Load Qwen3-1.7B once per invocation; batch size one, FP16, explicit device.
- [x] Use checkpoint chat template and explicit thinking setting; pin revisions.
- [x] Direct: temperature 0.7, top-p 0.8, top-k 20, 256 answer tokens.
- [x] Thinking: temperature 0.6, top-p 0.95, top-k 20, 2,048 reasoning tokens,
      then 256 answer tokens; force closure at reasoning limit and record overhead.
- [x] Save raw text, separated reasoning/answer, token counts, time, and termination.
- [x] Complete and inspect 20 real smoke records; freeze tested environment.

## C — Resumable pilot

- [x] Freeze disjoint GSM8K splits: 100 pilot, 400 controller training,
      100 validation from train, and 500 from official test; reject duplicates.
- [x] Stable job seeds and identities covering content, revisions, template,
      decoding, precision, backend, and software configuration.
- [x] Atomic records, verified resume, explicit failures and retries.
- [x] Enforce cumulative token reservations and elapsed-time limits.
- [x] Report accuracy, parsing failures, forced closure, truncation, tokens,
      runtime, question-level bootstrap intervals, and projected cost.
- [x] Run 400 pilot generations after smoke inspection.
- [x] Manually audit at least 50 real pilot scores before accepting the report.

## Scientific integrity tests

- [x] Integers, decimals, fractions, negatives, boxes, conflicts, missing and
      incomplete answers; never choose a candidate using the gold label.
- [x] Natural reasoning closure, forced closure, early EOS, answer truncation,
      timeouts, and distinct token accounting using a fake model.
- [x] Split overlap / normalized duplicates; atomic resume, corrupted writes,
      configuration changes, duplicate prevention, and budgets across retries.
- [x] Paired policies and bootstrap resampling of whole questions.

## Compute controls

$100 overall ceiling: $10 pilot, $50 main experiments, $20 confirmation,
$20 reserve. No cloud launch before local cost estimates. Cloud billing remains
separate from token/time limits, which cannot stop idle instance charges.
Reserve maximum generated tokens before every job. Do not silently switch
device, precision, quantization, or inference engine. Report partial runs honestly.

## C.5 — Calibrate answer completion before training (active)

Accepted revision, 2026-09-14; rationale and related work in
[research next steps](docs/research-next-steps.md). Existing pilot stays immutable.

- [x] Freeze 25 pilot questions by a seeded hash of question identity, without
      using responses or labels; preserve original per-job generation seeds.
- [x] Compare answer allowances 256, 512, and 1,024 with two samples per mode;
      retain 2,048 reasoning tokens and all other generation settings.
- [x] Reuse the selected original 256-token records as the baseline. Generate
      actual 512/1,024-token runs with measured timing. Prefix reuse remains an
      optional optimization requiring explicit equivalence verification.
- [x] Report paired accuracy, truncation, tokens, runtime, forced closure, and
      retrospective sample-estimated routing headroom; show uncertainty and
      distinguish completed-run counts from successfully finished answers.
- [x] Implement tested `rb calibrate prepare/run/report/audit` commands, frozen
      arm configurations, matched-comparison checks, and resumable execution.
- [x] Inspect residual errors. A Markdown-heading scorer defect was corrected
      in numeric-v4; original pilot scores are unchanged. Prompt/extraction
      changes remain separate optional comparisons if full-pilot results warrant.
- [x] Select and freeze a protocol: 512 answer tokens and 2,048 reasoning tokens.
- [x] Finish the full 100-question confirmation, separately report the 75 not
      used for cap selection, and check mode complementarity before scaling D/E.
- [x] Prepare a stratified human-review artifact (50 calibration responses).
- [x] Resolve the human-review gate: explicitly waived by the user on
      2026-09-18 ("ignore the scoring audit"). The audit is not completed;
      preserve its pending worksheet and record the waiver in subsequent studies.

Keep the strict completion-aware scoring policy unchanged; version and audit
extraction bug fixes. Any additional answer-present
metric requires a predefined gold-independent rule and separate reporting. If
headroom remains small, use predeclared procedural/SVAMP diagnostics before
committing to large training acquisition; never select test cases by mode wins.

## D — Fixed baselines and a question-only controller

- [x] First learnability check: reuse the complete calibrated pilot in nested
      question-level cross-validation. Outer folds estimate performance; inner
      folds tune ridge alpha. Treat this as exploratory, since protocol selection
      already used pilot questions and the human audit remains pending.
- [x] Always-direct/thinking, exact expected random allocation, confidence
      routing, and explicitly labelled DART-SC-2 adaptation; count every draft
      and escalation. Save full curves, paired question intervals, and models.
- [ ] Complete the stronger published comparison: DART default third draft and
      budget-probing stage require additional traces and explicit adaptation
      settings. The two-draft cached comparison is not a full reproduction.
- [x] Frozen MiniLM plus question length/numeric/operator features; chunk long
      inputs; four standardized ridge predictors; validation-only alpha tuning
      over 0.1, 1, 10, 100; clipped accuracy/cost and accuracy-minus-cost routing.
- [x] With the audit gate waived, collect the common 32–50-question training seed set and
      disjoint validation responses. Freeze cost preferences and a learnability
      criterion before inspecting validation performance; do not choose a
      policy using the exploratory pilot's most favorable curve point.
- [ ] Confirm a reproducible accuracy–cost advantage over matched-cost random
      allocation before scaling adaptive acquisition. Failure of this small
      pilot check does not establish that routing is impossible.
- [ ] Keep architecture fixed across acquisition strategies and all response
      features confined to training acquisition. Keep official test data sealed.

## E — Acquire new questions, repetitions, or completions

- [ ] Begin every strategy with the same charged 32–50-question seed set; retain
      one pair on all 400 questions as an initialization ablation.
- [ ] Compare uniform, random, uncertainty-only, original regret-per-cost, and
      an explicitly documented relevant active-learning router baseline.
- [ ] Investigate expected reduction in downstream router regret per marginal
      training cost, choosing new questions, independent repeats, or completion
      of unfinished trajectories. Current regret/cost remains a heuristic
      baseline, not a claim of expected information gain or optimality.
- [ ] Test acquisition on synthetic observations first. Keep Beta(1,1) for
      independent fixed-budget correctness observations and 512 seeded posterior
      draws where applicable. Track correlated continuations by trajectory ID;
      never count one extended response as another independent Bernoulli trial.
- [ ] Use equal token ceilings, eight-independent-pair cap per question,
      periodic fitting, at least three acquisition seeds, and hidden-outcome
      replay. Generate the union of requested traces lazily and record actual
      cache cost separately. Charge prefix processing and continuation overhead.
- [ ] Report held-out utility versus acquired training tokens and tokens to a
      predefined utility target. Ablate completion information, continuation,
      cost normalization, and expected learning gain. Pair question bootstraps.

## F — Confirmation after the method demonstrates value

- [ ] SVAMP and procedural tasks; Qwen3-4B scale replication only after the main
      method works; another family only if needed for a broader claim and budget.
- [ ] Freeze controllers/cost preferences before test; generate manuscript
      figures and error summaries from saved records with one command.
- [ ] Two Qwen checkpoints do not establish cross-family generalization.

The earlier 37.78-hour estimate excludes the full eight-pair training cache:
400 questions × eight pairs = 6,400 responses, approximately 55 local hours at
the original pilot rates. Larger answer allowances can increase that estimate.

## Execution notes

Implementation and verification status will be recorded here as work completes.

- 2026-09-09: implemented the A–C CLI and offline pipeline; 59 tests pass.
  Python 3.11.13, PyTorch 2.14.0, Transformers 4.57.6. Git initialized; lock
  generated and verified. Real model revision:
  `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- GSM8K revision `740312add88f781978c0658806c59bc2815b9866`, seed 20260909;
  1,100 questions frozen with no normalized duplicates in this upstream revision.
- Initial calibration run `0d1ecd02bf9f50e2a9ee` was deliberately interrupted after
  7 completed responses: the prompt allowed verbose final answers. It remains a
  partial artifact. The shared prompt was clarified before the definitive smoke
  and pilot. Multiline final-answer boxes exposed a parser defect, fixed and
  regression-tested in `numeric-v2`.
- Definitive smoke `63d94a10f6f9b7d31309`: 20/20 records complete and individually
  inspected by Codex. Direct 10/10; thinking 7/10, with three answer truncations.
  No remaining scorer defects in the smoke audit. Total 8,615 generated tokens;
  390.1 seconds generation, 403.1 seconds including setup. MPS driver memory
  samples were approximately 4 GB. Pilot `af1f1e56c5d453bbfd5e` launched after review.
- 2026-09-13: verified the completed pilot: 400/400 successful generation records,
  400 attempts, 296,362 sampled tokens plus 60 inserted closure tokens, 3.438 hours
  including setup, and $0 cloud expenditure. All 30 forced closures and token
  counts verified against saved token IDs. Final scoring: direct 126/200 (63%),
  thinking 92/200 (46%); 63 and 105 answer truncations respectively.
- Inspected 50 stratified sampled responses and additional nontruncated errors;
  saved 51 formal audit reviews with no unresolved scorer defects. Added exact
  repeating-decimal parsing (`numeric-v3`), with no change in accuracy; 64 tests
  pass. Documented ambiguous upstream wording and the material answer-cap effect
  in [pilot results](docs/pilot-results.md). Milestones A–C are complete;
  Milestones D–F remain outside this pass.
- 2026-09-14: accepted C.5 and revised D–F; added calibration CLI and six-arm
  comparison reporting with unchanged numeric-v3 scoring. 69 tests pass.
  Frozen study: `artifacts/calibration/answer-cap-v1`, selection seed 20260914.
  Selected baseline: direct 30/50 correct, thinking 23/50; 15/27 truncated.
  Launched the sequential 512/1,024-token MPS calibration using cached weights;
  512-token run `d883ad976fc94dfe4cda`. Results remain provisional until both
  arms complete and are inspected. No cloud instance or expenditure introduced.
- Calibration completed: direct 72%, thinking 88% at both 512 and 1,024 tokens
  after the numeric-v4 heading fix. All token accounting and 200 cap-to-cap
  prefix comparisons verified; 161,729 new charged tokens, 1.823 local hours,
  $0 cloud. See [calibration results](docs/calibration-results.md).
- Added automatic confirmation reporting for the full pilot and its 25/75
  question partitions; froze `configs/pilot-calibrated.yaml` and launched
  `d00485799f1c8932bafa`. 76 tests pass. Human review remains pending;
  controller-training and official test generation have not started.
- 2026-09-17: confirmed full calibrated pilot completion: 400/400 responses,
  direct 84%, thinking 92%, answer truncation 1.5% in each mode, 310,586 charged
  tokens and 3.661 local hours. Human review still pending.
- Implemented `rb routing`, pinned CPU MiniLM, portable four-ridge fold models,
  five outer/four inner question folds, full baseline curves and paired
  descriptive intervals. Study `artifacts/routing/e1dd762743e19f93fb7d` reuses
  existing responses; zero new Qwen generations, GPU work, or cloud expense.
  Ridge has not shown a reliable gain over cost-matched random; the two-draft
  DART adaptation is promising but inconclusive. See
  [routing learnability](docs/routing-learnability.md). No official train,
  validation, or test generations have been launched for this step.
- Verification: 84 offline tests pass; Ruff and whitespace checks pass. Verified
  all source checksums and five disjoint evaluation folds, inspected the curve,
  and loaded a saved model to route a new question without an answer or response.
- 2026-09-18: user authorized the stronger-router implementation and waived the
  scoring-audit gate. Implemented portable retrieval/shrinkage and regret-weighted
  logistic routers with training-only PCA, plus an explicit utility-tuned ridge
  comparator. Retained the original four-ridge MSE baseline. 94 offline tests
  pass, including the complete fake-backend workflow and resume checks.
- Frozen disjoint study `artifacts/learnability/baselines-v1`: 50 training
  questions (one pair each); 50 tuning and 50 diagnostic validation questions
  (two pairs each). Predeclared nested training sizes 32/50, hyperparameter grids,
  and primary lambda=.05. Policies freeze before diagnostic generation; official
  test remains excluded. Generation started locally on MPS, training run
  `496228862bd511f17dd5`, with automatic subsequent stages, fitting and reporting.
  See [study tracking](docs/stronger-router-study.md). Actual results are pending.
- Completion, 2026-09-18: all 500 responses succeeded; policies froze before
  diagnostic generation, verified against timestamps and source/model checksums.
  Total acquisition 431,026 tokens, 5.064 local hours, $0 cloud. At primary
  lambda=.05, decision router improves utility over ridge by .039592 (paired
  interval [.006630,.077631]) but selects direct on 49/50 diagnostic questions
  and does not improve on always-direct or matched-cost random. The two-draft
  DART adaptation scores 95% at 759 tokens/question versus always-thinking 92%
  at 1,600. This is promising response-assisted development evidence; it does
  not establish question-only learnability, full-DART superiority, or novelty.
  Updated study analysis and next-step recommendation; no further GPU job started.
- Next accepted step, 2026-09-18: implement first-draft continuation routing,
  distinguishing predicted rescue, regression, and incremental token cost.
  Reuse the 100-question pilot for training and previous validation partitions
  for development tuning; reserve 100 unused training-pool questions permanently
  as a fresh diagnostic. Compare three actions against confidence gates,
  MiniLM/ridge, gain/cost regression, random policies and DART SC's third-draft
  branch. Freeze before new generation; retain the sealed official test.
  Full ReASC and DART SC-Budget, live latency, new seeds/tasks and Qwen3-4B remain
  later confirmation requirements. Generic confidence gating and optional
  information purchase are already prior work; novelty is conditional on a
  demonstrated distinction. See [continuation study](docs/continuation-study.md).
- Continuation implementation verified: 103 offline tests pass, including
  failure/resume, cost accounting, invalid agreement, future-response exclusion,
  frozen fitting and sealed-test rejection. Ruff and whitespace checks pass.
  Real models trained/frozen from 100 pilot and 100 prior validation questions;
  selected joint C=.1, cost alpha=10. Confirmed the deployed router accepts only
  the question and first response and the preceding study fingerprints remain
  valid. Frozen study `artifacts/probe/continuation-v1` reserves 100 fresh IDs.
- Launched bounded MPS collection with PID 92189: direct run
  `931c0e7a434abe265049` (300 responses), followed automatically by 200 thinking
  responses and reporting. Verified the first seven records completed without
  failure and model freezing preceded the first attempt. No diagnostic accuracy
  has been inspected; results and any novelty claim remain pending. No cloud
  spending. Tracking files are listed in the continuation-study document.
- 2026-09-19: continuation study complete, 500/500 successful final records on
  100 questions. At lambda=.05, joint routing scores 88% at 728 tokens/question;
  confidence continuation 86.5% at 591.8, gain ridge 89% at 877.3. Primary
  utility difference +.008188, bootstrap CI [-.020329,.044029]; inconclusive.
  Against gain ridge the utility difference is -.002536. Do not claim a novel
  statistical advantage or alter the completed study to create one.
- Added `rb power`: verified-source, whole-question paired power/sensitivity
  calculations. Approximate positive primary-effect confirmation needs 3,029
  fresh questions for 80% power, conditional on the noisy development estimate;
  estimated 122–139 local hours. Reserved unused non-test pool: 250 questions;
  official test remains sealed. The recommended next step is improving the
  method on development data before a costly confirmation. A fixed 3,100-question
  alternative, stopping/analysis rules and missing published comparisons are
  documented in [confirmation design](docs/confirmation-design.md). This is a
  draft, not a launched or registered confirmatory study.
- User selected freezing the current router for larger confirmation. Prepared
  `artifacts/confirmation/frozen-router-v1` on 2026-09-19: 3,100 fresh questions
  selected deterministically from 6,873 eligible cached upstream-training rows,
  excluding all 1,110 previously allocated IDs and normalized prompt matches.
  Original model/threshold bytes are unchanged; code snapshots and uv.lock are
  saved. Official test labels remain sealed, audit waiver retained.
- Implemented `rb confirm prepare|run|report|status`, 31 resumable batches,
  15,500-response fixed endpoint, and a gate preventing scoring/comparative
  analysis before full completion. Primary: two-sided paired t test, lambda=.05,
  alpha=.05; 10,000 whole-question bootstrap draws as a robustness interval.
  Four secondary tests use Holm adjustment with a positive-primary gate.
  113 offline tests and actual artifact checks passed. No refitting or generation
  was performed during preparation; GPU collection has not started. Expected
  local time 125–142 hours; ceilings 21.7M charged tokens/217 cumulative hours.
- 2026-09-23: completed a CPU-only nested question-fold comparison on the
  existing 100 pilot plus 100 validation questions. A shared first-correctness
  and action-conditional rescue/harm router reached 90.25% at 622 tokens per
  question, improving on refitted joint and gain-ridge models. Tuned confidence
  continuation also reached 90.25% at 589.4 tokens, so the new router did not
  clear the baseline at the preselected lambda=.05. A secondary high-accuracy
  region is exploratory, not a revised primary endpoint. The 100-question diagnostic and official test
  stayed out of fitting and evaluation. All 116 offline tests and Ruff passed;
  no GPU generation or cloud spend. See [router development results](docs/router-dev-results.md).
- 2026-10-01: started the accepted data-efficiency roadmap on
  `codex/research-data-efficiency`, based on `research/router-studies` at
  `15a4d2d`. Checkpointed the pre-existing research handoff at `1b67fbc`.
  Phase 1 checkpoint 1 corrected standalone always-thinking accounting and
  produced `artifacts/router-dev/shared-base-v2/` without replacing v1.
  Thinking remains 91.50% accurate at 1,430.69 rather than 1,654.47 tokens;
  all six other policies, settings, actions, and confidence curves are identical.
  Ten preserved artifact hashes and the legacy generation digest are unchanged.
  All 118 offline tests, Ruff, and diff checks passed; no solver generation,
  official-test scoring, or cloud/API expenditure. See the
  [Phase 1 evidence-repair record](docs/phase-1-evidence-repair.md).
- 2026-10-01: Phase 1 checkpoint 2 reconciled the parser as `numeric-v5` and
  generation as `qwen3-boxed-budget-v3`. Ported full EOS handling, separately
  recorded raw confidence, configurable closure, incremental accounting and
  consecutive-failure recovery. Added durable setup reservations and source
  provenance on sessions, attempts and responses; frozen-study readers reject
  mixed implementations. Preserved a detached legacy checkout at `6999eb5` for
  earlier study commands, without relaxing source/package/scorer guards.
  Versioned new score/report outputs preserve old artifacts and reject reuse of
  a scorer name with changed source. Independent agent review found numeric
  negation/alternative and response-provenance gaps; fixed them with adversarial
  and resume checks. All 195 offline tests, Ruff and whitespace checks passed.
  Verified 14 protected artifacts, 21 legacy source files, and 900 saved response
  records retain their hashes. Gold-free v4/v5 extraction had zero differences;
  pinned legacy probe/confirmation validation still succeeds. Cached MPS tokenizer
  inspection verified EOS `[151643, 151645]` and closure `[151668, 271]` without
  model weights. New bridge config is prepared; role manifests and real bridge
  generation remain next. Solver generations, gold/test access and cloud/API
  spend: zero. See [checkpoint 2](docs/phase-1-protocol-reconciliation.md).
- 2026-10-01: Phase 1 checkpoint 3 freezes all 4,023 unused GSM8K training
  questions into disjoint bridge/repeat/acquisition/validation/confirmation/reserve
  roles (25/50/1200/200/2000/548). Source revision and train Arrow SHA match the
  prior frozen source; allocation uses only IDs/prompts, seeded normalized hash
  order and all historical exclusions. Loading fails on source/inventory changes,
  index mismatch or reserved/external role swaps. No answer/outcome enters selection.
  Implemented a serial paired bridge: identical 25 questions and per-cell seeds,
  2 draws/mode, 100 responses/arm; each arm capped at 200k tokens and 4 hours.
  Legacy source/import/EOS guards, source archives, cumulative resume budgets,
  common v5 scoring and whole-question paired analysis freeze before generation.
  All 212 offline tests, Ruff and whitespace checks pass. Fourteen protected
  artifacts and 21 legacy Python sources retain their hashes. The allocation is
  now persistent; real bridge preparation/collection follows. Cloud spend $0.
  See [checkpoint 3](docs/phase-1-bridge.md).
- 2026-10-01: froze the actual paired bridge at source `bbcaac2` / legacy
  `6999eb5`, protocol payload `ed5f40e7…68066`, and started local collection.
  At 22:30:26 UTC, 49 legacy responses were complete with zero failures; outcomes
  remained locked. At the user's request, replaced chat polling with a detached
  background supervisor. It waits for collection locks, permits at most one
  automatic resume under unchanged cumulative limits, then writes the frozen
  report and runs an independent fixed-endpoint arithmetic/preservation audit.
  The incomplete-endpoint audit guard and script lint checks pass. Frozen package
  source/configuration are unchanged. No later experiment or cloud job is launched;
  report/gate review remains pending in the live artifact status. See
  [background operation](docs/phase-1-bridge.md).
- 2026-10-01: the paired bridge completed its fixed 200-response endpoint and
  background verification at 23:52:04 UTC (05:22:04 IST), without a retry or
  automatic resume. Each arm charges 81,593 tokens; 163,186 total, including
  inserted closures. Direct accuracy is 40/50 (80%) and thinking 47/50 (94%) in
  both arms; all 100 matched token sequences, terminations and extracted answers
  are identical. V3 finite raw direct confidence covers 50/50. All six
  predeclared engineering gates pass; the 800-response repeat-panel projection
  is 7.04 local hours excluding setup/retries. Independent arithmetic/bootstrap,
  common-v5 score-cache, budget and source checks pass; all 14 protected artifacts
  and 21 legacy sources retain their hashes. New EOS 151643 was not generated;
  one otherwise correct final answer is rejected for differing intermediate
  boxes under the frozen conservative scorer. Record this as a Phase 2 scoring
  preflight issue, preserve the bridge scores, and make no equivalence, causal
  speed or novelty claim. Checkpoint 3 is complete; next is a separate frozen
  repeat-panel protocol. Official test stays sealed, old confirmation unstarted,
  and cloud spend $0. See [completed bridge](docs/phase-1-bridge.md).
- 2026-10-01: completed the requested intermediate-box parser preflight on
  `codex/research-data-efficiency`. V6 (`715e0f0`) was rejected after a gold-free
  1,100-response check found 44 prose regressions; no real v6 gold scoring.
  V7 source/policy froze at `2607206` before its comparison: zero changes on 900
  historical responses and exactly two changes in the 200 bridge records, the
  same explicit final-180 case in both arms. Independent gold-free agent review
  agrees. All 341 tests (66 v7), Ruff and whitespace checks pass. Separate v7
  sensitivity, using only isolated bridge training gold, is 41/50 direct (82%)
  and 47/50 thinking (94%) per arm; all three remaining parse failures per arm
  are truncated and still rejected. Original v5 bridge scores/gates, 2,319
  protected files, 1,100 input records and 81,593 tokens per arm are unchanged.
  No new solver generation, shared/official-test gold access, confirmation start
  or cloud spend. This is a scoring repair on reused data, not novelty or a
  solver/router gain. Next: freeze a separate repeat-panel protocol pinning v7
  and its dependency digest, with the unchanged allocation and its own complete
  endpoint/gold lock. See [parser policy/results](docs/parser-preflight.md).
- 2026-10-01: prepared the separate Phase 2 repeat-panel protocol from `272403f`,
  protocol `8b01db2c…6f3c812`, on the same implementation branch. All 50 frozen
  repeat-role questions and 800 independent job IDs/seeds are pinned with v7,
  unchanged bridged inference settings, five 10-question folds and 50×387 pinned
  question features. Question data is gold-free (`gold_sha256: null`); only the
  completed endpoint permits selected-training-answer access and a versioned
  score sidecar. Added bounded resumable collection, source/role/package/data/
  feature guards, all-attempt/session provenance and cumulative budget checks.
  Nested question-fold analyses compare independent four-draw halves and 1/2/4
  supervision budgets, with eight draws secondary; inner tuning uses only the
  acquired training-half labels. Report standalone/post-direct gains distinctly,
  charge the sunk draft in total policy cost, and freeze conservative progression
  gates before outcomes. Agent review exposed configuration/formula/tuning and
  orphan-attempt issues; fixed before real preflight. All 363 tests (22 new),
  Ruff, whitespace, real tokenizer/feature preflight and 2,319-file preservation
  checks pass. Planned maximum reservations 1,229,600 tokens; local cumulative
  ceiling 1.4M tokens/12 hours, projected generation 7.04 hours excluding overhead.
  Status prepared, 0/800: generation unstarted, analysis locked, repeat reference
  answers and official test unopened, old confirmation unstarted, cloud spend $0.
  Next slice is local collection with a dedicated detached worker under this exact
  protocol. See [Phase 2 design and preparation](docs/phase-2-repeat-panel.md).
- 2026-10-01: started the user-authorized frozen Phase 2 local repeat collection
  on `codex/research-data-efficiency`. Committed the dedicated supervisor,
  independent endpoint verifier and nine operational tests at `3505a77`; the
  frozen generation package/config/source `272403f` and protocol `8b01db2c…6f3c812`
  are unchanged. All 363 existing tests plus the nine new checks pass, with Ruff
  and whitespace checks clean. Real pre-launch verification rejected the
  incomplete endpoint before score/report access and preserved all 2,319 originals.
  Supervisor PID 27132 started at 17:37:19 UTC (23:07:19 IST), collector 27339;
  cached Qwen weights loaded on MPS. At 17:40:49 UTC, independent launch proof
  recorded 2/800 completed, zero failures, both locks held and outcomes locked.
  Operational policy `dd242044…4b50be` pins both scripts, a 60-second heartbeat
  and a durable initial invocation plus at most one automatic resume. Original
  1.4M-token/12-hour cumulative collection limits remain authoritative; the
  supervisor's separate 14-hour wall ceiling includes post-collection analysis.
  It runs frozen analysis and independent accounting/policy/preservation
  verification only after all 800 responses complete and the collector exits,
  then stops regardless of the gates. Read the live status/log under
  `repeat-panel-v1/`; do not edit frozen sources or launch duplicate collectors.
  Later acquisition/confirmation/Jev/RL and cloud jobs are not started; official
  test stays sealed and old confirmation unstarted. See
  [Phase 2 collection and operation](docs/phase-2-repeat-panel.md).
- 2026-10-02: diagnosed and repaired the stopped repeat collection under the
  user's explicit instruction, keeping Docker running as requested. Initial and
  automatic-resume collectors each hit three consecutive timeouts, stopping at
  51/800 with six failed attempts. Median throughput fell from 17.34 to 0.0347
  tokens/s while sampled MPS allocation stayed near 3.456 GB. Docker's VM started
  13.07 seconds before the first failed attempt; this is suggestive of contention,
  not causal proof. Current synthetic MPS arithmetic is healthy. Frozen decoder,
  model, protocol, seeds, scorer and budgets are unchanged. Committed additive
  recovery scripts/tests/evidence at `3698102`: collector-scoped user-initiated
  activity, read-only telemetry, one manual invocation and first-failure stop.
  All 386 offline tests, native activity checks, Ruff and diff checks pass.
  Recovery supervisor/collector 4158/4365 are active under policy `3205df22…6f7e864`;
  old 2/2 journal, status and logs remain preserved, new journal is 1/1.
  Independent startup proof at 22:38:16 UTC (04:08:16 IST) records 59/800,
  zero failed current jobs, all three timed-out cells completed in 49.5/10.3/52.7
  seconds at 17–22 tokens/s and matching archived timeout prefixes. Original
  51 completed responses, 57 attempts, two setup sessions and all 2,319 protected
  files retain their hashes; three failed result rows are archived. Ledger is
  42,223 tokens / 1.909 cumulative hours including active reservations at this
  snapshot, within unchanged 1.4M/12-hour limits. Outcomes/reference answers
  remain locked until all 800 complete. Original confirmation unstarted,
  official test sealed, no later-phase/cloud launch. Use recovery-v1 status/log
  for current state. See [runtime diagnosis and recovery](docs/phase-2-runtime-recovery.md).

- 2026-10-02: completed Phase 2 at the full 800-response endpoint. Recovery
  supervisor recorded `complete_with_gate_failures` at 05:20:08 UTC (10:50:08 IST),
  with no further failed attempt. Cumulative ledger: 806 attempts (800 completed,
  six prior failures), three setup sessions, 644,519 tokens and 8.39463 hours,
  within unchanged 1.4M/12-hour limits. Docker stayed running. Both collection
  and supervisor locks are released; original 51 completed files/57 attempts/
  two sessions, archived failed rows, original worker artifacts and all 2,319
  protected originals retain hashes. Only the 50 selected training references
  were fetched after completion. Independent endpoint/accounting/policy audit
  passed; fresh CPU reconstruction exactly reproduced frozen statistics SHA
  `3eeb0129…ca40` from cached scores without reopening answers. Separate review
  proof is `recovery-v1/completion-review-verification.json`.
- 2026-10-02: reviewed the failed signal gate and committed isolated post-hoc
  diagnostic code at `51530f2` before execution. Seven synthetic tests and Ruff
  pass in addition to 386 existing checks from recovery. Primary report remains
  unchanged: four-draw combined-minus-training-selected baseline average
  −0.016204 (90% CI −0.033276 to −0.000635), split-half reproducibility interval
  crosses zero, both replica point comparisons fail, and full8 is −0.051630.
  Only informative-question count passes (14 ≥ 10). **Do not scale acquisition.**
  The separately versioned `repeat-diagnosis-v1/` finds 30 positive-gain pairs
  among 400, combined full8 capturing five in 174 escalations versus confidence
  16 in 58. Confidence is 92.5% accurate at 466.9 tokens, combined 89% at 799.5.
  Signed between-question variance is positive in this post-hoc decomposition,
  but oracle and same-question transfer use unavailable labels and cannot
  rescue the gate. Selection acquisition costs are reported separately.
  Added result tables, primary/post-hoc figures and a source-hash plotting
  recipe; updated roadmap to a bounded CPU-only conservative baseline/capacity
  feasibility stage before a separately locked fresh-question signal study.
  This is no new candidate fit, solver generation, reference access or cloud
  spend. No novelty, deployment speed or independent confirmation is claimed.
  Jev/RL and all later generation remain unstarted; official test sealed, old
  confirmation unstarted, human audit waiver unchanged. See [Phase 2 results](docs/phase-2-repeat-results.md).
- 2026-10-02: extended the checkpoint with gold-free syntax triage of all 27
  rejected repeat outputs (11 direct, 16 thinking). Five are incomplete; 16
  offer two different component quantities on one question. Five presentation
  candidates cover units/context/emphasis, and one terminal claim would broaden
  the explicit-final-marker policy. No references were opened, mathematical correctness assessed or
  new scores computed. Separate `repeat-parser-audit-v1/` envelopes pin
  the original inputs. Hypothetical fixed-action bounds, checked by exhaustive
  binary enumeration, leave four-draw average difference unchanged at −0.016204
  for the five presentation cases; full8 remains negative even at its upper
  bound −0.049130. These are not refitted-policy or new-scoring results. Updated
  next boundary: separate gold-free parser compatibility preflight before new
  learner fitting, with conservative incomplete/multi-answer rejection and
  adversarial tests; preserve frozen v7 and all primary labels/gates.
- 2026-10-02: completed a research/planning checkpoint prompted by the user's
  CLM article. Reviewed the official CLM repository, model card and relevant
  head/training/embedding code, MiniLM model card, RouterDC, Cost-Spectrum
  Contrastive Routing and SEMIROUTER, alongside the completed repeat results.
  An independent Sol agent reviewed the local statistical/code boundaries.
  Added [the contrastive-router review](docs/contrastive-router-review-2026-10-02.md)
  and revised the roadmap: bounded parser compatibility → confidence/capacity
  controls → matched question/draft representation and objective comparisons →
  optional frozen CLM probe with a matched 8B-backbone control → fresh locked
  signal test. CLM's encoder cost and binary action calibration are explicit;
  contrastive/cost-aware/sparse routing are acknowledged prior art. Candidate
  novelty remains a specific noise-aware supervision-acquisition method, subject
  to equal-budget evidence. No candidate fitting, parser implementation,
  generation, reference access, model download, API call or cloud spend; no
  frozen artifact/source/role changes. Docker remains running.

- 2026-10-03: completed the bounded 2a–2c milestone. Parser preflight checkpoint
  `b15e7de` repairs one balanced-bold final declaration across 1,900 outputs,
  preserving primary v7 labels. Before fitting, code/protocols were checkpointed
  at `1886bd4`. CPU grid completed 1,035 Ridge/75 PCA fits, selected average utility
  difference −0.014287 vs confidence (90% CI −0.025680 to −0.004425). The compact
  MiniLM pilot completed 600 neural/150 PCA fits: all eight family point differences
  negative, nested selected −0.033817 (CI −0.052515 to −0.017266). Both exploratory
  promotion screens fail; no expanded search, acquisition or CLM-8B launch.
  Local 400-draft embedding took 4.12s; 111 drafts were tail-truncated at the frozen
  256-token allowance. One optimizer seed and mean-vector fusion constrain claims.
  Full 500-test suite and two new independent accounting tests pass; read-only
  review recalculates 33,600 reported decisions and all 2,319 originals remain
  unchanged. New ignored artifacts freeze plans/reports/verification and chart
  exports. No new gold/references, solver generation, sealed access, cloud spend
  or Docker interruption. Next is a prospective design/power review of a broader
  signal study, with separate roles/protocol before any new generation.
  See [results and provenance](docs/phase-2-router-feasibility-results.md).

- 2026-10-03: user authorized continuing the research design and specified
  **local experiments only** for the released-CLM probe. Added a prospective
  [broader signal design](docs/broader-signal-design.md) with a question-level
  power/budget sensitivity script and meaningful arithmetic tests. Proposed
  64-question/two-solver diagnostic remains unallocated/unstarted; response-only
  reservations are 786,944 tokens, including forced closure. At hypothetical
  SD=.16, +.01 needs 2,010 question groups for 80% normal-approximation power.
  Added a separately frozen [synthetic local CLM preflight](docs/clm-local-preflight.md)
  using released heads plus pinned MLX 4-bit Qwen3-8B. Native Metal matrix check
  passed; dependencies are isolated from the frozen research environment.
  Public asset preparation is bounded to 5 GiB. Source/tests/protocol are
  checkpointed before model encoding; no cached study inputs enter this
  engineering endpoint. This authorization does not promote the failed MiniLM
  candidates or change primary gates. Docker stays running; cloud spend $0.
- 2026-10-03: source/protocol checkpoint `c06e2ff` completed local released-head
  engineering and power review. Downloaded 4,699,357,359 public asset bytes;
  all ten synthetic MLX encodings passed in one invocation, no retries, peak
  4.951 GiB, native worker wall 30.917s. Actual released heads load strictly and
  pass arithmetic; task-quality/full-precision transfer and live co-resident
  cost remain untested. Frozen report `53e2d76b…22f902`; do not restart.
  Power report `3d5a798c…5191a7` preserves all roles and leaves proposed 64 new
  questions unallocated: only 7.9% power for +.01 at hypothetical SD=.16;
  2,010 questions needed for 80%. The 786,944-token proposed budget is
  response-only; additional setup/retry/runtime protocol still needed.
  Fresh-process reviewer `a27df46e…418f2` checks 130 planning values plus cached
  synthetic vectors, resource and asset/input hashes; original verifier confirms
  all 800 responses and 2,319 originals unchanged. Full 514 offline tests plus
  two reviewer tests, Ruff and whitespace checks pass. The completed protocol
  JSON includes question-only snapshots; they were deserialized for integrity
  and cap metadata, not used in planning calculations (recorded clarification).
  No task-router fits, cached-draft CLM evaluation, new solver generation,
  reference/sealed access, cloud/API spending or Docker interruption. Next is
  one separately frozen cached CLM diagnostic with matched 8B supervised
  control and confidence; earlier negative grids stay closed. See
  [results and next boundary](docs/local-clm-and-power-results.md).
- 2026-10-03: user authorized the next cached released-CLM comparison. Added
  `scripts/repeat_clm_probe.py`, synthetic leakage/endpoint/accounting tests and
  [the frozen protocol](docs/phase-2-clm-probe-protocol.md). One fixed state/action
  recipe encodes all 400 cached direct drafts and two action vectors; the worker
  sees no labels/thinking text. Actual frozen heads, bounded scalar calibration,
  a supervised PCA8/Ridge control on identical 8B embeddings, and historical
  confidence are compared using unchanged v7/folds/independent halves.
  Maximum 450 Ridge/75 PCA fits; no auxiliary-statistics fusion, head finetuning,
  prompt search or new generation. Single encoder invocation, zero retries,
  40-minute wall cap; Docker stays running. Source/tests/protocol checkpoint
  precedes request/plan preparation and all real encoding/fitting. Preserve
  the earlier negative experiments, roles and preflight assets unchanged.
- 2026-10-03: corrected the documented CLM launcher after a direct-file import
  error before preparation created any plan/request/invocation. Use module
  execution (`python -m scripts.repeat_clm_probe`) so the repository's `scripts`
  namespace resolves. Source implementation, grid and data are unchanged;
  checkpoint the corrected command before actual preparation/encoding.
- 2026-10-03: completed the frozen cached released-CLM diagnostic from
  `5d40fa8` / launcher-protocol `ce1c7e6`, plan `270718aa…22a88c`. One native
  worker encodes 402/402 inputs in 575.67s, no retry, mean state 1.427s/p95
  2.244s, peak MLX 4.895 GiB, zero truncation. All 450 Ridge/75 PCA fits
  complete. Every exploratory screen fails: zero-shot −.026103 utility vs
  confidence, calibrated −.033262, raw-encoder control −.022617, nested selected
  −.028893. Zero-shot escalates 380/400; calibrated captures no positive gains
  in either four-draw direction. Keep confidence and close the tested recipe.
  Independent reviewer initially caught inherited per-condition bootstrap seed
  20261002; added a regression and preserved original report/source with a
  separate planned-20261006 interval sidecar for 75 policy intervals. Primary
  averaged intervals and every action/fit/point/screen remain unchanged.
  Verification `8d7392b5…88524e` checks 20,000 decisions and exact functional
  head logits; all 2,319 originals unchanged. Full 533 tests before launch
  plus four reviewer tests pass; graph PNG/PDF visually checked. All workers
  exited. No generation/references/sealed access, allocation change, cloud/API
  spend or Docker interruption. Report `5c05f655…07f117`; do not restart.
  Next is a separately frozen broader opportunity-rate diagnostic (64-question/
  two-solver proposal remains unallocated), not a fresh superiority test for
  these failed policies. See [results/deviation/provenance](docs/phase-2-clm-probe-results.md).
- 2026-10-03: user requested a deeper CLM architecture/novelty assessment and
  continued tests. Added a separately frozen descriptive cached-score audit
  (ranking vs confidence, independent-half association, fixed-policy cost
  sensitivity; no fitting/inference or new references), plus synthetic checks
  of binary contrastive decisions, duplicate-action hazards and regret targets.
  Reviewed the current official CLM code and RouterDC/CSCR/SEMIROUTER prior art;
  two-action compatibility and repeated supervision alone are not novelty.
  Added question-only reserve-child preparation and leakage/accounting tests
  for the proposed 64-question/two-solver opportunity diagnostic. Parent roles
  remain unchanged. Candidate 0.6B revision is identified, but its local asset/
  closure and new endpoint/resource/scoring protocol remain pending; collection
  stays locked. Full 555 offline tests, Ruff and whitespace checks pass before
  real audit calculations or child preparation. Source/test/protocol checkpoint
  precedes those exclusive additive artifacts. Docker remains running.
- 2026-10-03: the new descriptive audit launcher at `b2e4de8` failed at final
  sensitivity assembly because prior summaries use `mean_accuracy/mean_tokens`,
  not `accuracy/tokens`. No report was written and no model/reference/fitting call
  occurred. Preserve that source and plan `048687b3…350846`. Added a separate
  completion wrapper with schema regression tests and its own pre-calculation
  checkpoint/plan; rank functions/endpoints/bootstrap remain unchanged. The
  64-question child preparation and read-only verification succeeded with
  collection locked; the parent allocation is unchanged.
- 2026-10-03: completed the deeper [CLM research assessment](docs/clm-research-assessment-2026-10-03.md),
  revised problem-statement wording and conditional adaptation/novelty decision.
  Frozen cached-score audit completes through additive `a266621`, with original
  `b2e4de8` source/plan preserved. Report `d5010392…1a26f7` finds positive-gain
  AUROC .500450 for CLM vs .705045 for confidence; paired −.204595 interval
  [−.606961,+.195547] is imprecise. Fixed-action λ break-even .021691 does not
  change λ=.05 or any action. Independent automated review `57604e81…ad1710`
  reproduces six AUROCs, all three paired intervals and cost algebra. Full 557
  offline tests pass; all 2,319 protected originals remain unchanged.
  The 64-question reserve child is prepared/verified (`6d31e6e…50c230`), with
  parent unchanged, five grouped folds and gold deferred. No new generation,
  reference/sealed outcomes, 0.6B download, fitting, encoder execution or spend
  occurred. Next: separate pinned local 0.6B asset/closure preflight and full
  two-arm collection/scoring/analysis/global-budget protocol before collection.
  CLM remains conditional; tested recipe closed, acquisition/Jev/RL/confirmation
  stopped, Docker running. No publication contribution is established yet.
- 2026-10-04: implement the next additive local second-solver engineering
  preflight. Pin public Qwen3-0.6B revision, remote/local object hashes and isolated
  caches; one bounded download and one two-job synthetic MPS invocation. No
  diagnostic question enters the model. Sol review identified watchdog telemetry,
  final disk growth and restart-journal gaps; fix these before freeze and add
  synthetic failure tests. Real two-arm collection remains locked pending its
  separate full endpoint/scoring/analysis/global-budget protocol. Keep Docker
  running and the existing model/environment/study records unchanged.
- 2026-10-04: completed frozen local 0.6B preflight from `1e1e4d1`, plan
  `59827f88…99c04`. Nine pinned public assets total 1,519,207,673 bytes; one
  application download, 162.94 seconds, remote/local hashes pass. One MPS worker
  produces two valid synthetic outputs, including actual forced two-token
  closure; 42 charged tokens, 11.30 seconds parent wall, 2.06 GiB maximum sampled
  RSS. No retry. Completion payload `ce24395e…44e21c`; all 2,319 originals
  unchanged. Full 576 offline tests and pre-launch Sol review pass. No real
  question generation, reference/scoring/sealed access or cloud spend. Docker
  kept running. Next implement the separate two-arm collector with one global
  ledger, exact endpoint and cached-score analysis. Collection remains locked;
  synthetic timings are not full-budget throughput or task-quality evidence.
- 2026-10-04: user authorized the full two-solver diagnostic and conditional
  additional data. Implement additive `opportunity_panel_collect` and pure
  `opportunity_panel_analysis`: unchanged 64-question child, pinned 1.7B/0.6B,
  512 jobs with distinct per-arm seeds, one immutable global ledger, 1M tokens
  and 12-hour collection wall/charge ceiling, first-failure stop, at most one
  explicit runtime resume per arm. Native background supervisor has launch/
  startup/setup/job/finalization watchdogs and keeps Docker running. Both-arm
  full endpoint gates exactly selected training references and separate unchanged
  v7 scores. Mandatory post-warper confidence and secondary raw confidence use
  40 fixed scalar cutoffs; shared whole-question bootstrap is descriptive and
  conditional on fitted actions. Sol implementation and independent reviews
  identified/fixed launch and ledger read races, charge/attempt links, timestamp
  provenance, decoded-accounting boundaries and reference-cache safeguards.
  Freeze source/tests/protocol before native tokenizer-only preparation and
  background launch. No new reserve allocation or adaptive panel expansion;
  more data requires a separate prospective design after diagnostic evidence.
- 2026-10-04: native two-solver preparation completes from `a136f27`, protocol
  `d4e511ad…c1e44bc`; 623 tests and independent actual-job/asset audit pass.
  First background launch `d8788cf…e0e986` stops 0/512 before first response.
  Collector has only 26.98 monotonic seconds vs 1,057.29 wall seconds; power log
  proves maintenance sleeps of 106 and 929 seconds. The wall-clock watchdog
  counted sleep while the frozen generator's monotonic deadline did not.
  Preserve original journals/status/logs/setup/unresolved job: 512 tokens and
  619.55 charged seconds, with global wall age/sleep/gaps unchanged. No reference,
  score, new allocation or cloud spend. Docker kept running. Implement separate
  additive monotonic-watchdog/temporary-AC-sleep-guard recovery; use only the
  already permitted one 1.7B resume and 0.6B initial invocation. Do not edit
  frozen collector/protocol/configs or reset the budget. See the runtime record.
- 2026-10-05: separately reviewed additive recovery implementation passes all
  636 offline tests, including 13 recovery tests, Ruff and diff checks. Its
  monotonic anchors bind the original reservation and collector PID. One
  authenticated manual launch uses a temporary AC sleep guard, live progress,
  unchanged global wall/ledger limits and preserved failure classifications.
  Archive initial mutable status/active files; pin all existing immutable study
  bytes. Full endpoint still delegates to the original finalizer. Freeze these
  new sources/tests/runtime policy before preparation or native launch. No new
  questions, model responses or references entered this implementation check.
- 2026-10-05: additive recovery prepared from `efa72b2`, plan `614f5ea7…7392be`;
  independent actual-input audit passes (`69f66f1a…db961`). One native detached
  recovery launch `a0a21397…9777cb5` starts with original global budget and
  launch/invocation journals intact. First three responses complete; process
  idle/system-sleep assertions verified, no score/reference marker. Snapshot
  4,235 charged tokens and 5,742.27 seconds global wall age; preserved first
  failure included. Authoritative state is recovery-v1/status.json, not old
  background-status.json. Worker sequences 1.7B then0.6B and full-endpoint
  finalizer automatically, stopping on first failure. No extra allocation or
  cloud spend; review terminal diagnostic before a new prospective data plan.
- 2026-10-05 status checkpoint: recovery stops05:13:30UTC with budget failure,
  452/512 complete (1.7B256,0.6B196); 60 missing. Original wall age43,732.91s
  exceeds43,200s; ledger342,047tokens/14,701.20charged seconds, 454job reservations
  and two unresolved. No collection end/reference/score/report. Preserve all
  records; never reset/extend expired original budget or relaunch. Diagnose
  lost wall time read-only before separately freezing a completion protocol.
  No extra questions/cloud spend; no task-quality result yet.
- 2026-10-05: user authorized resuming the 60 missing responses, paused before
  any new launch, then resumed that work. Implement a separately bounded
  completion child; preserve the expired original run and its two unresolved
  charges. Only the 60 original 0.6B jobs (last15 questions,30direct/30thinking)
  are eligible, with unchanged seeds/backend/caps/v7/analysis. New wall/charged
  allowance4hours; original+new token ceiling1M, maximum planned combined
  reservation434,267. One child setup/invocation/launch; no automatic retry.
  Exact combined512 and exited collector gate selected64 training references.
  Child scores/report record the original budget failure as a deviation.
  Read-only power diagnosis found lid-close sleep and AC-to-battery transition;
  keep Mac open/onAC and Docker running. No new question allocation.
- Completion implementation review is finished. All643 offline tests (including
  seven new completion tests), Ruff and diff checks pass. Independent Sol review
  finds no launch blocker. Freeze the new source/test/protocol before preparing
  its exact parent inventory and starting one detached local worker.
- 2026-10-05: completion freezes at `b7c3b1e`; prepare plan `387e139c…a71b1d`,
  independent actual-parent/job audit `ef2e8882…e3b01` pass. Native detached
  launch `4606906c…826ecb` starts, supervisor14364/collector14373. Launch
  verification `1eba21d4…093935` confirms1/60settled new response,453/512combined,
 344897combinedcharges including active reservations, both process sleep guards
  and all2319parentstudy originals unchanged. References not opened; no extra
  allocation/spend. Use completion-v1/status.json; no relaunch. Worker completes
  exact60 then endpoint scoring/analysis, preserving original budget failure.
- 2026-10-06 status checkpoint: completion finishedOct5 18:14:48UTC. All512
  responses scored/analyzed;60new havezero failures/retries, allworkers exited.
  Combined384552tokens/16134.02chargedseconds; originalbudgetfailure/unresolved
  charges preserved. Report `f3f0d33c…ac6fd`; independentreview `b67d4e0a…5dfcc`
  checks artifacts/accounting and reproduces107fixed-action metrics/intervals
  without fitting/scoring/refs. 0.6Bpassesboth screens (24positiveq, confidence
  utilitygain+.152677);1.7Bfailsboth(4positiveq,gain−.030540). Preservecompleted
  study; nextprospective0.6B designreview withconfidencebaseline, noautomatic
  expansion/promotion. See two-solver results. Noextraquestions/cloudspend.
- 2026-10-06: user authorized the next 0.6B design/development step. Live
  question-only role/source/sibling audit confirms only opportunity64-v1 and
  484 unclaimed reserve rows; other roles remain unchanged. Rechecked primary
  RouterDC/CSCR/Thinkless and cost-aware acquisition prior art; novelty remains
  conditional on a specific equal-budget acquisition win, not this router.
  Implement one fixed alpha10 three-feature Ridge and matched confidence-only
  control,20 fits total across frozen question folds/opposite draws, plus frozen
  confidence and parser-rejection heuristic baselines. Keep lambda.05 and
  predeclare four further-study gates; no alpha/architecture search. Separate
  power/role planning proposes228 fresh groups only conditionally,700872response
  tokens, no allocation. All653 offline tests (ten new), Ruff and independent
  review pass. Freeze sources/test/protocol before preparation or fitting.
