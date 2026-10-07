# Local matched 1.7B cap-bridge runtime

This additive runtime implements the reviewed development cap plan
`553c514d…13112e2e`. The fresh 0.6B validation has completed and its independent
review passed; its scientific screen did not pass. That result remains
unchanged. This bridge addresses a different engineering hypothesis, not a
fresh validation of either router. Its 18 cells on 11 old development questions
were selected solely by original forced-closure metadata.

Freeze `scripts/qwen17_cap_bridge_collect.py`,
`tests/test_qwen17_cap_bridge_collect.py` and this document before runtime
preparation. Preparation writes only `qwen17-cap-bridge-v1/runtime-v1/`, verifies
the reviewed cap plan, question snapshot, original sources, package environment,
model-asset pins and validation ordering evidence, and freezes every manual
job and resource limit. It constructs no model and opens no references. An
independent audit of the actual prepared runtime must precede launch. The
earlier prep-only plan remains immutable; this separate runtime explicitly
implements its previously locked generation stage.

There are exactly 36 thinking jobs: one new 2,048-token control and one new
4,096-token response for each original capped cell. Preserve the original
question metadata, draw number and explicit generation seed in both arms;
36 job IDs are distinct, while the 18 per-cell seeds deliberately repeat across
matched arms. Do not derive seeds from arm names, new directories or changed
caps. The original 512-token answer budget, closure/EOS IDs, prompt, sampled
decoder, local pinned model/tokenizer and MPS/float16/SDPA remain fixed. Use the
manual catalog, never a generic runner that could expand the 11 questions into
additional draws or direct jobs.

Pair ordering is fixed and balanced: even-indexed cells run control then
extended; odd-indexed cells run extended then control. Both immutable backend
configuration instances share one loaded weight module and tokenizer. Load
weights once per invocation, retain distinct reasoning-cap configuration
objects and verify each engine against its arm/job. Do not silently change
one engine's configuration or hold two full copies of the model. No optimizer,
gradient update, adapter, cloud inference or Kaggle job belongs to this runtime.

The response maximum is `18 × (2,562 + 4,610) = 129,096` tokens. One shared
160,000-token/four-hour budget covers both arms, setup, interruptions, unknown
reservations and explicit retries. Time admission uses the maximum of total
charged setup/attempt seconds and wall age from the first launch, including
sleep and gaps. Setup/job limits are 900/600 awake monotonic seconds; operation
watchdogs retain five seconds of polling/termination grace. At most two
setups, collector invocations and supervisor launches exist: one initial and
one explicit runtime-failure resume. Stop on the first failure; no automatic
resume, quality retry, budget reset or seed search. Integrity, resource, budget and
prefix-engineering failures do not authorize a resume.

Reserve tokens/time durably before work; missing receipts retain the complete
reservation. Preserve failed attempts separately and never replace a completed
result. On explicit resume, a previously published valid output may be retained
only with its matching archive, reservation, setup and observed failed-process
provenance; its unknown charge remains conservative. Every current operation
must settle. Revalidate source/configuration/model identities before model work
and preserve all old study files. Source/ledger corruption blocks further work.

Keep the Mac open and connected to AC. The detached native process uses the
existing temporary activity guard and `caffeinate -s -i`; Docker stays running.
Monitor the owned child only, with two-second polling and a 9 GiB sampled RSS
ceiling. RSS is not total unified-memory accounting. Assertions and cooperative
timeouts cannot guarantee prevention of forced sleep or instantaneous resource
enforcement. A four-hour boundary is a stop limit, not a completion promise.

Before any new reference or mathematical correctness evaluation, require all
36 valid responses, exited collectors, global accounting, source/old-artifact
preservation and **all 18 new-arm shared-reasoning-prefix checks**. Compare the
prefix only through the first close/EOS or shorter reasoning allowance; answer
streams after forced closure may legitimately differ. A mismatch is a recorded
engineering failure, not permission to rerun or repair a seed. No bitwise MPS
determinism is assumed. Separately report new 2k versus cached-old replay as an
engineering diagnostic. Never borrow old outputs, labels or timing as the new
control arm.

The new full endpoint alone permits reopening exactly the 11 selected
upstream-training references to score the **new** outputs using unchanged
numeric-v7. This is explicitly scoped to the new user-authorized bridge, not
an old 64-question scoring command. Write one reference-access marker before
fetching; preserve reference/scorer/record hashes in a separate score sidecar.
The question snapshot keeps `gold_sha256: null` and no gold file. A marker
without a valid score cache blocks a second fetch; valid cached scores return
without reopening references. Keep the other 53 development references and
all official-test/validation/confirmation outcomes out of this endpoint.

For each cell, compare new extended minus new control correctness, actual
generated tokens and utility at λ=.05. Charge reasoning, answer and inserted
tokens. The +2,048 increase is a reasoning allowance, not a fixed actual token
cost: answer lengths can change too. Direct draft cost cancels between cap
arms; any optional total post-direct metric must identify the cached direct
cost reused identically in both arms. Post-thinking fallback or a new routing
policy is not selected from these results.

Primary descriptive metrics average the available cell differences within each
question, then equally over the 11 questions. Report the distinct 18-cell mean
as a secondary summary; seven questions contribute two cells and four one.
Bootstrap 2,000 whole-question draws with Python `random.Random(20261020)`:
each replicate uses `rng.choices(groups, k=11)` with replacement from the
question-ID-sorted group list. Use linearly interpolated 2.5th/97.5th percentiles
and share each sampled group across all arm metrics. These intervals condition
on the old cap trigger and fixed selected cells. They do not establish fresh
generalization, whole-panel superiority, live latency, acquisition promotion
or a novel contribution. Higher accuracy can still lose token utility.

After source freeze, reviewed preparation and the actual-input launch audit,
the operator commands are runtime `prepare`, `verify`, `status` and `launch`.
The private collector, supervisor and finalizer are not operator entry points.
Use `launch(resume=True)`/the dedicated resume command only after a reviewed
eligible runtime stop within the same journals and limits. Never relaunch a
completed endpoint. All run records, labels and old budget failures remain
preserved regardless of the result.
