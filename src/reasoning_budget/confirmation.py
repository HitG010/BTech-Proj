"""Prepare, collect, and analyze a fixed independent confirmation sample.

Preparation never invokes inference. Collection never fits a router and exposes
no intermediate comparative outcomes. Official test labels are never loaded.
"""

import gc
import hashlib
import os
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import yaml

from . import probe
from .config import from_dict
from .confirmation_stats import BOOTSTRAP_DRAWS, SECONDARY, SEED, analyze_policies
from .controller import Controller, choose_modes, feature_matrix
from .data import check_questions, load_questions, normalized, save_dataset
from .probe_study import implementation as router_implementation
from .probe_study import read_protocol as read_parent
from .probe_study import read_sources
from .records import Question
from .reporting import score_run
from .runner import (
    _usage,
    build_run_identity,
    implementation_digest,
    load_run,
    manifest_implementation,
    require_implementation,
    run,
)
from .scoring import SCORING_VERSION
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified

DEFAULT = "artifacts/confirmation/frozen-router-v1"
PARENT = "artifacts/probe/continuation-v1"
PACKAGES = ("numpy", "scipy", "scikit-learn", "torch", "transformers", "tokenizers", "datasets")


def implementation():
    folder = Path(__file__).parent
    return digest(
        {
            "router": router_implementation(),
            "generation": implementation_digest(),
            **{
                name: (folder / name).read_text()
                for name in ["confirmation.py", "confirmation_stats.py"]
            },
        }
    )


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def allocation_inventory(artifacts, output):
    """Exclude all existing dataset allocations and any previously generated prompts."""
    questions, sources = {}, {}
    for path in sorted(Path(artifacts).rglob("manifest.json")):
        if path.resolve().is_relative_to(Path(output).resolve()):
            continue
        raw = read_json(path)
        if "questions_sha256" in raw:
            rows = [q.to_dict() for q in load_questions(path.parent)]
        elif "payload" in raw and "identity" in raw["payload"]:
            manifest = verified(path)
            rows = manifest["identity"].get("questions", [])
        else:
            continue
        sources[str(path.resolve())] = digest(raw)
        for row in rows:
            if row["id"] in questions and normalized(questions[row["id"]]["prompt"]) != normalized(
                row["prompt"]
            ):
                raise ValueError("Previously allocated ID has conflicting question content")
            questions[row["id"]] = row
    return list(questions.values()), sources


def select_fresh(prompts, excluded, count=3100, seed=SEED):
    blocked_ids = {q["id"] for q in excluded}
    blocked_text = {normalized(q["prompt"]) for q in excluded}
    pool, seen = [], set()
    for index, prompt in enumerate(prompts):
        text = normalized(prompt)
        identifier = f"gsm8k-train-{digest(text)[:20]}"
        if not text or text in seen:
            continue
        seen.add(text)
        if identifier not in blocked_ids and text not in blocked_text:
            q = Question(identifier, "openai/gsm8k:main", "train", prompt)
            pool.append((index, q))
    if type(count) is not int or count < 2 or len(pool) < count:
        raise ValueError("Insufficient fresh questions or invalid fixed sample size")
    pool.sort(key=lambda row: digest({"seed": seed, "question": row[1].to_dict()}))
    chosen = pool[:count]
    check_questions([q for _, q in chosen])
    return chosen, len(pool)


