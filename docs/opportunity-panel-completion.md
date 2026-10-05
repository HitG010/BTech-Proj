# Separately authorized opportunity-panel completion

The frozen opportunity study and its one-shot recovery stopped with 452/512
responses: all 256 Qwen3-1.7B jobs and 196/256 Qwen3-0.6B jobs. Its original
12-hour wall budget failed. That failure remains part of the record; this
completion child is a new user-authorized diagnostic continuation, not a claim
that the original protocol passed. The stopped original ledger conservatively
charges 342,047 tokens, including its unresolved attempts. Its three setup
reservations and original invocation counts (two 1.7B, one 0.6B) remain
unchanged. The pending 60 frozen 0.6B jobs reserve at most 92,220 additional
response tokens, so the maximum combined reservation is 434,267, within the
original 1,000,000-token ceiling.

`scripts/opportunity_panel_completion.py` writes only under the new ignored
`artifacts/research/data-efficiency-v1/opportunity-panel-v1/completion-v1/`
directory. Before any collection, `prepare` checks the exact original endpoint,
protocol, model assets and stopped recovery, pins all old study file hashes,
the unchanged backend/source and analysis inputs, and the exact 60 pending job
identities. The old parent and recovery status, journals, results, logs and
source are never rewritten. The new child owns one launch, one 0.6B invocation,
one setup, its own reservations/attempts/results/status and a one-time endpoint
score sidecar. No automatic restart or quality retry is allowed.

The original prompts, model revisions, decoder, per-job seeds, response caps,
generation implementation and v7 scorer are reused. Setup and job ceilings
remain 900 and 600 monotonic seconds; the child has a separate 4-hour wall
budget, including any sleep, and admission uses the maximum of new wall age and
charged operation seconds. All old plus new token charges must stay at or below
1,000,000. An unresolved new reservation retains its full charge. A detached
`caffeinate -s -i` guard runs only on AC power after the no-model full-wake and
clock check; sampled RSS remains capped at 9 GiB with two-second polling and
first-failure stop. Keep the laptop lid open and AC connected. The previous
diagnosis records lid-close and an AC-to-battery transition, not a Docker cause;
the power/log evidence is separate from the original frozen protocol. A sleep
assertion cannot override lid closure or all system power decisions.

After all 60 new responses are settled and the collector has exited, the
unchanged 452 parent responses and 60 child responses must cover exactly 512
frozen jobs. Only then may the separate finalizer fetch the selected 64
upstream-training references and score with the unchanged v7 parser. A durable
score-start marker precedes that access. The sidecar identity is the new
completion plan; cached score reuse validates records and scorer without
reopening references. Grouped opportunity analysis runs with the frozen folds,
seed and policies. The final report records the original budget failure,
combined accounting, old-file preservation and that the result is diagnostic,
not an acquisition/RL or superiority promotion. Official-test gold remains
sealed; cloud/API spend remains $0.

After source/test/doc review and freeze, the operator commands are:

```sh
.venv/bin/python -m scripts.opportunity_panel_completion prepare
.venv/bin/python -m scripts.opportunity_panel_completion status
.venv/bin/python -m scripts.opportunity_panel_completion launch
.venv/bin/python -m scripts.opportunity_panel_completion status
```

`launch` returns a detached PID and log path. Monitor only the new completion
status until `complete` or `needs_attention`; never launch it a second time.
Preparation, status and synthetic tests do not generate responses or open
references. The full 512-response endpoint alone permits selected-only gold
access. Preserve the frozen originals regardless of the child outcome.
