# History

Records kept for provenance after the repository clean-ups of 5 and 7 November
2026. Nothing here is current guidance; read the [research map](../README.md)
first.

- [agents-log.md](agents-log.md): the dated agent handoff log from the old root
  `AGENTS.md` (3 October to 5 November 2026), verbatim apart from local paths.
- [plan.md](plan.md): the milestone checklist and execution log formerly at the
  repository root.
- [root-readme-2026-11-05.md](root-readme-2026-11-05.md): the old root README,
  with the full `rb` command walkthrough for every study.
- [research-map-2026-11-05.md](research-map-2026-11-05.md): the old research
  map, with dated status paragraphs from September to November.
- [pilot-v2/](pilot-v2/README.md): the three September reports from the
  unmerged `research/pilot-v2` branch.
- [planning/](#planning-and-launch-snapshots) and
  [launches/](#planning-and-launch-snapshots): superseded plans and launch-time
  status snapshots, listed below.
- Paper review memos are in
  [`papers/thinking-selection/history/`](../../papers/thinking-selection/history/README.md).

## Planning and launch snapshots

Moved from `docs/` on 7 November 2026. Some frozen, hash-checked records still
link to the old `docs/<name>.md` paths; those links no longer resolve, and the
files are here under the same names.

| File | What it was |
|---|---|
| [planning/research-roadmap.md](planning/research-roadmap.md) | Phase roadmap and decision gates (October) |
| [planning/research-next-steps.md](planning/research-next-steps.md) | September next-steps plan |
| [planning/router-research-proposal.md](planning/router-research-proposal.md), [planning/router-improvement-research.md](planning/router-improvement-research.md) | Router literature table and improvement ideas (September) |
| [planning/novelty-plan-2026-10-08.md](planning/novelty-plan-2026-10-08.md), [planning/research-evidence-map-2026-10-08.md](planning/research-evidence-map-2026-10-08.md), [planning/publication-plan-2026-10-08.md](planning/publication-plan-2026-10-08.md) | Threshold-acquisition plan, evidence map, and first publication plan |
| [planning/empirical-paper-outline-2026-10-09.md](planning/empirical-paper-outline-2026-10-09.md) | Original outline of the manuscript |
| [planning/qwen17-improvement-plan.md](planning/qwen17-improvement-plan.md) | 1.7B improvement plan (cap bridge before optional LoRA) |
| [planning/kaggle-free-gpu-plan.md](planning/kaggle-free-gpu-plan.md), [planning/kaggle-free-gpu-readiness.ipynb](planning/kaggle-free-gpu-readiness.ipynb) | Free Kaggle GPU plan and readiness notebook (never uploaded or run) |
| [launches/opportunity-panel-launch.md](launches/opportunity-panel-launch.md) | Two-solver first-launch diagnosis |
| [launches/sparse-validation-runtime-launch.md](launches/sparse-validation-runtime-launch.md) | Fresh guard test launch snapshot |
| [launches/qwen17-cap-bridge-runtime-launch.md](launches/qwen17-cap-bridge-runtime-launch.md), [launches/qwen17-cap-bridge-completion-launch.md](launches/qwen17-cap-bridge-completion-launch.md) | Cap-bridge launch snapshots |

## Archived branch tips

Before `master` was fast-forwarded, every older line of work was tagged so it
stays reachable even if its branch is later deleted:

| Tag | Commit | What it holds |
|---|---|---|
| `archive/master-2026-09-13` | `0087b92` | The original `master`: smoke test and audited pilot v1 |
| `archive/pilot-v2` | `6c7903c` | Protocol v2 pilot (side branch, never merged): reports, `configs/pilot_v2.yaml`, `configs/smoke_v2.yaml`, `src/reasoning_budget/analysis.py` |
| `archive/router-studies` | `15a4d2d` | Calibration, router studies 2–8, prepared 3,100-question confirmation |
| `archive/research-data-efficiency` | `ee88d64` | Protocol bridge through the 1.7B cap study (1–7 October) |

The old `master`, `research/router-studies`, and `codex/research-data-efficiency`
were ancestors of `codex/confidence-acquisition-plan`, so their whole history is
also in the main line. Only `research/pilot-v2` had commits that are not; its
code and configurations are reachable through the tag:

```bash
git show archive/pilot-v2:src/reasoning_budget/analysis.py
```

## Pushing the tags and `master` (from the Mac)

Done 5 November 2026: the four tags are on GitHub and `master` was
fast-forwarded to `b1003a0`, then to `42ecef1`. The remote branches
`research/pilot-v2`, `research/router-studies`, and
`codex/research-data-efficiency` were then deleted; the tags keep their tips. The cloud session that did the clean-up could push
only its own branch, so these commands were run from the Mac; they are kept as
the record. To bring `master` up to date with later main-line commits, rerun
the last command.

```bash
git fetch origin
```

```bash
git tag -a archive/master-2026-09-13 0087b92 -m "Original master before fast-forward: smoke test and audited pilot v1"
git tag -a archive/pilot-v2 6c7903c -m "Unmerged research/pilot-v2 tip: protocol v2 pilot reports, configs, analysis.py"
git tag -a archive/router-studies 15a4d2d -m "research/router-studies tip: calibration, router studies 2-8, prepared confirmation"
git tag -a archive/research-data-efficiency ee88d64 -m "codex/research-data-efficiency tip: protocol bridge through the 1.7B cap study"
```

```bash
git push origin archive/master-2026-09-13 archive/pilot-v2 archive/router-studies archive/research-data-efficiency
```

```bash
git push origin origin/codex/confidence-acquisition-plan:refs/heads/master
```

The last push is fast-forward only: without `--force`, Git refuses it if
`master` is not an ancestor of the main line.

## Removed builds

Deleted on 7 November 2026 at the author's request, to cut clutter before release.
They were last present in commit `e162865`. This overrides the instructions in
[agents-log.md](agents-log.md) to preserve these outputs. No code or test used them.

| Removed from `papers/thinking-selection/` | What it was |
|---|---|
| `latex/` | LaTeX reviewer package and 22-page PDF of manuscript v0.2 |
| `figures/` | Original R5 figures, renderer, and frozen export record |
| `figures-v2/output/` | First v2 figures, superseded by `figures-v2/output-r2/` |
| `thinking-selection-review-source.zip`, `thinking-selection-review-source-v2.zip` | Portable source bundles of manuscript v0.2 and v0.3 |

Links to these in archived and frozen documents no longer resolve, and the records
in `figures-v2/` (`freeze.json`, `export-record.json`, and their correction files)
still name them. To get one back, for example:

```bash
git show e162865:papers/thinking-selection/latex/output/pdf/main.pdf > manuscript-v0.2.pdf
```

```bash
mkdir restored && git archive e162865 papers/thinking-selection/figures | tar -x -C restored
```
