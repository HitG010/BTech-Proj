"""Independent read-only G1 artifact review; never invoke acquisition or fitting.

Only the new synthetic output directory and its pinned source files are read.
Implementation helpers are deliberately not imported. Seeded synthetic arrays
are reconstructed to check outcomes and held-out arithmetic, not to select or
purchase anything. An optional NEW review record uses exclusive creation.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

METHODS = ("uniform_coverage", "uniform_repeat", "confidence_stratified", "disagreement",
           "closest_cost_aware", "reactive_impact", "candidate", "candidate_no_repeat",
           "candidate_no_joint_covariance")
SETTINGS = ("null_no_benefit", "threshold_cost_zero", "high_noise_repeat",
            "heterogeneous_nonmonotonic", "rare_rescue_harms", "high_direct_cost",
            "threshold_cost_positive", "threshold_cost_negative")
BETA = 0.05 / 1000


def require(condition: bool, context: str) -> None:
    if not condition:
        raise ValueError(f"independent review failed: {context}")


def close(actual, expected, context: str) -> None:
    require(bool(np.allclose(actual, expected, atol=2e-12, rtol=0, equal_nan=True)), context)


def hashed_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _actions(public: dict) -> tuple[list, np.ndarray]:
    confidence = np.array(public["confidence"])
    ordered = sorted(confidence)
    candidates = [-math.inf] + [ordered[math.ceil(q * len(ordered)) - 1]
                                for q in (1 / 8, 2 / 8, 3 / 8, 4 / 8, 5 / 8, 6 / 8, 7 / 8)] + [math.inf]
    thresholds, rows = [], []
    for threshold in candidates:
        row = tuple(bool(c < threshold) for c in confidence)
        if row not in rows:
            rows.append(row)
            thresholds.append("-inf" if threshold == -math.inf else "inf" if threshold == math.inf else float(threshold))
    return thresholds, np.array(rows, dtype=int)


def _means_from_purchased(public: dict, purchased: dict) -> tuple[np.ndarray, np.ndarray]:
    """Independent arithmetic of the frozen mean model, using purchased rows."""
    n = len(public["confidence"])
    c = public["confidence"]
    ordered = sorted(c)
    boundaries = [ordered[math.ceil(q * n) - 1] for q in (0.25, 0.5, 0.75)]
    strata = [sum(value >= boundary for boundary in boundaries) for value in c]
    direct = public["direct_correct"]
    cap = public["thinking_cap"]
    means, costs = np.empty(n), np.empty(n)
    for s in set(strata):
        indices = [i for i in range(n) if strata[i] == s]
        available = [(cell, outcome) for cell, outcome in purchased.items() if strata[cell[0]] == s]
        prior_p = (1 + sum(y for _, (y, _) in available)) / (2 + len(available))
        prior_c = (cap + sum(tokens for _, (_, tokens) in available)) / (2 + len(available))
        pairs = []
        first = {}
        for (i, _), (y, tokens) in available:
            first.setdefault(i, y - direct[i] - BETA * tokens)
        for i in indices:
            if (i, 0) in purchased and (i, 1) in purchased:
                y0, c0 = purchased[(i, 0)]
                y1, c1 = purchased[(i, 1)]
                pairs.append(((y0 - y1) - BETA * (c0 - c1))**2 / 2)
        within = max(1e-4, (0.4 + sum(pairs)) / (2 + len(pairs)))
        first_values = list(first.values())
        weight = max(len(first_values) - 1, 0)
        sample_var = sum((g - np.mean(first_values))**2 for g in first_values) / weight if weight else 0
        between = max(1e-4, (0.2 + weight * max(sample_var - within, 0)) / (2 + weight))
        for i in indices:
            acquired = [out for (state, _), out in purchased.items() if state == i]
            count = len(acquired)
            total = sum(y - direct[i] - BETA * tokens for y, tokens in acquired)
            variance = 1 / (1 / between + count / within)
            unbounded = variance * ((prior_p - direct[i] - BETA * prior_c) / between + total / within)
            means[i] = max(-direct[i] - BETA * cap, min(1 - direct[i], unbounded))
            costs[i] = (2 * prior_c + sum(tokens for _, tokens in acquired)) / (2 + count)
    return means, costs


def review_trajectory(trajectory: dict, truth: tuple[np.ndarray, np.ndarray] | None = None) -> dict:
    """Replay recorded arithmetic; no strategy randomizer or selector is called."""
    public = trajectory["public"]
    n = len(public["confidence"])
    cap = public["thinking_cap"]
    require(public["repeats"] == 2 and cap == 2562, "fixed two-draw/cap identity")
    for key in ("state_ids", "direct_job_ids"):
        require(len(public[key]) == n and len(set(public[key])) == n, "fixed unique state identities")
    thresholds, actions = _actions(public)
    require(trajectory["grid"] == {"thresholds": thresholds, "actions": actions.tolist()}, "training-only strict threshold grid")
    baseline = sum(d - BETA * c for d, c in zip(public["direct_correct"], public["direct_tokens"], strict=True)) / n
    cells = [(i, r) for i in range(n) for r in (0, 1)]
    purchased, reserved = {}, {}
    charged = sum(public["direct_tokens"])
    pending = []
    snapshot = None
    checkpoint_number = 0
    adaptive_count = 0
    in_audit = False
    direct_events = 0
    for index, event in enumerate(trajectory["trace"]):
        kind = event["kind"]
        if kind == "direct_charge":
            require(not purchased and event["tokens"] == charged and direct_events == 0, "common direct charge")
            direct_events += 1
        elif kind == "seed_sample":
            require(not purchased and not pending, "seed before purchase")
            pending = list(map(tuple, event["cells"]))
            require(len(set(i for i, _ in pending)) == len(pending), "seed distinct states")
            require(event["cells"] == trajectory["seed_cells"], "common seed log")
        elif kind == "adaptive_decision":
            require(not pending and not reserved and not in_audit, "selection after previous settle, before audit")
            remaining = [cell for cell in cells if cell not in purchased]
            require(event["observed_cells"] == list(map(list, purchased)), "decision purchased-only history")
            require(event["remaining_cells"] == list(map(list, remaining)), "decision fixed remaining cells")
            means, costs = _means_from_purchased(public, purchased)
            close(event["posterior"]["mean"], means, "purchased-only posterior means")
            close(event["posterior"]["cost"], costs, "purchased-only predicted cost")
            probability = event["state_probabilities"]
            close(sum(probability), 1, "normalized state probabilities")
            selected = tuple(event["chosen_cell"])
            require(selected in remaining and probability[selected[0]] > 0, "selected available cell")
            count = sum(i == selected[0] for i, _ in remaining)
            close(event["chosen_state_probability"], probability[selected[0]], "selected state probability")
            close(event["chosen_cell_given_state_probability"], 1 / count, "conditional cell probability")
            close(event["chosen_cell_probability"], probability[selected[0]] / count, "exact cell probability")
            require(charged + cap + min(4, len(remaining) - 1) * cap <= event["budget"], "adaptive audit holdout")
            if trajectory["method"] == "candidate_no_repeat":
                require(not any(i == selected[0] for i, _ in purchased), "no adaptive repeat removal")
            pending = [selected]
            adaptive_count += 1
        elif kind == "audit_snapshot":
            require(not pending and not reserved and not in_audit, "complete pre-audit purchase history")
            remaining = [cell for cell in cells if cell not in purchased]
            require(event["observed_cells"] == list(map(list, purchased)), "frozen pre-audit history")
            require(event["remaining_cells"] == list(map(list, remaining)), "frozen audit population")
            means, _ = _means_from_purchased(public, purchased)
            close(event["predictions"], means, "frozen joint-model audit predictions")
            pending = list(map(tuple, event["sample"]))
            require(len(pending) == min(4, len(remaining)) and len(set(pending)) == len(pending), "full fixed audit sample")
            require(set(pending).issubset(remaining), "audit only remaining cells")
            close(event["inclusion_probability"], len(pending) / len(remaining) if remaining else 1, "audit inclusion probability")
            close(event["ordered_cell_probabilities"], [1 / (len(remaining) - k) for k in range(len(pending))], "audit order probabilities")
            require(event["batch_reservation"] == len(pending) * cap, "audit batch cap")
            snapshot = (dict(purchased), remaining, np.array(event["predictions"]), list(pending), event)
            in_audit = True
        elif kind == "reserve":
            require(event["id"] not in reserved and event["tokens"] == cap, "full unique reservation")
            require(event["id"] in {f"{i}:{r}" for i, r in pending}, "reservation after frozen selection")
            require(charged + sum(reserved.values()) + cap <= event["budget"], "cap affordability without future cost")
            reserved[event["id"]] = cap
            require(event["charged"] == charged and event["reserved"] == sum(reserved.values()), "reserve ledger")
        elif kind == "reveal":
            cell = tuple(event["cell"])
            require(bool(pending) and cell == pending[0] and cell not in purchased, "one reveal for each selected cell")
            require(event["id"] in reserved, "cap exists before reveal")
            require(cell in cells, "fixed repeat cell identity")
            if in_audit:
                require(event["phase"] == "audit" and set(reserved) == {f"{i}:{r}" for i, r in pending}, "complete audit reserved before reveal")
            require(event["state_id"] == public["state_ids"][cell[0]] and event["direct_job_id"] == public["direct_job_ids"][cell[0]], "unchanged direct state across repeats")
            require(event["correct"] in (0, 1) and 1 <= event["tokens"] <= cap, "valid purchased outcome")
            if truth is not None:
                require(event["correct"] == int(truth[0][cell]) and event["tokens"] == int(truth[1][cell]), "purchased frozen synthetic outcome")
            purchased[cell] = (event["correct"], event["tokens"])
            pending.pop(0)
        elif kind == "settle":
            cell = tuple(map(int, event["id"].split(":")))
            require(cell in purchased and event["id"] in reserved, "settle purchased reservation")
            actual = purchased[cell][1]
            reserved.pop(event["id"])
            require(event["actual"] == actual and event["refund"] == cap - actual, "actual plus refund equals cap")
            charged += actual
            require(event["charged"] == charged and event["reserved"] == sum(reserved.values()), "settled cumulative charge")
        elif kind == "checkpoint":
            require(snapshot is not None and in_audit and not pending and not reserved, "completed whole audit")
            before, remaining, predictions, sample, audit_event = snapshot
            sums = np.zeros(n)
            rem_counts = np.zeros(n)
            for (i, _), (y, tokens) in before.items():
                sums[i] += y - public["direct_correct"][i] - BETA * tokens
            for i, _ in remaining:
                rem_counts[i] += 1
            estimates = baseline + actions @ (sums + rem_counts * predictions) / (n * 2)
            covariance = np.zeros((len(actions), len(actions)))
            if remaining:
                residuals = np.array([actions[:, i] * (purchased[(i, r)][0] - public["direct_correct"][i] - BETA * purchased[(i, r)][1] - predictions[i]) / (n * 2) for i, r in sample])
                estimates += len(remaining) / len(sample) * residuals.sum(axis=0)
                if len(sample) >= 2:
                    centered = residuals - residuals.mean(axis=0)
                    covariance = len(remaining)**2 * (1 - len(sample) / len(remaining)) / len(sample) * (centered.T @ centered / (len(sample) - 1))
                elif len(sample) < len(remaining):
                    covariance[:] = np.nan
            close(event["utility_estimates"], estimates, "independent finite-cell audit correction")
            close([[np.nan if x is None else x for x in row] for row in event["audit_covariance"]], covariance, "audit covariance arithmetic")
            maximum = max(estimates)
            selected = min(k for k, value in enumerate(estimates) if value >= maximum - 1e-12)
            counts = [sum(i == state for i, _ in purchased) for state in range(n)]
            require(event["selected_policy"] == selected, "minimum-escalation estimate maximizer")
            require(event["charged_tokens"] == charged <= event["budget"], "nested checkpoint charges")
            require(event["purchased_cells"] == len(purchased) and event["distinct_states"] == sum(c > 0 for c in counts) and event["repeat_count"] == sum(max(c - 1, 0) for c in counts), "equal-group repeat accounting")
            require(event["audit_count"] == len(sample) and event["stop"] == audit_event["stop"], "checkpoint audit metadata")
            require(event["trace_prefix_events"] == index, "frozen checkpoint trace prefix")
            cp = trajectory["checkpoints"][checkpoint_number]
            require(all(cp[key] == value for key, value in event.items() if key != "kind"), "immutable checkpoint versus trace")
            checkpoint_number += 1
            in_audit = False
        else:
            raise ValueError(f"unknown trace event {kind}")
    require(direct_events == 1 and not reserved and not pending and not in_audit, "complete settled trajectory")
    require(len(purchased) == trajectory["access_count"] and checkpoint_number == len(trajectory["checkpoints"]), "exact reveal/checkpoint count")
    utilities = [cp["evaluation"]["utility"] for cp in trajectory["checkpoints"]]
    if len(utilities) == 3:
        weighted = utilities[0] / 6 + utilities[1] / 2 + utilities[2] / 3
        close(trajectory["normalized_aulc"], weighted, "normalized trapezoid AULC")
    return {"purchases": len(purchased), "checkpoints": checkpoint_number, "adaptive_decisions": adaptive_count,
            "charged_tokens": charged}


def regenerate_synthetic(spec: dict, setting: str, seed: int, evaluation: bool) -> tuple[dict, np.ndarray, np.ndarray]:
    """Restore seeded synthetic arrays from the written distribution contract."""
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, SETTINGS.index(setting), int(evaluation)])))
    n = 512 if evaluation else 64
    parameters = spec["settings"][setting]
    confidence = rng.uniform(0.02, 0.98, n)
    direct = (rng.random(n) < parameters["pD"][0] + parameters["pD"][1] * confidence).astype(int)
    if "pT_below_above_half" in parameters:
        pthink = np.array([parameters["pT_below_above_half"][0 if c < 0.5 else 1] for c in confidence])
    elif "pT_below_above_point_one" in parameters:
        pthink = np.array([parameters["pT_below_above_point_one"][0 if c < 0.1 else 1] for c in confidence])
    elif "pT_quartile" in parameters:
        base = np.array([parameters["pT_quartile"][min(int(c * 4), 3)] for c in confidence])
        offsets = np.array(parameters["state_offset"])[rng.integers(2, size=n)]
        pthink = np.clip(base + offsets, *parameters["pT_clip"])
    else:
        pthink = np.full(n, parameters["pT"])
    uy, uc = rng.random((n, 2)), rng.random((n, 2))
    correct = (uy < pthink[:, None]).astype(int)
    association = parameters["association"]
    high = (uy < 0.5) if association == "positive" else (uy >= 0.5) if association == "negative" else (uc < 0.5)
    tokens = np.where(high, parameters["length"][1], parameters["length"][0])
    prefix = "evaluation" if evaluation else "training"
    public = {"confidence": confidence.tolist(), "direct_correct": direct.tolist(),
              "direct_tokens": [parameters.get("direct_tokens", 128)] * n,
              "state_ids": [f"{prefix}-{i}" for i in range(n)],
              "direct_job_ids": [f"{prefix}-direct-{i}" for i in range(n)], "repeats": 2, "thinking_cap": 2562}
    return public, correct, tokens


def descriptive(values: list[float]) -> dict:
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean)**2 for value in values) / (len(values) - 1)
    sd = math.sqrt(variance)
    margin = 1.6448536269514722 * sd / math.sqrt(len(values))
    return {"mean": mean, "sample_sd": sd,
            "approximate_90_percent_simulation_interval": [mean - margin, mean + margin],
            "positive_pairs": sum(value > 0 for value in values), "seeds": len(values)}


def verify_timing(rows: list[dict], timings: dict, interpretation: str) -> None:
    """Check recorded descriptive durations without timing or invoking work."""
    mapped = {(row["setting"], row["method"]): row for row in rows}
    require(len(mapped) == len(rows) and set(mapped) == set(timings), "each timing group once")
    for identity, values in timings.items():
        require(bool(values) and all(math.isfinite(value) and value >= 0 for value in values),
                "finite nonnegative recorded acquisition times")
        actual = mapped[identity]
        close(actual["mean_acquisition_elapsed_seconds"], math.fsum(values) / len(values), "descriptive timing mean")
        close(actual["minimum_acquisition_elapsed_seconds"], min(values), "descriptive timing minimum")
        close(actual["maximum_acquisition_elapsed_seconds"], max(values), "descriptive timing maximum")
        require(actual["trajectories"] == len(values) and actual["interpretation"] == interpretation,
                "descriptive timing count and scope")


def review(output: Path, root: Path) -> dict:
    plan = read_json(output / "plan.json")
    invocation = read_json(output / "invocation.json")
    finish = read_json(output / "finish.json")
    summary = read_json(output / "summary.json")
    plan_hash = hashed_bytes((output / "plan.json").read_bytes())
    spec = plan["spec"]
    require(plan["spec_sha256"] == hashed_bytes(encoded(spec)) == summary["spec_sha256"], "frozen specification hash")
    require(plan["output"] == str(output.resolve()), "prepared output identity")
    require(invocation["plan_sha256"] == finish["plan_sha256"] == plan_hash, "invocation and finish plan identity")
    require(finish["status"] in ("complete_pass", "complete_gate_failures"), "completed endpoint only")
    require(invocation["allowed_invocations"] == 1 and invocation["retries"] == finish["retries"] == 0, "one immutable invocation")
    require(invocation["source_revision"] == plan["source_revision"], "source revision identity")
    require(Path(invocation["prelaunch_review_file"]).name == invocation["prelaunch_review_file"], "prelaunch review inside prepared output")
    prelaunch = output / invocation["prelaunch_review_file"]
    require(hashed_bytes(prelaunch.read_bytes()) == invocation["prelaunch_review_sha256"], "prelaunch review preservation")
    approval = read_json(prelaunch)
    require(approval.get("status") == "pass" and approval.get("plan_sha256") == plan_hash
            and approval.get("engineering_checks_passed") is True
            and approval.get("unresolved_blockers") == [], "independent prelaunch approval")
    require(set(plan["source_sha256"]) == set(spec["source_files"]), "all frozen source pins")
    for relative, expected in plan["source_sha256"].items():
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "relative source pin")
        require(hashed_bytes((root / relative).read_bytes()) == expected, f"source pin {relative}")
    for relative, expected in finish["inventory_sha256"].items():
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "relative output pin")
        require(hashed_bytes((output / relative).read_bytes()) == expected, f"output preservation {relative}")
    require(spec["methods"] == list(METHODS) and spec["synthetic_seeds"] == list(range(2026100900, 2026100930)), "method and seed cap")
    require(spec["budgets"] == [64000, 128000, 256000], "fixed nested budgets")
    require(spec["runtime_seconds"] == 1200 and spec["artifact_bytes_limit"] == 536870912,
            "frozen runtime and artifact ceilings")
    require(max(finish["elapsed_wall_seconds"], finish["elapsed_monotonic_seconds"]) < 1200,
            "completed invocation within runtime ceiling")
    require(finish["artifact_bytes_before_finish"] <= spec["artifact_bytes_limit"], "artifact ceiling")
    totals = {"purchases": 0, "checkpoints": 0, "trajectories": 0, "adaptive_decisions": 0}
    values, curves, expected_rows, timings = {}, {}, {}, {}
    physical_train = physical_eval = 0
    paths = []
    for setting in SETTINGS:
        for seed in spec["synthetic_seeds"]:
            path = output / "traces" / f"{setting}-{seed}.json.gz"
            paths.append(str(path.relative_to(output)))
            result = json.loads(gzip.decompress(path.read_bytes()))
            require(result["setting"] == setting and result["seed"] == seed, "paired seed/setting identity")
            require([t["method"] for t in result["trajectories"]] == list(METHODS), "all nine trajectories")
            train, train_y, train_c = regenerate_synthetic(spec, setting, seed, False)
            evaluation, eval_y, eval_c = regenerate_synthetic(spec, setting, seed, True)
            for prefix, public, y, c in (("training", train, train_y, train_c), ("evaluation", evaluation, eval_y, eval_c)):
                require(result[f"{prefix}_cache_hash"] == hashed_bytes(encoded({"public": public, "correct": y.tolist(), "tokens": c.tolist()})), "separate seeded cache identity")
                require(result[f"physical_{prefix}_cache_tokens"] == sum(public["direct_tokens"]) + int(c.sum()), "physical full-cache cost")
            physical_train += result["physical_training_cache_tokens"]
            physical_eval += result["physical_evaluation_cache_tokens"]
            common_seed = result["trajectories"][0]["seed_cells"]
            require(len(common_seed) == 8, "eight common initial states")
            seed_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, SETTINGS.index(setting), 2])))
            states = seed_rng.permutation(64)[:8]
            expected_seed = [[int(i), int(seed_rng.integers(2))] for i in states]
            require(common_seed == expected_seed, "outcome-independent frozen common seed")
            particle_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, SETTINGS.index(setting), 4])))
            close(result["particle_z"], particle_rng.standard_normal((32, 64)), "pre-outcome fixed particle normals")
            for trajectory in result["trajectories"]:
                require(trajectory["public"] == train and trajectory["seed_cells"] == common_seed, "matched common public states/seed")
                checked = review_trajectory(trajectory, (train_y, train_c))
                require([cp["budget"] for cp in trajectory["checkpoints"]] == spec["budgets"], "three endpoint checkpoints")
                for key in ("purchases", "checkpoints", "adaptive_decisions"):
                    totals[key] += checked[key]
                totals["trajectories"] += 1
                method = trajectory["method"]
                values[(setting, method, seed)] = trajectory["normalized_aulc"]
                timings.setdefault((setting, method), []).append(trajectory["acquisition_elapsed_seconds"])
                _, actions = _actions(train)
                full_gains = train_y - np.array(train["direct_correct"])[:, None] - BETA * train_c
                true_values = np.mean(np.array(train["direct_correct"]) - BETA * np.array(train["direct_tokens"])) + actions @ full_gains.sum(axis=1) / 128
                for cp in trajectory["checkpoints"]:
                    threshold = trajectory["grid"]["thresholds"][cp["selected_policy"]]
                    threshold_float = float(threshold)
                    action = np.array(evaluation["confidence"]) < threshold_float
                    direct = np.array(evaluation["direct_correct"])
                    scored = np.where(action[:, None], eval_y, direct[:, None])
                    deployed = np.array(evaluation["direct_tokens"])[:, None] + action[:, None] * eval_c
                    metrics = {"utility": float(np.mean(scored - BETA * deployed)), "accuracy": float(np.mean(scored)),
                               "deployment_tokens": float(np.mean(deployed)), "escalation_fraction": float(np.mean(action)),
                               "direct_accuracy": float(np.mean(direct)), "thinking_accuracy": float(np.mean(eval_y)),
                               "groups": 512, "draws_per_group": 2}
                    require(set(metrics) == set(cp["evaluation"]), "held-out metric keys")
                    for key, expected in metrics.items():
                        close(cp["evaluation"][key], expected, f"independent held-out {key}")
                    close(cp["fixed_policy_cache_errors"], np.array(cp["utility_estimates"]) - true_values, "fixed-policy cache errors")
                    curves.setdefault((setting, method, cp["budget"]), []).append(cp)
                    expected_rows[(setting, method, seed, cp["budget"])] = {"setting": setting, "method": method,
                        "seed": seed, "selected_threshold": threshold, "normalized_aulc": trajectory["normalized_aulc"], **cp}
    require(set(paths) == {relative for relative in finish["inventory_sha256"] if relative.startswith("traces/")}, "complete output trace inventory")
    require(finish["completed_seed_settings"] == 240 and totals["trajectories"] == 2160 and totals["checkpoints"] == 6480, "bounded complete endpoint")
    require(summary["engineering"]["actual_trace_checks"] == {key: totals[key] for key in ("purchases", "checkpoints", "trajectories")}, "reported engineering totals")
    require(len(summary["rows"]) == len(expected_rows), "summary row count")
    for row in summary["rows"]:
        identity = (row["setting"], row["method"], row["seed"], row["budget"])
        require(identity in expected_rows and row == expected_rows.pop(identity), "exact metric row from immutable trace")
    require(not expected_rows, "each metric row once")
    method_rows = {(row["setting"], row["method"]): row for row in summary["method_aulc"]}
    curve_rows = {(row["setting"], row["method"], row["budget"]): row for row in summary["learning_curves"]}
    require(len(method_rows) == len(summary["method_aulc"]) == 72, "all method AULCs once")
    require(len(curve_rows) == len(summary["learning_curves"]) == 216, "all learning curves once")
    verify_timing(summary["acquisition_overhead"], timings, spec["acquisition_timing"])
    for setting in SETTINGS:
        for method in METHODS:
            expected = descriptive([values[(setting, method, seed)] for seed in spec["synthetic_seeds"]])
            for key, value in expected.items():
                close(method_rows[(setting, method)][key], value, "independent method AULC summary")
            for budget in spec["budgets"]:
                checkpoints = curves[(setting, method, budget)]
                expected = descriptive([cp["evaluation"]["utility"] for cp in checkpoints])
                expected["mean_charged_tokens"] = math.fsum(cp["charged_tokens"] for cp in checkpoints) / 30
                for key, value in expected.items():
                    close(curve_rows[(setting, method, budget)][key], value, "independent fixed-budget curve")
    contrasts = {(row["setting"], row["comparator"]): row for row in summary["candidate_contrasts"]}
    require(len(contrasts) == len(summary["candidate_contrasts"]) == 64, "all candidate comparisons once")
    primary = []
    for setting in SETTINGS:
        for comparator in METHODS:
            if comparator == "candidate":
                continue
            actual = contrasts[(setting, comparator)]
            differences = [values[(setting, "candidate", seed)] - values[(setting, comparator, seed)] for seed in spec["synthetic_seeds"]]
            close(actual["paired_differences"], differences, "paired seed differences")
            expected = descriptive(differences)
            for key, value in expected.items():
                close(actual[key], value, "independent paired contrast interval")
            is_primary = setting in ("high_noise_repeat", "threshold_cost_negative") and comparator in ("uniform_coverage", "closest_cost_aware")
            require(actual["primary"] == is_primary and actual["mean_screen"] == (expected["mean"] >= 0.005) and actual["positive_pair_screen"] == (expected["positive_pairs"] >= 20), "frozen practical screen")
            if is_primary:
                primary.append(actual)
    scientific_gate = all(row["mean_screen"] and row["positive_pair_screen"] for row in primary)
    require(len(primary) == 4 and summary["engineering"]["pass"] is True, "primary endpoint and engineering marker")
    require(summary["gate_pass"] == finish["gate_pass"] == scientific_gate, "terminal screen identity")
    require(finish["status"] == ("complete_pass" if scientific_gate else "complete_gate_failures"), "engineering versus screen status")
    require(summary["physical_training_cache_tokens"] == physical_train and summary["physical_evaluation_cache_tokens"] == physical_eval, "physical cache totals")
    return {"schema": "independent-threshold-acquisition-g1-review-v1", "status": "pass", "plan_sha256": plan_hash,
            "summary_sha256": hashed_bytes((output / "summary.json").read_bytes()),
            "finish_sha256": hashed_bytes((output / "finish.json").read_bytes()), "source_revision": plan["source_revision"],
            "source_pins_checked": len(plan["source_sha256"]), "output_pins_checked": len(finish["inventory_sha256"]),
            **totals, "metric_rows": 6480, "paired_contrasts": 64, "scientific_screen_pass": scientific_gate,
            "primary": primary, "scope": "read_only_new_synthetic_artifacts;independent_arithmetic;no_acquisition_fitting_model_reference_network"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Optional NEW immutable review JSON; omit to print only")
    args = parser.parse_args()
    result = review(args.study.resolve(), args.root.resolve())
    if args.output is not None:
        with args.output.open("xb") as handle:
            handle.write(encoded(result))
            handle.flush()
            os.fsync(handle.fileno())
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
