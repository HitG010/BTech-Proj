"""Frozen first-draft continuation study; fresh diagnostic, sealed official test."""

import gc
import os
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import yaml

from . import probe
from .backend import GENERATION_PROTOCOL
from .calibration import select_questions
from .config import from_dict, load_config
from .controller import Controller, choose_modes, feature_matrix, fit_controller
from .data import check_questions, load_gold, load_questions, save_dataset
from .records import Question
from .reporting import bootstrap, score_run, scores_path
from .routing import summarize
from .runner import (
    _usage,
    build_run_identity,
    implementation_digest,
    load_run,
    require_implementation,
    run,
)
from .scoring import SCORING_VERSION, parse_answer
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified

SEED = 20260919
DEFAULT = "artifacts/probe/continuation-v1"
PILOT = "artifacts/runs/d00485799f1c8932bafa"
BASELINES = "artifacts/learnability/baselines-v1"


def implementation():
    root = Path(__file__).parent
    return digest(
        {
            n: (root / n).read_text()
            for n in [
                "probe.py",
                "probe_study.py",
                "controller.py",
                "stronger.py",
                "routing.py",
                "scoring.py",
                "reporting.py",
                "data.py",
            ]
        }
    )


def comparable(config):
    settings = {
        k: config[k]
        for k in [
            "backend",
            "seed",
            "answer_tokens",
            "reasoning_tokens",
            "prompt_suffix",
            "model",
            "direct",
            "thinking",
        ]
    }
    settings["closure_text"] = config.get("closure_text")
    return settings


def read_sources(paths, *, expected=None, diagnostic=False):
    """Verify complete inputs; combine either question partitions or mode partitions."""
    questions, observations, sources = {}, {}, {}
    reference = reference_backend = None
    for path in paths:
        manifest, records = load_run(path)
        config = manifest["identity"]["config"]
        if config["split"] not in ({"train"} if diagnostic else {"pilot", "validation"}):
            raise ValueError("Invalid source role; official test is sealed")
        source_backend = manifest["identity"]["backend"]
        if (
            manifest["identity"].get("protocol_version") != GENERATION_PROTOCOL
            or source_backend.get("generation_protocol") != GENERATION_PROTOCOL
        ):
            raise ValueError("Source generation protocol differs from current decoder")
        require_implementation(manifest, records, implementation_digest())
        settings = comparable(config)
        if reference is not None and settings != reference:
            raise ValueError("Decoder/model settings differ across source runs")
        if reference_backend is not None and source_backend != reference_backend:
            raise ValueError("Backend metadata differs across source runs")
        reference = settings
        reference_backend = source_backend
        artifact = read_json(scores_path(path))
        if (
            artifact["records_sha256"] != digest(records)
            or artifact["run_id"] != manifest["run_id"]
            or artifact["gold_sha256"] != manifest["scoring_gold_sha256"]
            or artifact["scoring_version"] != SCORING_VERSION
        ):
            raise ValueError("Stale scoring artifact")
        scores = {s["job_id"]: s for s in artifact["scores"]}
        if len(scores) != len(records) or len(scores) != len(artifact["scores"]):
            raise ValueError("Duplicate or missing scores")
        for q in manifest["identity"]["questions"]:
            if q["split"] != config["split"]:
                raise ValueError("Question role disagrees with source config")
            if q["id"] in questions and questions[q["id"]] != q:
                raise ValueError("Question identity conflict")
            questions[q["id"]] = q
        for record in records:
            if record["status"] != "completed":
                raise ValueError("Source generation is incomplete")
            job = record["job"]
            key = (job["question_id"], job["mode"], job["sample"])
            if key in observations:
                raise ValueError("Duplicate generation observation")
            score = scores[job["id"]]
            if score["question_id"] != key[0] or score["mode"] != key[1]:
                raise ValueError("Score/job mismatch")
            observations[key] = (record["result"], score["correct"])
        sources[str(Path(path).resolve())] = {
            "manifest": digest(manifest),
            "records": digest(records),
            "scores": digest(artifact),
        }
    ordered = list(questions.values()) if expected is None else expected
    if {q["id"]: q for q in ordered} != questions:
        raise ValueError("Source questions differ from frozen role allocation")
    check_questions([Question(**q) for q in ordered])
    count = 3 if diagnostic else 2
    required = {
        (q["id"], mode, s)
        for q in ordered
        for mode, limit in [("direct", count), ("thinking", 2)]
        for s in range(limit)
    }
    if set(observations) != required:
        raise ValueError("Incomplete or unsupported response matrix")
    data = {"questions": ordered, "answers": [], "direct_results": []}
    for mode, limit in [("direct", count), ("thinking", 2)]:
        matrix = []
        for q in ordered:
            rows, answers, results = [], [], []
            for s in range(limit):
                result, correct = observations[(q["id"], mode, s)]
                cost = sum(
                    result[k] for k in ["answer_tokens", "reasoning_tokens", "inserted_tokens"]
                )
                rows.append([float(correct), cost, result["elapsed_seconds"]])
                answers.append(
                    parse_answer(result["final_answer"], incomplete=result["answer_truncated"])[0]
                )
                results.append(result)
            matrix.append(rows)
            if mode == "direct":
                data["answers"].append(answers)
                data["direct_results"].append(results)
        data[mode] = np.array(matrix)
    return data, sources, reference


