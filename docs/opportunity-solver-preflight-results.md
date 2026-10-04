# Local second-solver check: results

Date: 2026-10-04. Branch: `codex/research-data-efficiency`.

The Qwen3-0.6B local check passed. This model can run both modes through the
existing generator. The next step is the full two-solver collection protocol.
The 64-question study has not started.

## What we completed

Source, tests and [protocol](opportunity-solver-preflight.md) were frozen at
`1e1e4d16eab76506c85bc3bd0c136ea2fbd961fd`. The plan payload is
`59827f88d5958fd3fed077d5999fd88d6d13a1b51758cf351034c40464b99c04`.

One download collected nine public files from Qwen3-0.6B revision
`c1899de289a04d12100db370d81485cdf75e47ca`. The files total **1,519,207,673
bytes**. Download time was **162.94 seconds**. Each file passed its remote object
hash and local SHA-256 check. All cache paths are separate from the old cache.
There was no application retry. The HTTP client can retry transport requests.

One native worker ran two synthetic jobs. It used MPS, float16 and SDPA.
It loaded no study question or reference answer.

| Measurement | Direct | Thinking |
|---|---:|---:|
| Answer tokens, including EOS | 6 | 2 |
| Reasoning tokens | 0 | 32 |
| Inserted closure tokens | 0 | 2 |
| Job time, seconds | 1.201 | 0.882 |
| Forced closure | No | Yes |
| Truncated answer | No | No |

Both jobs produced a nonempty final answer. Direct returned `\boxed{7}`.
Thinking returned `7` after forced closure. This is an engineering check.
It is not an accuracy test. It does not establish full-budget throughput.

The two jobs charged **42 tokens**. Model load took **3.094 seconds**.
The worker's internal time was **7.278 seconds**. The parent observed **11.301
seconds**, including process start and checks. The largest sampled process RSS
was **2,217,115,648 bytes**, about **2.06 GiB**, across 22 samples.
This measure is not total unified-memory use. After-job MPS allocated memory was
1,199,702,272 bytes. The largest after-job driver measure was 1,244,381,184 bytes.
Those MPS measures are not peak measures and must not be added to RSS.

Actual EOS IDs were `[151643,151645]`. Actual closure IDs were `[151668,271]`.
The direct and thinking prefixes differed. The two-token closure assumption
therefore passes for this model. The planned **786,944-token** reservation covers
study responses only. It is not the complete collection budget.

Direct raw confidence was finite at −0.0584372. Post-warper confidence was 0.0.
These values are not calibrated correctness probabilities. Keep raw confidence
as the planned routing feature; freeze its exact use in the new analysis plan.

## Where we face problems

1. **The current CLM route has no demonstrated benefit.** It chose thinking on
   380 of 400 cached drafts. Its accuracy increase did not cover the token cost
   at the fixed penalty. Keep the tested recipe closed.
2. **Useful corrections are sparse.** The old panel has 50 question groups.
   Repeated responses do not create more independent questions. A smaller
   solver may have a different correction pattern. We have not measured it yet.
3. **The new panel has limited precision.** Its 64 questions can support a
   diagnostic. They cannot confirm a +.01 gain with the planned power.
4. **The full collector still needs shared limits.** Existing accounting is per
   run directory. Separate full budgets could double the allowed use. Implement
   one parent ledger for both models before collection.
5. **Novelty is unproven.** Contrastive routing and repeated solver samples have
   prior work. A model name is not a new research contribution. Test a specific
   mechanism only after fresh evidence shows useful routing opportunities.

See the [deep CLM assessment](clm-research-assessment-2026-10-03.md) and
[power review](broader-signal-design.md) for the evidence behind these decisions.

## Next implementation

Freeze the 512-job protocol before any study response is generated. It must bind
both models, tokenizer files, jobs, independent seeds, prompt, real token caps,
scorer, folds and analysis rules. Keep the existing 64-question child unchanged.

The proposed resource design uses one global **1,000,000-token / 12-hour** ceiling.
Count both arms, setup time and failed attempts. Permit at most four setup
sessions: one initial session and at most one separately journaled resume per
arm. Stop at the first failure. Reserve budget before each operation. Charge
unresolved reservations conservatively. These choices are not yet a frozen
collection protocol. There is no completion-time guarantee.

Require all **512 valid, distinct responses**, exited collectors and released
locks before fetching exactly the 64 selected upstream-training references.
Write one separate v7 score sidecar for both arms. Leave the question-only
dataset's `gold_sha256` null. Reviews must use cached scores.

Report corrections, new errors, positive utility gains and affected questions by
solver and draw. Resample the same question groups for paired comparisons.
Keep the single confidence threshold as a control. Train on one draw of other
question folds; test on the other draw of held-out questions. Reverse the draws.
No CLM finetuning or new architecture search is part of this diagnostic.

## Verification and preservation

The full offline suite passes **576 tests**, including 19 preflight cases.
Ruff and whitespace checks pass. Sol reviewed the code before freeze.
The review found gaps in telemetry, final disk checks, restart prevention and
decoded-answer validation. Those gaps were fixed and tested before execution.

The completion verifier confirms all **2,319 protected originals** are unchanged.
An independent Sol audit reproduced 11 artifact envelope checksums, 10 frozen
source hashes, eight protected input hashes and all nine public file hashes.
It also reproduced job identities, seeds, token-ID counts and the limits.
Its separate read-only preservation check passed all 2,319 originals.
The old studies, model environment, parent roles and child roles are unchanged.
Docker stayed running. Cloud/API spend is **$0**. The worker has exited.
No fresh diagnostic response, scoring, reference access or sealed-data access
occurred. Acquisition, Jev/RL and confirmation remain stopped.

Artifact directory:
`artifacts/research/data-efficiency-v1/opportunity-solver-preflight-v1/`.

- Asset payload: `970a2716d7017d2761052c35d3c9fb1af19cfd416993a9078eead24a79b19f43`.
- Worker payload: `31308ac0fa106776b3cce885d583f46e3613f59a8fc50a782441ff51a9f3c0d9`.
- Completion payload: `ce24395e69ad11c5e186d942bd622be160de1215e19f2e97f55dca9a0e44e21c`.

Preserve all plans, sources, tests, protocol, files, invocations, start markers,
logs and reports. Do not restart the completed download or worker.
