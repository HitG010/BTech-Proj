# Phase 1, checkpoint 3: disjoint roles and paired protocol bridge

Allocation frozen 2026-10-01 on `codex/research-data-efficiency`. The bridge
collector completed its fixed endpoint and passed all six engineering gates.
Background verification finished on 2026-10-01 local time. It follows
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
Both arms completed **100/100 responses**, with zero failed attempts, one model
loading session per arm, and no automatic resume. The detached supervisor
recorded completion at 2026-09-30 23:52:04 UTC (2026-10-01 05:22:04 IST).
Comparative scoring ran only after all 200 responses finished.

| Arm | Mode | Correct / responses | Charged tokens / response | Seconds / response | Parse failures | Answer truncations |
|---|---|---:|---:|---:|---:|---:|
| Legacy | Direct | 40/50 (80%) | 211.00 | 8.23 | 2/50 (4%) | 1/50 (2%) |
| Legacy | Thinking | 47/50 (94%) | 1,420.86 | 57.09 | 2/50 (4%) | 2/50 (4%) |
| V3 | Direct | 40/50 (80%) | 211.00 | 8.10 | 2/50 (4%) | 1/50 (2%) |
| V3 | Thinking | 47/50 (94%) | 1,420.86 | 55.30 | 2/50 (4%) | 2/50 (4%) |

All **100 matched cells have identical token sequences, terminations and extracted
answers** across arms. Paired accuracy, charged-token and utility differences
are zero, with bootstrap intervals `[0, 0]` on these 25 questions. This exact
observed match supports continuing with v3, but does not establish equivalence
on unseen inputs or a novel router result. Each arm charged 81,593 tokens,
including 16 inserted closure tokens: **163,186 charged tokens total**. Recorded
inference/attempt/setup time was 0.9107 legacy hours plus 0.8833 v3 hours;
setup accounted for 12.26 and 9.67 seconds respectively. No retries or cloud
expenditure occurred.

| Predeclared engineering gate | Observed result | Decision |
|---|---|---|
| Complete matched collection and valid provenance/accounting | 200/200 completed; matched seeds; frozen code/config and ledger checks pass | Pass |
| Finite v3 raw direct confidence on every response | 50/50 | Pass |
| At most 5% answer truncation in each v3 mode | Direct 2%; thinking 4% | Pass |
| At most 5% parser failure in each v3 mode | Direct 4%; thinking 4% | Pass |
| No observed accuracy loss larger than 10 percentage points per mode | Zero loss in both modes | Pass |
| Projected 50-question/eight-draw-per-mode panel at most 48 local hours | 7.04 hours, excluding setup/retries | Pass |

The 800-response repeat-panel projection is
`50 × 8 × (8.0972 + 55.3022) / 3600 = 7.0444` hours. It is a planning estimate,
not a guaranteed runtime. The bridge supports local collection; no cloud pilot
is needed for this checkpoint.

### Remaining limitations and next preflight

- Every naturally terminated response ended with EOS `151645` (97/100 per arm);
  none generated `151643`. The added EOS stop path is configured and tested
  offline, but was not exercised by real outputs here. Eight thinking responses
  per arm used forced closure. Broader EOS equivalence is untested.
- Three v3 parse failures are incomplete, answer-capped responses. The fourth,
  direct sample 0 of `gsm8k-train-b4edeb1f526dc57ea197`, boxes intermediate totals
  170 and 180 before a final answer of 180, matching the isolated bridge gold.
  The frozen v5 rule rejects differing explicit boxes as `conflicting`. This is
  a conservative scoring limitation, not evidence that the model's final answer
  was numerically wrong. Keep the primary bridge scores unchanged. Before new
  repeated-label collection, document a gold-independent, adversarially checked
  scoring policy for intermediate versus final claims; any change needs its own
  version and frozen protocol rather than silently replacing v5.
- Finite confidence coverage establishes measurement availability, not confidence
  calibration or predictive usefulness. Those are Phase 2 questions.
- V3's observed timing is lower, but serial arm order and MPS thermal variation
  prevent a causal speed-improvement claim. The observed MPS allocation maximum
  is sampled after each response, not the actual generation-time memory peak.
- The loss and failure thresholds are engineering screens on 25 questions.
  Passing them does not establish superiority, noninferiority, equivalence,
  novelty or task/model generalization.

At the user's request, `scripts/bridge_background_worker.py` supervised the
collector in a detached process with idle-sleep prevention and a 60-second
operational heartbeat. It checks the study and both arm locks before starting
at most one automatic resume, preserving completed cells and the original
cumulative budgets. It stops with an attention record on errors, incomplete
coverage after that resume, or its nine-hour monitoring limit. It never starts
the repeat panel, confirmation or any cloud job.

After all 200 responses finished and collection released its locks, the worker
checked the frozen report and ran
`scripts/verify_phase1_bridge.py`. This separate audit checks common v5 scores,
matched seeds/cells, token IDs and charges, attempts/setup/reservations, summary
arithmetic, whole-question bootstrap intervals, all gates, and protected hashes.
It recorded checksummed `phase-1-step-3/verification.json`. A manual pre-endpoint
invocation correctly rejected analysis before gold access. Both new scripts pass
Ruff; no frozen package source, configuration or analysis rule was changed.

The final state (`complete`) and gate decision are in
`bridge-v1/background-status.json`; worker output is in
`bridge-v1/background-worker.log`. Completed output is `bridge-v1/report.md`
and `report.json`. Status token/time totals include active or unreleased
reservations, so they are not elapsed wall-clock measurements during collection.
The report's MPS memory maximum samples post-response allocation; it is not a
true peak-memory measurement.

The endpoint audit passed: common frozen-v5 rescoring, cache digests, paired
arithmetic/bootstrap, stage token counts, ledgers and budgets all agree. It
reuses the same scorer and is not a second independently implemented parser or
human validation. All 14 protected artifacts and 21 legacy Python sources retain
their hashes; the old 3,100-question confirmation remains unstarted, and official
test gold stays sealed. Independent agent review agrees with the engineering
decision and the limitations above. Preservation evidence lives under
`artifacts/research/data-efficiency-v1/phase-1-step-3/`.

**Checkpoint 3 is complete.** Next is Phase 2: freeze a separate protocol for the
already allocated 50-question repeat panel, resolve the scoring-policy preflight,
and test whether repeated labels and solver-aware features supply reproducible
routing signal. The current allocation permits only bridge generation; a new
role-specific protocol must reference its unchanged manifest. No repeat-panel,
acquisition, confirmation or cloud generation was launched in this checkpoint.

**Later parser preflight, 2026-10-01:** the documented intermediate-box issue is
resolved by separate opt-in `numeric-v7`; see [the policy and validation
record](parser-preflight.md). The gold-free 1,100-response check changed only the
same final-180 case in each arm. Separate sensitivity scores are 41/50 (82%)
direct and 47/50 (94%) thinking in both arms, with three incomplete responses per
arm still rejected. This does not revise the frozen v5 bridge report, gates,
generation source or token charges. A separate Phase 2 protocol is still required.
