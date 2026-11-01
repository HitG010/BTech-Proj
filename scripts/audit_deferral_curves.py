"""Post-hoc Phase 2 audit: deferral curves, refit-inclusive uncertainty, agreement.

Reads cached repeat-panel and two-solver data through the guarded loaders, plus
the extracted answers in their cached score files. Refits only the historical
rules, with their original procedures, on resampled or repartitioned questions
or at other cost penalties. No generation, scoring or reference access; nothing
is selected and lambda .05 stays the primary point.
"""

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest import mock

import numpy as np
from threadpoolctl import threadpool_limits

from reasoning_budget import repeat_stats as historical
from reasoning_budget import scoring as v5
from reasoning_budget.storage import digest, envelope, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
REPEAT = BASE / "repeat-panel-v1"
OUTPUT = BASE / "deferral-curves-v1"
SOURCE_FILES = ("scripts/audit_deferral_curves.py", "tests/test_audit_deferral_curves.py",
                "docs/deferral-curves-protocol.md", "src/reasoning_budget/repeat_stats.py",
                "src/reasoning_budget/scoring.py", "scripts/opportunity_panel_plan.py",
                "scripts/opportunity_panel_analysis.py", "scripts/audit_confidence_gain_shape.py",
                "scripts/repeat_cpu_feasibility.py")
ORIGINAL_INNER_SPLITS = historical._inner_splits
K4 = {"k4_A_to_B": [[0, 1, 2, 3], [4, 5, 6, 7]], "k4_B_to_A": [[4, 5, 6, 7], [0, 1, 2, 3]]}
CONDITIONS = {**K4, "k8_full": [list(range(8)), list(range(8))]}
REPEAT_POLICIES = ("accept", "escalate", "confidence", "question_only", "solver_only",
                   "combined", "selected_baseline")
REDUCED_POLICIES = ("accept", "escalate", "confidence", "combined", "selected_baseline")
REPEAT_ENDPOINTS = ("combined_minus_selected_baseline", "combined_minus_confidence",
                    "confidence_minus_accept")
SOLVERS = ("qwen3-0.6b", "qwen3-1.7b")
REPORTED_TABLE3 = {
    "training_selected_cpu_family": [0.9075, 514.22],
    "training_selected_compact_neural_family": [0.8925, 604.82],
    "released_clm_zero_shot": [0.9475, 1550.53],
    "released_clm_calibrated": [0.8850, 443.71],
    "same_encoder_pca8_ridge": [0.8900, 330.81],
    "training_selected_clm_raw_family": [0.8875, 406.34],
    "token_learned_error_score": [0.8875, 570.33],
    "token_min_token_threshold": [0.9100, 483.20],
    "token_gain_ridge": [0.9000, 483.21],
}
SPEC = {
    "version": "deferral-curves-v1",
    "label": "post_hoc/descriptive-and-exploratory/reused-development",
    "lambda": 0.05,
    "lambda_grid": [0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3],
    "repeat_conditions": CONDITIONS, "primary_conditions": list(K4),
    "curve_fractions": [round(0.05 * i, 2) for i in range(21)],
    "reported_table3_points": REPORTED_TABLE3,
    "reported_table3_source": "manuscript v0.6 Table 3 [accuracy, tokens per state]",
    "refit": {"bootstrap_draws": 2000, "repeat_seed": 20261102, "two_solver_seed": 20261103,
              "repartitions": 200, "repeat_repartition_seed": 20261104,
              "two_solver_repartition_seed": 20261105, "interval": [0.05, 0.95],
              "repeat_learners": ["combined"],
              "outer_fold": "each copy keeps its original question fold",
              "inner_split": "distinct questions expanded to copies; original split if no copies",
              "fixed_action_seeds": {"repeat": 20261002, "two_solver": 20261009}},
    "agreement": {"bootstrap_seed": 20261101, "bootstrap_draws": 2000, "interval": [0.05, 0.95],
                  "agree": "both parser_status ok and equal v5 numeric values",
                  "repeat_partners": "other draws of the same evaluation half; full8 other seven",
                  "two_solver_partner": "other draw of the same question",
                  "charges": "both drafts always; thinking call on escalation",
                  "screen": {"minimum_mean": 0.01, "both_directions_positive": True,
                             "all_leave_one_question_out_positive": True}},
    "selection": "none; historical rules refitted with original procedures; lambda .05 primary",
}
_WORK = {}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def historical_spec(lam=None, learners=None):
    spec = copy.deepcopy(historical.ANALYSIS)
    if lam is not None:
        spec["lambda"] = float(lam)
    if learners is not None:
        spec["learners"] = list(learners)
    return spec


def gains(d, t, lam):
    return t[..., 0] - d[..., 0] - lam * t[..., 1] / 1000


# ---------------------------------------------------------------- repeat refits

def grouped_splits(groups):
    """Inner question folds over distinct questions, expanded to their copies.

    Without copies this returns exactly the historical inner split.
    """
    groups = np.asarray(groups)

    def split(questions, seed, count):
        questions = np.asarray(questions, dtype=int)
        _, first = np.unique(groups[questions], return_index=True)
        representatives = questions[np.sort(first)]
        out = []
        for inside, heldout in ORIGINAL_INNER_SPLITS(representatives, seed, count):
            out.append(tuple(questions[np.isin(groups[questions], groups[part])]
                             for part in (inside, heldout)))
        return out

    return split


def run_condition(q, z, d, t, fold_of, train_draws, eval_draws, spec):
    """Historical cross-fitting decisions; folds without held-out questions are skipped."""
    lam = spec["lambda"]
    gain = gains(d, t, lam)
    policies = [*spec["baselines"], *spec["learners"], "selected_baseline"]
    decisions = {p: np.zeros((len(q), len(eval_draws)), dtype=bool) for p in policies}
    details = []
    for fold in range(5):
        test = np.flatnonzero(fold_of == fold)
        train = np.flatnonzero(fold_of != fold)
        if not len(test):
            continue
        baseline, alphas, threshold, chosen, _ = historical._fit_fold(
            q, z, d, t, gain, train, test, train_draws, eval_draws, spec,
            spec["bootstrap_seed"] + fold)
        chosen["selected_baseline"] = chosen[baseline]
        for policy in policies:
            decisions[policy][test] = chosen[policy]
        details.append({"fold": fold, "selected_baseline": baseline, "alphas": alphas,
                        "confidence_threshold": float(threshold)})
    everyone = np.arange(len(q))
    metrics = {p: historical._rows(d, t, everyone, eval_draws, decisions[p], lam)
               for p in policies}
    return decisions, metrics, details


