"""Freeze and execute a small paired legacy/v3 protocol bridge on unused data."""

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import yaml

from .config import load_config
from .confirmation import file_hash
from .data import save_dataset
from .records import Question
from .reporting import bootstrap, score_run, scoring_digest
from .runner import _usage, load_run
from .scoring import SCORING_VERSION
from .storage import atomic_json, digest, envelope, run_lock, verified

ROOT = "artifacts/research/data-efficiency-v1"
LEGACY = "artifacts/legacy/router-studies-6999eb5/src"
WORKER = Path(__file__).with_name("bridge_worker.py")
ANALYSIS = {
    "version": "paired-protocol-bridge-v1",
    "comparison": "v3 minus legacy; fixed 25-question engineering diagnostic",
    "scorer": "numeric-v5 on both arms",
    "preference": 0.05,
    "bootstrap_unit": "whole question with both independent draws retained",
    "bootstrap_seed": 20261001,
    "bootstrap_draws": 2000,
    "stopping": "100 completed cells per arm; no comparative analysis before both finish",
    "retry_policy": "at most three worker invocations per arm per run command, same cumulative budgets",
    "gate": {
        "max_answer_truncation_per_mode": 0.05,
        "max_parse_failure_per_mode": 0.05,
        "max_observed_accuracy_loss_per_mode": 0.10,
        "raw_direct_confidence_coverage": 1.0,
        "max_projected_repeat_panel_local_hours": 48,
    },
    "scope": "Behavior, reliability, cost and throughput; no superiority or equivalence claim",
}


def implementation():
    root = Path(__file__).parent
    return digest(
        {name: (root / name).read_text() for name in [
            "research_bridge.py", "bridge_worker.py", "research_data.py", "reporting.py",
            "scoring.py", "data.py", "storage.py",
        ]}
    )


def worker_environment(source):
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(Path(source).resolve()), HF_HUB_OFFLINE="1",
        PYTHONUNBUFFERED="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1", PYTORCH_ENABLE_MPS_FALLBACK="0",
    )
    return env


def resolve_arm(config_path, source, output):
    subprocess.run(
        [sys.executable, str(WORKER), "inspect", "--config", str(config_path),
         "--output", str(output)],
        env=worker_environment(source), check=True,
    )
    return verified(output)


def _validate_pair(arms):
    legacy, new = [arms[name]["snapshot"] for name in ("legacy", "v3")]
    for key in [
        "seed", "data_dir", "split", "samples", "modes", "answer_tokens",
        "reasoning_tokens", "prompt_suffix", "model", "direct", "thinking",
    ]:
        if legacy["config"][key] != new["config"][key]:
            raise ValueError(f"Bridge arms differ in matched setting {key}")
    if legacy["identity"]["environment"] != new["identity"]["environment"]:
        raise ValueError("Bridge arms differ in execution environment")
    if legacy["identity"]["questions"] != new["identity"]["questions"]:
        raise ValueError("Bridge question identities differ")
    def cells(arm):
        return {(job["question_id"], job["mode"], job["sample"]): job["seed"]
                for job in arm["jobs"]}

    if cells(legacy) != cells(new) or any(len(cells(arm)) != len(arm["jobs"]) for arm in (legacy, new)):
        raise ValueError("Bridge cells or paired seeds differ")
    for snapshot in (legacy, new):
        if snapshot["planned_max_tokens"] > snapshot["config"]["limits"]["max_tokens"]:
            raise ValueError("Bridge cannot reserve its planned jobs")
    if legacy["run_dir"] == new["run_dir"]:
        raise ValueError("Bridge arms must have isolated run directories")
    for field in ["model_name", "model_revision", "tokenizer_revision", "chat_template_sha256",
                  "closure_tokens", "device", "dtype", "attention", "batch_size", "continuation"]:
        old_backend, new_backend = legacy["identity"]["backend"], new["identity"]["backend"]
        if old_backend.get(field) != new_backend.get(field):
            raise ValueError(f"Bridge resolved backends differ in {field}")


