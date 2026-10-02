"""One frozen cached released-CLM diagnostic, with matched encoder control.

Separate prepare / execute commands, one encoder invocation, no solver generation
or reference fetching. Worker sees a label-free request file, never the panel.
"""

import argparse
import importlib.metadata
import importlib.util
import os
import subprocess
import time
from pathlib import Path

from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import clm_local_preflight as local

ROOT = local.ROOT
STUDY = local.BASE / "repeat-panel-v1"
OUTPUT = local.BASE / "repeat-clm-probe-v1"
FAMILIES = ("clm_calibrated", "raw_encoder_ridge")
STATE_TEMPLATE = (
    "Choose whether to accept a direct draft or request a fresh thinking solve.\n"
    "Solver: Qwen3-1.7B. Thinking receives only the original question.\n"
    "Objective: expected correctness minus 0.05 times generated tokens divided by 1000.\n"
    "The direct draft has already been generated.\n"
    "Original question:\n{question}\nDirect draft:\n{draft}\n"
)
SPEC = {"version": "repeat-clm-probe-v1", "label": "exploratory/reused-development",
    "lambda": .05, "families": list(FAMILIES), "alphas": [100., 1000., 10000.],
    "thresholds": [0., .02, .05], "pca_components": 8, "pca_solver": "full",
    "raw_control": "training-state PCA8; StandardScaler; divide by sqrt(8); Ridge gain",
    "calibration": "StandardScaler of frozen CLM scalar margin; Ridge gain with intercept",
    "auxiliary_draft_features": False, "released_head_finetuning": False,
    "zero_shot": "strict think-minus-accept margin > 0; no tuning",
    "conditions": {"k4_A_to_B": [[0, 1, 2, 3], [4, 5, 6, 7]],
                   "k4_B_to_A": [[4, 5, 6, 7], [0, 1, 2, 3]],
                   "k8_full": [list(range(8)), list(range(8))]},
    "inner_folds": 4, "split_seed": 20261002, "threads": 1,
    "selection": "inner mean question utility; ties prefer larger alpha then threshold; family order",
    "maximum_ridge_fits": 450, "maximum_pca_fits": 75,
    "bootstrap_seed": 20261006, "bootstrap_draws": 2000, "interval": [.05, .95],
    "promotion_minimum_mean": .01,
    "max_input_tokens": 2047, "token_recipe": "plain text, no added special tokens; retain tail",
    "batch_size": 1, "state_count": 400, "action_count": 2,
    "memory_guideline_bytes": 7 * 1024**3, "cache_limit_bytes": 128 * 1024**2,
    "maximum_observed_peak_mlx_bytes": 7 * 1024**3,
    "maximum_polled_worker_rss_bytes": 9 * 1024**3,
    "worker_wall_seconds": 2400, "per_input_seconds": 60., "rss_poll_seconds": .5,
    "encoder_invocations": 1, "retries": 0, "docker": "keep running",
    "scope": "one quantized released-head adaptation; no primary gate or deployment claim"}


def new(path, value):
    local.write_new(path, value)


def checked_output():
    if OUTPUT.is_symlink() or OUTPUT.resolve() != local.BASE.resolve() / SPEC["version"]:
        raise ValueError("Only the separate CLM probe artifact directory is writable")


def requests_for(panel):
    """Do not even index result fields on a thinking row."""
    questions = {item["question"]["id"]: item["question"]["prompt"]
                 for item in panel["protocol"]["selected"]}
    if set(questions) != set(panel["ids"]):
        raise ValueError("Frozen question inventory differs")
    drafts = {}
    for row in panel["rows"]:
        job = row["job"]
        if job["mode"] != "direct":
            continue
        key = (job["question_id"], job["sample"])
        if key in drafts or row["status"] != "completed":
            raise ValueError("Duplicate or incomplete direct draft")
        drafts[key] = row["result"]["final_answer"]
    expected = {(qid, draw) for qid in panel["ids"] for draw in range(8)}
    if set(drafts) != expected or any(not isinstance(text, str) for text in drafts.values()):
        raise ValueError("Complete direct-only draft coverage required")
    return {"schema_version": 1, "states": [{"question_id": qid, "sample": draw,
        "text": STATE_TEMPLATE.format(question=questions[qid], draft=drafts[qid, draw])}
        for qid in panel["ids"] for draw in range(8)], "actions": local.ACTIONS}


