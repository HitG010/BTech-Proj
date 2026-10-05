# Repository orientation

Snapshot checked 2026-10-03. Verify `git status --short --branch` and
`git worktree list` before relying on branch names or this snapshot.

- This worktree, `/Users/hiteshgupta/Documents/BTechProj`, is on
  `codex/research-data-efficiency`, created from `research/router-studies` at
  `15a4d2d`. The pre-existing documentation and shared-router work were
  checkpointed at `1b67fbc` before Phase 1 changes. Router studies 2–8 remain in
  its history; `master` at `0087b92` is not the current checkout.
- The sibling worktree `/Users/hiteshgupta/Documents/BTechProj-pilot-v2` is on
  `research/pilot-v2` at `6c7903c`. It was also clean. Its prompt, token caps,
  backend and scorer differ from the historical router-studies branch.
  `numeric-v3` and `numeric-v4` have different historical meanings. The active
  branch now uses `numeric-v5` and `qwen3-boxed-budget-v3`; the
  [protocol record](docs/phase-1-protocol-reconciliation.md) explains the merge.
  The real 25-question generation bridge is complete; historical generation
  protocols are still not interchangeable.
- Start with [the research map](docs/README.md) for study results, code layout,
  artifact paths and reading order. [The root README](README.md) covers setup and
  commands; [the plan](plan.md) is the milestone and execution log. Source is in
  `src/reasoning_budget/`, offline tests in `tests/`, configurations in
  `configs/`, and research notes in `docs/`.
- `artifacts/`, `.cache/`, `.python/` and `.venv/` are local and ignored by Git.
  The pilot-v2 worktree shares `.cache/`, `.python/` and `artifacts/runs/` with
  this worktree through symlinks. Preserve existing run records and frozen study
  identities. Its `artifacts/data/` is a separate directory.
- `artifacts/legacy/router-studies-6999eb5/` is a detached legacy checkout for
  frozen-study commands. Use its `src/` through `PYTHONPATH` from this root; the
  shared editable environment alone imports the current source. The new code
  correctly rejects legacy frozen studies. Checkpoint 2 verified
  195 tests; no new generation, gold/test access, or cloud spend in that checkpoint.
- The 3,100-question confirmation in
  `artifacts/confirmation/frozen-router-v1/` is prepared for the **unchanged**
  joint router; `status.json` says generation has not started. The user deferred
  its 125–142-hour local run to improve the router first. The official 500-test
  split is sealed. The human scoring audit was explicitly waived.
- The active [research roadmap](docs/research-roadmap.md) targets data-efficient
  acquisition, with protocol repair and supervision diagnosis before scaling.
  Jev/RL are conditional extensions. Do not treat generic RL, agreement, or
  cost-aware acquisition as an established novel contribution.
- The cached-trace CPU test is complete; see
  [router development results](docs/router-dev-results.md) and
  the corrected `artifacts/router-dev/shared-base-v2/report.md` (v1 preserved).
  The standalone-thinking cost was corrected from 1,654.47 to 1,430.69 tokens;
  all six other policies and the legacy generator are unchanged. On 200 reused development
  questions, the shared-correctness router improved over refitted joint and
  gain-ridge models, but at the preselected `λ=.05` tuned confidence matched its
  90.25% accuracy with fewer generated tokens (589.4 versus 622.0 per question).
  A higher-accuracy, low-penalty part of the curve is exploratory. This is not
  independent confirmation. Do not treat the prepared 3,100-question protocol
  as a test of the new router. Only 11 wrong direct-draft agreements exist in
  development, so selective verification remains a limited optional direction.
