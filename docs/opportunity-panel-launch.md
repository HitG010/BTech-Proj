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

## Recovery terminal checkpoint: budget stop

At **2026-10-05 05:13:30 UTC** (**10:43:30 Asia/Kolkata**), recovery stopped at
`needs_attention`, failure kind `budget`, reason
`BudgetExhausted: Original shared budget reached`. There are **452/512**
completed responses: **256/256** for 1.7B and **196/256** for 0.6B. Sixty 0.6B
responses remain missing. The 1.7B process exited successfully; the recovery
supervisor terminated its own 0.6B process with exit code −15.

Terminal ledger charges are **342,047 tokens / 14,701.20 seconds**. Global wall
age is **43,732.91 seconds**, above the original **43,200-second** ceiling.
The ledger includes active/unresolved reservations; these are not just tokens
in completed outputs. There are 454 job reservations, 452 completed responses
and two unresolved reservations. The initial failed job remains preserved.

The original wall-time rule counts pauses, sleep and gaps. The terminal files
alone do not establish why wall age exceeded charged operation time, or why
the supervisor observed the ceiling about 533 seconds late. Diagnose that
with separate read-only clock/power evidence before proposing another run.
The temporary assertion observed at launch is not proof of uninterrupted wake.

No collection-end, score-start, score sidecar or final report exists. References
and task-quality analysis remain locked. No worker is collecting; recovery has
an immutable supervisor finish. Do not relaunch, reset journals, increase the
old budget, or score the partial endpoint. Preserve every response and input.
Completing the missing 60 needs a separate prospective completion protocol
that accounts for this failed run and retains unchanged question/job/scoring
identities. No extra questions or cloud spend occurred.

## Authorized completion child: running

The user authorized completion of the missing 60 responses. The separate
[completion protocol](opportunity-panel-completion.md) froze at **`b7c3b1e`**
after all **643 offline tests** and independent Sol review passed. Plan identity:
`387e139c492236c0e9719886e59d872f724242eac72af460ac969b42c4a71b1d`.
Prelaunch verification `ef2e8882…e3b01` independently checked all **2,319 parent
study files**, four completion source pins, 52 original input/source pins and
the exact 60 jobs. This parent inventory is distinct from the historical
2,319 protected originals checked separately by the endpoint finalizer.

One completion launch **`4606906ca6c84dd89fc7ab8d46826ecb`** is running.
Supervisor PID **14364**, temporary sleep-guard PID **14365**, collector PID
**14373**, invocation **`a922ea9134f74448bef55efd9ec137e5`**. It uses only the
original pending 0.6B jobs. The new child has a four-hour wall/charged allowance;
combined original plus new token charges remain capped at one million. Maximum
planned combined reservation is 434,267 tokens. Old journals, statuses, charges
and the expired original budget remain unchanged.

Launch verification `1eba21d4…093935` verified **1/60** settled new responses
and **453/512** combined responses. At that snapshot the ledger charged 344,897
combined tokens, including the active thinking reservation and both old
unresolved charges. Both temporary idle/system-sleep assertions were observed
for this worker; all parent inventory hashes matched. No reference-access
marker existed. These are launch snapshots, not final usage or quality results.

The authoritative status is now
`opportunity-panel-v1/completion-v1/status.json`. Original and recovery statuses
remain historical failures. Do not relaunch or edit frozen completion source,
tests or protocol. The detached supervisor will run the exact 60 jobs, then
perform endpoint-gated v7 scoring and the unchanged analysis, or stop on first
failure. Keep the Mac open/on AC and Docker running. No extra questions, cloud
spend, sealed access or acquisition/RL promotion occurred.

## Completion terminal checkpoint

Completion finished **2026-10-05 18:14:48 UTC** (23:44:48 Asia/Kolkata).
All60 new responses completed with no failure/retry; combined512/512 were
scored and analysed. Collector/finalizer exit zero, supervisor terminal
`complete`, workers absent and locks released. Combined charges384,552tokens
and16,134.02operationseconds; new collection wall1,466.61seconds. Original
budget failure and both old unresolved charges remain unchanged.

Report `f3f0d33c…ac6fd`, independent endpoint verification `b67d4e0a…5dfcc`.
The review checks all parent hashes, job/score/record identities and costs, and
reproduces107metric payloads without refitting, scoring or opening references.
See [results](opportunity-panel-results.md). Preserve all frozen records and do
not restart preparation/launch/collection/finalization. New data or policy work
requires a prospective design; this diagnostic alone is not novelty evidence.
