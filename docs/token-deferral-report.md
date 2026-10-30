# Token-level deferral check

Post-hoc, exploratory, reused development data. See `docs/token-deferral-protocol.md`.

Extraction fidelity: **passed**. Recomputed pre-warper mean versus recorded: median absolute difference +0.000139, maximum +0.001055; share within tolerance +1.0000. Post-warper support misses: 4 tokens in 4 drafts.

Primary reading (learned error score): **fail**.

| Rule | Mean utility difference vs confidence [90%] | A→B | B→A | Leave-one-out all positive | Accuracy | Tokens/state |
|---|---|---:|---:|---|---:|---:|
| learned_error_score | -0.037093 [-0.061320, -0.012740] | -0.043491 | -0.030694 | False | 0.8875 | 570.33 |
| min_token_threshold | -0.010236 [-0.027213, +0.005476] | -0.025371 | +0.004898 | False | 0.9100 | 483.20 |
| token_gain_ridge | -0.020237 [-0.035444, -0.007115] | -0.032280 | -0.008193 | False | 0.9000 | 483.21 |
| confidence (comparator) | reference | | | | 0.9275 | 628.47 |

Secondary eight-draw condition, mean difference vs confidence: learned_error_score -0.028534; min_token_threshold -0.014151; token_gain_ridge -0.023358.

| Score (higher = more likely to escalate) | AUROC, incorrect direct | AUROC, positive gain |
|---|---:|---:|
| negative_recorded_confidence | +0.5952 | +0.7050 |
| negative_raw_mean | +0.6202 | +0.7371 |
| negative_min_token | +0.5601 | +0.6415 |
| negative_quantile_0.05 | +0.6244 | +0.7441 |
| negative_quantile_0.1 | +0.6445 | +0.7504 |
| negative_quantile_0.25 | +0.6443 | +0.7613 |
| negative_median | +0.6239 | +0.7010 |

Spearman with log answer length: recorded confidence -0.0267; minimum token -0.3108. Descriptive pooled values without intervals.

