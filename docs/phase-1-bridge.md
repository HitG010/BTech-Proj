# Phase 1, checkpoint 3: disjoint roles and paired protocol bridge

Allocation frozen 2026-10-01 on `codex/research-data-efficiency`. The bridge
collector is implemented and verified offline; real local collection is running
under a detached supervisor. This record will be updated after the fixed
endpoint. It follows
[protocol reconciliation](phase-1-protocol-reconciliation.md).

## Frozen allocation

The allocation reads only the cached GSM8K **training question column**.
Revision: `740312add88f781978c0658806c59bc2815b9866`; 7,473 source rows;
Arrow raw SHA-256:
`6146bca074f4c6c5e07de7e96cc968adab3833dbdafeda21830f27558eea3d9b`.

| Role | Questions | Origin and use |
|---|---:|---|
| Bridge | 25 | Unused original reserved training IDs; protocol diagnostic |
| Repeat panel | 50 | Disjoint reserved IDs; later 1/2/4/8-draw supervision check |
| Acquisition | 1,200 | One common pool: 175 reserved plus 1,025 unallocated |
| Validation | 200 | Threshold/model selection; excluded from acquisition |
| New confirmation | 2,000 | Selected and sealed for a later frozen candidate |
| Reserve | 548 | No collection planned in this checkpoint |

The 250 unused reserved IDs exclude all 150 previously influenced training and
diagnostic IDs, plus any additional historical run/dataset IDs or normalized
prompts. The external pool has 3,773 questions, excluding the entire base
allocation and every historical/frozen dataset and run. The old 3,100-question
confirmation and official 500-test allocation remain separate and unchanged.

Seed `20261001` sorts each source stratum by the canonical digest of
`{"seed": seed, "question": {"id": id, "prompt": normalized_prompt}}`.
Contiguous slices assign the roles. Source row indices are recorded for later
selected-answer access; they do not influence hash ordering. All roles have
unique IDs and normalized prompts. Grouping is by question; template families
are unknown, so normalized deduplication is not a semantic-family leakage claim.

The checksummed, gold-free manifest is
`artifacts/research/data-efficiency-v1/allocations/manifest.json`, payload digest
`c2b28b3d32612517f549a054ae2107185f26181e487b22d027ed59c207d3a4fd`.
It snapshots source revision/file hashes, every historical input, constraints,
roles and source strata. Reload verifies live inputs, source-index membership,
prior/frozen exclusions, and role boundaries; repeating preparation cannot
rewrite a changed allocation. Only bridge generation is currently permitted by
the manifest. No role-selection answer or model outcome was consulted.

## Fixed bridge design

- Same 25 question objects and seeds in both arms; two independent draws per
  direct/thinking mode, **100 responses per arm, 200 total**.
- Retain Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`, original
  boxed-answer prompt, 2,048/512 caps, closure IDs `[151668,271]`, decoding,
  batch-one MPS/float16/SDPA and the same local software environment.
- Legacy code is pinned at `6999eb5`, using the single EOS `151645`. New code
  uses `qwen3-boxed-budget-v3`, EOS `[151643,151645]`, and separately records raw
  direct confidence. Code/config/environment snapshots and matched job seeds
  freeze before the first generation attempt.
- Serial order: legacy, then v3. Each arm has a 200,000-token and four-hour
  cumulative ceiling, with 600 seconds per job. Maximum planned reservation
  is 153,700 tokens per arm. At most three bounded worker invocations per arm
  occur in a run command; reruns retain the same ledger and limits. The other
  arm can still collect under its cap if one is incomplete.
- Only the selected 25 training answers are materialized after all roles freeze.
  Workers verify question/config files and never open gold. Scoring uses common
  `numeric-v5` on both arms only after all 200 responses complete. Incomplete
  coverage is reported operationally; outcomes are not imputed or compared.

The preselected engineering gates are complete matched collection and valid
provenance/accounting, finite raw confidence on every v3 direct response,
at most 5% answer truncation and 5% parse failure in each v3 mode, no observed
accuracy loss larger than 10 percentage points in either mode, and a projected
50-question/eight-draw-per-mode panel of at most 48 local hours. A loss threshold
is a diagnostic trigger, not an inferiority hypothesis test.

Analysis reports accuracy, charged tokens including insertion, utility at
`lambda=.05`, prompt work, stage/result timing, setup/retries, memory, raw
confidence coverage, token/answer agreement and terminations. Paired intervals
resample whole questions, retaining both draws (2,000 draws, seed `20261001`).
The small bridge cannot establish superiority, equivalence, novelty, or deployed
router latency. Serial order and MPS thermal variation limit timing comparisons.

## Commands and verification

From the repository root:

```sh
.venv/bin/python -c 'from reasoning_budget.research_data import prepare; print(prepare())'
# Device access is required for cached tokenizer/backend inspection and generation.
.venv/bin/python -m reasoning_budget.research_bridge prepare
HF_HUB_OFFLINE=1 caffeinate -i .venv/bin/python -m reasoning_budget.research_bridge run \
  artifacts/research/data-efficiency-v1/bridge-v1
