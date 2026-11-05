# Repository orientation

Rewritten 5 November 2026. The dated log of every study, freeze, launch, and
result from 3 October to 5 November now lives in
[docs/history/agents-log.md](docs/history/agents-log.md). Check
`git status --short --branch` before relying on this summary.

## Where things are

- **Main line.** `codex/confidence-acquisition-plan`. `master` is to be
  fast-forwarded to it and the older tips tagged `archive/*`; the commands, run
  from the Mac, are in [docs/history](docs/history/README.md). Only the
  pilot-v2 tip holds commits that are not in the main line.
- **Start here.** The [research map](docs/README.md) for results and reading
  order; the [paper folder](papers/thinking-selection/README.md) for manuscript
  v0.7 (long report) and the 8-page [short paper](papers/thinking-selection/short/README.md);
  the [root README](README.md) for setup and commands.
- **Code.** `src/reasoning_budget/` (package), `scripts/` (study and audit
  entry points), `tests/` (offline tests), `configs/`, `docs/` (protocols and
  result records), `papers/`.
- **Local only.** `artifacts/`, `.cache/`, `.python/`, and `.venv/` are ignored
  by Git and exist only on the author's Mac. They hold every raw response and
  score cache. `artifacts/legacy/router-studies-6999eb5/` is the detached
  checkout used for frozen legacy studies.

## Current state

- The research is complete as an empirical negative result: on GSM8K with
  Qwen3, no learned deferral rule beat the direct-draft confidence threshold.
  Phase 2 post-hoc audits (cost curves, refit-inclusive intervals, two-draft
  agreement, confidence–gain shape, token-level deferral) found no new
  candidate.
- The short paper reproduces from one cache file: `scripts/reproduce_paper.py
  check` passes all 195 checks ([report](docs/reproduction-report.md)). The
  cache `artifacts/research/data-efficiency-v1/paper-cache-v1/paper-cache.json`
  (SHA-256 `3da91b57…92e73757`) is local and unpublished; do not re-export over it.
- Open items are author decisions, listed in the
  [submission checklist](papers/thinking-selection/short/submission-checklist.md):
  authors and endorsement, full-text citation checks, feedback, venue, licences,
  and publishing the cache.

## Standing rules

- **Local experiments only.** No paid cloud or API spend. Free Kaggle GPU use
  needs its own separately frozen plan. Docker on the Mac must stay running.
- **Sealed data stays sealed.** The official 500-question test split, the
  2,000-question sealed confirmation, and the prepared 3,100-question
  confirmation are untouched. 256 reserve rows remain unclaimed; any new
  allocation needs its own frozen protocol.
- **Completed work is frozen.** Do not rerun, re-prepare, relaunch, or
  re-score a completed study or audit, reset its journals or clocks, or reopen
  its references. Use cached score sidecars; never call `score` or `analyze`
  merely to reproduce statistics. Do not edit pinned protocol, script, test,
  figure-plan, or renderer files; corrections are additive and separately
  versioned.
- **New analyses** follow the frozen-protocol pattern: commit the protocol,
  script, and tests before `prepare`/`execute`, write to a new artifact
  directory, and keep failed criteria as reported.
- **Claims.** Do not present the cascade framing, the confidence rule,
  agreement, cost-aware acquisition, contrastive routing, or RL as novel.
  Preserve failed gates and conditional intervals in any rewrite.
- **Commits.** No Claude or AI attribution trailers (`Co-Authored-By: Claude…`,
  `Claude-Session:`). The AI-assistance statement in the papers stays.
