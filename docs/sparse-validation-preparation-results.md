# Fresh parser-guard validation: preparation complete, collection locked

The new protocol is prepared after source/test/document freeze at `9bc9ac7`.
All **670 offline tests** and independent code reviews pass. It validates a
parser-aware confidence baseline, not the failed learned candidate or its
conditional fresh-run proposal.

## Frozen cutoff

One scalar cutoff was fitted on the 128 existing 0.6B states from 64 training
groups. It maximizes plain-confidence training utility at lambda .05, with
strict `<` escalation and ties favoring fewer escalations, then a lower cutoff.
The result is **-.07951707680497253**. Both prospective policies share it.

Policy plan `81c70aee…fe98a`; policy `c761a265…2b177`. Independent exact-integer
verification checks all 130 candidate cutoffs and confirms the optimum. All
11 source pins, nine pilot pins and 2,652 closed-study files match. Required
policy review `9d1b04de…156e3`, detailed verification `9b1dee5a…f50b8`.

The full-data plain policy escalates 85 training states; the parser-aware rule
escalates 87. Thus this refit has **two changed training states**, rather than
the previous cross-fitted control's three. Both thinking outputs are scored
correct in the existing cache. These are training observations, not fresh gains
or a sample-size guarantee. The earlier event-rate projection must not be
silently treated as a prediction for this refitted policy.

## Fresh question role

After policy review, one new child was selected by the frozen hash order:
`reserve-children/qwen06-guard-fresh228-v1/`, split `guard_fresh228`, selection
seed 20261018. Its **228** question-only rows are disjoint from the old 64-child,
every other role and sibling. Parent source/index/normalized-prompt/exclusion
checks pass. The parent manifest remains unchanged at 548 reserve rows:
64 earmarked earlier, 228 earmarked now, and **256 unclaimed**. There is no gold
file; dataset `gold_sha256` is null.

Child payload `2e2d9623…e81f1`; question protocol `de5011cb…194c8`.
Independent preparation verification `c24a7808…fef2e` reconstructs all **456
potential** job identities/seeds: 228 direct and one possible thinking response
per question. Model, tokenizer revision, sampling, prompt, caps, v7 and backend
metadata are unchanged. No tokenizer or model was constructed during preparation.

## Next implementation boundary

The collector is **unimplemented and locked**. No solver response, scoring,
training reference, cloud job or Kaggle upload occurred. Do not rerun policy fit
or question preparation, reset either marker, modify their frozen sources,
or add gold to the dataset. Read-only verification is available through
`python -m scripts.qwen06_sparse_validation verify-policy` and
`verify-questions`.

The future collector must complete all 228 direct responses, freeze the
gold-free changed-action eligibility mask, then complete **all** eligible
thinking jobs. More than 32 eligible states stops incomplete without reference
access or subsampling. The response-only maximum is **198,720 tokens**;
250k tokens/six hours and setup/retry limits are proposals that still need a
separate runtime implementation and freeze. Only eligible training references
may unlock after the complete activated endpoint, exited workers and accounting.

Analysis estimates only the fixed-policy difference. Common outcomes cancel;
absolute policy accuracy/utility and always-thinking performance are not
identified. The sparse changed-state count may be too small for a useful
95% interval. Do not declare the study powered from two training events.

The [1.7B investigation](qwen17-improvement-plan.md) is a separate line of work.
Free [Kaggle training](kaggle-free-gpu-plan.md) is an optional resource after
its own data/environment/training protocol; the current preparation uses no GPU.
Docker stays running. Official test, confirmation and acquisition remain sealed
or unstarted; earlier failures and primary labels remain unchanged.
