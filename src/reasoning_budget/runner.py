"""Atomic, bounded, single-writer, resumable generation experiments."""

import math
import time
from pathlib import Path

from .backend import environment, make_backend
from .data import load_questions
from .records import GenerationJob, GenerationResult
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified


def implementation_digest():
    root = Path(__file__).parent
    return digest(
        {
            name: (root / name).read_text()
            for name in ["backend.py", "config.py", "records.py", "runner.py", "storage.py"]
        }
    )


def build_jobs(config, questions, backend_metadata):
    jobs = []
    for question in questions:
        for sample in range(config.samples):
            for mode in config.modes:
                identity = {
                    "question": question.to_dict(),
                    "backend": backend_metadata,
                    "config": config.to_dict(),
                    "mode": mode,
                    "sample": sample,
                }
                seed = int(
                    digest(
                        {
                            "seed": config.seed,
                            "question": question.to_dict(),
                            "mode": mode,
                            "sample": sample,
                        }
                    )[:8],
                    16,
                )
                identity["generation_seed"] = seed
                limit = config.answer_tokens + (
                    config.reasoning_tokens + backend_metadata["closure_tokens"]
                    if mode == "thinking"
                    else 0
                )
                jobs.append(
                    GenerationJob(
                        digest(identity), question.id, mode, sample, seed, limit, identity
                    )
                )
    return jobs


def valid_record_result(result, job):
    counts = [result.reasoning_tokens, result.answer_tokens, result.inserted_tokens]
    config = job.identity["config"]
    return (
        all(type(n) is int and n >= 0 for n in counts)
        and sum(counts) <= job.max_tokens
        and result.answer_tokens <= config["answer_tokens"]
        and result.reasoning_tokens <= (config["reasoning_tokens"] if job.mode == "thinking" else 0)
        and result.inserted_tokens
        <= (job.identity["backend"]["closure_tokens"] if job.mode == "thinking" else 0)
        and math.isfinite(result.elapsed_seconds)
        and result.elapsed_seconds >= 0
    )


def valid_record(path, job):
    try:
        record = verified(path)
        if record["job"] != job.to_dict() or record["status"] not in {"completed", "failed"}:
            return None
        if record["status"] == "completed":
            result = GenerationResult(**record["result"])
            if not valid_record_result(result, job):
                return None
            if result.termination == "timeout":
                return None
        return record
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _usage(run_dir):
    tokens, elapsed = 0, 0.0
    for path in (run_dir / "attempts").glob("*.json"):
        # A corrupt budget ledger is a hard error, never permission to spend again.
        attempt = verified(path)
        tokens += attempt.get("charged_tokens", attempt["reserved_tokens"])
        elapsed += attempt.get("elapsed_seconds", attempt["reserved_seconds"])
    for path in (run_dir / "sessions").glob("*.json"):
        elapsed += verified(path)["setup_seconds"]
    return tokens, elapsed


