# Confidence–gain shape audit

Post-hoc, descriptive, reused development data. See `docs/confidence-gain-shape-protocol.md`.

Two-solver runtime environment fields differing from collection: platform. Cached bytes were verified by hash; no generation or scoring occurred.

## repeat_qwen3_1.7b

Reading: **inconclusive**. States 400; mean gain -0.0195; pooled Spearman 0.1553 [-0.0021, 0.2975]; between questions -0.0348 [-0.3007, 0.2447]; within questions -0.0555 [-0.1584, 0.0476]; monotonicity violations 2.

| Bin | States | Confidence range | Direct acc. | Thinking acc. | Thinking tokens | Mean gain [90% interval] | Rescues | Harms | Both wrong |
|---:|---:|---|---:|---:|---:|---|---:|---:|---:|
| 1 | 80 | -0.1025 to -0.0499 | 0.738 | 0.900 | 1638.0 | 0.0806 [-0.0158, 0.1757] | 17 | 4 | 4 |
| 2 | 80 | -0.0499 to -0.0386 | 0.963 | 0.988 | 1390.6 | -0.0445 [-0.0822, -0.0036] | 3 | 1 | 0 |
| 3 | 80 | -0.0385 to -0.0306 | 0.975 | 0.963 | 1416.8 | -0.0833 [-0.1443, -0.0316] | 2 | 3 | 0 |
| 4 | 80 | -0.0305 to -0.0205 | 0.938 | 0.975 | 1349.5 | -0.0300 [-0.1153, 0.0813] | 5 | 2 | 0 |
| 5 | 80 | -0.0205 to -0.0026 | 0.863 | 0.900 | 1154.2 | -0.0202 [-0.0647, 0.0563] | 3 | 0 | 8 |

Best in-sample confidence escalation: fraction 0.117, gain per state 0.022675; hindsight oracle 0.068956; share 0.329. In-sample and optimistic.

## two_solver_qwen3_0.6b

Reading: **consistent**. States 128; mean gain 0.1275; pooled Spearman -0.1931 [-0.3572, -0.0251]; between questions -0.2801 [-0.4648, -0.0782]; within questions -0.1776 [-0.3724, 0.0278]; monotonicity violations 0.

| Bin | States | Confidence range | Direct acc. | Thinking acc. | Thinking tokens | Mean gain [90% interval] | Rescues | Harms | Both wrong |
|---:|---:|---|---:|---:|---:|---|---:|---:|---:|
| 1 | 26 | -0.2327 to -0.1370 | 0.269 | 0.769 | 1558.3 | 0.4221 [0.1920, 0.6260] | 15 | 2 | 4 |
| 2 | 25 | -0.1369 to -0.1082 | 0.400 | 0.720 | 1241.0 | 0.2579 [0.1057, 0.4273] | 8 | 0 | 7 |
| 3 | 26 | -0.1065 to -0.0855 | 0.769 | 0.885 | 1178.2 | 0.0565 [-0.0470, 0.1654] | 3 | 0 | 3 |
| 4 | 25 | -0.0852 to -0.0685 | 0.720 | 0.800 | 1012.7 | 0.0294 [-0.1607, 0.2219] | 5 | 3 | 2 |
| 5 | 26 | -0.0685 to -0.0242 | 0.923 | 0.846 | 1002.8 | -0.1271 [-0.2982, 0.0253] | 1 | 3 | 1 |

Best in-sample confidence escalation: fraction 0.664, gain per state 0.167306; hindsight oracle 0.233159; share 0.718. In-sample and optimistic.

## two_solver_qwen3_1.7b

Reading: **inconsistent**. States 128; mean gain -0.0367; pooled Spearman 0.3439 [0.1612, 0.4994]; between questions 0.3943 [0.1814, 0.5768]; within questions 0.0759 [-0.1404, 0.2840]; monotonicity violations 2.

| Bin | States | Confidence range | Direct acc. | Thinking acc. | Thinking tokens | Mean gain [90% interval] | Rescues | Harms | Both wrong |
|---:|---:|---|---:|---:|---:|---|---:|---:|---:|
| 1 | 26 | -0.1227 to -0.0499 | 0.692 | 0.731 | 1799.8 | -0.0515 [-0.2219, 0.1376] | 3 | 2 | 5 |
| 2 | 25 | -0.0497 to -0.0408 | 0.720 | 0.760 | 1557.2 | -0.0379 [-0.1611, 0.0947] | 2 | 1 | 5 |
| 3 | 26 | -0.0407 to -0.0322 | 0.808 | 0.885 | 1333.5 | 0.0102 [-0.0655, 0.0954] | 2 | 0 | 3 |
| 4 | 25 | -0.0319 to -0.0249 | 1.000 | 1.000 | 1049.3 | -0.0525 [-0.0596, -0.0460] | 0 | 0 | 0 |
| 5 | 26 | -0.0247 to -0.0042 | 1.000 | 1.000 | 1049.8 | -0.0525 [-0.0577, -0.0467] | 0 | 0 | 0 |

Best in-sample confidence escalation: fraction 0.000, gain per state 0.000000; hindsight oracle 0.051535; share 0.000. In-sample and optimistic.