def source_paths():
    from reasoning_budget import repeat_stats
    from scripts import repeat_cpu_feasibility as cpu
    return [Path(__file__), Path(local.__file__), Path(cpu.__file__), Path(repeat_stats.__file__),
        ROOT / "scripts/diagnose_repeat_signal.py", ROOT / "scripts/repeat_contrastive_pilot.py",
        ROOT / "src/reasoning_budget/storage.py", ROOT / "tests/test_repeat_clm_probe.py",
        ROOT / "docs/phase-2-clm-probe-protocol.md"]


def prepare():
    from scripts.repeat_cpu_feasibility import load_panel
    checked_output()
    panel = load_panel(STUDY)
    preflight = verified(local.OUTPUT / "report.json")
    if (digest(preflight) != "53e2d76b735ee820a193dd66021bd0c1c7778015cc42593c2fe2a18de022f902"
            or preflight["status"] != "engineering_pass_quantized_transfer_unvalidated"):
        raise ValueError("Require the completed engineering pass")
    assets = local.validate_assets()
    request = requests_for(panel)
    plan = {"spec": SPEC, "state_template": STATE_TEMPLATE, "action_texts": local.ACTIONS,
        "request_sha256": digest(request), "panel_identity": panel["identity"], "assets": assets,
        "preflight_sha256": digest(preflight),
        "source_sha256": {str(p.resolve()): local.sha(p) for p in source_paths()},
        "analysis_packages": {name: importlib.metadata.version(name) for name in
            ("numpy", "scipy", "scikit-learn", "threadpoolctl", "torch")},
        "question_ids": panel["ids"], "folds": panel["folds"],
        "no_new_references": True, "no_solver_generation": True, "cloud_spend_usd": 0.}
    with run_lock(OUTPUT):
        new(OUTPUT / "encoder-request.json", request)
        new(OUTPUT / "analysis-plan.json", plan)
    print({"prepared": True, "plan_sha256": digest(plan), "states": len(request["states"])})


def checked_plan():
    checked_output()
    plan = verified(OUTPUT / "analysis-plan.json")
    if plan["spec"] != SPEC or plan["state_template"] != STATE_TEMPLATE or plan["action_texts"] != local.ACTIONS:
        raise ValueError("Frozen CLM specification changed")
    for path, expected in plan["source_sha256"].items():
        if local.sha(path) != expected:
            raise ValueError("Frozen CLM source/protocol changed")
    return plan


def tail_ids(tokenizer, text):
    ids = tokenizer.encode(text, add_special_tokens=False)
    if not ids:
        ids = tokenizer.encode(" ", add_special_tokens=False)
    if not ids:
        raise ValueError("Empty tokenized state")
    return ids[-SPEC["max_input_tokens"]:], {"raw_tokens": len(ids),
        "kept_tokens": min(len(ids), SPEC["max_input_tokens"]),
        "truncated": len(ids) > SPEC["max_input_tokens"]}