def repeat_endpoints(q, z, d, t, fold_of, spec):
    """Per-question four-draw averages of the three refit endpoints."""
    utility = {}
    for name, (train, evaluate) in K4.items():
        _, metrics, _ = run_condition(q, z, d, t, fold_of, train, evaluate, spec)
        utility[name] = {policy: values["utility"] for policy, values in metrics.items()}

    def average(a, b):
        first, second = (utility[name][a] - utility[name][b] for name in K4)
        return (first + second) / 2

    return {"combined_minus_selected_baseline": average("combined", "selected_baseline"),
            "combined_minus_confidence": average("combined", "confidence"),
            "confidence_minus_accept": average("confidence", "accept")}


# ------------------------------------------------------------ two-solver refits

def two_solver_rows(panel, fold_of, ids):
    rows = [{"question_id": qid, "solver": "s", "draw": draw,
             "confidence": float(panel["confidence"][i, draw]),
             "direct_correct": int(panel["direct_correct"][i, draw]),
             "thinking_correct": int(panel["thinking_correct"][i, draw]),
             "thinking_tokens": float(panel["thinking_tokens"][i, draw])}
            for i, qid in enumerate(ids) for draw in (0, 1)]
    return rows, {qid: int(fold) for qid, fold in zip(ids, fold_of)}


def confidence_crossfit(rows, folds, lam):
    """Line-for-line copy of the frozen two-solver crossfit with lambda as an argument.

    The only difference: a fold without held-out questions (possible in a
    bootstrap resample) is skipped instead of rejected. Tests and the runtime
    reproduction gate compare it with the frozen function.
    """
    ids = set(folds)
    keyed = {(r["question_id"], r["draw"]): r for r in rows}
    if set(keyed) != {(q, d) for q in ids for d in (0, 1)} or len(keyed) != len(rows):
        raise ValueError("Exactly two rows per question required")
    results = {}
    for train_draw, eval_draw in ((0, 1), (1, 0)):
        for fold in range(5):
            train = [keyed[q, train_draw] for q in sorted(ids) if folds[q] != fold]
            test = [keyed[q, eval_draw] for q in sorted(ids) if folds[q] == fold]
            if not test:
                continue
            candidates = [-np.inf, *sorted(set(r["confidence"] for r in train)), np.inf]

            def objective(threshold, train=train):
                action = [r["confidence"] < threshold for r in train]
                gain = sum(a * (r["thinking_correct"] - r["direct_correct"]
                                - lam * r["thinking_tokens"] / 1000)
                           for a, r in zip(action, train)) / len(train)
                return (gain, -sum(action), -threshold)

            threshold = max(candidates, key=objective)
            for r in test:
                results[(r["question_id"], train_draw, eval_draw)] = {
                    "fold": fold, "threshold": threshold,
                    "escalate": bool(r["confidence"] < threshold)}
    return results


def two_solver_actions(panel, fold_of, ids, lam=SPEC["lambda"]):
    """The two-solver confidence crossfit, run on these questions at this lambda."""
    rows, folds = two_solver_rows(panel, fold_of, ids)
    results = confidence_crossfit(rows, folds, lam)
    actions = np.zeros((len(ids), 2), dtype=bool)
    thresholds = np.zeros((len(ids), 2))
    for i, qid in enumerate(ids):
        for draw in (0, 1):
            item = results[qid, 1 - draw, draw]
            actions[i, draw], thresholds[i, draw] = item["escalate"], item["threshold"]
    return actions, thresholds


def two_solver_utilities(panel, actions, lam=SPEC["lambda"]):
    """Per-question, per-draw utilities in the original analysis's arithmetic."""
    dc, tc = panel["direct_correct"], panel["thinking_correct"]
    dtok, ttok = panel["direct_tokens"], panel["thinking_tokens"]
    accept = dc - lam * dtok / 1000
    escalated = tc - lam * (dtok + ttok) / 1000
    return {"accept": accept, "confidence": np.where(actions, escalated, accept),
            "escalate": escalated}


def two_solver_delta(panel, fold_of, ids, lam=SPEC["lambda"]):
    actions, _ = two_solver_actions(panel, fold_of, ids, lam)
    utility = two_solver_utilities(panel, actions, lam)
    delta = utility["confidence"] - utility["accept"]
    return (delta[:, 0] + delta[:, 1]) / 2


def copy_ids(ids, indices):
    """Unique names for resampled copies that keep the original sort order."""
    seen, out = {}, []
    for index in indices:
        seen[index] = seen.get(index, -1) + 1
        out.append(f"{ids[index]}#{seen[index]:04d}")
    return out


# ------------------------------------------------------------ worker processes

def _init(payload):
    _WORK.clear()
    _WORK.update(payload)
    _WORK["limiter"] = threadpool_limits(1)


def _repeat_bootstrap(indices):
    q, z, d, t, fold_of = _WORK["repeat"]
    indices = np.asarray(indices)
    with mock.patch.object(historical, "_inner_splits", grouped_splits(indices)):
        values = repeat_endpoints(q[indices], z[indices], d[indices], t[indices],
                                  fold_of[indices], historical_spec(learners=["combined"]))
    return {name: float(value.mean()) for name, value in values.items()}


def _repeat_repartition(fold_of):
    q, z, d, t, _ = _WORK["repeat"]
    values = repeat_endpoints(q, z, d, t, np.asarray(fold_of),
                              historical_spec(learners=["combined"]))
    return {name: float(value.mean()) for name, value in values.items()}


def _two_solver_bootstrap(indices):
    panels, ids, fold_of = _WORK["two_solver"]
    indices = np.asarray(indices)
    names = copy_ids(ids, indices)
    return {solver: float(two_solver_delta(
        {key: value[indices] for key, value in panel.items()}, fold_of[indices], names).mean())
        for solver, panel in panels.items()}


def _two_solver_repartition(fold_of):
    panels, ids, _ = _WORK["two_solver"]
    return {solver: float(two_solver_delta(panel, np.asarray(fold_of), ids).mean())
            for solver, panel in panels.items()}


