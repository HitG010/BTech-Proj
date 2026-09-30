# Phase 1, checkpoint 2: reconcile the experiment protocol

Completed 2026-10-01 on `codex/research-data-efficiency`, after checkpoint
`6999eb5`. This implements the next foundation step in the
[accepted roadmap](research-roadmap.md). It prepares a consistent collection
pipeline; it does not add new solver outcomes or establish a novel router.

## What we are building first

The eventual router will use the question and a cheap direct draft to choose
whether to accept the answer, buy another direct draft, or invoke thinking.
The research hypothesis concerns how to acquire reliable training evidence for
these decisions with fewer generated tokens. Repeated responses can inform
several actions, whose correctness and costs are dependent.

First, that evidence needs a fixed experimental definition. Otherwise a changed
answer parser, stopping rule, or retry policy can move the accuracy/cost curve
without any improvement in the router. This checkpoint establishes the parser,
generation settings, accounting, and provenance for the next bridge experiment.
Jev features and a contextual-bandit extension remain conditional Phase 5 work.

## New generation and scoring identities

The generation protocol is **`qwen3-boxed-budget-v3`**. The prepared bridge
configuration is [research-gsm8k-v3.yaml](../configs/research-gsm8k-v3.yaml):

| Setting | New bridge protocol |
|---|---|
| Model/tokenizer | Qwen/Qwen3-1.7B, both pinned to `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` |
| Prompt suffix | `In your final response, give only the numerical answer in \boxed{}.` |
| Reasoning / answer caps | 2,048 / 512 tokens |
| Forced closure | `</think>\n\n`, cached token IDs `[151668, 271]` |
| EOS | Union of tokenizer, checkpoint and generation configuration: `[151643, 151645]` |
| Direct decoding | temperature .7, top-p .8, top-k 20 |
| Thinking decoding | temperature .6, top-p .95, top-k 20 |
| Execution | batch one, explicit MPS / float16 / SDPA, local cached files only |
| Bridge draws / seed | two per mode; generation seed root `20261001` |
| Bridge ceilings | 200,000 charged tokens; four cumulative hours; 600 seconds/job; stop after three consecutive failures |

The generic configuration's historical 256-answer-token default is unchanged;
the research configuration explicitly selects 512. Bridge data will live in an
isolated directory, which has **not yet been prepared**. Its exact question
manifest and matched legacy-arm configuration must freeze before generation.

The scorer is **`numeric-v5`**, with an implementation digest in every new score
artifact. It combines the two historical branches' repeating-decimal,
Markdown-heading, LaTeX decoration, and answer-label fixes. Explicit numeric
claims must agree, truncated answers remain unscorable, and extraction never
receives gold. Unit suffixes use a finite vocabulary: unsupported phrases are
parse failures, rather than arbitrary prose being treated as a unit.

Independent review found that accepting arbitrary words around one numeral
could turn `\boxed{not 7}` or `Final answer: 7 or eight` into a correct answer.
The fix preserves words when unwrapping formatting and accepts only a numeral
followed by supported unit words. Adversarial tests cover negation, written
alternatives, operators, numeric wrappers, and conflicting claims.

The historical post-warper mean generated log-probability remains available
with its original meaning. An optional **pre-warper** likelihood is recorded
separately; old result dictionaries remain byte-equivalent on load. This is a
measurement, not a calibrated probability of correctness. The raw recorder
keeps one vocabulary row and scalar observations, but Transformers still
retains the existing post-warper `output.scores`; total confidence collection
memory is not constant in sequence length. Its latency needs the real bridge.

## Accounting, recovery, and source provenance

- New run/job identities include protocol version, resolved backend settings,
  configuration and question identity. Run identities also include the
  environment. Source hashes are recorded separately, so a same-protocol
  maintenance change can resume a general run without inventing new jobs.
- Every session, attempt, and response records its source implementation and
  session identity. Loading a new response verifies its matching session.
  Frozen-study readers reject mixed implementations; source and package guards
  remain active. A behavior-changing maintenance edit requires a protocol bump.
