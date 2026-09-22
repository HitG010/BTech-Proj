"""Fixed whole-question confirmation tests; no outcome-dependent stopping."""

import numpy as np
from scipy.stats import t

ALPHA = 0.05
PREFERENCE = 0.05
BOOTSTRAP_DRAWS = 10000
SEED = 20260919
SECONDARY = ("gain-ridge", "always-direct", "always-thinking", "DART-SC-3-adapted")


def holm(pvalues):
    values = np.asarray(pvalues, float)
    if (
        values.ndim != 1
        or not len(values)
        or not np.isfinite(values).all()
        or np.any((values < 0) | (values > 1))
    ):
        raise ValueError("Expected finite p-values in [0, 1]")
    order = np.argsort(values, kind="stable")
    adjusted = np.minimum(
        1, np.maximum.accumulate((len(values) - np.arange(len(values))) * values[order])
    )
    result = np.empty_like(values)
    result[order] = adjusted
    return result.tolist()


def paired_test(differences, *, seed=SEED, draws=BOOTSTRAP_DRAWS):
    values = np.asarray(differences, float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Expected at least two finite whole-question differences")
    if type(draws) is not int or draws < 1:
        raise ValueError("Bootstrap draws must be a positive integer")
    n, mean, sd = len(values), float(values.mean()), float(values.std(ddof=1))
    se = float(sd / np.sqrt(n))
    statistic = mean / se if se > 0 else None
    pvalue = float(2 * t.sf(abs(statistic), n - 1)) if se > 0 else float(mean == 0)
    margin = float(t.ppf(1 - ALPHA / 2, n - 1) * se)
    rng, samples = np.random.default_rng(seed), []
    # Bound memory even for thousands of questions and 10,000 replicates.
    for start in range(0, draws, 128):
        ids = rng.integers(0, n, size=(min(128, draws - start), n))
        samples.extend(values[ids].mean(1))
    return {
        "n_questions": n,
        "mean_difference": mean,
        "paired_sd": sd,
        "t_statistic": statistic,
        "zero_variance": se == 0,
        "degrees_of_freedom": n - 1,
        "p_two_sided": pvalue,
        "t_ci95": [mean - margin, mean + margin],
        "bootstrap_ci95": np.quantile(samples, [0.025, 0.975]).tolist(),
        "bootstrap_draws": draws,
        "bootstrap_seed": seed,
    }


def analyze_policies(policies):
    matrices = {name: np.asarray(rows, float) for name, rows in policies.items()}
    shapes = {x.shape for x in matrices.values()}
    if len(shapes) != 1 or any(
        x.ndim != 2 or x.shape[1] != 3 or not np.isfinite(x).all() for x in matrices.values()
    ):
        raise ValueError("All policies need aligned whole-question accuracy/token/time rows")
    utilities = {name: x[:, 0] - PREFERENCE * x[:, 1] / 1000 for name, x in matrices.items()}
    primary = paired_test(utilities["joint"] - utilities["confidence-continuation"])
    primary["comparison"] = "joint minus confidence-continuation"
    primary["positive_superiority"] = (
        primary["mean_difference"] > 0 and primary["p_two_sided"] < ALPHA
    )
    primary["direction"] = (
        ("positive" if primary["mean_difference"] > 0 else "negative")
        if primary["p_two_sided"] < ALPHA
        else "inconclusive"
    )
    secondary = {name: paired_test(utilities["joint"] - utilities[name]) for name in SECONDARY}
    for (name, row), adjusted in zip(
        secondary.items(), holm([r["p_two_sided"] for r in secondary.values()]), strict=True
    ):
        row.update(
            comparison=f"joint minus {name}",
            p_holm=adjusted,
            primary_gate_open=primary["positive_superiority"],
            positive_superiority=bool(
                primary["positive_superiority"] and adjusted < ALPHA and row["mean_difference"] > 0
            ),
        )
    return {
        "primary": primary,
        "secondary": secondary,
        "alpha": ALPHA,
        "preference": PREFERENCE,
        "secondary_rule": "Holm across four predeclared comparisons; confirmatory claims require positive primary rejection",
    }