def run_jobs(function, jobs, payload, processes):
    """Deterministic map; results do not depend on the number of processes."""
    jobs = [np.asarray(job).tolist() for job in jobs]
    if processes <= 1:
        _init(payload)
        return [function(job) for job in jobs]
    with ProcessPoolExecutor(processes, initializer=_init, initargs=(payload,)) as pool:
        return list(pool.map(function, jobs, chunksize=max(1, len(jobs) // (8 * processes))))


def repartitions(count, size, seed):
    rng = np.random.default_rng(seed)
    base = np.arange(size) % 5
    out = []
    for _ in range(count):
        fold_of = np.empty(size, dtype=int)
        fold_of[rng.permutation(size)] = base
        out.append(fold_of)
    return out


def fixed_means(values, seed, draws, interval):
    values = np.asarray(values, dtype=float)
    samples = np.random.default_rng(seed).integers(0, len(values), size=(draws, len(values)))
    means = values[samples].mean(1)
    return [float(x) for x in np.quantile(means, interval)], float(means.std(ddof=1))


def side(ci):
    return 1 if ci[0] > 0 else -1 if ci[1] < 0 else 0


def refit_reading(fixed_ci, refit_ci):
    fixed, refit = side(fixed_ci), side(refit_ci)
    if fixed and refit == fixed:
        return "sign_robust"
    if fixed and not refit:
        return "no_longer_excludes_zero"
    if not fixed and not refit:
        return "both_include_zero"
    if not fixed:
        return "refit_excludes_zero"
    return "sign_reversed"


def refit_summary(point, fixed, bootstrap, repartition, interval):
    fixed_ci, fixed_sd = fixed
    boot = np.asarray(bootstrap, dtype=float)
    parts = np.asarray(repartition, dtype=float)
    refit_ci = [float(x) for x in np.quantile(boot, interval)]
    return {"point": float(point), "fixed_action_ci90": fixed_ci, "fixed_action_sd": fixed_sd,
            "refit_ci90": refit_ci, "refit_mean": float(boot.mean()),
            "refit_sd": float(boot.std(ddof=1)), "refit_share_below_zero": float((boot < 0).mean()),
            "width_ratio": float((refit_ci[1] - refit_ci[0]) / (fixed_ci[1] - fixed_ci[0])),
            "repartition": {"min": float(parts.min()), "max": float(parts.max()),
                            "quantiles_05_50_95": [float(x) for x in
                                                   np.quantile(parts, [0.05, 0.5, 0.95])],
                            "share_below_zero": float((parts < 0).mean()),
                            "count": int(parts.size)},
            "reading": refit_reading(fixed_ci, refit_ci)}


# ------------------------------------------------------------------- curves

def states(dc, tc, dtok, ttok, confidence=None):
    out = {"dc": np.ravel(dc).astype(float), "tc": np.ravel(tc).astype(float),
           "dtok": np.ravel(dtok).astype(float), "ttok": np.ravel(ttok).astype(float)}
    if confidence is not None:
        out["confidence"] = np.ravel(confidence).astype(float)
    return out


def point(state, escalate, lam):
    dc, tc, dtok, ttok = (state[key] for key in ("dc", "tc", "dtok", "ttok"))
    esc = np.ravel(escalate).astype(bool)
    if esc.shape != dc.shape:
        raise ValueError("One action per state required")
    chosen = np.where(esc, tc, dc)
    tokens = dtok + esc * ttok
    rescue, harm = (dc == 0) & (tc == 1), (dc == 1) & (tc == 0)
    return {"accuracy": float(chosen.mean()), "tokens": float(tokens.mean()),
            "utility": float((chosen - lam * tokens / 1000).mean()),
            "escalation_rate": float(esc.mean()), "escalations": int(esc.sum()),
            "escalated_rescues": int((esc & rescue).sum()),
            "escalated_harms": int((esc & harm).sum()),
            "escalated_both_correct": int((esc & (dc == 1) & (tc == 1)).sum()),
            "escalated_both_wrong": int((esc & (dc == 0) & (tc == 0)).sum()),
            "missed_rescues": int((~esc & rescue).sum())}


def references(state, lam):
    n = len(state["dc"])
    gain = state["tc"] - state["dc"] - lam * state["ttok"] / 1000
    direct, escalate = point(state, np.zeros(n), lam), point(state, np.ones(n), lam)
    return {"always_direct": direct, "always_escalate": escalate,
            "oracle": point(state, gain > 0, lam),
            "random_line": {"direct_accuracy": direct["accuracy"],
                            "escalate_accuracy": escalate["accuracy"],
                            "direct_tokens": direct["tokens"],
                            "mean_thinking_tokens": float(state["ttok"].mean())},
            "states": n}


def position(accuracy, tokens, refs, lam):
    line = refs["random_line"]
    p = (tokens - line["direct_tokens"]) / line["mean_thinking_tokens"]
    inside = -1e-9 <= p <= 1 + 1e-9
    p = min(max(p, 0.0), 1.0) if inside else None
    random = (line["direct_accuracy"] + p * (line["escalate_accuracy"] - line["direct_accuracy"])
              if inside else None)
    utility = accuracy - lam * tokens / 1000
    base, top = refs["always_direct"]["utility"], refs["oracle"]["utility"]
    return {"utility": float(utility), "matched_random_escalation": p,
            "random_accuracy_at_equal_tokens": random,
            "lift_over_random": float(accuracy - random) if inside else None,
            "oracle_share": float((utility - base) / (top - base)) if top > base else None}


def placed(state_point, refs, lam):
    return state_point | position(state_point["accuracy"], state_point["tokens"], refs, lam)


def confidence_envelope(state, fractions, lam):
    n = len(state["dc"])
    order = np.lexsort((np.arange(n), state["confidence"]))
    rows = []
    for fraction in fractions:
        esc = np.zeros(n, dtype=bool)
        esc[order[:int(round(fraction * n))]] = True
        p = point(state, esc, lam)
        rows.append({"fraction": fraction, "accuracy": p["accuracy"], "tokens": p["tokens"],
                     "utility": p["utility"]})
    return rows


def oracle_frontier(state, fractions, lam):
    rescues = np.flatnonzero((state["dc"] == 0) & (state["tc"] == 1))
    rescues = rescues[np.lexsort((rescues, state["ttok"][rescues]))]
    rows = []
    for fraction in fractions:
        esc = np.zeros(len(state["dc"]), dtype=bool)
        esc[rescues[:int(round(fraction * len(rescues)))]] = True
        p = point(state, esc, lam)
        rows.append({"rescue_fraction": fraction, "accuracy": p["accuracy"],
                     "tokens": p["tokens"]})
    return rows


def repeat_states(d, t, z, conditions):
    parts = [(d[:, e], t[:, e], z[:, e, 0]) for _, e in conditions.values()]
    return states(np.concatenate([p[0][..., 0].ravel() for p in parts]),
                  np.concatenate([p[1][..., 0].ravel() for p in parts]),
                  np.concatenate([p[0][..., 1].ravel() for p in parts]),
                  np.concatenate([p[1][..., 1].ravel() for p in parts]),
                  np.concatenate([p[2].ravel() for p in parts]))


def pooled(decisions, conditions, policy):
    return np.concatenate([decisions[name][policy].ravel() for name in conditions])


def panel_curves(state, policies, lam, spec):
    refs = references(state, lam)
    return {"references": {name: placed(refs[name], refs, lam)
                           for name in ("always_direct", "always_escalate", "oracle")},
            "random_line": refs["random_line"], "states": refs["states"],
            "policies": {name: placed(point(state, esc, lam), refs, lam)
                         for name, esc in policies.items()},
            "confidence_envelope_in_sample": confidence_envelope(
                state, spec["curve_fractions"], lam),
            "oracle_frontier_in_sample": oracle_frontier(state, spec["curve_fractions"], lam)}


def two_solver_states(panel):
    return states(*(panel[key].T.ravel() for key in ("direct_correct", "thinking_correct",
                                                     "direct_tokens", "thinking_tokens",
                                                     "confidence")))


# ---------------------------------------------------------------- agreement

def answer_values(answers, statuses):
    answers, statuses = np.asarray(answers, dtype=object), np.asarray(statuses, dtype=object)
    values = np.empty(statuses.shape, dtype=object)
    for index in np.ndindex(statuses.shape):
        values[index] = v5.numeric(answers[index]) if statuses[index] == "ok" else None
    return values


def agreement_matrix(values, correct):
    n, draws = values.shape
    agree = np.zeros((n, draws, draws), dtype=bool)
    for i in range(n):
        for a in range(draws):
            for b in range(draws):
                if a != b and values[i, a] is not None and values[i, a] == values[i, b]:
                    if correct[i, a] != correct[i, b]:
                        raise ValueError("Agreeing answers have different cached correctness")
                    agree[i, a, b] = True
    return agree


def pairs_within(draws):
    return [(s, p) for s in draws for p in draws if p != s]


def agreement_rows(d, t, agree, pairs, lam):
    """Per-question means over (state, partner) pairs; expected counts per state."""
    s_index = np.array([s for s, _ in pairs])
    p_index = np.array([p for _, p in pairs])
    dc, tc = d[:, s_index, 0], t[:, s_index, 0]
    esc = ~agree[:, s_index, p_index]
    chosen = np.where(esc, tc, dc)
    second = d[:, p_index, 1]
    tokens = d[:, s_index, 1] + second + esc * t[:, s_index, 1]
    states_per_question = len({s for s, _ in pairs})
    weight = states_per_question / len(pairs)
    rescue, harm = (dc == 0) & (tc == 1), (dc == 1) & (tc == 0)
    composition = {name: float(mask.sum() * weight) for name, mask in {
        "escalations": esc, "escalated_rescues": esc & rescue, "escalated_harms": esc & harm,
        "escalated_both_correct": esc & (dc == 1) & (tc == 1),
        "escalated_both_wrong": esc & (dc == 0) & (tc == 0),
        "missed_rescues": ~esc & rescue}.items()}
    return {"accuracy": chosen.mean(1), "tokens": tokens.mean(1),
            "utility": (chosen - lam * tokens / 1000).mean(1), "escalation_rate": esc.mean(1),
            "second_draft_utility_cost": (lam * second / 1000).mean(1)}, composition


def screen(per_direction, spec):
    names = list(per_direction)
    per = np.array([per_direction[name] for name in names])
    values = per.mean(0)
    leave = (values.sum() - values) / (len(values) - 1)
    rule = spec["screen"]
    checks = {"average_at_least_minimum": bool(values.mean() >= rule["minimum_mean"]),
              "both_directions_positive": bool((per.mean(1) > 0).all()),
              "all_leave_one_question_out_positive": bool((leave > 0).all())}
    return {"mean": float(values.mean()), "ci90": historical._ci(values, spec),
            "directions": dict(zip(names, map(float, per.mean(1)))),
            "leave_one_out_min": float(leave.min()), "checks": checks,
            "passes": all(checks.values())}


def agreement_summary(rows_by_direction, comparator, accept, composition, spec):
    delta = {n: rows_by_direction[n]["utility"] - comparator[n] for n in rows_by_direction}
    free = {n: delta[n] + rows_by_direction[n]["second_draft_utility_cost"]
            for n in rows_by_direction}
    versus_accept = {n: rows_by_direction[n]["utility"] - accept[n] for n in rows_by_direction}

    def mean(metric):
        return float(np.mean([rows_by_direction[n][metric].mean() for n in rows_by_direction]))

    return {"accuracy": mean("accuracy"), "tokens": mean("tokens"), "utility": mean("utility"),
            "escalation_rate": mean("escalation_rate"),
            "second_draft_utility_cost": mean("second_draft_utility_cost"),
            "versus_confidence": screen(delta, spec),
            "versus_accept": {"mean": float(np.mean(list(versus_accept.values()))),
                              "ci90": historical._ci(np.mean(list(versus_accept.values()), 0),
                                                     spec)},
            "free_second_draft_difference_vs_confidence_descriptive":
                float(np.mean(list(free.values()))),
            "expected_composition": composition}


def repeat_agreement(d, t, agree, confidence_metrics, spec):
    lam = spec["lambda"]
    rows, composition, comparator, accept = {}, {}, {}, {}
    for name, (_, evaluate) in K4.items():
        rows[name], composition[name] = agreement_rows(d, t, agree, pairs_within(evaluate), lam)
        comparator[name] = confidence_metrics[name]["confidence"]["utility"]
        accept[name] = confidence_metrics[name]["accept"]["utility"]
    totals = {key: sum(c[key] for c in composition.values()) for key in composition["k4_A_to_B"]}
    primary = agreement_summary(rows, comparator, accept, totals, spec["agreement"])
    full_rows, full_composition = agreement_rows(d, t, agree, pairs_within(range(8)), lam)
    full = {"accuracy": float(full_rows["accuracy"].mean()),
            "tokens": float(full_rows["tokens"].mean()),
            "utility": float(full_rows["utility"].mean()),
            "difference_vs_full8_confidence": float(
                (full_rows["utility"] - confidence_metrics["k8_full"]["confidence"]["utility"])
                .mean()),
            "expected_composition": full_composition}
    return {"primary_k4": primary, "secondary_full8": full,
            "reading": "pass" if primary["versus_confidence"]["passes"] else "fail"}


def two_solver_agreement(panel, actions, spec):
    lam = spec["lambda"]
    d = np.stack([panel["direct_correct"], panel["direct_tokens"]], axis=2)
    t = np.stack([panel["thinking_correct"], panel["thinking_tokens"]], axis=2)
    values = answer_values(panel["answers"], panel["statuses"])
    agree = agreement_matrix(values, panel["direct_correct"])
    utility = two_solver_utilities(panel, actions, lam)
    rows, composition, comparator, accept = {}, {}, {}, {}
    for draw in (0, 1):
        name = f"draw_{draw}"
        rows[name], composition[name] = agreement_rows(d, t, agree, [(draw, 1 - draw)], lam)
        comparator[name], accept[name] = utility["confidence"][:, draw], utility["accept"][:, draw]
    totals = {key: sum(c[key] for c in composition.values()) for key in composition["draw_0"]}
    summary = agreement_summary(rows, comparator, accept, totals, spec["agreement"])
    return summary | {"agreeing_questions": int(agree[:, 0, 1].sum()),
                      "reading_secondary": "pass" if summary["versus_confidence"]["passes"]
                      else "fail"}


# ------------------------------------------------------------------ analysis

def check_repeat_reproduction(primary, ids, full, reduced):
    cached_conditions = primary["statistics"]["conditions"]
    for name, (train, evaluate) in CONDITIONS.items():
        cached = cached_conditions[name]
        if cached["train_draws"] != train or cached["evaluation_draws"] != evaluate:
            raise ValueError(f"Repeat condition draws changed: {name}")
        for policy in REPEAT_POLICIES:
            for i, qid in enumerate(ids):
                recorded = cached["per_question"][qid]["policies"][policy]["decisions"]
                if full[name][0][policy][i].tolist() != recorded:
                    raise ValueError(f"Repeat decision not reproduced: {name}/{qid}/{policy}")
        delta = full[name][1]["combined"]["utility"] - full[name][1]["selected_baseline"]["utility"]
        if not np.isclose(delta.mean(), cached["combined_minus_baseline"]["mean"],
                          rtol=0, atol=1e-12):
            raise ValueError(f"Repeat combined-minus-baseline not reproduced: {name}")
    for name in K4:
        for policy in REDUCED_POLICIES:
            if not np.array_equal(reduced[name][policy], full[name][0][policy]):
                raise ValueError(f"Reduced refit changes decisions: {name}/{policy}")


def check_frozen_crossfit(panel, fold_of, ids):
    """The copied crossfit must equal the frozen function on the real questions."""
    from scripts import opportunity_panel_plan as plan
    rows, folds = two_solver_rows(panel, fold_of, ids)
    if confidence_crossfit(rows, folds, plan.LAM) != plan.confidence_crossfit(rows, folds, "s"):
        raise ValueError("Copied two-solver crossfit differs from the frozen function")


def check_two_solver_reproduction(report, solver, actions, thresholds, delta):
    cached = report["statistics"]["solvers"][solver]
    for draw in (0, 1):
        recorded = cached["draws"][str(draw)]
        if actions[:, draw].tolist() != recorded["confidence_actions"]:
            raise ValueError(f"Two-solver confidence actions not reproduced: {solver}/{draw}")
        mapped = ["always" if v == np.inf else "never" if v == -np.inf else float(v)
                  for v in thresholds[:, draw]]
        if mapped != recorded["confidence_thresholds"]:
            raise ValueError(f"Two-solver thresholds not reproduced: {solver}/{draw}")
    if not np.isclose(delta.mean(), cached["screen"]["confidence_minus_accept_average"]["mean"],
                      rtol=0, atol=1e-12):
        raise ValueError(f"Two-solver confidence-minus-accept not reproduced: {solver}")


def repeat_curves(q, z, d, t, fold_of, spec):
    state = repeat_states(d, t, z, K4)
    sweep = []
    for lam in spec["lambda_grid"]:
        hspec = historical_spec(lam=lam)
        decisions = {name: run_condition(q, z, d, t, fold_of, a, b, hspec)[0]
                     for name, (a, b) in K4.items()}
        refs = references(state, lam)
        points = {p: point(state, pooled(decisions, K4, p), lam) for p in REPEAT_POLICIES}
        sweep.append({"lambda": lam, "oracle": refs["oracle"], "policies": points,
                      "combined_minus_confidence":
                          points["combined"]["utility"] - points["confidence"]["utility"],
                      "combined_minus_selected_baseline":
                          points["combined"]["utility"] - points["selected_baseline"]["utility"]})
    return state, sweep


def analyze(repeat, two_solver, processes=1, spec=SPEC, primary=None, report=None):
    """`repeat` = (ids, q, z, d, t, fold_of, answers, statuses);
    `two_solver` = (ids, fold_of, {solver: panel}). Optional primary/report gate reproduction."""
    ids, q, z, d, t, fold_of, answers, statuses = repeat
    two_ids, two_folds, panels = two_solver
    lam, refit = spec["lambda"], spec["refit"]
    base = historical_spec()
    full = {name: run_condition(q, z, d, t, fold_of, a, b, base)
            for name, (a, b) in CONDITIONS.items()}
    reduced = {name: run_condition(q, z, d, t, fold_of, a, b,
                                   historical_spec(learners=refit["repeat_learners"]))[0]
               for name, (a, b) in K4.items()}
    if primary is not None:
        check_repeat_reproduction(primary, ids, full, reduced)
    two = {}
    for solver in SOLVERS:
        actions, thresholds = two_solver_actions(panels[solver], two_folds, two_ids)
        delta = two_solver_delta(panels[solver], two_folds, two_ids)
        if report is not None:
            check_frozen_crossfit(panels[solver], two_folds, two_ids)
            check_two_solver_reproduction(report, solver, actions, thresholds, delta)
        two[solver] = {"actions": actions, "delta": delta}

    # Part A: curves
    state, sweep = repeat_curves(q, z, d, t, fold_of, spec)
    refs = references(state, lam)
    k4_policies = {p: pooled({n: full[n][0] for n in K4}, K4, p) for p in REPEAT_POLICIES}
    repeat_curve = panel_curves(state, k4_policies, lam, spec) | {"lambda_sweep": sweep}
    repeat_curve["reported_table3_points"] = {
        name: {"accuracy": acc, "tokens": tok} | position(acc, tok, refs, lam)
        for name, (acc, tok) in spec["reported_table3_points"].items()}
    full_state = repeat_states(d, t, z, {"k8_full": CONDITIONS["k8_full"]})
    repeat_curve["secondary_full8"] = panel_curves(
        full_state, {p: full["k8_full"][0][p].ravel() for p in REPEAT_POLICIES}, lam, spec)
    curves = {"repeat_qwen3_1.7b": repeat_curve}
    for solver in SOLVERS:
        panel = panels[solver]
        solver_state = two_solver_states(panel)
        n = len(solver_state["dc"])
        solver_sweep = []
        for grid_lam in spec["lambda_grid"]:
            actions, _ = two_solver_actions(panel, two_folds, two_ids, grid_lam)
            points = {"accept": point(solver_state, np.zeros(n), grid_lam),
                      "escalate": point(solver_state, np.ones(n), grid_lam),
                      "confidence": point(solver_state, actions.T.ravel(), grid_lam)}
            solver_sweep.append({"lambda": grid_lam,
                                 "oracle": references(solver_state, grid_lam)["oracle"],
                                 "policies": points, "confidence_minus_accept":
                                     points["confidence"]["utility"] - points["accept"]["utility"]})
        curves["two_solver_" + solver.replace("-", "_")] = panel_curves(
            solver_state, {"confidence": two[solver]["actions"].T.ravel()}, lam, spec) | {
            "lambda_sweep": solver_sweep}

    # Part C: agreement (before the long resampling, so data errors surface early)
    values = answer_values(answers, statuses)
    agree = agreement_matrix(values, d[:, :, 0])
    agreement = {"repeat_qwen3_1.7b": repeat_agreement(
        d, t, agree, {n: full[n][1] for n in CONDITIONS}, spec)}
    for solver in SOLVERS:
        agreement["two_solver_" + solver.replace("-", "_")] = two_solver_agreement(
            panels[solver], two[solver]["actions"], spec)

    # Part B: refit-inclusive uncertainty
    utilities = {n: {p: full[n][1][p]["utility"] for p in REDUCED_POLICIES} for n in K4}

    def average(a, b):
        first, second = (utilities[n][a] - utilities[n][b] for n in K4)
        return (first + second) / 2

    endpoints = {"combined_minus_selected_baseline": average("combined", "selected_baseline"),
                 "combined_minus_confidence": average("combined", "confidence"),
                 "confidence_minus_accept": average("confidence", "accept")}
    if primary is not None:
        recorded = primary["statistics"]["k4_average_delta"]
        mean = endpoints["combined_minus_selected_baseline"].mean()
        if (not np.isclose(mean, recorded["mean"], rtol=0, atol=1e-12)
                or not np.allclose(historical._ci(endpoints["combined_minus_selected_baseline"],
                                                  historical.ANALYSIS),
                                   recorded["ci90"], rtol=0, atol=1e-12)):
            raise ValueError("Repeat four-draw average or interval not reproduced")
    payload = {"repeat": (q, z, d, t, fold_of),
               "two_solver": ({s: {k: v for k, v in panels[s].items()
                                   if k not in ("answers", "statuses")} for s in SOLVERS},
                              list(two_ids), two_folds)}
    rng = np.random.default_rng(refit["repeat_seed"])
    repeat_samples = rng.integers(0, len(ids), size=(refit["bootstrap_draws"], len(ids)))
    rng = np.random.default_rng(refit["two_solver_seed"])
    two_samples = rng.integers(0, len(two_ids), size=(refit["bootstrap_draws"], len(two_ids)))
    boot_repeat = run_jobs(_repeat_bootstrap, repeat_samples, payload, processes)
    part_repeat = run_jobs(_repeat_repartition, repartitions(
        refit["repartitions"], len(ids), refit["repeat_repartition_seed"]), payload, processes)
    boot_two = run_jobs(_two_solver_bootstrap, two_samples, payload, processes)
    part_two = run_jobs(_two_solver_repartition, repartitions(
        refit["repartitions"], len(two_ids), refit["two_solver_repartition_seed"]),
        payload, processes)
    seeds = refit["fixed_action_seeds"]
    uncertainty = {}
    for name in REPEAT_ENDPOINTS:
        fixed = fixed_means(endpoints[name], seeds["repeat"], historical.ANALYSIS[
            "bootstrap_draws"], historical.ANALYSIS["interval"])
        uncertainty["repeat_" + name] = refit_summary(
            endpoints[name].mean(), fixed, [b[name] for b in boot_repeat],
            [p[name] for p in part_repeat], refit["interval"])
    for solver in SOLVERS:
        fixed = fixed_means(two[solver]["delta"], seeds["two_solver"], 2000, [0.05, 0.95])
        if report is not None and not np.allclose(
                fixed[0], report["statistics"]["solvers"][solver]["screen"][
                    "confidence_minus_accept_average"]["ci90"], rtol=0, atol=1e-12):
            raise ValueError(f"Two-solver fixed-action interval not reproduced: {solver}")
        uncertainty["two_solver_" + solver.replace("-", "_") + "_confidence_minus_accept"] = \
            refit_summary(two[solver]["delta"].mean(), fixed, [b[solver] for b in boot_two],
                          [p[solver] for p in part_two], refit["interval"])

    return {"curves": curves, "refit_uncertainty": uncertainty, "agreement": agreement,
            "agreement_primary_reading": agreement["repeat_qwen3_1.7b"]["reading"],
            "historical_actions_verified": primary is not None and report is not None,
            "processes": int(processes)}


# -------------------------------------------------------------------- inputs

def repeat_inputs():
    from scripts.repeat_cpu_feasibility import load_panel
    panel = load_panel(REPEAT)
    score = verified(REPEAT / "scores.numeric-v7.json")
    if digest(score) != panel["identity"]["scores_sha256"]:
        raise ValueError("Repeat score cache changed")
    jobs = {(r["job"]["question_id"], r["job"]["sample"]): r["job"]["id"]
            for r in panel["rows"] if r["job"]["mode"] == "direct"}
    scores = {item["job_id"]: item for item in score["scores"]}
    ids = panel["ids"]
    answers = np.empty((len(ids), 8), dtype=object)
    statuses = np.empty((len(ids), 8), dtype=object)
    for i, qid in enumerate(ids):
        for sample in range(8):
            item = scores[jobs[qid, sample]]
            if item["mode"] != "direct" or item["question_id"] != qid:
                raise ValueError("Repeat score does not match its direct draft")
            answers[i, sample] = item["extracted_answer"]
            statuses[i, sample] = item["parser_status"]
    if not np.array_equal(statuses == "ok", panel["z"][:, :, 2] == 1):
        raise ValueError("Repeat parser status differs from the panel feature")
    fold_of = np.array([panel["folds"][qid] for qid in ids])
    data = (ids, panel["q"], panel["z"], panel["d"], panel["t"], fold_of, answers, statuses)
    return data, panel["primary"], {"panel": panel["identity"], "study": str(REPEAT)}


def two_solver_inputs():
    from scripts.audit_confidence_gain_shape import two_solver_endpoint
    from scripts.opportunity_panel_analysis import paired_rows
    grouped, report, scores, identity = two_solver_endpoint()
    rows = paired_rows(grouped, scores)
    ids, folds = report["statistics"]["question_ids"], report["statistics"]["folds"]
    index = {qid: i for i, qid in enumerate(ids)}
    by_job = {(item["solver"], item["job_id"]): item for item in scores["scores"]}
    keys = ("direct_correct", "thinking_correct", "direct_tokens", "thinking_tokens",
            "confidence")
    panels = {}
    for solver in SOLVERS:
        panel = {key: np.full((len(ids), 2), np.nan) for key in keys}
        panel["answers"] = np.full((len(ids), 2), None, dtype=object)
        panel["statuses"] = np.full((len(ids), 2), None, dtype=object)
        for row in (r for r in rows if r["solver"] == solver):
            for key in keys:
                panel[key][index[row["question_id"]], row["draw"]] = row[key]
        for record in grouped[solver]:
            job = record["job"]
            if job["mode"] == "direct":
                item = by_job[solver, job["id"]]
                cell = (index[job["question_id"]], job["sample"])
                panel["answers"][cell] = item["extracted_answer"]
                panel["statuses"][cell] = item["parser_status"]
        if (any(not np.isfinite(panel[key]).all() for key in keys)
                or any(s is None for s in panel["statuses"].ravel())):
            raise ValueError(f"Incomplete two-solver panel: {solver}")
        panels[solver] = panel
    fold_of = np.array([folds[qid] for qid in ids])
    return (ids, fold_of, panels), report, identity


# ------------------------------------------------------------------- outputs

def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(payload), stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked_output():
    if OUTPUT.is_symlink() or OUTPUT.resolve() != BASE.resolve() / SPEC["version"]:
        raise ValueError("Only the separate deferral-curves directory is writable")


def sources():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def packages():
    return {name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "scikit-learn", "threadpoolctl")}


def identities():
    _, _, repeat_identity = repeat_inputs()
    _, _, two_identity = two_solver_inputs()
    return {"repeat": repeat_identity, "two_solver": two_identity}


def prepare():
    checked_output()
    plan = {"spec": SPEC, "inputs": identities(), "source_file_sha256": sources(),
            "packages": packages(), "no_generation_scoring_references": True}
    write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "plan_sha256": digest(plan)}


def fmt(value, digits=4, sign=True):
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(v, digits, sign) for v in value) + "]"
    if isinstance(value, float):
        return f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
    return str(value)


