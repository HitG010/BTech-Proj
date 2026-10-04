# Local second-solver engineering protocol

Protocol date: 2026-10-04. This new checkpoint prepares Qwen3-0.6B for the
64-question opportunity diagnostic. It uses only public model files and one
synthetic prompt. It reads no study prompt into the model and no reference answer.
It does not score, fit a router, or start the 512-response diagnostic.

Freeze this script, its tests, this document, the unchanged generator/config/helper
sources, package versions and protected artifact hashes before any download or
real model call. Public repository `Qwen/Qwen3-0.6B` is pinned to
`c1899de289a04d12100db370d81485cdf75e47ca`. The
[pinned config](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json)
and [generation config](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/generation_config.json)
are verified locally rather than inferred from the earlier solver.

The explicit nine-file allowlist covers config, generation config, tokenizer
files, one safetensors checkpoint, license and README. Resolve exact public
metadata first. Reject a changed revision, missing sizes/hashes or selected bytes
above **2 GiB**. Pin its metadata before fetching bytes. Verify ordinary Git
objects with Git blob SHA-1 and LFS objects with raw SHA-256; retain every local
SHA-256. Downloads, locks and temporary files use a new isolated cache under
`opportunity-solver-preflight-v1/`. Set Hub/home/assets/Xet paths before subprocess
imports; disable Xet and telemetry. Keep the existing environment and cache intact.

There is one application-level download invocation, maximum 30 minutes. The
client may internally retry HTTP transport requests; no new application invocation
or silent restart is allowed. Observe isolated cache disk bytes with a **2.25 GiB**
ceiling, counting blob data once and ignoring snapshot symlinks. Observations do
not constitute an instantaneous filesystem quota. All partial files/logs stay
available if the invocation fails.
Check final disk use after process exit, too. Stop if required disk or RSS
telemetry is unavailable. Durable exclusive child-start markers prohibit restart
or concurrent child entry, including after a partial failure. Preserve a process
record even when the process cannot launch. Reject symlinks at all cache roots.

After assets pass, reserve one native worker invocation, zero application retries.
Use the unchanged Transformers backend on **MPS / float16 / SDPA**, no CPU
fallback. Only the engineering answer/reasoning caps are reduced to **32/32**;
the prompt suffix, closure and sampling settings remain the bridged settings.
This is not a task-performance comparison or a full-budget throughput estimate.
No runner or dataset loader is called.

Use one fixed synthetic question: `Synthetic engineering check. Return the number
7.` Generate once in direct mode and once in thinking mode with seeds from the
unchanged job builder, base seed 20261008. Assert that both mode prefixes differ,
the actual revisions match, EOS IDs are `[151643,151645]`, and closure IDs are
`[151668,271]`. This verifies the proposed two-token closure assumption and the
**786,944 response-only token reservation**, not the future global budget.

Each job has a 120-second deadline. Validate unchanged generator invariants and
finite direct post-warper/raw confidence. Stop at the first failed synthetic job.
Report actual forced closure/insertion/truncation; a test that closes early does
not prove the forced-closure path. A thinking output without an answer fails
this bounded engineering endpoint, rather than supplying a usable study response.

The parent watchdog is 600 seconds and samples only its own child's RSS every
0.5 seconds, with a 9-GiB observed ceiling. It may terminate only that child.
Record after-job MPS allocated/driver bytes separately; these are neither peak
memory nor complete unified-memory accounting. Keep Docker running. Process-scoped
macOS user activity applies only while the native worker runs.

Preserve plan, invocation reservations, public inventory, assets, logs, process
accounting and synthetic results with exclusive writes. Existing protected
artifact hashes and the original 2,319-file verifier must pass at completion.
No existing source/config/study/role/gold file changes. Cloud spend is $0.

Checkpoint before these commands:

```bash
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_solver_preflight freeze
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_solver_preflight download
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_solver_preflight execute
```

The native execution requires access to Metal. Preparation is not a collection
protocol. A passed engineering report permits the next separate two-arm protocol
implementation, with real caps, exact jobs/seeds, both-arm endpoint, v7 scoring,
question-group analysis and complete global token/time/retry/setup accounting.
