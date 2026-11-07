# Research map

An index of every study in this repository, with its protocol and result
records. Rewritten 7 November 2026; the older map, with its dated status
paragraphs, is in [history](history/research-map-2026-11-05.md).

**Start here:** the [short paper](../papers/thinking-selection/short/README.md),
the [full manuscript](../papers/thinking-selection/manuscript.md) (v0.8), and the
[project review](project-review-and-publication-plan-2026-10-29.md), which
explains the research arc and the publication plan.

**Ground rules for every study.** Questions are GSM8K training rows in frozen
roles; the official test split stays sealed. Each study froze its protocol,
grid, endpoints, and criteria before running, opened reference answers only
after all responses were complete, and recorded source, input, and output
hashes. Many records here are hash-checked by their scripts or later study
plans, so treat every protocol and result record in this folder as frozen: do
not edit or move it; corrections are separate, versioned files. Failed criteria
are reported as failed.

## 1. September development studies (older protocol)

Qwen3-1.7B, legacy generation code, numeric-v3/v4 scorers, two draws per mode.
Not comparable with later studies; summarized in manuscript Appendix D.

| Study | Record | Outcome |
|---|---|---|
| Pilot v1 and audit | [pilot-results](pilot-results.md), [verification](verification.md) | 256 answer tokens truncated thinking; measured the cap, not the modes |
| Answer-cap calibration | [calibration-results](calibration-results.md) | 512 answer tokens frozen |
| Question-only routing | [routing-learnability](routing-learnability.md) | No router beat cost-matched random |
| Stronger question-only routers | [stronger-router-study](stronger-router-study.md) | Decision-focused head beat Ridge, not random |
| Three-action continuation router | [continuation-study](continuation-study.md) | Joint minus confidence +.008, inconclusive |
| Shared-correctness router | [router-dev-results](router-dev-results.md) | Tied confidence's accuracy at more tokens |
| Review and confirmation design | [research-review-2026-09-24](research-review-2026-09-24.md), [confirmation-design](confirmation-design.md) | 3,100-question confirmation prepared, never run |

The unmerged protocol-v2 pilot is in [history/pilot-v2](history/pilot-v2/README.md).

## 2. Protocol repair (1–2 October)

| Step | Record |
|---|---|
| New protocol (`qwen3-boxed-budget-v3`, numeric-v5) and role allocation | [phase-1-protocol-reconciliation](phase-1-protocol-reconciliation.md), [phase-1-evidence-repair](phase-1-evidence-repair.md) |
| 25-question paired bridge: identical token sequences across protocols | [phase-1-bridge](phase-1-bridge.md) |
| Final-answer parser numeric-v7 | [parser-preflight](parser-preflight.md) |

## 3. Main panel: Qwen3-1.7B, 50 questions × 8 draws

| Step | Records | Outcome |
|---|---|---|
| Protocol and collection | [phase-2-repeat-panel](phase-2-repeat-panel.md), [phase-2-runtime-recovery](phase-2-runtime-recovery.md) | 800 responses |
| Predeclared learner | [phase-2-repeat-results](phase-2-repeat-results.md) | Fails 4 of 5 criteria; −.016 vs training-selected comparator |
| Parser compatibility | [phase-2-parser-compatibility](phase-2-parser-compatibility.md) | One wrapper added; labels unchanged |
| CPU regularization/compression | [phase-2-cpu-feasibility-protocol](phase-2-cpu-feasibility-protocol.md), [results](phase-2-router-feasibility-results.md) | −.014 vs confidence; fails |
| Compact contrastive/neural objectives | [phase-2-contrastive-protocol](phase-2-contrastive-protocol.md), [results](phase-2-router-feasibility-results.md), [review](contrastive-router-review-2026-10-02.md) | −.034 vs confidence; fails |
| Released CLM heads (local Qwen3-8B) | [clm-local-preflight](clm-local-preflight.md), [local-clm-and-power-results](local-clm-and-power-results.md), [phase-2-clm-probe-protocol](phase-2-clm-probe-protocol.md), [results](phase-2-clm-probe-results.md) | All four screens fail |
| CLM signal audit | [clm-research-assessment](clm-research-assessment-2026-10-03.md), [clm-signal-audit-protocol](clm-signal-audit-protocol.md), [clm-audit-completion](clm-audit-completion.md) | CLM AUROC .50 vs confidence .71 (imprecise) |

