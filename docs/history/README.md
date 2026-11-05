# History

Records kept for provenance after the repository clean-up of 5 November 2026.
Nothing here is current guidance; read the [research map](../README.md) first.

- [agents-log.md](agents-log.md): the dated agent handoff log from the old root
  `AGENTS.md` (3 October to 5 November 2026), verbatim apart from local paths.
- [pilot-v2/](pilot-v2/README.md): the three September reports from the
  unmerged `research/pilot-v2` branch.

## Archived branch tips

Before `master` was fast-forwarded, every older line of work was tagged so it
stays reachable even if its branch is later deleted:

| Tag | Commit | What it holds |
|---|---|---|
| `archive/master-2026-09-13` | `0087b92` | The original `master`: smoke test and audited pilot v1 |
| `archive/pilot-v2` | `6c7903c` | Protocol v2 pilot (side branch, never merged): reports, `configs/pilot_v2.yaml`, `configs/smoke_v2.yaml`, `src/reasoning_budget/analysis.py` |
| `archive/router-studies` | `15a4d2d` | Calibration, router studies 2–8, prepared 3,100-question confirmation |
| `archive/research-data-efficiency` | `ee88d64` | Protocol bridge through the 1.7B cap study (1–7 October) |

`master`, `research/router-studies`, and `codex/research-data-efficiency` are
ancestors of `codex/confidence-acquisition-plan`, so their whole history is
also in the main line. Only `research/pilot-v2` has commits that are not; its
code and configurations are reachable through the tag:

```bash
git show archive/pilot-v2:src/reasoning_budget/analysis.py
```
