# Final-answer parser preflight

The completed bridge exposed a scoring limitation: a response boxed intermediate
totals 170 and 180, then explicitly declared a final answer of 180. Frozen
`numeric-v5` treated every box as a competing answer and rejected the response.
The bridge's original scores, gates, source and report remain unchanged.

`reasoning_budget.scoring_v7` is an additive, opt-in candidate for the next study.
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

V7 compatibility and isolated bridge sensitivity results are pending.