- Phase 1 checkpoint 3 freezes all new GSM8K roles in
  `artifacts/research/data-efficiency-v1/allocations/manifest.json`: 25 bridge,
  50 repeat, one 1,200-question acquisition pool, 200 validation, 2,000 new sealed
  confirmation, 548 reserve. Preparation reads question-only source rows; loading
  validates live inventory/source hashes, source index, exclusions and pool roles.
  The [paired bridge](docs/phase-1-bridge.md) is implemented with 100 responses per
  arm, common v5 scoring only after all 200 complete, and unchanged old code at
  `6999eb5`. Its pre-collection verification passed 212 offline tests. Collection
  from frozen `bbcaac2` is complete: 200/200 responses, zero failures/retries, all six engineering gates
  passed, and every matched cell has identical token sequences across protocols.
  Direct accuracy is 80%, thinking 94%; v3 raw direct confidence is finite on
  50/50 responses. Both arms charge 81,593 tokens. Independent endpoint
  arithmetic/provenance/preservation checks passed. The background supervisor
  recorded `complete` at 2026-09-30 23:52:04 UTC; report and verification paths
  are in `bridge-v1/background-status.json`. Do not restart the completed study
  or change frozen package sources/config. EOS `151643` was not emitted in this
  bridge; timing is not a causal speed comparison. The multiple-box
  scoring limitation is resolved by the separate parser preflight below. The
  subsequent 50-question repeat study is now complete with failed progression
  gates; see its result record below. Later phases remain pending. Cloud expenditure is $0.
- The [parser preflight](docs/parser-preflight.md) is complete. V6 was rejected
  for 44 gold-free prose regressions and is retained for provenance. Opt-in v7
  was frozen at `2607206`; its implementation digest is
  `c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964`.
  All 341 offline tests pass (66 v7 tests). Of 1,100 cached responses, only the
  same final-180 case in each bridge arm changes; 900 historical extracts are
  identical. Separate v7 sensitivity is 82% direct / 94% thinking, using only
  isolated 25-question bridge training gold. Primary bridge v5 remains 80%/94%;
  all 2,319 protected files and input records are unchanged. The ordinary CLI
  still uses v5. V7's opt-in scorer permits only complete frozen bridge arms or
  synthetic fixtures; real repeat scoring requires a new endpoint-locked Phase 2
  protocol pinning v7/dependencies and the unchanged allocation. No generation,
  historical shared/official-test gold access, confirmation start or cloud spend
  occurred in this preflight. Do not restart the bridge or edit frozen existing
  package files. Artifacts: `parser-v6-preflight-v1/` and `parser-v7-preflight-v1/`
  under `artifacts/research/data-efficiency-v1/`.
- Phase 2 [repeat-panel protocol](docs/phase-2-repeat-panel.md) is frozen
  from source `272403f`, protocol `8b01db2c…6f3c812`. It pins the unchanged
  allocation, 50 repeat questions, v7, all 800 independent jobs/seeds, 50×387
  question features and five 10-question folds. Preparation passed 363 tests
  (22 new repeat tests), with no repeat references or official-test gold opened.
  Maximum planned reservations are 1,229,600 tokens; cumulative local limits
  remain 1.4M tokens/12 hours including setup/retries. The question-only
  `data/repeat/` manifest still has `gold_sha256: null`; do not add a gold file
  or use ordinary `rb score` on it. Frozen sources/config/roles/features and
  attempt/setup timestamps are guarded. Only the full 800-response endpoint
  permitted fetching exactly the 50 selected upstream-training references for
  the separate v7 score sidecar. Future reviews use cached scores; do not call
  score/analyze merely to reproduce statistics, because score reopens references.
  All tuning used acquired training-half labels and question folds. The two
  four-draw halves supply independent-draw diagnostics; eight-draw labels have
  no independent same-question eight-draw replica.
