"""Frozen disjoint baseline study: acquire train/tune, freeze policies, then diagnose.

The diagnostic partition is drawn from validation, never the official test set.
Manual scoring audit was explicitly waived by the user on 2026-09-18.
"""

import gc
import os
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import yaml

from .calibration import select_questions
from .config import from_dict, load_config
from .controller import Controller, choose_modes, feature_matrix, fit_controller
from .data import check_questions, load_gold, load_questions, save_dataset
from .records import Question
from .reporting import bootstrap, score_run
from .routing import confidence_threshold, escalation, outcomes, summarize
from .runner import _usage, implementation_digest, load_run, run
from .scoring import SCORING_VERSION, parse_answer
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified
from .stronger import (
    GRIDS,
    PREFERENCES,
    PRIMARY_PREFERENCE,
    predict_modes,
    select_model,
    targets,
)

SEED = 20260918
TRAIN_SIZES = (32, 50)


def study_implementation():
    folder = Path(__file__).parent
    return digest(
        {
            name: (folder / name).read_text()
            for name in [
                "learnability.py",
                "stronger.py",
                "controller.py",
                "routing.py",
                "scoring.py",
            ]
        }
    )


def prepare(
    config_path="configs/pilot-calibrated.yaml", output="artifacts/learnability/baselines-v1"
):
    base, directory = load_config(config_path), Path(output).resolve()
    if base.answer_tokens != 512 or base.reasoning_tokens != 2048:
        raise ValueError("Study requires frozen 512 answer / 2048 reasoning allowances")
    if set(base.modes) != {"direct", "thinking"}:
        raise ValueError("Both modes are required")
    all_questions = load_questions(base.data_dir)
    train = select_questions([q for q in all_questions if q.split == "train"], 50, SEED)
    validation = select_questions([q for q in all_questions if q.split == "validation"], 100, SEED)
    groups = {"train": train, "tune": validation[:50], "diagnostic": validation[50:]}
    check_questions([q for group in groups.values() for q in group])
    configs = {}
    for role, questions in groups.items():
        values = base.to_dict() | {
            "name": f"learnability-{role}-v1",
            "split": "train" if role == "train" else "validation",
            "samples": 1 if role == "train" else 2,
            "data_dir": str(directory / "data" / role),
            "output_dir": str(Path(base.output_dir).resolve()),
            "limits": {
                "max_tokens": 170000 if role == "train" else 340000,
                "max_elapsed_seconds": 7200 if role == "train" else 10800,
                "job_seconds": 600,
            },
        }
        configs[role] = from_dict(values).to_dict()
    protocol = {
        "schema_version": 1,
        "seed": SEED,
        "selection": "sha256-question-identity-v1",
        "groups": {role: [q.to_dict() for q in group] for role, group in groups.items()},
        "configs": configs,
        "train_sizes": list(TRAIN_SIZES),
        "grids": GRIDS,
        "preferences": list(PREFERENCES),
        "primary_preference": PRIMARY_PREFERENCE,
        "primary_comparison": "decision versus ridge-MSE utility at train_size=50, lambda=.05",
        "selection_rule": "one setting/family maximizing tune utility at lambda=.05; first wins ties",
        "scoring_version": SCORING_VERSION,
        "audit": {
            "status": "waived_by_user",
            "date": "2026-09-18",
            "instruction": "Lets move to the next implementation, ignore the scoring audit",
            "review_completed": False,
        },
        "implementation": study_implementation(),
        "generation_implementation": implementation_digest(),
        "packages": {
            name: version(name)
            for name in ["numpy", "scikit-learn", "torch", "transformers", "tokenizers"]
        },
        "scope": "development study; validation split is partitioned; official test excluded",
        "cloud_spend": 0,
    }
    with run_lock(directory):
        path = directory / "protocol.json"
        if path.exists() and verified(path) != protocol:
            raise ValueError("Study is frozen with different inputs/code; choose a new directory")
        # Selection is gold-independent. Only selected labels enter isolated scoring artifacts.
        gold = load_gold(base.data_dir)
        for role, questions in groups.items():
            save_dataset(
                directory / "data" / role,
                questions,
                {q.id: gold[q.id] for q in questions},
                {"role": role, "seed": SEED, "parent_data": base.data_dir},
            )
            (directory / f"{role}.yaml").write_text(yaml.safe_dump(configs[role], sort_keys=False))
        atomic_json(path, envelope(protocol))
    return directory


