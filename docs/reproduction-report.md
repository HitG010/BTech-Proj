# Reproduction from the paper cache

Cache SHA-256 `3da91b57c98612141f2962cc657d6c9e3e26b4b0592d52006a7dcfce92e73757`. Worker processes: 4. Checks: 195; failed: 0; skipped: 0.

**All published values reproduced.**

## Table 1 (repeat panel, λ = .05)

| Rule | Accuracy | Tokens | Utility vs confidence [90%] | Lift (points) |
|---|---:|---:|---|---:|
| Always direct | 89.50% | 221.14 | -0.012 [-0.034, +0.007] | +0.00 |
| Always think | 94.50% | 1610.97 | -0.032 | +0.00 |
| Hindsight oracle (not deployable) | 97.00% | 342.02 | +0.057 | +7.07 |
| Confidence | 92.75% | 628.47 | +0.000 | +1.78 |
| Predeclared learner (combined Ridge) | 89.00% | 757.13 | -0.044 [-0.064, -0.025] | -2.43 |
| Regularized/compressed (CPU family) | 90.75% | 514.22 | -0.014 [-0.026, -0.004] | +0.20 |
| Compact neural objectives | 89.25% | 604.82 | -0.034 [-0.053, -0.017] | -1.63 |
| Released CLM, zero-shot | 94.75% | 1550.53 | -0.026 [-0.059, +0.017] | +0.47 |
| Released CLM, calibrated | 88.50% | 443.71 | -0.033 [-0.054, -0.015] | -1.80 |
| Same encoder, PCA8/Ridge | 89.00% | 330.81 | -0.023 [-0.044, -0.004] | -0.89 |
| CLM/raw learned family | 88.75% | 406.34 | -0.029 [-0.050, -0.011] | -1.42 |
| Token-level learned error score | 88.75% | 570.33 | -0.037 [-0.061, -0.013] | -2.01 |
| Minimum-token threshold | 91.00% | 483.20 | -0.010 [-0.027, +0.005] | +0.56 |
| Token-level gain Ridge | 90.00% | 483.21 | -0.020 [-0.035, -0.007] | -0.44 |
| Two-draft agreement (simulated) | 92.25% | 597.69 | -0.003 [-0.021, +0.012] | +1.40 |

## Table 2 (refit-inclusive intervals)

| Contrast | Point | Fixed actions | With refitting | Fold repartitions |
|---|---:|---|---|---|
| repeat_combined_minus_selected_baseline | -0.016 | [-0.033, -0.001] | [-0.042, +0.021] | [-0.036, -0.005] |
| repeat_combined_minus_confidence | -0.044 | [-0.064, -0.025] | [-0.058, +0.008] | [-0.051, -0.029] |
| repeat_confidence_minus_accept | +0.012 | [-0.007, +0.034] | [-0.027, +0.028] | [+0.003, +0.015] |
| two_solver_qwen3_0.6b_confidence_minus_accept | +0.153 | [+0.086, +0.220] | [+0.068, +0.220] | [+0.131, +0.168] |
| two_solver_qwen3_1.7b_confidence_minus_accept | -0.031 | [-0.056, -0.006] | [-0.051, +0.010] | [-0.037, -0.016] |