def run(config, backend=None, progress=print):
    setup_started = time.monotonic()
    config.validate()
    questions = load_questions(config.data_dir, config.split)  # Never opens gold.json.
    env = environment()
    backend = backend or make_backend(config)
    jobs = build_jobs(config, questions, backend.metadata)
    identity = {
        "config": config.to_dict(),
        "backend": backend.metadata,
        "questions": [q.to_dict() for q in questions],
        "environment": env,
        "implementation_sha256": implementation_digest(),
    }
    run_id = digest(identity)
    run_dir = Path(config.output_dir) / run_id[:20]
    with run_lock(run_dir):
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            manifest = verified(manifest_path)
            if manifest["identity"] != identity:
                raise ValueError("Run identity collision or corrupted manifest")
        else:
            dataset_manifest = read_json(Path(config.data_dir) / "manifest.json")
            manifest = {
                "schema_version": 1,
                "run_id": run_id,
                "identity": identity,
                "scoring_gold_sha256": dataset_manifest["gold_sha256"],
                "jobs": [j.to_dict() for j in jobs],
                "created_at": time.time(),
            }
            atomic_json(manifest_path, envelope(manifest))
            atomic_json(run_dir / "resolved_config.json", config.to_dict())
            atomic_json(run_dir / "environment.json", env)
            atomic_json(run_dir / "questions.json", [q.to_dict() for q in questions])
        pending = [
            j
            for j in jobs
            if not (
                (r := valid_record(run_dir / "results" / f"{j.id}.json", j))
                and r["status"] == "completed"
            )
        ]
        progress(
            f"Run: {run_dir} | verified {len(jobs) - len(pending)}/{len(jobs)} | pending {len(pending)}"
        )
        if not pending:
            return run_dir
        charged, elapsed = _usage(run_dir)
        if (
            charged + pending[0].max_tokens > config.limits.max_tokens
            or elapsed >= config.limits.max_elapsed_seconds
        ):
            progress("Stopped: cumulative budget cannot reserve the next job.")
            return run_dir
        try:
            backend.load()
        except BaseException as exc:
            atomic_json(
                run_dir / "sessions" / f"{time.time_ns()}.json",
                envelope(
                    {
                        "setup_seconds": time.monotonic() - setup_started,
                        "error": f"{type(exc).__name__}: {exc}",
                        "started_at": time.time(),
                    }
                ),
            )
            raise
        session = {"setup_seconds": time.monotonic() - setup_started, "started_at": time.time()}
        atomic_json(run_dir / "sessions" / f"{time.time_ns()}.json", envelope(session))
        by_id = {q.id: q for q in questions}
        stop_reason = "complete"
        for job in pending:
            charged, elapsed = _usage(run_dir)
            remaining_seconds = config.limits.max_elapsed_seconds - elapsed
            if charged + job.max_tokens > config.limits.max_tokens:
                stop_reason = "token_budget"
                break
            if remaining_seconds <= 0:
                stop_reason = "elapsed_budget"
                break
            attempt_id = f"{job.id}-{time.time_ns()}"
            attempt_path = run_dir / "attempts" / f"{attempt_id}.json"
            seconds = min(config.limits.job_seconds, remaining_seconds)
            attempt = {
                "job_id": job.id,
                "attempt_id": attempt_id,
                "status": "started",
                "reserved_tokens": job.max_tokens,
                "reserved_seconds": seconds,
                "started_at": time.time(),
            }
            atomic_json(attempt_path, envelope(attempt))
            started = time.monotonic()
            record = {
                "job": job.to_dict(),
                "attempt_id": attempt_id,
                "status": "failed",
                "result": None,
            }
            interrupted = False
            try:
                result = backend.generate(by_id[job.question_id], job, started + seconds)
                record["result"] = result.to_dict()
                total_tokens = (
                    result.reasoning_tokens + result.answer_tokens + result.inserted_tokens
                )
                if total_tokens > job.max_tokens:
                    raise ValueError("Backend exceeded reserved tokens")
                if not valid_record_result(result, job):
                    raise ValueError("Backend returned invalid token accounting")
                record["status"] = "failed" if result.termination == "timeout" else "completed"
                attempt["charged_tokens"] = total_tokens
            except KeyboardInterrupt:
                record["error"] = (
                    "KeyboardInterrupt: interrupted; reservation retained conservatively"
                )
                interrupted = True
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                attempt.update(status=record["status"], elapsed_seconds=time.monotonic() - started)
                # Write the result before releasing the conservative reservation.
                atomic_json(run_dir / "results" / f"{job.id}.json", envelope(record))
                atomic_json(attempt_path, envelope(attempt | {"record": record}))
            result = record["result"]
            progress(
                f"{job.question_id} {job.mode} sample={job.sample} {record['status']} "
                + (
                    f"tokens={result['reasoning_tokens'] + result['answer_tokens']} "
                    f"time={result['elapsed_seconds']:.1f}s termination={result['termination']}"
                    if result
                    else record.get("error", "")
                )
            )
            if interrupted:
                stop_reason = "interrupted"
                break
            if record["status"] == "failed":
                # Avoid burning an entire run on a broken device; explicit resume retries.
                stop_reason = "failed_job"
                break
        charged, elapsed = _usage(run_dir)
        completed = sum(
            bool(
                (r := valid_record(run_dir / "results" / f"{j.id}.json", j))
                and r["status"] == "completed"
            )
            for j in jobs
        )
        atomic_json(
            run_dir / "status.json",
            {
                "completed": completed,
                "expected": len(jobs),
                "charged_tokens": charged,
                "elapsed_seconds": elapsed,
                "stop_reason": stop_reason,
            },
        )
        progress(f"Saved {completed}/{len(jobs)}; stop={stop_reason}; charged_tokens={charged}")
    return run_dir


def load_run(run_dir):
    run_dir = Path(run_dir)
    manifest = verified(run_dir / "manifest.json")
    records = []
    for row in manifest["jobs"]:
        job = GenerationJob(**row)
        record = valid_record(run_dir / "results" / f"{job.id}.json", job)
        records.append(record or {"job": row, "status": "pending", "result": None})
    return manifest, records
