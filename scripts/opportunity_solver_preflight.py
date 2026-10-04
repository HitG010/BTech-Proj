"""Pinned local assets and one synthetic Qwen3-0.6B engineering preflight."""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from reasoning_budget.backend import environment
from reasoning_budget.config import from_dict, load_config
from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, envelope, run_lock, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
OUTPUT = BASE / "opportunity-solver-preflight-v1"
CACHE = OUTPUT / "hub"
REPO = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
FILES = ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
         "merges.txt", "vocab.json", "model.safetensors", "LICENSE", "README.md")
SPEC = {"version": "opportunity-solver-preflight-v1", "repository": REPO, "revision": REVISION,
    "maximum_public_asset_bytes": 2 * 1024**3, "maximum_download_seconds": 1800,
    "maximum_observed_cache_bytes": 2304 * 1024**2,
    "worker_wall_seconds": 600, "per_job_seconds": 120, "maximum_polled_rss_bytes": 9 * 1024**3,
    "answer_cap": 32, "reasoning_cap": 32, "synthetic_jobs": 2,
    "worker_invocations": 1, "retries": 0, "device": "mps", "dtype": "float16", "attention": "sdpa",
    "expected_closure_ids": [151668, 271], "expected_eos_ids": [151643, 151645],
    "synthetic_prompt": "Synthetic engineering check. Return the number 7.",
    "scope": "tokenizer/backend/resource engineering only; no task accuracy or study throughput claim",
    "docker": "keep running", "cloud_spend_usd": 0.}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(value), stream, indent=2, allow_nan=False)
        stream.write("\n")


def paths_checked():
    if (any(path.is_symlink() for path in (OUTPUT, CACHE, OUTPUT / "hf-home",
            OUTPUT / "xet", OUTPUT / "hf-assets"))
            or OUTPUT.resolve() != BASE.resolve() / SPEC["version"]):
        raise ValueError("Only the separate preflight output/cache are writable")


def source_paths():
    return [ROOT / path for path in (
        "scripts/opportunity_solver_preflight.py", "tests/test_opportunity_solver_preflight.py",
        "docs/opportunity-solver-preflight.md", "scripts/macos_runtime_guard.py",
        "configs/research-repeat-v1.yaml", "src/reasoning_budget/backend.py",
        "src/reasoning_budget/config.py", "src/reasoning_budget/records.py",
        "src/reasoning_budget/runner.py", "src/reasoning_budget/storage.py")]


def stable_environment():
    values = environment()
    return {key: values[key] for key in ("python", "platform", "machine", "packages", "mps_fallback")}


def protected_paths():
    return [BASE / path for path in (
        "allocations/manifest.json", "repeat-panel-v1/report.json",
        "repeat-panel-v1/scores.numeric-v7.json", "repeat-clm-probe-v1/report.json",
        "reserve-children/opportunity64-v1/child-manifest.json",
        "reserve-children/opportunity64-v1/preparation-plan.json",
        "reserve-children/opportunity64-v1/dataset/manifest.json",
        "reserve-children/opportunity64-v1/dataset/questions.json")]


def freeze():
    paths_checked()
    plan = {"spec": SPEC, "source_file_sha256": {str(p): file_hash(p) for p in source_paths()},
        "protected_file_sha256": {str(p): file_hash(p) for p in protected_paths()},
        "environment": stable_environment(), "no_study_question_or_reference_input": True}
    with run_lock(OUTPUT):
        write_new(OUTPUT / "plan.json", plan)
    return {"prepared": True, "plan_sha256": digest(plan)}


def checked_plan():
    paths_checked()
    plan = verified(OUTPUT / "plan.json")
    if plan["spec"] != SPEC or plan["environment"] != stable_environment():
        raise ValueError("Frozen preflight spec/environment changed")
    for key in ("source_file_sha256", "protected_file_sha256"):
        for path, sha in plan[key].items():
            if file_hash(path) != sha:
                raise ValueError(f"Frozen preflight input changed: {path}")
    return plan


def inventory(info):
    if info.sha != REVISION:
        raise ValueError("Public source revision differs from the frozen revision")
    available = {item.rfilename: item for item in info.siblings}
    if not set(FILES) <= set(available):
        raise ValueError("Pinned public inventory is incomplete")
    result = {}
    for name in FILES:
        item = available[name]
        if type(item.size) is not int or item.size < 0:
            raise ValueError("Trustworthy public file sizes required")
        if item.lfs is not None:
            remote = item.lfs.sha256
            algorithm, width = "sha256-lfs", 64
            if item.lfs.size != item.size:
                raise ValueError("Public LFS size mismatch")
        else:
            remote = item.blob_id
            algorithm, width = "git-blob-sha1", 40
        if not isinstance(remote, str) or not re.fullmatch(f"[0-9a-f]{{{width}}}", remote):
            raise ValueError("Trustworthy remote object hashes required")
        result[name] = {"bytes": item.size, "remote_object": remote, "algorithm": algorithm}
    total = sum(item["bytes"] for item in result.values())
    if total > SPEC["maximum_public_asset_bytes"]:
        raise ValueError("Public download exceeds the frozen byte ceiling")
    return result, total