def pct(value):
    return f"{100 * value:.2f}%"


def markdown(report):
    stats = report["statistics"]
    lines = ["# Deferral curves, refit uncertainty, and agreement baseline", "",
             "Post-hoc analysis of cached, reused development data. See "
             "`docs/deferral-curves-protocol.md`. Historical decisions were reproduced "
             f"before analysis: **{stats['historical_actions_verified']}**. "
             f"Worker processes: {stats['processes']}.", ""]
    deviation = report.get("runtime_environment_deviation")
    if deviation is not None:
        lines += ["Two-solver runtime fields differing from collection: "
                  f"{', '.join(deviation) or 'none'}. Cached bytes were verified by hash.", ""]
    lines += ["## A. Accuracy and cost at λ = .05", ""]
    for panel, curve in stats["curves"].items():
        lines += [f"### {panel}", "", "| Policy | Accuracy | Tokens/state | Utility | "
                  "Escalation | Lift over random | Oracle share | Rescues | Harms | "
                  "Both wrong | Missed rescues |", "|---|---:|---:|---:|---:|---:|---:|---:|"
                  "---:|---:|---:|"]
        for group in ("references", "policies"):
            for name, p in curve[group].items():
                lines.append(
                    f"| {name} | {pct(p['accuracy'])} | {p['tokens']:.2f} | "
                    f"{p['utility']:.6f} | {p['escalation_rate']:.3f} | "
                    f"{fmt(p['lift_over_random'], 4)} | {fmt(p['oracle_share'], 3)} | "
                    f"{p['escalated_rescues']} | {p['escalated_harms']} | "
                    f"{p['escalated_both_wrong']} | {p['missed_rescues']} |")
        for name, p in curve.get("reported_table3_points", {}).items():
            lines.append(f"| {name} (Table 3, reported) | {pct(p['accuracy'])} | "
                         f"{p['tokens']:.2f} | {p['utility']:.6f} | | "
                         f"{fmt(p['lift_over_random'], 4)} | {fmt(p['oracle_share'], 3)} | | | | |")
        lines += ["", "λ sweep (rules refitted at each λ; utility at that λ):", ""]
        if panel.startswith("repeat"):
            lines += ["| λ | Confidence acc./tokens | Combined acc./tokens | Oracle acc./tokens | "
                      "Combined − confidence | Combined − selected baseline |",
                      "|---:|---|---|---|---:|---:|"]
            for row in curve["lambda_sweep"]:
                c, m, o = row["policies"]["confidence"], row["policies"]["combined"], row["oracle"]
                lines.append(f"| {row['lambda']:g} | {pct(c['accuracy'])} / {c['tokens']:.1f} | "
                             f"{pct(m['accuracy'])} / {m['tokens']:.1f} | "
                             f"{pct(o['accuracy'])} / {o['tokens']:.1f} | "
                             f"{row['combined_minus_confidence']:+.6f} | "
                             f"{row['combined_minus_selected_baseline']:+.6f} |")
        else:
            lines += ["| λ | Confidence acc./tokens | Oracle acc./tokens | Confidence − accept |",
                      "|---:|---|---|---:|"]
            for row in curve["lambda_sweep"]:
                c, o = row["policies"]["confidence"], row["oracle"]
                lines.append(f"| {row['lambda']:g} | {pct(c['accuracy'])} / {c['tokens']:.1f} | "
                             f"{pct(o['accuracy'])} / {o['tokens']:.1f} | "
                             f"{row['confidence_minus_accept']:+.6f} |")
        lines.append("")
    lines += ["## B. Refit-inclusive uncertainty", "",
              "| Endpoint | Point | Fixed-action 90% | Refit-inclusive 90% | Refit mean | "
              "Width ratio | Repartition 5–50–95% | Reading |",
              "|---|---:|---|---|---:|---:|---|---|"]
    for name, r in stats["refit_uncertainty"].items():
        lines.append(f"| {name} | {r['point']:+.6f} | {fmt(r['fixed_action_ci90'], 6)} | "
                     f"{fmt(r['refit_ci90'], 6)} | {r['refit_mean']:+.6f} | "
                     f"{r['width_ratio']:.2f} | "
                     f"{fmt(r['repartition']['quantiles_05_50_95'], 6)} | {r['reading']} |")
    lines += ["", "## C. Two-draft agreement baseline", "",
              f"Primary reading (repeat panel): **{stats['agreement_primary_reading']}**.", "",
              "| Panel | Accuracy | Tokens/state | Escalation | Difference vs confidence [90%] | "
              "Directions | LOO min | Second-draft cost | Free-draft difference | vs accept |",
              "|---|---:|---:|---:|---|---|---:|---:|---:|---|"]
    for panel, item in stats["agreement"].items():
        a = item.get("primary_k4", item)
        v = a["versus_confidence"]
        directions = ", ".join(f"{k} {x:+.6f}" for k, x in v["directions"].items())
        lines.append(f"| {panel} | {pct(a['accuracy'])} | {a['tokens']:.2f} | "
                     f"{a['escalation_rate']:.3f} | {v['mean']:+.6f} {fmt(v['ci90'], 6)} | "
                     f"{directions} | {v['leave_one_out_min']:+.6f} | "
                     f"{a['second_draft_utility_cost']:.6f} | "
                     f"{a['free_second_draft_difference_vs_confidence_descriptive']:+.6f} | "
                     f"{a['versus_accept']['mean']:+.6f} {fmt(a['versus_accept']['ci90'], 6)} |")
    full8 = stats["agreement"]["repeat_qwen3_1.7b"]["secondary_full8"]
    lines += ["", f"Secondary full8 agreement: {pct(full8['accuracy'])} at "
              f"{full8['tokens']:.2f} tokens; difference vs full8 confidence "
              f"{full8['difference_vs_full8_confidence']:+.6f}.", ""]
    return "\n".join(lines) + "\n"


