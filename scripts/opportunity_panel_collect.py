"""Frozen local two-solver opportunity diagnostic with one shared ledger.

Preparation resolves local tokenizers only. Reference access is endpoint locked.
"""

import argparse
import math
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from reasoning_budget.backend import GENERATION_PROTOCOL, TransformersBackend, environment
from reasoning_budget.config import from_dict, load_config
from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob, GenerationResult, Question
from reasoning_budget.runner import build_jobs, implementation_digest, valid_record_result
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, run_lock, verified
from scripts import opportunity_panel_plan as child_plan
from scripts import opportunity_solver_preflight as asset_preflight

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
STUDY = BASE / "opportunity-panel-v1"
SOLVERS = ("qwen3-1.7b", "qwen3-0.6b")
SEEDS = dict(zip(SOLVERS, (20261010, 20261011)))
SPEC = {"version": "opportunity-panel-v1", "questions": 64, "draws": 2,
    "responses": 512, "response_only_tokens": 786944, "global_tokens": 1000000,
    "global_seconds": 43200, "setup_seconds": 900, "job_seconds": 600,
    "maximum_setups": 4, "invocations_per_solver": 2, "maximum_supervisor_launches": 3,
    "supervisor_seconds": 50400, "poll_seconds": 2, "watchdog_grace_seconds": 5,
    "maximum_polled_rss_bytes": 9 * 1024**3, "automatic_resume": False,
    "solver_order": list(SOLVERS), "seeds": SEEDS, "cloud_spend_usd": 0,
    "docker": "keep_running", "lambda": .05,
    "time_policy": "maximum of collection wall age and summed setup/attempt charges; gaps count",
    "incorrect_output_policy": "completed outputs include parser rejection/early_eos/answer_limit; no quality retry",
    "purpose": "solver-specific opportunity diagnostic, not superiority confirmation"}


class IntegrityError(ValueError):
    pass


class BudgetExhausted(RuntimeError):
    pass