def validate_file(path, expected):
    path = Path(path)
    if expected["algorithm"] not in ("sha256-lfs", "git-blob-sha1"):
        raise ValueError("Unknown remote object algorithm")
    if path.stat().st_size != expected["bytes"]:
        raise ValueError("Downloaded file size differs from public metadata")
    sha = hashlib.sha256()
    git = hashlib.sha1(f"blob {expected['bytes']}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            git.update(block)
    actual = sha.hexdigest() if expected["algorithm"] == "sha256-lfs" else git.hexdigest()
    if actual != expected["remote_object"]:
        raise ValueError("Downloaded bytes differ from the remote object hash")
    return sha.hexdigest()


def claim_worker(name, report):
    paths_checked()
    if not (OUTPUT / f"{name}-invocation.json").exists() or (OUTPUT / report).exists():
        raise ValueError("Only one reserved unfinished child invocation is allowed")
    # Exclusive creation also rejects concurrent or crash-recovery restarts.
    write_new(OUTPUT / f"{name}-started.json", {"started_at": time.time(), "pid": os.getpid()})


def download_worker():
    claim_worker("download", "assets.json")
    from huggingface_hub import HfApi, snapshot_download
    plan = checked_plan()
    meta, total = inventory(HfApi(token=False).model_info(REPO, revision=REVISION, files_metadata=True))
    write_new(OUTPUT / "remote-inventory.json", {"plan_sha256": digest(plan), "files": meta, "bytes": total})
    directory = Path(snapshot_download(REPO, revision=REVISION, allow_patterns=list(FILES),
        cache_dir=str(CACHE), token=False, max_workers=2)).resolve()
    if directory.name != REVISION or not directory.is_relative_to(CACHE.resolve()):
        raise ValueError("Downloaded snapshot escaped the isolated pinned cache")
    hashes = {}
    for name, expected in meta.items():
        path = directory / name
        if not path.resolve().is_relative_to(CACHE.resolve()):
            raise ValueError("Downloaded file escaped the isolated cache")
        hashes[name] = validate_file(path, expected)
    write_new(OUTPUT / "assets.json", {"plan_sha256": digest(plan), "snapshot_path": str(directory),
        "repository": REPO, "revision": REVISION, "download_bytes": total,
        "file_sha256": hashes, "remote_inventory_sha256": digest(meta)})


def assets_checked(plan):
    asset = verified(OUTPUT / "assets.json")
    remote = verified(OUTPUT / "remote-inventory.json")
    directory = Path(asset["snapshot_path"])
    if (asset["plan_sha256"] != digest(plan) or remote["plan_sha256"] != digest(plan)
            or asset["repository"] != REPO or asset["revision"] != REVISION
            or asset["remote_inventory_sha256"] != digest(remote["files"])
            or set(asset["file_sha256"]) != set(FILES) or set(remote["files"]) != set(FILES)
            or directory.name != REVISION or not directory.resolve().is_relative_to(CACHE.resolve())
            or asset["download_bytes"] != remote["bytes"]
            or asset["download_bytes"] > SPEC["maximum_public_asset_bytes"]):
        raise ValueError("Prepared local asset identity changed")
    for name in FILES:
        path = directory / name
        if (not path.resolve().is_relative_to(CACHE.resolve())
                or validate_file(path, remote["files"][name]) != asset["file_sha256"][name]):
            raise ValueError("Prepared local asset bytes changed")
    return asset


def synthetic_config():
    values = load_config(ROOT / "configs/research-repeat-v1.yaml").to_dict()
    values.update(name=SPEC["version"], seed=20261008, samples=1, split="synthetic",
        answer_tokens=SPEC["answer_cap"], reasoning_tokens=SPEC["reasoning_cap"],
        data_dir="unused-no-dataset-loader", output_dir=str(OUTPUT / "unused-no-runner"))
    values["model"].update(name=REPO, revision=REVISION, tokenizer_revision=REVISION,
        cache_dir=str(CACHE), local_files_only=True)
    return from_dict(values)


def check_tokenizer(metadata):
    if (metadata["model_revision"] != REVISION or metadata["tokenizer_revision"] != REVISION
            or metadata["closure_ids"] != SPEC["expected_closure_ids"]
            or metadata["closure_tokens"] != 2 or metadata["eos_token_ids"] != SPEC["expected_eos_ids"]):
        raise ValueError("Actual tokenizer revision/EOS/closure differs from the planned assumption")
    return 64 * 2 * 2 * (512 + 512 + 2048 + metadata["closure_tokens"])


def check_job(row):
    result = row["result"]
    if (row["mode"] not in ("direct", "thinking")
            or result["termination"] in ("timeout", "reasoning_in_answer")
            or not isinstance(result["final_answer"], str) or not result["final_answer"].strip()
            or not math.isfinite(result["elapsed_seconds"])
            or not 0 <= result["elapsed_seconds"] <= SPEC["per_job_seconds"] + 5
            or any(type(result[key]) is not int for key in ("answer_tokens", "reasoning_tokens", "inserted_tokens"))
            or not 0 < result["answer_tokens"] <= SPEC["answer_cap"]
            or not 0 <= result["reasoning_tokens"] <= (32 if row["mode"] == "thinking" else 0)
            or not 0 <= result["inserted_tokens"] <= (2 if row["mode"] == "thinking" else 0)):
        raise ValueError("Synthetic generation engineering endpoint failed")
    if row["mode"] == "direct" and not all(
            isinstance(result[key], (int, float)) and math.isfinite(result[key])
            for key in ("mean_generated_logprob", "mean_generated_logprob_raw")):
        raise ValueError("Synthetic direct confidence must be finite")


def check_jobs(rows):
    if len(rows) != 2 or [r["mode"] for r in rows] != ["direct", "thinking"]:
        raise ValueError("Exactly the two synthetic engineering jobs are required")
    for row in rows:
        check_job(row)
    return sum(sum(r["result"][key] for key in ("answer_tokens", "reasoning_tokens", "inserted_tokens")) for r in rows)


def worker():
    claim_worker("worker", "worker-report.json")
    from reasoning_budget.backend import TransformersBackend
    from reasoning_budget.records import Question
    from reasoning_budget.runner import build_jobs, valid_record_result
    from scripts.macos_runtime_guard import user_activity
    plan = checked_plan()
    assets = assets_checked(plan)
    question = Question("synthetic-engineering-7", "fixture:engineering", "synthetic", SPEC["synthetic_prompt"])
    config = synthetic_config()
    began = time.monotonic()
    with user_activity():
        engine = TransformersBackend(config)
        response_bound = check_tokenizer(engine.metadata)
        prefixes = {mode: engine.tokenizer.apply_chat_template(
            [{"role": "user", "content": question.prompt + "\n\n" + config.prompt_suffix}],
            tokenize=True, add_generation_prompt=True, enable_thinking=mode == "thinking")
            for mode in config.modes}
        if prefixes["direct"] == prefixes["thinking"]:
            raise ValueError("Thinking/direct chat-template switch has no effect")
        load_begin = time.monotonic()
        engine.load()
        engine._sync()
        load_seconds = time.monotonic() - load_begin
        rows = []
        for job in build_jobs(config, [question], engine.metadata):
            result = engine.generate(question, job, time.monotonic() + SPEC["per_job_seconds"])
            if not valid_record_result(result, job):
                raise ValueError("Synthetic result violates unchanged generator invariants")
            row = {"mode": job.mode, "job": job.to_dict(), "result": result.to_dict(),
                "mps_current_allocated_bytes_after_job": engine.torch.mps.current_allocated_memory(),
                "mps_driver_allocated_bytes_after_job": engine.torch.mps.driver_allocated_memory()}
            check_job(row)
            rows.append(row)
    tokens = check_jobs(rows)
    write_new(OUTPUT / "worker-report.json", {"plan_sha256": digest(plan), "assets_sha256": digest(assets),
        "synthetic_config": config.to_dict(), "backend_metadata": engine.metadata,
        "prefix_sha256": {mode: digest(ids) for mode, ids in prefixes.items()},
        "prefix_tokens": {mode: len(ids) for mode, ids in prefixes.items()},
        "rows": rows, "charged_synthetic_tokens": tokens, "load_seconds": load_seconds,
        "worker_seconds": time.monotonic() - began, "prospective_response_only_bound": response_bound,
        "no_real_question_gold_or_scoring": True})


def run_child(command, wall_seconds, name, monitor_rss=False):
    paths_checked()
    write_new(OUTPUT / f"{name}-invocation.json", {"reserved_at": time.time(), "command": command})
    began, maximum_rss, maximum_cache, reason = time.monotonic(), 0, 0, None
    child, rss_samples, final_cache = None, 0, None
    with (OUTPUT / f"{name}.log").open("x") as log:
        try:
            env = child_environment()
            if name == "download":
                env["HF_HUB_OFFLINE"] = "0"
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, env=env)
            while child.poll() is None:
                if monitor_rss:
                    reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
                        capture_output=True, text=True, timeout=5)
                    if reading.returncode == 0 and reading.stdout.strip():
                        maximum_rss = max(maximum_rss, int(reading.stdout.strip()) * 1024)
                        rss_samples += 1
                    elif child.poll() is None:
                        reason = "own worker RSS telemetry unavailable"
                    if maximum_rss > SPEC["maximum_polled_rss_bytes"]:
                        reason = "own worker RSS observation exceeded ceiling"
                if name == "download":
                    maximum_cache = max(maximum_cache, cache_size())
                    if maximum_cache > SPEC["maximum_observed_cache_bytes"]:
                        reason = "isolated cache disk observation exceeded ceiling"
                if time.monotonic() - began > wall_seconds:
                    reason = "own worker exceeded wall ceiling"
                if reason:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                    break
                time.sleep(.5)
        except BaseException as error:
            reason = f"controller aborted: {type(error).__name__}"
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
    if name == "download":
        try:
            final_cache = cache_size()
            maximum_cache = max(maximum_cache, final_cache)
            if maximum_cache > SPEC["maximum_observed_cache_bytes"]:
                reason = reason or "isolated cache disk observation exceeded ceiling"
        except Exception as error:
            reason = reason or f"final disk telemetry unavailable: {type(error).__name__}"
    if monitor_rss and not rss_samples:
        reason = reason or "no valid own-worker RSS observations"
    result = {"exit_code": child.returncode if child is not None else None, "reason": reason,
        "pid": child.pid if child is not None else None, "rss_samples": rss_samples,
        "wall_seconds": time.monotonic() - began, "maximum_polled_rss_bytes": maximum_rss,
        "maximum_observed_cache_bytes": maximum_cache, "final_cache_bytes": final_cache}
    write_new(OUTPUT / f"{name}-process.json", result)
    if result["exit_code"] != 0 or reason:
        raise RuntimeError(f"{name} stopped; inspect preserved log/process record")
    return result


