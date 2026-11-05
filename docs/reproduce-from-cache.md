# Reproducing the paper from the cache

`scripts/reproduce_paper.py` rebuilds the numbers of the short paper
(`papers/thinking-selection/short/`) from one cache file. It never generates a
response, calls a scorer, or opens a reference answer.

## Two steps

**1. Export (once, on the machine that holds `artifacts/`).** Loads the
completed repeat and two-solver studies through their guarded loaders (all
source, protocol, record, score, and report hashes are checked), reads the
recorded decisions of the control families from their completed reports, and
writes one self-contained file:

```bash
PYTHONPATH=src .venv/bin/python -m scripts.reproduce_paper export
```

Output: `artifacts/research/data-efficiency-v1/paper-cache-v1/paper-cache.json`
(under 1 MB). The command refuses to overwrite an existing cache. For every
control family it first checks that the report's confidence decisions equal
the primary repeat report's, so the recorded decisions line up with the
cached outcomes.

**2. Check (anywhere, from the cache alone).**

```bash
PYTHONPATH=src .venv/bin/python -m scripts.reproduce_paper check
```

Use `--cache PATH` for a downloaded cache, `--output DIR` (default
`reproduction-output/`), and `--processes N` (default up to 4). The full check
reruns the 2,000-resample refit bootstrap and takes roughly 10–20 minutes on
four cores; `--skip-refit` takes about a minute and marks the
refit-inclusive and repartition columns of Table 2 as skipped. The command
exits non-zero if any value differs from the published one.

Outputs: `reproduction.md` (Tables 1 and 2 as recomputed, plus any
mismatches) and `reproduction.json` (every recomputed value and every
comparison).

## What the cache contains

- **Repeat panel** (Qwen3-1.7B, 50 questions × 8 draws): question IDs and
  folds; scored correctness, charged tokens, and seconds for each direct and
  thinking response; the four draft features (confidence, log answer length,
  parser validity, truncation); the 387 question features; and each direct
  draft's extracted answer and parser status.
- **Two-solver panel** (64 questions × 2 draws, Qwen3-0.6B and Qwen3-1.7B):
  the same outcomes, confidence, extracted answers, and folds.
- **Recorded decisions** of the nine control-family rows of Table 1 (CPU,
  compact neural, four CLM rows, three token-level rows) for both four-draw
  directions.
- **Provenance**: hashes of the source studies and reports, the exporter, and
  the audit code. No absolute local paths or machine environment.

It contains no response text, no reference answers, and nothing from the
sealed confirmation or official-test roles. Correctness flags are the frozen
numeric-v7 labels.

## What is recomputed and what is recorded

| Paper element | How the check obtains it |
|---|---|
| Table 1: always direct, always think, oracle, confidence, predeclared learner | Refit from cached outcomes and features with the frozen historical code |
| Table 1: two-draft agreement | Simulated from cached extracted answers |
| Table 1: nine control-family rows | Accuracy, tokens, utility difference, interval, and lift recomputed from their **recorded** decisions; their fitting (encoders, teacher forcing, neural training) is not rerun |
| Table 2 | Fixed-action intervals with each study's seed; refit bootstrap and fold repartitions rerun |
| Figure 1 | Every λ-sweep point recomputed by refitting at each λ and compared with the frozen figure's manifest |
| Quoted text values | Outcome counts, escalation composition, oracle share, two-solver and agreement values |

Recomputation uses `scripts/audit_deferral_curves.py`, the frozen code that
produced the deferral-curve report, so a passing check means the same code and
the same cached data give the published numbers.

## Status

**Reproduced, 5 November 2026.** `export` and the full `check` (refit bootstrap
included, four processes) were run on the Mac. All 195 checks pass, none
skipped: every Table 1 and Table 2 value, every Figure 1 point, and every quoted
text value matches the published number. The report is
[reproduction-report.md](reproduction-report.md); the cache has SHA-256
`3da91b57c98612141f2962cc657d6c9e3e26b4b0592d52006a7dcfce92e73757`.

The cache is not yet published. Keep `paper-cache.json` with the backup of
`artifacts/`; it is the file to deposit once the release decisions in the
[submission and release checklist](../papers/thinking-selection/short/submission-checklist.md)
(what to publish, licenses, DOI) are made. A reader who downloads it can
confirm it with the SHA-256 above before running `check`.
