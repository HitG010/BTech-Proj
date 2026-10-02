"""Bounded exploratory MiniLM representation/objective pilot (no generation).

Freeze with --freeze-only before encoding or fitting. --execute is deliberately
separate: it requires that frozen plan and a completed CPU feasibility study.
Only cached endpoint labels are permitted. No source scorer is invoked here.
"""
from __future__ import annotations

import argparse
import os
import time
from copy import deepcopy
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from reasoning_budget.confirmation import file_hash
from reasoning_budget.controller import MODEL, REVISION
from reasoning_budget.storage import digest, envelope, run_lock, verified

SEED = 20261004
REPRESENTATIONS = ("q_only", "q_plus_draft")
OBJECTIVES = ("gain_mse", "regret_ce", "bidirectional", "binary_ce")
FAMILIES = tuple(f"{representation}/{objective}" for representation in REPRESENTATIONS for objective in OBJECTIVES)
THRESHOLDS = (-0.1, 0.0, 0.1)
SPEC = {
    "version": "repeat-contrastive-pilot-v1", "label": "exploratory/reused-development",
    "lambda": 0.05, "seed": SEED, "inner_split_seed": 20261002,
    "representations": list(REPRESENTATIONS), "objectives": list(OBJECTIVES),
    "families": list(FAMILIES), "thresholds": list(THRESHOLDS),
    "conditions": {"A4_to_B4": [[0, 1, 2, 3], [4, 5, 6, 7]],
                   "B4_to_A4": [[4, 5, 6, 7], [0, 1, 2, 3]],
                   "full8_secondary": [list(range(8)), list(range(8))]},
    "outer_folds": 5, "inner_folds": 4, "max_fits": 600,
    "encoder": {"model": MODEL, "revision": REVISION, "local_files_only": True,
                "device": "cpu", "dtype": "float32", "max_tokens": 256,
                "draft_truncation": "keep final token_ids up to 256 minus special tokens",
                "draft_pooling": "attention-mask mean including specials; L2 normalize",
                "q_only": "unchanged cached first 384 normalized MiniLM dimensions",
                "q_plus_draft": "L2 normalize mean(cached question384, normalized draft384)"},
    "preprocessing": {"pca_components": 8, "pca_fit": "training state rows only; equal draws/question",
                      "blocks": "standardize PCA8 /sqrt(8), draft4 /sqrt(4)", "lexical_features": False},
    "head": {"input": 12, "projection": "affine Linear(12,8); L2 normalize",
             "actions": "two learned normalized 8d prototypes; accept then think",
             "temperature": 0.1, "parameters": 120, "backbone_trainable": False},
    "optimization": {"algorithm": "fullbatch Adam", "learning_rate": 0.01,
                     "weight_decay": 0.001, "epochs": 100, "seed": SEED,
                     "early_stopping": False, "threads_max": 2},
    "margin": "cosine_think/0.1 - cosine_accept/0.1; strict greater than threshold",
    "losses": {"gain_mse": "mean((margin-g)^2)",
               "regret_ce": "sum(abs(g)*CE(logits, g>0))/sum(abs(g))",
               "binary_ce": "unweighted mean CE(logits, g>0)",
               "bidirectional": "0.5*(regret_ce + present-action mean reverse multi-positive CE); reverse targets proportional to abs(g) within action"},
    "selection": "maximize four inner-question-fold mean utility; threshold ties favor higher threshold; family ties first frozen family",
    "bootstrap": {"draws": 2000, "seed": SEED, "interval": [0.05, 0.95], "unit": "whole question", "fixed_fits": True},
    "screen": {"average_delta_at_least": 0.01, "each_direction_positive": True,
               "every_leave_one_question_out_average_positive": True},
    "interpretation": "Compact CLM-inspired objective study; not released CLM-8B, novelty or confirmation; no restoration of primary gates",
}


