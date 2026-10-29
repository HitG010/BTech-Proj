# Matched 1.7B cap bridge: complete

All **36 responses** are complete: 18 matched 2k/4k pairs on 11 existing
development questions. The separate completion finished its 30 jobs with
zero new failures or retries. Terminal status is `complete` at **2026-10-07
17:20:17 UTC**; collector and finalizer exited zero, all owned workers exited,
and nine existing locks are free. Do not prepare, generate, score or finalize
again, or reopen the selected references.

Independent cached-only review `0172f489…fed89` verified all inputs, responses,
charges, timestamps, source/model identities, prefix gates and statistics.
All 18 new paired reasoning prefixes match. Every new 2k control also exactly
replays its cached original reasoning, answer and inserted token streams.
The review invoked no model, reference access, scorer, fitting or executor.

## Result at the frozen cost weight

The primary summary gives each question equal weight after averaging its
selected draws. These questions were selected by old forced-closure metadata;
the table does not describe whole-panel or general model accuracy.

| Primary mean over 11 question groups | 2k | 4k | 4k minus 2k |
|---|---:|---:|---:|
| Scored accuracy | 36.36% | 40.91% | +4.55 percentage points |
| Generated tokens | 2,430.59 | 4,093.05 | +1,662.45 |
| Utility at lambda .05 | .242107 | .204439 | −.037668 |

Paired 95% question-bootstrap intervals are **[0,+.136364]** for accuracy,
**[1,225.67,1,996.95]** for extra tokens and **[−.094767,+.061647]** for utility.
Both accuracy and utility intervals include zero. There is one rescued response
on one question and no harms. The secondary equally weighted 18-cell count is
**6/18 correct at 2k versus 7/18 at 4k**; its utility difference is −.033025.
Do not mix these cell means with the primary question-weighted intervals.

The extra reasoning allowance produces a small observed accuracy increase,
with a larger token cost and lower point utility. It does not support changing
the default to 4k at the preselected lambda. Keep the frozen 2k operating point
while planning the next study. The utility interval does not establish a
population disadvantage, and this reused, enriched cohort supplies no fresh
superiority or novelty confirmation. Do not change lambda, expand the cap
grid or fit another router from this result.

Cached v7 statuses are 13 accepted / five rejected for controls and 15 accepted
/ three rejected for extended responses. Eight accepted extended outputs are
scored incorrect. These are scorer outcomes; no new human or mathematical
correctness audit was performed. Future diagnosis must separate presentation
failures from accepted numeric errors using cached data before deciding on a
training design. A math adapter still needs a separate corpus, exclusions,
environment, solver identity and fresh evaluation protocol.

## Accounting and boundaries

The completion charges **99,136 tokens / 4,641.4133 operation seconds**, with
4,655.2292 collection wall seconds, one setup and 30 settled attempts. Combined
old plus new charges are **127,171 tokens / 7,262.9591 operation seconds**.
The old failed 2,814-token response and unknown 4,610-token/600-second reservation
remain charged. All 85 cap-parent files, 2,652 closed old-study files and 2,319
protected historical originals are preserved. Both original runtime stops and
the separately authorized eight-hour/1,800-second completion deviation remain
in the report; the old four-hour protocol was not completed.

The longest completed new backend call was 251.0471 seconds, with a maximum
job receipt charge of 251.3651 seconds. Every new job finished within 600
seconds, so the larger deadline was not reached. The available records do not
establish why this invocation ran faster or what caused the earlier stalls.

Full coverage, worker exit, accounting/preservation and all prefix gates passed
before exactly 11 selected upstream-training references were opened once by
the new private finalizer. The question snapshot remains gold-free; scores
are cached separately. No other references or sealed outcomes were opened.
No new allocation, training, paid cloud/API or Docker change occurred; 256
reserve rows remain unclaimed and cloud/API spend is $0.

Source/tests/protocol `dd4d733`, plan `a718942c…00836`, report `11e61657…e1622`,
scores `38a91695…0ca47`. Authoritative terminal state is
`qwen17-cap-bridge-v1/completion-v1/status.json`. Preserve the completed child
and every frozen source/input/result. The original runtime's stopped status
is historical and remains unchanged.