def prepare(
    parent=PARENT,
    output=DEFAULT,
    data_dir="artifacts/data/gsm8k",
    artifacts="artifacts",
    cache_dir=".cache/huggingface",
    *,
    count=3100,
    batch_size=100,
):
    from datasets import Dataset

    parent, directory = Path(parent).resolve(), Path(output).resolve()
    request = {
        "parent": str(parent),
        "data_dir": str(Path(data_dir).resolve()),
        "artifacts": str(Path(artifacts).resolve()),
        "cache_dir": str(Path(cache_dir).resolve()),
        "count": count,
        "batch_size": batch_size,
    }
    with run_lock(directory):
        if (directory / "protocol.json").exists():
            existing = read_protocol(directory)
            if existing["request"] != request:
                raise ValueError("Frozen confirmation inputs differ; choose a new directory")
            if file_hash(parent / "models.json") != existing["model_file_sha256"]:
                raise ValueError("Original model file differs from the frozen copy")
            return directory
        prior = read_parent(parent)
        models = verified(parent / "models.json")
        report = verified(parent / "report.json")
        if report["protocol"] != digest(prior) or report["models_sha256"] != digest(models):
            raise ValueError("Parent study dependencies changed")
        base = prior["configs"]["direct"]
        if (
            (base["backend"] != "fake" and count != 3100)
            or type(batch_size) is not int
            or not 1 <= batch_size <= 100
        ):
            raise ValueError(
                "Real confirmation requires exactly 3100 questions and batches of at most 100"
            )
        dataset_manifest = read_json(Path(data_dir) / "manifest.json")
        revision = dataset_manifest["metadata"]["revision"]
        arrow = (
            Path(cache_dir) / "openai___gsm8k" / "main" / "0.0.0" / revision / "gsm8k-train.arrow"
        )
        dataset = Dataset.from_file(str(arrow))
        excluded, inventory = allocation_inventory(artifacts, directory)
        # Require the base manifest and every development/diagnostic question to be excluded.
        known = {q["id"] for q in excluded}
        mandatory = load_questions(data_dir)
        if (
            not {q.id for q in mandatory}.issubset(known)
            or not set(prior["excluded_ids"]).issubset(known)
            or not {q["id"] for q in prior["diagnostic"]}.issubset(known)
        ):
            raise ValueError("Exclusion inventory misses previously allocated questions")
        selected, eligible = select_fresh(
            dataset.select_columns(["question"])["question"], excluded, count
        )
        questions = [q for _, q in selected]
        # Only selected upstream-training answers enter isolated scoring artifacts.
        gold = {}
        for index, q in selected:
            answer = dataset[index]["answer"]
            if "####" not in answer:
                raise ValueError("Selected GSM8K answer lacks final-answer delimiter")
            gold[q.id] = answer.rsplit("####", 1)[1].strip()
        batches = []
        for start in range(0, count, batch_size):
            batch_id = f"batch-{start // batch_size:03d}"
            group = questions[start : start + batch_size]
            data_path = directory / "data" / batch_id
            save_dataset(
                data_path,
                group,
                {q.id: gold[q.id] for q in group},
                {
                    "role": "frozen-confirmation-only",
                    "seed": SEED,
                    "revision": revision,
                    "upstream": "train",
                    "batch": batch_id,
                    "never_reuse_for_training": True,
                },
            )
            configs = {}
            for mode, samples, token_limit, seconds in [
                ("direct", 3, 170000, 7200),
                ("thinking", 2, 530000, 18000),
            ]:
                config = from_dict(
                    dict(prior["configs"][mode])
                    | {
                        "name": f"confirmation-v1-{batch_id}-{mode}",
                        "data_dir": str(data_path),
                        "output_dir": str((directory / "runs").resolve()),
                        "samples": samples,
                        "limits": {
                            "max_tokens": token_limit,
                            "max_elapsed_seconds": seconds,
                            "job_seconds": 600,
                        },
                    }
                ).to_dict()
                configs[mode] = config
                config_path = directory / "configs" / f"{batch_id}-{mode}.yaml"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(yaml.safe_dump(config, sort_keys=False))
            batches.append(
                {
                    "id": batch_id,
                    "questions": [q.to_dict() for q in group],
                    "configs": configs,
                    "dataset_manifest": digest(read_json(data_path / "manifest.json")),
                }
            )
        (directory / "models.json").write_bytes((parent / "models.json").read_bytes())
        code = directory / "frozen_code"
        code.mkdir(exist_ok=True)
        code_hashes = {}
        for file in sorted(Path(__file__).parent.glob("*.py")):
            (code / file.name).write_bytes(file.read_bytes())
            code_hashes[file.name] = file_hash(file)
        (directory / "uv.lock").write_bytes(Path("uv.lock").read_bytes())
        protocol = {
            "schema_version": 1,
            "prepared_at": time.time(),
            "request": request,
            "sample_size": count,
            "responses_per_question": 5,
            "expected_responses": count * 5,
            "selection_seed": SEED,
            "selection": "sha256 seed and gold-free Question; normalized deduplication",
            "upstream": {
                "dataset": "openai/gsm8k",
                "subset": "main",
                "split": "train",
                "revision": revision,
                "arrow_sha256": file_hash(arrow),
                "cached_rows": len(dataset),
                "eligible_questions": eligible,
            },
            "excluded_ids": sorted(known),
            "excluded_normalized_prompts_sha256": digest(
                sorted({normalized(q["prompt"]) for q in excluded})
            ),
            "exclusion_inventory": inventory,
            "batches": batches,
            "parent_protocol_sha256": digest(prior),
            "parent_report_sha256": digest(report),
            "models_sha256": digest(models),
            "model_file_sha256": file_hash(directory / "models.json"),
            "parent_models_frozen_at": models["frozen_at"],
            "refitting_allowed": False,
            "implementation": implementation(),
            "packages": {p: version(p) for p in PACKAGES},
            "frozen_code_sha256": code_hashes,
            "lockfile_sha256": file_hash(directory / "uv.lock"),
            "scoring_version": SCORING_VERSION,
            "preference": 0.05,
            "primary": "joint minus confidence-continuation mean question-level utility",
            "test": "two-sided paired Student t test of zero mean difference, alpha=.05",
            "unit": "whole question; average two correlated first-draft orientations",
            "bootstrap": {
                "draws": BOOTSTRAP_DRAWS,
                "seed": SEED,
                "unit": "whole question",
                "role": "robustness interval, not alternate rejection rule",
            },
            "secondary": list(SECONDARY),
            "multiplicity": "Holm within four secondary comparisons; positive primary rejection gates confirmatory secondary claims",
            "stopping_rule": f"Analyze once after all {count * 5} responses complete; no outcome-based sample-size changes or exclusions",
            "resource_stop": "incomplete study; no comparative inference until fixed sample completes",
            "audit": prior["audit"],
            "official_test": "sealed; labels not loaded",
            "cloud_spend": 0,
            "baseline_scope": prior["baseline_scope"],
            "registration": "locally frozen, not externally preregistered",
            "max_charged_tokens": sum(
                c["limits"]["max_tokens"] for b in batches for c in b["configs"].values()
            ),
            "max_cumulative_hours": sum(
                c["limits"]["max_elapsed_seconds"] for b in batches for c in b["configs"].values()
            )
            / 3600,
        }
        atomic_json(directory / "protocol.json", envelope(protocol))
        atomic_json(
            directory / "status.json",
            {"status": "prepared", "generation_started": False, "expected_responses": count * 5},
        )
        _write_protocol_summary(directory, protocol)
    return directory