- Budget usage is scanned once on entry and updated only after durable result
  and attempt writes. Restart reconstructs usage from disk. Unfinalized
  generation reservations remain charged conservatively.
- Setup has a durable time reservation before model loading. A hard kill during
  load retains the remaining time allowance; a normal return/exception replaces
  it with observed setup time. Model loading is not preemptible, so it may
  overrun wall time; the runner starts no further generation after exhaustion.
- An isolated failed job no longer stops the whole run. Success resets the
  failure streak; three consecutive failures stop collection, and interrupted
  work stops immediately. Retry attempts remain charged.
- New reports identify the active $100 roadmap allocation: $10 foundation,
  $15 signal, $30 main, $30 shared replication/confirmation, $15 extensions and
  buffer. Historical reports are preserved.

Charged output includes generated and inserted tokens. Prompt/prefill tokens
are reported separately. Stage time includes generation/prefill and associated
synchronization; result time includes template/decode/confidence work, while
model setup is tracked separately. Live end-to-end latency remains to measure.

## Preserve and reproduce historical studies

A detached checkout at `artifacts/legacy/router-studies-6999eb5/` preserves the
pre-integration source. Both old branches' `numeric-v3`/`numeric-v4` names remain
historical collisions; v5 does not make their different generation protocols
interchangeable. The new code correctly refuses the old frozen studies.

If the local legacy checkout is absent, recreate it from this repository root:

```sh
git worktree add --detach artifacts/legacy/router-studies-6999eb5 6999eb5
```

Use the pinned source with the existing environment and root-relative artifacts:

```sh
PYTHONPATH=artifacts/legacy/router-studies-6999eb5/src \
  .venv/bin/python -m reasoning_budget.cli confirm status \
  artifacts/confirmation/frozen-router-v1
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=artifacts/legacy/router-studies-6999eb5/src \
  .venv/bin/python -m reasoning_budget.router_dev \
  --source artifacts/probe/continuation-v1 \
  --output artifacts/router-dev/shared-base-v2
```

New scoring preserves a historical `scores.json` and writes
`scores.numeric-v5.json` alongside it. Reports with old/unspecified scoring
provenance remain in `report/`, with new outputs in `report.numeric-v5/`.
Reusing the same scoring name with different scorer source is rejected.
No real historical run was rescored for this checkpoint: its gold artifact also
contains sealed official-test labels, which were not opened.

## Verification and next gate

- **195 offline tests pass**, including synthetic full-study pipelines, EOS
  handling in both generation stages, raw likelihood recording, conservative
  interruption/setup accounting, per-response provenance, mixed-code rejection,
  numeric ambiguity, and versioned scores/reports. Ruff and whitespace checks pass.
- **900 saved records** (400 calibrated-pilot, 300 diagnostic-direct and 200
  diagnostic-thinking) retain exactly the hashes recorded by their old score
  caches. A gold-free v4/v5 extraction comparison found **zero differences**.
  This is compatibility evidence, not an accuracy or novelty result.
- **14 protected artifacts** and **21 pinned legacy Python files** retain their
  raw-file SHA-256 hashes. Legacy probe and confirmation protocol validation
  still succeeds with the pinned source. The confirmation remains prepared for
  the old joint router with generation not started.
- Cached tokenizer/configuration inspection verified both EOS IDs and closure
  IDs on the explicit MPS configuration without loading model weights.

The checksummed local evidence is under
`artifacts/research/data-efficiency-v1/phase-1-step-2/`: `preservation.json`,
`verification.json`, `legacy-compatibility.json`, `parser-diff.json`,
`cached-backend-metadata.json`, `cached-environment.json`, and `resolved-protocol.json`.
Solver generations: **0**. Gold/test access: **0**. Cloud/API spend: **$0**.
The human audit waiver remains in effect; reviews here are agent and automated.

Next, allocate the disjoint roles from question IDs and prompts, prepare the
25-question bridge, freeze both generation arms and the analysis, and measure
local behavior/throughput. Only that real bridge can establish the effects of
the EOS and confidence instrumentation changes. The repeated-draw supervision
panel follows if the foundation gate passes.
