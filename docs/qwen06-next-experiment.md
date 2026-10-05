# Next 0.6B experiment: value beyond confidence

Design date: 2026-10-06. This follows the completed and independently verified
[two-solver diagnostic](opportunity-panel-results.md). Local work only; Docker
stays running. The original wall-budget failure and all completed studies remain
unchanged. The user authorized the next step after the result review.

## Decision and immediate test

The 0.6B result establishes a useful opportunity regime: 24/64 questions have
positive thinking gain in at least one draw. Confidence routing improves utility
by .152677 versus accepting the direct draft. It does **not** establish that a
learned router can beat confidence. That is the next question.

Run one separately frozen, bounded CPU development test on the existing 64
groups. Do not generate more labels to search for a favorable architecture.
The [pilot protocol](qwen06-router-pilot-protocol.md) fixes just two models:

- One Ridge model on direct-answer confidence, log answer length and a gold-free
  parser-rejection indicator.
- The same Ridge model using confidence alone, to isolate any value from the
  two added features.

Both use alpha 10 and escalate only when predicted incremental utility is greater
than zero. There is no parameter grid. The target is thinking correctness minus
direct correctness minus .05 times thinking tokens/1000. Future thinking outcomes
and costs are supervision only; they cannot enter the feature vector. The solver
and scorer remain frozen.

Use five question folds and both opposite-draw directions. Train on one draw
excluding the held-out question fold; evaluate on the other draw's held-out
questions. Fit scaling on training rows only. This gives ten fits per learner,
twenty total. Keep the exact previously recorded confidence actions as the main
baseline. Also report fixed accept/think, the matched confidence-only learner,
and confidence routing with forced escalation on parser rejection.

Freeze source, tests, features, folds, inputs, settings and gates before fitting.
The primary three-feature candidate is promising only if average utility gain
over confidence is at least .01, both draw-direction point gains are positive,
and its average utility is no worse than either cheap matched/heuristic control.
Report all policies and intervals even if a gate fails. Do not pick another
alpha, feature set or winner from the held-out results.

The panel already influenced the 0.6B choice and these features. All new fits are
**exploratory development**. Conditional intervals keep actions fixed and omit
refit uncertainty. Measure feature/prediction CPU time separately from generated
tokens; idle cached timing is not live co-resident latency. No model download,
embedding, new generation or reference access is needed for this stage.

## Conditional fresh follow-up

The live question-only audit finds 548 parent reserve rows, one registered
64-question child, and **484 unclaimed** rows. Leave the 1,200 acquisition,
200 validation, 2,000 confirmation and official-test roles unchanged. Do not
allocate all 484 across a speculative train/dev/test plan now.

If every pilot gate passes, propose **228 new reserve questions** for a separate
fixed-policy signal test. The existing 64 questions become declared training/development;
they are never fresh evaluation. Before selecting any new question, freeze the
one nominated learner, its full-data refit, confidence comparator and cheap
controls, role manifest, fresh seeds, scorer, analysis and global runtime budget.
No fresh label may tune a threshold, feature, lambda or model.

One independent direct/thinking pair per fresh question gives 456 responses.
The unchanged caps reserve 3,074 tokens per pair, hence **700,872 response-only
tokens**. Setup, failures and all router time require an additional frozen
envelope. This is a conditional size proposal, not an allocation or collection
protocol. If allocated, 256 reserve rows would remain unclaimed.

The planned primary comparison remains learner minus confidence at lambda .05.
A fixed-policy positive signal would need a prespecified interval and effect
criterion, plus the cheap controls; passing a diagnostic does not automatically
start acquisition or sealed confirmation. The final endpoint and success rule
must be frozen in the future collection protocol before fresh labels exist.

## Power and what the sample can support

`scripts/qwen06_next_design.py` writes a separate reproducible planning record.
It audits existing question-only role/child manifests and completed protocol/
report metadata. It never selects questions, fits a model, scores an output or
reads upstream references. It uses the earlier frozen pure normal-power helpers,
not the earlier study executors. The grid is learner-minus-confidence, two-sided
alpha .05, target power 80%, hypothetical paired question SDs .05/.10/.16/.25,
effects .01/.03/.05 and independent group counts 64/128/200/228/484/2000.

| Hypothetical SD | Questions for +.01 | For +.03 | For +.05 | Effect detectable with 228 |
|---:|---:|---:|---:|---:|
| .10 | 785 | 88 | 32 | about .0186 |
| .16 | 2,010 | 224 | 81 | about .0297 |
| .25 | 4,906 | 546 | 197 | about .0464 |

These are known-SD normal sensitivities, not exact finite-sample guarantees.
Neither the candidate's improvement nor its fresh single-draw SD is established.
Do not reuse the .152677 confidence-minus-direct effect, or a two-draw descriptive
SD, to claim power for learner-minus-confidence. 228 questions may detect a
moderate effect under SD .16; they generally cannot confirm a +.01 gain. Repeated
responses do not multiply the number of independent questions. This also does
not power the acquisition learning-curve endpoint or include training variance.

## Contribution and architecture boundary

The fixed Ridge test is a control, not a novel method. Contrastive routing and
repeated solver-response supervision are present in
[RouterDC](https://arxiv.org/html/2409.19886). Cost-aware contrastive routing is
present in [CSCR](https://proceedings.neurips.cc/paper_files/paper/2025/file/e46eb6403af68506331f941282d838aa-Paper-Conference.pdf).
RL selection of thinking mode is present in
[Thinkless](https://arxiv.org/html/2505.13379v2). A new loss name or adding RL
cannot supply the paper contribution.

Generic cost-aware experiment acquisition is also covered by
[Cost-Aware Near-Optimal Policy Learning](https://ojs.aaai.org/index.php/AAAI/article/view/35027).
The authors' [Targeting the Exceptions implementation](https://github.com/wikit-ai/online-active-learning-llm-routers)
already selects informative query annotations for a router. These methods are
prior-art boundaries, not interchangeable benchmark scores for this endpoint.

Our conditional advancement hypothesis remains specific: use uncertainty in
incremental direct-to-thinking utility to decide whether the next paid label
should cover a new question, a missing action, or an independent repeat. To
support that contribution, it must beat random acquisition, uncertainty-only,
new-question-only and fixed-repeat allocations at equal **acquired token**
budgets, with ablations and untouched evaluation. Full inference overhead and
another task/solver setting remain required. No such win exists yet.

Released CLM and Jev/RL remain conditional. The completed CLM recipe failed;
its frozen outputs remain preserved. This stage buys evidence about cheap
observable signal before expensive representations or on-policy exploration.
If the fixed pilot fails, stop that recipe and revise the signal hypothesis
without extending its grid or spending the proposed fresh-question budget.
