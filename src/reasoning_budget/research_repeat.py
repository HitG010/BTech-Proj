"""Frozen Phase 2 repeat panel; reference answers remain deferred to completion."""

import argparse
import importlib.metadata
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import yaml

from . import repeat_stats, scoring_v7
from .bridge_worker import inspect
from .config import from_dict, load_config
from .confirmation import file_hash
from .controller import feature_matrix
from .data import load_questions
from .records import Question
from .research_data import load_allocation
from .runner import _usage, load_run, require_implementation, run
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified

ROOT = "artifacts/research/data-efficiency-v1"
CONFIG = "configs/research-repeat-v1.yaml"
STUDY = "repeat-panel-v1"
SOURCES = (
    "research_repeat.py", "repeat_stats.py", "bridge_worker.py", "backend.py",
    "runner.py", "config.py", "records.py", "data.py", "storage.py", "controller.py",
    "research_data.py", "confirmation.py", "scoring.py", "scoring_v6.py", "scoring_v7.py",
)


def implementation():
    package = Path(__file__).parent
    return digest({name: (package / name).read_text() for name in SOURCES})


def partition(questions):
    ordered = sorted(questions, key=lambda q: digest({"seed": 20261002, "question": q.to_dict()}))
    return {q.id: i % 5 for i, q in enumerate(ordered)}


def _validate_template(config, allocation):
    if config.samples != 8 or config.modes != ["direct", "thinking"] or config.split != "repeat":
        raise ValueError("Repeat panel requires eight samples in both fixed modes")
    if config.backend == "fake":
        return
    base = from_dict(allocation["generation_constraints"]["config_snapshot"]).to_dict()
    actual = config.to_dict()
    for key in ["backend", "answer_tokens", "reasoning_tokens", "prompt_suffix", "closure_text",
                "model", "direct", "thinking"]:
        if actual[key] != base[key]:
            raise ValueError(f"Repeat decoder differs from bridged setting {key}")
    if config.seed != 20261002 or actual["limits"] != {
        "max_tokens": 1400000, "max_elapsed_seconds": 43200,
        "job_seconds": 600, "max_consecutive_failures": 3,
    }:
        raise ValueError("Real repeat requires the fixed seed and cumulative local limits")


def prerequisites(root, allocation):
    """Verify the completed foundation without reference-answer access."""
    from .research_bridge import checked_arm
    from .research_bridge import read_protocol as read_bridge

    bridge = root / "bridge-v1"
    protocol = read_bridge(bridge)
    report = verified(bridge / "report.json")
    if not report["engineering_gate_passed"] or protocol["allocation_sha256"] != digest(allocation):
        raise ValueError("Repeat preparation requires passed engineering gates on the same allocation")
    for arm in protocol["arms"]:
        _, rows = checked_arm(bridge, protocol, arm)
        if len(rows) != 100 or any(r["status"] != "completed" for r in rows) or digest(rows) != report["summaries"][arm]["records_sha256"]:
            raise ValueError("Repeat preparation requires the unchanged completed bridge")
    preflight = root / "parser-v7-preflight-v1"
    parser_protocol = verified(preflight / "protocol.json")
    review = verified(preflight / "compatibility-review.json")
    verification = verified(preflight / "verification.json")
    if parser_protocol["implementation_sha256"] != scoring_v7.implementation_digest() or review["decision"] != "pass" or verification["changed_original_files"]:
        raise ValueError("Repeat preparation requires passed unchanged numeric-v7 preflight")
    return {"bridge_protocol_sha256": digest(protocol), "bridge_report_sha256": digest(report),
            "parser_protocol_sha256": digest(parser_protocol),
            "parser_verification_sha256": digest(verification)}


