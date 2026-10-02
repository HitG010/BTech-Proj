# Released CLM: local quantized engineering preflight

Protocol date: 2026-10-03. User preference: **keep experiments local** and
**keep Docker running**. This bounded synthetic preflight tests local feasibility
of the actual released CLM heads with a 4-bit conversion of their Qwen3-8B encoder.
It does not test the router or revise the completed negative experiments.

## Why this probe, and why deployment is still conditional

The completed MiniLM experiment did not test released CLM's pretrained heads or
8B representations. Its negative outcome is not evidence that the released
model must fail. The [CLM model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)
requires last-token-pooled Qwen3-8B embeddings, so swapping in MiniLM/1.7B would
not test the release. Full-precision 8B weights alone approach this Mac's 16 GB
RAM. The [MLX conversion](https://huggingface.co/mlx-community/Qwen3-8B-4bit)
provides a smaller local alternative. Quantized embeddings can change scores;
matching width and pooling does not prove transfer fidelity.

Current [vLLM installation documentation](https://docs.vllm.ai/en/latest/getting_started/installation/)
lists an Apple Silicon backend. This preflight uses MLX directly: the
[official Qwen3 model implementation](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/models/qwen3.py)
exposes normalized transformer hidden states before the language-model output
head. Calling that path avoids generating text and avoids vocabulary logits.

## Frozen identities and isolation

`scripts/clm_local_preflight.py` contains fixed asset allowlists, download ceilings,
synthetic inputs, one-invocation journal, resource observation and score checks.
An isolated Python 3.11 environment resides in ignored
`artifacts/research/data-efficiency-v1/clm-local-environment-v1/venv/`.
Install **mlx-lm 0.32.0 / mlx 0.32.3** there; freeze the complete resolved package
inventory in the asset manifest. The existing `.venv`, package source, generation
configuration and earlier collectors remain unchanged. Download only public
model assets; no project inputs are uploaded or model API called.

| Asset | Pinned revision |
|---|---|
| `mlx-community/Qwen3-8B-4bit` | `545dc4251c05440727734bcd94334791f6ab0192` |
| `Contrastive-LM/CLM-v0.1-8B` | `e939398d4556fcd9400c76fa8c5a513202f42b0a` |
| Official `src/clm/heads.py` | Git commit `bb42c6c5bf914fd449bed2f6ca65be80602cb1f7` |

Reviewed official head source SHA-256 is
`3f3b880e940a47b45879614b140fd873f7de9b13ccb8254b07989af7ea92e093`.
Pin every downloaded file hash before execution. The checkpoint loads with
PyTorch **weights_only=True**; its heads are built with the pinned official
`make_head`, strict state-dict loading, evaluation mode and one CPU thread.
Freeze research-environment Torch/NumPy versions for head checks separately.

## Endpoint and engineering gates

Use **ten synthetic inputs**: two identical sequences at each length 32, 128,
512 and 2,047 tokens, followed by two fixed action descriptions. Tokenize fixed
generic text with no added special tokens, repeat its token unit to the exact
prescribed length, and truncate only the last repetition. These artificial
inputs stress resource use; their timing cannot estimate real question/draft
lengths or semantic quality. Action text is fixed in the script and frozen plan.

Encode batch size one with no persistent KV cache. Use the last normalized
transformer hidden state, cast to float32 and L2-normalize its 4,096 components.
Save vectors, token-ID hashes, norm, input lengths and timing. Identical inputs
must agree to max absolute error ≤1e-5; norms must be within [0.99999, 1.00001].
Reject nonfinite values, unexpected shapes or incomplete endpoints.

The local resource observation limits are: **5 GiB allowed public downloads**,
7 GiB MLX memory guideline, 128 MiB free allocator cache, observed MLX peak
≤7 GiB, polled worker RSS ≤9 GiB, worker wall ≤600 seconds, and each encoder
input ≤60 seconds. MLX's memory setting is a **guideline, not a hard allocator
cap**. The parent observes only its own child every .5 seconds and terminates
that child on RSS/wall failure. It cannot prevent an unsampled transient peak.
Stop on the first failure, with **zero retries**; preserve logs, vectors,
invocation and terminal report. Never terminate Docker or unrelated processes.

Project the eight state vectors and two action vectors using the released heads.
Check scaled-cosine score arithmetic independently with NumPy (absolute error
≤1e-4), finite scores, and the binary softmax/sigmoid-margin identity (≤1e-6).
Record separate cold head loading and warm state projection/pair scoring.
Action projection can be cached. These checks verify implementation, not solver
correctness, probability calibration or full-precision embedding equivalence.

Preparation hashes the earlier primary/cached-score/CPU/neural reports and
allocation. Successful completion verifies these hashes unchanged. No cached
questions, drafts, reference answers or sealed data enter the synthetic endpoint.
The encoder process exits before CPU head checks, so this does **not** measure
co-resident end-to-end solver/router latency.

## Execution and interpretation

Freeze source/tests/protocol in Git before real encoding, then use:

```sh
PYTHONPATH=src artifacts/research/data-efficiency-v1/clm-local-environment-v1/venv/bin/python \
  scripts/clm_local_preflight.py --download
PYTHONPATH=src .venv/bin/python scripts/clm_local_preflight.py --freeze
PYTHONPATH=src .venv/bin/python scripts/clm_local_preflight.py --execute
```

The encoder worker needs native Metal access; sandbox-denied GPU access is not
a model failure. Network is needed only for public asset preparation. Completed
steps refuse overwrite; do not reset a journal or restart a completed endpoint.

An engineering pass only permits designing a separately frozen cached diagnostic
with **confidence and a matched 8B-backbone supervised control**. Keep labels v7,
question-group splits and independent draw halves unchanged. The released heads
stay frozen; any scalar calibration uses training-half labels only. A quantized
adaptation result remains development evidence and cannot establish that official
full-precision CLM succeeds or fails. Any new generation needs a separate protocol.
See the [broader signal design and power review](broader-signal-design.md).
