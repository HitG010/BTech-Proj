# Deferral curves, refit uncertainty, and agreement baseline

Post-hoc analysis of cached, reused development data. See `docs/deferral-curves-protocol.md`. Historical decisions were reproduced before analysis: **True**. Worker processes: 4.

Two-solver runtime fields differing from collection: platform. Cached bytes were verified by hash.

## A. Accuracy and cost at λ = .05

### repeat_qwen3_1.7b

| Policy | Accuracy | Tokens/state | Utility | Escalation | Lift over random | Oracle share | Rescues | Harms | Both wrong | Missed rescues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| always_direct | 89.50% | 221.14 | 0.883943 | 0.000 | +0.0000 | +0.000 | 0 | 0 | 0 | 30 |
| always_escalate | 94.50% | 1610.97 | 0.864451 | 1.000 | +0.0000 | -0.283 | 30 | 10 | 12 | 0 |
| oracle | 97.00% | 342.02 | 0.952899 | 0.075 | +0.0707 | +1.000 | 30 | 0 | 0 | 0 |
| accept | 89.50% | 221.14 | 0.883943 | 0.000 | +0.0000 | +0.000 | 0 | 0 | 0 | 30 |
| escalate | 94.50% | 1610.97 | 0.864451 | 1.000 | +0.0000 | -0.283 | 30 | 10 | 12 | 0 |
| confidence | 92.75% | 628.47 | 0.896076 | 0.250 | +0.0178 | +0.176 | 17 | 4 | 4 | 13 |
| question_only | 88.75% | 794.10 | 0.847795 | 0.430 | -0.0281 | -0.524 | 3 | 6 | 1 | 27 |
| solver_only | 89.75% | 621.67 | 0.866417 | 0.280 | -0.0119 | -0.254 | 5 | 4 | 6 | 25 |
| combined | 89.00% | 757.13 | 0.852143 | 0.405 | -0.0243 | -0.461 | 4 | 6 | 5 | 26 |
| selected_baseline | 90.25% | 683.06 | 0.868347 | 0.297 | -0.0091 | -0.226 | 7 | 4 | 2 | 23 |
| training_selected_cpu_family (Table 3, reported) | 90.75% | 514.22 | 0.881789 | | +0.0020 | -0.031 | | | | |
| training_selected_compact_neural_family (Table 3, reported) | 89.25% | 604.82 | 0.862259 | | -0.0163 | -0.314 | | | | |
| released_clm_zero_shot (Table 3, reported) | 94.75% | 1550.53 | 0.869973 | | +0.0047 | -0.203 | | | | |
| released_clm_calibrated (Table 3, reported) | 88.50% | 443.71 | 0.862815 | | -0.0180 | -0.306 | | | | |
| same_encoder_pca8_ridge (Table 3, reported) | 89.00% | 330.81 | 0.873460 | | -0.0089 | -0.152 | | | | |
| training_selected_clm_raw_family (Table 3, reported) | 88.75% | 406.34 | 0.867183 | | -0.0142 | -0.243 | | | | |
| token_learned_error_score (Table 3, reported) | 88.75% | 570.33 | 0.858983 | | -0.0201 | -0.362 | | | | |
| token_min_token_threshold (Table 3, reported) | 91.00% | 483.20 | 0.885840 | | +0.0056 | +0.028 | | | | |
| token_gain_ridge (Table 3, reported) | 90.00% | 483.21 | 0.875839 | | -0.0044 | -0.118 | | | | |

λ sweep (rules refitted at each λ; utility at that λ):