def worker():
    import mlx.core as mx
    import numpy as np
    from mlx_lm import load
    plan = checked_plan()
    request = verified(OUTPUT / "encoder-request.json")
    if digest(request) != plan["request_sha256"] or len(request["states"]) != 400 or request["actions"] != local.ACTIONS:
        raise ValueError("Frozen label-free encoder request changed")
    for name in ("mlx", "mlx-lm", "mlx-metal", "numpy", "transformers", "tokenizers"):
        if importlib.metadata.version(name) != plan["assets"]["packages"][name]:
            raise ValueError("Frozen encoder environment changed")
    if not mx.metal.is_available():
        raise ValueError("Native Metal unavailable")
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(SPEC["memory_guideline_bytes"])
    mx.set_cache_limit(SPEC["cache_limit_bytes"])
    began = time.monotonic()
    model, tokenizer = load(str(local.ENV / "assets/encoder"), lazy=False,
        tokenizer_config={"trust_remote_code": False})
    load_seconds = time.monotonic() - began
    vectors, rows = [], []
    jobs = [("state", item["text"]) for item in request["states"]]
    jobs += [("action", text) for text in request["actions"]]
    for i, (kind, text) in enumerate(jobs):
        began = time.perf_counter()
        ids, meta = tail_ids(tokenizer, text)
        tokenization_seconds = time.perf_counter() - began
        forward = time.perf_counter()
        hidden = model.model(mx.array([ids], dtype=mx.int32), cache=None)
        vector = hidden[:, -1, :].astype(mx.float32)
        vector = vector / mx.maximum(mx.linalg.norm(vector, axis=-1, keepdims=True), 1e-12)
        mx.eval(vector)
        value = np.asarray(vector)[0].copy()
        forward_seconds = time.perf_counter() - forward
        seconds = time.perf_counter() - began
        if value.shape != (4096,) or not np.isfinite(value).all() or abs(np.linalg.norm(value) - 1) > 1e-5:
            raise ValueError("Invalid last-token vector")
        meta.update(kind=kind, index=i, text_sha256=digest(text), input_ids_sha256=digest(ids),
            tokenization_seconds=tokenization_seconds, forward_to_numpy_seconds=forward_seconds,
            total_seconds=seconds, mlx_peak_bytes=mx.get_peak_memory())
        vectors.append(value)
        rows.append(meta)
        del hidden, vector
        atomic_json(OUTPUT / "encoder-progress.json", envelope({"completed_inputs": i + 1,
            "total_inputs": 402, "latest_seconds": seconds, "mlx_peak_bytes": mx.get_peak_memory()}))
        if i % 40 == 0 or i == 401:
            print({"completed_inputs": i + 1, "total_inputs": 402, "latest_seconds": round(seconds, 3)}, flush=True)
        if mx.get_peak_memory() > SPEC["maximum_observed_peak_mlx_bytes"] or seconds > SPEC["per_input_seconds"]:
            raise ValueError("Encoder resource/latency gate exceeded; no retry")
    with (OUTPUT / "encoder-features.npz").open("xb") as stream:
        np.savez(stream, states=np.stack(vectors[:400]).reshape(50, 8, 4096), actions=np.stack(vectors[400:]))
    new(OUTPUT / "encoder-report.json", {"plan_sha256": digest(plan),
        "request_sha256": digest(request), "feature_file_sha256": local.sha(OUTPUT / "encoder-features.npz"),
        "load_seconds": load_seconds, "rows": rows, "mlx_peak_bytes": mx.get_peak_memory(),
        "truncated_states": sum(row["truncated"] for row in rows[:400])})


def released_margins(states, actions):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    began = time.perf_counter()
    ck = torch.load(local.ENV / "assets/heads/CLM_v0.1-8B.pt", map_location="cpu", weights_only=True)
    cfg = dict(ck["cfg"])
    spec = importlib.util.spec_from_file_location("frozen_probe_clm_heads", local.ENV / "assets/official-heads.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kw = dict(width=cfg["width"], depth=cfg["depth"],
        proj=ck.get("projection_dim", cfg.get("projection_dim", 512)),
        activation=cfg.get("activation", "gelu"), layernorm=cfg.get("layernorm", False),
        residual=cfg.get("residual", False), hidden=cfg.get("hidden_size", 4096))
    sh, ah = module.make_head(**kw), module.make_head(**kw)
    sh.load_state_dict(ck["state_head"], strict=True)
    ah.load_state_dict(ck["action_head"], strict=True)
    sh.eval()
    ah.eval()
    scale = float(torch.as_tensor(ck["logit_scale"]).float().exp().clamp(max=100.))
    load_seconds = time.perf_counter() - began
    margins, durations, logits = [], [], []
    with torch.inference_mode():
        began = time.perf_counter()
        za = torch.nn.functional.normalize(ah(torch.from_numpy(actions)), dim=-1)
        action_seconds = time.perf_counter() - began
        for vector in states.reshape(-1, 4096):
            began = time.perf_counter()
            zs = torch.nn.functional.normalize(sh(torch.from_numpy(vector[None, :])), dim=-1)
            scores = (scale * (zs @ za.T)).numpy()[0].copy()
            durations.append(time.perf_counter() - began)
            logits.append(scores)
            margins.append(float(scores[1] - scores[0]))
    if not np.isfinite(margins).all():
        raise ValueError("Nonfinite released CLM margin")
    return np.asarray(margins).reshape(50, 8), np.asarray(durations).reshape(50, 8), {
        "load_seconds_after_import": load_seconds, "action_projection_seconds": action_seconds,
        "scale": scale, "checkpoint_cfg": cfg, "logits": np.asarray(logits).reshape(50, 8, 2).tolist(),
        "mean_state_projection_and_score_seconds": float(np.mean(durations))}