def prepare(root=ROOT, config_path=CONFIG, *, encoder=feature_matrix, resolver=inspect):
    """Freeze questions, features, jobs and analysis without accessing any answer."""
    root = Path(root).resolve()
    study = root / STUDY
    request = {"root": str(root), "config_path": str(Path(config_path).resolve())}
    with run_lock(study):
        if (study / "protocol.json").exists():
            protocol = read_protocol(study)
            if protocol["request"] != request:
                raise ValueError("Repeat request changed; choose a new study identity")
            return study
        allocation = load_allocation(root / "allocations")
        selected = allocation["roles"]["repeat"]
        questions = [Question(**row["question"]) for row in selected]
        config = load_config(config_path)
        _validate_template(config, allocation)
        foundation = prerequisites(root, allocation) if config.backend != "fake" else {"synthetic": True}
        if config.backend != "fake" and len(questions) != 50:
            raise ValueError("Real repeat panel requires the allocated 50 questions")
        if len(questions) < 10 or any(q.split != "repeat" for q in questions):
            raise ValueError("Repeat role must contain at least ten exact questions")
        if config.backend == "fake" and any(not q.source.startswith("fixture") for q in questions):
            raise ValueError("Synthetic allowance requires explicit fixture questions")
        dataset = root / "data" / "repeat"
        rows = [q.to_dict() for q in questions]
        manifest = {"schema_version": 1, "metadata": {
            "role": "repeat", "upstream": "train", "allocation_sha256": digest(allocation),
            "revision": allocation["source"]["revision"], "gold_deferred": True,
            "never_use_for_confirmation": True,
        }, "questions_sha256": digest(rows), "gold_sha256": None,
            "splits": {"repeat": [q.id for q in questions]}}
        with run_lock(dataset):
            if (dataset / "gold.json").exists():
                raise ValueError("Repeat reference gold must remain deferred")
            if (dataset / "manifest.json").exists():
                if read_json(dataset / "manifest.json") != manifest or read_json(dataset / "questions.json") != rows:
                    raise ValueError("Question-only repeat dataset changed")
            else:
                atomic_json(dataset / "questions.json", rows)
                atomic_json(dataset / "manifest.json", manifest)
        values = config.to_dict() | {"data_dir": str(dataset), "output_dir": str(study / "runs")}
        frozen_config = study / "config.yaml"
        frozen_config.write_text(yaml.safe_dump(values, sort_keys=False))
        snapshot, _, _ = resolver(frozen_config)
        expected_package = str(Path(__file__).parent.resolve())
        if snapshot["package_root"] != expected_package:
            raise ValueError("Repeat preflight imported a different package")
        if Path(snapshot["run_dir"]).exists():
            raise ValueError("Repeat preparation refuses a preexisting generation directory")
        jobs = snapshot["jobs"]
        cells = {(j["question_id"], j["mode"], j["sample"]) for j in jobs}
        expected = {(q.id, mode, s) for q in questions for mode in config.modes for s in range(8)}
        if cells != expected or len(jobs) != len(expected) or len({j["seed"] for j in jobs}) != len(jobs):
            raise ValueError("Repeat cells or independent per-cell seeds are invalid")
        if snapshot["planned_max_tokens"] > config.limits.max_tokens:
            raise ValueError("Repeat budget cannot reserve all planned jobs")
        x, metadata = encoder(questions, str(study / "feature-cache"), lambda _: None)
        x = np.asarray(x)
        if x.ndim != 2 or len(x) != len(questions) or not np.isfinite(x).all():
            raise ValueError("Invalid question-only feature matrix")
        features = {"questions": rows, "features": x.tolist(), "metadata": metadata}
        atomic_json(study / "question-features.json", envelope(features))
        frozen = study / "frozen_code" / "reasoning_budget"
        frozen.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for path in sorted(Path(__file__).parent.glob("*.py")):
            shutil.copy2(path, frozen / path.name)
            hashes[path.name] = file_hash(path)
        protocol = {
            "schema_version": 1, "request": request, "prepared_at": time.time(),
            "implementation": implementation(), "scoring_version": scoring_v7.SCORING_VERSION,
            "scoring_implementation_sha256": scoring_v7.implementation_digest(),
            "allocation_sha256": digest(allocation), "selected": selected,
            "foundation": foundation,
            "analysis": repeat_stats.ANALYSIS, "folds": partition(questions),
            "question_features_sha256": digest(features), "snapshot": snapshot,
            "template_config_sha256": file_hash(config_path), "config_sha256": file_hash(frozen_config),
            "dataset_file_sha256": {n: file_hash(dataset / n) for n in ["manifest.json", "questions.json"]},
            "source_file_sha256": hashes, "source_package": expected_package,
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "collection_permission": {"role": "repeat", "allocation_sha256": digest(allocation),
                "max_responses": len(jobs), "cloud_spend_usd": 0,
                "scope": "Separate local collection command only; preparation does not start generation."},
            "gold_policy": "No reference answers during prepare/collect/status; only selected training answers after all jobs complete.",
        }
        atomic_json(study / "protocol.json", envelope(protocol))
        atomic_json(study / "status.json", {"state": "prepared", "generation_started": False,
            "expected_responses": len(jobs), "analysis": "locked", "gold_materialized": False})
    return study