| λ | Confidence acc./tokens | Combined acc./tokens | Oracle acc./tokens | Combined − confidence | Combined − selected baseline |
|---:|---|---|---|---:|---:|
| 0 | 92.50% / 1199.5 | 89.75% / 1055.9 | 97.00% / 342.0 | -0.027500 | -0.040000 |
| 0.01 | 92.00% / 1060.1 | 88.75% / 996.3 | 97.00% / 342.0 | -0.031863 | -0.027497 |
| 0.02 | 92.25% / 783.7 | 88.50% / 928.3 | 97.00% / 342.0 | -0.040392 | -0.018366 |
| 0.03 | 92.25% / 783.7 | 89.25% / 865.9 | 97.00% / 342.0 | -0.032465 | -0.014542 |
| 0.05 | 92.75% / 628.5 | 89.00% / 757.1 | 97.00% / 342.0 | -0.043933 | -0.016204 |
| 0.075 | 91.25% / 347.3 | 89.00% / 667.1 | 97.00% / 342.0 | -0.046482 | -0.039690 |
| 0.1 | 91.25% / 347.3 | 88.25% / 588.8 | 97.00% / 342.0 | -0.054146 | -0.048423 |
| 0.15 | 89.50% / 266.0 | 88.50% / 435.1 | 97.00% / 342.0 | -0.035352 | -0.038223 |
| 0.2 | 89.25% / 246.2 | 88.75% / 368.2 | 97.00% / 342.0 | -0.029406 | -0.036918 |
| 0.3 | 89.25% / 230.2 | 89.25% / 251.5 | 97.00% / 342.0 | -0.006374 | -0.011604 |

### two_solver_qwen3_0.6b

| Policy | Accuracy | Tokens/state | Utility | Escalation | Lift over random | Oracle share | Rescues | Harms | Both wrong | Missed rescues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| always_direct | 61.72% | 209.80 | 0.606697 | 0.000 | +0.0000 | +0.000 | 0 | 0 | 0 | 32 |
| always_escalate | 80.47% | 1409.52 | 0.734211 | 1.000 | +0.0000 | +0.547 | 32 | 8 | 17 | 0 |
| oracle | 86.72% | 546.63 | 0.839856 | 0.250 | +0.1974 | +1.000 | 32 | 0 | 0 | 0 |
| confidence | 81.25% | 1062.52 | 0.759374 | 0.656 | +0.0620 | +0.655 | 28 | 3 | 14 | 4 |

λ sweep (rules refitted at each λ; utility at that λ):

| λ | Confidence acc./tokens | Oracle acc./tokens | Confidence − accept |
|---:|---|---|---:|
| 0 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.195312 |
| 0.01 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.186785 |
| 0.02 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.178258 |
| 0.03 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.169731 |
| 0.05 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.152677 |
| 0.075 | 81.25% / 1062.5 | 86.72% / 546.6 | +0.131359 |
| 0.1 | 81.25% / 1031.0 | 86.72% / 546.6 | +0.113188 |
| 0.15 | 78.12% / 806.9 | 86.72% / 546.6 | +0.074491 |
| 0.2 | 77.34% / 720.2 | 86.72% / 546.6 | +0.054164 |
| 0.3 | 70.31% / 542.1 | 86.72% / 546.6 | -0.013740 |

### two_solver_qwen3_1.7b

| Policy | Accuracy | Tokens/state | Utility | Escalation | Lift over random | Oracle share | Rescues | Harms | Both wrong | Missed rescues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| always_direct | 84.38% | 228.01 | 0.832350 | 0.000 | +0.0000 | +0.000 | 0 | 0 | 0 | 7 |
| always_escalate | 87.50% | 1586.79 | 0.795661 | 1.000 | +0.0000 | -0.712 | 7 | 3 | 13 | 0 |
| oracle | 89.84% | 291.06 | 0.883884 | 0.055 | +0.0532 | +1.000 | 7 | 0 | 0 | 0 |
| confidence | 83.59% | 682.56 | 0.801809 | 0.266 | -0.0183 | -0.593 | 1 | 2 | 8 | 6 |

λ sweep (rules refitted at each λ; utility at that λ):

