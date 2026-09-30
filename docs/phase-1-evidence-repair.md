# Phase 1, checkpoint 1: correct the development evidence

Completed 2026-10-01 on `codex/research-data-efficiency`. This is the first
implementation checkpoint of the [accepted roadmap](research-roadmap.md).
It repairs a reporting defect using existing development traces; it adds no
new solver outcomes or independent confirmation.

## Branch and source lineage

- Starting study branch: `research/router-studies` at `15a4d2d`.
- New implementation branch: `codex/research-data-efficiency`.
- Pre-existing research handoff checkpoint: `1b67fbc`, including the original
  shared-router implementation, tests, documentation, and September review.
- The sibling `research/pilot-v2` worktree remains at `6c7903c`.

The checkpoint separates prior research from the correction. Git excludes
large generated artifacts; their content hashes and versioned local paths
provide the artifact lineage.

## Evidence, decision, and change

`probe.continuation_rows` correctly charges a first direct draft plus a
thinking generation for continuation action 2. The development evaluator
incorrectly reused that row as its standalone always-thinking baseline.
A standalone policy never requests that draft.

`router_dev.fixed_baselines` now retains action 2's correctness and subtracts
the first draft's token and cached-time costs. It copies the row, so the
continuation observations used for training and decisions remain intact.
The analysis identity is `shared-development-v2`; its default output is
`artifacts/router-dev/shared-base-v2/`. Fresh output directories are created
automatically, while existing reports with mismatched identities are rejected.

| Quantity at λ=.05 | Original v1 | Corrected v2 |
|---|---:|---:|
| Standalone thinking accuracy | 91.50% | 91.50% |
| Charged tokens/question | 1,654.47 | 1,430.69 |
| Cached generation seconds/question | 69.2591 | 60.1361 |
| Standalone thinking utility | 0.8322765 | 0.8434655 |
| Shared minus standalone thinking utility | +0.0391226 | +0.0279336 |

The corrected shared-minus-thinking exploratory question-bootstrap interval
is **[−0.0015151, +0.0571785]**. Shared minus confidence remains
**−0.0016321 [−0.0092263, +0.0054987]**. Neither interval establishes a
shared-router advantage. The corrected [development result](router-dev-results.md)
retains that conclusion.

## Reproduction and validation

From the repository root, using this checkpoint's source and environment:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -m reasoning_budget.router_dev \
  --source artifacts/probe/continuation-v1 \
  --output artifacts/router-dev/shared-base-v2
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

The regenerated artifact contains `report.json`, `report.md`, `curve.csv`,
and `accuracy-cost.png`. The figure was visually inspected.

- Before changes: 116 offline tests passed; Ruff passed.
- After changes: **118 offline tests passed**; Ruff and `git diff --check` passed.
- The new semantic test constructs real continuation rows with unequal direct
  and thinking costs and verifies standalone thinking pays only its own cost,
  continuation thinking still pays both costs, and the source rows are unchanged.
- The report-output test checks directory creation, verified reuse, and rejection
  of changed analysis identity without altering the saved report.
- Artifact comparisons verified all 200 corrected question rows and all
  always-thinking curve points. Every other policy summary, fitted setting,
  action, calibration result, curve point, and non-thinking comparison is
  identical to v1.
- An independent subagent repeated the report and preservation comparisons
  and found no remaining material issue in the change.

The checksummed local preservation ledger is
`artifacts/research/data-efficiency-v1/phase-1-step-1/preservation.json`;
the verified results are in the adjacent `verification.json`.
The ledger labels raw-file SHA-256 separately from envelope payload digests.
It records the four original v1 report artifacts, four frozen-confirmation
control files, and the GSM8K manifest/questions files. All ten retained their
exact bytes. The legacy generation implementation digest is also unchanged.

No gold file was opened for this checkpoint's integrity comparison. The CPU
replay used previously scored development records. The official test remains
sealed; the old confirmation still reports `generation_started: false`.
Solver generations: **0**. Cloud/API expenditure: **$0**.

## Next checkpoint within Phase 1

Reconcile scorer and generation identities before preparing the protocol bridge.
The code audits established these concrete requirements:

1. Combine repeating-decimal and Markdown-heading handling with the sibling's
   decorated-number and answer-label fixes under a new `numeric-v5` identity.
   Preserve strict incomplete-output handling and gold-independent extraction.
2. Keep the main GSM8K prompt, 2,048/512 caps, closure, and decoder confidence;
   port full checkpoint EOS handling, optional raw confidence, and runner
   ledger/failure safeguards under a new generation-protocol identity.
3. Preserve a checkout pinned to the existing source for legacy runs. Frozen
   study loading hashes both generation and scoring code; changing those modules
   requires new study identities, rather than bypassing the existing guards.
4. Add branch-crossing parser and fake-backend tests before the 25-question
   generation bridge. Measure actual throughput before cloud expenditure.

These integrations and the bridge remain pending. The checkpoint does not
establish a novel routing method or authorize reinterpreting the old frozen
confirmation as a test of a new candidate.
