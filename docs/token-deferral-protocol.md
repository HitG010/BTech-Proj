# Token-level deferral check protocol

Prepared 2026-10-30 on `codex/confidence-acquisition-plan`. This is check 2 of
Phase 2 in the [cascade reframing record](../papers/thinking-selection/cascade-reframing-2026-10-29.md#5-analyses-this-framing-calls-for-phase-2).
It is **post-hoc and exploratory** on the reused 50-question repeat panel.
Code, tests, and this protocol must be committed, and the `prepare` plan
written, before `extract` and `execute` run.

## Question

[Gupta et al. (2024)](https://arxiv.org/abs/2404.10136) report that a
sequence-level aggregate of token uncertainty suffers from a length bias, and
that a learned deferral rule on token-level uncertainty quantiles is more
consistent. Our confidence feature is such an aggregate: the mean post-warper
log probability of the direct draft. Does a token-level deferral rule improve
on the frozen confidence policy on held-out questions?

This is an adaptation, not a reproduction. The full text of Gupta et al. was
not retrievable in the session that wrote this protocol; their exact quantile
set, uncertainty measure, and model class are not copied.

## Step 1: label-blind token extraction

`extract` reads the 400 completed direct drafts and their questions through the
repeat endpoint reader. It opens no score, label, or reference. It rebuilds the
collection backend from the frozen study configuration and requires its full
metadata to equal the backend metadata recorded in the repeat protocol
(model and tokenizer revisions, chat template hash, EOS IDs, decoder settings).

For each draft it rebuilds the exact chat-template prompt, appends the recorded
`answer_token_ids`, and runs one forward pass (teacher forcing). No token is
generated. It stores, for every answer token:

- the **pre-warper** log probability, `log_softmax` of the model logits at the
  recorded token. This is the token-level uncertainty used for features.
- the **post-warper** log probability after the recorded temperature, top-k,
  and top-p settings, as a diagnostic only.

### Fidelity gate (must pass before analysis)

- All 400 direct drafts are present, one per question and draw.
- The rebuilt prompt length equals each record's `prompt_tokens`.
- The stored token count equals each record's `answer_tokens`, and decoding the
  tokens reproduces `final_answer` (except `reasoning_in_answer` records, whose
  answer was blanked at collection).
- The recomputed mean pre-warper log probability is within 0.02 of the recorded
  `mean_generated_logprob_raw` for at least 99% of drafts, and never more than
  0.10 away. Teacher forcing in float16 is not bit-identical to cached
  incremental decoding, so exact equality is not required.

Agreement of the recomputed post-warper mean with the recorded confidence, and
the number of tokens falling outside the recomputed post-warper support, are
reported but do not gate.

## Step 2: features

For each draft, from its pre-warper token log probabilities: quantiles at
0, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, and 1.0 (`numpy.quantile`, linear
interpolation), their mean, and `log(1 + token count)`. Eleven features.

## Step 3: rules and evaluation

Evaluation reuses the repeat study's design exactly: the five frozen question
folds; train on one four-draw half of training questions and evaluate on the
other half of held-out questions, in both directions (A→B and B→A); the
eight-draw condition is secondary. All fitting, tuning, and threshold choice use
only training questions and training draws. Inner choices use the repeat
study's four inner question folds.

| Rule | Definition |
|---|---|
| **Learned error score (primary)** | Standardized features; L2 logistic regression (C = 1) predicting an incorrect direct draft. Its escalation cutoff is chosen to maximize training utility on out-of-fold inner predictions, with the repeat study's threshold search; the final model is refitted on all training rows |
| Minimum-token threshold (secondary) | Escalate when the lowest token log probability is below a cutoff chosen on training utility with the same threshold search as confidence |
| Token gain Ridge (secondary) | Standardized features; Ridge regression predicting the gain \(G\); alpha in {1, 10, 100, 1000} and decision threshold in {0, 0.02, 0.05} chosen by inner mean utility, ties preferring larger values |

The comparator is the **frozen four-draw confidence policy**. For every
condition and fold, the analysis first reproduces the historical accept,
escalate, confidence, solver-only, and combined decisions and requires them to
equal those in the primary repeat report. It then compares each rule with those
confidence decisions question by question, at \(\lambda = .05\).

## Screen and reading, fixed before execution

Intervals use 2,000 whole-question bootstrap resamples, seed 20261030, central
90% intervals, with fitted actions held fixed (as in the earlier controls).

The **primary rule passes** only if all three hold, matching the CPU, compact
neural, and CLM screens:

1. its average four-draw utility difference versus confidence is at least 0.01;
2. both directional means (A→B and B→A) are positive;
3. every leave-one-question-out average is positive.

Secondary rules are reported with the same statistics but cannot change the
primary reading. Whatever the outcome, the result is exploratory on reused
data. A pass would justify a separately frozen confirmation, not a claim; a
fail is evidence against this recipe only, not against token-level features in
general.

Also reported descriptively: pooled AUROC of selected single features for
incorrect direct drafts and for positive-gain states, and the Spearman
correlation of confidence and of the minimum token log probability with answer
length.

## Outputs and preservation

Everything is written to
`artifacts/research/data-efficiency-v1/token-deferral-v1/` with exclusive file
creation: `plan.json`, `token-logprobs.json`, `extraction-report.json`,
`report.json`, and `report.md`. Completed steps are not restarted. `execute`
reruns the frozen repeat-study verifier.

## Commands (on the machine holding `artifacts/` and the model cache)

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_token_deferral prepare
```

```bash
caffeinate -i env PYTHONPATH=src .venv/bin/python -m scripts.audit_token_deferral extract
```

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_token_deferral execute
```

`extract` loads Qwen3-1.7B once and runs 400 forward passes; expect several
minutes. Synthetic tests are in `tests/test_audit_token_deferral.py`; they load
no model and read no study data.