- Phase 2 [runtime recovery](docs/phase-2-runtime-recovery.md) is complete.
  The original supervisor at `3505a77` stopped at 51/800 after six timeout
  attempts, exhausting its initial/one-resume journal (2/2). The policy/journal/
  status/log, all 51 completed responses, 57 attempts and two setup sessions are
  preserved; three failed result rows are archived under
  `recovery-v1/failed-results-before/`. Throughput fell from 17.34 to 0.0347
  tokens/s; Docker's VM started 13 seconds before the first failure. Correlation
  is not proven causality. The user explicitly chose to keep Docker running.
  Additive scripts frozen at `3698102` supplied one manual invocation (1/1),
  process-scoped macOS user-initiated activity, read-only telemetry and first-
  failure stop, without changing protocol/model/decoder/seeds/scorer/budgets.
  Do not stop Docker, edit pinned package/config/scripts, reset either journal
  or relaunch completed collectors. The authoritative terminal status is
  `repeat-panel-v1/recovery-v1/status.json`, **complete_with_gate_failures** at
  **2026-10-02 05:20:08 UTC**, not the original stopped `background-status.json`.
  Recovery policy digest:
  `3205df22e02694ea41f58fdbd1b66d56e01bc731c8173fa29eaa2ea7e6f7e864`.
  All 800 final responses completed, with no further failure during recovery.
  Full ledger: 806 attempts (800 completed/six earlier failures), three setup
  sessions, **644,519 tokens / 8.39463 cumulative hours**. Both collection and
  supervisor locks are released. All original recovery inputs/archived rows and
  2,319 protected originals are unchanged. `background-verification.json` and
  `recovery-v1/completion-review-verification.json` record accounting, preservation
  and exact fresh-CPU reproduction of the frozen statistics from cached scores.
- Phase 2 [results](docs/phase-2-repeat-results.md) **stop acquisition scaling**:
  four of five predeclared gates fail. Four-draw average combined-minus-training-
  selected-baseline utility is −0.016204 (90% CI −0.033276 to −0.000635);
  reproducibility's interval crosses zero and secondary full8 is −0.051630.
  Only informative question count passes (14 ≥ 10). Primary report payload is
  `e4d17cc5ab4e0d3ffd1b79d301a988537d43bd2379fd1a99243f1e2843dd6d56`.
  Separate post-hoc/development diagnosis code froze at `51530f2`, with seven
  synthetic tests plus 386 previously passing existing tests. Artifacts live in
  `repeat-diagnosis-v1/` (plan `ae71e727…00a5c87`, report `4278a314…9d9aedf`).
  It fits no candidate and reads no new references. Full8 combined escalates
  174 times, with 5 positive-gain/169 nonpositive decisions, versus confidence
  58 with 16/42. Confidence achieves 92.5% at 466.9 tokens; combined 89% at 799.5.
  Some repeated question-level structure remains, but hindsight or same-question
  label transfer is not deployable evidence or unseen-question generalization.
  Separate gold-free syntax triage in `repeat-parser-audit-v1/` found five
  presentation candidates, five incomplete outputs, 16 two-component answers
  on one question, and one unmarked terminal claim requiring broader policy.
  No mathematical correctness was assessed or label changed. Fixed-policy
  bounds cannot reverse the combined-minus-baseline comparison on these cases;
  this is not a result for refitted policies or unflagged scorer errors.
  Next is a separately versioned gold-free parser compatibility preflight;
  retain incomplete/multi-answer rejection, stress-test negation/alternatives/
  context/units, and never edit frozen v7 or replace the primary report. Then
  freeze a bounded CPU-only capacity/calibration grid around confidence,
  explicitly exploratory; it cannot change failed primary gates.
  Any new generation needs a separate frozen question-role/
  endpoint/analysis protocol and fresh signal evidence before scaling. Jev/RL,
  acquisition, validation and confirmation generation remain unstarted; official
  test sealed, old confirmation unstarted, human audit waived and cloud spend $0.
- The [October contrastive-router checkpoint](docs/contrastive-router-review-2026-10-02.md)
  revises the pending roadmap without running new experiments: 2a bounded
  gold-free parser compatibility (retain v7 if the candidate fails), 2b CPU
  confidence/capacity controls, 2c matched question/draft representation and
  supervised/contrastive objective controls, 2d optional resource-gated frozen
  CLM probe, 2e separately frozen fresh signal test. Current MiniLM already has
  contrastive pretraining; released CLM heads require Qwen3-8B last-token
  representations and cannot be attached to Qwen3-1.7B/MiniLM. Measure full
  router overhead and use a matched-backbone control. RouterDC, CSCR and
  SEMIROUTER restrict novelty claims. All new fitting remains exploratory on
  this panel; freeze grids, pair construction and training-fold/half boundaries
  before execution. No CLM download/API/training, new generation, role changes
  or sealed-label access is authorized by the review itself. Acquisition scaling
  and Jev/RL remain stopped pending fresh signal evidence. Docker stays running.
