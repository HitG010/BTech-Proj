"""Question-only MiniLM features and four independent, portable ridge predictors."""

import re
import time
from dataclasses import dataclass
from importlib.metadata import version

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

from .records import Question
from .storage import atomic_json, digest, envelope, verified

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
ALPHAS = (0.1, 1.0, 10.0, 100.0)
TARGETS = ("direct_accuracy", "thinking_accuracy", "direct_tokens", "thinking_tokens")
FEATURE_SPEC = {
    "model": MODEL,
    "revision": REVISION,
    "device": "cpu",
    "dtype": "float32",
    "max_chunk_tokens": 256,
    "pooling": "masked mean; normalize chunks; average; normalize",
    "extra": ["character_count", "numeric_literal_count", "symbolic_operator_count"],
    "version": 1,
}


def chunks(token_ids, capacity):
    if capacity < 1:
        raise ValueError("Chunk capacity must be positive")
    return [token_ids[i : i + capacity] for i in range(0, len(token_ids), capacity)] or [[]]


def lexical_features(question):
    if type(question) is not Question:
        raise TypeError("Features accept only a gold-free Question")
    return [
        len(question.prompt),
        len(re.findall(r"\d+(?:[.,]\d+)*", question.prompt)),
        len(re.findall(r"[+*/=−×÷-]", question.prompt)),
    ]


def feature_matrix(questions, cache_dir=".cache/routing", progress=print):
    """No labels or responses enter the encoder. Cache keys include entire questions."""
    from pathlib import Path

    questions = list(questions)
    for q in questions:
        lexical_features(q)
    identity = {
        "spec": FEATURE_SPEC,
        "packages": {name: version(name) for name in ["torch", "transformers", "tokenizers"]},
        "questions": [q.to_dict() for q in questions],
    }
    path = Path(cache_dir) / f"{digest(identity)}.json"
    if path.exists():
        saved = verified(path)
        if saved["identity"] != identity:
            raise ValueError("Feature cache identity mismatch")
        features = np.asarray(saved["features"])
        if features.shape != (len(questions), 387) or not np.isfinite(features).all():
            raise ValueError("Invalid cached feature matrix")
        return features, saved["metadata"]
    import torch
    from transformers import AutoModel, AutoTokenizer

    started = time.perf_counter()
    progress("Loading pinned MiniLM on CPU (no Qwen generation)")
    kwargs = {"revision": REVISION, "cache_dir": ".cache/huggingface"}
    tokenizer = AutoTokenizer.from_pretrained(MODEL, **kwargs)
    model = AutoModel.from_pretrained(MODEL, **kwargs).float().cpu().eval()
    load_seconds = time.perf_counter() - started
    encode_start = time.perf_counter()
    capacity = 256 - tokenizer.num_special_tokens_to_add(pair=False)
    rows, chunk_counts = [], []
    with torch.inference_mode():
        for q in questions:
            parts = chunks(tokenizer.encode(q.prompt, add_special_tokens=False), capacity)
            embeddings = []
            for part in parts:
                batch = tokenizer.prepare_for_model(
                    part, return_tensors="pt", return_attention_mask=True
                )
                batch = {key: value.unsqueeze(0) for key, value in batch.items()}
                hidden = model(**batch).last_hidden_state
                mask = batch["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                embeddings.append(torch.nn.functional.normalize(pooled, dim=1)[0])
            embedding = torch.nn.functional.normalize(torch.stack(embeddings).mean(0), dim=0)
            rows.append(embedding.tolist() + lexical_features(q))
            chunk_counts.append(len(parts))
    metadata = {
        "spec": FEATURE_SPEC,
        "packages": identity["packages"],
        "load_seconds": load_seconds,
        "encode_seconds": time.perf_counter() - encode_start,
        "chunk_counts": chunk_counts,
        "cache_identity": digest(identity),
    }
    atomic_json(path, envelope({"identity": identity, "features": rows, "metadata": metadata}))
    return np.asarray(rows), metadata


def clipped(predictions):
    out = np.array(predictions, dtype=float, copy=True)
    out[:, :2] = np.clip(out[:, :2], 0, 1)
    out[:, 2:] = np.maximum(out[:, 2:], 1)
    return out


def choose_modes(predictions, cost_preference):
    if not np.isfinite(cost_preference) or cost_preference < 0:
        raise ValueError("Cost preference must be finite and nonnegative")
    predictions = clipped(predictions)
    utility = predictions[:, :2] - cost_preference * predictions[:, 2:] / 1000
    # Direct wins exact ties, decided without reference to actual outcomes.
    return (utility[:, 1] > utility[:, 0]).astype(int)


@dataclass
class Controller:
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    intercepts: np.ndarray
    alphas: list

    def route(self, questions, cost_preference, cache_dir=".cache/routing"):
        """Deployment interface: questions and lambda only; no responses or gold labels."""
        x, _ = feature_matrix(questions, cache_dir)
        return [
            "thinking" if mode else "direct"
            for mode in choose_modes(self.predict(x), cost_preference)
        ]

    def predict(self, x):
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != len(self.mean) or not np.isfinite(x).all():
            raise ValueError("Invalid controller features")
        return clipped(((x - self.mean) / self.scale) @ self.coefficients.T + self.intercepts)

    def to_dict(self):
        return {
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "coefficients": self.coefficients.tolist(),
            "intercepts": self.intercepts.tolist(),
            "alphas": self.alphas,
            "targets": list(TARGETS),
            "feature_spec": FEATURE_SPEC,
        }

    @classmethod
    def from_dict(cls, payload):
        if payload["feature_spec"] != FEATURE_SPEC or payload["targets"] != list(TARGETS):
            raise ValueError("Controller feature/target schema mismatch")
        return cls(
            *(np.asarray(payload[key]) for key in ["mean", "scale", "coefficients", "intercepts"]),
            payload["alphas"],
        )


def fit_controller(x, y, seed=20260917, inner_folds=4):
    """Select each alpha by inner validation MSE; outer evaluation never enters here."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 2 or y.shape != (len(x), 4) or len(x) < inner_folds:
        raise ValueError("Need aligned features/four targets and enough training questions")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Non-finite training data")
    losses = np.zeros((len(ALPHAS), 4))
    for train, validation in KFold(inner_folds, shuffle=True, random_state=seed).split(x):
        scaler = StandardScaler().fit(x[train])
        for i, alpha in enumerate(ALPHAS):
            reg = Ridge(alpha=alpha, solver="svd").fit(scaler.transform(x[train]), y[train])
            pred = clipped(reg.predict(scaler.transform(x[validation])))
            losses[i] += ((pred - y[validation]) ** 2).sum(axis=0)
    selected = [ALPHAS[i] for i in losses.argmin(axis=0)]
    scaler = StandardScaler().fit(x)
    regressors = [
        Ridge(alpha=alpha, solver="svd").fit(scaler.transform(x), y[:, j])
        for j, alpha in enumerate(selected)
    ]
    return Controller(
        scaler.mean_,
        scaler.scale_,
        np.stack([r.coef_ for r in regressors]),
        np.array([r.intercept_ for r in regressors]),
        selected,
    )