def read_protocol(directory):
    protocol = verified(Path(directory) / "protocol.json")
    if (
        protocol["implementation"] != study_implementation()
        or protocol["generation_implementation"] != implementation_digest()
        or protocol["scoring_version"] != SCORING_VERSION
    ):
        raise ValueError("Frozen implementation/scorer changed; do not mix studies on resume")
    if protocol["packages"] != {name: version(name) for name in protocol["packages"]}:
        raise ValueError("Frozen package environment changed")
    return protocol


def load_observations(path, expected_questions, split):
    """Read verified generated/scored observations; never consult gold in fitting code."""
    manifest, records = load_run(path)
    config = manifest["identity"]["config"]
    if split not in {"train", "validation"} or config["split"] != split:
        raise ValueError("Only disjoint train/validation observations are permitted")
    if manifest["identity"]["questions"] != expected_questions:
        raise ValueError("Run questions differ from frozen role")
    if set(config["modes"]) != {"direct", "thinking"}:
        raise ValueError("Both modes must be present")
    scores = read_json(Path(path) / "scores.json")
    if (
        scores["records_sha256"] != digest(records)
        or scores["run_id"] != manifest["run_id"]
        or scores["gold_sha256"] != manifest["scoring_gold_sha256"]
        or scores["scoring_version"] != SCORING_VERSION
    ):
        raise ValueError("Stale scoring artifact")
    by_id = {s["job_id"]: s for s in scores["scores"]}
    n, samples = len(expected_questions), config["samples"]
    ids = {q["id"]: i for i, q in enumerate(expected_questions)}
    data = {key: np.empty((n, 2, samples)) for key in ["accuracy", "tokens", "seconds"]}
    data["confidence"] = np.empty((n, samples))
    answers = [[None] * samples for _ in range(n)]
    seen = set()
    for record in records:
        if record["status"] != "completed":
            raise ValueError("All observations must be complete; resume generation first")
        job, result = record["job"], record["result"]
        i, mode, s = (
            ids[job["question_id"]],
            {"direct": 0, "thinking": 1}[job["mode"]],
            job["sample"],
        )
        if (i, mode, s) in seen or not 0 <= s < samples:
            raise ValueError("Duplicate or unsupported observation")
        seen.add((i, mode, s))
        data["accuracy"][i, mode, s] = by_id[job["id"]]["correct"]
        data["tokens"][i, mode, s] = sum(
            result[k] for k in ["answer_tokens", "reasoning_tokens", "inserted_tokens"]
        )
        data["seconds"][i, mode, s] = result["elapsed_seconds"]
        if mode == 0:
            confidence = result["mean_generated_logprob"]
            if confidence is None or not np.isfinite(confidence):
                raise ValueError("Missing direct decoder log-probability")
            data["confidence"][i, s] = confidence
            answers[i][s] = parse_answer(
                result["final_answer"], incomplete=result["answer_truncated"]
            )[0]
    if len(seen) != n * 2 * samples or len(by_id) != len(seen):
        raise ValueError("Incomplete observation matrix")
    data["agreement"] = np.array(
        [len(a) == 2 and a[0] is not None and a[0] == a[1] for a in answers]
    )
    return data, {
        "manifest": digest(manifest),
        "records": digest(records),
        "scores": digest(scores),
    }


def freeze_models(directory, progress=print):
    directory = Path(directory)
    protocol = read_protocol(directory)
    runs = verified(directory / "runs.json")
    loaded, features, sources = {}, {}, {}
    for role in ["train", "tune"]:
        split = "train" if role == "train" else "validation"
        loaded[role], sources[role] = load_observations(runs[role], protocol["groups"][role], split)
    path = directory / "models.json"
    identity = {"protocol": digest(protocol), "sources": sources}
    if path.exists():
        saved = verified(path)
        if saved["identity"] != identity:
            raise ValueError("Frozen policies have different training/tuning inputs")
        return saved
    for role in ["train", "tune"]:
        features[role], _ = feature_matrix(
            [Question(**q) for q in protocol["groups"][role]], progress=progress
        )
    y_tune = targets(loaded["tune"])
    models = []
    for size in protocol["train_sizes"]:
        progress(f"Fitting routers on {size} training questions; tuning on separate 50 questions")
        x, y = features["train"][:size], targets(loaded["train"])[:size]
        original = fit_controller(x, y, seed=SEED)
        models.append(
            {
                "family": "ridge-MSE",
                "train_size": size,
                "model": original.to_dict(),
                "candidates": [],
                "train_ids": [q["id"] for q in protocol["groups"]["train"][:size]],
            }
        )
        for kind in GRIDS:
            model, candidates = select_model(kind, x, y, features["tune"], y_tune)
            models.append(
                {
                    "family": kind,
                    "train_size": size,
                    "model": model,
                    "candidates": candidates,
                    "train_ids": [q["id"] for q in protocol["groups"]["train"][:size]],
                }
            )
    thresholds = [
        confidence_threshold(loaded["tune"], np.arange(len(y_tune)), p) for p in PREFERENCES
    ]
    saved = {
        "identity": identity,
        "models": models,
        "confidence_thresholds": thresholds,
        "frozen_at": time.time(),
        "diagnostic_used_for_fitting": False,
        "scoring_audit": protocol["audit"],
    }
    atomic_json(path, envelope(saved))
    return saved


