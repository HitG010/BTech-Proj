"""One-shot synthetic MLX Qwen3-8B / released CLM resource preflight.

Download public pinned assets into a new isolated artifact directory, freeze a
plan, then run only synthetic embeddings. No solver generation or study labels.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from reasoning_budget.storage import digest, envelope, run_lock, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
ENV = BASE / "clm-local-environment-v1"
OUTPUT = BASE / "clm-local-preflight-v1"
MODEL_REPO = "mlx-community/Qwen3-8B-4bit"
MODEL_REVISION = "545dc4251c05440727734bcd94334791f6ab0192"
HEAD_REPO = "Contrastive-LM/CLM-v0.1-8B"
HEAD_REVISION = "e939398d4556fcd9400c76fa8c5a513202f42b0a"
HEAD_CODE_COMMIT = "bb42c6c5bf914fd449bed2f6ca65be80602cb1f7"
HEAD_CODE_SHA256 = "3f3b880e940a47b45879614b140fd873f7de9b13ccb8254b07989af7ea92e093"
MODEL_FILES = ["config.json", "model.safetensors", "model.safetensors.index.json",
    "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
    "added_tokens.json", "merges.txt", "vocab.json", "README.md"]
HEAD_FILES = ["CLM_v0.1-8B.pt", "config.json", "LICENSE", "README.md"]
ACTIONS = [
    "Accept the completed direct draft from Qwen3-1.7B as the final answer without another solve.",
    "Discard the direct draft and pay for a fresh thinking solve of the original question by Qwen3-1.7B.",
]
SPEC = {"version": "clm-local-preflight-v1", "synthetic_only": True,
    "sequence_lengths": [32, 128, 512, 2047], "repetitions": 2,
    "max_input_tokens": 2047, "pooling": "final normalized hidden state at last input token, then L2",
    "batch_size": 1, "persistent_kv_cache": False,
    "maximum_download_bytes": 5 * 1024**3,
    "mlx_memory_guideline_bytes": 7 * 1024**3, "mlx_free_cache_limit_bytes": 128 * 1024**2,
    "maximum_observed_peak_mlx_bytes": 7 * 1024**3,
    "maximum_observed_worker_rss_bytes": 9 * 1024**3,
    "worker_wall_seconds": 600, "rss_poll_seconds": 0.5,
    "repeat_max_absolute_difference": 1e-5,
    "minimum_acceptable_norm": 0.99999, "maximum_acceptable_norm": 1.00001,
    "head_score_absolute_tolerance": 1e-4,
    "max_long_input_seconds": 60.0,
    "scope": "quantized engineering adaptation; no routing accuracy or full-precision equivalence claim",
    "docker": "keep running", "cloud_spend_usd": 0.0,
    "retries": 0, "cached_panel_access": False}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(payload), stream, indent=2, allow_nan=False)
        stream.write("\n")


def selected_download_size(info, allowed):
    files = {item.rfilename: item for item in info.siblings}
    if not set(allowed) <= set(files):
        raise ValueError("Pinned public model file inventory changed")
    sizes = [files[name].size for name in allowed]
    if any(type(size) is not int or size < 0 for size in sizes):
        raise ValueError("Missing trustworthy file-size metadata")
    return sum(sizes)


def download():
    from huggingface_hub import HfApi, snapshot_download
    if (ENV / "assets-manifest.json").exists():
        raise ValueError("Assets already prepared; do not redownload a completed setup")
    api, metadata, total = HfApi(token=False), [], 0
    for name, repo, revision, allowed in (
        ("encoder", MODEL_REPO, MODEL_REVISION, MODEL_FILES),
        ("heads", HEAD_REPO, HEAD_REVISION, HEAD_FILES)):
        info = api.model_info(repo, revision=revision, files_metadata=True)
        if info.sha != revision:
            raise ValueError("Public revision mismatch")
        size = selected_download_size(info, allowed)
        metadata.append((name, repo, revision, allowed, size))
        total += size
    if total > SPEC["maximum_download_bytes"]:
        raise ValueError("Local download ceiling exceeded")
    print({"pinned_public_download_bytes": total}, flush=True)
    inventory = {}
    for name, repo, revision, allowed, size in metadata:
        directory = ENV / "assets" / name
        snapshot_download(repo, revision=revision, allow_patterns=allowed,
            local_dir=directory, token=False, max_workers=2)
        inventory[name] = {"repo": repo, "revision": revision, "download_bytes": size,
            "files": {filename: sha(directory / filename) for filename in allowed}}
    code = ENV / "assets" / "official-heads.py"
    url = f"https://raw.githubusercontent.com/Contrastive-LM/CLM/{HEAD_CODE_COMMIT}/src/clm/heads.py"
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read(1024 * 1024)
    if hashlib.sha256(content).hexdigest() != HEAD_CODE_SHA256:
        raise ValueError("Reviewed official head source changed")
    with code.open("xb") as stream:
        stream.write(content)
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    write_new(ENV / "assets-manifest.json", {"assets": inventory,
        "head_code_commit": HEAD_CODE_COMMIT, "head_code_sha256": sha(code),
        "python": sys.version, "packages": packages, "download_bytes": total})


def validate_assets():
    manifest = verified(ENV / "assets-manifest.json")
    for name, repo, revision, allowed in (("encoder", MODEL_REPO, MODEL_REVISION, MODEL_FILES),
                                         ("heads", HEAD_REPO, HEAD_REVISION, HEAD_FILES)):
        asset = manifest["assets"][name]
        if (asset["repo"] != repo or asset["revision"] != revision
                or set(asset["files"]) != set(allowed)):
            raise ValueError("Prepared asset identities changed")
        for filename, expected in asset["files"].items():
            if sha(ENV / "assets" / name / filename) != expected:
                raise ValueError(f"Prepared file changed: {name}/{filename}")
    if sha(ENV / "assets/official-heads.py") != HEAD_CODE_SHA256:
        raise ValueError("Official head source changed")
    config = json.loads((ENV / "assets/encoder/config.json").read_text())
    if config["hidden_size"] != 4096 or config["quantization"]["bits"] != 4:
        raise ValueError("Require the pinned 4096-dimensional 4-bit Qwen encoder")
    return manifest


def freeze():
    assets = validate_assets()
    sources = [Path(__file__), ROOT / "tests/test_clm_local_preflight.py",
               ROOT / "docs/clm-local-preflight.md"]
    protected = [BASE / name for name in (
        "repeat-panel-v1/report.json", "repeat-panel-v1/scores.numeric-v7.json",
        "allocations/manifest.json", "repeat-cpu-feasibility-v1/report.json",
        "repeat-contrastive-pilot-v1/report.json")]
    plan = {"spec": SPEC, "assets": assets, "action_texts": ACTIONS,
        "synthetic_text": "Local resource preflight. A draft is available. Decide whether to accept it or request a fresh solve. ",
        "source_sha256": {str(p): sha(p) for p in sources},
        "protected_file_sha256": {str(p): sha(p) for p in protected},
        "head_runtime_packages": {name: importlib.metadata.version(name) for name in ("torch", "numpy")}}
    with run_lock(OUTPUT):
        write_new(OUTPUT / "analysis-plan.json", plan)
    print({"plan_sha256": digest(plan)}, flush=True)


def checked_plan():
    plan = verified(OUTPUT / "analysis-plan.json")
    if plan["spec"] != SPEC or plan["action_texts"] != ACTIONS:
        raise ValueError("Frozen preflight spec changed")
    for path, expected in plan["source_sha256"].items():
        if sha(path) != expected:
            raise ValueError("Preflight implementation/protocol changed after freezing")
    return plan


def synthetic_ids(tokenizer, text, length):
    if not 0 < length <= SPEC["max_input_tokens"]:
        raise ValueError("Invalid synthetic length")
    unit = tokenizer.encode(text, add_special_tokens=False)
    if not unit:
        raise ValueError("Empty synthetic token unit")
    return (unit * ((length + len(unit) - 1) // len(unit)))[:length]


def worker():
    import mlx.core as mx
    import numpy as np
    from mlx_lm import load
    plan = checked_plan()
    if not mx.metal.is_available():
        raise ValueError("Native Metal unavailable")
    for name in ("mlx", "mlx-lm", "mlx-metal", "numpy", "transformers", "tokenizers"):
        if importlib.metadata.version(name) != plan["assets"]["packages"][name]:
            raise ValueError("Isolated encoder dependencies changed")
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(SPEC["mlx_memory_guideline_bytes"])
    mx.set_cache_limit(SPEC["mlx_free_cache_limit_bytes"])
    start = time.monotonic()
    model, tokenizer = load(str(ENV / "assets/encoder"), lazy=False,
        tokenizer_config={"trust_remote_code": False})
    load_seconds = time.monotonic() - start
    rows, vectors = [], []
    jobs = [(f"synthetic-{length}-{repeat}", synthetic_ids(tokenizer, plan["synthetic_text"], length))
            for length in SPEC["sequence_lengths"] for repeat in range(SPEC["repetitions"])]
    jobs += [(f"action-{i}", tokenizer.encode(text, add_special_tokens=False)[:SPEC["max_input_tokens"]])
             for i, text in enumerate(ACTIONS)]
    for name, ids in jobs:
        if not ids:
            raise ValueError("Empty input")
        begin = time.monotonic()
        hidden = model.model(mx.array([ids], dtype=mx.int32), cache=None)
        vector = hidden[:, -1, :].astype(mx.float32)
        vector = vector / mx.maximum(mx.linalg.norm(vector, axis=-1, keepdims=True), 1e-12)
        mx.eval(vector)
        value = np.asarray(vector)[0].copy()
        seconds = time.monotonic() - begin
        if value.shape != (4096,) or not np.isfinite(value).all():
            raise ValueError("Nonfinite or wrong-width pooled vector")
        rows.append({"id": name, "input_tokens": len(ids), "input_ids_sha256": digest(ids),
            "seconds": seconds, "l2_norm": float(np.linalg.norm(value)),
            "mlx_peak_bytes": mx.get_peak_memory()})
        vectors.append(value)
        print({"completed": name, "seconds": round(seconds, 3), "peak_bytes": mx.get_peak_memory()}, flush=True)
        del hidden, vector
        if mx.get_peak_memory() > SPEC["maximum_observed_peak_mlx_bytes"]:
            raise ValueError("Measured MLX peak exceeded the predeclared gate")
        if seconds > SPEC["max_long_input_seconds"]:
            raise ValueError("Measured per-input latency exceeded the predeclared gate")
    with (OUTPUT / "synthetic-embeddings.npz").open("xb") as stream:
        np.savez(stream, vectors=np.stack(vectors))
    write_new(OUTPUT / "encoder-report.json", {"plan_sha256": digest(plan),
        "model_load_seconds": load_seconds, "rows": rows,
        "embedding_file_sha256": sha(OUTPUT / "synthetic-embeddings.npz"),
        "mlx_peak_bytes": mx.get_peak_memory(), "metal_available": True})


def check_geometry(rows, vectors):
    import numpy as np
    if vectors.shape != (10, 4096) or not np.isfinite(vectors).all() or len(rows) != 10:
        raise ValueError("Incomplete synthetic endpoint")
    norms = np.linalg.norm(vectors, axis=1)
    if (norms.min() < SPEC["minimum_acceptable_norm"] or norms.max() > SPEC["maximum_acceptable_norm"]):
        raise ValueError("Pooled embeddings are not normalized")
    differences = [float(np.abs(vectors[2*i] - vectors[2*i+1]).max()) for i in range(4)]
    if max(differences) > SPEC["repeat_max_absolute_difference"]:
        raise ValueError("Identical synthetic inputs did not repeat")
    expected_names = [f"synthetic-{length}-{repeat}" for length in SPEC["sequence_lengths"]
                      for repeat in range(2)] + ["action-0", "action-1"]
    if [r["id"] for r in rows] != expected_names:
        raise ValueError("Synthetic endpoint order changed")
    if [r["input_tokens"] for r in rows[:8]] != [length for length in SPEC["sequence_lengths"] for _ in range(2)]:
        raise ValueError("Synthetic endpoint lengths changed")
    if any(r["seconds"] > SPEC["max_long_input_seconds"] for r in rows):
        raise ValueError("Latency gate failed")
    return {"maximum_identical_input_difference": max(differences),
            "minimum_norm": float(norms.min()), "maximum_norm": float(norms.max())}


def head_check(vectors):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    begin = time.monotonic()
    checkpoint = torch.load(ENV / "assets/heads/CLM_v0.1-8B.pt", map_location="cpu", weights_only=True)
    cfg = dict(checkpoint["cfg"])
    spec = importlib.util.spec_from_file_location("pinned_clm_heads", ENV / "assets/official-heads.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kw = dict(width=cfg["width"], depth=cfg["depth"],
        proj=checkpoint.get("projection_dim", cfg.get("projection_dim", 512)),
        activation=cfg.get("activation", "gelu"), layernorm=cfg.get("layernorm", False),
        residual=cfg.get("residual", False), hidden=cfg.get("hidden_size", 4096))
    if kw["hidden"] != 4096:
        raise ValueError("Released head encoder width mismatch")
    state, action = module.make_head(**kw), module.make_head(**kw)
    state.load_state_dict(checkpoint["state_head"], strict=True)
    action.load_state_dict(checkpoint["action_head"], strict=True)
    state.eval()
    action.eval()
    scale = float(torch.as_tensor(checkpoint["logit_scale"]).float().exp().clamp(max=100.0))
    load_seconds = time.monotonic() - begin
    with torch.inference_mode():
        zs = torch.nn.functional.normalize(state(torch.from_numpy(vectors[:8])), dim=-1)
        za = torch.nn.functional.normalize(action(torch.from_numpy(vectors[8:])), dim=-1)
        begin = time.monotonic()
        logits = scale * (zs @ za.T)
        torch_logits = logits.numpy()
        # Independent cosine/scaling arithmetic after the official projections.
        np_logits = scale * np.sum(zs.numpy()[:, None, :] * za.numpy()[None, :, :], axis=2)
        arithmetic_error = float(np.max(np.abs(torch_logits - np_logits)))
        if not np.isfinite(torch_logits).all() or arithmetic_error > SPEC["head_score_absolute_tolerance"]:
            raise ValueError("CLM head score arithmetic failed")
        pair_p = torch.softmax(logits, dim=-1)[:, 1].numpy()
        sigmoid_p = torch.sigmoid(logits[:, 1] - logits[:, 0]).numpy()
        if not np.allclose(pair_p, sigmoid_p, atol=1e-6, rtol=0):
            raise ValueError("Binary CLM margin/softmax identity failed")
        arithmetic_seconds = time.monotonic() - begin
        warm = []
        for vector in vectors[:8]:
            begin = time.monotonic()
            z = torch.nn.functional.normalize(state(torch.from_numpy(vector[None, :])), dim=-1)
            scores = scale * (z @ za.T)
            _ = scores.numpy().copy()
            warm.append(time.monotonic() - begin)
    return {"checkpoint_cfg": cfg, "parameters": sum(p.numel() for h in (state, action) for p in h.parameters()),
        "scale": scale, "projection_dimension": kw["proj"], "load_seconds": load_seconds,
        "warm_state_projection_and_pair_scoring_seconds": warm,
        "arithmetic_seconds": arithmetic_seconds, "maximum_arithmetic_difference": arithmetic_error,
        "binary_margin_identity_pass": True,
        "synthetic_logits": torch_logits.tolist(),
        "qualification": "dimensions and implementation arithmetic only; no original-precision embedding comparison"}


def execute():
    import numpy as np
    plan = checked_plan()
    if validate_assets() != plan["assets"]:
        raise ValueError("Assets changed after freezing")
    for name, expected in plan["head_runtime_packages"].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("Head dependencies changed")
    with run_lock(OUTPUT):
        write_new(OUTPUT / "invocation.json", {"plan_sha256": digest(plan), "started_at_unix": time.time(), "invocations": 1})
        maximum_rss, termination = 0, None
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"), HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
        start = time.monotonic()
        with (OUTPUT / "encoder.log").open("x") as log:
            process = subprocess.Popen([str(ENV / "venv/bin/python"), str(Path(__file__).resolve()), "--encode-worker"],
                cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    status = subprocess.run(["ps", "-o", "rss=", "-p", str(process.pid)], text=True, capture_output=True)
                    if status.returncode and process.poll() is None:
                        raise ValueError("Worker RSS telemetry unavailable")
                    rss = int(status.stdout.strip() or "0") * 1024
                    maximum_rss = max(maximum_rss, rss)
                    if maximum_rss > SPEC["maximum_observed_worker_rss_bytes"]:
                        termination = "worker RSS exceeded the observed cap"
                    if time.monotonic() - start > SPEC["worker_wall_seconds"]:
                        termination = "worker wall limit exceeded"
                    if termination:
                        break
                    time.sleep(SPEC["rss_poll_seconds"])
            except Exception as exc:
                termination = f"Worker observation failed: {type(exc).__name__}: {exc}"
            finally:
                # Also clean up this child if the parent is interrupted. Never
                # signal a service or process outside this invocation.
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            code = process.wait()
        report = {"plan_sha256": digest(plan), "worker_exit_code": code,
            "worker_wall_seconds": time.monotonic() - start,
            "maximum_polled_worker_rss_bytes": maximum_rss, "termination": termination,
            "status": "failed_engineering", "no_cached_panel_access": True,
            "no_solver_generation": True, "cloud_spend_usd": 0.0,
            "limitations": ["Synthetic single-encoder resource profile only, not task accuracy",
                "Memory guideline is not a hard allocator cap; RSS sampled every 0.5 seconds",
                "No full-precision anchors; quantized transfer quality unvalidated",
                "Solver/router co-resident end-to-end cost not measured",
                "Synthetic timing is not an estimate of real draft length distribution"]}
        try:
            if code or termination:
                raise ValueError(termination or "Encoder worker failed; inspect preserved log")
            encoder = verified(OUTPUT / "encoder-report.json")
            if (encoder["plan_sha256"] != digest(plan)
                    or sha(OUTPUT / "synthetic-embeddings.npz") != encoder["embedding_file_sha256"]):
                raise ValueError("Encoder endpoint identity changed")
            with np.load(OUTPUT / "synthetic-embeddings.npz", allow_pickle=False) as values:
                vectors = values["vectors"]
            report["geometry"] = check_geometry(encoder["rows"], vectors)
            report["heads"] = head_check(vectors)
            report["encoder"] = encoder
            if encoder["mlx_peak_bytes"] > SPEC["maximum_observed_peak_mlx_bytes"]:
                raise ValueError("Measured MLX peak failed the gate")
            for path, expected in plan["protected_file_sha256"].items():
                if sha(path) != expected:
                    raise ValueError("Protected experiment input changed")
            report["protected_inputs_unchanged"] = True
            report["status"] = "engineering_pass_quantized_transfer_unvalidated"
        except Exception as exc:
            report["failure"] = f"{type(exc).__name__}: {exc}"
        write_new(OUTPUT / "report.json", report)
        print({"status": report["status"], "report_sha256": digest(report)}, flush=True)
        if report["status"] == "failed_engineering":
            raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--encode-worker", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    elif args.freeze:
        freeze()
    elif args.encode_worker:
        worker()
    else:
        execute()


if __name__ == "__main__":
    main()
