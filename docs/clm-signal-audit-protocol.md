# Cached CLM score audit protocol

Prepared 2026-10-03 after observing the completed Phase 2d policy results. This
audit is explicitly post-hoc and descriptive. Its separate code/test/protocol
checkpoint and immutable plan precede all additional rank calculations.

Read the unchanged completed repeat panel, cached v7 labels, released-head score
sidecar, prior CLM report and independent verification. Use the existing guarded
loader. Never fit, encode, generate, fetch references, change actions or edit any
completed source/artifact. Write exclusively to `clm-signal-audit-v1/`.

Compute tie-aware AUROC for three already defined events: positive paired
incremental gain, incorrect direct draft, and harmful escalation. Compare the
fixed think-minus-accept margin against negative direct post-warper confidence.
Higher scores predict each event. The harmful-event endpoint measures association,
not a desirable direction for a router. Use all eight draws descriptively; they
remain 50 question groups. Sample all eight draws together within a whole-question
bootstrap, 2,000 replicates, seed 20261007, central 90% intervals. Report undefined
one-class replicates explicitly. Paired AUROC differences use identical resamples.

Also report an unweighted within-question mean AUROC restricted to groups with
both event classes, including the informative-group count. This subset cannot
represent the whole population. Correlate question mean scores from A4 with mean
gain in B4 and reverse using Spearman; these correlations are descriptive without
intervals. No same-question transfer becomes a deployable feature.

Report the already fixed zero-margin rule's event precision/recall and harmful
decisions, plus margin range. Calculate the cost preference at which the *fixed*
zero-shot and frozen confidence actions tie using the average four-draw accuracy
and token differences. This sensitivity omits encoder cost and is not a new
operating point, threshold search or justification to change primary λ=.05.

The inherited conditional-bootstrap correction remains in its original additive
sidecar. No primary interval or failed gate changes. The original frozen verifier
must confirm preservation of all 2,319 protected files before the audit result is
written. Sources, tests, protocol, input payloads and NumPy/SciPy versions are
pinned in the plan. Output files use exclusive writes; completed analysis is not
restarted.

```bash
PYTHONPATH=src .venv/bin/python -m scripts.audit_clm_signal prepare
PYTHONPATH=src .venv/bin/python -m scripts.audit_clm_signal execute
```

Four additional synthetic tests in `tests/test_clm_objective_checks.py` check
two-action softmax algebra, naive duplicate-action InfoNCE ambiguity, the
regret-weighted BCE target and full cost accounting. They train no real model.
The current upstream choice-training implementation already deduplicates action
texts and supports multi-positive reverse targets; these checks identify an
adaptation hazard, **not a demonstrated upstream bug**.