def read_protocol(study):
    study = Path(study).resolve()
    p = verified(study / "protocol.json")
    if p["schema_version"] != 1 or p["implementation"] != implementation() or p["analysis"] != repeat_stats.ANALYSIS:
        raise ValueError("Frozen repeat implementation or analysis changed")
    if p["scoring_version"] != "numeric-v7" or p["scoring_implementation_sha256"] != scoring_v7.implementation_digest():
        raise ValueError("Frozen repeat scorer changed")
    allocation = load_allocation(Path(p["request"]["root"]) / "allocations")
    if digest(allocation) != p["allocation_sha256"] or allocation["roles"]["repeat"] != p["selected"]:
        raise ValueError("Frozen repeat allocation or role changed")
    config = load_config(study / "config.yaml")
    _validate_template(config, allocation)
    if config.backend != "fake" and prerequisites(Path(p["request"]["root"]), allocation) != p["foundation"]:
        raise ValueError("Frozen repeat foundation evidence changed")
    if file_hash(p["request"]["config_path"]) != p["template_config_sha256"] or file_hash(study / "config.yaml") != p["config_sha256"]:
        raise ValueError("Frozen repeat configuration changed")
    for name, sha in p["source_file_sha256"].items():
        if file_hash(Path(p["source_package"]) / name) != sha or file_hash(study / "frozen_code" / "reasoning_budget" / name) != sha:
            raise ValueError("Frozen repeat package source changed")
    if p["source_package"] != str(Path(__file__).parent.resolve()):
        raise ValueError("Repeat reader imported a different package")
    packages = p["snapshot"]["identity"]["environment"]["packages"]
    if packages != {name: importlib.metadata.version(name) for name in packages}:
        raise ValueError("Frozen repeat package versions changed")
    dataset = Path(config.data_dir)
    if (dataset / "gold.json").exists():
        raise ValueError("Repeat gold must remain deferred outside the question dataset")
    for name, sha in p["dataset_file_sha256"].items():
        if file_hash(dataset / name) != sha:
            raise ValueError("Frozen repeat question dataset changed")
    questions = load_questions(dataset)
    if [q.to_dict() for q in questions] != [r["question"] for r in p["selected"]] or p["folds"] != partition(questions):
        raise ValueError("Repeat questions or folds changed")
    features = verified(study / "question-features.json")
    if digest(features) != p["question_features_sha256"] or features["questions"] != [q.to_dict() for q in questions]:
        raise ValueError("Frozen repeat features changed")
    return p


