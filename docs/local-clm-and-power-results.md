# Local CLM feasibility and prospective precision checkpoint

Completed 2026-10-03 on `codex/research-data-efficiency`, from source/protocol
checkpoint **`c06e2ff`**. The user requested local experiments and continued
research. Docker stayed running. The bounded released-head engineering preflight
passes; routing quality remains **untested**. The power review is complete, but
the proposed new-question panel remains unallocated and unstarted.

## Why CLM was deferred, and the revised decision

The negative [compact pilot](phase-2-router-feasibility-results.md) does not reject
released CLM: it trained small MiniLM heads and never tested pretrained CLM
representations. The released heads require Qwen3-8B last-token embeddings; an
8B router's encoding cost matters beside a 1.7B solver. Those implementation and
resource uncertainties justified sequencing a preflight before task evaluation.

The new [local preflight](clm-local-preflight.md) resolves the basic local resource
question for **one quantized encoder**. Thus released-head investigation is no
longer deferred for lack of a local implementation. Next is one separately
frozen cached diagnostic comparing the released head, a supervised control on
the same quantized 8B embeddings, and confidence. The completed MiniLM grid stays
closed, failed primary gates remain authoritative, and acquisition/RL stay stopped.

This is a 4-bit MLX adaptation. Neither matching 4,096 dimensions nor a passing
arithmetic check verifies preservation of full-precision embeddings or task
rankings. Pretraining exposure to GSM8K is also unresolved. No routing improvement,
published benchmark reproduction or novel contribution is claimed.

## Observed synthetic resource profile

All ten prescribed inputs completed in one invocation, with zero retries and
zero solver generation. Last-token vectors are finite, normalized, and exactly
identical across both repeated inputs at every prescribed length.

| Measurement | Observed value |
|---|---:|
| Public pinned asset download | 4,699,357,359 bytes |
| Encoder weight/model loading | 2.148 s |
| First 32-token encoding, including initial execution overhead | 2.912 s |
| Repeated 32-token encoding | .148 s |
| 128-token encodings | .507 / .507 s |
| 512-token encodings | 1.973 / 2.047 s |
| 2,047-token encodings | 8.205 / 8.246 s |
| Two cached action embeddings, initial / subsequent | 1.052 / .148 s |
| Peak MLX allocation | **4.951 GiB** |
| Native encoder worker wall time | 30.917 s |
| Released projection-head parameters | 18,887,680 |
| CPU head weights/construction loading, after library import | .0814 s |
| Mean warm state projection + two-action scoring | .788 ms |

The head check used the pinned official architecture and actual released
checkpoint, with safe weights-only loading and strict state dictionaries.
Independent scaled-cosine arithmetic differs by at most 7.63e-6; the binary
softmax/sigmoid-margin identity passes. Synthetic action scores have no
mathematical-correctness interpretation.

Polled worker RSS was .683 GiB; macOS RSS does **not** account for all GPU/unified
allocations. Report it separately from the 4.951 GiB MLX allocation measure.
The configured MLX memory limit is a guideline and RSS is sampled every .5 s,
so these are observed resource gates, not proof of a hard total-memory bound.

This profile excludes a co-resident solver, real question/draft tokenization,
production scheduling and a full live router path. Repetitive synthetic input
lengths stress the implementation but do not estimate task latency. The native
encoder exited before CPU head checks. A deployment claim requires measured
end-to-end behavior including transfer, tokenizer, state encoding and head work.

## Prospective power and budget results

The [broader signal design](broader-signal-design.md) proposes a **diagnostic**
64-question panel, two frozen solvers and two independent draws per mode.
That is 512 responses but only 64 question groups. No reserve IDs are selected
and no allocation, generation endpoint or scorer is changed.

The sensitivity analysis uses hypothetical question-level SDs, a two-sided
normal approximation at α=.05, and paired mean utility. It does not power the
roadmap's AULC endpoint or estimate new-task variance from this development panel.

| Independent questions | Power for +.01, if SD=.16 | Detectable gain at 80% power, if SD=.16 |
|---:|---:|---:|
| 64 | 7.9% | .0560 |
| 128 | 10.9% | .0396 |
| 548 | 31.0% | .0191 |
| 2,000 | 79.8% | .0100 |

Under that hypothetical SD, +.01 requires **2,010 questions for 80% power** or
2,690 for 90%. This does not authorize borrowing sealed roles. If independent
precision is unaffordable, narrow the paper's claims instead of interpreting a
small panel as confirmation.

The proposed response-only maximum is **786,944 tokens**, including the frozen
two-token thinking closure. Applying the current GSM8K/1.7B measured profile to
only that solver's 128 pairs gives **206,205 tokens / 2.34 hours**. The second
solver runtime, setup, retries and router cost remain unmeasured/unbudgeted.
The panel needs a separate source/role/endpoint/analysis protocol before launch.

Data-access clarification: the planning tool loads the completed protocol JSON
for checksums and cap/job-count metadata. That JSON contains old question-only
snapshots, whose contents are not used in the calculations. The frozen payload's
phrase “No question rows ... accessed” should be read as **no new question data,
reference access or sealed outcomes**; it is not a claim that the old protocol
was never deserialized. Preserve the original payload and this clarification.

## Verification and immutable artifacts

A separate fresh-process reviewer checks **130** normal-power, sample-size and
detectable-effect values using SciPy, plus response reservations and input/source
hashes. It verifies the synthetic vector/resource endpoint from cached arrays,
the public model/head asset hashes and protected report/allocation hashes. It
fits no candidate, executes no encoder and opens no reference. The original
endpoint verifier confirms 800 completed responses and all **2,319 protected
originals** unchanged after the native preflight.

Validation: full **514-test** offline suite passed at the protocol checkpoint;
two new independent-review tests also pass. Ruff and whitespace checks pass.
Both confirmations remain unstarted; official test stays sealed. No new solver
response, fetched reference, cloud/API spend or Docker interruption occurred.
Public weight downloads and ten synthetic encoder forwards are new local work.

All paths below are under `artifacts/research/data-efficiency-v1/`:

| Artifact | Payload SHA-256 |
|---|---|
| `broader-signal-power-v1/report.json` | `3d5a798cadc6152d3fc762a43c23a9de4acfbc602d55c7265e65dc99615191a7` |
| `clm-local-preflight-v1/analysis-plan.json` | `5364474e73d1678516142d79a4fc9bddfc8aeb594bed43a6d8dddd82d4ca7756` |
| `clm-local-preflight-v1/report.json` | `53e2d76b735ee820a193dd66021bd0c1c7778015cc42593c2fe2a18de022f902` |
| `local-research-review-v1/verification.json` | `a27df46edaf694b659a114f46c00770846014246ac78f9a1a153fc06274418f2` |

Do not rerun completed preparation, freeze, encoding or power commands. They use
exclusive writes/one-invocation journals. The public assets and isolated runtime
are reusable read-only inputs for a **new**, separately named cached diagnostic.
The reviewer recipe is `scripts/review_local_research_preflight.py`; a future
review needs a new output filename/directory rather than overwriting this record.