def prepare(
    config_path="configs/pilot-calibrated.yaml",
    output=DEFAULT,
    pilot=PILOT,
    baselines=BASELINES,
    count=100,
):
    directory = Path(output).resolve()
    if type(count) is not int or count < 2:
        raise ValueError("Diagnostic question count must be at least two")
    base = load_config(config_path)
    old = verified(Path(baselines) / "protocol.json")
    old_runs = verified(Path(baselines) / "runs.json")
    paths = {
        "train": [str(Path(pilot).resolve())],
        "tune": [old_runs["tune"], old_runs["diagnostic"]],
    }
    development, sources = {}, {}
    for role in ("train", "tune"):
        data, sources[role], settings = read_sources(paths[role])
        if settings != comparable(base.to_dict()):
            raise ValueError("Development traces and new generation settings differ")
        development[role] = data["questions"]
    exclusions = development["train"] + development["tune"] + old["groups"]["train"]
    check_questions([Question(**q) for q in exclusions])
    used = {q["id"] for q in exclusions}
    candidates = [q for q in load_questions(base.data_dir, "train") if q.id not in used]
    fresh = select_questions(candidates, count, SEED)
    check_questions([Question(**q) for q in exclusions] + fresh)
    configs = {}
    for mode, samples, tokens, seconds in [
        ("direct", 3, 170000, 7200),
        ("thinking", 2, 530000, 18000),
    ]:
        values = base.to_dict() | {
            "name": f"continuation-diagnostic-{mode}-v1",
            "split": "train",
            "modes": [mode],
            "samples": samples,
            "data_dir": str(directory / "data"),
            "output_dir": str(Path(base.output_dir).resolve()),
            "limits": {"max_tokens": tokens, "max_elapsed_seconds": seconds, "job_seconds": 600},
        }
        configs[mode] = from_dict(values).to_dict()
    protocol = {
        "schema_version": 1,
        "seed": SEED,
        "source_paths": paths,
        "sources": sources,
        "development": development,
        "diagnostic": [q.to_dict() for q in fresh],
        "excluded_ids": sorted(used),
        "configs": configs,
        "implementation": implementation(),
        "generation_implementation": implementation_digest(),
        "packages": {
            n: version(n) for n in ["numpy", "scikit-learn", "torch", "transformers", "tokenizers"]
        },
        "scoring_version": SCORING_VERSION,
        "settings": probe.SETTINGS,
        "preferences": list(probe.PREFERENCES),
        "primary_preference": probe.PRIMARY,
        "primary_comparison": "joint three-action minus tuned confidence-continuation utility at lambda=.05",
        "selection_rule": "one model setting per family at lambda=.05; first candidate wins ties",
        "hypothesis": "First-draft rescue minus regression probability can allocate continuation cost better than confidence alone",
        "scope": "fresh development diagnostic from unused train pool; reserve these IDs permanently from future training; official test sealed",
        "novelty_status": "unestablished; ordinary value-of-information and confidence stopping are prior work",
        "baseline_scope": "DART SC K_init=2 K_max=3 branch, matched decoder/caps and numeric parser; SC-Budget and full ReASC not reproduced",
        "audit": old["audit"],
        "cloud_spend": 0,
    }
    with run_lock(directory):
        path = directory / "protocol.json"
        if path.exists() and verified(path) != protocol:
            raise ValueError("Frozen study differs; choose a new directory")
        gold = load_gold(base.data_dir)
        save_dataset(
            directory / "data",
            fresh,
            {q.id: gold[q.id] for q in fresh},
            {"role": "continuation-diagnostic", "seed": SEED, "excluded_ids": sorted(used)},
        )
        for mode, config in configs.items():
            (directory / f"{mode}.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        atomic_json(path, envelope(protocol))
    return directory


def read_protocol(directory):
    protocol = verified(Path(directory) / "protocol.json")
    if (
        protocol["implementation"] != implementation()
        or protocol["generation_implementation"] != implementation_digest()
        or protocol["scoring_version"] != SCORING_VERSION
    ):
        raise ValueError("Frozen study implementation changed")
    if protocol["packages"] != {n: version(n) for n in protocol["packages"]}:
        raise ValueError("Frozen package versions changed")
    return protocol


def freeze_models(directory, progress=print):
    directory = Path(directory)
    protocol = read_protocol(directory)
    loaded = {}
    for role in ("train", "tune"):
        data, source, _ = read_sources(
            protocol["source_paths"][role], expected=protocol["development"][role]
        )
        if source != protocol["sources"][role]:
            raise ValueError("Frozen development source changed")
        loaded[role] = data
    identity = {"protocol": digest(protocol), "sources": protocol["sources"]}
    path = directory / "models.json"
    if path.exists():
        saved = verified(path)
        if saved["identity"] != identity:
            raise ValueError("Frozen model identity differs")
        return saved
    features, rows, metadata, question_features = {}, {}, {}, {}
    for role, data in loaded.items():
        x, metadata[role] = feature_matrix(
            [Question(**q) for q in data["questions"]], progress=progress
        )
        features[role] = probe.state_features(x, data["direct_results"])
        question_features[role] = x
        rows[role] = probe.continuation_rows(data)
    models = {}
    for name, kind, response_only in [
        ("joint", "joint", False),
        ("gain-ridge", "gain-ridge", False),
        ("response-only", "joint", True),
    ]:
        progress(f"Fitting {name}: existing development traces only")
        models[name] = probe.select(
            features["train"], rows["train"], features["tune"], rows["tune"], kind, response_only
        )
    confidence = features["tune"][:, -4]
    thresholds = {
        name: [
            probe.select_confidence(confidence, rows["tune"], p, allowed) for p in probe.PREFERENCES
        ]
        for name, allowed in [
            ("confidence-continuation", (1, 2)),
            ("confidence-probe", (1,)),
            ("confidence-thinking", (2,)),
        ]
    }
    train = loaded["train"]
    targets = np.column_stack(
        [
            train["direct"][:, :, 0].mean(1),
            train["thinking"][:, :, 0].mean(1),
            train["direct"][:, :, 1].mean(1),
            train["thinking"][:, :, 1].mean(1),
        ]
    )
    question_router = fit_controller(question_features["train"], targets, seed=SEED)
    saved = {
        "identity": identity,
        "models": models,
        "thresholds": thresholds,
        "features": metadata,
        "frozen_at": time.time(),
        "diagnostic_used_for_fitting": False,
        "question_ridge": question_router.to_dict(),
    }
    atomic_json(path, envelope(saved))
    return saved


def evaluate(directory, progress=print):
    directory = Path(directory)
    protocol, saved = read_protocol(directory), freeze_models(directory, progress)
    runs = verified(directory / "runs.json")
    data, source, _ = read_sources(
        [runs[m] for m in ("direct", "thinking")], expected=protocol["diagnostic"], diagnostic=True
    )
    x, metadata = feature_matrix([Question(**q) for q in data["questions"]], progress=progress)
    question_predictions = Controller.from_dict(saved["question_ridge"]).predict(x)
    x = probe.state_features(x, data["direct_results"])
    rows = probe.continuation_rows(data)
    direct, thinking = data["direct"][:, :2].mean(1), data["thinking"].mean(1)
    dart2 = rows[:, :, 1].mean(1)
    policies = [
        ("always-direct", None, direct),
        ("always-thinking", None, thinking),
        ("DART-SC-2-adapted", None, dart2),
        ("DART-SC-3-adapted", None, probe.dart_sc3(data)),
    ]
    for p in np.linspace(0, 1, 11):
        policies += [
            ("random-expected", float(p), (1 - p) * direct + p * thinking),
            ("random-probe-expected", float(p), (1 - p) * direct + p * dart2),
        ]
    decisions = []
    for p_index, p in enumerate(probe.PREFERENCES):
        modes = choose_modes(question_predictions, p)
        policies.append(("question-ridge", p, np.where(modes[:, None] == 0, direct, thinking)))
        for name, model in saved["models"].items():
            choices = probe.actions(model["model"], x, p)
            policies.append((name, p, probe.selected_rows(rows, choices)))
            decisions.append({"policy": name, "parameter": p, "actions": choices.tolist()})
        for name, kwargs in [
            ("joint-binary", {"binary": True}),
            ("joint-ignore-harm", {"ignore_harm": True}),
        ]:
            choices = probe.actions(saved["models"]["joint"]["model"], x, p, **kwargs)
            policies.append((name, p, probe.selected_rows(rows, choices)))
            decisions.append({"policy": name, "parameter": p, "actions": choices.tolist()})
        for name, settings in saved["thresholds"].items():
            choices = probe.confidence_actions(x[:, -4], settings[p_index])
            policies.append((name, p, probe.selected_rows(rows, choices)))
    primary = {
        name: values[:, 0] - probe.PRIMARY * values[:, 1] / 1000
        for name, p, values in policies
        if p == probe.PRIMARY or p is None
    }
    delta = primary["joint"] - primary["confidence-continuation"]
    result = {
        "protocol": digest(protocol),
        "models_sha256": digest(saved),
        "diagnostic_sources": source,
        "question_ids": [q["id"] for q in data["questions"]],
        "summaries": summarize(policies, SEED),
        "primary": {
            "comparison": protocol["primary_comparison"],
            "utility_difference": float(delta.mean()),
            "ci95": bootstrap(delta, SEED),
        },
        "per_question": [
            {"policy": name, "parameter": p, "rows": r.tolist()} for name, p, r in policies
        ],
        "decisions": decisions,
        "features": metadata,
        "actual_cache_expenditure": {
            mode: dict(zip(["charged_tokens", "elapsed_seconds"], _usage(Path(path)), strict=True))
            for mode, path in runs.items()
        },
        "historical_source_expenditure": {
            path: dict(zip(["charged_tokens", "elapsed_seconds"], _usage(Path(path)), strict=True))
            for paths in protocol["source_paths"].values()
            for path in paths
        },
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
    fig, ax = plt.subplots(figsize=(10, 6))
    for name in dict.fromkeys(r["policy"] for r in summaries):
        if name in {"joint-ignore-harm", "joint-binary", "confidence-probe", "confidence-thinking"}:
            continue
        subset = [r for r in summaries if r["policy"] == name]
        ax.plot(
            [r["mean_charged_tokens"] for r in subset],
            [100 * r["accuracy"] for r in subset],
            "o-",
            label=name,
            markersize=3,
        )
    ax.set(
        xlabel="All consumed output/closure tokens per question",
        ylabel="Accuracy (%)",
        title="Frozen first-draft policies on fresh diagnostic questions",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(directory / "accuracy-cost.png", dpi=180)
    plt.close(fig)
    lines = [
        "# First-draft continuation diagnostic",
        "",
        str(result["primary"]),
        "",
        "Previously observed pilot/validation data train and tune the policies. This is a fresh development diagnostic, not the official test. "
        "Both first-draft orientations are averaged within question; bootstrap resamples whole questions. "
        "Intervals condition on these fitted models; secondary comparisons are not multiplicity-adjusted.",
        "",
        "DART-SC-3 includes the third-draft majority branch with matched caps/decoders and our numeric parser. "
        "SC-Budget and full ReASC are not reproduced. Confidence uses saved mean decoder-warped log-probability, not ReASC's group confidence. "
        "Cached replay seconds exclude CPU router/encoder latency; cache collection expenditure is separate from policy inference cost. "
        "Manual scoring audit was waived, not completed. Novelty and superiority are not assumed.",
        "",
        "| Policy | Preference | Accuracy | Tokens/question |",
        "|---|---:|---:|---:|",
    ]
    for row in summaries:
        if row["parameter"] in (None, probe.PRIMARY):
            lines.append(
                f"| {row['policy']} | {row['parameter']} | {row['accuracy']:.3f} | {row['mean_charged_tokens']:.1f} |"
            )
    lines += [
        "",
        "Full curves and per-question outcomes are in curve.csv and report.json.",
        "",
        "![Curve](accuracy-cost.png)",
        "",
    ]
    (directory / "report.md").write_text("\n".join(lines))


def run_study(directory, progress=print):
    from .backend import environment, make_backend

    directory = Path(directory).resolve()
    with run_lock(directory):
        protocol = read_protocol(directory)
        freeze_models(directory, progress)  # Must exist before any fresh response is generated.
        path = directory / "runs.json"
        runs = verified(path) if path.exists() else {}
        state = {"pid": os.getpid(), "started_at": time.time(), "status": "running"}
        atomic_json(directory / "status.json", state)
        try:
            for mode in ("direct", "thinking"):
                config = from_dict(protocol["configs"][mode])
                if [q.to_dict() for q in load_questions(config.data_dir, config.split)] != protocol[
                    "diagnostic"
                ]:
                    raise ValueError("Diagnostic question allocation changed")
                backend = make_backend(config)
                identity = build_run_identity(
                    config, protocol["diagnostic"], backend.metadata, environment()
                )
                actual_path = Path(config.output_dir) / digest(identity)[:20]
                if mode in runs and Path(runs[mode]) != actual_path:
                    raise ValueError("Run identity changed on resume")
                runs[mode] = str(actual_path)
                atomic_json(path, envelope(runs))
                atomic_json(
                    directory / "status.json", state | {"stage": mode, "run_dir": str(actual_path)}
                )
                progress(f"Fresh diagnostic {mode}: {actual_path}")
                result = run(config, backend, progress)
                if result.resolve() != actual_path.resolve():
                    raise ValueError("Generation identity mismatch")
                del backend
                gc.collect()
                if not all(r["status"] == "completed" for r in load_run(result)[1]):
                    atomic_json(
                        directory / "status.json", state | {"status": "paused", "stage": mode}
                    )
                    return directory
                score_run(result)
            report = evaluate(directory, progress)
            atomic_json(
                directory / "status.json",
                state | {"status": "complete", "report": str(report), "finished_at": time.time()},
            )
            progress(f"Study complete: {report}")
        except BaseException as exc:
            atomic_json(directory / "status.json", state | {"status": "failed", "error": str(exc)})
            raise
    return directory