def evaluate(directory, progress=print):
    directory = Path(directory)
    protocol = read_protocol(directory)
    saved = freeze_models(directory, progress)
    runs = verified(directory / "runs.json")
    data, source = load_observations(
        runs["diagnostic"], protocol["groups"]["diagnostic"], "validation"
    )
    x, metadata = feature_matrix(
        [Question(**q) for q in protocol["groups"]["diagnostic"]], progress=progress
    )
    n = len(x)
    direct, thinking = outcomes(data, np.zeros(n, int)), outcomes(data, np.ones(n, int))
    policies = [("always-direct", None, direct), ("always-thinking", None, thinking)]
    policies += [
        ("random-expected", float(p), (1 - p) * direct + p * thinking)
        for p in np.linspace(0, 1, 11)
    ]
    for row in saved["models"]:
        for preference in PREFERENCES:
            modes = (
                choose_modes(Controller.from_dict(row["model"]).predict(x), preference)
                if row["family"] == "ridge-MSE"
                else predict_modes(row["model"], x, preference)
            )
            policies.append(
                (f"{row['family']}-n{row['train_size']}", preference, outcomes(data, modes))
            )
    for p, threshold in zip(PREFERENCES, saved["confidence_thresholds"], strict=True):
        policies.append(("confidence", p, escalation(data, data["confidence"] < threshold)))
    policies.append(
        (
            "DART-SC-2-adapted",
            None,
            escalation(data, np.repeat((~data["agreement"])[:, None], 2, axis=1), two_drafts=True),
        )
    )
    primary = {
        name: rows[:, 0] - PRIMARY_PREFERENCE * rows[:, 1] / 1000
        for name, parameter, rows in policies
        if parameter == PRIMARY_PREFERENCE or parameter is None
    }
    difference = primary["decision-n50"] - primary["ridge-MSE-n50"]
    usage = {
        role: dict(zip(["charged_tokens", "elapsed_seconds"], _usage(Path(path)), strict=True))
        for role, path in runs.items()
    }
    result = {
        "protocol": digest(protocol),
        "models_sha256": digest(saved),
        "diagnostic_source": source,
        "summaries": summarize(policies, SEED),
        "features": metadata,
        "expenditure": usage,
        "primary": {
            "comparison": protocol["primary_comparison"],
            "mean_utility_difference": float(difference.mean()),
            "ci95": bootstrap(difference, SEED),
        },
        "per_question": [
            {"policy": name, "parameter": p, "rows": rows.tolist()} for name, p, rows in policies
        ],
        "question_ids": [q["id"] for q in protocol["groups"]["diagnostic"]],
        "audit": protocol["audit"],
    }
    atomic_json(directory / "report.json", envelope(result))
    _report(directory, result)
    return directory / "report.md"