def child_environment():
    return dict(os.environ, HF_HOME=str(OUTPUT / "hf-home"), HF_HUB_CACHE=str(CACHE),
        HF_XET_CACHE=str(OUTPUT / "xet"), HF_ASSETS_CACHE=str(OUTPUT / "hf-assets"),
        HF_HUB_DISABLE_XET="1", HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_PROGRESS_BARS="1")


def cache_size():
    # Count each physical file once; snapshot symlinks already point at blobs.
    total = 0
    for directory in (CACHE, OUTPUT / "hf-home", OUTPUT / "xet", OUTPUT / "hf-assets"):
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink():
                    total += path.stat().st_size
            except FileNotFoundError:
                # Downloader atomically renames completed .incomplete files.
                continue
    return total


def download():
    with run_lock(OUTPUT):
        plan = checked_plan()
        process = run_child([sys.executable, "-m", "scripts.opportunity_solver_preflight", "download-worker"],
            SPEC["maximum_download_seconds"], "download")
        assets_checked(plan)
        return process


def execute():
    with run_lock(OUTPUT):
        plan = checked_plan()
        assets = assets_checked(plan)
        process = run_child([sys.executable, "-m", "scripts.opportunity_solver_preflight", "worker"],
            SPEC["worker_wall_seconds"], "worker", monitor_rss=True)
        report = verified(OUTPUT / "worker-report.json")
        if report["plan_sha256"] != digest(plan) or report["assets_sha256"] != digest(assets):
            raise ValueError("Synthetic worker report identity changed")
        check_jobs(report["rows"])
        check_tokenizer(report["backend_metadata"])
        if checked_plan() != plan or assets_checked(plan) != assets:
            raise ValueError("Frozen inputs changed during execution")
        from scripts.verify_phase2_repeat import verify
        preservation = verify(BASE / "repeat-panel-v1")
        complete = {"status": "synthetic_engineering_pass_collection_protocol_pending",
            "plan_sha256": digest(plan), "worker_report_sha256": digest(report),
            "assets_sha256": digest(assets), "process": process,
            "protected_originals_verified": preservation["protected_originals_verified"],
            "no_real_question_gold_or_scoring": True, "cloud_spend_usd": 0.}
        write_new(OUTPUT / "report.json", complete)
        return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "download", "execute", "download-worker", "worker"])
    args = parser.parse_args()
    result = {"freeze": freeze, "download": download, "execute": execute,
        "download-worker": download_worker, "worker": worker}[args.command]()
    print(result)


if __name__ == "__main__":
    main()
