# Evidence available for the next paper

Snapshot: 2026-10-08, base commit `ee88d64`.
This is an index of existing evidence. It adds no experimental result.
Use each study's original population, protocol, scorer, and weighting.
Do not pool incompatible rows or describe development data as fresh confirmation.

| Evidence block | Main finding | Permitted use | Important limit |
|---|---|---|---|
| [Protocol bridge](phase-1-bridge.md) | 200 responses; six engineering gates passed; matched token sequences agree. | Protocol migration case study and reproducibility evidence. | Agreement on 25 questions does not establish universal equivalence. |
| [Parser preflight](parser-preflight.md) | Rejected v6; retained separately tested v7. | Evidence that parser changes need controlled regression checks. | Primary historical labels remain frozen. |
| [Parser compatibility](phase-2-parser-compatibility.md) | One extraction change in 1,900 outputs; no accepted-answer regressions. | Narrow syntax-compatibility finding. | It does not establish general mathematical correctness. |
| [Repeat panel](phase-2-repeat-results.md) | 800 responses on 50 questions; four of five gates fail; main utility difference −.016204. | Main within-solver development case with independent draw halves. | Small group count; reused data; fixed-policy intervals omit research selection. |
| [Capacity and objective controls](phase-2-router-feasibility-results.md) | 1,035 Ridge and 600 neural fits; selected differences −.014287 and −.033817 versus confidence. | Matched controls showing limits of the tested recipes. | Fits are not independent datasets. Draft truncation and one neural optimization seed limit scope. |
| [Released CLM probe](phase-2-clm-probe-results.md) | 402 encodings; 450 Ridge fits; calibrated difference −.033262. | Bounded representation-transfer case with measured encoder cost. | Quantized backbone; no full-precision equivalence or live joint-latency claim. |
| [CLM signal audit](clm-research-assessment-2026-10-03.md) | Positive-gain AUROC .500450 versus .705045 for negative confidence. | Descriptive evidence of poor action-value ranking in this recipe. | Wide paired interval; no population inferiority conclusion. |
| [Two-solver panel](opportunity-panel-results.md) | 512 responses on 64 groups; 0.6B confidence utility gain +.152677 over direct; 1.7B difference −.030540. | Evidence that the opportunity pattern depends on solver size in this family. | Two sizes are not two independent model families. |
| [0.6B learned pilot](qwen06-router-pilot-results.md) | 20 fits; +.003516 utility versus confidence; two gates fail. | Small-model learner result and comparison with simple controls. | Parser-aware development gain rests on three rescued groups. |
| [Fresh sparse validation](sparse-validation-results.md) | 228 direct and one thinking response; zero scored accuracy gain. | Prospective test of a specific rule that changed only one action. | Does not identify full-policy accuracy; one event cannot reject all parser-aware rules. |
| [1.7B cap bridge](qwen17-cap-bridge-results.md) | 36 responses on 11 selected groups; one rescue; utility −.037668. | Matched cap intervention with exact prefix/replay checks. | Enriched development cohort; intervals include zero; default remains 2k. |

## Claims that are ready for a scoped manuscript draft

- The tested representation and learner recipes did not pass the declared gates on these panels.
- Confidence was a strong control in the tested setting.
- In the shared 64-group panel, the practical value of thinking differed between the two solver sizes.
- A favorable parser-aware development observation did not reproduce as a scored gain in its sparse prospective follow-up.
- More reasoning tokens did not establish positive utility in the selected 1.7B cap study.
- The project preserved failed runs, charges, and original protocols through separately declared recovery steps.

These findings describe the named experiments. They do not establish universal impossibility or superiority.
Human mathematical scoring was waived. Automated and agent checks must be named accurately.
The latest recorded full offline suite is 720 tests. No tests were rerun for this planning change.

## Gaps before a broad empirical claim

1. A precise added finding beyond the prior audits in literature items L15–L17.
2. An independent second task or a deliberately narrow single-task claim.
3. A faithful current external control when claiming a method comparison, especially DART.
4. Uncertainty that matches the claimed policy-training procedure, rather than only fixed actions.
5. Full deployment cost for any cross-model system recommendation.
6. A release package that excludes sealed data and obeys source/model/data licenses.

## Reusable artifacts

The candidate release includes protocol schemas, collector state machines, cost ledgers,
parser fixtures, aggregate scores, analysis recipes, and a claim-to-artifact manifest.
It can support the paper and the BTech thesis even if acquisition fails.
Prepare a clean additive export. Do not edit or publish the original ignored artifact tree directly.
Check licenses and unpublished data boundaries before selecting raw responses for release.

## Current boundary

The opportunity completion, sparse validation, and cap completion have terminal `complete` records.
Their result records report exited workers. Old stopped parent statuses remain preserved.
Official test is sealed. Both confirmation studies are unstarted. There are 256 unclaimed reserve rows.
Acquisition, MATH, Jev/RL, and training remain unstarted or stopped as recorded.
The new plan changes the research question only. It does not change these execution states.