def _report(directory, result):
    import csv

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summaries = result["summaries"]
    with (directory / "curve.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    fig, ax = plt.subplots(figsize=(9, 5))
    for name in dict.fromkeys(s["policy"] for s in summaries):
        if name.endswith("-n32"):
            continue
        rows = [s for s in summaries if s["policy"] == name]
        ax.plot(
            [r["mean_charged_tokens"] for r in rows],
            [100 * r["accuracy"] for r in rows],
            "o--" if name == "random-expected" else "o-",
            label=name,
            markersize=3,
        )
    ax.set(
        xlabel="Charged output tokens per question (all probes included)",
        ylabel="Accuracy (%)",
        title="Frozen routers on 50 disjoint validation holdout questions",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(directory / "accuracy-cost.png", dpi=180)
    plt.close(fig)
    primary = result["primary"]
    lines = [
        "# Disjoint router baseline study",
        "",
        "50 training questions; separate 50-question tuning and 50-question diagnostic "
        "partitions. The official test split is excluded. Policies/settings were frozen "
        "before diagnostic generation. One pair per training question; two per validation "
        "question. The human scoring audit was waived by the user on 2026-09-18, not completed.",
        "",
        "Retrieval uses cosine MiniLM neighbors and shrinkage to training means. Decision "
        "routing uses regret-weighted logistic heads with training-only PCA/scaling. These "
        "are adaptations, not full CARROT/Causal LLM Routing reproductions. DART-SC-2 remains "
        "a two-draft agreement adaptation; its third draft and budget probing are absent.",
        "",
        f"Primary comparison: {primary['comparison']}. Utility difference: "
        f"{primary['mean_utility_difference']:.5f}, paired 95% interval {primary['ci95']}.",
        "",
        "Lambda is accuracy probability per 1,000 charged tokens. Model settings were "
        "selected once per family at lambda=.05. Remaining preferences and n32 curves are "
        "secondary; do not select a policy from the diagnostic results. Intervals resample "
        "whole questions and condition on this training set; training-seed variability is "
        "not estimated by them. Historical acquisition cost is separate from per-query "
        "inference costs. CPU routing and encoder costs are excluded from token curves; "
        "cached generation seconds are replay accounting, not measured live policy latency.",
        "",
        "| Policy | Parameter | Accuracy | Tokens/question |",
        "|---|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['policy']} | {row['parameter']} | {row['accuracy']:.3f} | "
            f"{row['mean_charged_tokens']:.1f} |"
        )
    lines += ["", "![Accuracy–cost curve](accuracy-cost.png)", ""]
    (directory / "report.md").write_text("\n".join(lines))


def run_study(directory, progress=print):
    """Resumable serial GPU collection, then CPU fit/evaluation. Never spawns cloud jobs."""
    from .backend import environment, make_backend

    directory = Path(directory).resolve()
    with run_lock(directory):
        protocol = read_protocol(directory)
        state_path = directory / "runs.json"
        runs = verified(state_path) if state_path.exists() else {}
        state = {"pid": os.getpid(), "started_at": time.time(), "status": "running"}
        atomic_json(directory / "status.json", state)
        reference = None
        try:
            for role in ["train", "tune", "diagnostic"]:
                if role == "diagnostic":
                    freeze_models(directory, progress)
                config = from_dict(protocol["configs"][role])
                if [q.to_dict() for q in load_questions(config.data_dir, config.split)] != protocol[
                    "groups"
                ][role]:
                    raise ValueError("Dataset changed after freezing role allocation")
                backend = make_backend(config)
                identity = {
                    "config": config.to_dict(),
                    "questions": protocol["groups"][role],
                    "backend": backend.metadata,
                    "environment": environment(),
                    "implementation_sha256": implementation_digest(),
                }
                comparable = {
                    key: identity[key]
                    for key in ["backend", "environment", "implementation_sha256"]
                }
                if reference is not None and comparable != reference:
                    raise ValueError("Backend/environment changed between study stages")
                reference = comparable
                path = Path(config.output_dir) / digest(identity)[:20]
                if role in runs and Path(runs[role]) != path:
                    raise ValueError("Run identity changed on resume")
                runs[role] = str(path)
                atomic_json(state_path, envelope(runs))
                atomic_json(
                    directory / "status.json", state | {"stage": role, "run_dir": str(path)}
                )
                progress(f"Stage {role}: {path}")
                actual = run(config, backend, progress)
                if actual.resolve() != path.resolve():
                    raise ValueError("Preflight/generation identity mismatch")
                complete = all(r["status"] == "completed" for r in load_run(path)[1])
                del backend
                gc.collect()
                if not complete:
                    atomic_json(
                        directory / "status.json", state | {"stage": role, "status": "paused"}
                    )
                    progress("Study paused; resume with the same command after checking run status")
                    return directory
                score_run(path)
            report_path = evaluate(directory, progress)
            atomic_json(
                directory / "status.json",
                state
                | {"status": "complete", "report": str(report_path), "finished_at": time.time()},
            )
            progress(f"Study complete: {report_path}")
        except BaseException as exc:
            atomic_json(directory / "status.json", state | {"status": "failed", "error": str(exc)})
            raise
    return directory