def checked_run(study, protocol):
    snapshot = protocol["snapshot"]
    path = Path(snapshot["run_dir"])
    if not (path / "manifest.json").exists():
        return None, []
    manifest, rows = load_run(path)
    if manifest["identity"] != snapshot["identity"] or manifest["jobs"] != snapshot["jobs"] or manifest["scoring_gold_sha256"] is not None or manifest["run_id"] != digest(snapshot["identity"]):
        raise ValueError("Repeat run differs from frozen identity, jobs or deferred gold")
    require_implementation(manifest, rows, snapshot["generation_implementation"])
    jobs = {job["id"]: job for job in snapshot["jobs"]}
    # Interrupted reservations and superseded retries still consume the ledger;
    # they must obey the same pre-freeze/source boundary as final responses.
    for attempt_path in (path / "attempts").glob("*.json"):
        attempt = verified(attempt_path)
        if attempt["started_at"] < protocol["prepared_at"]:
            raise ValueError("Repeat generation preceded protocol freeze")
        if attempt["job_id"] not in jobs or attempt["implementation_sha256"] != snapshot["generation_implementation"]:
            raise ValueError("Repeat attempt has unknown job or mixed implementation")
    for session_path in (path / "sessions").glob("*.json"):
        session = verified(session_path)
        if session["started_at"] < protocol["prepared_at"] or session["implementation_sha256"] != snapshot["generation_implementation"]:
            raise ValueError("Repeat setup session preceded freeze or changed implementation")
    for row in rows:
        if row["status"] != "pending":
            attempt = verified(path / "attempts" / f"{row['attempt_id']}.json")
            if attempt["started_at"] < protocol["prepared_at"]:
                raise ValueError("Repeat generation preceded protocol freeze")
    tokens, seconds = _usage(path)
    limits = snapshot["config"]["limits"]
    if tokens > limits["max_tokens"] or seconds > limits["max_elapsed_seconds"]:
        raise ValueError("Repeat cumulative limits were exceeded")
    return manifest, rows


def status(study):
    p = read_protocol(study)
    manifest, rows = checked_run(study, p)
    tokens, seconds = _usage(Path(p["snapshot"]["run_dir"])) if manifest else (0, 0)
    completed = sum(r["status"] == "completed" for r in rows)
    expected = len(p["snapshot"]["jobs"])
    return {"completed": completed, "expected": expected,
            "failed": sum(r["status"] == "failed" for r in rows),
            "charged_tokens": tokens, "cumulative_hours": seconds / 3600,
            "analysis": "eligible" if completed == expected else "locked",
            "generation_started": manifest is not None}


def collect(study, progress=print):
    study = Path(study).resolve()
    with run_lock(study):
        p = read_protocol(study)
        checked_run(study, p)
        snapshot, config, engine = inspect(study / "config.yaml")
        if snapshot != p["snapshot"]:
            raise ValueError("Resolved repeat backend/environment differs from preflight")
        atomic_json(study / "status.json", {"state": "collecting", "generation_started": True,
            "expected_responses": len(snapshot["jobs"]), "analysis": "locked", "gold_materialized": False})
        path = run(config, backend=engine, progress=progress)
        if str(path) != snapshot["run_dir"]:
            raise ValueError("Repeat run identity changed")
        state = status(study)
        atomic_json(study / "status.json", state | {"state": "collected" if state["analysis"] == "eligible" else "paused",
                                                   "gold_materialized": False})
        return state


def _selected_gold(protocol):
    from datasets import Dataset

    selected = protocol["selected"]
    source = load_allocation(Path(protocol["request"]["root"]) / "allocations")["source"]
    # Physical source is pinned training Arrow; project and select before fetching values.
    answers = Dataset.from_file(source["arrow_path"]).select_columns(["answer"]).select(
        [r["upstream_index"] for r in selected])["answer"]
    gold = {}
    for row, answer in zip(selected, answers):
        if "####" not in answer:
            raise ValueError("Selected repeat training answer lacks final delimiter")
        value = answer.rsplit("####", 1)[1].strip()
        scoring_v7.v5.numeric(value)
        gold[row["question"]["id"]] = value
    return gold