def validate_endpoint(encoder, request, states, actions):
    import numpy as np
    if states.shape != (50, 8, 4096) or actions.shape != (2, 4096):
        raise ValueError("Incomplete encoder feature endpoint")
    for values in (states, actions):
        if (values.dtype != np.float32 or not np.isfinite(values).all()
                or np.max(np.abs(np.linalg.norm(values, axis=-1) - 1)) > 1e-5):
            raise ValueError("Encoder features must be finite normalized float32")
    rows = encoder["rows"]
    texts = [item["text"] for item in request["states"]] + request["actions"]
    if len(rows) != 402 or len(texts) != 402:
        raise ValueError("Incomplete encoder rows")
    for i, (row, text) in enumerate(zip(rows, texts)):
        if (row["index"] != i or row["text_sha256"] != digest(text)
                or row["kind"] != ("state" if i < 400 else "action")
                or row["kept_tokens"] != min(row["raw_tokens"], SPEC["max_input_tokens"])
                or row["kept_tokens"] < 1
                or row["truncated"] != (row["raw_tokens"] > SPEC["max_input_tokens"])
                or not 0 <= row["total_seconds"] <= SPEC["per_input_seconds"]
                or row["mlx_peak_bytes"] > SPEC["maximum_observed_peak_mlx_bytes"]):
            raise ValueError("Encoder row binding or resource gate differs")
    if (encoder["truncated_states"] != sum(row["truncated"] for row in rows[:400])
            or encoder["mlx_peak_bytes"] > SPEC["maximum_observed_peak_mlx_bytes"]):
        raise ValueError("Encoder truncation/resource summary differs")


class Representation:
    def __init__(self, family, semantic, margin, questions, draws):
        import numpy as np
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        self.family, self.pca = family, None
        if family == "raw_encoder_ridge":
            raw = semantic[np.ix_(questions, draws)].reshape(-1, semantic.shape[-1])
            self.pca = PCA(n_components=8, svd_solver="full").fit(raw)
            values = self.pca.transform(raw)
        elif family == "clm_calibrated":
            values = margin[np.ix_(questions, draws)].reshape(-1, 1)
        else:
            raise ValueError("Unknown probe representation")
        self.scaler = StandardScaler().fit(values)

    def transform(self, semantic, margin, questions, draws):
        import numpy as np
        if self.pca is not None:
            raw = semantic[np.ix_(questions, draws)].reshape(-1, semantic.shape[-1])
            values = self.pca.transform(raw)
        else:
            values = margin[np.ix_(questions, draws)].reshape(-1, 1)
        result = self.scaler.transform(values) / (np.sqrt(8) if self.pca is not None else 1)
        if not np.isfinite(result).all():
            raise ValueError("Nonfinite supervised features")
        return result


def config_key(family, alpha, threshold):
    return f"{family}:alpha={alpha:g}:threshold={threshold:g}"


