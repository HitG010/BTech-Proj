# Repository orientation

Snapshot checked 2026-10-02. Verify `git status --short --branch` and
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
  scoring limitation is resolved by the separate parser preflight below. Next is
  a separate frozen 50-question repeat-panel protocol (projected 7.04 local hours excluding
  setup/retries); its generation permission must reference the unchanged role
  allocation. Later phases remain pending. Cloud expenditure is $0.
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
- Phase 2 [repeat-panel preparation](docs/phase-2-repeat-panel.md) is complete
  from source `272403f`. Protocol `8b01db2c…6f3c812` under `repeat-panel-v1/`
  pins the unchanged allocation and 50 repeat questions, v7, all 800 independent
  jobs/seeds, 50×387 question features and five 10-question folds. All 363 tests
  pass (22 new repeat tests). Preparation was 0/800, generation not started;
  no repeat reference answers or official-test gold were opened then. Maximum planned
  reservations are 1,229,600 tokens; cumulative local limits are 1.4M tokens and
  12 hours including setup/retries. The question-only `data/repeat/` manifest has
  `gold_sha256: null`; do not add a gold file or use ordinary `rb score` on it.
  Use the additive `python -m reasoning_budget.research_repeat` prepare/status/
  collect/score/analyze commands. Only its full 800-completed endpoint permits
  fetching the 50 selected upstream-training answers and separate v7 scoring.
  Every source/config/feature/role and attempt/setup timestamp is guarded; do not
  edit frozen existing package files or launch duplicate collectors. The two
  four-draw halves provide independent-draw diagnostics; all model tuning stays
  within the acquired training-half labels and question folds. Eight-draw labels
  have no independent same-question eight-draw replica. Scale acquisition only
  if all predeclared signal/utility gates pass. Initial collection stopped at
  51/800 after timeouts; the separate manual recovery is described below.
  No Phase 2 generation or cloud spend in this preparation checkpoint; all 2,319
  protected original files and the old unstarted confirmation remain unchanged.
- Phase 2 local collection started at 2026-10-01 17:37:19 UTC (23:07:19 IST)
  under `scripts/repeat_background_worker.py`, committed with the independent
  endpoint verifier at `3505a77`. Initial supervisor/collector PIDs are
  27132/27339; read `repeat-panel-v1/background-status.json` for current state,
  or use the script's `--status` command. It records 60-second heartbeats, holds
  a singleton lock, and permits at most one automatic resume through a durable
  invocation journal. Script hashes and protocol are pinned in checksummed
  `background-policy.json`; do not edit these scripts, frozen package/config,
  or launch a duplicate collector. The same 1.4M-token/12-hour cumulative
  generation limits apply, with a separate 14-hour monitoring ceiling. Only
  the full 800-response endpoint and collector exit permit automatic analysis
  and an independent accounting/policy/preservation audit. It stops after that
  audit, including if the progression gates fail; no later studies or cloud jobs
  are launched. All 363 existing tests plus nine new operational tests pass.
  Pre-launch incomplete-endpoint and 2,319-file preservation checks passed;
  repeat reference answers remain locked until completion, official test sealed
  and old confirmation unstarted.
- Phase 2 [runtime recovery](docs/phase-2-runtime-recovery.md) is now active.
  The original supervisor stopped at 51/800 after six timeout attempts, with
  its two invocation reservations exhausted. Its policy/journal/status/log,
  all 51 completed responses, 57 attempts and two setup sessions are preserved;
  three failed result rows are archived under `recovery-v1/failed-results-before/`.
  Gold-free diagnosis records a throughput collapse from 17.34 to 0.0347 tokens/s,
  flat sampled MPS allocation, and Docker's VM starting 13 seconds before the
  first failed attempt. Docker contention is an inference, not proven causality;
  no contemporaneous host-pressure trace exists. The user requested repair and
  explicitly chose to keep Docker running. Additive scripts at `3698102` provide
  one manual recovery invocation, with process-scoped macOS user-initiated
  activity, read-only telemetry and a stop at the first durable failed job.
  Do not stop Docker, edit any pinned scripts/package/config, reset either
  invocation journal or launch duplicate collectors. New supervisor/collector
  PIDs are 4158/4365; live state is `repeat-panel-v1/recovery-v1/status.json`,
  not the original terminal `background-status.json`. The new policy digest is
  `3205df22e02694ea41f58fdbd1b66d56e01bc731c8173fa29eaa2ea7e6f7e864`.
  Original protocol `8b01db2c…6f3c812`, seeds, solver, scorer and cumulative
  1.4M-token/12-hour limits are unchanged. All 386 offline tests pass. Independent
  `recovery-v1/startup-verification.json` at 2026-10-01 22:38:16 UTC records
  59/800 complete, zero failed current rows, all three previously timed-out cells
  completed at 17–22 tokens/s with matching archived token prefixes, and all old
  records/2,319 protected files unchanged. Full endpoint remains pending.
  Outcomes/reference answers stay locked,
  official test sealed, old confirmation unstarted and cloud expenditure $0.