def execute(processes):
    checked_output()
    plan = verified(OUTPUT / "plan.json")
    if plan["spec"] != SPEC:
        raise ValueError("Deferral-curves spec changed")
    if plan["source_file_sha256"] != sources():
        raise ValueError("Frozen deferral-curves source changed")
    if plan["packages"] != packages():
        raise ValueError("Frozen deferral-curves environment changed")
    if (OUTPUT / "report.json").exists():
        raise ValueError("Analysis already completed; it is not restarted")
    repeat, primary, repeat_identity = repeat_inputs()
    two_solver, two_report, two_identity = two_solver_inputs()
    if {"repeat": repeat_identity, "two_solver": two_identity} != plan["inputs"]:
        raise ValueError("Frozen deferral-curves inputs changed")
    with threadpool_limits(1):
        statistics = analyze(repeat, two_solver, processes, SPEC, primary, two_report)
    from scripts.audit_confidence_gain_shape import study_inventory
    from scripts.verify_phase2_repeat import verify
    preservation = verify(REPEAT)
    if digest(study_inventory(Path(two_identity["study"]))) != \
            two_identity["study_inventory_sha256"]:
        raise ValueError("Two-solver study files changed")
    report = {"plan_sha256": digest(plan), "spec": SPEC, "inputs": plan["inputs"],
              "statistics": statistics,
              "repeat_protected_originals_verified": preservation["protected_originals_verified"],
              "two_solver_inventory_unchanged": True,
              "runtime_environment_deviation":
                  two_identity["runtime_environment"]["differing_fields"],
              "no_generation_scoring_references": True, "cloud_spend_usd": 0.0}
    write_new(OUTPUT / "report.json", report)
    with (OUTPUT / "report.md").open("x") as stream:
        stream.write(markdown(report))
    return {"report_sha256": digest(report),
            "agreement_primary_reading": statistics["agreement_primary_reading"],
            "refit_readings": {k: v["reading"]
                               for k, v in statistics["refit_uncertainty"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "execute"])
    parser.add_argument("--processes", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    # Run through the importable module so worker processes can unpickle functions.
    from scripts import audit_deferral_curves as module
    print(module.prepare() if args.command == "prepare" else module.execute(args.processes))


if __name__ == "__main__":
    main()