def _validate_sources(arms):
    for details in arms.values():
        expected = str((Path(details["source"]) / "reasoning_budget").resolve())
        if details["snapshot"]["package_root"] != expected:
            raise ValueError("Worker imported a different source package")
    if arms["v3"]["snapshot"]["config"]["backend"] == "fake":
        return  # Synthetic integrity fixtures make no claim to legacy inference.
    legacy_root = Path(arms["legacy"]["source"]).parent
    head = subprocess.check_output(["git", "-C", str(legacy_root), "rev-parse", "HEAD"], text=True).strip()
    pin = subprocess.check_output(["git", "-C", str(legacy_root), "rev-parse", "6999eb5^{commit}"], text=True).strip()
    dirty = subprocess.check_output([
        "git", "-C", str(legacy_root), "status", "--porcelain", "--untracked-files=no",
        "--", "src/reasoning_budget",
    ], text=True).strip()
    if head != pin or dirty:
        raise ValueError("Real bridge requires unmodified legacy source pinned at 6999eb5")
    old = arms["legacy"]["snapshot"]["identity"]["backend"]
    new = arms["v3"]["snapshot"]["identity"]["backend"]
    if new.get("generation_protocol") != "qwen3-boxed-budget-v3" or new.get("eos_token_ids") != [151643, 151645]:
        raise ValueError("New bridge decoder does not use the fixed v3 EOS protocol")
    if any(old["decoder_configs"][mode]["eos_token_id"] != 151645 for mode in ("direct", "thinking")):
        raise ValueError("Legacy bridge decoder does not use its fixed single EOS")
    if old["closure_ids"] != [151668, 271] or new["closure_ids"] != old["closure_ids"]:
        raise ValueError("Bridge closure IDs differ from the fixed matched closure")


def prepare(root=ROOT, config_path="configs/research-gsm8k-v3.yaml", legacy_src=LEGACY,
            *, resolver=resolve_arm):
    from datasets import Dataset

    from .research_data import load_allocation

    root, study = Path(root).resolve(), Path(root).resolve() / "bridge-v1"
    request = {"root": str(root), "config_path": str(Path(config_path).resolve()),
               "legacy_src": str(Path(legacy_src).resolve())}
    with run_lock(study):
        if (study / "protocol.json").exists():
            frozen = read_protocol(study)
            if frozen["request"] != request:
                raise ValueError("Bridge inputs differ; choose a new study identity")
            return study
        allocation = load_allocation(root / "allocations")
        rows = allocation["roles"]["bridge"]
        questions = [Question(**row["question"]) for row in rows]
        config = load_config(config_path)
        if config.backend != "fake" and file_hash(config_path) != allocation[
            "generation_constraints"
        ]["config_sha256"]:
            raise ValueError("Bridge config differs from the frozen allocation settings")
        if config.backend != "fake" and (
            len(rows) != 25 or config.samples != 2 or config.answer_tokens != 512
            or config.reasoning_tokens != 2048 or config.closure_text != "</think>\n\n"
        ):
            raise ValueError("Real bridge requires the fixed 25-question 2048/512 protocol")
        if set(config.modes) != {"direct", "thinking"} or config.samples != 2:
            raise ValueError("Bridge requires two samples in both modes")
        # Selection/role allocation has already frozen, without any answer access.
        # Read only the selected training answers, never base gold or official test.
        arrow = Path(allocation["source"]["arrow_path"])
        if file_hash(arrow) != allocation["source"]["arrow_sha256"]:
            raise ValueError("Frozen upstream training source changed")
        selected = Dataset.from_file(str(arrow)).select_columns(["answer"]).select(
            [row["upstream_index"] for row in rows]
        )
        gold = {}
        for row, answer in zip(rows, selected["answer"]):
            if "####" not in answer:
                raise ValueError("Selected training answer lacks final-answer delimiter")
            gold[row["question"]["id"]] = answer.rsplit("####", 1)[1].strip()
        dataset = root / "data" / "bridge"
        save_dataset(dataset, questions, gold, {
            "role": "bridge", "upstream": "train", "allocation_sha256": digest(allocation),
            "revision": allocation["source"]["revision"], "never_use_for_confirmation": True,
        })
        new_values = config.to_dict() | {
            "data_dir": str(dataset), "output_dir": str(study / "runs" / "v3"),
            "split": "bridge",
        }
        old_values = json.loads(json.dumps(new_values))
        old_values["name"] = "qwen3-1.7b-research-bridge-legacy"
        old_values["output_dir"] = str(study / "runs" / "legacy")
        old_values.pop("closure_text")
        old_values["limits"].pop("max_consecutive_failures")
        arms = {}
        sources = {"legacy": Path(legacy_src).resolve(), "v3": Path(__file__).parent.parent.resolve()}
        for arm, values in [("legacy", old_values), ("v3", new_values)]:
            config_file = study / "configs" / f"{arm}.yaml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(yaml.safe_dump(values, sort_keys=False))
            snapshot = resolver(config_file, sources[arm], study / f"{arm}-snapshot.json")
            arms[arm] = {"config_path": str(config_file), "config_sha256": file_hash(config_file),
                         "source": str(sources[arm]), "snapshot": snapshot}
        _validate_pair(arms)
        _validate_sources(arms)
        dataset_hashes = {name: file_hash(dataset / name) for name in ["manifest.json", "questions.json"]}
        protocol = {
            "schema_version": 1, "request": request, "prepared_at": time.time(),
            "implementation": implementation(), "worker_sha256": file_hash(WORKER),
            "allocation_sha256": digest(allocation), "question_count": len(questions),
            "dataset_file_sha256": dataset_hashes, "scoring_version": SCORING_VERSION,
            "scoring_implementation_sha256": scoring_digest(), "analysis": ANALYSIS,
            "arms": arms, "template_config_sha256": file_hash(config_path),
            "source_commits": {
                arm: subprocess.check_output(
                    ["git", "-C", str(source.parent), "rev-parse", "HEAD"], text=True
                ).strip() for arm, source in sources.items()
            },
            "cloud_spend_usd": 0,
        }
        # Preserve exact collection/analysis sources before the first attempt.
        source_hashes = {}
        for arm, source in sources.items():
            target = study / "frozen_code" / arm
            target.mkdir(parents=True, exist_ok=True)
            source_hashes[arm] = {}
            for path in sorted((source / "reasoning_budget").glob("*.py")):
                shutil.copy2(path, target / path.name)
                source_hashes[arm][path.name] = file_hash(path)
        protocol["source_file_sha256"] = source_hashes
        atomic_json(study / "protocol.json", envelope(protocol))
        atomic_json(study / "status.json", {
            "state": "prepared", "generation_started": False,
            "expected_per_arm": len(questions) * 4, "comparative_analysis": "locked",
        })
    return study


