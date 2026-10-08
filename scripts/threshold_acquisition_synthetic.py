"""Frozen, bounded G1 synthetic threshold-acquisition adaptation.

This module imports no project data or historical research modules. Acquisition
gets public direct states and a purchase capability; evaluator arrays are kept
outside that interface. Posterior scores are heuristics, while the final audit
is a finite-population sampling correction. No selected-policy coverage or
algorithm-priority claim is made.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import numbers
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

METHODS = (
    "uniform_coverage",
    "uniform_repeat",
    "confidence_stratified",
    "disagreement",
    "closest_cost_aware",
    "reactive_impact",
    "candidate",
    "candidate_no_repeat",
    "candidate_no_joint_covariance",
)
SETTINGS = (
    "null_no_benefit",
    "threshold_cost_zero",
    "high_noise_repeat",
    "heterogeneous_nonmonotonic",
    "rare_rescue_harms",
    "high_direct_cost",
    "threshold_cost_positive",
    "threshold_cost_negative",
)
BETA = 0.05 / 1000
SPEC = {
    "identity": "threshold-acquisition-synthetic-g1-v1",
    "classification": "empirical_adaptation_no_priority_claim",
    "train_groups": 64,
    "train_repeats": 2,
    "evaluation_groups": 512,
    "evaluation_repeats": 2,
    "direct_cap": 512,
    "thinking_cap": 2562,
    "budgets": [64000, 128000, 256000],
    "aulc_weights": [1 / 6, 1 / 2, 1 / 3],
    "lambda": 0.05,
    "seed_states": 8,
    "audit_cells": 4,
    "strata_quantiles": [0.25, 0.5, 0.75],
    "threshold_quantiles": [i / 8 for i in range(1, 8)],
    "quantile": "stable_order_value_at_ceil_qN_minus_1",
    "action": "strict_confidence_less_than_threshold",
    "ties": "utility_tolerance_1e-12_then_fewer_escalations_then_lower_threshold",
    "exploration": 0.1,
    "plausible_width": 0.03,
    "between_prior": 0.10,
    "within_prior": 0.20,
    "variance_strength": 2,
    "variance_floor": 1e-4,
    "correctness_pseudocounts": [1, 1],
    "cost_prior_cells": 2,
    "cost_prior_length_fraction": 0.5,
    "information_particles": 32,
    "information_length_categories": "high_if_C_gt_thinking_cap_over_2",
    "information_probability_clip": [0.001, 0.999],
    "information_target": "exact_purchased_cells_plus_remaining_count_times_particle_mean",
    "reactive_z": [-2, -1, 0, 1, 2],
    "reactive_weights": [0.05, 0.25, 0.40, 0.25, 0.05],
    "covariance_ablation": "omit_cross_term_only_in_Delta_uncertainty;common_joint_posterior_means",
    "singleton_stop_methods": list(METHODS[3:]),
    "uniform_stop_methods": list(METHODS[:3]),
    "seed_rule": "uniform_8_distinct_states_then_uniform_cell_per_state;sample_frozen_before_reveal",
    "nested_checkpoints": True,
    "methods": list(METHODS),
    "synthetic_seeds": list(range(2026100900, 2026100930)),
    "rng": "numpy_PCG64_SeedSequence([seed,setting_ordinal,stream])",
    "streams": {"training": 0, "evaluation": 1, "common_seed": 2, "acquisition": 3, "particles": 4},
    "common_confidence": {"distribution": "uniform", "low": 0.02, "high": 0.98},
    "common_direct_tokens": 128,
    "thinking_independence": "independent_UY_and_UC_per_draw_conditional_fixed_state",
    "settings": {
        "null_no_benefit": {"pD": [0.45, 0.45], "pT": 0.0, "length": [800, 800], "association": "zero"},
        "threshold_cost_zero": {"pD": [0.25, 0.70], "pT_below_above_half": [0.88, 0.55], "length": [384, 2304], "association": "zero"},
        "high_noise_repeat": {"pD": [0.30, 0.60], "pT_below_above_half": [0.72, 0.42], "length": [256, 2048], "association": "zero"},
        "heterogeneous_nonmonotonic": {"pD": [0.30, 0.60], "pT_quartile": [0.88, 0.45, 0.90, 0.30], "fixed_confidence_cuts": [0.25, 0.50, 0.75], "state_offset": [-0.25, 0.25], "pT_clip": [0.02, 0.98], "length": [256, 2304], "association": "zero"},
        "rare_rescue_harms": {"pD": [0.90, 0.0], "pT_below_above_point_one": [0.98, 0.78], "length": [1024, 1024], "association": "zero"},
        "high_direct_cost": {"pD": [0.25, 0.70], "pT_below_above_half": [0.88, 0.55], "length": [384, 2304], "association": "zero", "direct_tokens": 512},
        "threshold_cost_positive": {"pD": [0.25, 0.70], "pT_below_above_half": [0.88, 0.55], "length": [384, 2304], "association": "positive"},
        "threshold_cost_negative": {"pD": [0.25, 0.70], "pT_below_above_half": [0.88, 0.55], "length": [384, 2304], "association": "negative"},
    },
    "length_rule": "equal_probability_low_high;zero:UC_lt_.5;positive:UY_lt_.5;negative:UY_ge_.5",
    "matched_marginals": "expected_only_not_identical_finite_realizations",
    "primary_settings": ["high_noise_repeat", "threshold_cost_negative"],
    "primary_comparators": ["uniform_coverage", "closest_cost_aware"],
    "primary_mean_difference_min": 0.005,
    "primary_positive_pairs_min": 20,
    "gate": "all_four_setting_comparator_mean_and_positive_pair_checks_and_all_engineering_checks",
    "runtime_seconds": 1200,
    "artifact_bytes_limit": 536870912,
    "invocations": 1,
    "retries": 0,
    "descriptive_interval": "mean_plus_minus_1.6448536269514722_sampleSD_ddof1_over_sqrt30",
    "acquisition_timing": "monotonic_elapsed_around_run_strategy_including_trace_construction;excludes_evaluation_verification_compression;descriptive_not_causal_benchmark",
    "source_files": [
        "scripts/threshold_acquisition_synthetic.py",
        "tests/test_threshold_acquisition_synthetic.py",
        "tests/test_threshold_acquisition_review.py",
        "scripts/review_threshold_acquisition_synthetic.py",
        "docs/g1-synthetic-protocol-2026-10-09.md",
        "docs/g0-threshold-algorithm-2026-10-09.md",
        "docs/g0-prior-art-review-2026-10-09.md",
    ],
}

Cell = tuple[int, int]
Observed = dict[Cell, tuple[int, int]]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_json(path: Path, value: object) -> None:
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def frozen_array(value: object, dtype: object) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True)
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class PublicPool:
    confidence: np.ndarray
    direct_correct: np.ndarray
    direct_tokens: np.ndarray
    repeats: int = 2
    thinking_cap: int = 2562
    state_ids: tuple[str, ...] = ()
    direct_job_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        raw_y, raw_c = np.asarray(self.direct_correct), np.asarray(self.direct_tokens)
        if not np.isin(raw_y, [0, 1]).all():
            raise ValueError("binary direct correctness required")
        if not np.isfinite(raw_c).all() or not np.equal(raw_c, np.floor(raw_c)).all():
            raise ValueError("integer direct tokens required")
        for name, dtype in (("confidence", float), ("direct_correct", int), ("direct_tokens", int)):
            object.__setattr__(self, name, frozen_array(getattr(self, name), dtype))
        n = len(self.confidence)
        if n < 1 or self.confidence.shape != (n,) or not np.isfinite(self.confidence).all():
            raise ValueError("finite one-dimensional confidence required")
        if self.direct_correct.shape != (n,) or not np.isin(self.direct_correct, [0, 1]).all():
            raise ValueError("binary direct correctness required")
        if self.direct_tokens.shape != (n,) or not ((self.direct_tokens >= 1) & (self.direct_tokens <= SPEC["direct_cap"])).all():
            raise ValueError("direct token cap violated")
        if self.repeats != 2 or self.thinking_cap != SPEC["thinking_cap"]:
            raise ValueError("fixed two-draw/cap contract required")
        if not self.state_ids:
            object.__setattr__(self, "state_ids", tuple(f"state-{i}" for i in range(n)))
        if not self.direct_job_ids:
            object.__setattr__(self, "direct_job_ids", tuple(f"direct-{i}" for i in range(n)))
        if (len(self.state_ids) != n or len(self.direct_job_ids) != n
                or len(set(self.state_ids)) != n or len(set(self.direct_job_ids)) != n):
            raise ValueError("unique fixed state and direct-job identities required")

    @property
    def n(self) -> int:
        return len(self.confidence)

    @property
    def baseline(self) -> float:
        return float(np.mean(self.direct_correct - BETA * self.direct_tokens))

    def as_dict(self) -> dict:
        return {"confidence": self.confidence.tolist(), "direct_correct": self.direct_correct.tolist(),
                "direct_tokens": self.direct_tokens.tolist(), "state_ids": list(self.state_ids),
                "direct_job_ids": list(self.direct_job_ids), "repeats": self.repeats,
                "thinking_cap": self.thinking_cap}


@dataclass(frozen=True)
class PolicyGrid:
    thresholds: np.ndarray
    actions: np.ndarray

    def as_dict(self) -> dict:
        return {"thresholds": ["-inf" if x == -np.inf else "inf" if x == np.inf else float(x) for x in self.thresholds],
                "actions": self.actions.astype(int).tolist()}


def quantile_boundaries(confidence: np.ndarray, probabilities: list[float]) -> np.ndarray:
    ordered = np.sort(confidence, kind="stable")
    return np.array([ordered[math.ceil(q * len(ordered)) - 1] for q in probabilities])


def policy_grid(confidence: np.ndarray) -> PolicyGrid:
    c = np.asarray(confidence, dtype=float)
    if c.ndim != 1 or len(c) == 0 or not np.isfinite(c).all():
        raise ValueError("finite confidence required")
    boundaries = [-np.inf, *quantile_boundaries(c, SPEC["threshold_quantiles"]), np.inf]
    unique: dict[bytes, tuple[float, np.ndarray]] = {}
    for boundary in boundaries:
        action = c < boundary
        unique.setdefault(action.tobytes(), (boundary, action))
    rows = sorted(unique.values(), key=lambda row: (int(row[1].sum()), row[0]))
    return PolicyGrid(frozen_array([row[0] for row in rows], float), frozen_array([row[1] for row in rows], bool))


def confidence_strata(confidence: np.ndarray) -> np.ndarray:
    boundaries = quantile_boundaries(confidence, SPEC["strata_quantiles"])
    return np.sum(confidence[:, None] >= boundaries[None, :], axis=1)


def choose_policy(values: np.ndarray, actions: np.ndarray) -> int:
    values = np.asarray(values)
    eligible = np.flatnonzero(values >= np.max(values) - 1e-12)
    counts = np.sum(actions, axis=1)
    return int(min(eligible, key=lambda k: (int(counts[k]), int(k))))


def gain(public: PublicPool, cell: Cell, outcome: tuple[int, int]) -> float:
    return float(outcome[0] - public.direct_correct[cell[0]] - BETA * outcome[1])


def observed_arrays(public: PublicPool, observed: Observed) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = np.zeros(public.n, dtype=int)
    sums = np.zeros(public.n)
    costs = np.zeros(public.n)
    for cell, outcome in observed.items():
        counts[cell[0]] += 1
        sums[cell[0]] += gain(public, cell, outcome)
        costs[cell[0]] += outcome[1]
    return counts, sums, costs


@dataclass(frozen=True)
class Posterior:
    mean: np.ndarray
    variance: np.ndarray
    cost: np.ndarray
    within: np.ndarray
    between: np.ndarray
    within_no_cross: np.ndarray
    between_no_cross: np.ndarray
    variance_no_cross: np.ndarray
    high_given_correctness: np.ndarray
    counts: np.ndarray
    sums: np.ndarray

    def as_dict(self) -> dict:
        return {name: getattr(self, name).tolist() for name in self.__dataclass_fields__}


def build_posterior(public: PublicPool, observed: Observed) -> Posterior:
    """Purchased-only moments. No-cross variants affect uncertainty only."""
    strata = confidence_strata(public.confidence)
    counts, sums, costs = observed_arrays(public, observed)
    mean0 = np.empty(public.n)
    stratum_cost = np.empty(public.n)
    within = np.empty(public.n)
    between = np.empty(public.n)
    within_nc = np.empty(public.n)
    between_nc = np.empty(public.n)
    conditional = np.empty((public.n, 2))
    first: dict[int, float] = {}
    for cell, outcome in observed.items():
        first.setdefault(cell[0], gain(public, cell, outcome))
    for stratum in range(4):
        states = np.flatnonzero(strata == stratum)
        if len(states) == 0:
            continue
        cells = [(cell, out) for cell, out in observed.items() if strata[cell[0]] == stratum]
        py = (1 + sum(out[0] for _, out in cells)) / (2 + len(cells))
        mc = (public.thinking_cap + sum(out[1] for _, out in cells)) / (2 + len(cells))
        mean0[states] = py - public.direct_correct[states] - BETA * mc
        stratum_cost[states] = mc
        for y in (0, 1):
            yc = [out for _, out in cells if out[0] == y]
            conditional[states, y] = (1 + sum(out[1] > public.thinking_cap / 2 for out in yc)) / (2 + len(yc))
        pair_joint, pair_nc = [], []
        for i in states:
            if (int(i), 0) in observed and (int(i), 1) in observed:
                out0, out1 = observed[(int(i), 0)], observed[(int(i), 1)]
                dy, dc = out0[0] - out1[0], out0[1] - out1[1]
                pair_joint.append((dy - BETA * dc) ** 2 / 2)
                pair_nc.append((dy**2 + BETA**2 * dc**2) / 2)
        h = max(1e-4, (2 * 0.20 + sum(pair_joint)) / (2 + len(pair_joint)))
        hn = max(1e-4, (2 * 0.20 + sum(pair_nc)) / (2 + len(pair_nc)))
        first_gains = [first[int(i)] for i in states if int(i) in first]
        weight = max(len(first_gains) - 1, 0)
        sample_variance = float(np.var(first_gains, ddof=1)) if weight else 0.0
        b = max(1e-4, (2 * 0.10 + weight * max(sample_variance - h, 0)) / (2 + weight))
        bn = max(1e-4, (2 * 0.10 + weight * max(sample_variance - hn, 0)) / (2 + weight))
        within[states], between[states] = h, b
        within_nc[states], between_nc[states] = hn, bn
    variance = 1 / (1 / between + counts / within)
    mean = variance * (mean0 / between + sums / within)
    mean = np.clip(mean, -public.direct_correct - BETA * public.thinking_cap, 1 - public.direct_correct)
    cost = (2 * stratum_cost + costs) / (2 + counts)
    variance_nc = 1 / (1 / between_nc + counts / within_nc)
    return Posterior(mean, variance, cost, within, between, within_nc, between_nc,
                     variance_nc, conditional, counts, sums)


def model_values(public: PublicPool, actions: np.ndarray, posterior: Posterior) -> np.ndarray:
    totals = posterior.sums + (public.repeats - posterior.counts) * posterior.mean
    return public.baseline + actions @ totals / (public.n * public.repeats)


def plausible_policies(public: PublicPool, actions: np.ndarray, posterior: Posterior) -> np.ndarray:
    values = model_values(public, actions, posterior)
    return np.flatnonzero(values >= values.max() - SPEC["plausible_width"])


def candidate_score(public: PublicPool, actions: np.ndarray, posterior: Posterior,
                    plausible: np.ndarray, no_cross: bool = False) -> np.ndarray:
    p = actions[plausible].sum(axis=0)
    k = p * (len(plausible) - p)
    h = posterior.within_no_cross if no_cross else posterior.within
    b = posterior.between_no_cross if no_cross else posterior.between
    v = posterior.variance_no_cross if no_cross else posterior.variance
    r = public.repeats - posterior.counts
    vn = 1 / (1 / b + (posterior.counts + 1) / h)
    delta = (r**2 * v + r * h - (r - 1)**2 * vn - (r - 1) * h) / (public.n * public.repeats)**2
    return k * np.maximum(delta, 0) / np.maximum(posterior.cost, 1)


def mutual_information(joint: np.ndarray) -> float:
    """Categorical MI in nats, with zero joint terms omitted."""
    table = np.asarray(joint, dtype=float)
    if table.ndim != 2 or (table < 0).any() or not np.isclose(table.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError("normalized nonnegative joint table required")
    denominator = table.sum(axis=1)[:, None] * table.sum(axis=0)[None, :]
    positive = table > 0
    return max(0.0, float(np.sum(table[positive] * np.log(table[positive] / denominator[positive]))))


def information_score(public: PublicPool, actions: np.ndarray, posterior: Posterior,
                      particle_z: np.ndarray) -> tuple[np.ndarray, dict]:
    if particle_z.shape != (SPEC["information_particles"], public.n):
        raise ValueError("fixed particle dimensions required")
    means = posterior.mean + np.sqrt(posterior.variance) * particle_z
    means = np.clip(means, -public.direct_correct - BETA * public.thinking_cap, 1 - public.direct_correct)
    totals = posterior.sums + (public.repeats - posterior.counts) * means
    values = public.baseline + totals @ actions.T / (public.n * public.repeats)
    choices = np.array([choose_policy(row, actions) for row in values])
    probabilities = np.clip(means + public.direct_correct + BETA * posterior.cost, 0.001, 0.999)
    scores = np.zeros(public.n)
    tables = []
    assignment = np.eye(len(actions))[choices].T / len(choices)
    for i in range(public.n):
        py = probabilities[:, i]
        ph0, ph1 = posterior.high_given_correctness[i]
        categories = np.stack(((1 - py) * (1 - ph0), (1 - py) * ph0,
                               py * (1 - ph1), py * ph1), axis=1)
        joint = assignment @ categories
        scores[i] = mutual_information(joint) / max(posterior.cost[i], 1)
        tables.append(joint.tolist())
    return scores, {"particle_thresholds": choices.tolist(), "joint_tables": tables,
                    "category_order": [[0, 0], [0, 1], [1, 0], [1, 1]]}


def reactive_score(public: PublicPool, actions: np.ndarray, posterior: Posterior) -> np.ndarray:
    old_values = model_values(public, actions, posterior)
    old = choose_policy(old_values, actions)
    scores = np.zeros(public.n)
    old_totals = posterior.sums + (public.repeats - posterior.counts) * posterior.mean
    for i in range(public.n):
        r = public.repeats - posterior.counts[i]
        if r == 0:
            continue
        hypothetical = np.clip(posterior.mean[i] + np.sqrt(posterior.within[i]) * np.array(SPEC["reactive_z"]),
                               -public.direct_correct[i] - BETA * public.thinking_cap, 1 - public.direct_correct[i])
        vn = 1 / (1 / posterior.between[i] + (posterior.counts[i] + 1) / posterior.within[i])
        updated_mean = vn * (posterior.mean[i] / posterior.variance[i] + hypothetical / posterior.within[i])
        updated_mean = np.clip(updated_mean, -public.direct_correct[i] - BETA * public.thinking_cap, 1 - public.direct_correct[i])
        new_total = posterior.sums[i] + hypothetical + (r - 1) * updated_mean
        new_values = old_values[None, :] + (new_total - old_totals[i])[:, None] * actions[:, i] / (public.n * public.repeats)
        changes = [np.mean(actions[choose_policy(row, actions)] != actions[old]) for row in new_values]
        scores[i] = float(np.dot(SPEC["reactive_weights"], changes))
    return scores


def state_probabilities(public: PublicPool, method: str, posterior: Posterior,
                        actions: np.ndarray, plausible: np.ndarray,
                        particle_z: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    eligible = posterior.counts < public.repeats
    if method == "candidate_no_repeat":
        eligible &= posterior.counts == 0
    probabilities, scores = np.zeros(public.n), np.zeros(public.n)
    diagnostics: dict = {}
    if not eligible.any():
        return probabilities, scores, diagnostics
    if method == "uniform_coverage":
        if (eligible & (posterior.counts == 0)).any():
            eligible &= posterior.counts == 0
        probabilities[eligible] = 1 / eligible.sum()
    elif method == "uniform_repeat":
        if (eligible & (posterior.counts == 1)).any():
            eligible &= posterior.counts == 1
        probabilities[eligible] = 1 / eligible.sum()
    elif method == "confidence_stratified":
        strata = confidence_strata(public.confidence)
        nonempty = [s for s in range(4) if (eligible & (strata == s)).any()]
        for s in nonempty:
            states = eligible & (strata == s)
            probabilities[states] = 1 / len(nonempty) / states.sum()
    else:
        if method == "disagreement":
            p = actions[plausible].sum(axis=0)
            scores = (p * (len(plausible) - p)).astype(float)
        elif method == "closest_cost_aware":
            scores, diagnostics = information_score(public, actions, posterior, particle_z)
        elif method == "reactive_impact":
            scores = reactive_score(public, actions, posterior)
        elif method in ("candidate", "candidate_no_repeat", "candidate_no_joint_covariance"):
            scores = candidate_score(public, actions, posterior, plausible, method == "candidate_no_joint_covariance")
        else:
            raise ValueError(f"unknown method: {method}")
        probabilities[eligible] = SPEC["exploration"] / eligible.sum()
        if np.max(scores[eligible]) <= 0:
            probabilities[eligible] = 1 / eligible.sum()
        else:
            best = np.flatnonzero(eligible)[np.argmax(scores[eligible])]
            probabilities[best] += 1 - SPEC["exploration"]
    diagnostics["eligible_states"] = np.flatnonzero(eligible).tolist()
    return probabilities, scores, diagnostics


class Ledger:
    """Actual settled charges plus cap reservations. Reservations precede reveal."""

    def __init__(self, direct_tokens: int, trace: list[dict]):
        self.charged = int(direct_tokens)
        self.reservations: dict[str, int] = {}
        self.trace = trace
        trace.append({"kind": "direct_charge", "tokens": self.charged})

    @property
    def reserved(self) -> int:
        return sum(self.reservations.values())

    def reserve(self, identifier: str, tokens: int, budget: int) -> None:
        if identifier in self.reservations or tokens <= 0:
            raise ValueError("unique positive reservation required")
        if self.charged + self.reserved + tokens > budget:
            raise ValueError("full cap reservation exceeds checkpoint")
        self.reservations[identifier] = int(tokens)
        self.trace.append({"kind": "reserve", "id": identifier, "tokens": int(tokens), "budget": int(budget),
                           "charged": self.charged, "reserved": self.reserved})

    def settle(self, identifier: str, tokens: int) -> None:
        cap = self.reservations[identifier]
        if not 1 <= tokens <= cap:
            raise ValueError("actual tokens violate reserved cap")
        del self.reservations[identifier]
        self.charged += int(tokens)
        self.trace.append({"kind": "settle", "id": identifier, "actual": int(tokens), "refund": cap - int(tokens),
                           "charged": self.charged, "reserved": self.reserved})


class PurchaseInterface:
    """Only capability to hidden thinking cells; no hidden-cost getter exists.

    Python privacy is an interface contract, not a hostile-code security sandbox.
    Executor verification replays every decision from purchased observations.
    """

    def __init__(self, public: PublicPool, reveal: Callable[[Cell], tuple[int, int]], trace: list[dict],
                 guard: Callable[[], None] | None = None):
        self.public = public
        self.__reveal = reveal
        self.__observed: Observed = {}
        self.trace = trace
        self.ledger = Ledger(int(public.direct_tokens.sum()), trace)
        self.reveal_count = 0
        self.__guard = guard

    @property
    def observed(self) -> Observed:
        return dict(self.__observed)

    @property
    def remaining(self) -> list[Cell]:
        return [(i, r) for i in range(self.public.n) for r in range(self.public.repeats) if (i, r) not in self.__observed]

    def purchase(self, cell: Cell, budget: int, phase: str, pre_reserved: bool = False) -> tuple[int, int]:
        if self.__guard is not None:
            self.__guard()
        if cell not in self.remaining:
            raise ValueError("cell already bought or outside fixed state")
        identifier = f"{cell[0]}:{cell[1]}"
        if pre_reserved:
            if self.ledger.reservations.get(identifier) != self.public.thinking_cap:
                raise ValueError("batch must reserve cap before reveal")
        else:
            self.ledger.reserve(identifier, self.public.thinking_cap, budget)
        raw = self.__reveal(cell)
        if (len(raw) != 2 or any(isinstance(x, (bool, np.bool_)) or not isinstance(x, numbers.Integral) for x in raw)):
            raise ValueError("integer synthetic correctness and tokens required")
        outcome = tuple(int(x) for x in raw)
        if outcome[0] not in (0, 1) or not 1 <= outcome[1] <= self.public.thinking_cap:
            raise ValueError("invalid synthetic cell")
        self.reveal_count += 1
        self.trace.append({"kind": "reveal", "cell": list(cell), "id": identifier, "phase": phase,
                           "state_id": self.public.state_ids[cell[0]], "direct_job_id": self.public.direct_job_ids[cell[0]],
                           "correct": outcome[0], "tokens": outcome[1]})
        self.__observed[cell] = outcome
        self.ledger.settle(identifier, outcome[1])
        return outcome


def audit_estimate(public: PublicPool, actions: np.ndarray, observed_before: Observed,
                   remaining: list[Cell], predictions: np.ndarray,
                   audit_outcomes: Observed) -> tuple[np.ndarray, np.ndarray]:
    """Frozen pre-audit difference estimator, with shared design covariance."""
    expected_remaining = {(i, r) for i in range(public.n) for r in range(public.repeats)} - set(observed_before)
    if set(remaining) != expected_remaining or len(set(remaining)) != len(remaining):
        raise ValueError("remaining cells must be exact frozen complement")
    if not set(audit_outcomes).issubset(expected_remaining):
        raise ValueError("audit must use only frozen remaining cells")
    if np.shape(predictions) != (public.n,) or not np.isfinite(predictions).all():
        raise ValueError("finite frozen state predictions required")
    m, length = len(remaining), len(audit_outcomes)
    if m > 0 and length == 0:
        raise ValueError("positive remaining pool requires audit")
    _, sums, _ = observed_arrays(public, observed_before)
    rem_counts = np.bincount([i for i, _ in remaining], minlength=public.n)
    v = 1 / (public.n * public.repeats)
    estimates = public.baseline + actions @ (sums + rem_counts * predictions) * v
    covariance = np.zeros((len(actions), len(actions)))
    if m:
        residuals = np.array([actions[:, cell[0]] * (gain(public, cell, outcome) - predictions[cell[0]]) * v
                              for cell, outcome in audit_outcomes.items()])
        estimates = estimates + (m / length) * residuals.sum(axis=0)
        if length >= 2:
            centered = residuals - residuals.mean(axis=0)
            covariance = m**2 * (1 - length / m) / length * (centered.T @ centered / (length - 1))
        elif length < m:
            covariance[:] = np.nan
    return estimates, covariance


def run_strategy(public: PublicPool, purchase: PurchaseInterface, method: str,
                 rng: np.random.Generator, seed_cells: list[Cell], particle_z: np.ndarray,
                 budgets: tuple[int, ...] = (64000, 128000, 256000)) -> dict:
    if method not in METHODS:
        raise ValueError("fixed method list required")
    if not budgets or any(b <= 0 for b in budgets) or list(budgets) != sorted(set(budgets)):
        raise ValueError("strictly increasing positive checkpoints required")
    if purchase.public is not public or purchase.observed:
        raise ValueError("fresh matched purchase interface required")
    if len({i for i, _ in seed_cells}) != len(seed_cells) or len(set(seed_cells)) != len(seed_cells):
        raise ValueError("common seed must contain distinct fixed states")
    if purchase.ledger.charged + (len(seed_cells) + min(4, public.n * public.repeats - len(seed_cells))) * public.thinking_cap > budgets[0]:
        raise ValueError("common seed plus audit reservation cannot fit")
    grid = policy_grid(public.confidence)
    purchase.trace.append({"kind": "seed_sample", "cells": [list(c) for c in seed_cells],
                           "state_probabilities": [1 / (public.n - k) for k in range(len(seed_cells))],
                           "cell_given_state_probability": 1 / public.repeats})
    for cell in seed_cells:
        purchase.purchase(cell, budgets[0], "seed")
    checkpoints = []
    for budget in budgets:
        stop = "exhausted"
        while purchase.remaining:
            remaining = purchase.remaining
            if len(remaining) <= SPEC["audit_cells"]:
                stop = "remaining_all_audited"
                break
            if purchase.ledger.charged + public.thinking_cap + min(4, len(remaining) - 1) * public.thinking_cap > budget:
                stop = "cap_with_audit_reservation"
                break
            posterior = build_posterior(public, purchase.observed)
            plausible = plausible_policies(public, grid.actions, posterior)
            if len(plausible) == 1 and method not in METHODS[:3]:
                stop = "unique_heuristic_plausible_policy"
                break
            probabilities, scores, diagnostics = state_probabilities(public, method, posterior, grid.actions, plausible, particle_z)
            if not probabilities.any():
                stop = "adaptive_eligible_exhausted"
                break
            state = int(rng.choice(public.n, p=probabilities))
            cells = [c for c in remaining if c[0] == state]
            cell = cells[int(rng.integers(len(cells)))]
            purchase.trace.append({"kind": "adaptive_decision", "budget": int(budget), "method": method,
                                   "observed_cells": [list(c) for c in purchase.observed],
                                   "remaining_cells": [list(c) for c in remaining], "posterior": posterior.as_dict(),
                                   "plausible": plausible.tolist(), "state_probabilities": probabilities.tolist(),
                                   "scores": scores.tolist(), "diagnostics": diagnostics, "chosen_cell": list(cell),
                                   "chosen_state_probability": float(probabilities[state]),
                                   "chosen_cell_given_state_probability": 1 / len(cells),
                                   "chosen_cell_probability": float(probabilities[state] / len(cells)),
                                   "reservation_tokens": public.thinking_cap})
            purchase.purchase(cell, budget, "adaptive")
        before = purchase.observed
        remaining = purchase.remaining
        posterior = build_posterior(public, before)
        length = min(SPEC["audit_cells"], len(remaining))
        indices = rng.choice(len(remaining), size=length, replace=False) if length else []
        sample = [remaining[int(index)] for index in indices]
        purchase.trace.append({"kind": "audit_snapshot", "budget": int(budget), "stop": stop,
                               "observed_cells": [list(c) for c in before], "remaining_cells": [list(c) for c in remaining],
                               "predictions": posterior.mean.tolist(), "sample": [list(c) for c in sample],
                               "inclusion_probability": length / len(remaining) if remaining else 1,
                               "ordered_cell_probabilities": [1 / (len(remaining) - k) for k in range(length)],
                               "batch_reservation": length * public.thinking_cap})
        # Reserve the entire audit before any of its observations. Refunds are
        # retained for later checkpoints, never reused inside this checkpoint.
        for cell in sample:
            purchase.ledger.reserve(f"{cell[0]}:{cell[1]}", public.thinking_cap, budget)
        audited = {cell: purchase.purchase(cell, budget, "audit", pre_reserved=True) for cell in sample}
        estimates, covariance = audit_estimate(public, grid.actions, before, remaining, posterior.mean.copy(), audited)
        selected = choose_policy(estimates, grid.actions)
        counts, _, _ = observed_arrays(public, purchase.observed)
        checkpoint = {"budget": int(budget), "charged_tokens": purchase.ledger.charged,
                      "selected_policy": selected, "utility_estimates": estimates.tolist(),
                      "audit_covariance": [[None if not np.isfinite(x) else float(x) for x in row] for row in covariance],
                      "audit_count": length, "purchased_cells": len(purchase.observed),
                      "distinct_states": int(np.count_nonzero(counts)), "repeat_count": int(np.sum(np.maximum(counts - 1, 0))),
                      "stop": stop, "trace_prefix_events": len(purchase.trace)}
        purchase.trace.append({"kind": "checkpoint", **checkpoint})
        checkpoints.append(checkpoint)
    if purchase.ledger.reserved or purchase.reveal_count != len(purchase.observed):
        raise ValueError("unsettled reservation or access mismatch")
    return {"method": method, "public": public.as_dict(), "grid": grid.as_dict(),
            "seed_cells": [list(c) for c in seed_cells], "checkpoints": checkpoints,
            "trace": purchase.trace, "access_count": purchase.reveal_count}


def make_rng(seed: int, setting_ordinal: int, stream: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, setting_ordinal, stream])))


def common_seed_cells(public: PublicPool, seed: int, ordinal: int) -> list[Cell]:
    rng = make_rng(seed, ordinal, 2)
    states = rng.permutation(public.n)[:SPEC["seed_states"]]
    return [(int(i), int(rng.integers(public.repeats))) for i in states]


def generate_cache(setting: str, seed: int, evaluation: bool = False) -> tuple[PublicPool, np.ndarray, np.ndarray]:
    ordinal = SETTINGS.index(setting)
    rng = make_rng(seed, ordinal, 1 if evaluation else 0)
    n = SPEC["evaluation_groups"] if evaluation else SPEC["train_groups"]
    parameters = SPEC["settings"][setting]
    confidence = rng.uniform(0.02, 0.98, n)
    pd = parameters["pD"][0] + parameters["pD"][1] * confidence
    direct = (rng.random(n) < pd).astype(int)
    if "pT_below_above_half" in parameters:
        pt = np.where(confidence < 0.5, *parameters["pT_below_above_half"])
    elif "pT_below_above_point_one" in parameters:
        pt = np.where(confidence < 0.1, *parameters["pT_below_above_point_one"])
    elif "pT_quartile" in parameters:
        base = np.array(parameters["pT_quartile"])[np.minimum((confidence * 4).astype(int), 3)]
        offsets = np.array(parameters["state_offset"])[rng.integers(2, size=n)]
        pt = np.clip(base + offsets, *parameters["pT_clip"])
    else:
        pt = np.full(n, parameters["pT"])
    uy, uc = rng.random((n, 2)), rng.random((n, 2))
    correct = (uy < pt[:, None]).astype(int)
    association = parameters["association"]
    high = uy < 0.5 if association == "positive" else uy >= 0.5 if association == "negative" else uc < 0.5
    tokens = np.where(high, parameters["length"][1], parameters["length"][0])
    prefix = "evaluation" if evaluation else "training"
    public = PublicPool(confidence, direct, np.full(n, parameters.get("direct_tokens", 128)),
                        state_ids=tuple(f"{prefix}-{i}" for i in range(n)),
                        direct_job_ids=tuple(f"{prefix}-direct-{i}" for i in range(n)))
    return public, frozen_array(correct, int), frozen_array(tokens, int)


def evaluate_policy(public: PublicPool, correct: np.ndarray, tokens: np.ndarray, threshold: float) -> dict:
    action = public.confidence < threshold
    correctness = public.direct_correct[:, None] + action[:, None] * (correct - public.direct_correct[:, None])
    deployment = public.direct_tokens[:, None] + action[:, None] * tokens
    return {"utility": float(np.mean(correctness - BETA * deployment)),
            "accuracy": float(np.mean(correctness)), "deployment_tokens": float(np.mean(deployment)),
            "escalation_fraction": float(np.mean(action)), "direct_accuracy": float(np.mean(public.direct_correct)),
            "thinking_accuracy": float(np.mean(correct)), "groups": public.n, "draws_per_group": public.repeats}


def aulc(utilities: list[float]) -> float:
    if len(utilities) != 3:
        raise ValueError("three fixed checkpoints required")
    return float(np.dot(SPEC["aulc_weights"], utilities))


def cache_values(public: PublicPool, correct: np.ndarray, tokens: np.ndarray, actions: np.ndarray) -> np.ndarray:
    gains = correct - public.direct_correct[:, None] - BETA * tokens
    return public.baseline + actions @ gains.sum(axis=1) / (public.n * public.repeats)


def run_seed(setting: str, seed: int, guard: Callable[[], None] | None = None,
             progress: Callable[[dict], None] | None = None) -> dict:
    train, correct, tokens = generate_cache(setting, seed)
    evaluation, eval_correct, eval_tokens = generate_cache(setting, seed, evaluation=True)
    ordinal = SETTINGS.index(setting)
    seed_cells = common_seed_cells(train, seed, ordinal)
    particles = make_rng(seed, ordinal, 4).standard_normal((SPEC["information_particles"], train.n))
    trajectories = []
    for method in METHODS:
        if guard is not None:
            guard()
        trace: list[dict] = []
        if progress is not None:
            progress({"setting": setting, "seed": seed, "completed_trajectories": trajectories,
                      "active_method": method, "active_public": train.as_dict(), "active_trace": trace})
        interface = PurchaseInterface(train, lambda cell: (int(correct[cell]), int(tokens[cell])), trace, guard)
        acquisition_started = time.perf_counter()
        trajectory = run_strategy(train, interface, method, make_rng(seed, ordinal, 3), seed_cells, particles)
        trajectory["acquisition_elapsed_seconds"] = time.perf_counter() - acquisition_started
        grid = policy_grid(train.confidence)
        truth = cache_values(train, correct, tokens, grid.actions)
        for checkpoint in trajectory["checkpoints"]:
            threshold = grid.thresholds[checkpoint["selected_policy"]]
            checkpoint["evaluation"] = evaluate_policy(evaluation, eval_correct, eval_tokens, threshold)
            checkpoint["fixed_policy_cache_errors"] = (np.array(checkpoint["utility_estimates"]) - truth).tolist()
        trajectory["normalized_aulc"] = aulc([cp["evaluation"]["utility"] for cp in trajectory["checkpoints"]])
        trajectories.append(trajectory)
    return {"setting": setting, "seed": seed, "trajectories": trajectories,
            "particle_z": particles.tolist(), "training_cache_hash": digest({"public": train.as_dict(), "correct": correct.tolist(), "tokens": tokens.tolist()}),
            "evaluation_cache_hash": digest({"public": evaluation.as_dict(), "correct": eval_correct.tolist(), "tokens": eval_tokens.tolist()}),
            "physical_training_cache_tokens": int(train.direct_tokens.sum() + tokens.sum()),
            "physical_evaluation_cache_tokens": int(evaluation.direct_tokens.sum() + eval_tokens.sum())}


def _close(actual: object, expected: object, context: str) -> None:
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.allclose(a, b, atol=1e-12, rtol=1e-12, equal_nan=True):
        raise ValueError(f"verification mismatch: {context}")


def public_from_dict(value: dict) -> PublicPool:
    return PublicPool(value["confidence"], value["direct_correct"], value["direct_tokens"],
                      value["repeats"], value["thinking_cap"], tuple(value["state_ids"]), tuple(value["direct_job_ids"]))


def validate_trajectory(trajectory: dict, setting: str, seed: int, particle_z: np.ndarray) -> dict:
    """Read-only trace replay from public values and already revealed cells.

    This is an engineering self-check, separate from independent reviewer tests.
    It verifies the actual random choices, predictions and estimates, rather
    than inferring leakage freedom merely from the declared class interface.
    """
    public = public_from_dict(trajectory["public"])
    method = trajectory["method"]
    if trajectory["seed_cells"] != [list(cell) for cell in common_seed_cells(public, seed, SETTINGS.index(setting))]:
        raise ValueError("question-only common seed randomization changed")
    grid = policy_grid(public.confidence)
    if grid.as_dict() != trajectory["grid"]:
        raise ValueError("training-only threshold grid changed")
    rng = make_rng(seed, SETTINGS.index(setting), 3)
    observed: Observed = {}
    charged = int(public.direct_tokens.sum())
    reserved: dict[str, int] = {}
    pending: list[Cell] = []
    checkpoint_index = 0
    snapshot: tuple[Observed, list[Cell], np.ndarray, list[Cell]] | None = None
    reveals = 0
    for event in trajectory["trace"]:
        kind = event["kind"]
        remaining = [(i, r) for i in range(public.n) for r in range(public.repeats) if (i, r) not in observed]
        if kind == "direct_charge":
            if event["tokens"] != charged or observed:
                raise ValueError("direct charge mismatch")
        elif kind == "seed_sample":
            pending = [tuple(cell) for cell in event["cells"]]
            if [list(cell) for cell in pending] != trajectory["seed_cells"]:
                raise ValueError("common seed mismatch")
            _close(event["state_probabilities"], [1 / (public.n - k) for k in range(len(pending))], "seed probabilities")
            _close(event["cell_given_state_probability"], 1 / public.repeats, "seed cell probability")
        elif kind == "adaptive_decision":
            if pending or reserved:
                raise ValueError("adaptation inside unfinished purchase batch")
            if event["observed_cells"] != [list(c) for c in observed] or event["remaining_cells"] != [list(c) for c in remaining]:
                raise ValueError("adaptive history or cell identity mismatch")
            posterior = build_posterior(public, observed)
            plausible = plausible_policies(public, grid.actions, posterior)
            for name in posterior.__dataclass_fields__:
                _close(event["posterior"][name], getattr(posterior, name), f"purchased-only {name}")
            probabilities, scores, diagnostics = state_probabilities(public, method, posterior, grid.actions, plausible, particle_z)
            _close(event["state_probabilities"], probabilities, "state probabilities")
            _close(event["scores"], scores, "purchase scores")
            if event["plausible"] != plausible.tolist() or event["diagnostics"] != diagnostics:
                raise ValueError("score diagnostics mismatch")
            chosen_state = int(rng.choice(public.n, p=probabilities))
            choices = [cell for cell in remaining if cell[0] == chosen_state]
            chosen = choices[int(rng.integers(len(choices)))]
            if list(chosen) != event["chosen_cell"]:
                raise ValueError("random purchase choice mismatch")
            _close(event["chosen_state_probability"], probabilities[chosen_state], "chosen state probability")
            _close(event["chosen_cell_given_state_probability"], 1 / len(choices), "chosen conditional cell probability")
            _close(event["chosen_cell_probability"], probabilities[chosen_state] / len(choices), "chosen cell probability")
            if charged + public.thinking_cap + min(4, len(remaining) - 1) * public.thinking_cap > event["budget"]:
                raise ValueError("adaptive purchase spent audit reserve")
            pending = [chosen]
        elif kind == "audit_snapshot":
            if pending or reserved:
                raise ValueError("audit before previous purchases settled")
            posterior = build_posterior(public, observed)
            if event["observed_cells"] != [list(c) for c in observed] or event["remaining_cells"] != [list(c) for c in remaining]:
                raise ValueError("audit snapshot changed remaining population")
            _close(event["predictions"], posterior.mean, "frozen pre-audit predictions")
            length = min(4, len(remaining))
            indices = rng.choice(len(remaining), size=length, replace=False) if length else []
            sample = [remaining[int(index)] for index in indices]
            if event["sample"] != [list(c) for c in sample]:
                raise ValueError("audit randomization mismatch")
            _close(event["inclusion_probability"], length / len(remaining) if remaining else 1, "audit inclusion probability")
            _close(event["ordered_cell_probabilities"], [1 / (len(remaining) - k) for k in range(length)], "ordered audit probabilities")
            if event["batch_reservation"] != length * public.thinking_cap:
                raise ValueError("audit reservation mismatch")
            snapshot = (dict(observed), list(remaining), posterior.mean.copy(), sample)
            pending = list(sample)
        elif kind == "reserve":
            if event["id"] in reserved or event["tokens"] != public.thinking_cap:
                raise ValueError("invalid cap reservation")
            if event["id"] not in {f"{cell[0]}:{cell[1]}" for cell in pending}:
                raise ValueError("reservation outside prior frozen selection")
            reserved[event["id"]] = event["tokens"]
            if charged + sum(reserved.values()) > event["budget"]:
                raise ValueError("reservation budget violation")
            if event["charged"] != charged or event["reserved"] != sum(reserved.values()):
                raise ValueError("reservation ledger mismatch")
        elif kind == "reveal":
            cell = tuple(event["cell"])
            if not pending or cell != pending[0] or cell in observed or event["id"] not in reserved:
                raise ValueError("hidden outcome exposed before selected cap reservation")
            if event["phase"] == "audit" and snapshot is not None:
                expected_reserved = {f"{i}:{r}" for i, r in pending}
                if set(reserved) != expected_reserved:
                    raise ValueError("audit batch not fully reserved before first reveal")
            if event["state_id"] != public.state_ids[cell[0]] or event["direct_job_id"] != public.direct_job_ids[cell[0]]:
                raise ValueError("repeat changed its fixed direct state")
            observed[cell] = (event["correct"], event["tokens"])
            pending.pop(0)
            reveals += 1
        elif kind == "settle":
            cell = tuple(int(x) for x in event["id"].split(":"))
            if cell not in observed or event["id"] not in reserved:
                raise ValueError("settlement without reserved purchased observation")
            cap = reserved.pop(event["id"])
            actual = observed[cell][1]
            if event["actual"] != actual or not 1 <= actual <= cap or event["refund"] != cap - actual:
                raise ValueError("settlement arithmetic mismatch")
            charged += actual
            if event["charged"] != charged or event["reserved"] != sum(reserved.values()):
                raise ValueError("settlement ledger mismatch")
        elif kind == "checkpoint":
            if snapshot is None or reserved or pending:
                raise ValueError("incomplete checkpoint audit")
            before, rem, predictions, sample = snapshot
            audited = {cell: observed[cell] for cell in sample}
            estimates, covariance = audit_estimate(public, grid.actions, before, rem, predictions, audited)
            _close(event["utility_estimates"], estimates, "audit estimate")
            event_covariance = [[np.nan if x is None else x for x in row] for row in event["audit_covariance"]]
            _close(event_covariance, covariance, "audit covariance")
            counts, _, _ = observed_arrays(public, observed)
            if (event["selected_policy"] != choose_policy(estimates, grid.actions)
                    or event["charged_tokens"] != charged or charged > event["budget"]
                    or event["purchased_cells"] != len(observed)
                    or event["distinct_states"] != int(np.count_nonzero(counts))
                    or event["repeat_count"] != int(np.sum(np.maximum(counts - 1, 0)))
                    or event["audit_count"] != len(sample)):
                raise ValueError("checkpoint arithmetic mismatch")
            cp = trajectory["checkpoints"][checkpoint_index]
            for key in event:
                if key != "kind" and cp[key] != event[key]:
                    raise ValueError("immutable checkpoint differs from trace")
            checkpoint_index += 1
        else:
            raise ValueError(f"unknown trace event: {kind}")
    if reserved or pending or checkpoint_index != 3 or reveals != trajectory["access_count"]:
        raise ValueError("unfinished trace or wrong hidden-access count")
    return {"purchases": reveals, "checkpoints": checkpoint_index, "charged_tokens": charged}


def _descriptive(values: list[float]) -> dict:
    array = np.array(values, dtype=float)
    mean = float(array.mean())
    sd = float(array.std(ddof=1))
    margin = 1.6448536269514722 * sd / np.sqrt(len(array))
    return {"mean": mean, "sample_sd": sd, "approximate_90_percent_simulation_interval": [mean - margin, mean + margin],
            "positive_pairs": int(np.count_nonzero(array > 0)), "seeds": len(array)}


def summarize_acquisition_timing(seed_results: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for result in seed_results:
        for trajectory in result["trajectories"]:
            elapsed = trajectory["acquisition_elapsed_seconds"]
            if not np.isfinite(elapsed) or elapsed < 0:
                raise ValueError("nonnegative finite acquisition elapsed time required")
            grouped.setdefault((result["setting"], trajectory["method"]), []).append(elapsed)
    return [{"setting": setting, "method": method, "mean_acquisition_elapsed_seconds": float(np.mean(values)),
             "minimum_acquisition_elapsed_seconds": float(np.min(values)),
             "maximum_acquisition_elapsed_seconds": float(np.max(values)), "trajectories": len(values),
             "interpretation": SPEC["acquisition_timing"]}
            for (setting, method), values in sorted(grouped.items())]


def summarize(seed_results: list[dict], engineering: dict) -> dict:
    expected = {(setting, seed) for setting in SETTINGS for seed in SPEC["synthetic_seeds"]}
    identities = [(result["setting"], result["seed"]) for result in seed_results]
    if set(identities) != expected or len(identities) != len(expected):
        raise ValueError("full 8 by 30 endpoint required")
    rows, learning_curves, values = [], [], {}
    for result in seed_results:
        if [t["method"] for t in result["trajectories"]] != list(METHODS):
            raise ValueError("full method endpoint required")
        for trajectory in result["trajectories"]:
            key = (result["setting"], trajectory["method"])
            values.setdefault(key, []).append((result["seed"], trajectory["normalized_aulc"]))
            for checkpoint in trajectory["checkpoints"]:
                rows.append({"setting": result["setting"], "seed": result["seed"], "method": trajectory["method"],
                             "normalized_aulc": trajectory["normalized_aulc"],
                             "selected_threshold": trajectory["grid"]["thresholds"][checkpoint["selected_policy"]], **checkpoint})
    method_summaries = []
    contrasts = []
    for setting in SETTINGS:
        for method in METHODS:
            ordered = sorted(values[(setting, method)])
            method_summaries.append({"setting": setting, "method": method, **_descriptive([x[1] for x in ordered])})
            for budget in SPEC["budgets"]:
                selected_rows = [r for r in rows if r["setting"] == setting and r["method"] == method and r["budget"] == budget]
                learning_curves.append({"setting": setting, "method": method, "budget": budget,
                                        **_descriptive([r["evaluation"]["utility"] for r in selected_rows]),
                                        "mean_charged_tokens": float(np.mean([r["charged_tokens"] for r in selected_rows]))})
        candidate = dict(values[(setting, "candidate")])
        for control in METHODS:
            if control == "candidate":
                continue
            comparator = dict(values[(setting, control)])
            differences = [candidate[seed] - comparator[seed] for seed in SPEC["synthetic_seeds"]]
            contrast = {"setting": setting, "candidate": "candidate", "comparator": control,
                        "paired_differences": differences, **_descriptive(differences)}
            contrast["primary"] = setting in SPEC["primary_settings"] and control in SPEC["primary_comparators"]
            contrast["mean_screen"] = contrast["mean"] >= SPEC["primary_mean_difference_min"]
            contrast["positive_pair_screen"] = contrast["positive_pairs"] >= SPEC["primary_positive_pairs_min"]
            contrasts.append(contrast)
    primary = [c for c in contrasts if c["primary"]]
    gate = engineering["pass"] and len(primary) == 4 and all(c["mean_screen"] and c["positive_pair_screen"] for c in primary)
    return {"spec_sha256": digest(SPEC), "classification": SPEC["classification"], "gate_pass": gate,
            "gate_interpretation": "engineering_and_synthetic_screen_only;no_real_data_or_novelty_claim",
            "endpoint": {"settings": 8, "paired_seeds_per_setting": 30, "methods_and_ablations": 9, "checkpoints": 3},
            "engineering": engineering, "rows": rows, "method_aulc": method_summaries, "learning_curves": learning_curves,
            "acquisition_overhead": summarize_acquisition_timing(seed_results),
            "candidate_contrasts": contrasts,
            "physical_training_cache_tokens": sum(r["physical_training_cache_tokens"] for r in seed_results),
            "physical_evaluation_cache_tokens": sum(r["physical_evaluation_cache_tokens"] for r in seed_results),
            "physical_cache_cost_interpretation": "synthetic_generated_cache_including_unpurchased_cells;not_model_compute",
            "uncertainty": "approximate_descriptive_normal_Monte_Carlo_intervals;not_population_or_selected_policy_coverage"}


def engineering_checks() -> dict:
    """Small exact enumeration, not a Monte Carlo feasibility experiment."""
    public = PublicPool([0.2, 0.8], [0, 1], [128, 128])
    actions = policy_grid(public.confidence).actions
    cells = list(itertools.product(range(2), range(2)))
    outcomes = {(0, 0): (1, 2200), (0, 1): (0, 300), (1, 0): (1, 400), (1, 1): (0, 2100)}
    correct = np.array([[1, 0], [1, 0]])
    tokens = np.array([[2200, 300], [400, 2100]])
    truth = cache_values(public, correct, tokens, actions)
    # Enumerate all pre-audit subsets, including unequal repeat histories and
    # a frozen history selected by a length-sensitive adaptive stop.
    cases = 0
    maximum_bias = 0.0
    for size in range(5):
        for observed_cells in itertools.combinations(cells, size):
            observed = {cell: outcomes[cell] for cell in observed_cells}
            remaining = [cell for cell in cells if cell not in observed]
            predictions = np.array([0.17, -0.41])
            length = min(2, len(remaining))
            estimates = []
            for sample in itertools.combinations(remaining, length):
                estimate, _ = audit_estimate(public, actions, observed, remaining, predictions,
                                              {cell: outcomes[cell] for cell in sample})
                estimates.append(estimate)
            bias = float(np.max(np.abs(np.mean(estimates, axis=0) - truth)))
            maximum_bias = max(maximum_bias, bias)
            cases += 1
    if maximum_bias > 1e-12:
        raise ValueError("finite audit exact enumeration failed")
    return {"pass": True, "exact_audit_histories": cases, "maximum_enumerated_bias": maximum_bias,
            "trace_replay": "required_for_every_actual_trajectory",
            "independent_review": "required_prelaunch_and_separate_from_these_self_checks"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_identity() -> dict:
    return {"python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
            "numpy": np.__version__, "platform": platform.platform(), "machine": platform.machine()}


def source_pins(root: Path, revision: str, check_committed: bool = True) -> dict:
    pins = {}
    for relative in SPEC["source_files"]:
        path = root / relative
        contents = path.read_bytes()
        if check_committed:
            committed = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=root,
                                       check=True, capture_output=True).stdout
            if committed != contents:
                raise ValueError(f"source is not identical to frozen commit: {relative}")
        pins[relative] = hashlib.sha256(contents).hexdigest()
    return pins


def prepare(output: Path, source_commit: str) -> dict:
    root = repository_root()
    revision = subprocess.run(["git", "rev-parse", "--verify", f"{source_commit}^{{commit}}"],
                              cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    pins = source_pins(root, revision)
    plan = {"schema": "threshold-acquisition-g1-preparation-v1", "spec": SPEC, "spec_sha256": digest(SPEC),
            "source_revision": revision, "source_sha256": pins, "runtime": runtime_identity(),
            "output": str(output.resolve()), "created_unix_seconds": time.time(),
            "data_boundary": "generated_synthetic_only;no_existing_artifacts_models_network_references"}
    output.mkdir(parents=True, exist_ok=False)
    immutable_json(output / "plan.json", plan)
    return {"status": "prepared", "plan_sha256": file_digest(output / "plan.json"), "output": str(output.resolve())}


def validate_plan(output: Path) -> dict:
    plan = json.loads((output / "plan.json").read_text())
    if plan["spec"] != SPEC or plan["spec_sha256"] != digest(SPEC):
        raise ValueError("frozen specification changed")
    if plan["output"] != str(output.resolve()):
        raise ValueError("prepared output identity changed")
    if plan["runtime"] != runtime_identity():
        raise ValueError("runtime identity changed")
    if plan["source_sha256"] != source_pins(repository_root(), plan["source_revision"]):
        raise ValueError("frozen source pins changed")
    return plan


def compressed_json(path: Path, value: object, byte_limit: int) -> int:
    payload = canonical_bytes(value)
    compressed = gzip.compress(payload, compresslevel=6, mtime=0)
    if len(compressed) > byte_limit:
        raise ValueError("artifact byte limit would be exceeded")
    with path.open("xb") as handle:
        handle.write(compressed)
        handle.flush()
        os.fsync(handle.fileno())
    return len(compressed)


def artifact_bytes(output: Path) -> int:
    return sum(path.stat().st_size for path in output.rglob("*") if path.is_file())


def report_markdown(summary: dict) -> str:
    lines = ["# G1 synthetic threshold-acquisition results", "",
             f"Synthetic screen: **{'pass' if summary['gate_pass'] else 'fail'}**.", "",
             "This is a bounded empirical adaptation study using generated data. It establishes no real-data advantage or method priority.", "",
             "| Mechanism setting | Comparator | Mean paired normalized AULC difference | Positive pairs | Screen |",
             "|---|---|---:|---:|---|"]
    for contrast in summary["candidate_contrasts"]:
        if contrast["primary"]:
            passed = contrast["mean_screen"] and contrast["positive_pair_screen"]
            lines.append(f"| {contrast['setting']} | {contrast['comparator']} | {contrast['mean']:+.6f} | {contrast['positive_pairs']}/30 | {'pass' if passed else 'fail'} |")
    lines.extend(["", "Each required contrast needs mean ≥+.005 and ≥20 positive paired seeds. All engineering checks must pass.", "",
                  "Approximate 90% intervals describe simulation variation only. The audit is unbiased for each fixed finite-cache threshold; selection of its maximum has no coverage guarantee.", "",
                  "All eight settings, nine methods and three nested checkpoints are in summary.json. Full immutable purchase traces are in traces/*.json.gz.", "",
                  "Revealed acquisition expenditure, physical synthetic cache cost and deployment token cost are separate. Synthetic tokens are not measured model compute.", "",
                  "Passing requires a separate reviewed real-data protocol before G2. Failure closes this recipe without expanding the grid.", ""])
    return "\n".join(lines)


def execute(output: Path, review_path: Path) -> dict:
    plan = validate_plan(output)
    review = json.loads(review_path.read_text())
    plan_hash = file_digest(output / "plan.json")
    if (review.get("status") != "pass" or review.get("plan_sha256") != plan_hash
            or review.get("engineering_checks_passed") is not True or review.get("unresolved_blockers") != []):
        raise ValueError("independent actual-input prelaunch review is required")
    if review_path.resolve().parent != output.resolve():
        raise ValueError("prelaunch review must be preserved inside prepared output")
    started_wall, started_monotonic = time.time(), time.monotonic()
    invocation = {"plan_sha256": plan_hash, "source_revision": plan["source_revision"],
                  "prelaunch_review_sha256": file_digest(review_path), "prelaunch_review_file": review_path.name,
                  "started_unix_seconds": started_wall, "runtime_seconds": SPEC["runtime_seconds"],
                  "allowed_invocations": 1, "retries": 0}
    # Exclusive creation consumes the one invocation even if the process fails.
    immutable_json(output / "invocation.json", invocation)
    results, inventory = [], {}
    active: dict = {}

    def guard() -> None:
        if max(time.time() - started_wall, time.monotonic() - started_monotonic) >= SPEC["runtime_seconds"]:
            raise RuntimeError("single-invocation 1200-second runtime limit")

    def progress(value: dict) -> None:
        active.clear()
        active.update(value)

    status = "failed"
    try:
        engineering = engineering_checks()
        traces = output / "traces"
        traces.mkdir(exist_ok=False)
        checks = {"purchases": 0, "checkpoints": 0, "trajectories": 0}
        for setting in SETTINGS:
            for seed in SPEC["synthetic_seeds"]:
                guard()
                result = run_seed(setting, seed, guard, progress)
                for trajectory in result["trajectories"]:
                    guard()
                    validated = validate_trajectory(trajectory, setting, seed, np.array(result["particle_z"]))
                    checks["purchases"] += validated["purchases"]
                    checks["checkpoints"] += validated["checkpoints"]
                    checks["trajectories"] += 1
                path = traces / f"{setting}-{seed}.json.gz"
                compressed_json(path, result, SPEC["artifact_bytes_limit"] - artifact_bytes(output))
                inventory[str(path.relative_to(output))] = file_digest(path)
                # The summary needs metrics, not retained full traces in RAM.
                compact = {k: v for k, v in result.items() if k != "particle_z"}
                compact["trajectories"] = [{k: v for k, v in t.items() if k not in ("trace", "public")} for t in result["trajectories"]]
                results.append(compact)
                active.clear()
        guard()
        engineering["actual_trace_checks"] = checks
        summary = summarize(results, engineering)
        immutable_json(output / "summary.json", summary)
        with (output / "report.md").open("x") as handle:
            handle.write(report_markdown(summary))
        inventory["summary.json"] = file_digest(output / "summary.json")
        inventory["report.md"] = file_digest(output / "report.md")
        if artifact_bytes(output) > SPEC["artifact_bytes_limit"]:
            raise RuntimeError("artifact byte limit")
        guard()
        validate_plan(output)
        status = "complete_pass" if summary["gate_pass"] else "complete_gate_failures"
        finish = {"status": status, "plan_sha256": plan_hash, "inventory_sha256": inventory,
                  "completed_seed_settings": len(results), "elapsed_wall_seconds": time.time() - started_wall,
                  "elapsed_monotonic_seconds": time.monotonic() - started_monotonic,
                  "artifact_bytes_before_finish": artifact_bytes(output), "retries": 0,
                  "gate_pass": summary["gate_pass"]}
        immutable_json(output / "finish.json", finish)
        return finish
    except Exception as error:
        if active:
            try:
                compressed_json(output / "failed-current-trace.json.gz", active,
                                max(0, SPEC["artifact_bytes_limit"] - artifact_bytes(output)))
                inventory["failed-current-trace.json.gz"] = file_digest(output / "failed-current-trace.json.gz")
            except (OSError, ValueError):
                pass
        failure = {"status": status, "plan_sha256": plan_hash, "inventory_sha256": inventory,
                   "completed_seed_settings": len(results), "elapsed_wall_seconds": time.time() - started_wall,
                   "elapsed_monotonic_seconds": time.monotonic() - started_monotonic,
                   "error_type": type(error).__name__, "error": str(error), "retries": 0,
                   "instruction": "preserve_failed_run;no_retry_or_grid_expansion"}
        immutable_json(output / "finish.json", failure)
        raise


def verify(output: Path) -> dict:
    """Verify immutable completed outputs; never restart an acquisition run."""
    validate_plan(output)
    plan_hash = file_digest(output / "plan.json")
    if not (output / "invocation.json").exists():
        return {"status": "prepared_verified", "plan_sha256": plan_hash}
    invocation = json.loads((output / "invocation.json").read_text())
    if invocation["plan_sha256"] != plan_hash:
        raise ValueError("invocation plan changed")
    review = output / invocation["prelaunch_review_file"]
    if file_digest(review) != invocation["prelaunch_review_sha256"]:
        raise ValueError("prelaunch review changed")
    finish = json.loads((output / "finish.json").read_text())
    if finish["plan_sha256"] != plan_hash:
        raise ValueError("finish plan changed")
    for relative, expected in finish["inventory_sha256"].items():
        if file_digest(output / relative) != expected:
            raise ValueError(f"immutable output changed: {relative}")
    if finish["status"] == "failed":
        return {"status": "failed_run_preserved", "completed_seed_settings": finish["completed_seed_settings"]}
    results = []
    checked = {"purchases": 0, "checkpoints": 0, "trajectories": 0}
    for setting in SETTINGS:
        for seed in SPEC["synthetic_seeds"]:
            path = output / "traces" / f"{setting}-{seed}.json.gz"
            result = json.loads(gzip.decompress(path.read_bytes()))
            train, correct, tokens = generate_cache(setting, seed)
            evaluation, eval_correct, eval_tokens = generate_cache(setting, seed, evaluation=True)
            if result["training_cache_hash"] != digest({"public": train.as_dict(), "correct": correct.tolist(), "tokens": tokens.tolist()}):
                raise ValueError("synthetic training identity mismatch")
            if result["evaluation_cache_hash"] != digest({"public": evaluation.as_dict(), "correct": eval_correct.tolist(), "tokens": eval_tokens.tolist()}):
                raise ValueError("independent evaluation identity mismatch")
            grid = policy_grid(train.confidence)
            truth = cache_values(train, correct, tokens, grid.actions)
            expected_particles = make_rng(seed, SETTINGS.index(setting), 4).standard_normal((32, train.n))
            _close(result["particle_z"], expected_particles, "frozen particle randomization")
            for trajectory in result["trajectories"]:
                check = validate_trajectory(trajectory, setting, seed, np.array(result["particle_z"]))
                checked["purchases"] += check["purchases"]
                checked["checkpoints"] += check["checkpoints"]
                checked["trajectories"] += 1
                if trajectory["public"] != train.as_dict():
                    raise ValueError("public training state mismatch")
                for event in trajectory["trace"]:
                    if event["kind"] == "reveal":
                        cell = tuple(event["cell"])
                        if event["correct"] != int(correct[cell]) or event["tokens"] != int(tokens[cell]):
                            raise ValueError("purchased synthetic outcome identity mismatch")
                for checkpoint in trajectory["checkpoints"]:
                    ev = evaluate_policy(evaluation, eval_correct, eval_tokens, grid.thresholds[checkpoint["selected_policy"]])
                    if ev != checkpoint["evaluation"]:
                        raise ValueError("held-out evaluation arithmetic mismatch")
                    _close(checkpoint["fixed_policy_cache_errors"], np.array(checkpoint["utility_estimates"]) - truth, "fixed-policy cache error")
                _close(trajectory["normalized_aulc"], aulc([cp["evaluation"]["utility"] for cp in trajectory["checkpoints"]]), "normalized AULC")
            compact = {k: v for k, v in result.items() if k != "particle_z"}
            compact["trajectories"] = [{k: v for k, v in t.items() if k not in ("trace", "public")} for t in result["trajectories"]]
            results.append(compact)
    engineering = engineering_checks()
    engineering["actual_trace_checks"] = checked
    reproduced = summarize(results, engineering)
    primary = json.loads((output / "summary.json").read_text())
    if canonical_bytes(primary) != canonical_bytes(reproduced):
        raise ValueError("complete summary reproduction mismatch")
    if primary["gate_pass"] != finish["gate_pass"]:
        raise ValueError("terminal gate mismatch")
    return {"status": "complete_verified", "plan_sha256": plan_hash, "summary_sha256": file_digest(output / "summary.json"),
            "gate_pass": primary["gate_pass"], **checked}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "run", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--output", type=Path, required=True)
        if command == "prepare":
            sub.add_argument("--source-commit", required=True)
        elif command == "run":
            sub.add_argument("--prelaunch-review", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.output, args.source_commit)
    elif args.command == "run":
        result = execute(args.output, args.prelaunch_review)
    else:
        result = verify(args.output)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
