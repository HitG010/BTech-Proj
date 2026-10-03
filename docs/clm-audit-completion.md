# Additive completion of the cached CLM audit

The first `audit_clm_signal execute` invocation exited with `KeyError('accuracy')`
after its fixed rank calculations, before writing any report. The existing
cached policy summaries expose `mean_accuracy` and `mean_tokens`; the new launcher
incorrectly expected `accuracy` and `tokens`. Synthetic rank tests did not cover
that integration boundary. No fitting, encoder, solver or reference call occurred.

Preserve the original source/test/protocol checkpoint `b2e4de8` and immutable audit
plan `048687b3…350846`. Do not rerun its launcher. The separate
`scripts/complete_clm_signal_audit.py` reads the correct summary keys, invokes the
unchanged pure rank functions/spec, and writes to `clm-signal-audit-v1/completion-v1/`.
Two integration-schema tests cover the corrected boundary. The completion source,
tests and this record are checkpointed and frozen in an additive plan before
recomputing exactly the original descriptive statistics. No metric, bootstrap
setting, action, label or primary gate is changed.

```bash
PYTHONPATH=src .venv/bin/python -m scripts.complete_clm_signal_audit prepare
PYTHONPATH=src .venv/bin/python -m scripts.complete_clm_signal_audit execute
```

Successful completion is additive and exclusive. It verifies original source and
input identity plus all 2,319 protected files. The failure of the initial launcher
remains part of provenance; this is not a second policy trial.
