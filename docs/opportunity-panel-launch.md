# Two-solver study: preparation and runtime record

Date: 2026-10-04. Branch: `codex/research-data-efficiency`.

The full two-solver diagnostic is implemented. Its initial collection stopped
before the first response completed. System sleep caused the stop. This is a
runtime failure, not a router result. No references were opened.

## Frozen preparation

Source, tests and [protocol](opportunity-panel-protocol.md) froze at
`a136f273b413fec0461aad29d16930194f037b7d`. All **623 offline tests** passed.
Two Sol reviews checked the collector and the analysis. The actual native
preparation then resolved both local tokenizers without loading model weights.

Protocol payload:
`d4e511ad16c1b7330452492a5c9d0a0c1a3dccc10418b0591ea73666fc1e44bc`.

An independent prelaunch audit verified 39 source/test/document hashes, 11
protected input hashes, two dataset hashes and 16 cached model files. It
reconstructed all 512 job IDs and independent seeds. The planned response
reservation is **786,944 tokens**. No new question or model file was allocated
or downloaded. The parent roles and 64-question child are unchanged.

## Initial collection stop

Original launch: `d8788cf47d5640ff8c85a84546e0e986`.
Collector invocation: `83817a822d0c43ae878f638291033e59`.
The original status is `needs_attention`, with **0/512** completed.

The setup completed. Its monotonic elapsed time was **19.5537 seconds**.
Its wall timestamps differ by **122.9654 seconds**. The full collector process
recorded **26.9831 seconds** on the monotonic clock, but the collection wall
timestamps differ by **1,057.2915 seconds**. Do not treat that difference as
model compute time.

The read-only Mac power log shows these events in Asia/Kolkata time:

| Time | Event |
|---|---|
| 22:34:47 | Maintenance sleep, 106 seconds |
| 22:36:33 | Maintenance wake |
| 22:36:42 | First direct job reserved |
| 22:36:43 | Maintenance sleep, 929 seconds |
| 22:52:12 | Maintenance wake |
| 22:52:14 | Supervisor stops its own collector |

The recorded sleep intervals account for the large wall/monotonic difference.
The watchdog compares wall time with the job's start timestamp. The generator
uses a monotonic deadline, which excludes these sleep intervals on this Mac.
The watchdog therefore stopped the job after only a few awake seconds.
There is no evidence here that Docker caused this stop.

The existing idle-sleep assertions from Python and `caffeinate -i` were present.
They did not prevent maintenance sleep. Apple's
[power assertion documentation](https://developer.apple.com/documentation/iokit/iopmlib_h/iopmassertiontypes)
distinguishes idle-sleep and system-sleep prevention. System-sleep prevention
can keep a process working during maintenance wake. Assertions remain
best-effort OS requests, not a guarantee against every sleep condition.

The installed `caffeinate(8)` manual confirms that `-s` applies only on AC power
and ends with the guarded process. No persistent power preference change is
required.

## Preservation and recovery boundary

Keep the original status, logs, launch journal, setup and failed job reservation.
The unresolved first job keeps its **512-token / 600-second** charge. Together
with setup, the charged ledger is **512 tokens / 619.5537 seconds**. The separate
global wall-age measure also counts sleep and gaps. Do not reset either clock,
the collection start, budget or invocation journal.

The first 1.7B invocation is spent. It has one permitted resume left. The 0.6B
initial invocation remains unstarted. References, scoring and analysis remain
locked until all 512 valid completed responses and exited collectors exist.

Next use a separately frozen additive recovery supervisor. It must match each
operation watchdog to the generator's monotonic clock and record those anchors
in separate sidecars. Keep the original wall-age global rule, both solver
configs, job seeds, prompt, token caps, unchanged v7 scorer and analysis.
Use a temporary AC system-sleep guard and a no-model power/clock preflight.
Keep Docker running. Never retry an incorrect answer to improve its label.

Any recovery report is engineering evidence. It cannot establish a causal speed
comparison, useful routing signal or publication novelty. Additional questions
remain conditional on the completed diagnostic and a new prospective protocol.

The new study directory is
`artifacts/research/data-efficiency-v1/opportunity-panel-v1/`.
Narrow power-event evidence is under `clock-diagnosis-v1/power-events.json`.
Cloud/API spend is **$0**. Official test and both confirmations remain sealed
or unstarted. Acquisition and Jev/RL remain stopped.

## Separately frozen recovery: running

Recovery source/tests/runtime policy froze at **`efa72b2`**, after all **636
offline tests** and independent Sol review passed. The
[runtime policy](opportunity-panel-runtime-recovery.md) describes the unchanged
study boundaries. The recovery plan is
`614f5ea758f42995b3b5fe9c707364eb898afa371f6caa0ee770b732937392be`.
An independent prelaunch audit verified all 22 immutable original study files,
three recovery pins, two archived mutable files and 52 original source,
protected-input and dataset pins. Its payload is `69f66f1a…db961`.

The one recovery launch is **`a0a2139708944595a3f2bd4289777cb5`**.
Supervisor PID is **32363**; its temporary `caffeinate -s -i` guard is PID
**32364**. The 1.7B collector invocation is
`a87455276d3f4c1d818abc2dd6151bed`, PID **32417**. This uses the existing permitted
1.7B resume. The 0.6B initial invocation will follow after the 1.7B endpoint.

At the launch verification snapshot, **3/512** responses were complete,
all from 1.7B. Both idle-sleep and system-sleep assertions were observed for
the recovery guard. The shared ledger charged **4,235 tokens**, including
active reservations and the preserved failed attempt. Global wall age was
**5,742.27 seconds**. This is a time-stamped progress snapshot, not final usage.
No reference access or scoring marker existed. Launch review payload is
`76ef00c9…a6fd64`.

The authoritative live status is now
`opportunity-panel-v1/recovery-v1/status.json`. It updates about every ten
seconds. Original `background-status.json` remains the historical failure and
must not be used as the recovery status. Do not restart either launcher or
edit pinned recovery files. The detached worker will run both arms and the
unchanged full-endpoint scoring/analysis transaction, or stop at the first
failure. Review the terminal report before any new question allocation.
