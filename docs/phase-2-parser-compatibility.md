# Phase 2a: bounded gold-free parser compatibility

Completed **2026-10-02**, from repository checkpoint `3822826`. The separately
frozen candidate passes its narrow compatibility gate: **one** balanced-bold
presentation repair among **1,900** cached responses, with zero losses or changes
to previously accepted answers. **Frozen v7 and all completed primary labels,
reports and failed progression gates remain authoritative.** No correctness
sensitivity sidecar was created, no reference answers were opened, and no solver
generation or cloud expenditure occurred.

The [October checkpoint](contrastive-router-review-2026-10-02.md) requested one
bounded candidate before CPU learner investigation. The earlier
[gold-free audit](../artifacts/research/data-efficiency-v1/repeat-parser-audit-v1/report.json)
informed the scope, so this is reused-development compatibility evidence, not a
blind test, improved correctness result or independent confirmation.

## Frozen policy and scope

The candidate removes exactly one balanced, whole-line `**` wrapper enclosing
an explicit `Final answer:` / `Final answer =` / `Final answer is` declaration.
Optional Markdown headings and the existing check-mark prefix are supported.
It then delegates every extraction and generation-completeness check to the
unchanged v7 implementation. It does not rewrite numbers, infer correctness,
select the last box or introduce an unmarked terminal-claim boundary.

Numeric context and unit conversion would require deciding which quantity the
prose denotes. This candidate keeps v7's literal consistency checks and written
number rejection. Existing numeric/unit formats remain supported; different
numeric literals in dollars/cents equivalents remain rejected. The two written
count descriptors and contextual digit quantity from the audit remain outside
the bounded contract. Negation, alternatives, conflicting labels, arithmetic,
malformed boxes, incomplete generation and multiple component answers remain
subject to unchanged v7 rejection.

The [plan](../artifacts/research/data-efficiency-v1/parser-compatibility-v1/plan.json)
was created before compatibility extraction. It pins the candidate script and
tests by file SHA-256, all 56 synthetic syntax fixtures, six exact cached-response
inventories, 67 protected source/configuration/primary-artifact files and v7's
implementation digest. No post-comparison policy variants were tried.

## Compatibility result

| Cached group | Responses | Changed extractions | Accepted-answer losses/value changes |
|---|---:|---:|---:|
| Historical development | 900 | 0 | 0 |
| Completed paired bridge | 200 | 0 | 0 |
| Completed repeat panel | 800 | 1 | 0 |
| Total | 1,900 | 1 | 0 |

The sole transition is a repeat direct response ending with
`**Final answer: $\boxed{1400}$**`: v7 returns `invalid_number`, while the
format-normalized candidate returns `1400, ok`. The numeric claim is explicit
and unique within its final section. The preamble is intermediate work under
the existing v7 boundary rule. This is a syntactic review, with no assessment
of whether the solution or answer is mathematically correct.

All 56 prespecified synthetic/adversarial cases pass. They vary numeric values,
fractions, decimal rational equivalents, headings and declaration separators,
and test unit suffixes, conversion/context rejection, written quantities,
alternatives, negation, arithmetic, multiple claims, malformed declarations,
reasoning leakage and truncation. The test suite also checks unsupported
format preservation, generation metadata, immutable output creation and refusal
of incomplete/tampered preflight inputs. All **71 new tests** and **66 existing
v7 tests** pass; Ruff passes.

A fresh process reproduced all 1,900 extraction pairs exactly and verified
every input response hash and all 67 protected file hashes. The five incomplete
outputs and 16 multi-component-answer cases identified by the prior audit retain
their exact v7 rejection. The repeat parser would reject 26 responses under this
candidate versus 27 under v7; this is extraction coverage, not a correctness
score. All score caches remain unchanged.

## Decision and reproduction

**Phase 2a is complete.** The narrow formatting candidate is compatible on the
declared syntax and cached inputs. It is retained as a separately versioned
preflight artifact; production and primary analysis continue to use frozen v7.
Any future correctness sensitivity requires separate authorization, pinned
endpoint and sidecar identity. This result supplies no permission to reopen
references, refit primary policies, rescue gates or scale acquisition. Bounded
CPU exploratory controls can proceed using the unchanged cached v7 labels.

```sh
.venv/bin/python -m pytest tests/test_parser_compatibility_preflight.py tests/test_scoring_v7.py
.venv/bin/ruff check scripts/parser_compatibility_preflight.py tests/test_parser_compatibility_preflight.py
```

The executed sequence was
`python scripts/parser_compatibility_preflight.py freeze`, followed by
`python scripts/parser_compatibility_preflight.py execute`. Both commands create
outputs exclusively and refuse overwriting existing artifacts. Do not rerun
those mutation commands merely to inspect the completed preflight; use the
report and verification records.

- Frozen plan payload SHA-256: `1cca9f06af29ad99c6411d3b294163f8fe0892926c6cd34f9408f45513231a9e`.
- Report payload SHA-256: `51cbe6a6db3b0ec8be6e033427af7ad58fbfaf7721924fef3126c0321a5ec199`.
- Frozen v7 implementation: `c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964`.

Artifacts: [report](../artifacts/research/data-efficiency-v1/parser-compatibility-v1/report.json)
and [fresh-process verification](../artifacts/research/data-efficiency-v1/parser-compatibility-v1/verification.json).
The [script](../scripts/parser_compatibility_preflight.py) accepts response text
and generation metadata only; it has no gold argument or scoring entry point.