def normalize(array):
    values = np.asarray(array, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite feature vector")
    norms = np.linalg.norm(values, axis=-1, keepdims=True)
    if np.any(norms < 1e-12):
        raise ValueError("Zero embedding cannot be normalized")
    return values / norms


def representations(question_features, draft_embeddings):
    """Inputs contain no label, thinking response, or future cost fields."""
    q, draft = np.asarray(question_features, float), np.asarray(draft_embeddings, float)
    if q.ndim != 2 or q.shape[1] != 387 or draft.shape != (len(q), 8, 384):
        raise ValueError("Expected cached question387 and direct-draft384 features")
    cached = q[:, :384].copy()
    if not np.allclose(np.linalg.norm(cached, axis=1), 1, atol=1e-5):
        raise ValueError("Cached question embeddings must already be normalized")
    q_states = np.broadcast_to(cached[:, None, :], draft.shape).copy()
    return {"q_only": q_states, "q_plus_draft": normalize((q_states + normalize(draft)) / 2)}


def tail_tokens(token_ids, special_tokens, max_tokens=256):
    capacity = max_tokens - special_tokens
    if capacity < 1:
        raise ValueError("No capacity after encoder special tokens")
    ids = list(token_ids)
    return ids[-capacity:], {"raw_tokens": len(ids), "kept_tokens": min(len(ids), capacity),
                            "truncated": len(ids) > capacity}


def direct_texts(panel):
    """Select only the current direct answer; never inspect thinking answer text."""
    index = {qid: i for i, qid in enumerate(panel["ids"])}
    texts = [[None] * 8 for _ in index]
    for row in panel["rows"]:
        job = row["job"]
        if job["mode"] != "direct":
            continue
        i, draw = index[job["question_id"]], job["sample"]
        if texts[i][draw] is not None or row["status"] != "completed":
            raise ValueError("Duplicate or incomplete direct draft")
        texts[i][draw] = row["result"]["final_answer"]
    if any(not isinstance(text, str) for group in texts for text in group):
        raise ValueError("Complete direct-draft text coverage required")
    return texts


def encoder_inventory(cache_root=Path(".cache/huggingface")):
    """Pin local files by bytes; never resolve a remote model identifier."""
    snapshot = (Path(cache_root) / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots" / REVISION).resolve()
    if not snapshot.is_dir():
        raise ValueError("Pinned MiniLM revision is absent from local cache")
    files = {str(path.relative_to(snapshot)): file_hash(path) for path in sorted(snapshot.rglob("*")) if path.is_file()}
    if "config.json" not in files or not any(name.endswith((".safetensors", "pytorch_model.bin")) for name in files):
        raise ValueError("Cached MiniLM snapshot lacks configuration or weights")
    return {"snapshot": str(snapshot), "revision": REVISION, "files": files}


def encode_direct_drafts(direct_text, pinned_inventory):
    """Only direct text enters this encoder. Max 256, tail retained, CPU/offline."""
    if any(not isinstance(text, str) for row in direct_text for text in row) or any(len(row) != 8 for row in direct_text):
        raise ValueError("Eight strings per question required; no response dictionaries allowed")
    current = encoder_inventory()
    if current != pinned_inventory:
        raise ValueError("Pinned encoder bytes changed")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    import torch
    from transformers import AutoModel, AutoTokenizer
    torch.set_num_threads(min(2, torch.get_num_threads()))
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(current["snapshot"], local_files_only=True)
    model = AutoModel.from_pretrained(current["snapshot"], local_files_only=True).float().cpu().eval()
    cold_seconds = time.perf_counter() - started
    started = time.perf_counter()
    vectors, rows, warm_seconds = [], [], []
    with torch.inference_mode():
        for texts in direct_text:
            question_vectors, question_meta = [], []
            for text in texts:
                began = time.perf_counter()
                ids, metadata = tail_tokens(tokenizer.encode(text, add_special_tokens=False), tokenizer.num_special_tokens_to_add(pair=False))
                batch = tokenizer.prepare_for_model(ids, return_tensors="pt", return_attention_mask=True)
                batch = {key: value.unsqueeze(0).cpu() for key, value in batch.items()}
                hidden = model(**batch).last_hidden_state
                mask = batch["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                vector = torch.nn.functional.normalize(pooled, dim=1)[0].cpu().numpy()
                question_vectors.append(vector)
                question_meta.append(metadata | {"input_tokens_with_specials": int(batch["attention_mask"].sum())})
                warm_seconds.append(time.perf_counter() - began)
            vectors.append(question_vectors)
            rows.append(question_meta)
    durations = np.asarray(warm_seconds)
    return np.asarray(vectors), {"cold_load_seconds": cold_seconds, "encode_seconds": time.perf_counter() - started,
                                "warm_per_draft_seconds": {"mean": float(durations.mean()), "p50": float(np.quantile(durations, .5)), "p95": float(np.quantile(durations, .95))},
                                "truncation_count": sum(item["truncated"] for row in rows for item in row),
                                "truncation_rate": float(np.mean([item["truncated"] for row in rows for item in row])),
                                "draft_tokens": rows, "cpu_threads": torch.get_num_threads(),
                                "new_question_encoding_measured": False, "deployment_latency_claim": False}


@dataclass
class TrainingTransform:
    pca: PCA
    semantic_scaler: StandardScaler
    draft_scaler: StandardScaler
    questions: tuple[int, ...]
    draws: tuple[int, ...]

    @classmethod
    def fit(cls, semantic, draft4, questions, draws):
        q, d = validate_indices(questions, draws, len(semantic))
        raw = np.asarray(semantic)[np.ix_(q, d)].reshape(-1, 384)
        aux = np.asarray(draft4)[np.ix_(q, d)].reshape(-1, 4)
        if len(raw) < 8 or not np.isfinite(raw).all() or not np.isfinite(aux).all():
            raise ValueError("PCA8 needs eight finite permitted training states")
        pca = PCA(n_components=8, svd_solver="full").fit(raw)
        return cls(pca, StandardScaler().fit(pca.transform(raw)), StandardScaler().fit(aux), tuple(q), tuple(d))

    def transform(self, semantic, draft4, questions, draws):
        q, d = validate_indices(questions, draws, len(semantic))
        raw = np.asarray(semantic)[np.ix_(q, d)].reshape(-1, 384)
        aux = np.asarray(draft4)[np.ix_(q, d)].reshape(-1, 4)
        block = self.semantic_scaler.transform(self.pca.transform(raw)) / np.sqrt(8)
        features = np.concatenate([block, self.draft_scaler.transform(aux) / np.sqrt(4)], axis=1)
        if not np.isfinite(features).all():
            raise ValueError("Nonfinite transformed features")
        return features


def validate_indices(questions, draws, question_count):
    q, d = list(questions), list(draws)
    if not q or not d or len(set(q)) != len(q) or len(set(d)) != len(d):
        raise ValueError("Need nonempty unique questions and draws")
    if any(type(i) not in (int, np.int64, np.int32) or i < 0 or i >= question_count for i in q) or any(i not in range(8) for i in d):
        raise ValueError("Invalid question/draw index")
    return q, d


def action_head(seed=SEED):
    import torch
    torch.manual_seed(seed)
    class ActionHead(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.projection = torch.nn.Linear(12, 8)
            self.prototypes = torch.nn.Parameter(torch.randn(2, 8))
        def forward(self, x):
            states = torch.nn.functional.normalize(self.projection(x), dim=1)
            actions = torch.nn.functional.normalize(self.prototypes, dim=1)
            return states @ actions.T / .1
    head = ActionHead().float().cpu()
    if sum(parameter.numel() for parameter in head.parameters()) != 120:
        raise ValueError("Head parameter count changed")
    return head


def reverse_targets(gain):
    """Every same-action state is a positive; zero regret carries no mass."""
    import torch
    targets = torch.zeros((2, len(gain)), dtype=gain.dtype, device=gain.device)
    present = []
    labels, weights = (gain > 0).long(), gain.abs()
    for action in range(2):
        mass = weights * (labels == action)
        if mass.sum() > 0:
            targets[action] = mass / mass.sum()
            present.append(action)
    return targets, present


def objective_loss(logits, gain, objective):
    import torch
    if logits.shape != (len(gain), 2) or not torch.isfinite(logits).all() or not torch.isfinite(gain).all():
        raise ValueError("Finite paired logits/gains required")
    labels = (gain > 0).long()
    if objective == "gain_mse":
        return ((logits[:, 1] - logits[:, 0] - gain) ** 2).mean()
    ce = torch.nn.functional.cross_entropy(logits, labels, reduction="none")
    if objective == "binary_ce":
        return ce.mean()
    weighted = (ce * gain.abs()).sum() / gain.abs().sum().clamp(min=1e-12)
    if objective == "regret_ce":
        return weighted
    if objective == "bidirectional":
        target, present = reverse_targets(gain)
        if not present:
            return weighted
        reverse = -(target[present] * torch.nn.functional.log_softmax(logits.T, dim=1)[present]).sum(1).mean()
        return .5 * (weighted + reverse)
    raise ValueError("Unknown objective")


def fit_head(train_features, train_gain, objective):
    """Only acquired training rows enter optimization; there is no validation arg."""
    import torch
    torch.set_num_threads(min(2, torch.get_num_threads()))
    x, g = np.asarray(train_features, float), np.asarray(train_gain, float)
    if x.shape != (len(g), 12) or not len(g) or not np.isfinite(x).all() or not np.isfinite(g).all():
        raise ValueError("Finite 12d training features and gains required")
    model = action_head()
    optimizer = torch.optim.Adam(model.parameters(), lr=.01, weight_decay=.001)
    data, target = torch.tensor(x, dtype=torch.float32), torch.tensor(g, dtype=torch.float32)
    for _ in range(100):
        optimizer.zero_grad()
        loss = objective_loss(model(data), target, objective)
        if not torch.isfinite(loss):
            raise ValueError("Nonfinite loss")
        loss.backward()
        if any(p.grad is None or not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise ValueError("Nonfinite or absent gradient")
        optimizer.step()
    return model.eval()


def margins(model, features, shape):
    import torch
    with torch.inference_mode():
        logits = model(torch.tensor(features, dtype=torch.float32))
        return (logits[:, 1] - logits[:, 0]).cpu().numpy().reshape(shape)


def evaluate_actions(direct, thinking, questions, draws, decisions):
    from reasoning_budget.repeat_stats import _rows
    d, t = direct[np.ix_(questions, draws)], thinking[np.ix_(questions, draws)]
    g = t[:, :, 0] - d[:, :, 0] - .05 * t[:, :, 1] / 1000
    rows = _rows(direct, thinking, questions, draws, decisions, .05)
    rows.update(rescued=((d[:, :, 0] == 0) & (t[:, :, 0] == 1) & decisions).sum(1),
                harmed=((d[:, :, 0] == 1) & (t[:, :, 0] == 0) & decisions).sum(1),
                positive_gain_escalations=((g > 0) & decisions).sum(1),
                nonpositive_gain_escalations=((g <= 0) & decisions).sum(1),
                missed_positive_gains=((g > 0) & ~decisions).sum(1))
    return rows


def fit_fold(ids, semantic, draft4, direct, thinking, train, test, train_draws, eval_draws, fold):
    from reasoning_budget.repeat_stats import _confidence_threshold, _inner_splits
    if set(train) & set(test):
        raise ValueError("Training and evaluation questions overlap")
    if train_draws != eval_draws and set(train_draws) & set(eval_draws):
        raise ValueError("Independent halves overlap")
    gain = thinking[:, :, 0] - direct[:, :, 0] - .05 * thinking[:, :, 1] / 1000
    splits = _inner_splits(train, 20261002 + fold, 4)
    scores = {family: {threshold: [] for threshold in THRESHOLDS} for family in FAMILIES}
    training_records = []
    fit_count = 0
    for inner_train, inner_validation in splits:
        if set(inner_train) & (set(inner_validation) | set(test)):
            raise ValueError("Inner training leaked evaluation question")
        training_records.append({"train_ids": [ids[i] for i in inner_train],
                                 "validation_ids": [ids[i] for i in inner_validation], "draws": list(train_draws)})
        for representation in REPRESENTATIONS:
            transform = TrainingTransform.fit(semantic[representation], draft4, inner_train, train_draws)
            x = transform.transform(semantic[representation], draft4, inner_train, train_draws)
            v = transform.transform(semantic[representation], draft4, inner_validation, train_draws)
            y = gain[np.ix_(inner_train, train_draws)].ravel()
            for objective in OBJECTIVES:
                family = f"{representation}/{objective}"
                model = fit_head(x, y, objective)
                fit_count += 1
                prediction = margins(model, v, (len(inner_validation), len(train_draws)))
                for threshold in THRESHOLDS:
                    rows = evaluate_actions(direct, thinking, inner_validation, train_draws, prediction > threshold)
                    scores[family][threshold].append(float(rows["utility"].mean()))
    thresholds = {family: max(THRESHOLDS, key=lambda h: (float(np.mean(scores[family][h])), h)) for family in FAMILIES}
    best_scores = {family: float(np.mean(scores[family][thresholds[family]])) for family in FAMILIES}
    selected = max(FAMILIES, key=lambda family: best_scores[family])
    confidence_threshold = _confidence_threshold(draft4, direct, thinking, train, train_draws, .05)
    shape = (len(test), len(eval_draws))
    actions = {"confidence": draft4[np.ix_(test, eval_draws, [0])][:, :, 0] < confidence_threshold,
               "accept": np.zeros(shape, bool), "escalate": np.ones(shape, bool)}
    for representation in REPRESENTATIONS:
        transform = TrainingTransform.fit(semantic[representation], draft4, train, train_draws)
        x = transform.transform(semantic[representation], draft4, train, train_draws)
        v = transform.transform(semantic[representation], draft4, test, eval_draws)
        y = gain[np.ix_(train, train_draws)].ravel()
        for objective in OBJECTIVES:
            family = f"{representation}/{objective}"
            model = fit_head(x, y, objective)
            fit_count += 1
            actions[family] = margins(model, v, shape) > thresholds[family]
    actions["nested_selected"] = actions[selected].copy()
    details = {"fold": fold, "train_ids": [ids[i] for i in train], "test_ids": [ids[i] for i in test],
               "train_draws": list(train_draws), "evaluation_draws": list(eval_draws),
               "inner_splits": training_records, "inner_scores": {family: {str(h): float(np.mean(v)) for h, v in score.items()} for family, score in scores.items()},
               "family_thresholds": thresholds, "selected_family": selected,
               "confidence_threshold": float(confidence_threshold), "fit_count": fit_count}
    return actions, details


def ci90(values):
    values = np.asarray(values, float)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(values), (2000, len(values)))
    return np.quantile(values[draws].mean(1), [.05, .95]).tolist()


def screen(deltas_a, deltas_b):
    a, b = np.asarray(deltas_a, float), np.asarray(deltas_b, float)
    if a.shape != b.shape or a.ndim != 1 or len(a) < 2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Screen requires aligned finite whole-question differences")
    average = (a + b) / 2
    loo = (average.sum() - average) / (len(average) - 1)
    gates = {"average_at_least_0.01": float(average.mean()) >= .01,
             "both_directions_positive": float(a.mean()) > 0 and float(b.mean()) > 0,
             "all_leave_one_question_out_positive": bool(np.all(loo > 0))}
    return {"gates": gates, "passes": all(gates.values()), "average_delta": float(average.mean()),
            "average_ci90": ci90(average), "leave_one_question_out_deltas": loo.tolist(),
            "scale_acquisition": False, "fresh_test_only_if_separately_authorized": True}


def analyze(panel, draft_embeddings):
    """Nested training-only selection; all eight families remain in the report."""
    ids, q, d, t, z, folds = (panel[key] for key in ("ids", "q", "d", "t", "z", "folds"))
    from reasoning_budget.repeat_stats import ANALYSIS, _validate
    ids, q, d, t, z = _validate(ids, q, d, t, z, folds, ANALYSIS)
    semantic = representations(q, draft_embeddings)
    conditions, deltas, total_fits = {}, {}, 0
    started = time.perf_counter()
    for name, (train_draws, eval_draws) in SPEC["conditions"].items():
        records = {qid: {"fold": folds[qid], "policies": {}} for qid in ids}
        details = []
        for fold in range(5):
            train = [i for i, qid in enumerate(ids) if folds[qid] != fold]
            test = [i for i, qid in enumerate(ids) if folds[qid] == fold]
            actions, detail = fit_fold(ids, semantic, z, d, t, train, test, train_draws, eval_draws, fold)
            if "primary" in panel:
                original = {"A4_to_B4": "k4_A_to_B", "B4_to_A4": "k4_B_to_A",
                            "full8_secondary": "k8_full"}[name]
                cached = panel["primary"]["statistics"]["conditions"][original]["per_question"]
                if any(actions["confidence"][j].tolist() != cached[ids[i]]["policies"]["confidence"]["decisions"]
                       for j, i in enumerate(test)):
                    raise ValueError("Historical confidence action reproduction differs")
            details.append(detail)
            total_fits += detail["fit_count"]
            if total_fits > 600:
                raise ValueError("Fit budget exceeded")
            for policy, decisions in actions.items():
                rows = evaluate_actions(d, t, test, eval_draws, decisions)
                for j, index in enumerate(test):
                    records[ids[index]]["policies"][policy] = {key: float(value[j]) for key, value in rows.items()} | {"decisions": decisions[j].tolist()}
        summary = {}
        for policy in ["accept", "escalate", "confidence", *FAMILIES, "nested_selected"]:
            metrics = {key: np.asarray([records[qid]["policies"][policy][key] for qid in ids]) for key in records[ids[0]]["policies"][policy] if key != "decisions"}
            delta = metrics["utility"] - np.asarray([records[qid]["policies"]["confidence"]["utility"] for qid in ids])
            summary[policy] = {f"mean_{key}": float(value.mean()) for key, value in metrics.items()} | {"utility_ci90": ci90(metrics["utility"]), "delta_vs_confidence": float(delta.mean()), "delta_ci90": ci90(delta)}
            if policy == "nested_selected":
                deltas[name] = delta
        conditions[name] = {"folds": details, "per_question": records, "summary": summary}
    if total_fits != 600:
        raise ValueError("Full frozen grid did not complete exactly 600 fits")
    averages = {}
    for policy in [*FAMILIES, "nested_selected"]:
        values = np.mean([[conditions[name]["per_question"][qid]["policies"][policy]["utility"]
                           - conditions[name]["per_question"][qid]["policies"]["confidence"]["utility"]
                           for qid in ids] for name in ("A4_to_B4", "B4_to_A4")], axis=0)
        averages[policy] = {"mean": float(values.mean()), "ci90": ci90(values),
                           "per_question": dict(zip(ids, map(float, values)))}
    return {"spec": deepcopy(SPEC), "conditions": conditions, "fit_count": total_fits,
            "family_average_vs_confidence": averages,
            "historical_confidence_actions_exactly_reproduced": "primary" in panel,
            "training_seconds": time.perf_counter() - started,
            "screen": screen(deltas["A4_to_B4"], deltas["B4_to_A4"]),
            "limitations": ["Post-hoc reused-development panel; fixed-fit whole-question intervals, no selection/multiplicity correction.",
                            "Full8 has no independent same-question eight-draw replica.",
                            "Head scores are not correctness probabilities; this does not establish deployment advantage.",
                            "No failed primary gate or allocation is changed."]}


def write_new(path, payload):
    """Exclusive-create; existing artifacts can never be overwritten."""
    import json
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Output cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x") as handle:
            json.dump(envelope(payload), handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except FileExistsError:
        raise ValueError(f"Output already exists: {path}") from None


def dependencies():
    return {package: version(package) for package in ("numpy", "scipy", "scikit-learn", "torch", "transformers", "tokenizers", "threadpoolctl")}


def plan_identity(study, panel, feasibility, pinned_encoder):
    return {"spec": deepcopy(SPEC), "study": str(Path(study).resolve()),
            "source_files": {str(Path(path).resolve()): file_hash(path) for path in
                             (__file__, Path(__file__).with_name("repeat_cpu_feasibility.py"),
                              Path(__file__).parent.parent / "tests/test_repeat_contrastive_pilot.py",
                              Path(__file__).parent.parent / "docs/phase-2-contrastive-protocol.md",
                              Path(__file__).parent.parent / "src/reasoning_budget/controller.py",
                              Path(__file__).parent.parent / "src/reasoning_budget/repeat_stats.py")},
            "dependencies": dependencies(), "inputs": panel["identity"], "encoder": pinned_encoder,
            "feasibility_sha256": digest(feasibility), "primary_gates_unchanged": True,
            "no_generation": True, "no_new_references": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=Path("artifacts/research/data-efficiency-v1/repeat-panel-v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/research/data-efficiency-v1/repeat-contrastive-pilot-v1"))
    parser.add_argument("--feasibility", type=Path, default=Path("artifacts/research/data-efficiency-v1/repeat-cpu-feasibility-v1/report.json"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    # Loader reads only cached endpoint scores and known direct texts. It does not
    # invoke a scoring or reference loader. Import is intentionally lazy.
    from scripts.repeat_cpu_feasibility import load_panel
    panel = load_panel(args.study)
    feasibility = verified(args.feasibility)
    feasibility_plan = verified(args.feasibility.parent / "analysis-plan.json")
    if (feasibility["primary_gates"] != panel["primary"]["statistics"]["gates"]
            or feasibility["historical_actions_exactly_reproduced"] is not True
            or feasibility["fit_accounting"]["ridge_fits"] != 1035
            or feasibility["plan_sha256"] != digest(feasibility_plan)
            or feasibility_plan["inputs"] != panel["identity"]):
        raise ValueError("Completed CPU feasibility identity or reproduction differs")
    pinned = encoder_inventory()
    plan = plan_identity(args.study, panel, feasibility, pinned)
    output = args.output.resolve()
    study = args.study.resolve()
    if output == study or study in output.parents:
        raise ValueError("Pilot output must be outside frozen study")
    with run_lock(output):
        target = output / "analysis-plan.json"
        if args.freeze_only:
            write_new(target, plan)
            print({"frozen_plan": str(target), "plan_sha256": digest(plan), "features_or_fit_started": False})
            return
        if not target.exists() or verified(target) != plan:
            raise ValueError("Freeze the exact current plan before encoding or fitting")
        if any((output / name).exists() for name in ("draft-features.json", "report.json")):
            raise ValueError("Completed or partial pilot output exists; never overwrite or restart it")
        before = deepcopy(panel["identity"])
        texts = direct_texts(panel)
        embeddings, metadata = encode_direct_drafts(texts, pinned)
        write_new(output / "draft-features.json", {"plan_sha256": digest(plan), "embeddings": embeddings.tolist(), "metadata": metadata})
        with threadpool_limits(limits=2):
            report = analyze(panel, embeddings)
        if load_panel(args.study)["identity"] != before or encoder_inventory() != pinned:
            raise ValueError("Frozen input or encoder inventory changed during pilot")
        write_new(output / "report.json", {"plan_sha256": digest(plan), "statistics": report, "encoder_metadata": metadata,
                                            "inputs_preserved": True, "router_overhead_conversion_to_generated_tokens": None})
        print({"report": str(output / "report.json"), "exploratory_screen": report["screen"]})


if __name__ == "__main__":
    main()