- Phases 2a–2c are now complete. The [parser compatibility preflight](docs/phase-2-parser-compatibility.md)
  froze one balanced-bold final-declaration wrapper: 56 fixtures, 1,900 outputs,
  one newly extracted scalar, zero accepted-answer regressions; v7/primary labels
  unchanged. Its script/tests/results checkpoint is `b15e7de`. The
  [bounded router experiments](docs/phase-2-router-feasibility-results.md) froze
  code/protocols at `1886bd4` before real fits. CPU: 1,035 Ridge/75 PCA fits;
  training-selected average four-draw difference vs confidence −0.014287
  (90% CI −0.025680 to −0.004425). Compact MiniLM representation/objective pilot:
  600 neural/150 PCA fits, all eight family average point differences negative;
  nested-selected −0.033817 (90% CI −0.052515 to −0.017266). Both screens fail.
  Draft features used tail-256 encoding; 111/400 truncated. One optimization
  seed and mean-vector fusion limit generalization. Full 500-test suite plus
  two independent accounting tests pass. New read-only review verified 33,600
  decisions and all 2,319 originals without refitting/scoring/references.
  Artifacts: `repeat-cpu-feasibility-v1/`, `repeat-contrastive-pilot-v1/` and
  `router-feasibility-review-v1/`. Preserve their plans/source/test/protocol pins
  and completed outputs; do not rerun the neural executor or expand the grid.
  CPU completed-run lookup returns cached results. No CLM-8B/API/new generation
  or sealed access occurred. Close this bounded reused-panel search; next is a
  prospective broader-signal design/power review under a separate protocol.
  Acquisition, CLM-8B, Jev/RL and fresh superiority testing remain unstarted;
  Docker running, cloud spend $0, original failed gates/roles unchanged.
- Latest user preference is **local experiments only**; Docker must stay running.
  The [local CLM/power checkpoint](docs/local-clm-and-power-results.md) follows
  2a–2c and supersedes their CLM-unstarted statement for engineering only.
  Source/tests/protocol froze at `c06e2ff`; full 514 offline tests plus two
  new independent-review tests pass. Public assets (4,699,357,359 bytes) and
  MLX 0.32.3 / mlx-lm 0.32.0 live in the separate ignored
  `clm-local-environment-v1/`, leaving `.venv` unchanged. The actual released
  heads plus pinned 4-bit Qwen3-8B passed all ten synthetic inputs in one
  invocation, zero retries: peak MLX 4.951 GiB, 512-token encoding about 2 s,
  2,047-token encoding about 8.2 s. No cached draft/label enters that endpoint.
  The native worker has exited; no collector or training worker is running.
  Frozen preflight plan `5364474e…ca7756`, report `53e2d76b…22f902`;
  do not alter its script/tests/protocol/asset inventory, reset its journal,
  redownload assets or restart the completed preflight. It verifies dimensions,
  repeatability and arithmetic, **not full-precision equivalence, task signal,
  calibration or co-resident solver/router latency**. RSS is separate from MLX
  allocation, not total unified-memory accounting. No router deployment claim.
  The prospective [broader signal design](docs/broader-signal-design.md) and
  power report `3d5a798c…5191a7` are complete. SD=.16 sensitivity requires 2,010
  question groups for +.01 at 80% power; proposed 64-question/two-solver panel
  remains diagnostic/unallocated/unstarted, with 786,944 response-only token
  reservations. Old protocol JSON was deserialized for integrity/cap metadata;
  its question-only snapshots were not used in calculations. See the result
  record's data-access clarification; no new questions, references or sealed
  outcomes were opened. Preserve the additive power `access-clarification.json`
  (`277b17fd…76f79c`) alongside the unchanged primary planning payload.
  The independent reviewer `a27df46e…418f2` checks 130
  power values and synthetic/resource/asset/input identities. All 2,319 originals
  are unchanged. Next: **one separately frozen matched-backbone cached CLM
  diagnostic**, keeping confidence, unchanged v7 labels and grouped independent
  halves; not another MiniLM search. New generation still needs a separate
  reserve-child-role/endpoint/analysis protocol. Acquisition, Jev/RL, MATH and
  confirmation stay unstarted; cloud/API spend $0, official test sealed.
