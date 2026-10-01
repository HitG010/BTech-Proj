# Phase 2 runtime diagnosis and recovery

The original local repeat collector stopped at **51/800 responses**. Its initial
invocation and the single automatic resume each encountered three consecutive
timeouts. The original supervisor correctly stopped at `needs_attention` at
2026-10-01 19:19:58 UTC. This is an operational failure; no partial accuracy,
router utility or signal-gate result is eligible for analysis.

## Evidence

The gold-free attempt ledger contains 51 successful and six failed attempts on
three distinct jobs. Successful attempts have a median **17.342 tokens/s**;
failed attempts have a median **0.03467 tokens/s**, about 500 times slower.
The last normal thinking response generated 1,631 tokens in 93.2 seconds, and
the next direct response generated 248 in 21.8 seconds. The next thinking
attempt, started at 18:14:02 UTC, generated only 15 tokens in 661.1 seconds.
The collapse persisted across both modes and a fresh model process. The prompts
are short, and the same question had already completed successfully.

Sampled MPS allocation stays near **3.456 GB**; driver allocation is near
4.38 GB in the first process and 4.00 GB after reload. These are post-response
samples, not peak memory or proof that host memory pressure never occurred.
Almost all failed-attempt time is spent inside generation. The existing
600-second deadline is checked after each generation step; a stalled step can
overrun it by 8–61 seconds. Increasing that deadline would change the frozen
protocol and would not explain the throughput collapse.

Native process and startup-log checks identify Docker's VM, PID 60079, created
at **18:13:49 UTC** (23:43:49 IST), **13.07 seconds** before the first failed
attempt. Its client is Docker's `com.docker.virtualization`, PID 60046. Six
other-project containers are active. The host has 16 GB RAM and approximately
5–6 GB swap in use. This temporal alignment suggests resource contention, but
there was no simultaneous host pressure/thermal trace during the failures, so
Docker causality is **unproven**. Current pressure queries are not critical,
AC power is connected, and no thermal warning is recorded. Historical power
queries found no sleep event in the examined collapse window. RunningBoard
describes the resumed Python collector as unmanaged; App Nap is not established
as the cause either.

A current synthetic 512×512 FP16 MPS multiplication has a warm median of
0.000415 seconds with the pinned Torch 2.14.0. It loads no solver and generates
no research responses. This small check establishes basic current GPU function;
it does not establish full-model throughput under load.

Evidence is in `repeat-panel-v1/diagnostics-v1/before-recovery-diagnosis.json`
and `throughput-diagnosis.png`. No reference answer or official-test gold was
read. All **2,319 protected original files** retained their hashes.

## Authorized recovery

The user requested diagnosis and repair, then selected **“Keep Docker running;
test recovery alongside it.”** Docker remains running. The additive
`scripts/repeat_recovery_worker.py` uses the unchanged collector and existing run
ledger. It does not edit the original worker, frozen package, decoder, protocol,
allocation, environment versions, seeds, model, dtype, caps or scoring policy.

The new `scripts/macos_runtime_guard.py` creates a process-scoped
`NSActivityUserInitiated` token inside the collector and ends it on exit. Apple
documents this API for finite, explicitly requested work to prevent scheduling
deferral; it is a runtime precaution, not proof of the historical cause.
No latency-critical scheduling or permanent system preference change is made.
The native activity begin/end path and its idle-sleep assertion were verified.
See Apple's [activity guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/PrioritizeWorkAtTheAppLevel.html)
and [ProcessInfo documentation](https://developer.apple.com/documentation/foundation/processinfo?language=objc).

Recovery preparation holds supervisor → study → run → recovery locks. Its
checksummed preservation inventory covers all 51 completed result files,
57 existing attempts, two setup sessions, run identity/data files, frozen study
inputs and original background policy/journal/status/log. Three failed result
rows are archived separately before the existing resumable runner replaces
them; all original attempt records remain unchanged.

`repeat-panel-v1/recovery-v1/` has a separate checksummed policy and journal,
status and log. It permits **one manually authorized collector invocation**,
with no automatic retry. The old invocation journal remains exhausted at 2/2.
The original cumulative **1.4M-token/12-hour** generation limits include all
old and new attempts, setup and retries. The new wrapper's separate 14-hour
monitoring ceiling cannot extend that ledger. Its callback stops after the
first durable failed job, avoiding another chain of wasted timeout attempts.
Every heartbeat records read-only power, swap, VM and pressure telemetry without
calling Docker APIs, which could otherwise resume a paused VM.

Only a full 800-completed endpoint and collector exit unlock the frozen analysis
and existing independent verifier. No later study or cloud job is launched.
Initial recovery success must be checked on actual solver jobs; synthetic GPU
health alone is insufficient to declare the runtime restored.

```sh
.venv/bin/python scripts/repeat_recovery_worker.py --prepare
HF_HUB_OFFLINE=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/repeat_recovery_worker.py
.venv/bin/python scripts/repeat_recovery_worker.py --status
```

Use the new recovery status for current progress. Original
`background-status.json` remains a preserved record of the exhausted supervisor.
Do not relaunch either collector or edit the pinned operational scripts while
recovery is active.