def fit_fold(semantic, margin, d, t, z, train, test, train_draws, eval_draws, fold):
    import numpy as np
    from sklearn.linear_model import Ridge

    from reasoning_budget import repeat_stats as historical
    if set(train) & set(test) or (train_draws != eval_draws and set(train_draws) & set(eval_draws)):
        raise ValueError("Held-out questions or independent draws overlap")
    gain = t[..., 0] - d[..., 0] - .05 * t[..., 1] / 1000
    splits = historical._inner_splits(train, SPEC["split_seed"] + fold, 4)
    scores = {config_key(f, a, h): [] for f in FAMILIES for a in SPEC["alphas"] for h in SPEC["thresholds"]}
    for inside, heldout in splits:
        for family in FAMILIES:
            rep = Representation(family, semantic, margin, inside, train_draws)
            x = rep.transform(semantic, margin, inside, train_draws)
            v = rep.transform(semantic, margin, heldout, train_draws)
            y = gain[np.ix_(inside, train_draws)].ravel()
            for alpha in SPEC["alphas"]:
                predicted = Ridge(alpha=alpha).fit(x, y).predict(v).reshape(len(heldout), len(train_draws))
                for threshold in SPEC["thresholds"]:
                    scores[config_key(family, alpha, threshold)].extend(historical._rows(
                        d, t, heldout, train_draws, predicted > threshold, .05)["utility"])
    means = {key: float(np.mean(values)) for key, values in scores.items()}
    settings = {}
    for family in FAMILIES:
        alpha, threshold = max(((a, h) for a in SPEC["alphas"] for h in SPEC["thresholds"]),
            key=lambda pair: (means[config_key(family, *pair)], *pair))
        settings[family] = {"alpha": alpha, "threshold": threshold,
            "inner_utility": means[config_key(family, alpha, threshold)]}
    selected = max(FAMILIES, key=lambda family: settings[family]["inner_utility"])
    threshold = historical._confidence_threshold(z, d, t, train, train_draws, .05)
    shape = (len(test), len(eval_draws))
    actions = {"accept": np.zeros(shape, bool), "escalate": np.ones(shape, bool),
        "confidence": z[np.ix_(test, eval_draws, [0])][:, :, 0] < threshold,
        "clm_zero_shot": margin[np.ix_(test, eval_draws)] > 0}
    inference_times = {}
    for family in FAMILIES:
        rep = Representation(family, semantic, margin, train, train_draws)
        x = rep.transform(semantic, margin, train, train_draws)
        v = rep.transform(semantic, margin, test, eval_draws)
        y = gain[np.ix_(train, train_draws)].ravel()
        selected_model = None
        for alpha in SPEC["alphas"]:
            model = Ridge(alpha=alpha).fit(x, y)
            prediction = model.predict(v).reshape(shape)
            for h in SPEC["thresholds"]:
                actions[config_key(family, alpha, h)] = prediction > h
            if alpha == settings[family]["alpha"]:
                selected_model = model
        actions[family] = actions[config_key(family, settings[family]["alpha"], settings[family]["threshold"])]
        times = np.zeros(shape)
        for j, question in enumerate(test):
            for k, draw in enumerate(eval_draws):
                began = time.perf_counter()
                single = rep.transform(semantic, margin, [question], [draw])
                selected_model.predict(single)
                times[j, k] = time.perf_counter() - began
        inference_times[family] = times
    actions["nested_selected"] = actions[selected].copy()
    inference_times["nested_selected"] = inference_times[selected].copy()
    return actions, {"fold": fold, "train_indices": list(map(int, train)), "test_indices": list(map(int, test)),
        "train_draws": train_draws, "evaluation_draws": eval_draws,
        "inner_splits": [{"train_indices": a.tolist(), "validation_indices": b.tolist(), "draws": train_draws}
                         for a, b in splits], "settings": settings, "selected_family": selected,
        "inner_utility": means, "confidence_threshold": float(threshold), "ridge_fits": 30, "pca_fits": 5}, inference_times