- Phase 2d [cached released-CLM results](docs/phase-2-clm-probe-results.md) are
  complete, superseding the preceding task-quality-untested/next-probe boundary.
  Source/tests `5d40fa8`, launcher/protocol `ce1c7e6`, frozen plan
  `270718aa…22a88c`; report `5c05f655…07f117`. One local worker finished all
  400 direct-state plus two action encodings in 575.67 s, no retry, mean state
  1.427 s/p95 2.244 s, maximum 659 input tokens, zero truncation, peak MLX
  4.895 GiB. All 450 Ridge/75 PCA fits completed. Actual frozen heads were not
  finetuned. The matched control uses PCA8 on the same 8B embeddings; scalar
  CLM calibration and neither learned family include auxiliary draft statistics.
  Every screen fails: averaged deltas vs confidence zero-shot −.026103 (90% CI
  −.058826 to +.016513), calibrated −.033262 (−.053818 to −.015171), raw control
  −.022617 (−.043758 to −.004464), nested-selected −.028893. Calibrated minus
  raw −.010645. Zero-shot chooses thinking 380/400 times; secondary full8
  94.75% at 1,550.53 tokens vs confidence 92.5% at 466.88. The four-draw
  confidence comparator is different (92.75%/628.47); do not mix endpoints.
  Close this recipe; no adaptive prompt/fusion/finetuning search or deployment,
  acquisition/RL promotion follows. Quantized/full-precision equivalence,
  pretraining disjointness and live co-resident latency remain untested.
  Reporting deviation: imported CPU summary used bootstrap seed 20261002 for
  75 per-condition intervals. Preserve frozen code/report. The additive
  `repeat-clm-review-v1/conditional-intervals.protocol-seed.json`
  (`ea1c9226…faaaf6`) supplies planned-20261006 versions; use it for conditional
  intervals. Primary averaged intervals, points, actions, fits, selection and
  screens are unchanged. Independent verification `8d7392b5…88524e` checks
  20,000 decisions, boundaries, selection, costs, intervals and resource/input
  identities; functional head logits reproduce exactly. All 2,319 originals
  are preserved. Full 533 offline tests before launch plus four reviewer tests
  pass. Both native worker and analysis exited; no job remains running.
  Do not edit frozen probe script/tests/protocol or restart preparation/encoding/
  fitting; preserve requests, invocation, NPZ, logs and completed reports.
  Reviewer plotting recipe is `scripts/review_repeat_clm_probe.py`; PNG/PDF
  comparison was visually checked. Docker stayed running, cloud/API spend $0,
  no new solver response/reference/sealed access or role change occurred.
  Next is a separately frozen broader opportunity-rate diagnostic protocol
  (the proposed 64-question/two-solver panel is still unallocated/unstarted),
  not superiority confirmation of a failed policy. Acquisition, Jev/RL, MATH,
  confirmations remain stopped; official test stays sealed.
