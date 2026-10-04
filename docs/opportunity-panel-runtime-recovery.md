# Opportunity panel: one bounded local recovery

The original frozen collector (`a136f27`, protocol SHA-256
`d4e511ad16c1b7330452492a5c9d0a0c1a3dccc10418b0591ea73666fc1e44bc`)
stopped with zero of 512 responses. Its first Qwen3-1.7B setup loaded in 19.5537
seconds; the first 512-token job reservation has no settlement. Two recorded
maintenance sleeps lasted about 106 and 929 seconds. Across the stopped launch,
wall time reached about 1,057 seconds while the child was awake for about 27
monotonic seconds. The original supervisor
uses wall time to watch an active job and stopped it. The original ledger charges
the unresolved job conservatively. The original collection start, token ceiling
of 1,000,000 and shared 12-hour wall ceiling remain authoritative; sleep and
gaps continue to count against the latter. The cause of the sleep is unknown.

This separate recovery script uses the original protocol reader, invocation
reservation, collector, ledger, and finalizer. It changes no model, prompt,
decoder, seed, response cap, scorer, allocation, or reference boundary. Its
wrapper calls the original `reserve` exactly once per operation and immediately
writes an immutable sidecar containing a monotonic timestamp captured before
that call and the reservation digest. The recovery supervisor checks the
original active reservation against that timestamp. It still uses the original
global ledger/wall budget. Per-setup and per-job limits remain 900/600 seconds,
plus the original five-second watchdog grace. The supervisor keeps the 9 GiB
sampled RSS, two-second polling and 14-hour monotonic ceiling, with one bounded
finalization child. Missing clock anchors or RSS readings stop collection.

Before any model process, `prepare` checks the exact stopped boundary and saves
an exclusive, checksummed plan with source/test/document hashes, environment,
protocol identity, first original collection-start hash, and a byte-hash
inventory of all then-existing immutable study files. The original mutable
`active.json` and `status.json` are archived byte-for-byte with hashes before
the collector may update them; their current values are excluded from later
inventory checks. The old `background-status.json` remains pinned and unchanged.
The inventory includes the additive clock diagnosis. The
launcher verifies the plan and originals; the background worker repeats those
checks. Frozen original source pins and original finished journals are not
rewritten. New original invocation/process/ledger records are append-only.

Exactly one manual recovery launch is possible. It reserves the second original
supervisor launch, then executes a detached `/usr/bin/caffeinate -s -i` process
guard. Before launch it requires AC power, current CPU and graphics system
capabilities, and a stable two-second no-model wall/monotonic clock sample.
Process assertions are best effort; thermal or low-power system behavior can
still override them. The guard never changes persistent sleep settings or
controls Docker. The first recovery child uses the one remaining 1.7B
invocation; the second uses the first 0.6B invocation. Any failure stops the
sequence, with no automatic retry or resume. The original
`background-status.json` and logs retain their historical failure. New
`recovery-v1/status.json` is the recovery status, and its immutable journals,
anchors, process observations and logs identify this implementation. Recovery
collectors require a sidecar bound to the actual original invocation, this
launch, and the live supervisor parent process. Progress is updated about every
ten seconds during collection. A separate finalization request is frozen after
all 512 responses before the unchanged endpoint finalizer starts.

After source/test/doc review and commit, run the following from the project
root with its existing `.venv`. These are operator commands, not test commands:

```sh
.venv/bin/python -m scripts.opportunity_panel_recovery prepare
.venv/bin/python -m scripts.opportunity_panel_recovery status
.venv/bin/python -m scripts.opportunity_panel_recovery launch
.venv/bin/python -m scripts.opportunity_panel_recovery status
```

`launch` returns immediately with the detached process ID and log path. Wait
for the status to become `complete` or `needs_attention`; do not call launch a
second time. Full-endpoint scoring alone may fetch the selected 64 training
references. Partial collection, status and tests never access references or
official-test gold. A completed report is a diagnostic for each solver's
opportunity rate and fixed confidence controls, not confirmation of a new
router or approval to scale acquisition/RL.
