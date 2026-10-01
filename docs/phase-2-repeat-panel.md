# Phase 2: independent-draw routing signal

Local collection started, 2026-10-01; [runtime recovery](phase-2-runtime-recovery.md)
is active after timeouts. Results are pending. The purpose is to establish whether router
supervision reproduces across independent draws and predicts useful escalation
on unseen questions before scaling adaptive acquisition. This is a small
diagnostic study; it cannot establish the roadmap's acquisition contribution.

## Fixed data and inference

Use exactly the 50 `repeat` questions in the unchanged
`data-efficiency-v1/allocations/manifest.json`, disjoint from the bridge,
acquisition, validation and both confirmations. The existing allocation digest
is `c2b28b3d32612517f549a054ae2107185f26181e487b22d027ed59c207d3a4fd`.
`research_data.load_allocation` verifies live source/inventory hashes, upstream
indices, normalized prompt exclusions and all role boundaries before use.

The separate `repeat-panel-v1/protocol.json` pins generation permission to that
allocation and the repeat role. Collection has a fixed endpoint of **800
completed responses**: 50 questions × eight independent draws × two modes.
Every question/mode/draw has a distinct deterministic seed. Responses are paired
by sample index solely for replay; their seeds differ between modes.

Keep the bridged Qwen3-1.7B revision, prompt, 2,048/512 caps, decoders, closure,
full EOS handling, device and dtype. The new seed is 20261002. The cumulative
local ceilings are 1,400,000 charged tokens and 12 hours, including setup,
interruptions and retries, with 600 seconds per job and a three-consecutive-
failure stop. The bridge projects 7.04 generation hours excluding setup/retries;
this is a projection on different questions, not a guarantee. Cloud budget for
this local protocol is $0. The maximum planned job reservations are checked
against the token ceiling before freezing.

The question-only dataset contains `questions.json` and a manifest with
`gold_sha256: null`. No repeat reference answer is read during preparation,
collection or status inspection. Only after **every** planned job completes may
the scorer project the pinned upstream **training** Arrow to the answer column
and fetch exactly the 50 selected row indices. It never reads historical shared
gold or official-test gold, and it never adds gold to the question dataset.
Generation records keep their deferred-gold marker; a separate score sidecar
pins the selected reference-answer hash, all records and numeric-v7 implementation.

## Frozen estimands

For question `q` and paired draw `s`, let `D` be the already-paid direct draft
and `T` a fresh thinking call. The escalation target at `λ = .05` is:

```
G(q,s) = correct(T) - correct(D) - .05 * charged_tokens(T) / 1000
```

The direct cost is sunk at the routing decision. Report total policy cost as
`D_tokens + escalate * T_tokens`, with corresponding total seconds and final
correctness. Parse failures and incomplete answers count as incorrect. Also
report the separate standalone mode advantage:

```
correct(T) - correct(D) - .05 * (T_tokens - D_tokens) / 1000
```

These targets differ because their decision states differ. No 8×8 pairing or
pseudo-independent state expansion is used. Every question contributes equally
to reported means and uncertainty.

## Independent halves and held-out questions

- Half A is sample indices 0–3; half B is 4–7. For k=1/2/4, use the first k
  draws of each half. Report direct/thinking accuracy and cost, target signs
  including ties, and split-half gain differences.
- Compare A's per-question gain estimate with B's and vice versa. The pooled
  comparator is the mean estimate from the other 49 questions in the prediction
  half. Report the symmetrized per-question MSE improvement and a grouped interval.
- Freeze five question-only hash folds, ten questions per outer fold. All draws
  of an outer test question stay outside model fitting and tuning.
- For each k, fit using training questions' first k A draws and evaluate outer
  test questions on all four B draws; repeat B→A. Inner tuning uses only the
  same acquired first-k training-half draws. Opposite-half training outcomes
  cannot select hyperparameters or baselines.
- A secondary eight-draw model trains on all eight draws of training questions
  and evaluates all eight draws of held-out questions. Eight-draw labels have
  no independent same-question eight-draw replica in this cache.

## Models, acquisition accounting and gates

Policies are always accept, always escalate after a draft, a training-fitted
post-warper confidence threshold, question-only ridge, solver-only ridge and
combined ridge. The question features are pinned MiniLM plus three lexical
features, computed without outcomes before collection. Draft inputs are only
post-warper mean log probability, log answer length, v7 parse validity and
truncation. No correctness, gold, thinking output or future direct draft enters
the deployed decision interface. Raw confidence is retained in generation
records but is not an additional selectable primary model in this protocol.

All three learned feature families share ridge and alpha `{1,10,100}`.
Standardization is fitted inside training folds. Four inner question folds tune
alpha by held-out utility; exact alpha ties choose the larger alpha. Confidence
thresholds are fitted on inner training observations and evaluated on inner
validation questions. Select the strongest eligible accept/escalate/confidence
baseline using inner validation only; never select on outer test utility.
The **combined** model is the predeclared progression learner. The other learned
models remain reported diagnostics, without a best-model switch after outcomes.