def read_protocol(directory):
    directory = Path(directory)
    protocol = verified(directory / "protocol.json")
    if (
        protocol["implementation"] != implementation()
        or protocol["scoring_version"] != SCORING_VERSION
    ):
        raise ValueError("Frozen implementation/scorer changed; do not mix confirmation runs")
    if protocol["packages"] != {p: version(p) for p in protocol["packages"]}:
        raise ValueError("Frozen packages changed")
    if (
        file_hash(directory / "models.json") != protocol["model_file_sha256"]
        or digest(verified(directory / "models.json")) != protocol["models_sha256"]
    ):
        raise ValueError("Frozen models changed")
    for name, expected in protocol["frozen_code_sha256"].items():
        if file_hash(directory / "frozen_code" / name) != expected:
            raise ValueError("Frozen code snapshot changed")
    if file_hash(directory / "uv.lock") != protocol["lockfile_sha256"]:
        raise ValueError("Frozen lockfile changed")
    questions = []
    for batch in protocol["batches"]:
        data_dir = Path(batch["configs"]["direct"]["data_dir"])
        if digest(read_json(data_dir / "manifest.json")) != batch["dataset_manifest"]:
            raise ValueError("Frozen scoring/dataset manifest changed")
        actual = [q.to_dict() for q in load_questions(data_dir, "train")]
        if actual != batch["questions"]:
            raise ValueError("Frozen confirmation questions changed")
        questions.extend(Question(**q) for q in actual)
    check_questions(questions)
    if len(questions) != protocol["sample_size"] or {q.id for q in questions}.intersection(
        protocol["excluded_ids"]
    ):
        raise ValueError("Sample size or disjointness violation")
    return protocol


def _checked_records(path, batch, mode):
    manifest, records = load_run(path)
    require_implementation(manifest, records, implementation_digest())
    if (
        manifest["identity"]["config"] != batch["configs"][mode]
        or manifest["identity"]["questions"] != batch["questions"]
        or manifest_implementation(manifest) != implementation_digest()
    ):
        raise ValueError("Run differs from frozen confirmation job specification")
    return manifest, records