- The [deep CLM assessment](docs/clm-research-assessment-2026-10-03.md) and
  descriptive cached-score audit are complete. Source/test/protocol `b2e4de8`,
  base plan `048687b3…350846`. The first new launcher hit a cached-summary
  field error before writing its report; preserve it unchanged and **do not
  rerun its execute command**. Additive completion source `a266621`, plan
  `4e0a58e6…64ba29`, report `d5010392…1a26f7`, independent automated review
  `57604e81…ad1710` live in `clm-signal-audit-v1/completion-v1/`. They invoke
  no fitting, encoding, scoring/reference access or solver generation.
  Positive-gain AUROC is .500450 for CLM versus .705045 for negative confidence;
  paired difference −.204595 has 90% interval [−.606961,+.195547]. This is
  imprecise reused-data description, not proof of a population disadvantage.
  CLM chooses 380/400 and has 7.89% positive-gain precision. Preserve λ=.05;
  fixed-action break-even .021691 omits encoder cost and is not a new endpoint.
  Six AUROCs, all paired intervals and cost algebra were independently reproduced
  with scikit-learn. Full **557 offline tests** pass; 2,319 originals unchanged.
  Retain CLM as a conditional representation, not claimed novelty; current
  upstream choice training already deduplicates shared action texts. Neither
  contrastive routing nor repeated supervision alone is novel (RouterDC uses
  repeated solver samples). No renewed search/finetuning on the 50-question panel.
  Both audit analyses are finished; preserve sources/tests/protocols/plans/results.
- The [opportunity preparation](docs/opportunity-panel-preparation.md) supersedes
  the preceding unallocated-64 statement: `reserve-children/opportunity64-v1/`
  now contains a separately frozen **question-only child of 64 parent-reserve
  rows**, split `opportunity64`, seed 20261007, fold counts 13/13/13/13/12.
  Child payload `6d31e6e…50c230`, preparation plan `300bfbc…3ee10`; unchanged
  parent payload `c2b28b3d…d3a4fd`. Parent roles remain 548 reserve, with 64
  earmarked by this child and 484 unclaimed; audit sibling children before
  any other allocation. Source/index/exclusion/normalized-prompt checks and
  seven frozen preparation source hashes are independently verified. Dataset
  `gold_sha256` remains null and no gold file may be added. Do not rerun prepare;
  `python -m scripts.opportunity_panel_plan verify` is read-only. Preserve its
  script/tests/preparation doc and child artifacts. The candidate Qwen3-0.6B
  revision `c1899de289a04d12100db370d81485cdf75e47ca` is identified but not
  downloaded or tokenizer/closure verified. Generation is **unstarted/locked**.
  Next implement a separate additive local-asset preflight, then freeze both
  solver arms, independent seeds/jobs, unchanged prompt/caps/scorer, both-arm
  full endpoint before exactly selected training-reference access, analysis,
  and global setup/retry/token/time limits. Existing preparation is not a full
  collection protocol; its 786,944 token bound is response-only and assumes two
  closure tokens. The pure confidence/opportunity helpers have synthetic tests
  only; real use needs the new analysis protocol. This panel is diagnostic, not
  +.01 confirmation. Official test sealed, both confirmations/acquisition/Jev/RL
  unstarted, no worker running, Docker kept running, cloud/API spend $0.
- The [local second-solver preflight](docs/opportunity-solver-preflight-results.md)
  is complete and supersedes the preceding 0.6B-assets-unverified boundary.
  Frozen source/tests/protocol `1e1e4d1`, plan `59827f88…99c04`; nine pinned
  public files total 1,519,207,673 bytes and pass remote/local hashes. One bounded
  download and one synthetic MPS worker, zero application retries. Both modes
  pass, actual EOS `[151643,151645]`, closure `[151668,271]`, thinking forced
  closure observed, 42 charged synthetic tokens, largest sampled RSS 2.06 GiB.
  Report `ce24395e…44e21c`; all 2,319 originals unchanged; full 576 offline tests
  pass. Preserve sources/tests/protocol/plan/assets/invocations/start markers/
  logs/reports. Do not download again or restart the completed preflight. No
  study question entered the model, no reference/scoring/sealed access occurred,
  and the worker exited. This is engineering only, not real-cap throughput or
  routing evidence. The real 64-question diagnostic remains unstarted/locked.
  Next implement and freeze its separate 512-job two-arm collector with a shared
  global ledger and full endpoint/scoring/analysis rules. The proposed 1M-token/
  12-hour global limits are not yet a frozen collection protocol. Docker stays
  running, cloud/API spend $0, acquisition/Jev/RL/confirmations remain stopped.