| λ | Confidence acc./tokens | Oracle acc./tokens | Confidence − accept |
|---:|---|---|---:|
| 0 | 83.59% / 788.9 | 89.84% / 291.1 | -0.007812 |
| 0.01 | 83.59% / 788.9 | 89.84% / 291.1 | -0.013422 |
| 0.02 | 83.59% / 788.9 | 89.84% / 291.1 | -0.019031 |
| 0.03 | 82.81% / 727.4 | 89.84% / 291.1 | -0.030606 |
| 0.05 | 83.59% / 682.6 | 89.84% / 291.1 | -0.030540 |
| 0.075 | 82.81% / 435.4 | 89.84% / 291.1 | -0.031183 |
| 0.1 | 83.59% / 344.2 | 89.84% / 291.1 | -0.019434 |
| 0.15 | 84.38% / 279.4 | 89.84% / 291.1 | -0.007702 |
| 0.2 | 84.38% / 279.4 | 89.84% / 291.1 | -0.010269 |
| 0.3 | 84.38% / 269.3 | 89.84% / 291.1 | -0.012391 |

## B. Refit-inclusive uncertainty

| Endpoint | Point | Fixed-action 90% | Refit-inclusive 90% | Refit mean | Width ratio | Repartition 5–50–95% | Reading |
|---|---:|---|---|---:|---:|---|---|
| repeat_combined_minus_selected_baseline | -0.016204 | [-0.033276, -0.000635] | [-0.042296, +0.020701] | -0.012218 | 1.93 | [-0.036404, -0.021630, -0.004875] | no_longer_excludes_zero |
| repeat_combined_minus_confidence | -0.043933 | [-0.064068, -0.025246] | [-0.057621, +0.007865] | -0.026597 | 1.69 | [-0.050609, -0.041050, -0.029268] | no_longer_excludes_zero |
| repeat_confidence_minus_accept | +0.012133 | [-0.007486, +0.034069] | [-0.026994, +0.027814] | +0.001844 | 1.32 | [+0.002526, +0.009895, +0.015153] | both_include_zero |
| two_solver_qwen3_0.6b_confidence_minus_accept | +0.152677 | [+0.085535, +0.220375] | [+0.068168, +0.219945] | +0.145412 | 1.13 | [+0.130551, +0.147658, +0.167709] | sign_robust |
| two_solver_qwen3_1.7b_confidence_minus_accept | -0.030540 | [-0.056066, -0.006071] | [-0.050563, +0.009868] | -0.018640 | 1.21 | [-0.036918, -0.024999, -0.016126] | no_longer_excludes_zero |

## C. Two-draft agreement baseline

Primary reading (repeat panel): **fail**.

| Panel | Accuracy | Tokens/state | Escalation | Difference vs confidence [90%] | Directions | LOO min | Second-draft cost | Free-draft difference | vs accept |
|---|---:|---:|---:|---|---|---:|---:|---:|---|
| repeat_qwen3_1.7b | 92.25% | 597.69 | 0.085 | -0.003461 [-0.021222, +0.011806] | k4_A_to_B -0.015173, k4_B_to_A +0.008251 | -0.006690 | 0.011057 | +0.007596 | +0.008672 [-0.005264, +0.024367] |
| two_solver_qwen3_0.6b | 78.12% | 997.94 | 0.406 | -0.028021 [-0.079512, +0.017542] | draw_0 -0.062330, draw_1 +0.006288 | -0.037022 | 0.010490 | -0.017531 | +0.124656 [+0.060736, +0.191424] |
| two_solver_qwen3_1.7b | 84.38% | 678.90 | 0.094 | +0.007996 [-0.015234, +0.032537] | draw_0 +0.004168, draw_1 +0.011823 | -0.001389 | 0.011400 | +0.019396 | -0.022545 [-0.030778, -0.015073] |

Secondary full8 agreement: 92.64% at 617.81 tokens; difference vs full8 confidence -0.006118.