def score(study):
    study = Path(study).resolve()
    with run_lock(study):
        p = read_protocol(study)
        with run_lock(p["snapshot"]["run_dir"]):
            manifest, rows = checked_run(study, p)
            if len(rows) != len(p["snapshot"]["jobs"]) or any(r["status"] != "completed" for r in rows):
                raise ValueError("Repeat analysis/gold locked until the complete fixed endpoint")
            gold = _selected_gold(p)
            if set(gold) != {r["question"]["id"] for r in p["selected"]}:
                raise ValueError("Repeat gold IDs differ from the isolated role")
            artifact = {"protocol_sha256": digest(p), "allocation_sha256": p["allocation_sha256"],
                "run_id": manifest["run_id"], "records_sha256": digest(rows), "gold_sha256": digest(gold),
                "scoring_version": "numeric-v7", "scoring_implementation_sha256": p["scoring_implementation_sha256"],
                "scores": [scoring_v7.score_record(r, gold[r["job"]["question_id"]]) for r in rows]}
            output = study / "scores.numeric-v7.json"
            if output.exists() and verified(output) != artifact:
                raise ValueError("Frozen repeat score cache identity changed")
            if not output.exists():
                atomic_json(output, envelope(artifact))
            return artifact


def analyze(study):
    # score() independently enforces the endpoint before any gold or extraction.
    artifact = score(study)
    study = Path(study).resolve()
    with run_lock(study):
        p = read_protocol(study)
        _, rows = checked_run(study, p)
        if digest(rows) != artifact["records_sha256"]:
            raise ValueError("Repeat records changed after scoring")
        features = verified(study / "question-features.json")
        ids = [r["question"]["id"] for r in p["selected"]]
        idx = {q: i for i, q in enumerate(ids)}
        scores = {s["job_id"]: s for s in artifact["scores"]}
        direct = np.empty((len(ids), 8, 3))
        thinking = np.empty_like(direct)
        drafts = np.empty((len(ids), 8, 4))
        for row in rows:
            result, job = row["result"], row["job"]
            i, s = idx[job["question_id"]], job["sample"]
            target = direct if job["mode"] == "direct" else thinking
            target[i, s] = [float(scores[job["id"]]["correct"]),
                result["reasoning_tokens"] + result["answer_tokens"] + result["inserted_tokens"],
                result["elapsed_seconds"]]
            if job["mode"] == "direct":
                confidence = result["mean_generated_logprob"]
                if confidence is None or not math.isfinite(confidence):
                    raise ValueError("Finite post-warper first-draft confidence is required")
                # Gold-free feature construction; correctness is never an input.
                _, valid = scoring_v7.extract_record(row)
                drafts[i, s] = [confidence, np.log1p(result["answer_tokens"]),
                                float(valid == "ok"), float(result["answer_truncated"])]
        statistics = repeat_stats.analyze(ids, np.asarray(features["features"]), direct,
                                          thinking, drafts, p["folds"], spec=p["analysis"])
        tokens, seconds = _usage(Path(p["snapshot"]["run_dir"]))
        report = {"protocol_sha256": digest(p), "scores_sha256": digest(artifact),
            "statistics": statistics, "collection_charged_tokens_all_attempts": tokens,
            "collection_hours_all_attempts_and_setup": seconds / 3600,
            "synthetic": p["snapshot"]["config"]["backend"] == "fake",
            "official_test_gold_opened": False, "cloud_spend_usd": 0,
            "human_audit": "waived; automated/agent only"}
        output = study / "report.json"
        if output.exists() and verified(output) != report:
            raise ValueError("Frozen repeat report identity changed")
        if not output.exists():
            atomic_json(output, envelope(report))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--root", default=ROOT)
    prep.add_argument("--config", default=CONFIG)
    for name in ["status", "collect", "score", "analyze"]:
        command = sub.add_parser(name)
        command.add_argument("--study", default=str(Path(ROOT) / STUDY))
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.root, args.config))
    else:
        result = getattr(sys.modules[__name__], args.command)(args.study)
        if args.command == "score":
            print(f"{len(result['scores'])} scores: {Path(args.study) / 'scores.numeric-v7.json'}")
        elif args.command == "analyze":
            print(f"Report: {Path(args.study) / 'report.json'}; scale acquisition: {result['statistics']['scale_acquisition']}")
        else:
            print(result)


if __name__ == "__main__":
    main()