def analyze(panel, semantic, margin, encoder_seconds, head_seconds):
    import numpy as np

    from reasoning_budget import repeat_stats as historical
    from scripts.repeat_contrastive_pilot import screen
    from scripts.repeat_cpu_feasibility import summarize
    ids, d, t, z, folds = (panel[key] for key in ("ids", "d", "t", "z", "folds"))
    conditions, fits, pcas = {}, 0, 0
    for name, (train_draws, eval_draws) in SPEC["conditions"].items():
        rows = {qid: {"fold": folds[qid], "policies": {}} for qid in ids}
        details = []
        for fold in range(5):
            train = [i for i, qid in enumerate(ids) if folds[qid] != fold]
            test = [i for i, qid in enumerate(ids) if folds[qid] == fold]
            actions, detail, prediction_times = fit_fold(semantic, margin, d, t, z, train, test, train_draws, eval_draws, fold)
            if "primary" in panel:
                cached = panel["primary"]["statistics"]["conditions"][name]["per_question"]
                if any(actions["confidence"][j].tolist() != cached[ids[i]]["policies"]["confidence"]["decisions"]
                       for j, i in enumerate(test)):
                    raise ValueError("Historical confidence actions changed")
            detail.update(train_ids=[ids[i] for i in train], test_ids=[ids[i] for i in test])
            details.append(detail)
            fits += detail["ridge_fits"]
            pcas += detail["pca_fits"]
            for policy, decision in actions.items():
                metrics = historical._rows(d, t, test, eval_draws, decision, .05)
                for j, i in enumerate(test):
                    record = {key: float(value[j]) for key, value in metrics.items()} | {"decisions": decision[j].tolist()}
                    if policy in ("clm_zero_shot", *FAMILIES, "nested_selected"):
                        family = detail["selected_family"] if policy == "nested_selected" else policy
                        overhead = encoder_seconds[i, eval_draws].copy()
                        if family in ("clm_zero_shot", "clm_calibrated"):
                            overhead += head_seconds[i, eval_draws]
                        if policy in prediction_times:
                            overhead += prediction_times[policy][j]
                        record["observed_router_seconds_by_draw"] = overhead.tolist()
                        record["cached_solver_plus_observed_router_seconds"] = record["seconds"] + float(overhead.mean())
                    rows[ids[i]]["policies"][policy] = record
        summary = summarize(ids, rows, d, t, eval_draws)
        for policy in ("clm_zero_shot", *FAMILIES, "nested_selected"):
            summary[policy]["cached_solver_plus_observed_router_seconds"] = float(np.mean([
                rows[qid]["policies"][policy]["cached_solver_plus_observed_router_seconds"] for qid in ids]))
        conditions[name] = {"train_draws": train_draws, "evaluation_draws": eval_draws,
            "folds": details, "per_question": rows, "summary": summary}
    if fits != 450 or pcas != 75:
        raise ValueError("Frozen fit grid incomplete")
    averages, screens = {}, {}
    for policy in ("clm_zero_shot", *FAMILIES, "nested_selected"):
        a, b = [np.asarray([conditions[name]["per_question"][qid]["policies"][policy]["utility"] -
            conditions[name]["per_question"][qid]["policies"]["confidence"]["utility"] for qid in ids])
            for name in ("k4_A_to_B", "k4_B_to_A")]
        average = (a + b) / 2
        averages[policy] = {"mean": float(average.mean()), "ci90": historical._ci(average, SPEC),
            "per_question": dict(zip(ids, map(float, average))),
            "A_to_B": float(a.mean()), "B_to_A": float(b.mean())}
        result = screen(a, b)
        result["average_ci90"] = averages[policy]["ci90"]
        screens[policy] = result
    difference = np.asarray([np.mean([conditions[name]["per_question"][qid]["policies"]["clm_calibrated"]["utility"] -
        conditions[name]["per_question"][qid]["policies"]["raw_encoder_ridge"]["utility"]
        for name in ("k4_A_to_B", "k4_B_to_A")]) for qid in ids])
    return {"conditions": conditions, "averages_vs_confidence": averages, "screens": screens,
        "calibrated_clm_minus_raw_control": {"mean": float(difference.mean()), "ci90": historical._ci(difference, SPEC)},
        "fit_count": fits, "pca_fit_count": pcas, "historical_confidence_actions_exactly_reproduced": "primary" in panel}


