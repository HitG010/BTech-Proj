"""First-draft routing with explicit rescue, regression, and continuation costs.

Prediction receives only a question and one already-paid-for direct response.
Counterfactual observations are confined to training and replay evaluation.
"""

import numpy as np
from scipy.special import expit, softmax
from sklearn.linear_model import LogisticRegression, Ridge

from .scoring import parse_answer
from .stronger import fit_transform, transform

PREFERENCES = (0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
PRIMARY = 0.05
FEATURES = ["decoder_mean_logprob", "log_answer_tokens", "parse_valid", "truncated"]
SETTINGS = [{"C": c, "alpha": a} for c in (0.1, 1, 10) for a in (1, 10, 100)]


def first_features(result):
    """No scores, gold, second draft, or thinking response enter this interface."""
    confidence = result["mean_generated_logprob"]
    if confidence is None or not np.isfinite(confidence):
        raise ValueError("First-draft routing requires finite decoder log-probability")
    answer, _ = parse_answer(result["final_answer"], incomplete=result["answer_truncated"])
    return [
        confidence,
        np.log1p(result["answer_tokens"]),
        float(answer is not None),
        float(result["answer_truncated"]),
    ]


def state_features(question_features, direct_results):
    """Order is question-major, then first-draft orientation 0/1."""
    if len(question_features) != len(direct_results) or any(len(r) < 2 for r in direct_results):
        raise ValueError("Two first-draft orientations are required for every question")
    first = np.array([first_features(r[s]) for r in direct_results for s in (0, 1)])
    return np.column_stack([np.repeat(question_features, 2, axis=0), first])


def continuation_rows(data):
    """[question, first orientation, action, accuracy/tokens/seconds].

    Actions: accept first; buy second then think on disagreement; think now.
    All consumed calls count, including the first draft and unsuccessful probes.
    """
    direct, thinking = data["direct"], data["thinking"]
    if direct.shape[1] < 2 or thinking.shape[1] != 2:
        raise ValueError("Replay requires at least two direct and exactly two thinking samples")
    n = len(direct)
    rows = np.empty((n, 2, 3, 3))
    for s in (0, 1):
        rows[:, s, 0] = direct[:, s]
        agree = np.array([a[0] is not None and a[0] == a[1] for a in data["answers"]])
        rows[:, s, 1, 0] = np.where(agree, direct[:, s, 0], thinking[:, s, 0])
        rows[:, s, 1, 1:] = direct[:, :2, 1:].sum(1) + (~agree)[:, None] * thinking[:, s, 1:]
        rows[:, s, 2, 0] = thinking[:, s, 0]
        rows[:, s, 2, 1:] = direct[:, s, 1:] + thinking[:, s, 1:]
    return rows


def dart_sc3(data):
    """DART SC branch: two unanimous drafts, third-draft majority, else thinking.

    Same allowance/decoder adaptation as the other policies; not SC-Budget.
    Invalid answers never establish agreement. Ties fall back to thinking.
    """
    if data["direct"].shape[1] != 3:
        raise ValueError("DART SC-3 needs a third direct draft")
    rows = []
    for i, answers in enumerate(data["answers"]):
        orientations = []
        for s in (0, 1):
            order = [s, 1 - s, 2]
            first_two = [answers[j] for j in order[:2]]
            consumed = 2
            winner = s if first_two[0] is not None and first_two[0] == first_two[1] else None
            if winner is None:
                consumed = 3
                winner = next(
                    (
                        j
                        for j in order
                        if answers[j] is not None
                        and sum(answers[k] == answers[j] for k in order) >= 2
                    ),
                    None,
                )
            cost = data["direct"][i, :consumed, 1:].sum(0)
            if winner is None:
                output = data["thinking"][i, s]
                cost = cost + output[1:]
            else:
                output = data["direct"][i, winner]
            orientations.append(np.r_[output[0], cost])
        rows.append(np.mean(orientations, axis=0))
    return np.array(rows)


def selected_rows(rows, actions):
    actions = np.asarray(actions)
    if actions.shape != (len(rows) * 2,) or not np.isin(actions, [0, 1, 2]).all():
        raise ValueError("One valid action is required for each first-draft state")
    states = rows.reshape(-1, 3, 3)
    return states[np.arange(len(states)), actions].reshape(-1, 2, 3).mean(1)


def fit(x, rows, setting, kind="joint", response_only=False):
    if kind not in {"joint", "gain-ridge"} or setting not in SETTINGS:
        raise ValueError("Unsupported model or setting")
    raw = np.asarray(x)[:, -4:] if response_only else np.asarray(x)
    z, state = fit_transform(raw, None if response_only else 16)
    outcomes = rows.reshape(-1, 3, 3)
    if len(z) != len(outcomes):
        raise ValueError("State and training target counts differ")
    baseline = outcomes[:, 0, 0].astype(int)
    heads = []
    for action in (1, 2):
        current = outcomes[:, action, 0].astype(int)
        extra_cost = outcomes[:, action, 1] - outcomes[:, 0, 1]
        reg = Ridge(alpha=setting["alpha"], solver="svd").fit(z, extra_cost)
        head = {"cost_coef": reg.coef_.tolist(), "cost_intercept": float(reg.intercept_)}
        if kind == "joint":
            # 0=still wrong, 1=rescue, 2=regression, 3=still correct.
            labels = 2 * baseline + current
            classes = np.unique(labels)
            head["classes"] = classes.tolist()
            if len(classes) > 1:
                classifier = LogisticRegression(C=setting["C"], max_iter=3000).fit(z, labels)
                if max(classifier.n_iter_) >= 3000:
                    raise ValueError("Continuation classifier did not converge")
                head.update(
                    coef=classifier.coef_.tolist(), intercept=classifier.intercept_.tolist()
                )
        else:
            reg = Ridge(alpha=setting["alpha"], solver="svd").fit(z, current - baseline)
            head.update(coef=reg.coef_.tolist(), intercept=float(reg.intercept_))
        heads.append(head)
    return {
        "kind": kind,
        "setting": setting,
        "response_only": response_only,
        "transform": state,
        "heads": heads,
        "feature_schema": FEATURES,
    }


def predictions(model, x, ignore_harm=False):
    raw = np.asarray(x)[:, -4:] if model["response_only"] else np.asarray(x)
    z = transform(raw, model["transform"])
    gains, costs = [], []
    for head in model["heads"]:
        costs.append(np.maximum(1, z @ head["cost_coef"] + head["cost_intercept"]))
        if model["kind"] == "joint":
            classes = head["classes"]
            probabilities = np.ones((len(z), 1))
            if len(classes) > 1:
                logits = z @ np.asarray(head["coef"]).T + head["intercept"]
                probabilities = (
                    np.column_stack([1 - expit(logits[:, 0]), expit(logits[:, 0])])
                    if len(classes) == 2
                    else softmax(logits, axis=1)
                )
            joint = np.zeros((len(z), 4))
            joint[:, classes] = probabilities
            gains.append(joint[:, 1] - (0 if ignore_harm else joint[:, 2]))
        else:
            gains.append(np.clip(z @ head["coef"] + head["intercept"], -1, 1))
    return np.column_stack(gains), np.column_stack(costs)


def actions(model, x, preference, *, binary=False, ignore_harm=False):
    if not np.isfinite(preference) or preference < 0:
        raise ValueError("Preference must be finite and nonnegative")
    gain, cost = predictions(model, x, ignore_harm)
    utility = gain - preference * cost / 1000
    if binary:
        utility[:, 1] = -np.inf
    return np.argmax(np.column_stack([np.zeros(len(x)), utility]), axis=1)


def route_first(model, questions, first_results, preference, progress=print):
    """Deploy a saved model from questions and their first direct responses only.

    Returns 0=accept, 1=second draft then think on disagreement, 2=think now.
    The caller must charge this first generation and every requested continuation.
    """
    from .controller import feature_matrix

    if len(questions) != len(first_results):
        raise ValueError("Each question needs exactly one first response")
    x = np.array([first_features(r) for r in first_results])
    if not model["response_only"]:
        question_features, _ = feature_matrix(questions, progress=progress)
        x = np.column_stack([question_features, x])
    return actions(model, x, preference)


def select(x, train_rows, x_tune, tune_rows, kind="joint", response_only=False):
    candidates, models = [], []
    for setting in SETTINGS:
        model = fit(x, train_rows, setting, kind, response_only)
        selected = selected_rows(tune_rows, actions(model, x_tune, PRIMARY))
        score = float(np.mean(selected[:, 0] - PRIMARY * selected[:, 1] / 1000))
        candidates.append({"setting": setting, "tune_utility": score})
        models.append(model)
    best = int(np.argmax([r["tune_utility"] for r in candidates]))
    return {"model": models[best], "candidates": candidates}


def confidence_actions(confidence, setting):
    return np.where(np.asarray(confidence) < setting["threshold"], setting["action"], 0)


def select_confidence(confidence, rows, preference, allowed=(1, 2)):
    # Include always accept and always continue without nonfinite JSON values.
    thresholds = [
        float(np.min(confidence) - 1),
        *np.unique(confidence).tolist(),
        float(np.max(confidence) + 1),
    ]
    best, best_score = None, -np.inf
    for action in allowed:
        for threshold in thresholds:
            setting = {"action": action, "threshold": threshold}
            selected = selected_rows(rows, confidence_actions(confidence, setting))
            score = float(np.mean(selected[:, 0] - preference * selected[:, 1] / 1000))
            if score > best_score:
                best, best_score = setting, score
    return best | {"tune_utility": best_score}
