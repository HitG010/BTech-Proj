# Fresh sparse guard validation: complete, screen failed

The frozen validation completed at **2026-10-06 19:16:18 UTC** (2026-10-07
00:46:18 Asia/Kolkata). All **228 direct responses** and the **one eligible
thinking response** completed. Collector and finalizer exited with code zero.
The runtime did not need a resume or retry.

Only one direct state met the frozen changed-action rule. Its extra thinking
response was rejected by the unchanged numeric-v7 parser and scored incorrect.
This is a scorer outcome, not a new human or mathematical correctness audit.
There was no scored accuracy improvement.

| Fixed-policy difference | Result |
|---|---:|
| Mean incremental utility at lambda .05 | -.000312061 |
| 95% question-bootstrap interval | [-.000936184, 0] |
| Scored accuracy increment | 0 |
| Extra thinking tokens per question | 6.24123 |
| Changed states | 1/228 |
| Further-study screen | Fail |

The extra call used 1,423 tokens. The point difference is exactly
`−.05 × 1423 / 1000 / 228`. Unchanged states contribute zero because both policies
choose the same action there. No absolute full-policy accuracy, utility or
always-thinking counterfactual is identified by this sparse evaluation.

One changed event cannot establish a general disadvantage for parser-aware
routing. It also does not confirm the earlier three rescued development groups.
Do not expand the cohort, tune the cutoff or replace the failed endpoint from
these results. The frozen cutoff and all primary labels remain unchanged.

Combined runtime charge is **43,448 tokens / 1,498.07 operation seconds**, with
**1,611.79 collection wall seconds** and one setup. There are 229 completed
attempts and no unresolved reservations. Exactly **one selected training
reference** was accessed after the full activated endpoint. The other 227
references were not opened; the dataset still has no gold file. Both before/
after checks report all 2,319 historical protected originals preserved, alongside
the closed parent-study inventory. Cloud/API spend is $0; Docker kept running.

Plan `e7479290…bff9b`, report `ee07790d…a98ed`, score cache `4e545a59…1b690`.
Independent completion review `9a8077b5…ff882` passed. It reproduced the
statistics and bootstrap from cached scores, checked all 229 jobs and their
charges, and verified endpoint, reference-access and preservation boundaries.
It did not rerun fitting, inference, scoring or reference access.

Authoritative terminal status is
`qwen06-sparse-validation-v1/runtime-v1/status.json`; supervisor finish records
`complete`. Preserve sources, cutoff, roles, jobs, responses, scores, masks and
journals. Do not relaunch, prepare again, rerun scoring/finalization, reset the
budget or reopen references. All 256 remaining reserve rows stay unclaimed.

The user-authorized next step is the **separate 1.7B cap bridge**. Its ordering
gate requires completed validation and independent verification, not a positive
guard screen. Its [preparation and independent review](qwen17-cap-bridge-preparation-results.md)
are complete: 36 planned matched 2k/4k responses on 11 enriched development
groups. Generation remains locked until a separate executor is implemented,
frozen and reviewed. No GPU training, acquisition, CLM/RL or sealed confirmation
has started.
