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
