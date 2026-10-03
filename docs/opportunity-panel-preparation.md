# Reserve-child opportunity panel: question-only preparation

This additive checkpoint can freeze a 64-question child of the existing 548-question
`reserve` role. It prepares questions only. The real prepare command must follow a
source/test checkpoint; it has not been run by this implementation checkpoint.
Collection, model downloads, reference access, scoring and fitting are absent from
this module. The resulting status is `prepared_question_only_collection_locked`.

`scripts/opportunity_panel_plan.py prepare` validates the unchanged parent with
`load_allocation`, orders reserve records by a fixed hash with seed 20261007, copies
the first 64 into child split `opportunity64`, and fixes five question folds. It
records upstream row indices, source revision, parent file and payload hashes,
normalized prompt digests, exclusions, and source/test/document hashes. The output
is under `artifacts/research/data-efficiency-v1/reserve-children/opportunity64-v1`.
Its dataset has no gold file. An existing child is never overwritten; `verify`
checks its frozen identity and sibling child conflicts. Parent roles and artifacts
stay unchanged.

The prospective response shape is 64 questions × two solvers × two independent
draws × two modes = 512 responses. With 512 answer tokens, 2048 thinking tokens
and an assumed two-token closure, the response-only reservation is 786,944
tokens. The candidate Qwen3-0.6B revision is
`c1899de289a04d12100db370d81485cdf75e47ca`, verified in the
[official model metadata](https://huggingface.co/api/models/Qwen/Qwen3-0.6B).
Its local files, tokenizer closure, global setup/retry limits, endpoint and
scorer protocol remain unresolved. The 1.7B revision
is already pinned in the earlier repeat study. No collector can be launched from
this script.

Pure synthetic helpers check rescue/harm and the λ=.05 incremental gain. The
secondary confidence control uses five question folds, training on draw 0 and
evaluating draw 1 of held-out questions, then reversing draws. It fits a scalar
cutoff on training questions only and breaks utility ties toward fewer thinking
calls. This diagnostic will need a separately frozen outcome/scoring protocol
before use with real responses. All intervals must resample questions, not draws.

Use module execution after checkpointing the source:

```bash
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_panel_plan prepare
PYTHONPATH=src .venv/bin/python -m scripts.opportunity_panel_plan verify
```

The child's selected questions become development after this diagnostic. Its
preparation does not reassign or open validation, confirmation or official-test
outcomes. Real collection still requires a separate additive frozen protocol and
a reviewed bounded worker. These 64 question groups cannot confirm a +.01 gain
with adequate power under the current variance sensitivity.