- The [full two-solver diagnostic](docs/opportunity-panel-protocol.md) is frozen
  from `a136f27` after 623 offline tests. Actual protocol `d4e511ad…c1e44bc`
  binds both local solvers, unchanged 64-child/folds, 512 unique jobs/seeds,
  786,944 response reservations, one 1M-token/12-hour shared budget and fixed
  analysis. Actual independent prelaunch audit verified 39 source/11 protected/
  two dataset/16 model-asset hashes and all job/seed identities. The first
  background launch stopped 0/512 at `needs_attention`, before references.
  See [runtime diagnosis](docs/opportunity-panel-launch.md): macOS maintenance
  sleep106+929 seconds explains 26.98 monotonic vs1,057.29 wall seconds. The
  old wall watchdog counted sleep; generator uses monotonic time. Preserve
  every frozen file and initial status/log/journal/reservation/receipt. The
  first unresolved job stays charged512tokens/600seconds, setup19.5537seconds;
  collection start/global wall age including sleep/gaps must not reset. Only
  one permitted 1.7B resume remains; 0.6B initial is unstarted. Next is a
  separately pinned additive runtime recovery with matching monotonic watchdogs
  and a process-scoped AC system-sleep guard. Do not call original launch again
  while recovery is prepared. No new question allocation, label/reference,
  scoring or cloud access occurred. Official test/confirmations/acquisition/RL
  remain stopped; Docker running. More data needs a new prospective child/plan
  after the diagnostic; do not silently expand the frozen64 panel.
- The additive [opportunity recovery](docs/opportunity-panel-runtime-recovery.md)
  froze at `efa72b2` after 636 offline tests and independent review. Plan
  `614f5ea7…7392be`, prelaunch review `69f66f1a…db961`; all 22 immutable study
  originals, three new pins, two mutable archives and 52 original file pins pass.
  One recovery launch `a0a21397…9777cb5` is **running**, supervisor PID32363,
  temporary AC `caffeinate -s -i` PID32364, 1.7B collector PID32417/invocation
  `a8745527…6151bed`. Launch verification `76ef00c9…a6fd64` observed 3/512
  completed, 4,235 charged tokens including active/old failed reservations,
  5,742.27 seconds global wall age, both process sleep assertions and no scoring
  marker. These are snapshots, not terminal results. Authoritative live state:
  `opportunity-panel-v1/recovery-v1/status.json`; old background status remains
  the preserved failure. Do not relaunch, prepare again, edit frozen original
  or recovery source/tests/policy, or reset clocks/journals. The 1.7B permitted
  resume is consumed; 0.6B initial follows automatically after that arm completes.
  Endpoint finalizer fetches exactly selected64 training references only after
  all512 and collector exits; no earlier reference access. Same64/folds/jobs/
  seeds/caps/v7/analysis/global1M/12h remain authoritative. No extra questions
  allocated; decide after terminal diagnostic under a new prospective protocol.
  Docker running, cloud/API spend $0, official test sealed and confirmations/
  acquisition/Jev/RL remain stopped. See launch record for provenance and status.
- Opportunity recovery is now **stopped**, superseding the preceding running
  snapshot. At 2026-10-05 05:13:30 UTC, `recovery-v1/status.json` and immutable
  supervisor finish record `needs_attention`/`budget`: original shared wall
  ceiling reached. Completed452/512: 1.7B256/256 (exit0), 0.6B196/256 (own
  process terminated−15). Sixty missing; 454attempt reservations/two unresolved,
  342,047charged tokens/14,701.20charged seconds, 43,732.91global wall seconds
  vs43,200limit. Preserve all inputs/responses/journals/charges. No collection
  end/score marker/score sidecar/report; references remain locked. Do not
  relaunch either collector/supervisor, reset the original start or extend old
  budget. Next is read-only lost-wall-time diagnosis and a separately prospective
  completion protocol, retaining unchanged64/job identities and accounting for
  this stop. Launch guard does not prove uninterrupted wake or a cause of the
  wall/charged-time difference. No new questions, reference access or cloud
  spend; Docker kept running, official test sealed and other phases stopped.
