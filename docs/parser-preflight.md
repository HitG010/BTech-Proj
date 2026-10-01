# Final-answer parser preflight

The completed bridge exposed a scoring limitation: a response boxed intermediate
totals 170 and 180, then explicitly declared a final answer of 180. Frozen
`numeric-v5` treated every box as a competing answer and rejected the response.
The bridge's original scores, gates, source and report remain unchanged.

`reasoning_budget.scoring_v7` is an additive, opt-in scorer ready to pin in the
next study's separate protocol.
All existing files named in the bridge's frozen source inventory remain
byte-identical. The ordinary `rb score` command still uses v5. The v7 digest pins
its source and the reused v6/v5 numeric helpers and record schema. It does not
change generation settings, question allocation, solver outputs or token costs.

## Candidate history

The first candidate, v6, required numeric-only final sections. It was frozen at
commit `715e0f0` before a gold-free comparison of 900 historical development and
200 completed bridge responses. It rescued the known final-180 case in each arm,
but rejected 44 previously parseable responses (34 historical, 10 bridge) with
ordinary explanatory prose. **V6 was rejected for compatibility**, before any
real v6 gold scoring. Its source, protocol and all 46 transitions are retained
in `artifacts/research/data-efficiency-v1/parser-v6-preflight-v1/`; its protocol
digest is `8261a6b922cabacaba0a5cc4fd1b471beb627beb25a3caa35003584ef53e6530`.
It must not be selected by a future study.

V7 permits explanatory prose around an explicit numeric claim. Development was
informed by the gold-free v6 regressions and an already observed bridge example;
this is a repair on reused data, not an independent evaluation. Synthetic tests
and agent review precede freezing v7 and its subsequent compatibility comparison.

## Gold-independent extraction policy

1. A line-anchored `Final answer:` / `Final answer is` / `Final answer =` label,
   a standalone final-answer heading, or a numeric `####` delimiter introduces
   an explicit final section. Markdown headings/bold and a check-mark prefix are
   supported. A prose mention embedded in a sentence does not introduce
   precedence. A malformed anchored final label fails instead of falling back.
2. Balanced, unlabelled boxes before the first final section are intermediate
   work. Earlier labelled numeric answers remain binding; `Answer: 3` followed
   by `Final answer: 4` is still conflicting. All final sections must agree;
   selecting the last label silently is forbidden.
3. Every final section requires an explicit numeric anchor: a strictly numeric
   box, a supported numeric answer label, or a standalone numeric/unit line.
   A nonempty same-line declaration without a box must itself be a strict numeric
   claim. Thus `Final answer: see below` cannot defer to a later box. Prose alone
   never supplies an answer.
4. Explanatory prose can surround an explicit anchor. Every extra digit numeral
   must agree exactly with all anchors. Fractions and repeating decimals use
   exact rational arithmetic. Prose numerals only veto a conflict; they never
   choose an answer. Written number words in prose, negations, alternatives,
   hedges, arithmetic operators and specified transformation/relationship terms
   are rejected conservatively. Unsupported formulae remain unscorable. A
   percentage unit is allowed; a modulo expression or `percent of` is not.
5. Any unclosed box anywhere, malformed final display, truncated/timed-out output,
   early EOS or reasoning leakage remains unscorable. Never infer an answer from
   incomplete output. The bridge's three truncations per arm need a separate
   generation-protocol decision, not a permissive scoring exception.
6. With no explicit final section, preserve v5 extraction and ambiguity rules.
   Extraction accepts no gold argument. Correctness is compared with gold only
   after a single value has already been extracted.

These lexical checks are a bounded numeric-extraction contract, not a semantic
verifier for arbitrary English. Unsupported formats may be rejected, and an
unanticipated verbal qualification can evade a finite vocabulary. Report parser
coverage and representative failures in future studies; do not claim exhaustive
natural-language correctness or general benchmark coverage from this preflight.

## Integration and safeguards