def encode_child(plan):
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT),
        HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    began, maximum_rss, termination = time.monotonic(), 0, None
    with (OUTPUT / "encoder.log").open("x") as log:
        process = subprocess.Popen([str(local.ENV / "venv/bin/python"), "-u", str(Path(__file__).resolve()), "worker"],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                status = subprocess.run(["ps", "-o", "rss=", "-p", str(process.pid)], text=True, capture_output=True)
                if status.returncode and process.poll() is None:
                    raise ValueError("RSS observation failed")
                maximum_rss = max(maximum_rss, int(status.stdout.strip() or "0") * 1024)
                if maximum_rss > SPEC["maximum_polled_worker_rss_bytes"]:
                    termination = "observed worker RSS exceeded cap"
                if time.monotonic() - began > SPEC["worker_wall_seconds"]:
                    termination = "encoder wall cap exceeded"
                if termination:
                    break
                time.sleep(SPEC["rss_poll_seconds"])
        except Exception as exc:
            termination = f"observer failed: {type(exc).__name__}: {exc}"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        code = process.wait()
    return {"exit_code": code, "maximum_polled_worker_rss_bytes": maximum_rss,
        "wall_seconds": time.monotonic() - began, "termination": termination, "plan_sha256": digest(plan)}


def execute():
    import numpy as np
    from threadpoolctl import threadpool_limits

    from scripts.repeat_cpu_feasibility import load_panel
    plan = checked_plan()
    if (OUTPUT / "invocation.json").exists():
        raise ValueError("CLM probe already invoked; never reset or restart")
    if local.validate_assets() != plan["assets"]:
        raise ValueError("Pinned assets changed")
    for name, expected in plan["analysis_packages"].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("Analysis dependencies changed")
    panel = load_panel(STUDY)
    if panel["identity"] != plan["panel_identity"] or digest(requests_for(panel)) != plan["request_sha256"]:
        raise ValueError("Panel/request identity changed")
    with run_lock(OUTPUT):
        new(OUTPUT / "invocation.json", {"plan_sha256": digest(plan), "started_unix": time.time(), "invocations": 1})
        atomic_json(OUTPUT / "status.json", envelope({"status": "encoding", "plan_sha256": digest(plan)}))
        process = encode_child(plan)
        new(OUTPUT / "encoder-process.json", process)
        if process["exit_code"] or process["termination"]:
            atomic_json(OUTPUT / "status.json", envelope({"status": "failed_encoder_no_retry", "process": process}))
            raise ValueError("Encoder failed; preserve journal and log, no retry")
        encoder = verified(OUTPUT / "encoder-report.json")
        if (encoder["plan_sha256"] != digest(plan) or encoder["request_sha256"] != plan["request_sha256"]
                or local.sha(OUTPUT / "encoder-features.npz") != encoder["feature_file_sha256"]):
            raise ValueError("Encoder endpoint identity changed")
        with np.load(OUTPUT / "encoder-features.npz", allow_pickle=False) as feature:
            states, actions = feature["states"], feature["actions"]
        validate_endpoint(encoder, verified(OUTPUT / "encoder-request.json"), states, actions)
        atomic_json(OUTPUT / "status.json", envelope({"status": "analyzing", "plan_sha256": digest(plan)}))
        margin, head_times, head = released_margins(states, actions)
        new(OUTPUT / "released-head-report.json", head | {"plan_sha256": digest(plan), "margins": margin.tolist(), "state_head_seconds": head_times.tolist()})
        began = time.perf_counter()
        encoder_times = np.asarray([r["total_seconds"] for r in encoder["rows"][:400]]).reshape(50, 8)
        with threadpool_limits(limits=1):
            statistics = analyze(panel, states, margin, encoder_times, head_times)
        analysis_seconds = time.perf_counter() - began
        if load_panel(STUDY)["identity"] != plan["panel_identity"] or checked_plan() != plan:
            raise ValueError("Frozen inputs changed during execution")
        report = {"plan_sha256": digest(plan), "panel_identity": panel["identity"], "spec": SPEC,
            "encoder_report_sha256": digest(encoder), "statistics": statistics,
            "analysis_seconds": analysis_seconds, "primary_gates_unchanged": panel["primary"]["statistics"]["gates"],
            "no_solver_generation": True, "no_new_references": True, "cloud_spend_usd": 0.,
            "limitations": ["Reused-development; fixed-fit question bootstrap omits selection/refitting uncertainty",
                "Full8 has no independent same-question eight-draw replica",
                "Quantized MLX adaptation; no official full-precision or pretraining-disjointness claim",
                "One fixed state/action text and low-capacity calibration; no prompt or head-finetuning search",
                "Backbone is matched, head capacity and prior training are not matched; no contrastive-objective causal claim",
                "Generated-token utility excludes encoder work; timing sums are proxies from different runs, not live end-to-end measurements",
                "No auxiliary draft statistics or confidence/CLM fusion learner is tested"]}
        new(OUTPUT / "report.json", report)
        atomic_json(OUTPUT / "status.json", envelope({"status": "complete", "report_sha256": digest(report),
            "screens_pass": {name: value["passes"] for name, value in statistics["screens"].items()}, "primary_gates_unchanged": True}))
        print({"status": "complete", "report_sha256": digest(report),
            "average_deltas": {name: value["mean"] for name, value in statistics["averages_vs_confidence"].items()}}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "worker"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "worker":
        worker()
    else:
        already_invoked = (OUTPUT / "invocation.json").exists()
        try:
            execute()
        except Exception as exc:
            if not already_invoked and (OUTPUT / "invocation.json").exists() and not (OUTPUT / "report.json").exists():
                atomic_json(OUTPUT / "status.json", envelope({"status": "failed_no_retry", "error": f"{type(exc).__name__}: {exc}"}))
            raise


if __name__ == "__main__":
    main()