def read_protocol(study):
    from .research_data import load_allocation

    study = Path(study)
    protocol = verified(study / "protocol.json")
    if protocol["implementation"] != implementation() or protocol["analysis"] != ANALYSIS:
        raise ValueError("Frozen bridge analysis implementation changed")
    if protocol["scoring_version"] != SCORING_VERSION or protocol[
        "scoring_implementation_sha256"
    ] != scoring_digest():
        raise ValueError("Frozen bridge scorer changed")
    allocation = load_allocation(Path(protocol["request"]["root"]) / "allocations")
    if digest(allocation) != protocol["allocation_sha256"]:
        raise ValueError("Frozen bridge allocation changed")
    if file_hash(protocol["request"]["config_path"]) != protocol["template_config_sha256"]:
        raise ValueError("Frozen bridge template changed")
    for arm, details in protocol["arms"].items():
        if file_hash(details["config_path"]) != details["config_sha256"]:
            raise ValueError("Frozen bridge arm YAML changed")
        for name, expected in protocol["source_file_sha256"][arm].items():
            if file_hash(Path(details["source"]) / "reasoning_budget" / name) != expected:
                raise ValueError("Frozen bridge generation source changed")
            if file_hash(study / "frozen_code" / arm / name) != expected:
                raise ValueError("Archived bridge source changed")
        packages = details["snapshot"]["identity"]["environment"]["packages"]
        if packages != {name: importlib.metadata.version(name) for name in packages}:
            raise ValueError("Frozen bridge package versions changed")
    dataset = Path(protocol["arms"]["v3"]["snapshot"]["config"]["data_dir"])
    for name, expected in protocol["dataset_file_sha256"].items():
        if file_hash(dataset / name) != expected:
            raise ValueError("Frozen bridge question/dataset artifact changed")
    _validate_pair(protocol["arms"])
    _validate_sources(protocol["arms"])
    return protocol


def checked_arm(study, protocol, arm):
    expected = protocol["arms"][arm]["snapshot"]
    path = Path(expected["run_dir"])
    if not (path / "manifest.json").exists():
        return None, []
    manifest, records = load_run(path)
    if manifest["identity"] != expected["identity"] or manifest["jobs"] != expected["jobs"]:
        raise ValueError("Bridge run differs from frozen jobs")
    code = manifest.get("implementation_sha256", manifest["identity"].get("implementation_sha256"))
    if code != expected["generation_implementation"] or any(
        record["status"] != "pending"
        and record.get("implementation_sha256", code) != code
        for record in records
    ):
        raise ValueError("Bridge run contains mixed implementations")
    for record in records:
        if record["status"] != "pending":
            path = Path(expected["run_dir"]) / "attempts" / f"{record['attempt_id']}.json"
            if verified(path)["started_at"] < protocol["prepared_at"]:
                raise ValueError("Bridge generation preceded the protocol freeze")
    return manifest, records


