# Phase 2 runtime diagnosis and recovery

Recovery is **complete**, with all 800 responses and no further failed attempt.
The frozen research analysis failed four progression gates; see
[the separate result record](phase-2-repeat-results.md). The incident and startup
evidence below are preserved as historical checkpoints. Do not relaunch workers
or edit their pinned scripts.

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

## Verified recovery checkpoint

Recovery scripts froze at **`3698102`**; all **386 offline tests**, Ruff and
whitespace checks pass. Separate policy digest:
`3205df22e02694ea41f58fdbd1b66d56e01bc731c8173fa29eaa2ea7e6f7e864`.
Supervisor/collector PIDs are **4158/4365**. Its invocation journal is 1/1;
the original remains 2/2. Docker continues running and no system preference
was changed. The collector's own native activity assertion is active.

At **2026-10-01 22:38:16 UTC** (2026-10-02 04:08:16 IST), independent
`recovery-v1/startup-verification.json` recorded **59/800 complete**, zero failed
current job rows and outcomes locked. All three previously failed cells are
complete under the identical job definitions and seeds:

| Mode / draw | Latest timeout | Recovered response | Throughput |
| --- | --- | --- | --- |
| Thinking / 1 | 24 tokens / 630.0 s | 993 tokens / 49.5 s | 20.05 tokens/s |
| Direct / 2 | 23 tokens / 608.7 s | 177 tokens / 10.3 s | 17.15 tokens/s |
| Thinking / 2 | 28 tokens / 628.6 s | 1,143 tokens / 52.7 s | 21.68 tokens/s |

Every archived timeout token prefix matches the corresponding recovered token
sequence. This supports unchanged sampling behavior for the observed prefixes;
it does not establish universal determinism or a causal effect of the activity
guard. Ordinary full-model throughput has returned with Docker still active.
The exact historical trigger remains unproven.

The proof verifies all original 51 completed files, 57 attempts, two setup
sessions, old supervisor artifacts, archived failed rows and 2,319 protected
original files. No source/config/role or cumulative-budget identity changed.
The cumulative ledger, including old failures and active reservations, is
42,223 tokens / 1.909 hours at this snapshot. Those charges are not just the
cost of completed responses. No score/report exists yet, repeat data still has
`gold_sha256: null`, official test stays sealed and old confirmation unstarted.
Collection continued independently under this boundary; completion is recorded
below.

## Completion

Terminal state is **`complete_with_gate_failures`**, recorded at
**2026-10-02 05:20:08 UTC** (10:50:08 IST). All **800/800** final responses
are completed. The recovery invocation encountered no further failed attempt.
The full ledger has **806 attempts (800 completed, six earlier failures), three
setup sessions, 644,519 charged tokens and 8.39463 cumulative hours**, below the
unchanged 1.4M-token/12-hour limits. Cumulative charged time differs from elapsed
wall time, which includes the diagnostic pause. Docker was kept running; no
container or system preference was changed. The exact historical trigger and
the activity guard's causal effect remain unproven.

The collector and supervisor released their locks. The one-invocation recovery
journal stays at 1/1, and the original exhausted journal stays at 2/2. All 51
original completed files, 57 prior attempts, two original setup sessions,
archived failed rows, old supervisor artifacts and 2,319 protected originals
retain their hashes. `background-verification.json` independently verifies
endpoint/accounting/policy arithmetic. The fresh review proof is
`recovery-v1/completion-review-verification.json`; it also records exact CPU
reproduction of the original statistical analysis from cached scores.

The operational repair succeeded, but **acquisition scaling is stopped** because
the fixed signal/utility gates failed. The supervisor launched no later study.
Only the 50 selected training references were fetched after the completed
endpoint; official test remains sealed and old confirmation unstarted. Cloud
expenditure remains $0.