def require_complete(directory, protocol):
    runs = verified(Path(directory) / "runs.json")
    expected = {f"{b['id']}/{mode}" for b in protocol["batches"] for mode in ("direct", "thinking")}
    if set(runs) != expected:
        raise ValueError("Confirmation incomplete; comparative analysis is locked")
    total = 0
    for batch in protocol["batches"]:
        for mode in ("direct", "thinking"):
            path = Path(runs[f"{batch['id']}/{mode}"])
            _, records = _checked_records(path, batch, mode)
            if not all(r["status"] == "completed" for r in records):
                raise ValueError("Confirmation incomplete; comparative analysis is locked")
            for r in records:
                attempt = verified(path / "attempts" / f"{r['attempt_id']}.json")
                if attempt["started_at"] <= protocol["prepared_at"]:
                    raise ValueError("Confirmation generation preceded protocol freeze")
            total += len(records)
    if total != protocol["expected_responses"]:
        raise ValueError("Unexpected completed response count")
    return runs


def status(directory):
    directory = Path(directory)
    protocol = read_protocol(directory)
    runs = verified(directory / "runs.json") if (directory / "runs.json").exists() else {}
    completed = failed = 0
    charged = elapsed = 0.0
    for batch in protocol["batches"]:
        for mode in ("direct", "thinking"):
            key = f"{batch['id']}/{mode}"
            if key not in runs or not (Path(runs[key]) / "manifest.json").exists():
                continue
            _, records = _checked_records(runs[key], batch, mode)
            completed += sum(r["status"] == "completed" for r in records)
            failed += sum(r["status"] == "failed" for r in records)
            tokens, seconds = _usage(Path(runs[key]))
            charged += tokens
            elapsed += seconds
    return {
        "state": read_json(directory / "status.json"),
        "completed": completed,
        "failed": failed,
        "expected": protocol["expected_responses"],
        "charged_tokens": int(charged),
        "elapsed_hours": elapsed / 3600,
        "comparative_outcomes": "available only after fixed sample completion",
    }


def run_study(directory, progress=print, max_batches=None):
    from .backend import environment, make_backend
    from .config import from_dict

    if max_batches is not None and (type(max_batches) is not int or max_batches < 1):
        raise ValueError("max_batches must be a positive integer")
    directory = Path(directory).resolve()
    with run_lock(directory):
        protocol = read_protocol(directory)
        path = directory / "runs.json"
        runs = verified(path) if path.exists() else {}
        state = {
            "status": "running",
            "pid": os.getpid(),
            "started_at": time.time(),
            "generation_started": True,
        }
        atomic_json(directory / "status.json", state)
        finished_batches, reference = 0, None
        try:
            for batch in protocol["batches"]:
                pending = []
                for mode in ("direct", "thinking"):
                    key = f"{batch['id']}/{mode}"
                    if key in runs and (Path(runs[key]) / "manifest.json").exists():
                        manifest, records = _checked_records(runs[key], batch, mode)
                        comparable = {
                            k: manifest["identity"][k] for k in ("backend", "environment")
                        }
                        if reference is not None and comparable != reference:
                            raise ValueError(
                                "Backend/environment changed across confirmation stages"
                            )
                        reference = comparable
                        if all(r["status"] == "completed" for r in records):
                            continue
                    pending.append(mode)
                if not pending:
                    continue
                if max_batches is not None and finished_batches >= max_batches:
                    atomic_json(
                        directory / "status.json",
                        state | {"status": "paused", "reason": "requested batch limit"},
                    )
                    return directory
                for mode in pending:
                    key = f"{batch['id']}/{mode}"
                    config = from_dict(batch["configs"][mode])
                    backend = make_backend(config)
                    identity = build_run_identity(
                        config, batch["questions"], backend.metadata, environment()
                    )
                    comparable = {k: identity[k] for k in ("backend", "environment")}
                    if reference is not None and comparable != reference:
                        raise ValueError("Backend/environment changed across confirmation stages")
                    reference = comparable
                    target = Path(config.output_dir) / digest(identity)[:20]
                    if key in runs and Path(runs[key]) != target:
                        raise ValueError("Run identity changed on resume")
                    runs[key] = str(target)
                    atomic_json(path, envelope(runs))
                    atomic_json(
                        directory / "status.json", state | {"stage": key, "run_dir": str(target)}
                    )
                    progress(f"Confirmation {key}: {target}")
                    actual = run(config, backend, progress)
                    del backend
                    gc.collect()
                    if actual.resolve() != target.resolve():
                        raise ValueError("Generation identity mismatch")
                    if not all(
                        r["status"] == "completed" for r in _checked_records(actual, batch, mode)[1]
                    ):
                        atomic_json(
                            directory / "status.json",
                            state
                            | {"status": "paused", "stage": key, "reason": "generation incomplete"},
                        )
                        return directory
                finished_batches += 1
            require_complete(directory, protocol)
            atomic_json(directory / "status.json", state | {"stage": "final-analysis"})
            result = evaluate(directory, progress)
            atomic_json(
                directory / "status.json",
                state | {"status": "complete", "report": str(result), "finished_at": time.time()},
            )
            progress(f"Confirmation complete: {result}")
        except BaseException as exc:
            atomic_json(directory / "status.json", state | {"status": "failed", "error": str(exc)})
            raise
    return directory