For each outer fold, record the actual direct and thinking tokens revealed in
its training condition, plus the number of pairs/responses. Inner reuse is not
another acquisition. Report the entire 800-response cache expenditure, setup
and retries separately; cross-validation folds/conditions reuse that cache.
Frozen embedding load/encode timing is retained. Cached generation seconds and
token utility do not establish live router latency or net deployment speed.

Use 2,000 paired whole-question bootstrap draws, seed 20261002, with two-sided
90% intervals. These are diagnostic intervals conditional on the fixed OOF fits,
not uncertainty from repeating the full training process. There are 50 grouped
evaluation units. Draw-level state counts are reported only descriptively.

Proceed to adaptive acquisition only if **all** fixed gates pass:

1. Four-draw split-half MSE improvement is positive with a positive interval
   lower bound.
2. Combined four-draw utility exceeds the training-selected baseline in both
   A→B and B→A point estimates.
3. Their average per-question gain is at least .01 utility, with a positive
   grouped interval lower bound.
4. The eight-draw combined comparison does not reverse direction.
5. At least ten distinct questions have a direct/thinking correctness difference
   in some paired draw. Report rescue and harm counts separately.

If any gate fails, retain the diagnostic result and narrow or stop acquisition
scaling on this signal. This gate is distinct from the later normalized-AULC
primary endpoint; it does not constitute publication novelty or confirmation.

## Implementation and operation

The additive modules are `research_repeat.py` and `repeat_stats.py`.
Existing bridge generation/scoring modules and configuration stay byte-identical.
Preparation checks the completed bridge gates and accepted v7 preflight, freezes
the question data, encoder features, folds, backend/environment, exact jobs,
scorer/source digests and package snapshots, then marks generation unstarted.
It refuses preexisting generation directories. Every later command checks the
same identities, and every attempt/setup session, including orphaned reservations
and superseded retries, must follow the protocol freeze. The existing runner
provides cumulative budgets, single-writer locks and resumability; the new study
lock prevents duplicate study collectors and scoring during collection.

Commands from the repository root with the pinned environment:

```sh
HF_HUB_OFFLINE=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -m reasoning_budget.research_repeat prepare
.venv/bin/python -m reasoning_budget.research_repeat status
```

Collection is a separate local command. It does not automatically retry in a
new process or analyze a partial endpoint; a later resume uses the same protocol
and cumulative limits:

```sh
HF_HUB_OFFLINE=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -m reasoning_budget.research_repeat collect
.venv/bin/python -m reasoning_budget.research_repeat analyze
```

The dedicated detached supervisor starts this exact protocol:

```sh
HF_HUB_OFFLINE=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/repeat_background_worker.py
.venv/bin/python scripts/repeat_background_worker.py --status
```

It uses `caffeinate` to inhibit idle sleep, single-supervisor and collection locks,
and an atomic heartbeat every 60 seconds. Its checksummed operational policy pins
the protocol and both operational script hashes. A durable invocation journal
allows the initial collector and at most one automatic resume, including across
supervisor restarts. Both retain the same generation ledger and 1.4M-token/
12-hour cumulative limits. The supervisor has a separate 14-hour wall-clock
monitoring ceiling to allow analysis after collection; it cannot extend the
generation budget. Collector errors require inspection. A zero exit code alone
does not establish completion.

Only after all 800 responses complete and collection exits does it run the frozen
analysis, then `scripts/verify_phase2_repeat.py`. That verifier refuses incomplete
collection before opening scores or the report, reads no reference answers, and
checks job/cell coverage, scorer/report identity, all-attempt/setup accounting,
token-ID counts, frozen folds, training acquisition costs, policy utility and
protected originals. Terminal status distinguishes completion with passing gates
from completion with failed gates. It never launches acquisition, confirmation,
Jev/RL, or cloud jobs.

Operational artifacts in `repeat-panel-v1/` are `background-status.json`,
`background-worker.log`, checksummed `background-policy.json` and
`background-journal.json`, `background-launch-verification.json`, and, only after successful endpoint analysis/audit,
`background-verification.json`. Inspect these instead of repeated chat polling.
Do not edit the operational scripts while the supervisor runs or manually start
another collector. The completed bridge supervisor remains specific to its own
study. The v7 standalone bridge CLI remains restricted; repeat scoring uses this
study's complete-endpoint guard and separate sidecar. Preparation accesses no
repeat reference answers.

## Actual preparation checkpoint

Prepared from committed source **`272403f`**. Real cached tokenizer inspection
resolved `qwen3-boxed-budget-v3`, Qwen revision
`70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`, MPS/float16, EOS
`[151643,151645]` and closure `[151668,271]`; Qwen weights were not loaded.
The pinned MiniLM question encoder produced a frozen **50 × 387** feature
matrix on CPU. Every outer fold has ten questions. All 800 job IDs and seeds
are unique. Maximum job reservations total **1,229,600 tokens**, within the
1,400,000 ceiling.

