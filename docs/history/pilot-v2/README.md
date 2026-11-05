# Pilot v2 reports (September 2026)

Copied from the tip of `research/pilot-v2` (`6c7903c`, tagged
`archive/pilot-v2`), which was never merged into the main line. The text is
unchanged except that absolute local paths are replaced with `~/Documents/...`.
Links and commands inside these files refer to that branch's layout, not this
one.

- [pilot-v2-report.md](pilot-v2-report.md): feasibility report. Direct 83.5%,
  thinking 93.0%, oracle 96%, confidence AUROC .83.
- [pilot-v2-prescreen.md](pilot-v2-prescreen.md): agent pre-screen for the
  targeted human audit.
- [project-status.md](project-status.md): what was built, results, and next
  steps as of 9 September.

These runs used a different protocol (4,096/1,024 token caps, the model-card
prompt, older scorer) and are not interchangeable with later studies. The
backend fixes were re-implemented in the protocol reconciliation
([record](../../phase-1-protocol-reconciliation.md)). The paper does not report
them; its Appendix D covers the later September studies on `master` and
`research/router-studies`.
