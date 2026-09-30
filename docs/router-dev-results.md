# CPU development test of the shared-correctness router

Completed 2026-09-23. The reproducible local outputs are
`artifacts/router-dev/shared-base-v1/report.md` and its checksummed
`report.json`; `curve.csv` and `accuracy-cost.png` contain the full out-of-fold
accuracy–token curve. Run the comparison again from the repository root with:

```sh
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -m reasoning_budget.router_dev
```

This loads saved generation records and cached MiniLM question features. It fits
small CPU models; it does not generate Qwen responses or use MPS/CUDA.

## Question and design

Can one coherent estimate of first-draft correctness, plus action-conditional
rescue and harm, choose a continuation better than the existing joint model,
gain-ridge, and a tuned confidence gate?

The test pooled 100 calibrated pilot questions and 100 validation questions.
These are **development** data that already informed router design. The
previously inspected 100-question continuation diagnostic and the official
500-question test set were excluded. Five outer folds held out whole questions,
balanced by source role; each question's two first-draft orientations stayed in
the same fold. Three inner question-level folds selected regularization and
features for each learned family. The confidence threshold and continuation
action were fitted on each outer training fold. All metrics below are pooled
out-of-fold results over 200 questions, averaging two orientations within a
question. The primary cost preference remained `λ=0.05`.

The new model fits one logistic `P(first correct)` head. For each continuation
action it fits conditional `P(rescue | first wrong)` and `P(harm | first right)`
heads, shrunk toward training-only Beta(1,1) rates; rare classes fall back to
those rates. A ridge head predicts extra generated tokens. The small candidate
grid varied response-only versus question-plus-response features, logistic
regularization, and shrinkage. The question features use the existing frozen
MiniLM embedding with train-fold PCA16. The new model never sees the second
draft, thinking output, gold answer, or held-out labels when choosing an action.

## Result

| Policy | Accuracy | Charged tokens/question | Utility, λ=.05 |
|---|---:|---:|---:|
| Always direct | 86.00% | 223.8 | 0.8488 |
| Always thinking | 91.50% | 1,654.5 | 0.8323 |
| DART SC-2 adaptation | 90.25% | 702.2 | 0.8674 |
| Shared-correctness router | 90.25% | 622.0 | 0.8714 |
| Existing joint router, refitted in folds | 88.50% | 641.9 | 0.8529 |
| Gain-ridge, refitted in folds | 89.25% | 794.7 | 0.8528 |
| Tuned confidence continuation | 90.25% | 589.4 | 0.8730 |

Shared minus gain-ridge utility was **+0.0186**, with an exploratory paired
whole-question bootstrap interval **[+0.0018, +0.0342]**. Shared minus the
existing joint model was **+0.0185** [+0.0061, +0.0315]. But shared minus the
confidence baseline was **−0.0016** [−0.0092, +0.0055]. Confidence achieved the
same accuracy using 32.6 fewer generated tokens/question, so the shared router
does not clear the practical baseline at the preselected preference.

The full curve has a **secondary high-accuracy lead**. At `λ=0`, shared reached
91.50% at 1,285.7 tokens/question; confidence reached 90.50% at 1,283.2.
Their paired utility difference was +0.0100, with an exploratory whole-question
interval [+0.0025, +0.0200]. At `λ=0.01` and `0.025`, the point differences
were also positive (+0.0136 and +0.0147), but their intervals crossed zero.
The settings were selected at `λ=0.05`, and these other cost preferences were
inspected afterward. None of these secondary intervals adjusts for testing
many preferences or for the development data having shaped this model.

Shared minus confidence utility by outer fold was approximately +0.0000,
−0.0033, −0.0089, −0.0004, and +0.0045. Four of five folds selected only the
first response's four features rather than adding question embeddings. The
first-correct out-of-fold Brier score was 0.0999. Rescue and harm events remain
sparse: among 400 linked first-draft states, 56 were initially wrong. The
probe action rescued 22, and thinking immediately rescued 35; among 344 right
first drafts, those actions harmed five and 13 respectively. These are
descriptive orientation counts, not 400 independent questions.

## Interpretation and next decision

The shared estimate improves on the two refitted learned baselines, which is
useful model simplification. Its action choices still do not beat a cheap
confidence gate at the chosen preference. The high-accuracy curve is worth
testing only after freezing a fresh endpoint; it does not replace the original
primary comparison. The intervals above are exploratory:
the same 200 questions influenced the research direction and the comparison
was not a separately frozen confirmation. The cached replay excludes CPU
encoding/routing time; full DART SC-Budget and ReASC are not reproduced. The
user waived the human scoring audit.

Do not freeze this shared router as a claimed new method or launch the prepared
3,100-question confirmation for it. That confirmation remains for the unchanged
old router and has not begun generation. The next useful router question is
whether information *after two agreeing direct drafts* can identify the rare
wrong-consensus cases without paying for thinking on every agreement. Only 11
wrong agreements exist across the 200 development questions, so keep any such
test small, strongly shrunk, and exploratory. A task with a wider direct-versus-
thinking gap may be needed before investing in another large router study.

`src/reasoning_budget/router_dev.py` contains the fit and replay procedure.
`tests/test_router_dev.py` checks rare-event fallback, question grouping, and
that changing held-out outcomes does not change that fold's actions. All 116
offline tests and Ruff lint passed after implementation; the final report
generation was also rerun after code formatting. The frozen continuation and
confirmation source files were not changed.