def evaluate(directory, progress=print):
    directory = Path(directory)
    protocol = read_protocol(directory)
    if not (directory / "runs.json").exists():
        raise ValueError("Confirmation incomplete; comparative analysis is locked")
    runs = require_complete(directory, protocol)  # No scoring or labels before this gate.
    for path in runs.values():
        score_run(path)
    questions = [q for batch in protocol["batches"] for q in batch["questions"]]
    paths = [runs[f"{b['id']}/{m}"] for b in protocol["batches"] for m in ("direct", "thinking")]
    data, sources, _ = read_sources(paths, expected=questions, diagnostic=True)
    saved = verified(directory / "models.json")
    x, metadata = feature_matrix([Question(**q) for q in questions], progress=progress)
    predictions = Controller.from_dict(saved["question_ridge"]).predict(x)
    state_x = probe.state_features(x, data["direct_results"])
    rows = probe.continuation_rows(data)
    direct, thinking = data["direct"][:, :2].mean(1), data["thinking"].mean(1)
    policies = {
        "always-direct": direct,
        "always-thinking": thinking,
        "DART-SC-2-adapted": rows[:, :, 1].mean(1),
        "DART-SC-3-adapted": probe.dart_sc3(data),
        "question-ridge": np.where(choose_modes(predictions, 0.05)[:, None] == 0, direct, thinking),
        "random-half": 0.5 * direct + 0.5 * thinking,
    }
    for name, model in saved["models"].items():
        policies[name] = probe.selected_rows(rows, probe.actions(model["model"], state_x, 0.05))
    for name, settings in saved["thresholds"].items():
        policies[name] = probe.selected_rows(
            rows, probe.confidence_actions(state_x[:, -4], settings[probe.PREFERENCES.index(0.05)])
        )
    for name, kwargs in [
        ("joint-binary", {"binary": True}),
        ("joint-ignore-harm", {"ignore_harm": True}),
    ]:
        policies[name] = probe.selected_rows(
            rows, probe.actions(saved["models"]["joint"]["model"], state_x, 0.05, **kwargs)
        )
    result = {
        "protocol_sha256": digest(protocol),
        "models_sha256": digest(saved),
        "sources": sources,
        "question_ids": [q["id"] for q in questions],
        "inference": analyze_policies(policies),
        "summaries": {
            name: {
                "accuracy": float(r[:, 0].mean()),
                "tokens_per_question": float(r[:, 1].mean()),
                "cached_seconds_per_question": float(r[:, 2].mean()),
            }
            for name, r in policies.items()
        },
        "per_question": {name: r.tolist() for name, r in policies.items()},
        "features": metadata,
        "actual_expenditure": {
            key: dict(zip(["charged_tokens", "elapsed_seconds"], _usage(Path(p)), strict=True))
            for key, p in runs.items()
        },
        "audit": protocol["audit"],
        "baseline_scope": protocol["baseline_scope"],
    }
    atomic_json(directory / "report.json", envelope(result))
    primary = result["inference"]["primary"]
    lines = [
        "# Frozen-router confirmation",
        "",
        f"Fixed sample: {len(questions)} fresh upstream-training questions; lambda=.05.",
        "",
        f"Primary result: **{primary['direction']}**. Mean utility difference {primary['mean_difference']:.6f}; two-sided p={primary['p_two_sided']:.6g}; 95% t interval {primary['t_ci95']}; bootstrap interval {primary['bootstrap_ci95']}.",
        "",
        "| Policy | Accuracy | Charged tokens/question |",
        "|---|---:|---:|",
    ]
    for name, summary in result["summaries"].items():
        lines.append(
            f"| {name} | {summary['accuracy']:.4f} | {summary['tokens_per_question']:.1f} |"
        )
    lines += [
        "",
        "## Predeclared secondary comparisons",
        "",
        "| Joint minus comparator | Utility difference | Holm p | Confirmatory positive superiority |",
        "|---|---:|---:|---|",
    ]
    for name, row in result["inference"]["secondary"].items():
        lines.append(
            f"| {name} | {row['mean_difference']:.6f} | {row['p_holm']:.6g} | {row['positive_superiority']} |"
        )
    lines += [
        "",
        "Secondary claims require positive primary rejection. Other policy comparisons are descriptive. "
        "A non-rejection does not establish equivalence. The prior diagnostic is excluded. Models were not refitted. "
        "This is not the official GSM8K test; pretraining contamination is unknown. DART is the matched-cap SC adaptation; "
        "full SC-Budget and ReASC are not reproduced. Accuracy and token costs do not include CPU routing/prefill costs. "
        "Cached seconds are not measured end-to-end policy latency. The manual scoring audit was waived, not completed. "
        "Intervals condition on these fixed models; novelty and cross-model generalization are separate claims.",
        "",
    ]
    (directory / "report.md").write_text("\n".join(lines))
    return directory / "report.md"