The pure `parse_answer`, `extract_record` and `score_record` APIs are available
from `reasoning_budget.scoring_v7`. A future Phase 2 protocol must explicitly pin
this scorer/digest and control its own complete endpoint and isolated gold access.
The existing allocation does not itself authorize repeat collection or scoring.

For a completed real bridge arm only:

```sh
.venv/bin/python -m reasoning_budget.scoring_v7 <complete-bridge-run-directory>
```

The opt-in CLI verifies exact question records, isolated upstream-training
metadata, the frozen bridge source/allocation/data protocol and both completed
arms before reading gold. It rejects real repeat, confirmation, test, shared-gold
or incomplete runs. Synthetic fixture runs have an explicit test-only allowance.
It writes only `scores.numeric-v7.json`; canonical/v5/v6 caches are never
rewritten. Changed source, records, gold or scores under that cache identity
are rejected. Any v7 bridge comparison is a separate development sensitivity
analysis; original v5 results remain primary.

## Validation sequence and result

Synthetic tests cover final-section precedence, Markdown/display formatting,
fractions, explanatory prose, numeric/written alternatives, arithmetic,
negation, malformed/empty final labels, unclosed boxes, truncation, gold
invariance, exact question identity, isolated gold access, paired completion
and cache preservation/tampering. Agent reviews use synthetic cases and do not
replace a human audit; the existing human-audit waiver remains in force.

After source/policy freeze, compare v5/v7 extraction on the same 1,100 cached
responses without opening historical gold, review every transition, then write
separate sensitivity scores using only the 25 isolated bridge training answers.
Preserve and verify all original study hashes. No new solver generation,
official-test gold access or cloud expense belongs to this fix.

**Preflight complete, 2026-10-01.** V7 source/policy was committed at `2607206`
before comparison. All **341 offline tests** pass, including 66 v7 tests; Ruff
and whitespace checks pass. The fixed 1,100-response comparison found exactly
two changes: the same final-180 direct response in each bridge arm changed from
`conflicting` to `180, ok`. The 900 historical responses had zero changes, and
no previously accepted extraction became a failure. Independent gold-free
agent review found both transitions justified. They represent one duplicated
case, not two independent observations.

Only after that compatibility review, the opt-in scorer read the existing
25-question isolated bridge training gold and wrote separate versioned caches:

| Mode, in each arm | Primary v5 correctness | Separate v7 sensitivity | V5 → v7 parse failures |
|---|---|---|---|
| Direct | 40/50 (80%) | 41/50 (82%) | 2/50 → 1/50 |
| Thinking | 47/50 (94%) | 47/50 (94%) | 2/50 → 2/50 |

All three remaining failures per arm are truncated responses, still rejected as
`incomplete`. Both arms still charge 81,593 tokens. All 2,319 protected original
files and all 1,100 input response records retain their hashes. The old
3,100-question confirmation remains prepared/unstarted; historical shared and
official-test gold were not opened. New solver responses and cloud spend: zero.

The direct change is a parser coverage repair on reused output, not improved
solver/router behavior, novelty or independent confirmation. Primary bridge
scores and gates remain 80%/94% under v5. No new repeat protocol or collection
was launched.

Frozen identifiers:

- V7 implementation: `c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964`.
- V7 preflight protocol: `bd0568e5f103960fdc5e02171828f1bf88a8d959bc2eff8c6d82613a0ae94b4e`.
- Existing bridge protocol: `ed5f40e722ef869c33a396c55ec57ab3b741a01ee6014612c8c8925376968066`.

Artifacts are under `artifacts/research/data-efficiency-v1/parser-v7-preflight-v1/`:
`protocol.json`, `frozen-scoring-v7.py`, `extraction-diff.json`,
`compatibility-review.json`, `agent-review.json`, `report.json`, `report.md` and
`verification.json`. Each bridge run additionally has `scores.numeric-v7.json`.
The rejected v6 trial is preserved in its separate directory. Future Phase 2
work must pin v7 and its dependencies in a new role-specific, endpoint-locked
protocol; neither this preflight nor its bridge-only CLI opens repeat gold.