## 4. Two-solver panel: Qwen3-0.6B and Qwen3-1.7B, 64 questions × 2 draws

| Step | Records | Outcome |
|---|---|---|
| Design and power | [broader-signal-design](broader-signal-design.md) | +.01 needs about 2,010 questions |
| Preparation and 0.6B preflight | [opportunity-panel-preparation](opportunity-panel-preparation.md), [opportunity-solver-preflight](opportunity-solver-preflight.md), [results](opportunity-solver-preflight-results.md) | |
| Protocol, recovery, completion | [opportunity-panel-protocol](opportunity-panel-protocol.md), [runtime recovery](opportunity-panel-runtime-recovery.md), [completion](opportunity-panel-completion.md) | 512 responses |
| Results | [opportunity-panel-results](opportunity-panel-results.md) | Confidence +.153 over accepting for 0.6B; −.031 for 1.7B |

## 5. Follow-ups (5–7 October)

| Study | Records | Outcome |
|---|---|---|
| 0.6B fixed CPU pilot | [qwen06-next-experiment](qwen06-next-experiment.md), [protocol](qwen06-router-pilot-protocol.md), [results](qwen06-router-pilot-results.md) | 2 of 4 gates; parser-aware confidence becomes the baseline |
| Parser guard on 228 fresh questions | [validation protocol](qwen06-sparse-validation-protocol.md), [preparation](sparse-validation-preparation-results.md), [runtime protocol](qwen06-sparse-runtime-protocol.md), [results](sparse-validation-results.md) | One changed action; −.0003 |
| 1.7B diagnosis | [qwen17-performance-diagnosis](qwen17-performance-diagnosis.md), [results](qwen17-diagnosis-results.md) | Forced closure in 18 cells, 12 with a wrong thinking answer; post-hoc |
| 2k → 4k reasoning allowance | [protocol](qwen17-cap-bridge-protocol.md), [preparation](qwen17-cap-bridge-preparation-results.md), [runtime](qwen17-cap-bridge-runtime-protocol.md), [completion](qwen17-cap-bridge-completion-protocol.md), [results](qwen17-cap-bridge-results.md) | One rescue; utility −.038; keep 2k |

## 6. Threshold acquisition (8–9 October)

| Step | Records | Outcome |
|---|---|---|
| Literature and prior art | [novelty-literature](novelty-literature-2026-10-08.md), [g0-prior-art-review](g0-prior-art-review-2026-10-09.md), [algorithm](g0-threshold-algorithm-2026-10-09.md) | Method priority not supported |
| Synthetic study | [g1-synthetic-protocol](g1-synthetic-protocol-2026-10-09.md), [results](g1-synthetic-results-2026-10-09.md), [independent review](g1-independent-review-2026-10-09.md) | All four primary contrasts fail; recipe closed |

## 7. Post-hoc audits for the paper (29 October – 2 November)

Each reproduces the historical decisions first and runs on cached data only.

| Audit | Records | Outcome |
|---|---|---|
| Confidence–gain shape | [protocol](confidence-gain-shape-protocol.md), [report](confidence-gain-shape-report.md), [results](confidence-gain-shape-results.md) | Lower confidence goes with higher gain for 0.6B only |
| Token-level deferral | [protocol](token-deferral-protocol.md), [report](token-deferral-report.md), [results](token-deferral-results.md) | All three rules fail |
| Cost curves, refit intervals, agreement | [protocol](deferral-curves-protocol.md), [report](deferral-curves-report.md), [results](deferral-curves-results.md) | Learner trails confidence at all ten λ; refit intervals include zero |
| Reproduction from cache | [guide](reproduce-from-cache.md), [report](reproduction-report.md) | 195 of 195 checks pass |

## History

Superseded plans and roadmaps, launch snapshots, the agent handoff log, the
milestone log, and the archived branch tips are described in
[history](history/README.md).