def _write_protocol_summary(directory, protocol):
    text = f"""# Frozen confirmation protocol

Prepared locally before generation; not externally preregistered.

- Sample: {protocol["sample_size"]} fresh questions, {protocol["expected_responses"]} responses, {len(protocol["batches"])} batches.
- Current router and comparators copied byte-for-byte. No retraining or retuning.
- Models SHA256: `{protocol["model_file_sha256"]}`.
- Protocol SHA256: `{digest(protocol)}`.
- Cached upstream training revision: `{protocol["upstream"]["revision"]}`.
- Exclusions: {len(protocol["excluded_ids"])} previously allocated IDs plus normalized prompt matches.
- Primary: joint versus frozen confidence continuation at lambda=.05, two-sided paired t test, alpha=.05.
- Whole questions are the statistical unit; two draft orientations are averaged inside each question.
- Secondary family: gain ridge, always direct, always thinking, DART SC-3; Holm correction with a positive-primary gate.
- Bootstrap robustness interval: {BOOTSTRAP_DRAWS} whole-question draws, seed {SEED}.
- Analyze once, only after the complete fixed sample. Operational batch pauses are allowed; outcome-based stopping is not.
- Official test labels remain sealed. This sample is reserved permanently for confirmation.
- Token ceiling: {protocol["max_charged_tokens"]:,}; cumulative stage time ceiling: {protocol["max_cumulative_hours"]:.0f} hours.
- Cloud spend: $0; local MPS with original precision/decoding. The scoring audit remains waived.

Expected actual duration is about 125–142 local hours, not the maximum time ceiling.
This planning estimate is conditional on previous throughput, variance, and effect;
80% power does not guarantee a favorable or significant result. No broad full-DART,
ReASC, cross-task, cross-model or originality claim follows from this comparison.

```sh
uv run --locked rb confirm status {directory}
# Run when ready; all batches and final reporting proceed automatically:
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \\
  caffeinate -i uv run --locked rb confirm run {directory}
# Or collect one unfinished batch, preserving the no-interim-analysis rule:
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \\
  caffeinate -i uv run --locked rb confirm run {directory} --batches 1
```

See `protocol.json`, copied `models.json`, `frozen_code/`, `uv.lock`, and
`configs/` for the full immutable specification. `status.json` is operational
state, not proof that its PID is still alive. `rb confirm status` exposes only
completion and expenditure until final analysis. Generation has not been started
by preparation.
"""
    (directory / "protocol.md").write_text(text)
