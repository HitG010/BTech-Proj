"""Standalone worker: selected PYTHONPATH determines the frozen generation arm.

Invoked by research_bridge in a fresh process; never scores or opens gold.
"""

import argparse
import hashlib
import time
from pathlib import Path


def inspect(config_path):
    from reasoning_budget import backend, runner
    from reasoning_budget.config import load_config
    from reasoning_budget.data import load_questions
    from reasoning_budget.storage import digest

    config = load_config(config_path)
    questions = load_questions(config.data_dir, config.split)
    engine = backend.make_backend(config)  # Tokenizer/config only; no weight loading.
    env = backend.environment()
    implementation = runner.implementation_digest()
    if hasattr(runner, "build_run_identity"):
        identity = runner.build_run_identity(config, questions, engine.metadata, env)
    else:
        identity = {
            "config": config.to_dict(),
            "backend": engine.metadata,
            "questions": [q.to_dict() for q in questions],
            "environment": env,
            "implementation_sha256": implementation,
        }
    jobs = runner.build_jobs(config, questions, engine.metadata)
    snapshot = {
        "config": config.to_dict(),
        "identity": identity,
        "run_dir": str(Path(config.output_dir) / digest(identity)[:20]),
        "generation_implementation": implementation,
        "package_root": str(Path(backend.__file__).parent.resolve()),
        "jobs": [job.to_dict() for job in jobs],
        "planned_max_tokens": sum(job.max_tokens for job in jobs),
    }
    return snapshot, config, engine


def collect(study, arm, progress=print):
    from reasoning_budget import runner
    from reasoning_budget.storage import atomic_json, digest, envelope, verified

    study = Path(study)
    protocol = verified(study / "protocol.json")
    expected = protocol["arms"][arm]
    worker_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if worker_hash != protocol["worker_sha256"]:
        raise ValueError("Frozen bridge worker changed")
    actual, config, engine = inspect(expected["config_path"])
    if actual != expected["snapshot"]:
        raise ValueError("Frozen arm configuration, source, backend or environment changed")
    if hashlib.sha256(Path(expected["config_path"]).read_bytes()).hexdigest() != expected[
        "config_sha256"
    ]:
        raise ValueError("Frozen arm YAML changed")
    dataset = Path(config.data_dir)
    for name, value in protocol["dataset_file_sha256"].items():
        if hashlib.sha256((dataset / name).read_bytes()).hexdigest() != value:
            raise ValueError("Frozen bridge data changed")
    started = time.monotonic()
    path = runner.run(config, backend=engine, progress=progress)
    if str(path) != actual["run_dir"]:
        raise ValueError("Run identity changed between preflight and collection")
    manifest, records = runner.load_run(path)
    code = manifest.get("implementation_sha256", manifest["identity"].get("implementation_sha256"))
    if code != actual["generation_implementation"] or any(
        record["status"] != "pending"
        and record.get("implementation_sha256", code) != code
        for record in records
    ):
        raise ValueError("Bridge arm contains mixed source implementations")
    tokens, elapsed = runner._usage(path)
    payload = {
        "arm": arm,
        "protocol_sha256": digest(protocol),
        "run_dir": str(path),
        "completed": sum(record["status"] == "completed" for record in records),
        "expected": len(records),
        "charged_tokens_all_attempts": tokens,
        "elapsed_seconds_all_attempts_and_setup": elapsed,
        "worker_invocation_seconds": time.monotonic() - started,
        "records_sha256": digest(records),
        "finished_at": time.time(),
        "gold_opened": False,
    }
    atomic_json(study / f"{arm}-completion.json", envelope(payload))
    return payload


def main():
    from reasoning_budget.storage import atomic_json, envelope

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    metadata = sub.add_parser("inspect")
    metadata.add_argument("--config", required=True)
    metadata.add_argument("--output", required=True)
    run = sub.add_parser("run")
    run.add_argument("--study", required=True)
    run.add_argument("--arm", choices=["legacy", "v3"], required=True)
    args = parser.parse_args()
    if args.command == "inspect":
        snapshot, _, _ = inspect(args.config)
        atomic_json(args.output, envelope(snapshot))
        print(f"Resolved {len(snapshot['jobs'])} jobs; weights not loaded.", flush=True)
    else:
        result = collect(args.study, args.arm, lambda message: print(message, flush=True))
        print(f"{args.arm}: {result['completed']}/{result['expected']}", flush=True)


if __name__ == "__main__":
    main()
