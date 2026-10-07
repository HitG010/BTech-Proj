# Fresh sparse validation: background run started

Runtime source/test/protocol froze at **440f655** after all **694 offline tests**,
Ruff and independent code review passed. The cutoff, question child, dataset
and prior studies remain unchanged.

Plan: `e747929078995cbd56e34a6ed44c8e91d2590d834a6c2838565fb63d055bff9b`.
Independent prelaunch review `7d67ae2a…8edea` checks three runtime source pins,
nine prepared files, eleven preparation pins, 2,652 closed-study files, all 456
potential jobs/seeds, model/scorer/config identities and the no-gold dataset.
Required launch marker: `80310432…81d9a`. No model or reference entered that audit.

One detached launch **217655d0341e4a8e84f144ccee66deb9** is running. Supervisor
PID **55471**, temporary sleep-guard PID **55472**, collector PID **55488**,
invocation **0ebc68c1a9f145ea8119672fc26adc16**. Launch verification
`3f8cf814…7050c8` confirms **8/228** complete direct responses, 1,933 charged
tokens including an active reservation, both own sleep assertions and no
reference-access marker. This is a launch snapshot, not final cost or efficacy.

Authoritative status is
`qwen06-sparse-validation-v1/runtime-v1/status.json` under the research artifact
root. The worker completes all direct jobs, freezes the gold-free eligibility
mask, then completes all selected thinking jobs if at most 32 are eligible.
Complete activated endpoint and exited collectors gate only eligible training
references, v7 scoring and sparse-difference analysis. Zero eligible states mean
zero references. No absolute full-policy accuracy or utility is identified.

The cumulative limit is 250k tokens/six hours, including setup, failures, sleep
and gaps. First failure stops; one explicit runtime resume is possible within
unchanged limits. Do not relaunch, reset journals, alter pinned sources/assets,
repeat preparation or add gold. Keep the Mac open/on AC and Docker running.
No API/cloud, Kaggle upload or training is part of this run.

The [1.7B cap bridge](qwen17-cap-bridge-protocol.md) is frozen as prep-only code.
Its ordered gate requires validation `complete` and report-bound independent
review with `checks_passed: true`. Baseline efficacy need not pass that ordering
gate. The bridge uses 36 new matched 2k/4k thinking jobs on 18 old cap-hit cells
across 11 development groups, with original seeds inherited and actual token
differences charged. Its generation executor is a later implementation boundary.
At launch, no cap preparation or 1.7B generation had started. Preserve previous negative
evidence regardless of the validation outcome.

## Terminal checkpoint

The launch snapshot above is superseded by the
[completed validation result](sparse-validation-results.md). Terminal status
is `complete` at 2026-10-06 19:16:18 UTC: 228 direct plus one thinking response,
zero failures/retries, 43,448 tokens. All workers exited. Independent completion
review `9a8077b5…ff882` passed; the scientific screen failed. Do not resume,
relaunch, rescore or reopen references.

The separately ordered [1.7B preparation](qwen17-cap-bridge-preparation-results.md)
is now complete and verified. Its generation executor remains unimplemented.