def status(study, protocol=None):
    protocol = protocol or read_protocol(study)
    arms = {}
    for arm in protocol["arms"]:
        manifest, records = checked_arm(study, protocol, arm)
        tokens, elapsed = _usage(Path(protocol["arms"][arm]["snapshot"]["run_dir"])) if manifest else (0, 0)
        arms[arm] = {
            "completed": sum(record["status"] == "completed" for record in records),
            "failed": sum(record["status"] == "failed" for record in records),
            "expected": len(protocol["arms"][arm]["snapshot"]["jobs"]),
            "charged_tokens": tokens, "elapsed_hours": elapsed / 3600,
        }
    return {"arms": arms, "comparative_outcomes": "locked until both arms complete"}


def run_study(study, progress=print):
    study = Path(study).resolve()
    with run_lock(study):
        protocol = read_protocol(study)
        for arm, details in protocol["arms"].items():
            for retry in range(3):
                _, records = checked_arm(study, protocol, arm)
                if records and all(record["status"] == "completed" for record in records):
                    break
                state = status(study, protocol)
                atomic_json(study / "status.json", state | {
                    "state": "collecting", "generation_started": True,
                    "active_arm": arm, "comparative_analysis": "locked",
                })
                progress(f"Collecting {arm}, invocation {retry + 1}/3; log: {study / (arm + '.log')}")
                with (study / f"{arm}.log").open("a") as log:
                    result = subprocess.run(
                        [sys.executable, str(WORKER), "run", "--study", str(study), "--arm", arm],
                        env=worker_environment(details["source"]), stdout=log,
                        stderr=subprocess.STDOUT, check=False,
                    )
                if result.returncode:
                    atomic_json(study / "status.json", status(study, protocol) | {
                        "state": "paused", "generation_started": True,
                        "worker_returncode": result.returncode, "comparative_analysis": "locked",
                    })
                    raise RuntimeError(f"{arm} worker failed; inspect its log before resuming")
            _, records = checked_arm(study, protocol, arm)
            if not records or not all(record["status"] == "completed" for record in records):
                atomic_json(study / "status.json", status(study, protocol) | {
                    "state": "paused", "generation_started": True, "comparative_analysis": "locked",
                })
                # Each arm has an independent fixed cap. Preserve incomplete
                # coverage and still exercise the other decoder; scoring stays locked.
                continue
        coverage = status(study, protocol)
        if any(values["completed"] != values["expected"] for values in coverage["arms"].values()):
            atomic_json(study / "status.json", coverage | {
                "state": "paused", "generation_started": True, "comparative_analysis": "locked",
            })
            return study
        evaluate(study, protocol)
        atomic_json(study / "status.json", status(study, protocol) | {
            "state": "complete", "generation_started": True, "comparative_analysis": "complete",
        })
    return study


