# Research repository implementation checklist

**Active roadmap, 2026-10-01:** [data-efficient trace acquisition](docs/research-roadmap.md).
The historical milestone decisions below remain an execution record. The new
roadmap governs current scope, phase gates, and the $100 cloud allocation.
Work continues on `codex/research-data-efficiency`; see the
[Phase 1 evidence-repair record](docs/phase-1-evidence-repair.md).

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