- Repeat protocol: `8b01db2cbb7b8d1777c40aa0a873f4626e4c6b2a04e9135a377a085a76f3c812`.
- Repeat implementation: `cd3bf4240b7f31921fe71c2e10120f0454527263e570b6f6bd5f67b17e5416db`.
- V7 scorer: `c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964`.

All **363 offline tests** pass, including 22 new repeat tests; Ruff and whitespace
checks pass. Meaningful synthetic checks cover held-out label invariance,
unused-draw invariance in inner tuning, correct sunk/total-cost arithmetic,
grouped bootstrap, deterministic ties, selected-only reference access, incomplete
and over-budget gold locks, resume without duplicates, changed data/features/
sources, score-cache tampering, pre-freeze/orphan attempts and deferred gold.
Agents reviewed allocation/source isolation and statistical design; the existing
human-audit waiver remains unchanged. Agent review found the inner tuning leak,
formula/config issues and orphan-attempt boundary; all were repaired before freeze.

Checksummed `repeat-panel-v1/preflight-verification.json` verifies the unchanged
allocation, decoder, job/fold identities, feature dimensions, frozen package,
scorer and all **2,319 protected original files**. Original bridge scores and
cached responses remain unchanged. Old confirmation remains unstarted. Preparation
status was **prepared, 0/800, generation not started, analysis locked**. No repeat
reference answer or official-test gold was opened; no real solver response,
cloud job or expenditure occurred in this checkpoint.

`endpoint-lock-verification.json` additionally confirms repeated preparation
preserves protocol bytes and a real unstarted scoring call rejects before
reference-answer access, without creating scores or a result report.

Artifacts under `artifacts/research/data-efficiency-v1/repeat-panel-v1/` are
`protocol.json`, `config.yaml`, `question-features.json`, `feature-cache/`,
`frozen_code/reasoning_budget/`, `status.json` and `preflight-verification.json`.
The question-only role lives under `data/repeat/`. No run manifest, score artifact
or result report existed at preparation. Bounded collection under this exact
protocol follows in the next checkpoint.

## Collection checkpoint

The user authorized local collection on 2026-10-01. The operational supervisor
and verifier were committed at **`3505a77`**, outside the frozen package. The
363 existing tests and nine new operational tests pass; Ruff and whitespace
checks pass. A real pre-launch verifier call rejected the incomplete endpoint
before scores/report access, and all **2,319 protected files** retained their
hashes. The generation protocol, source `272403f`, config, roles and scorer are
unchanged.

The detached supervisor started at **2026-10-01 17:37:19 UTC** (23:07:19 IST),
PID **27132**, with collector PID **27339**. The first invocation is durably
reserved; no automatic resume has been used. Cached Qwen weights loaded locally
on the frozen MPS backend. At **17:40:49 UTC**, launch verification recorded
**2/800 completed, zero failures**, both supervisor/collector locks held, no
scores/report and unchanged protocol/policy hashes. Its ledger included active
reservations, so charged-token/time status is not just completed-response cost.
The proof is `background-launch-verification.json`.
The live heartbeat and run ledger are authoritative
for progress; results and scoring remain locked until 800 completed responses.
The 7.04-hour generation projection remains an estimate, with the original
1.4M-token/12-hour cumulative ceilings and a separate 14-hour supervisor ceiling.

Operational policy digest:
`dd24204476f10e7334005c6de4e6c33833221d26b14edb0e530389f4a44b50be`.
Its supervisor and verifier hashes are
`7e1ea514800726de4a1429b471721c5f4f82d5b03d0c05bf598d0da456f8ffa7`
and `42ad7e8e05c4ea0bfb52c81045642537613a301ebf3340e8aa6209d56bdbe083`.
Old confirmation is unstarted, official-test gold stays sealed and cloud
expenditure is $0. Analysis and independent endpoint verification are automatic
after completion; progression to later phases still requires review of the
predeclared gates.

## Runtime recovery checkpoint

The original supervisor stopped at 51/800 after its initial invocation and one
automatic resume each hit three consecutive timeouts. Its status/log/policy and
exhausted 2/2 journal are preserved. The [diagnosis and recovery record](phase-2-runtime-recovery.md)
documents the abrupt throughput collapse, Docker startup correlation and
uncertainty about cause. The user authorized repair and requested Docker remain
running. A separate, single-invocation recovery wrapper from source **`3698102`**
is running under the same protocol, jobs, seeds and cumulative limits. It adds
process-scoped activity protection, read-only telemetry and a stop after the
first durable failed job. All **386 offline tests**, Ruff and diff checks pass.
Current operational progress is now `recovery-v1/status.json`; original
`background-status.json` is a frozen record of the stopped supervisor. Analysis
and reference access remain locked until 800 completed responses.

Recovery verification at 2026-10-01 22:38:16 UTC records **59/800 complete**,
zero failed current jobs and all three previously timed-out cells completed at
17–22 tokens/s. Archived token prefixes match. All original completed responses,
attempts/setup records, supervisor artifacts and 2,319 protected originals are
unchanged. The separate proof is `recovery-v1/startup-verification.json`; full
endpoint results remain pending.