def write_once(path, payload):
    """Atomic visibility, exclusive destination, durable file and directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        import json
        with os.fdopen(fd, "w") as stream:
            json.dump(envelope(payload), stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Fails if destination exists; never replaces it.
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.unlink(temporary)


def safe_paths():
    if STUDY.is_symlink() or STUDY.resolve() != BASE.resolve() / SPEC["version"]:
        raise IntegrityError("Only the new opportunity study is writable")
    if STUDY.exists() and any(p.is_symlink() for p in STUDY.rglob("*")):
        raise IntegrityError("Symlink in opportunity study")


def stable_environment():
    env = environment()
    return {k: env[k] for k in ("python", "platform", "machine", "packages", "mps_fallback")}


def source_files():
    paths = list((ROOT / "src/reasoning_budget").glob("*.py"))
    paths += [ROOT / name for name in (
        "scripts/opportunity_panel_collect.py", "scripts/opportunity_panel_analysis.py",
        "tests/test_opportunity_panel_collect.py", "tests/test_opportunity_panel_analysis.py",
        "tests/test_opportunity_panel_collector_review.py",
        "docs/opportunity-panel-protocol.md", "configs/research-repeat-v1.yaml",
        "scripts/opportunity_panel_plan.py", "scripts/opportunity_solver_preflight.py",
        "scripts/macos_runtime_guard.py", "scripts/verify_phase2_repeat.py")]
    return sorted(paths)


def assets_for(config):
    cache = Path(config.model.cache_dir).resolve()
    snapshot = cache / ("models--" + config.model.name.replace("/", "--")) / "snapshots" / config.model.revision
    common = ["config.json", "generation_config.json", "tokenizer_config.json",
              "tokenizer.json", "merges.txt", "vocab.json"]
    if config.model.name == "Qwen/Qwen3-1.7B":
        index = read_json(snapshot / "model.safetensors.index.json")
        common += ["model.safetensors.index.json", *sorted(set(index["weight_map"].values()))]
    else:
        common += ["model.safetensors"]
    if any(not (snapshot / name).resolve().is_relative_to(cache) for name in common):
        raise IntegrityError("Pinned model file escaped its cache")
    return {str(snapshot / name): file_hash(snapshot / name) for name in common}


def solver_config(solver, dataset):
    if solver not in SOLVERS:
        raise IntegrityError("Unknown solver")
    values = load_config(ROOT / "configs/research-repeat-v1.yaml").to_dict()
    values.update(name=f"opportunity64-{solver}", seed=SEEDS[solver], samples=2,
        split=child_plan.SPLIT, data_dir=str(dataset), output_dir=str(STUDY / "unused-runner"))
    values["limits"] = {"max_tokens": SPEC["global_tokens"],
        "max_elapsed_seconds": SPEC["global_seconds"], "job_seconds": SPEC["job_seconds"],
        "max_consecutive_failures": 1}
    if solver == SOLVERS[1]:
        values["model"].update(name=asset_preflight.REPO, revision=asset_preflight.REVISION,
            tokenizer_revision=asset_preflight.REVISION, cache_dir=str(asset_preflight.CACHE))
    else:
        values["model"]["cache_dir"] = str((ROOT / values["model"]["cache_dir"]).resolve())
    return from_dict(values)


def check_metadata(config, metadata):
    if (metadata["model_revision"] != config.model.revision
            or metadata["tokenizer_revision"] != config.model.tokenizer_revision
            or metadata["model_name"] != config.model.name
            or metadata["generation_protocol"] != GENERATION_PROTOCOL
            or metadata["closure_ids"] != [151668, 271] or metadata["closure_tokens"] != 2
            or metadata["eos_token_ids"] != [151643, 151645]
            or metadata["device"] != "mps" or metadata["dtype"] != "float16"
            or metadata["attention"] != "sdpa" or not config.model.local_files_only):
        raise IntegrityError("Resolved local solver differs from fixed protocol")


def prepare():
    from scripts.opportunity_panel_analysis import SPEC as analysis_spec
    safe_paths()
    with run_lock(STUDY / "preparation"):
        if (STUDY / "protocol.json").exists() or (STUDY / "prepare-started.json").exists():
            raise IntegrityError("Preparation is one-time; inspect its preserved artifacts")
        child = child_plan.verify(BASE, ROOT)
        preflight_plan = asset_preflight.checked_plan()
        preflight_assets = asset_preflight.assets_checked(preflight_plan)
        preflight_report = verified(asset_preflight.OUTPUT / "report.json")
        if (preflight_report["status"] != "synthetic_engineering_pass_collection_protocol_pending"
                or preflight_report["assets_sha256"] != digest(preflight_assets)):
            raise IntegrityError("Second-solver engineering foundation differs")
        start = {"spec": SPEC, "analysis": analysis_spec, "environment": stable_environment(),
            "source_file_sha256": {str(p): file_hash(p) for p in source_files()},
            "protected_file_sha256": {str(p): file_hash(p) for p in (
                *asset_preflight.protected_paths(), asset_preflight.OUTPUT / "plan.json",
                asset_preflight.OUTPUT / "assets.json", asset_preflight.OUTPUT / "report.json")},
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "child_sha256": digest(child), "preflight_report_sha256": digest(preflight_report),
            "started_at": time.time(), "no_reference_access": True}
        write_once(STUDY / "prepare-started.json", start)
        questions = [Question(**r["child_question"]) for r in child["selected"]]
        if len(questions) != 64:
            raise IntegrityError("Exactly 64 child questions required")
        dataset = BASE / "reserve-children" / child_plan.CHILD / "dataset"
        arms = {}
        for solver in SOLVERS:
            config = solver_config(solver, dataset)
            hashes = assets_for(config)
            engine = TransformersBackend(config)  # Local tokenizer/config; no weights.
            check_metadata(config, engine.metadata)
            jobs = build_jobs(config, questions, engine.metadata)
            arms[solver] = {"config": config.to_dict(), "backend_metadata": engine.metadata,
                "asset_file_sha256": hashes, "jobs": [j.to_dict() for j in jobs]}
        jobs = [j for arm in arms.values() for j in arm["jobs"]]
        if (len(jobs) != 512 or len({j["id"] for j in jobs}) != 512
                or len({j["seed"] for j in jobs}) != 512
                or sum(j["max_tokens"] for j in jobs) != SPEC["response_only_tokens"]):
            raise IntegrityError("Complete job shape/seeds/token reservation differs")
        from reasoning_budget import scoring_v7
        protocol = start | {"prepared_at": time.time(), "arms": arms,
            "selected": child["selected"], "folds": child["folds"],
            "generation_implementation_sha256": implementation_digest(),
            "scoring_version": "numeric-v7", "scoring_implementation_sha256": scoring_v7.implementation_digest(),
            "dataset_file_sha256": {str(dataset / n): file_hash(dataset / n) for n in ("questions.json", "manifest.json")},
            "gold_policy": "Complete both-arm 512-response endpoint before exactly 64 selected training references; cached sidecar thereafter"}
        write_once(STUDY / "protocol.json", protocol)
        atomic_json(STUDY / "status.json", {"state": "prepared", "completed": 0,
            "expected": 512, "generation_started": False, "analysis": "locked"})
        return {"prepared": True, "protocol_sha256": digest(protocol), "responses": 512}


def read_protocol(*, check_assets=False):
    from reasoning_budget import scoring_v7
    from scripts.opportunity_panel_analysis import SPEC as analysis_spec
    safe_paths()
    p = verified(STUDY / "protocol.json")
    if (p["spec"] != SPEC or p["analysis"] != analysis_spec
            or p["environment"] != stable_environment()
            or p["generation_implementation_sha256"] != implementation_digest()
            or p["scoring_implementation_sha256"] != scoring_v7.implementation_digest()):
        raise IntegrityError("Frozen source/settings/environment/scorer changed")
    for name in ("source_file_sha256", "dataset_file_sha256", "protected_file_sha256"):
        for path, sha in p[name].items():
            if file_hash(path) != sha:
                raise IntegrityError(f"Frozen input changed: {path}")
    child = verified(BASE / "reserve-children" / child_plan.CHILD / "child-manifest.json")
    if digest(child) != p["child_sha256"] or child["selected"] != p["selected"] or child["folds"] != p["folds"]:
        raise IntegrityError("Frozen child changed")
    dataset = Path(p["arms"][SOLVERS[0]]["config"]["data_dir"])
    if (dataset / "gold.json").exists() or read_json(dataset / "manifest.json")["gold_sha256"] is not None:
        raise IntegrityError("Question-only child gold is forbidden")
    for solver, arm in p["arms"].items():
        config = solver_config(solver, dataset)
        if arm["config"] != config.to_dict():
            raise IntegrityError("Frozen solver configuration changed")
        expected = [j.to_dict() for j in build_jobs(config,
            [Question(**r["child_question"]) for r in p["selected"]], arm["backend_metadata"])]
        if expected != arm["jobs"]:
            raise IntegrityError("Frozen jobs changed")
        check_metadata(config, arm["backend_metadata"])
        if check_assets:
            for path, sha in arm["asset_file_sha256"].items():
                if file_hash(path) != sha:
                    raise IntegrityError("Frozen local asset changed")
    return p


def finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def usage(protocol, *, now=None):
    """One authoritative immutable ledger for both solvers, including unknowns."""
    tokens, seconds, setups = 0, 0., 0
    pin = digest(protocol)
    # Creation order is reservation -> attempt record -> settlement. Observe in
    # reverse order so a concurrent append cannot look like an orphan receipt.
    receipts = {path.stem: verified(path) for path in (STUDY / "ledger/settlements").glob("*.json")}
    archives = {path.stem: verified(path) for path in (STUDY / "attempt-records").glob("*.json")}
    reservations = {path.stem: verified(path) for path in (STUDY / "ledger/reservations").glob("*.json")}
    if not set(receipts) <= set(reservations):
        raise IntegrityError("Settlement without reservation")
    if not set(archives) <= set(reservations):
        raise IntegrityError("Attempt record without reservation")
    invocations = {r["id"]: r for r in invocation_records(protocol)}
    setup_invocations = set()
    jobs = {j["id"]: (solver, j) for solver, arm in protocol["arms"].items() for j in arm["jobs"]}
    for key, r in reservations.items():
        if (r["id"] != key or r["protocol_sha256"] != pin or r["solver"] not in SOLVERS
                or r["kind"] not in ("setup", "job") or not finite_number(r["started_at"])
                or r["started_at"] < protocol["prepared_at"]
                or type(r["reserved_tokens"]) is not int or r["reserved_tokens"] < 0
                or not finite_number(r["reserved_seconds"]) or r["reserved_seconds"] <= 0):
            raise IntegrityError("Invalid shared reservation")
        invocation = invocations.get(r["invocation_id"])
        if (invocation is None or invocation["solver"] != r["solver"]
                or invocation["protocol_sha256"] != pin or r["started_at"] < invocation["reserved_at"]):
            raise IntegrityError("Reservation invocation changed")
        if r["kind"] == "setup":
            setups += 1
            if (r["reserved_tokens"] != 0 or r["reserved_seconds"] > SPEC["setup_seconds"]
                    or r["invocation_id"] in setup_invocations):
                raise IntegrityError("Invalid setup reservation")
            setup_invocations.add(r["invocation_id"])
        else:
            if (r["job_id"] not in jobs or jobs[r["job_id"]][0] != r["solver"]
                    or r["reserved_tokens"] != jobs[r["job_id"]][1]["max_tokens"]
                    or r["reserved_seconds"] > SPEC["job_seconds"]
                    or r["session_id"] not in reservations
                    or reservations[r["session_id"]]["kind"] != "setup"
                    or reservations[r["session_id"]]["invocation_id"] != r["invocation_id"]):
                raise IntegrityError("Invalid job reservation")
            setup_receipt = verified(STUDY / "ledger/settlements" / f"{r['session_id']}.json")
            if (setup_receipt["status"] != "loaded"
                    or setup_receipt["reservation_sha256"] != digest(reservations[r["session_id"]])
                    or r["started_at"] < setup_receipt["finished_at"]):
                raise IntegrityError("Job preceded completed model setup")
        receipt = receipts.get(key)
        spent, duration = r["reserved_tokens"], r["reserved_seconds"]
        if receipt is not None:
            if (receipt["reservation_sha256"] != digest(r) or receipt["id"] != key
                    or receipt["status"] not in (("loaded", "failed") if r["kind"] == "setup" else ("completed", "failed"))):
                raise IntegrityError("Invalid ledger settlement identity")
            spent, duration = receipt["charged_tokens"], receipt["elapsed_seconds"]
            if (type(spent) is not int or not 0 <= spent <= r["reserved_tokens"]
                    or not finite_number(duration) or duration < 0
                    or not finite_number(receipt["finished_at"]) or receipt["finished_at"] < r["started_at"]):
                raise IntegrityError("Invalid ledger settlement cost")
            if receipt["status"] in ("loaded", "completed") and duration > r["reserved_seconds"]:
                raise IntegrityError("Successful operation exceeded reserved clock")
            if r["kind"] == "job":
                record = archives.get(key)
                if (record is None or receipt.get("record_sha256") != digest(record)
                        or record["protocol_sha256"] != pin or record["solver"] != r["solver"]
                        or record["job"] != jobs[r["job_id"]][1]
                        or record["attempt_id"] != key or record["session_id"] != r["session_id"]
                        or record["implementation_sha256"] != protocol["generation_implementation_sha256"]
                        or record["status"] != receipt["status"]):
                    raise IntegrityError("Job settlement/attempt record changed")
                actual = r["reserved_tokens"]
                if record["result"] is not None:
                    try:
                        actual = validate_result(GenerationResult(**record["result"]), GenerationJob(**record["job"]))
                    except (IntegrityError, TypeError, KeyError):
                        if record["status"] == "completed":
                            raise IntegrityError("Completed attempt has invalid result") from None
                if spent != actual:
                    raise IntegrityError("Settlement charge differs from emitted tokens/conservative reservation")
                if record["status"] == "completed":
                    final = verified(STUDY / "results" / r["solver"] / f"{r['job_id']}.json")
                    if final != record:
                        raise IntegrityError("Completed attempt differs from final record")
        tokens += spent
        seconds += duration
    start_path = STUDY / "collection-start.json"
    start = None
    if start_path.exists():
        opening = verified(start_path)
        start = opening["started_at"]
        if (opening["protocol_sha256"] != pin or not finite_number(start)
                or start < protocol["prepared_at"]):
            raise IntegrityError("Invalid collection start record")
        if invocations and start != min(r["reserved_at"] for r in invocations.values()):
            raise IntegrityError("Collection start differs from first invocation")
    elif invocations:
        raise IntegrityError("Invocations lack collection start record")
    end = time.time() if now is None else now
    if (STUDY / "collection-end.json").exists():
        closing = verified(STUDY / "collection-end.json")
        if (closing["protocol_sha256"] != pin or not finite_number(closing["finished_at"])
                or start is None or closing["finished_at"] < start
                or any(closing["finished_at"] < r["started_at"] for r in reservations.values())
                or any(closing["finished_at"] < r["finished_at"] for r in receipts.values())):
            raise IntegrityError("Invalid collection end record")
        end = closing["finished_at"]
    age = max(0., end - start) if start is not None else 0.
    if setups > SPEC["maximum_setups"]:
        raise IntegrityError("Too many setup reservations")
    return {"charged_tokens": tokens, "charged_seconds": seconds, "collection_wall_seconds": age,
        "budget_seconds": max(seconds, age), "setup_reservations": setups,
        "attempts": sum(r["kind"] == "job" for r in reservations.values()),
        "unresolved": len(set(reservations) - set(receipts))}


def reserve(protocol, solver, invocation_id, kind, *, job=None, session_id=None):
    if (STUDY / "collection-end.json").exists():
        raise IntegrityError("Collection is closed to further reservations")
    tally = usage(protocol)
    maximum = SPEC["setup_seconds"] if kind == "setup" else SPEC["job_seconds"]
    remaining = SPEC["global_seconds"] - tally["budget_seconds"]
    tokens = job.max_tokens if job is not None else 0
    if (remaining <= 0 or tally["charged_tokens"] + tokens > SPEC["global_tokens"]
            or kind == "setup" and tally["setup_reservations"] >= SPEC["maximum_setups"]):
        raise BudgetExhausted("Shared collection budget cannot admit operation")
    key = uuid.uuid4().hex
    r = {"id": key, "protocol_sha256": digest(protocol), "solver": solver,
        "invocation_id": invocation_id, "kind": kind, "started_at": time.time(),
        "reserved_tokens": tokens, "reserved_seconds": min(maximum, remaining)}
    if job is not None:
        r.update(job_id=job.id, session_id=session_id)
    write_once(STUDY / "ledger/reservations" / f"{key}.json", r)
    atomic_json(STUDY / "active.json", envelope(r))
    return r


def settle(reservation, status, began, *, tokens=None, record=None):
    receipt = {"id": reservation["id"], "reservation_sha256": digest(reservation),
        "status": status, "charged_tokens": reservation["reserved_tokens"] if tokens is None else tokens,
        "elapsed_seconds": time.monotonic() - began, "finished_at": time.time()}
    if record is not None:
        receipt["record_sha256"] = digest(record)
    write_once(STUDY / "ledger/settlements" / f"{reservation['id']}.json", receipt)
    atomic_json(STUDY / "active.json", envelope({"kind": "idle"}))
    return receipt


def validate_result(result, job):
    if not valid_record_result(result, job):
        raise IntegrityError("Invalid generation token/time accounting")
    if result.termination not in {"eos", "early_eos", "answer_limit", "reasoning_in_answer", "timeout"}:
        raise IntegrityError("Unknown generation termination")
    if not isinstance(result.final_answer, str):
        raise IntegrityError("Invalid final answer type")
    metadata = result.metadata or {}
    for kind, count in (("reasoning", result.reasoning_tokens), ("answer", result.answer_tokens), ("inserted", result.inserted_tokens)):
        ids = metadata.get(f"{kind}_token_ids")
        if not isinstance(ids, list) or len(ids) != count or any(type(t) is not int or t < 0 for t in ids):
            raise IntegrityError("Token IDs/counts disagree")
    if metadata["inserted_token_ids"] not in ([], job.identity["backend"]["closure_ids"]):
        raise IntegrityError("Inserted closure differs from fixed tokenizer")
    if result.forced_closure != bool(result.inserted_tokens):
        raise IntegrityError("Forced closure accounting disagrees")
    if job.mode == "direct" and result.termination != "timeout" and not all(finite_number(v) for v in (
            result.mean_generated_logprob, result.mean_generated_logprob_raw)):
        raise IntegrityError("Finite direct raw/post-warper confidence required")
    if any(not finite_number(getattr(result, name)) or getattr(result, name) < 0 for name in
            ("reasoning_seconds", "answer_seconds", "closure_seconds")):
        raise IntegrityError("Invalid generation stage time")
    if result.termination in ("eos", "early_eos"):
        ids = metadata["answer_token_ids"] or metadata["reasoning_token_ids"]
        if not ids or ids[-1] not in job.identity["backend"]["eos_token_ids"]:
            raise IntegrityError("EOS termination lacks emitted EOS")
    return sum((result.answer_tokens, result.reasoning_tokens, result.inserted_tokens))


def completed_records(protocol):
    grouped = {}
    pin = digest(protocol)
    expected_paths = set()
    for solver, arm in protocol["arms"].items():
        rows = []
        for item in arm["jobs"]:
            path = STUDY / "results" / solver / f"{item['id']}.json"
            expected_paths.add(path)
            if not path.exists():
                continue
            r = verified(path)
            if (r["job"] != item or r["solver"] != solver or r["status"] != "completed"
                    or r["protocol_sha256"] != pin
                    or r["implementation_sha256"] != protocol["generation_implementation_sha256"]):
                raise IntegrityError("Completed result changed identity")
            job = GenerationJob(**item)
            validate_result(GenerationResult(**r["result"]), job)
            if r["result"]["termination"] == "timeout":
                raise IntegrityError("Timeout is not completed")
            setup = verified(STUDY / "ledger/settlements" / f"{r['session_id']}.json")
            attempt = verified(STUDY / "ledger/reservations" / f"{r['attempt_id']}.json")
            if (setup["status"] != "loaded" or attempt["job_id"] != job.id
                    or attempt["session_id"] != r["session_id"] or attempt["solver"] != solver):
                raise IntegrityError("Completed result ledger links changed")
            receipt_path = STUDY / "ledger/settlements" / f"{r['attempt_id']}.json"
            if receipt_path.exists():
                receipt = verified(receipt_path)
                if receipt["status"] != "completed" or receipt["record_sha256"] != digest(r):
                    raise IntegrityError("Completed result settlement differs")
            # Missing final receipt retains its full reservation; never releases it.
            rows.append(r)
        grouped[solver] = rows
    if any(path not in expected_paths for path in (STUDY / "results").rglob("*.json")):
        raise IntegrityError("Unknown completed result file")
    return grouped


def collection_status(protocol):
    tally = usage(protocol)
    grouped = completed_records(protocol)
    count = sum(map(len, grouped.values()))
    return tally | {"completed": count, "expected": SPEC["responses"],
        "by_solver": {s: len(rows) for s, rows in grouped.items()},
        "analysis": "eligible" if count == SPEC["responses"] else "locked"}


def invocation_records(protocol):
    pin = digest(protocol)
    rows = []
    for path in (STUDY / "invocations").glob("*.json"):
        r = verified(path)
        if (r["id"] != path.stem or r["protocol_sha256"] != pin or r["solver"] not in SOLVERS
                or not finite_number(r["reserved_at"]) or r["reserved_at"] < protocol["prepared_at"]):
            raise IntegrityError("Invalid invocation journal")
        rows.append(r)
    if any(sum(r["solver"] == solver for r in rows) > SPEC["invocations_per_solver"] for solver in SOLVERS):
        raise IntegrityError("Invocation ceiling exceeded")
    return rows


def reserve_invocation(protocol, solver):
    if (STUDY / "collection-end.json").exists():
        raise IntegrityError("Collection is closed to further invocations")
    rows = invocation_records(protocol)
    if sum(r["solver"] == solver for r in rows) >= SPEC["invocations_per_solver"]:
        raise BudgetExhausted("Solver invocation ceiling exhausted")
    tally = usage(protocol)
    if tally["budget_seconds"] >= SPEC["global_seconds"] or tally["charged_tokens"] >= SPEC["global_tokens"]:
        raise BudgetExhausted("Shared limits exhausted")
    key = uuid.uuid4().hex
    reserved_at = time.time()
    if not (STUDY / "collection-start.json").exists():
        write_once(STUDY / "collection-start.json", {"started_at": reserved_at, "protocol_sha256": digest(protocol)})
    write_once(STUDY / "invocations" / f"{key}.json", {"id": key, "solver": solver,
        "protocol_sha256": digest(protocol), "reserved_at": reserved_at})
    return key


def collect_core(protocol, solver, invocation_id, *, factory=TransformersBackend):
    """Called with the single collection writer lock; no scoring/reference access."""
    pin = digest(protocol)
    invocation = verified(STUDY / "invocations" / f"{invocation_id}.json")
    if invocation["solver"] != solver or invocation["protocol_sha256"] != pin:
        raise IntegrityError("Collector invocation was not reserved")
    write_once(STUDY / "invocation-starts" / f"{invocation_id}.json", {
        "invocation_id": invocation_id, "pid": os.getpid(), "started_at": time.time()})
    arm = protocol["arms"][solver]
    existing = {r["job"]["id"] for r in completed_records(protocol)[solver]}
    pending = [GenerationJob(**j) for j in arm["jobs"] if j["id"] not in existing]
    if not pending:
        raise IntegrityError("Completed solver cannot be relaunched")
    setup_begin = time.monotonic()
    session = reserve(protocol, solver, invocation_id, "setup")
    write_once(STUDY / "invocation-ready" / f"{invocation_id}.json", {
        "invocation_id": invocation_id, "session_id": session["id"], "ready_at": time.time()})
    try:
        config = from_dict(arm["config"])
        for path, sha in arm["asset_file_sha256"].items():
            if file_hash(path) != sha:
                raise IntegrityError("Frozen solver assets changed before setup")
        engine = factory(config)
        if engine.metadata != arm["backend_metadata"]:
            raise IntegrityError("Resolved backend changed after freeze")
        engine.load()
        if hasattr(engine, "_sync"):
            engine._sync()
        if time.monotonic() - setup_begin > session["reserved_seconds"]:
            raise BudgetExhausted("Model setup exceeded reserved time")
    except BaseException:
        settle(session, "failed", setup_begin, tokens=0)
        raise
    receipt = settle(session, "loaded", setup_begin, tokens=0)
    if receipt["elapsed_seconds"] > session["reserved_seconds"]:
        raise BudgetExhausted("Model setup exceeded reserved time")
    questions = {r["child_question"]["id"]: Question(**r["child_question"]) for r in protocol["selected"]}
    for job in pending:
        began = time.monotonic()
        attempt = reserve(protocol, solver, invocation_id, "job", job=job, session_id=session["id"])
        record = {"protocol_sha256": pin, "implementation_sha256": protocol["generation_implementation_sha256"],
            "solver": solver, "job": job.to_dict(), "status": "failed", "result": None,
            "attempt_id": attempt["id"], "session_id": session["id"]}
        tokens, error = None, None
        try:
            result = engine.generate(questions[job.question_id], job, began + attempt["reserved_seconds"])
            record["result"] = result.to_dict()
            tokens = validate_result(result, job)
            if result.termination == "timeout":
                raise RuntimeError("Generation deadline reached")
            if time.monotonic() - began > attempt["reserved_seconds"]:
                raise BudgetExhausted("Generation exceeded reserved time")
            record["status"] = "completed"
        except BaseException as exc:
            error = exc
            record["error"] = f"{type(exc).__name__}: {exc}"
        write_once(STUDY / "attempt-records" / f"{attempt['id']}.json", record)
        if record["status"] == "completed":
            write_once(STUDY / "results" / solver / f"{job.id}.json", record)
        settle(attempt, record["status"], began, tokens=tokens, record=record)
        progress = collection_status(protocol)
        atomic_json(STUDY / "status.json", progress | {"state": "collecting", "solver": solver})
        print(f"{solver} {progress['completed']}/512 {job.mode} draw={job.sample} {record['status']} charged={progress['charged_tokens']}", flush=True)
        if error is not None:
            raise error
    return collection_status(protocol)


def collector(solver, invocation_id):
    from scripts.macos_runtime_guard import user_activity
    with run_lock(STUDY / "collection"):
        p = read_protocol()
        invocation_records(p)
        try:
            with user_activity():
                result = collect_core(p, solver, invocation_id)
            write_once(STUDY / "invocation-finishes" / f"{invocation_id}.json", {"state": "complete", "progress": result})
            return 0
        except BaseException as exc:
            kind = "integrity" if isinstance(exc, (IntegrityError, ValueError)) else "budget" if isinstance(exc, BudgetExhausted) else "runtime"
            write_once(STUDY / "invocation-finishes" / f"{invocation_id}.json", {
                "state": "stopped", "failure_kind": kind, "reason": f"{type(exc).__name__}: {exc}"})
            print(f"Stopped {kind}: {type(exc).__name__}: {exc}", flush=True)
            return 1


def selected_gold(selected):
    """Only called by the full-endpoint score transaction, never by status."""
    from datasets import Dataset

    from reasoning_budget import scoring_v7
    child = child_plan.verify(BASE, ROOT)
    source = child["source"]
    answers = Dataset.from_file(source["arrow_path"]).select_columns(["answer"]).select(
        [r["upstream_index"] for r in selected])["answer"]
    gold = {}
    for row, answer in zip(selected, answers):
        if "####" not in answer:
            raise IntegrityError("Selected training reference lacks delimiter")
        value = answer.rsplit("####", 1)[1].strip()
        scoring_v7.v5.numeric(value)
        gold[row["child_question"]["id"]] = value
    return gold


def finalize():
    from scripts.opportunity_panel_analysis import (
        analyze_pairs,
        paired_rows,
        score_complete_endpoint,
    )
    with run_lock(STUDY / "collection"):
        p = read_protocol()
        tally = collection_status(p)
        if (tally["completed"] != 512 or tally["charged_tokens"] > SPEC["global_tokens"]
                or tally["budget_seconds"] > SPEC["global_seconds"]):
            raise IntegrityError("Full endpoint or global budget has not passed")
        grouped = completed_records(p)
        for invocation in invocation_records(p):
            finish = STUDY / "invocation-finishes" / f"{invocation['id']}.json"
            process = STUDY / "invocation-processes" / f"{invocation['id']}.json"
            if not process.exists():
                raise IntegrityError("Collector has not exited/reconciled")
            observation = verified(process)
            if type(observation["exit_code"]) is not int:
                raise IntegrityError("Collector launch/exit is unresolved")
            if observation["exit_code"] == 0 and (not finish.exists() or verified(finish)["state"] != "complete"):
                raise IntegrityError("Successful collector lacks terminal event")
        if not (STUDY / "collection-end.json").exists():
            write_once(STUDY / "collection-end.json", {"protocol_sha256": digest(p), "finished_at": time.time()})
        tally = collection_status(p)
        if tally["budget_seconds"] > SPEC["global_seconds"] or tally["charged_tokens"] > SPEC["global_tokens"]:
            raise IntegrityError("Global budget failed after collection close")
        scores_path = STUDY / "scores.numeric-v7.json"

        def guarded_gold(selected):
            write_once(STUDY / "score-started.json", {"protocol_sha256": digest(p), "started_at": time.time()})
            return selected_gold(selected)

        scores = score_complete_endpoint(grouped, p["selected"], guarded_gold,
            protocol_sha256=digest(p), output=scores_path)
        if (STUDY / "report.json").exists():
            report = verified(STUDY / "report.json")
            if report["protocol_sha256"] != digest(p) or report["scores_sha256"] != digest(scores):
                raise IntegrityError("Completed analysis identity changed")
            return report
        write_once(STUDY / "analysis-started.json", {"protocol_sha256": digest(p), "scores_sha256": digest(scores), "started_at": time.time()})
        rows = paired_rows(grouped, scores)
        statistics = analyze_pairs(rows, p["folds"], question_ids=[r["child_question"]["id"] for r in p["selected"]], spec=p["analysis"])
        from scripts.verify_phase2_repeat import verify
        preservation = verify(BASE / "repeat-panel-v1")
        report = {"protocol_sha256": digest(p), "scores_sha256": digest(scores),
            "statistics": statistics, "ledger": tally, "protected_originals_verified": preservation["protected_originals_verified"],
            "cloud_spend_usd": 0, "official_test_opened": False, "human_audit": "waived; automated/agent review only",
            "acquisition_or_rl_promotion": False, "more_data": "requires separately frozen prospective child/design; no automatic expansion"}
        write_once(STUDY / "report.json", report)
        return report


def native_environment():
    return dict(os.environ, PYTHONPATH=str(ROOT / "src"), HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", PYTHONUNBUFFERED="1",
        PYTORCH_ENABLE_MPS_FALLBACK="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def supervisor(launch_id):
    os.chdir(ROOT)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    handshake_deadline = time.monotonic() + 30
    while not (STUDY / "launch-ready" / f"{launch_id}.json").exists():
        if time.monotonic() > handshake_deadline:
            launch_path = STUDY / "supervisor-launches" / f"{launch_id}.json"
            if launch_path.exists():
                launch = verified(launch_path)
                terminal = {"state": "needs_attention", "failure_kind": "runtime",
                    "reason": "Supervisor launcher handshake expired", "launch_id": launch_id,
                    "pid": os.getpid(), "updated_at": time.time(), "protocol_sha256": launch["protocol_sha256"]}
                write_once(STUDY / "supervisor-finishes" / f"{launch_id}.json", terminal)
                atomic_json(STUDY / "background-status.json", terminal)
            raise TimeoutError("Supervisor launcher handshake expired")
        time.sleep(.1)
    with run_lock(STUDY / "supervisor"):
        p = read_protocol()
        launch = verified(STUDY / "supervisor-launches" / f"{launch_id}.json")
        if launch["protocol_sha256"] != digest(p):
            raise IntegrityError("Supervisor launch identity changed")
        write_once(STUDY / "supervisor-starts" / f"{launch_id}.json", {"pid": os.getpid(), "started_at": time.time()})
        began, child, invocation_id, reason, kind = time.monotonic(), None, None, None, None

        def update(state, **extras):
            try:
                progress = collection_status(p)
            except Exception as error:
                if state != "needs_attention":
                    raise
                progress = {"analysis": "locked", "integrity_error": f"{type(error).__name__}: {error}"}
            atomic_json(STUDY / "background-status.json", {"state": state, "updated_at": time.time(),
                "pid": os.getpid(), "launch_id": launch_id, "protocol_sha256": digest(p),
                "progress": progress, "cloud_spend_usd": 0, **extras})

        try:
            for solver in SOLVERS:
                if len(completed_records(p)[solver]) == len(p["arms"][solver]["jobs"]):
                    continue
                with run_lock(STUDY / "collection"):
                    invocation_id = reserve_invocation(p, solver)
                maximum_rss, rss_samples = 0, 0
                command = [sys.executable, "-m", "scripts.opportunity_panel_collect", "collector",
                    "--solver", solver, "--invocation-id", invocation_id]
                child_begin = time.monotonic()
                try:
                    with (STUDY / "logs" / f"{invocation_id}.log").open("x") as log:
                        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, env=native_environment())
                        while child.poll() is None:
                            if (not (STUDY / "invocation-ready" / f"{invocation_id}.json").exists()
                                    and time.monotonic() - child_begin > SPEC["setup_seconds"]):
                                raise RuntimeError("Collector startup watchdog reached")
                            if time.monotonic() - began > SPEC["supervisor_seconds"]:
                                raise BudgetExhausted("Supervisor wall ceiling reached")
                            if usage(p)["budget_seconds"] > SPEC["global_seconds"]:
                                raise BudgetExhausted("Global collection time ceiling reached")
                            active_path = STUDY / "active.json"
                            if active_path.exists():
                                active = verified(active_path)
                                if active.get("invocation_id") == invocation_id and active["kind"] != "idle":
                                    if time.time() - active["started_at"] > active["reserved_seconds"] + SPEC["watchdog_grace_seconds"]:
                                        raise RuntimeError("Active setup/job watchdog reached")
                            reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(child.pid)],
                                text=True, capture_output=True, timeout=5)
                            if reading.returncode == 0 and reading.stdout.strip():
                                maximum_rss = max(maximum_rss, int(reading.stdout.strip()) * 1024)
                                rss_samples += 1
                            elif child.poll() is None:
                                raise RuntimeError("Own collector RSS telemetry unavailable")
                            if maximum_rss > SPEC["maximum_polled_rss_bytes"]:
                                raise RuntimeError("Own collector sampled RSS ceiling reached")
                            update("collecting", solver=solver, child_pid=child.pid,
                                maximum_polled_rss_bytes=maximum_rss)
                            time.sleep(SPEC["poll_seconds"])
                finally:
                    if child is not None and child.poll() is None:
                        child.terminate()
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)
                    write_once(STUDY / "invocation-processes" / f"{invocation_id}.json", {
                        "pid": child.pid if child else None, "exit_code": child.returncode if child else None,
                        "wall_seconds": time.monotonic() - child_begin, "rss_samples": rss_samples,
                        "maximum_polled_rss_bytes": maximum_rss, "finished_at": time.time()})
                if child is None or child.returncode != 0:
                    finish_path = STUDY / "invocation-finishes" / f"{invocation_id}.json"
                    if finish_path.exists():
                        finish = verified(finish_path)
                        kind = finish.get("failure_kind", "runtime")
                        reason = finish.get("reason", "Collector stopped")
                    raise RuntimeError(reason or "Collector exited with error")
                child = None
                if not rss_samples:
                    raise RuntimeError("No valid collector RSS observations")
                if len(completed_records(p)[solver]) != len(p["arms"][solver]["jobs"]):
                    raise IntegrityError("Collector exited before its frozen endpoint")
            update("analyzing")
            # Keep collection and reference/analysis work in different processes.
            # This watchdog remains active if scoring or CPU analysis stalls.
            with (STUDY / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                child = subprocess.Popen([sys.executable, "-m", "scripts.opportunity_panel_collect", "finalize"],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=native_environment())
                try:
                    while child.poll() is None:
                        if time.monotonic() - began > SPEC["supervisor_seconds"]:
                            raise BudgetExhausted("Supervisor wall ceiling reached during finalization")
                        time.sleep(SPEC["poll_seconds"])
                finally:
                    if child.poll() is None:
                        child.terminate()
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)
                    write_once(STUDY / "finalize-processes" / f"{launch_id}.json", {
                        "pid": child.pid, "exit_code": child.returncode, "finished_at": time.time()})
            if child.returncode != 0:
                raise IntegrityError("Endpoint scoring/analysis process failed; preserved sidecars require review")
            child = None
            report = verified(STUDY / "report.json")
            update("complete", report_sha256=digest(report), acquisition_or_rl_promotion=False)
            write_once(STUDY / "supervisor-finishes" / f"{launch_id}.json", {"state": "complete", "report_sha256": digest(report)})
            return 0
        except BaseException as exc:
            kind = kind or ("integrity" if isinstance(exc, (IntegrityError, ValueError)) else "budget" if isinstance(exc, BudgetExhausted) else "runtime")
            reason = reason or f"{type(exc).__name__}: {exc}"
            # A killed child may have no final event; record the observed stop separately.
            update("needs_attention", failure_kind=kind, reason=reason, automatic_resume=False)
            write_once(STUDY / "supervisor-finishes" / f"{launch_id}.json", {"state": "needs_attention", "failure_kind": kind, "reason": reason})
            print(reason, flush=True)
            return 1


def launch(*, resume=False):
    os.chdir(ROOT)
    p = read_protocol()
    with run_lock(STUDY / "supervisor"), run_lock(STUDY / "collection"):
        if collection_status(p)["completed"] == 512:
            raise IntegrityError("Completed endpoint cannot be restarted")
        previous = list((STUDY / "supervisor-launches").glob("*.json"))
        if len(previous) >= SPEC["maximum_supervisor_launches"]:
            raise BudgetExhausted("Supervisor invocation ceiling exhausted")
        if previous:
            state = read_json(STUDY / "background-status.json")
            if not resume or state["state"] != "needs_attention" or state["failure_kind"] != "runtime":
                raise IntegrityError("Only an explicit bounded runtime resume is eligible")
        elif resume:
            raise IntegrityError("Initial launch cannot be a resume")
        child_plan.verify(BASE, ROOT)
        key = uuid.uuid4().hex
        write_once(STUDY / "supervisor-launches" / f"{key}.json", {
            "id": key, "protocol_sha256": digest(p), "reserved_at": time.time(), "resume": resume})
        (STUDY / "logs").mkdir(exist_ok=True)
        with (STUDY / "logs" / f"supervisor-{key}.log").open("x") as log:
            try:
                process = subprocess.Popen(["/usr/bin/caffeinate", "-i", sys.executable, "-m",
                    "scripts.opportunity_panel_collect", "supervisor", "--launch-id", key],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True, env=native_environment())
            except Exception as exc:
                terminal = {"state": "needs_attention", "failure_kind": "runtime",
                    "reason": f"Launch failed: {type(exc).__name__}: {exc}", "launch_id": key,
                    "updated_at": time.time(), "protocol_sha256": digest(p)}
                write_once(STUDY / "supervisor-finishes" / f"{key}.json", terminal)
                atomic_json(STUDY / "background-status.json", terminal)
                raise
        atomic_json(STUDY / "background-status.json", {"state": "launched", "pid": process.pid,
            "launch_id": key, "protocol_sha256": digest(p), "updated_at": time.time(), "cloud_spend_usd": 0})
    # Child waits for this marker before attempting the supervisor lock. Parent
    # has released both locks and has finished writing the initial status.
    write_once(STUDY / "launch-ready" / f"{key}.json", {"launch_id": key, "ready_at": time.time()})
    return {"pid": process.pid, "launch_id": key, "log": str(STUDY / "logs" / f"supervisor-{key}.log")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "status", "launch", "collector", "supervisor", "finalize"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--solver", choices=SOLVERS)
    parser.add_argument("--invocation-id")
    parser.add_argument("--launch-id")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "status":
        p = read_protocol()
        print(collection_status(p))
        if (STUDY / "background-status.json").exists():
            print(read_json(STUDY / "background-status.json"))
    elif args.command == "launch":
        print(launch(resume=args.resume))
    elif args.command == "collector":
        if args.solver is None or args.invocation_id is None:
            parser.error("Reserved solver and invocation are required")
        sys.exit(collector(args.solver, args.invocation_id))
    elif args.command == "supervisor":
        if args.launch_id is None:
            parser.error("Reserved launch ID required")
        sys.exit(supervisor(args.launch_id))
    else:
        print(finalize())


if __name__ == "__main__":
    main()
