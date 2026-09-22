"""Portable retrieval/shrinkage and regret-weighted binary routing baselines.

These are adaptations, not claimed reproductions of CARROT or Causal LLM Routing.
Every model consumes question features only at prediction time.
"""

import itertools

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from .controller import ALPHAS, FEATURE_SPEC, choose_modes, clipped

PREFERENCES = (0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
PRIMARY_PREFERENCE = 0.05
GRIDS = {
    "ridge": [{"alpha": a} for a in ALPHAS],
    "retrieval": [
        {"neighbors": k, "shrinkage": s} for k, s in itertools.product((3, 10, 20), (0, 5, 20))
    ],
    "decision": [
        {"dimensions": d, "inverse_regularization": c}
        for d, c in itertools.product((16, 32, None), (0.1, 1, 10))
    ],
}


def _matrix(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Expected a nonempty finite question-feature matrix")
    return x


def targets(data):
    return np.column_stack([data["accuracy"].mean(2), data["tokens"].mean(2)])


def selected_utility(y, modes, preference):
    y = np.asarray(y)
    i = np.arange(len(y))
    return y[i, modes] - preference * y[i, modes + 2] / 1000


def transform(x, state):
    x = _matrix(x)
    if x.shape[1] != state["input_dimensions"]:
        raise ValueError("Feature dimensions differ from the fitted transform")
    if state["pca_components"] is not None:
        n = state["embedding_dimensions"]
        embedding = (x[:, :n] - state["pca_mean"]) @ np.asarray(state["pca_components"]).T
        x = np.column_stack([embedding, x[:, n:]])
    return (x - state["mean"]) / state["scale"]


def fit_transform(x, dimensions):
    x = _matrix(x)
    # The real feature vector is 384 MiniLM coordinates followed by 3 lexical features.
    n = min(384, x.shape[1])
    state = {
        "input_dimensions": x.shape[1],
        "embedding_dimensions": n,
        "pca_components": None,
        "pca_mean": None,
    }
    projected = x
    if dimensions is not None:
        pca = PCA(n_components=min(dimensions, len(x) - 1, n), svd_solver="full").fit(x[:, :n])
        state.update(pca_components=pca.components_.tolist(), pca_mean=pca.mean_.tolist())
        projected = np.column_stack([pca.transform(x[:, :n]), x[:, n:]])
    scaler = StandardScaler().fit(projected)
    state.update(mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist())
    return transform(x, state), state


def fit_model(kind, x, y, setting, preferences=PREFERENCES):
    """Fit only on passed training questions. No tuning/evaluation arguments exist here."""
    x, y = _matrix(x), np.asarray(y, dtype=float)
    if y.shape != (len(x), 4) or not np.isfinite(y).all():
        raise ValueError("Expected four aligned finite training targets")
    if np.any((y[:, :2] < 0) | (y[:, :2] > 1)) or np.any(y[:, 2:] < 0):
        raise ValueError("Invalid accuracy/cost training targets")
    if kind not in GRIDS or setting not in GRIDS[kind]:
        raise ValueError("Model setting is outside the predefined grid")
    model = {
        "kind": kind,
        "setting": setting,
        "feature_spec": FEATURE_SPEC,
        "input_dimensions": x.shape[1],
        "preferences": list(preferences),
    }
    if kind == "retrieval":
        n = min(384, x.shape[1])
        embeddings = x[:, :n]
        embeddings = embeddings / np.maximum(
            np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12
        )
        model.update(embeddings=embeddings.tolist(), targets=y.tolist(), prior=y.mean(0).tolist())
        return model
    z, state = fit_transform(x, setting.get("dimensions"))
    model["transform"] = state
    if kind == "ridge":
        reg = Ridge(alpha=setting["alpha"], solver="svd").fit(z, y)
        model.update(coefficients=reg.coef_.tolist(), intercept=reg.intercept_.tolist())
        return model
    heads = []
    for preference in preferences:
        delta = y[:, 1] - y[:, 0] - preference * (y[:, 3] - y[:, 2]) / 1000
        weights = np.abs(delta)
        active = weights > 1e-12
        labels = (delta > 0).astype(int)
        if not active.any():
            heads.append({"constant": 0})
        elif len(np.unique(labels[active])) == 1:
            heads.append({"constant": int(labels[active][0])})
        else:
            # Normalize overall loss scale without changing relative regret weights.
            weights = weights[active] / weights[active].mean()
            classifier = LogisticRegression(
                C=setting["inverse_regularization"],
                solver="lbfgs",
                max_iter=2000,
                random_state=20260918,
            ).fit(z[active], labels[active], sample_weight=weights)
            if classifier.n_iter_[0] >= 2000:
                raise ValueError("Decision classifier did not converge")
            heads.append(
                {
                    "coefficients": classifier.coef_[0].tolist(),
                    "intercept": float(classifier.intercept_[0]),
                }
            )
    model["heads"] = heads
    return model


def predict_targets(model, x):
    x = _matrix(x)
    if x.shape[1] != model["input_dimensions"] or model["feature_spec"] != FEATURE_SPEC:
        raise ValueError("Model feature schema mismatch")
    if model["kind"] == "ridge":
        return clipped(
            transform(x, model["transform"]) @ np.asarray(model["coefficients"]).T
            + model["intercept"]
        )
    if model["kind"] != "retrieval":
        raise ValueError("Decision models predict modes, not correctness probabilities")
    memory = np.asarray(model["embeddings"])
    embedding = x[:, : memory.shape[1]]
    embedding = embedding / np.maximum(np.linalg.norm(embedding, axis=1, keepdims=True), 1e-12)
    # Stable ties preserve the frozen training-question order.
    k = min(model["setting"]["neighbors"], len(memory))
    neighbors = np.argsort(-(embedding @ memory.T), axis=1, kind="stable")[:, :k]
    strength = model["setting"]["shrinkage"]
    local_sum = np.asarray(model["targets"])[neighbors].sum(1)
    return clipped((local_sum + strength * np.asarray(model["prior"])) / (k + strength))


def predict_modes(model, x, preference):
    x = _matrix(x)
    if not np.isfinite(preference) or preference < 0:
        raise ValueError("Cost preference must be finite and nonnegative")
    if x.shape[1] != model["input_dimensions"] or model["feature_spec"] != FEATURE_SPEC:
        raise ValueError("Model feature schema mismatch")
    if model["kind"] != "decision":
        return choose_modes(predict_targets(model, x), preference)
    if preference not in model["preferences"]:
        raise ValueError("Decision head is not trained for this cost preference")
    head = model["heads"][model["preferences"].index(preference)]
    if "constant" in head:
        return np.full(len(x), head["constant"], dtype=int)
    return (transform(x, model["transform"]) @ head["coefficients"] + head["intercept"] > 0).astype(
        int
    )


def select_model(kind, x_train, y_train, x_tune, y_tune):
    """A single setting per family is selected at predeclared lambda=.05.

    Ties prefer the earliest setting, without examining diagnostic outcomes.
    """
    candidates, selected, best = [], None, -np.inf
    for setting in GRIDS[kind]:
        model = fit_model(kind, x_train, y_train, setting)
        modes = predict_modes(model, x_tune, PRIMARY_PREFERENCE)
        value = float(selected_utility(y_tune, modes, PRIMARY_PREFERENCE).mean())
        candidates.append({"setting": setting, "tuning_utility": value})
        if value > best:
            best, selected = value, model
    return selected, candidates


def route_questions(model, questions, preference, cache_dir=".cache/routing"):
    from .controller import feature_matrix

    x, _ = feature_matrix(questions, cache_dir)
    return ["thinking" if value else "direct" for value in predict_modes(model, x, preference)]
