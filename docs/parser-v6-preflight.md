# Numeric-v6 parser preflight

The completed bridge exposed a conservative scoring limitation: one response
boxed intermediate totals 170 and 180, then explicitly declared a final answer
of 180. Frozen `numeric-v5` treated every box as a competing answer and rejected
the response. The bridge's original scores, gates and report stay unchanged.

`reasoning_budget.scoring_v6` is an additive, opt-in scorer for the next study.
All files named in the bridge's frozen source inventory remain byte-identical.
The ordinary `rb score` command still uses v5. The new module includes both its
own source and its reused v5 numeric helpers/schema in its implementation digest.
It does not change generation settings, question allocation or solver outputs.

## Gold-independent extraction policy

1. A line-anchored `Final answer:` / `Final answer is` / `Final answer =` label,
   a standalone final-answer heading, or a numeric `####` delimiter introduces
   an explicit final section. Markdown headings/bold and the check-mark prefix
   are supported. A prose mention embedded in a sentence does not introduce
   precedence. A malformed anchored final label fails instead of falling back.
2. Balanced, **unlabelled** boxes before the first final section are intermediate
   work. Earlier labelled numeric answers remain binding; `Answer: 3` followed
   by `Final answer: 4` is still conflicting.
3. Every final section must contain only exact numeric claims, supported units,
   boxes and display formatting. All claims in every final section must agree.
   Multiple final labels cannot silently select the last answer. Extra prose,
   negation, written alternatives or unsupported formulae in that section fail.
   This restriction also catches alternatives after a boxed answer.
4. Any unclosed box anywhere, malformed final display, truncated/timed-out output,
   early EOS or reasoning leakage remains unscorable. Never guess an answer
   from incomplete output. Three bridge truncations are generation failures to
   obtain a complete answer, not cases to rescue with a permissive parser.
5. With no explicit final section, preserve v5 extraction and ambiguity rules.
   Extraction accepts no gold argument. Correctness is compared with gold only
   after a single value has already been extracted.

The stricter final-section rule deliberately rejects explanatory prose after a
final claim. This is a fixed conservative contract; compatibility changes must
be reported, not silently interpreted as an improvement in the solver.

## Integration and safeguards

The pure `parse_answer`, `extract_record` and `score_record` APIs are available
from `reasoning_budget.scoring_v6`. A future Phase 2 protocol must explicitly pin
this scorer/digest and control its own complete endpoint and isolated gold access.
The allocation and existing generation protocol do not grant repeat collection
or scoring permission by themselves.

For a completed real bridge arm only:

```sh
.venv/bin/python -m reasoning_budget.scoring_v6 <complete-bridge-run-directory>
```

The opt-in CLI verifies exact question records, isolated upstream-training
metadata, the frozen bridge source/allocation/data protocol and **both** completed
arms before reading gold. It rejects real repeat, confirmation, test, shared-gold
or incomplete runs. Synthetic fixture runs have a separate explicit test-only
allowance. Outputs are `scores.numeric-v6.json`; canonical/v5 caches are never
rewritten. Changed source, records, gold or scores under that same cache identity
are rejected. Existing v5 reports remain primary; any bridge v6 comparison is a
development sensitivity analysis motivated by an already observed case.

## Validation sequence

Synthetic positive and adversarial tests precede any cached-output comparison.
They cover intermediate boxes, labelled prefix conflicts, duplicate final
claims, Markdown/display formats, exact fractions/repeating decimals, negation,
numeric and written alternatives, empty/malformed labels, unclosed boxes,
truncation, gold invariance, versioned cache preservation, question identity,
sealed/shared gold rejection and the paired endpoint lock. An independent agent
review found malformed-label fallback and identity gaps; those were fixed before
comparison. Agent review does not replace human validation; the waiver remains.

Next, freeze the v6 source/policy and protected hashes, compare v5/v6 extraction
on 900 previously used development responses and 200 completed bridge responses
**without opening historical gold**, review every transition, then write separate
v6 sensitivity scores using only the 25 isolated bridge training answers. Record
test counts, hashes, changed extracts/statuses and remaining limitations. No
new solver generation, official-test access or cloud expense is part of this fix.

## Result

Pending the fixed compatibility check and isolated bridge sensitivity scoring.