.venv/bin/python -m reasoning_budget.research_bridge status \
  artifacts/research/data-efficiency-v1/bridge-v1
# Detach supervision; reuse an active collector or resume under unchanged limits.
.venv/bin/python scripts/bridge_background_worker.py
.venv/bin/python scripts/bridge_background_worker.py --status
```

The collector writes `legacy.log`, `v3.log`, per-arm runs/completion records,
checksummed `protocol.json`, archived sources, `report.json`, and `report.md`.
Generation and scoring are separate. The official test stays sealed; the human
audit waiver remains in effect. Cloud spending is **$0**; collection is local.

Before real collection: 212 offline tests, Ruff and whitespace checks pass.
New tests cover role exclusions/source membership, re-enveloped boundary swaps,
unchanged preparation, paired seeds, frozen-code rejection, source imports,
complete-endpoint gold locking, independent arm caps, finite scalar reporting,
and resume without repeating completed responses. Two agents audited the data
and protocol; agent review is not human validation.

## Collection result

Collection started from frozen code `bbcaac2`, with legacy `6999eb5`;
protocol payload digest
`ed5f40e722ef869c33a396c55ec57ab3b741a01ee6014612c8c8925376968066`.
At 2026-09-30 22:30:26 UTC (2026-10-01 local), legacy had completed 49/100
responses with zero failures; v3 had not started. Comparative outcomes remain
locked. This is a dated progress snapshot, not a result.

At the user's request, `scripts/bridge_background_worker.py` now supervises the
collector in a detached process with idle-sleep prevention and a 60-second
operational heartbeat. It checks the study and both arm locks before starting
at most one automatic resume, preserving completed cells and the original
cumulative budgets. It stops with an attention record on errors, incomplete
coverage after that resume, or its nine-hour monitoring limit. It never starts
the repeat panel, confirmation or any cloud job.

After all 200 responses finish and collection releases its locks, the worker
ensures the frozen report exists and runs
`scripts/verify_phase1_bridge.py`. This separate audit checks common v5 scores,
matched seeds/cells, token IDs and charges, attempts/setup/reservations, summary
arithmetic, whole-question bootstrap intervals, all gates, and protected hashes.
It records checksummed `phase-1-step-3/verification.json`. A manual pre-endpoint
invocation correctly rejected analysis before gold access. Both new scripts pass
Ruff; no frozen package source, configuration or analysis rule was changed.

Live state and any completion/error decision are in
`bridge-v1/background-status.json`; worker output is in
`bridge-v1/background-worker.log`. Completed output will be `bridge-v1/report.md`
and `report.json`. Status token/time totals include active or unreleased
reservations, so they are not elapsed wall-clock measurements during collection.
The report's MPS memory maximum samples post-response allocation; it is not a
true peak-memory measurement.

The fixed endpoint and gate review remain pending. Do not advance the
repeated-draw panel until they pass. Preservation evidence lives under
`artifacts/research/data-efficiency-v1/phase-1-step-3/`.
