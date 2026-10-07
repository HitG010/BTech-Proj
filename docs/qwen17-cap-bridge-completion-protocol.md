# Separate completion of the stopped 1.7B cap bridge

The user authorized one prospective completion of the exact 30 pending jobs
after the original cap runtime exhausted its initial and explicit-resume
invocations. This is a new child protocol, not another use of the stopped
launcher. Preserve the original runtime, both launches, status, logs,
reservations, failed attempts and six completed responses byte for byte.
The original stop remains a protocol deviation regardless of the child result.
It was a runtime stop while the frozen original token/time limits were still
within bounds; the original protocol did not reach its complete endpoint.

Freeze `scripts/qwen17_cap_bridge_completion.py`,
`tests/test_qwen17_cap_bridge_completion.py` and this document before one-time
child preparation. Only `qwen17-cap-bridge-v1/completion-v1/` receives
new files. Preparation reads existing cached records and question metadata,
verifies the stopped parent and its source, environment and asset identities,
and freezes its full inventory excluding the child. It constructs no model,
opens no reference and starts no worker. An independent actual-input review
must precede launch; prepare and launch are separate operator actions.

The stopped parent has six of 36 valid responses, eight attempt reservations,
two setups/invocations/launches, one settled failure and one killed unresolved
attempt. Its conservative charge is 28,035 tokens and 2,621.5458 seconds.
Retain the complete charge of the unresolved parent attempt; do not treat its
missing receipt or killed process as zero work. Preparation must authenticate
the terminal failure and exited collector before enumerating pending work.

The child catalog is exactly the original ordered catalog minus the six
completed job IDs: 15 control and 15 extended jobs. Preserve all job IDs,
questions, original per-cell seeds, draw numbers, arm order, model/tokenizer
revision, MPS backend, prompt, sampler, closure/EOS IDs, answer budget and both
immutable configurations. There is no new question allocation or draw.
Completed parent outputs are reused only with their original job, attempt,
reservation, receipt and implementation provenance. Never overwrite them.

The new external job deadline is **1,800 monotonic seconds** rather than the
parent's 600 seconds. This is an explicit execution deviation. The 600-second
limit serialized inside each frozen configuration remains part of its job
identity and is not edited. Pass the child's external deadline to the backend;
never derive a new seed or identity from the longer timeout. Setup retains its
900-second monotonic limit and operation watchdogs retain five seconds of
polling/termination grace. A longer deadline does not guarantee completion.

One child launch, setup and invocation are permitted. Stop at the first failure;
there is no automatic retry, explicit child resume or third parent restart.
Durably reserve before source/asset validation, model loading or generation.
Missing child receipts retain their full token/time reservation. Failed and
completed attempt archives are immutable, and completed results are published
only for valid non-timeout outputs with a matching settled receipt.

The child has its own eight-hour wall/charged limit, measured from its first
launch and using the maximum of elapsed wall age and accumulated charged
setup/job seconds. Sleep and operator gaps count against this wall clock.
The parent's clock, accounting and terminal status do not reset. Keep a single
160,000-token ceiling across old conservative charges and new work. Pending
response reservations are 107,580 tokens, so the planned combined maximum is
`28,035 + 107,580 = 135,615`; actual settled charges may be lower. Check the
combined token ceiling and the child's live wall boundary before every
operation and again before references and terminal completion. Late read-only
audits may use the frozen collection-end age; they do not permit late scoring.

Load one weight module/tokenizer and reuse it through separate immutable 2k
and 4k backend configuration instances. Verify each selected engine against
the frozen arm metadata and job configuration. No weight update, adapter,
cache purge, diagnostic model probe, decoder change or second model copy is
authorized. Keep Docker running and the Mac open/on AC. Use the existing
process-scoped activity guard and owned temporary system/idle sleep assertion;
do not touch unrelated assertions or processes. Preserve read-only native
hardware snapshots at job admission and coarse stall times.
Each active job may additionally receive one snapshot at 600 seconds and one
at 1,200 seconds; missing host observations are recorded as unavailable.
Memory pressure, swap, VM activity and throughput are descriptive observations, not causal
attributions. Sampled RSS is not total unified-memory accounting.

The new private endpoint requires all six original and 30 child responses,
exited collector, completed child ledger, both-accounting ceilings and exact
parent/source/prepared-input byte preservation. Require all 18 matched
new-control/new-extended reasoning prefixes before opening references.
Compare through the first close/EOS or shorter reasoning allowance; final
answer streams may differ. Prefix mismatch is an engineering failure, never
permission to choose another seed or remove a pair. No MPS determinism
guarantee is assumed.

Only this full new endpoint permits reopening exactly the 11 selected upstream
training references for the 36 combined bridge outputs using unchanged v7.
Authenticate the private child finalizer and its request before the access
marker, select the declared training indices only, and recheck live accounting
and preservation at the reference callback. Do not call the old collector's
scoring/finalization/authentication functions or reopen the old 64-question
endpoint. The question snapshot stays gold-free; no gold file is written.
Write one access marker and one validated score sidecar under the child. A
marker without a valid cache blocks another fetch; a valid cache must return
without references. Mathematical correctness analysis is locked until the
full combined endpoint. No sealed labels or new role are involved.

Keep the frozen descriptive comparison: new 4k minus new 2k correctness,
actual generated tokens and utility at lambda .05. Include reasoning, answer
and inserted tokens; the extra 2,048 allowance is not a fixed actual cost.
Average paired cell differences within each question, then equally over 11
questions for the primary summary. The 18-cell mean is secondary; seven
questions have two cells and four have one. Bootstrap 2,000 whole-question
replicates with `random.Random(20261020).choices(groups, k=11)` from the
question-ID-sorted groups, sharing each sample across metrics. Use linearly
interpolated 2.5th/97.5th percentiles. No threshold fit or policy selection
occurs. Report the inherited failures, partial-output conservative charge and
longer external deadline alongside these cap-enriched development summaries.
They do not establish fresh generalization, causal speed, whole-panel
superiority, acquisition promotion or novelty.

Completion receives its own terminal status/report. The stopped original
status and failed requests remain unchanged. A cached audit may inspect the
closed child after its live wall ceiling, but no completed collector, prepare,
score or finalizer is restarted. A child failure requires a new user decision
and separate prospective protocol; it supplies no retry slot itself.
