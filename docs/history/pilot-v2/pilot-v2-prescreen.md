# Pilot v2 scorer pre-screen (agent review)

Run `f73a5665230cd83a7f12`, scorer `numeric-v4`, reviewed 2026-09-10 by Claude, an
AI agent. This is not the human audit required by the protocol; it exists to tell the
human auditor where to look and to state which rows the agent judged. The human audit
is `audit.json` in the run directory (50 deterministic rows) and must be filled by a
named person.

## Method

`rb analyze` flagged every row whose scoring could plausibly be wrong: parser failures,
LaTeX-decorated boxes, answers without a box, thinking responses whose reasoning stated
a different answer than the final response, and wrong answers within rounding or 2% of
gold. The agent then read, in full at the tail, all 47 incorrect responses, all 14
flagged rows (5 of them correct), and a seeded random sample of 30 correct responses:
82 of 400 responses, 20.5%. For each row the question asked was: does the extracted
value equal the answer the model itself presented as final, and if the model presented
no single final answer, is the unscorable verdict right?

## Verdict

No scorer defect was found. Every incorrect row is a model failure: the extracted value
is the model's own final boxed number, or the model boxed two different values, or it
boxed two quantities instead of a total, or the answer was cut at the 1,024-token
allowance while still deriving. All 30 sampled correct rows have a single bare boxed
number equal to gold.

| Category | Rows | Agent judgement |
|---|---:|---|
| Wrong final answer, cleanly boxed | 41 | model failure, scorer correct |
| Two different boxed values (hedging) | 2 | `conflicting`, correct handling |
| Two quantities boxed instead of a total | 1 | `invalid_number`, correct handling |
| Cut at 1,024 answer tokens while still deriving | 3 | `incomplete`, correct handling |
| Decorated boxes (`50\%`, `\$10`, `\$25`, `64 \text{ dollars}`) | 5 | parsed as intended by numeric-v4; 4 correct, 1 wrong on the merits |
| Reasoning stated a different answer than the final response | 5 | scored on the final response, as the protocol requires; see below |
| Near miss (137.33 vs 138) | 1 | model did not round up; scorer correct |
| Random correct sample | 30 | all bare boxed numbers equal to gold |

Counts overlap: 52 distinct incorrect-or-flagged rows plus 30 sampled correct rows.

## Observations the human auditor should confirm

1. **Reasoning versus final response.** In five thinking responses the reasoning's last
   stated answer differs from the final response. In two of them the reasoning had the
   gold answer and the final response lost it: bridge concrete (reasoning 1800, final
   2000, forced closure) and Frank's hamburgers (reasoning 4, final 0, natural closure).
   In one the final response corrected the reasoning (tires: reasoning 96, final 84,
   forced closure). The protocol scores the final response only. Scoring thinking by
   the reasoning's own last stated answer instead would change thinking accuracy by
   about one point; the exact figure is in `docs/pilot-v2-report.md`.
2. **Forced closure.** 14 of 200 thinking responses (7%) hit 4,096 reasoning tokens.
   Seven of the 14 still scored correct after the budget phrase. The other seven are on
   questions the model treats as contradictory: Brian's stones, Roman's coins, the paper
   stars, the bridge concrete, and Madeline's hours. Direct mode fails the same
   questions, and two of the three truncated answers are on them too.
3. **Questionable gold or wording, affecting both modes.** "Enrique has 2 132
   contracts" (gold 44 implies two 132-page contracts; all four responses read 2,132),
   "2 times less than half" (gold 6; three of four responses read it as a further
   halving), and Roman's coins (gold 2; every response produced a non-integer or a
   different reading). These are dataset artefacts, not scorer defects, and they inflate
   the "both always wrong" cell of the outcome matrix.
4. **Direct answers without chain-of-thought suppression** average 301 tokens and reach
   1,024 only when the model loops on a contradictory question; the allowance is
   adequate.

## Rows the human auditor should read first

Job-id prefixes from the pre-screen section of `report/analysis.md`:

- Parser failures: `a9486d7649ca` (two boxed quantities), `96c9457eaba3` and
  `0f4b8fc6a0e1` (hedged boxes).
- Reasoning/final mismatches: `c5a3a0967d30`, `f269cb8717a1`, `2c377c6e0e1c`,
  `525ebc87aed6`, `86b4255bcfc9`.
- Decorated boxes: `4fba7ed3861f`, `9acfad15d6a3`, `9ef14654c9f3`, `6ea2e0163d46`,
  `d753657d3223`.
- Near miss: `d85cf2258d82`.
- Truncated: `0504142858c9`, `b2f3c5c1cc7e`, `cf8a77146ed5`.

The 50 rows in `audit.json` are sampled deterministically and independently of this
list; both sets should be reviewed.
