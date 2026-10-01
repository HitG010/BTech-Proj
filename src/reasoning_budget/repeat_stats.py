"""Gold-free, question-grouped diagnostics for an eight-draw repeat panel.

Correctness arrays are supplied by a separately authorized scorer. This module
never reads responses, gold, or a generation run.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

ANALYSIS = {
    "version": "repeat-signal-v1",
    "lambda": 0.05,
    "halves": {"A": [0, 1, 2, 3], "B": [4, 5, 6, 7]},
    "train_draws": [1, 2, 4],
    "full_draws_secondary": 8,
    "inner_question_folds": 4,
    "alphas": [1.0, 10.0, 100.0],
    "bootstrap_draws": 2000,
    "bootstrap_seed": 20261002,
    "interval": [0.05, 0.95],
    "minimum_utility_gain": 0.01,
    "minimum_informative_questions": 10,
    "baselines": ["accept", "escalate", "confidence"],
    "learners": ["question_only", "solver_only", "combined"],
    "gate_learner": "combined",
    "scope": "diagnostic; fixed out-of-fold fits; no multiplicity or novelty claim",
}


def _ci(question_values, spec):
    values = np.asarray(question_values, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Bootstrap needs finite per-question values")
    rng = np.random.default_rng(spec["bootstrap_seed"])
    draws = rng.integers(0, len(values), size=(spec["bootstrap_draws"], len(values)))
    return [float(x) for x in np.quantile(values[draws].mean(1), spec["interval"])]


def _validate(question_ids, question_features, direct, thinking, draft_features, folds, spec):
    ids = list(question_ids)
    if len(ids) < 10 or len(set(ids)) != len(ids) or any(not isinstance(q, str) for q in ids):
        raise ValueError("Need at least ten unique question IDs")
    q = np.asarray(question_features, dtype=float)
    d, t = np.asarray(direct, dtype=float), np.asarray(thinking, dtype=float)
    z = np.asarray(draft_features, dtype=float)
    if q.ndim != 2 or q.shape[0] != len(ids) or not q.shape[1]:
        raise ValueError("Invalid question feature shape")
    if d.shape != (len(ids), 8, 3) or t.shape != d.shape or z.shape != (len(ids), 8, 4):
        raise ValueError("Expected eight paired draws and four draft features per question")
    if not all(np.isfinite(a).all() for a in (q, d, t, z)):
        raise ValueError("Non-finite repeat data")
    if not all(np.isin(a[:, :, 0], [0, 1]).all() for a in (d, t)):
        raise ValueError("Correctness must be binary")
    if any((a[:, :, 1:] < 0).any() for a in (d, t)):
        raise ValueError("Tokens and seconds must be nonnegative")
    if set(folds) != set(ids) or any(type(folds[qid]) is not int or folds[qid] not in range(5) for qid in ids):
        raise ValueError("Fold map must assign every question to one of five folds")
    if any(sum(folds[qid] == fold for qid in ids) == 0 for fold in range(5)):
        raise ValueError("Every outer fold needs held-out questions")
    if spec["halves"] != ANALYSIS["halves"] or spec["train_draws"] != [1, 2, 4]:
        raise ValueError("Unsupported draw partition")
    if spec["inner_question_folds"] != 4 or spec["full_draws_secondary"] != 8:
        raise ValueError("Unsupported fold or full-draw plan")
    if not np.isfinite(spec["lambda"]) or spec["lambda"] < 0:
        raise ValueError("Invalid cost preference")
    return ids, q, d, t, z


def _features(kind, q, z):
    if kind == "question_only":
        return np.broadcast_to(q[:, None, :], (len(q), 8, q.shape[1]))
    if kind == "solver_only":
        return z
    if kind == "combined":
        return np.concatenate([_features("question_only", q, z), z], axis=2)
    raise ValueError(f"Unknown feature family: {kind}")


def _fit_ridge(x, gain, questions, draws, alpha):
    raw = x[np.ix_(questions, draws)].reshape(-1, x.shape[-1])
    target = gain[np.ix_(questions, draws)].ravel()
    scaler = StandardScaler().fit(raw)
    model = Ridge(alpha=alpha, solver="svd").fit(scaler.transform(raw), target)
    return scaler, model


def _ridge_actions(model, x, questions, draws):
    scaler, regressor = model
    raw = x[np.ix_(questions, draws)].reshape(-1, x.shape[-1])
    return (regressor.predict(scaler.transform(raw)).reshape(len(questions), len(draws)) > 0)


def _rows(d, t, questions, draws, decisions, preference):
    direct = d[np.ix_(questions, draws)]
    thinking = t[np.ix_(questions, draws)]
    chosen = np.where(decisions, thinking[:, :, 0], direct[:, :, 0])
    tokens = direct[:, :, 1] + decisions * thinking[:, :, 1]
    seconds = direct[:, :, 2] + decisions * thinking[:, :, 2]
    return {
        "accuracy": chosen.mean(1),
        "tokens": tokens.mean(1),
        "seconds": seconds.mean(1),
        "utility": (chosen - preference * tokens / 1000).mean(1),
        "escalation_rate": decisions.mean(1),
    }


def _confidence_threshold(z, d, t, questions, draws, preference):
    confidence = z[np.ix_(questions, draws, [0])][:, :, 0]
    values = np.unique(confidence)
    candidates = [float(values[0] - 1), *values.tolist(), float(values[-1] + 1)]
    best_score, best = -np.inf, None
    for threshold in candidates:
        score = float(_rows(d, t, questions, draws, confidence < threshold, preference)["utility"].mean())
        if score > best_score + 1e-12:
            best_score, best = score, threshold
    return best


def _inner_splits(questions, seed, count):
    questions = np.asarray(questions, dtype=int)
    if len(questions) < count:
        raise ValueError("Too few outer-training questions for inner folds")
    return [(questions[a], questions[b]) for a, b in KFold(count, shuffle=True, random_state=seed).split(questions)]


def _fit_fold(q, z, d, t, gain, train, test, train_draws, eval_draws, spec, seed):
    kinds = spec["learners"]
    features = {kind: _features(kind, q, z) for kind in kinds}
    splits = _inner_splits(train, seed, spec["inner_question_folds"])
    inner_scores = {name: [] for name in [*spec["baselines"], *kinds]}
    alpha_scores = {kind: {alpha: [] for alpha in spec["alphas"]} for kind in kinds}
    for inner_train, inner_test in splits:
        # Inner validation questions are distinct, but their labels must still
        # come from the acquired training draws. The opposite half is reserved
        # for the outer held-out endpoint.
        truth = d[np.ix_(inner_test, train_draws)]
        shape = truth.shape[:2]
        for name, decision in [("accept", False), ("escalate", True)]:
            actions = np.full(shape, decision, dtype=bool)
            inner_scores[name].extend(_rows(d, t, inner_test, train_draws, actions, spec["lambda"])["utility"])
        threshold = _confidence_threshold(z, d, t, inner_train, train_draws, spec["lambda"])
        actions = z[np.ix_(inner_test, train_draws, [0])][:, :, 0] < threshold
        inner_scores["confidence"].extend(_rows(d, t, inner_test, train_draws, actions, spec["lambda"])["utility"])
        for kind in kinds:
            for alpha in spec["alphas"]:
                fitted = _fit_ridge(features[kind], gain, inner_train, train_draws, alpha)
                actions = _ridge_actions(fitted, features[kind], inner_test, train_draws)
                alpha_scores[kind][alpha].extend(_rows(d, t, inner_test, train_draws, actions, spec["lambda"])["utility"])
    settings = {}
    for kind in kinds:
        alpha = max(spec["alphas"], key=lambda value: (np.mean(alpha_scores[kind][value]), value))
        settings[kind] = float(alpha)
        inner_scores[kind] = alpha_scores[kind][alpha]
    baseline = max(spec["baselines"], key=lambda name: np.mean(inner_scores[name]))
    threshold = _confidence_threshold(z, d, t, train, train_draws, spec["lambda"])
    decisions = {
        "accept": np.zeros((len(test), len(eval_draws)), dtype=bool),
        "escalate": np.ones((len(test), len(eval_draws)), dtype=bool),
        "confidence": z[np.ix_(test, eval_draws, [0])][:, :, 0] < threshold,
    }
    for kind in kinds:
        model = _fit_ridge(features[kind], gain, train, train_draws, settings[kind])
        decisions[kind] = _ridge_actions(model, features[kind], test, eval_draws)
    return baseline, settings, threshold, decisions, {name: float(np.mean(values)) for name, values in inner_scores.items()}


def _run_condition(ids, q, z, d, t, gain, folds, name, train_draws, eval_draws, spec):
    policies = [*spec["baselines"], *spec["learners"], "selected_baseline"]
    per_question = {qid: {"fold": folds[qid], "policies": {}} for qid in ids}
    fold_details = []
    for fold in range(5):
        train = np.array([i for i, qid in enumerate(ids) if folds[qid] != fold], dtype=int)
        test = np.array([i for i, qid in enumerate(ids) if folds[qid] == fold], dtype=int)
        baseline, settings, threshold, decisions, inner_scores = _fit_fold(
            q, z, d, t, gain, train, test, train_draws, eval_draws, spec,
            spec["bootstrap_seed"] + fold,
        )
        decisions["selected_baseline"] = decisions[baseline]
        acquired_direct = d[np.ix_(train, train_draws)]
        acquired_thinking = t[np.ix_(train, train_draws)]
        fold_details.append({
            "fold": fold, "train_ids": [ids[i] for i in train], "test_ids": [ids[i] for i in test],
            "selected_baseline": baseline, "alphas": settings,
            "confidence_threshold": float(threshold), "inner_utility": inner_scores,
            "training_acquisition": {
                "paired_draws": int(len(train) * len(train_draws)),
                "responses": int(2 * len(train) * len(train_draws)),
                "direct_tokens": float(acquired_direct[:, :, 1].sum()),
                "thinking_tokens": float(acquired_thinking[:, :, 1].sum()),
                "total_tokens": float(acquired_direct[:, :, 1].sum() + acquired_thinking[:, :, 1].sum()),
                "direct_seconds": float(acquired_direct[:, :, 2].sum()),
                "thinking_seconds": float(acquired_thinking[:, :, 2].sum()),
            },
        })
        for policy in policies:
            rows = _rows(d, t, test, eval_draws, decisions[policy], spec["lambda"])
            for j, index in enumerate(test):
                per_question[ids[index]]["policies"][policy] = {
                    metric: float(values[j]) for metric, values in rows.items()
                } | {"decisions": [bool(v) for v in decisions[policy][j]]}
    summary = {}
    for policy in policies:
        values = {
            metric: np.array([per_question[qid]["policies"][policy][metric] for qid in ids])
            for metric in ("accuracy", "tokens", "seconds", "utility", "escalation_rate")
        }
        summary[policy] = {
            f"mean_{metric}": float(value.mean()) for metric, value in values.items()
        } | {"ci90": _ci(values["utility"], spec)}
    deltas = np.array([
        per_question[qid]["policies"][spec["gate_learner"]]["utility"]
        - per_question[qid]["policies"]["selected_baseline"]["utility"] for qid in ids
    ])
    return {
        "name": name, "train_draws": list(train_draws), "evaluation_draws": list(eval_draws),
        "folds": fold_details, "per_question": per_question, "summary": summary,
        "combined_minus_baseline": {"mean": float(deltas.mean()), "ci90": _ci(deltas, spec)},
    }, deltas


def _reproducibility(ids, gain, spec):
    a = gain[:, spec["halves"]["A"]]
    b = gain[:, spec["halves"]["B"]]
    rows = {}
    for k in spec["train_draws"]:
        left, right = a[:, :k].mean(1), b[:, :k].mean(1)
        baseline_left = (left.sum() - left) / (len(ids) - 1)
        baseline_right = (right.sum() - right) / (len(ids) - 1)
        improvement = (
            ((right - baseline_left) ** 2 - (right - left) ** 2)
            + ((left - baseline_right) ** 2 - (left - right) ** 2)
        ) / 2
        rows[str(k)] = {
            "per_question": {qid: float(value) for qid, value in zip(ids, improvement)},
            "mean_mse_improvement": float(improvement.mean()), "ci90": _ci(improvement, spec),
            "mean_absolute_half_difference": float(np.abs(left - right).mean()),
        }
    full_mean = gain.mean(1)
    full_sd = gain.std(1, ddof=1)
    half_difference = a.mean(1) - b.mean(1)
    rows["8_descriptive"] = {
        "per_question": {
            qid: {
                "mean_gain": float(full_mean[i]),
                "within_question_gain_sd": float(full_sd[i]),
                "a4_minus_b4": float(half_difference[i]),
            }
            for i, qid in enumerate(ids)
        },
        "mean_within_question_gain_sd": float(full_sd.mean()),
        "mean_absolute_a4_b4_difference": float(np.abs(half_difference).mean()),
    }
    return rows


def _label_diagnostics(ids, d, t, spec):
    """Describe acquired labels without using an evaluation half for tuning."""
    diagnostics = {}
    for k in spec["train_draws"]:
        postdirect_by_half = {}
        for half, indices in spec["halves"].items():
            draws = indices[:k]
            direct = d[:, draws]
            thinking = t[:, draws]
            accuracy_delta = thinking[:, :, 0] - direct[:, :, 0]
            standalone = (
                accuracy_delta - spec["lambda"] *
                (thinking[:, :, 1] - direct[:, :, 1]) / 1000
            ).mean(1)
            postdirect = (
                accuracy_delta - spec["lambda"] * thinking[:, :, 1] / 1000
            ).mean(1)
            postdirect_by_half[half] = postdirect
            standalone_sign, postdirect_sign = np.sign(standalone), np.sign(postdirect)
            diagnostics[f"k{k}_{half}"] = {
                "draws": list(draws),
                "direct_accuracy": float(direct[:, :, 0].mean()),
                "thinking_accuracy": float(thinking[:, :, 0].mean()),
                "mean_direct_tokens": float(direct[:, :, 1].mean()),
                "mean_thinking_tokens": float(thinking[:, :, 1].mean()),
                "mean_direct_seconds": float(direct[:, :, 2].mean()),
                "mean_thinking_seconds": float(thinking[:, :, 2].mean()),
                "mean_standalone_gain": float(standalone.mean()),
                "mean_postdirect_gain": float(postdirect.mean()),
                "sign_agreement_with_ties": float((standalone_sign == postdirect_sign).mean()),
                "standalone_sign_counts": {
                    label: int(np.count_nonzero(standalone_sign == sign))
                    for label, sign in [("negative", -1), ("tie", 0), ("positive", 1)]
                },
                "postdirect_sign_counts": {
                    label: int(np.count_nonzero(postdirect_sign == sign))
                    for label, sign in [("negative", -1), ("tie", 0), ("positive", 1)]
                },
                "per_question": {
                    qid: {
                        "standalone_gain": float(standalone[i]),
                        "postdirect_gain": float(postdirect[i]),
                        "signs_agree": bool(standalone_sign[i] == postdirect_sign[i]),
                    }
                    for i, qid in enumerate(ids)
                },
            }
        a_sign = np.sign(postdirect_by_half["A"])
        b_sign = np.sign(postdirect_by_half["B"])
        diagnostics[f"k{k}_postdirect_A_B"] = {
            "sign_agreement_with_ties": float((a_sign == b_sign).mean()),
            "both_tie": int(np.count_nonzero((a_sign == 0) & (b_sign == 0))),
            "one_tie": int(np.count_nonzero((a_sign == 0) != (b_sign == 0))),
            "opposite_nonzero": int(np.count_nonzero(a_sign * b_sign < 0)),
            "same_nonzero": int(np.count_nonzero((a_sign == b_sign) & (a_sign != 0))),
            "per_question": {
                qid: {
                    "a_gain": float(postdirect_by_half["A"][i]),
                    "b_gain": float(postdirect_by_half["B"][i]),
                    "signs_agree": bool(a_sign[i] == b_sign[i]),
                }
                for i, qid in enumerate(ids)
            },
        }
    return diagnostics


def analyze(question_ids, question_features, direct, thinking, draft_features, folds, spec=ANALYSIS):
    """Return JSON-native diagnostics; folds and sample IDs must be frozen first."""
    spec = deepcopy(spec)
    ids, q, d, t, z = _validate(question_ids, question_features, direct, thinking, draft_features, folds, spec)
    gain = t[:, :, 0] - d[:, :, 0] - spec["lambda"] * t[:, :, 1] / 1000
    conditions, deltas = {}, {}
    for k in spec["train_draws"]:
        for replica, train_half, eval_half in [("A_to_B", "A", "B"), ("B_to_A", "B", "A")]:
            name = f"k{k}_{replica}"
            result, delta = _run_condition(
                ids, q, z, d, t, gain, folds, name,
                spec["halves"][train_half][:k], spec["halves"][eval_half], spec,
            )
            conditions[name], deltas[name] = result, delta
    result, delta = _run_condition(ids, q, z, d, t, gain, folds, "k8_full",
                                   list(range(8)), list(range(8)), spec)
    conditions["k8_full"], deltas["k8_full"] = result, delta
    repro = _reproducibility(ids, gain, spec)
    k4 = (deltas["k4_A_to_B"] + deltas["k4_B_to_A"]) / 2
    informative = int(np.any(d[:, :, 0] != t[:, :, 0], axis=1).sum())
    rescue = (d[:, :, 0] == 0) & (t[:, :, 0] == 1)
    harm = (d[:, :, 0] == 1) & (t[:, :, 0] == 0)
    gates = {
        "independent_half_reproducibility": repro["4"]["mean_mse_improvement"] > 0 and repro["4"]["ci90"][0] > 0,
        "k4_both_replica_point_gains": all(conditions[name]["combined_minus_baseline"]["mean"] > 0 for name in ("k4_A_to_B", "k4_B_to_A")),
        "k4_mean_gain_and_interval": float(k4.mean()) >= spec["minimum_utility_gain"] and _ci(k4, spec)[0] > 0,
        "full8_nonreversal": conditions["k8_full"]["combined_minus_baseline"]["mean"] >= 0,
        "informative_questions": informative >= spec["minimum_informative_questions"],
    }
    return {
        "analysis": spec, "question_count": len(ids), "informative_questions": informative,
        "paired_outcome_states": {
            "rescue_draws": int(rescue.sum()),
            "rescue_questions": int(np.any(rescue, axis=1).sum()),
            "harm_draws": int(harm.sum()),
            "harm_questions": int(np.any(harm, axis=1).sum()),
        },
        "reproducibility": repro, "label_diagnostics": _label_diagnostics(ids, d, t, spec),
        "conditions": conditions,
        "k4_average_delta": {"mean": float(k4.mean()), "ci90": _ci(k4, spec)},
        "gates": gates, "scale_acquisition": all(gates.values()),
        "limitations": ["Diagnostic, not confirmation; clustered intervals condition on fixed OOF fits.",
                        "Eight draws have no independent same-question eight-draw replica."],
    }