def paired_analysis(old_records, new_records, old_scores, new_scores, *, samples=2):
    def keyed(records, scores):
        by_job = {score["job_id"]: score for score in scores}
        if len({(record["job"]["question_id"], record["job"]["mode"], record["job"]["sample"])
                for record in records}) != len(records):
            raise ValueError("Duplicate bridge cells")
        if any(record["status"] != "completed" for record in records) or len(by_job) != len(records):
            raise ValueError("Complete unique bridge records and scores are required")
        result = {(record["job"]["question_id"], record["job"]["mode"], record["job"]["sample"]):
                (record["result"], by_job[record["job"]["id"]]) for record in records}
        if len(result) != len(records):
            raise ValueError("Duplicate bridge cells")
        return result
    old, new = keyed(old_records, old_scores), keyed(new_records, new_scores)
    if old.keys() != new.keys() or not old:
        raise ValueError("Complete matched bridge cells are required")
    comparisons = {}
    for mode in ["direct", "thinking"]:
        keys = [key for key in old if key[1] == mode]
        ids = sorted({key[0] for key in keys})
        if len(keys) != len(ids) * samples or any(
            {key[2] for key in keys if key[0] == identifier} != set(range(samples))
            for identifier in ids
        ):
            raise ValueError("Every bridge question needs both matched draws")
        cells = []
        for key in keys:
            old_result, old_score = old[key]
            new_result, new_score = new[key]
            def charged(result):
                return sum(result[name] for name in [
                    "reasoning_tokens", "answer_tokens", "inserted_tokens",
                ])
            old_cost, new_cost = charged(old_result), charged(new_result)
            cells.append({
                "question_id": key[0], "sample": key[2],
                "accuracy_delta": int(new_score["correct"]) - int(old_score["correct"]),
                "charged_tokens_delta": new_cost - old_cost,
                "utility_delta": int(new_score["correct"]) - int(old_score["correct"])
                - ANALYSIS["preference"] * (new_cost - old_cost) / 1000,
                "result_seconds_delta": new_result["elapsed_seconds"] - old_result["elapsed_seconds"],
                "token_ids_equal": all(new_result["metadata"][field] == old_result["metadata"][field]
                    for field in ["reasoning_token_ids", "answer_token_ids", "inserted_token_ids"]),
                "termination_equal": new_result["termination"] == old_result["termination"],
                "extracted_answer_equal": new_score["extracted_answer"] == old_score["extracted_answer"],
            })
        result = {"matched_cells": len(keys), "questions": len(ids)}
        for metric in ["accuracy_delta", "charged_tokens_delta", "utility_delta", "result_seconds_delta"]:
            means = [np.mean([cell[metric] for cell in cells if cell["question_id"] == identifier])
                     for identifier in ids]
            result[metric] = {"mean": float(np.mean(means)), "ci95": bootstrap(
                means, ANALYSIS["bootstrap_seed"], ANALYSIS["bootstrap_draws"])}
        for metric in ["token_ids_equal", "termination_equal", "extracted_answer_equal"]:
            result[metric] = sum(cell[metric] for cell in cells)
        result["cells"] = cells
        comparisons[mode] = result
    return comparisons


def evaluate(study, protocol=None):
    study = Path(study)
    protocol = protocol or read_protocol(study)
    loaded = {arm: checked_arm(study, protocol, arm) for arm in protocol["arms"]}
    if any(len(records) != len(protocol["arms"][arm]["snapshot"]["jobs"])
           or any(record["status"] != "completed" for record in records)
           for arm, (_, records) in loaded.items()):
        raise ValueError("Bridge incomplete; comparative analysis and gold access are locked")
    summaries, scores = {}, {}
    for arm, (manifest, records) in loaded.items():
        path = Path(protocol["arms"][arm]["snapshot"]["run_dir"])
        artifact = score_run(path)  # Exactly 25 isolated upstream-training gold answers.
        scores[arm] = artifact["scores"]
        by_job = {score["job_id"]: score for score in scores[arm]}
        modes = {}
        for mode in ["direct", "thinking"]:
            subset = [record for record in records if record["job"]["mode"] == mode]
            results = [record["result"] for record in subset]
            mode_scores = [by_job[record["job"]["id"]] for record in subset]
            n = len(results)
            means = {f"mean_{field}": float(np.mean([result[field] for result in results]))
                for field in ["prompt_tokens", "reasoning_tokens", "answer_tokens", "inserted_tokens",
                              "elapsed_seconds", "reasoning_seconds", "answer_seconds"]}
            charged = sum(result["reasoning_tokens"] + result["answer_tokens"]
                          + result["inserted_tokens"] for result in results)
            raw = [result.get("mean_generated_logprob_raw") for result in results]
            modes[mode] = means | {
                "responses": n, "accuracy": sum(score["correct"] for score in mode_scores) / n,
                "parse_failure_rate": sum(score["parser_status"] != "ok" for score in mode_scores) / n,
                "answer_truncation_rate": sum(result["answer_truncated"] for result in results) / n,
                "forced_closure_rate": sum(result["forced_closure"] for result in results) / n,
                "mean_charged_tokens": charged / n,
                "charged_tokens_per_result_second": charged / sum(result["elapsed_seconds"] for result in results),
                "raw_finite_coverage": float(sum(value is not None and bool(np.isfinite(value)) for value in raw) / n),
                "peak_mps_allocated_bytes": max(result["metadata"].get("memory", {}).get("mps_allocated_bytes", 0) for result in results),
            }
        tokens, elapsed = _usage(path)
        summaries[arm] = {
            "modes": modes, "charged_tokens_all_attempts": tokens,
            "elapsed_hours_all_attempts_and_setup": elapsed / 3600,
            "attempts": len(list((path / "attempts").glob("*.json"))),
            "setup_seconds": sum(verified(p)["setup_seconds"] for p in (path / "sessions").glob("*.json")),
            "manifest_sha256": digest(manifest), "records_sha256": digest(records),
            "scores_sha256": digest(artifact),
        }
    paired = paired_analysis(loaded["legacy"][1], loaded["v3"][1], scores["legacy"], scores["v3"])
    new_modes = summaries["v3"]["modes"]
    projected = 50 * 8 * sum(value["mean_elapsed_seconds"] for value in new_modes.values()) / 3600
    threshold = ANALYSIS["gate"]
    gates = {
        "complete_and_matched": True,
        "raw_confidence_covered": new_modes["direct"]["raw_finite_coverage"] >= threshold["raw_direct_confidence_coverage"],
        "answer_truncation": all(value["answer_truncation_rate"] <= threshold["max_answer_truncation_per_mode"] for value in new_modes.values()),
        "numeric_parser_coverage": all(value["parse_failure_rate"] <= threshold["max_parse_failure_per_mode"] for value in new_modes.values()),
        "no_large_observed_accuracy_loss": all(value["accuracy_delta"]["mean"] >= -threshold["max_observed_accuracy_loss_per_mode"] for value in paired.values()),
        "repeat_panel_local_feasible": projected <= threshold["max_projected_repeat_panel_local_hours"],
    }
    result = {"protocol_sha256": digest(protocol), "analysis": ANALYSIS,
              "summaries": summaries, "paired": paired,
              "repeat_panel_projection_hours_excluding_setup_retries": projected,
              "engineering_gates": gates, "engineering_gate_passed": all(gates.values()),
              "synthetic": protocol["arms"]["v3"]["snapshot"]["config"]["backend"] == "fake",
              "cloud_spend_usd": 0, "official_test_opened": False}
    atomic_json(study / "report.json", envelope(result))
    lines = ["# Paired protocol bridge", "", "Engineering diagnostic; not independent router confirmation.", "",
             "| Arm | Mode | Accuracy | Charged tokens/response | Seconds/response | Parse failure | Truncated |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for arm, summary in summaries.items():
        for mode, values in summary["modes"].items():
            lines.append(f"| {arm} | {mode} | {values['accuracy']:.1%} | {values['mean_charged_tokens']:.1f} | {values['mean_elapsed_seconds']:.2f} | {values['parse_failure_rate']:.1%} | {values['answer_truncation_rate']:.1%} |")
    lines += ["", "Differences are v3 minus legacy; confidence intervals resample 25 whole questions.", ""]
    for mode, values in paired.items():
        lines.append(f"- {mode}: accuracy delta {values['accuracy_delta']['mean']:+.3f}, CI {values['accuracy_delta']['ci95']}; identical token sequences {values['token_ids_equal']}/{values['matched_cells']}.")
    lines += ["", f"Engineering gate passed: **{result['engineering_gate_passed']}**; checks: `{gates}`.",
              f"Projected 50-question, eight-draw/mode panel: {projected:.2f} local hours, excluding setup and retries.",
              "", "Both protocols use common numeric-v5 scoring on isolated bridge gold. Setup, failed attempts and inserted tokens are charged separately from completed-response means. Stage/result timing is collected inference timing; it is not a deployed router's live latency. Serial arm order and MPS thermal variation can affect timing comparisons. A non-significant difference does not establish equivalence. No cloud spend; official test remains sealed. The human audit was waived."]
    if result["synthetic"]:
        lines += ["", "SYNTHETIC: fabricated responses/times establish no model or throughput conclusions."]
    (study / "report.md").write_text("\n".join(lines) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    preparation.add_argument("--root", default=ROOT)
    preparation.add_argument("--config", default="configs/research-gsm8k-v3.yaml")
    preparation.add_argument("--legacy-src", default=LEGACY)
    for name in ["run", "report", "status"]:
        sub.add_parser(name).add_argument("study")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.root, args.config, args.legacy_src))
    elif args.command == "run":
        print(run_study(args.study, lambda message: print(message, flush=True)))
    elif args.command == "report":
        with run_lock(args.study):
            evaluate(args.study)
        print(Path(args.study) / "report.md")
    else:
        print(json.dumps(status(args.study), indent=2))


if __name__ == "__main__":
    main()
