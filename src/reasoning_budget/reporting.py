"""Scoring, whole-question bootstrap statistics, audit samples, and cost reports."""

import csv
import math
from pathlib import Path

import numpy as np

from .data import load_gold
from .runner import _usage, load_run
from .scoring import SCORING_VERSION, score_record
from .storage import atomic_json, digest, read_json


def scoring_digest():
    from . import scoring

    return digest(Path(scoring.__file__).read_text())


def scores_path(run_dir):
    """Keep a historical scorer's canonical cache; write new versions alongside it."""
    run_dir = Path(run_dir)
    canonical = run_dir / "scores.json"
    if not canonical.exists() or read_json(canonical).get("scoring_version") == SCORING_VERSION:
        return canonical
    return run_dir / f"scores.{SCORING_VERSION}.json"


def _check_scorer_identity(path):
    if path.exists():
        previous = read_json(path)
        if previous.get("scoring_version") != SCORING_VERSION or previous.get(
            "scoring_implementation_sha256"
        ) != scoring_digest():
            raise ValueError("Scorer identity changed; use a new scoring version")


def score_run(run_dir):
    run_dir = Path(run_dir)
    path = scores_path(run_dir)
    _check_scorer_identity(path)
    manifest, records = load_run(run_dir)
    gold = load_gold(manifest["identity"]["config"]["data_dir"])
    if "scoring_gold_sha256" in manifest and digest(gold) != manifest["scoring_gold_sha256"]:
        raise ValueError("Gold artifact differs from the generation run's frozen scoring reference")
    scores = [score_record(record, gold[record["job"]["question_id"]]) for record in records]
    artifact = {
        "scoring_version": SCORING_VERSION,
        "scoring_implementation_sha256": scoring_digest(),
        "run_id": manifest["run_id"],
        "gold_sha256": digest(gold),
        "records_sha256": digest(records),
        "scores": scores,
    }
    if not path.exists() or read_json(path) != artifact:
        atomic_json(path, artifact)
    return artifact


def report_path(run_dir):
    """Do not replace a report whose scorer provenance is older or unspecified."""
    run_dir = Path(run_dir)
    canonical = run_dir / "report"
    summary = canonical / "summary.json"
    if summary.exists():
        if read_json(summary).get("scoring_version") == SCORING_VERSION:
            return canonical
        return run_dir / f"report.{SCORING_VERSION}"
    if canonical.exists() and any(canonical.iterdir()):
        return run_dir / f"report.{SCORING_VERSION}"
    return canonical


def bootstrap(values, seed=20260909, draws=2000):
    """Rows are independent questions; repeated samples already averaged within rows."""
    values = np.asarray(values, dtype=float)
    if not len(values):
        return None
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def paired_statistics(records, scores, samples, seed):
    by_id = {score["job_id"]: score for score in scores}
    grouped = {}
    for record in records:
        job = record["job"]
        if record["status"] == "completed":
            grouped.setdefault(job["question_id"], {}).setdefault(job["mode"], []).append(
                float(by_id[job["id"]]["correct"])
            )
    pairs = [
        values
        for values in grouped.values()
        if all(len(values.get(mode, [])) == samples for mode in ["direct", "thinking"])
    ]
    difference = [np.mean(values["thinking"]) - np.mean(values["direct"]) for values in pairs]
    return {
        "questions": len(pairs),
        "thinking_minus_direct_accuracy": float(np.mean(difference)) if difference else None,
        "ci95": bootstrap(difference, seed),
        "bootstrap_unit": "whole question",
        "bootstrap_draws": 2000,
        "bootstrap_seed": seed,
    }


def create_audit(run_dir, count=50):
    run_dir = Path(run_dir)
    manifest, records = load_run(run_dir)
    scores = {s["job_id"]: s for s in score_run(run_dir)["scores"]}
    config = manifest["identity"]["config"]
    gold = load_gold(config["data_dir"])
    questions = {q["id"]: q for q in manifest["identity"]["questions"]}
    complete = [r for r in records if r["status"] == "completed"]
    # Stable sampling order; include modes evenly, then fill remaining slots.
    ordered = sorted(
        complete, key=lambda r: digest({"seed": config["seed"], "job": r["job"]["id"]})
    )
    selected = []
    modes = config["modes"]
    for mode in modes:
        selected += [r for r in ordered if r["job"]["mode"] == mode][: count // len(modes)]
    selected_ids = {r["job"]["id"] for r in selected}
    selected += [r for r in ordered if r["job"]["id"] not in selected_ids][
        : max(0, count - len(selected))
    ]
    rows = []
    for record in selected:
        job, result = record["job"], record["result"]
        rows.append(
            {
                "job_id": job["id"],
                "record_sha256": digest(record),
                "mode": job["mode"],
                "question": questions[job["question_id"]]["prompt"],
                "gold": gold[job["question_id"]],
                "reasoning": result["reasoning"],
                "final_answer": result["final_answer"],
                "termination": result["termination"],
                "score": scores[job["id"]],
                "review": "pending",
                "notes": "",
            }
        )
    audit = {
        "run_id": manifest["run_id"],
        "scoring_version": SCORING_VERSION,
        "reviewer": "",
        "rows": rows,
    }
    path = run_dir / "audit.json"
    if path.exists():
        raise ValueError(f"Audit already exists; edit it in place: {path}")
    atomic_json(path, audit)
    return path


def audit_status(run_dir, manifest, records, scores):
    path = Path(run_dir) / "audit.json"
    if not path.exists():
        return {"verified_reviews": 0, "accepted": False, "scorer_defects": 0}
    audit = read_json(path)
    current = {r["job"]["id"]: r for r in records if r["status"] == "completed"}
    score_map = {s["job_id"]: s for s in scores}
    valid, defects, seen = 0, 0, set()
    if (
        audit.get("run_id") != manifest["run_id"]
        or audit.get("scoring_version") != SCORING_VERSION
        or not audit.get("reviewer", "").strip()
    ):
        return {"verified_reviews": 0, "accepted": False, "scorer_defects": 0}
    for row in audit["rows"]:
        job_id = row["job_id"]
        if job_id in seen or job_id not in current:
            continue
        seen.add(job_id)
        if (
            row.get("record_sha256") != digest(current[job_id])
            or row.get("score") != score_map[job_id]
        ):
            continue
        if (
            row.get("review") in {"correct_score", "model_failure", "scorer_defect"}
            and row.get("notes", "").strip()
        ):
            valid += 1
            defects += row["review"] == "scorer_defect"
    return {
        "verified_reviews": valid,
        "accepted": valid >= 50 and defects == 0,
        "scorer_defects": defects,
    }


def report(run_dir, hourly_rate=None, projection_questions=1100, projection_samples=2):
    if hourly_rate is not None and (not math.isfinite(hourly_rate) or hourly_rate < 0):
        raise ValueError("hourly rate must be a finite nonnegative number")
    if projection_questions <= 0 or projection_samples <= 0:
        raise ValueError("projection questions and samples must be positive")
    run_dir = Path(run_dir)
    manifest, records = load_run(run_dir)
    score_artifact = score_run(run_dir)
    scores = score_artifact["scores"]
    score_map = {s["job_id"]: s for s in scores}
    config = manifest["identity"]["config"]
    summaries = []
    for mode in config["modes"]:
        planned = [r for r in records if r["job"]["mode"] == mode]
        complete = [r for r in planned if r["status"] == "completed"]
        results = [r["result"] for r in complete]
        mode_scores = [score_map[r["job"]["id"]] for r in complete]
        groups = {}
        for r, score in zip(complete, mode_scores):
            groups.setdefault(r["job"]["question_id"], []).append(float(score["correct"]))
        question_means = [
            np.mean(values) for values in groups.values() if len(values) == config["samples"]
        ]
        count = len(complete)
        summary = {
            "mode": mode,
            "planned": len(planned),
            "completed": count,
            "failed": sum(r["status"] == "failed" for r in planned),
            "pending": sum(r["status"] == "pending" for r in planned),
            "accuracy_completed": sum(s["correct"] for s in mode_scores) / count if count else None,
            "accuracy_ci95_complete_questions": bootstrap(question_means, config["seed"]),
            "parse_failures": sum(s["parser_status"] != "ok" for s in mode_scores),
            "forced_closure": sum(r["forced_closure"] for r in results),
            "answer_truncation": sum(r["answer_truncated"] for r in results),
        }
        for field in [
            "prompt_tokens",
            "reasoning_tokens",
            "answer_tokens",
            "inserted_tokens",
            "elapsed_seconds",
            "reasoning_seconds",
            "answer_seconds",
            "closure_seconds",
        ]:
            summary[field] = sum(r[field] for r in results)
            summary[f"mean_{field}"] = summary[field] / count if count else None
        summary["mean_generated_tokens"] = (
            (summary["reasoning_tokens"] + summary["answer_tokens"]) / count if count else None
        )
        summaries.append(summary)
    paired = paired_statistics(records, scores, config["samples"], config["seed"])
    tokens_charged, elapsed = _usage(run_dir)
    rates_available = all(s["completed"] for s in summaries)
    seconds_per_question = (
        sum(s["mean_elapsed_seconds"] or 0 for s in summaries) * projection_samples
    )
    projected_hours = (
        seconds_per_question * projection_questions / 3600 if rates_available else None
    )
    projection = {
        "questions": projection_questions,
        "samples_per_mode": projection_samples,
        "modes": config["modes"],
        "hours_at_observed_local_speed": projected_hours,
        "scenario_hourly_rate_usd": hourly_rate,
        "scenario_cost_usd": projected_hours * hourly_rate
        if hourly_rate is not None and projected_hours is not None
        else None,
        "scope": "inference only; excludes acquisition repeats, setup, idle time and confirmation",
        "cloud_warning": "Local MPS throughput is not a CUDA throughput measurement. Rate is user-supplied, not a vendor quote.",
    }
    audit = audit_status(run_dir, manifest, records, scores)
    billing_path = run_dir / "billing.json"
    actual_billing = None
    if billing_path.exists():
        billing = read_json(billing_path)
        actual_billing = billing.get("actual_cloud_billing_usd")
        if (
            billing.get("currency") != "USD"
            or isinstance(actual_billing, bool)
            or not isinstance(actual_billing, (float, int))
            or not math.isfinite(actual_billing)
            or actual_billing < 0
        ):
            raise ValueError(
                "billing.json requires currency=USD and nonnegative actual_cloud_billing_usd"
            )
    complete = all(r["status"] == "completed" for r in records)
    accepted = (
        complete
        and audit["accepted"]
        and config["backend"] != "fake"
        and config["split"] == "pilot"
        and len(manifest["identity"]["questions"]) == 100
        and config["samples"] == 2
        and set(config["modes"]) == {"direct", "thinking"}
    )
    result = {
        "run_id": manifest["run_id"],
        "scoring_version": SCORING_VERSION,
        "scoring_implementation_sha256": scoring_digest(),
        "backend": config["backend"],
        "split": config["split"],
        "complete": complete,
        "pilot_report_accepted": accepted,
        "audit": audit,
        "modes": summaries,
        "paired": paired,
        "projection": projection,
        "charged_tokens_all_attempts": tokens_charged,
        "elapsed_seconds_all_attempts_and_setup": elapsed,
        "budget_plan": "data-efficiency-roadmap-2026-10-01",
        "budgets_usd": {
            "foundation": 10,
            "signal": 15,
            "main": 30,
            "replication_and_confirmation": 30,
            "extensions_and_buffer": 15,
        },
        "actual_cloud_billing_usd": actual_billing,
    }
    out = report_path(run_dir)
    _check_scorer_identity(out / "summary.json")
    out.mkdir(exist_ok=True)
    atomic_json(out / "summary.json", result)
    with (out / "modes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    lines = [
        f"# {config['name']}",
        "",
        f"Run `{manifest['run_id']}`; backend **{config['backend']}**.",
        "",
        f"Generation complete: {complete}. Pilot report accepted after audit: {accepted}.",
        "",
        "| Mode | Complete / planned | Accuracy | Parse failures | Forced closure | Truncated | Mean generated tokens | Mean seconds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        accuracy = f"{s['accuracy_completed']:.1%}" if s["completed"] else "n/a"
        lines.append(
            f"| {s['mode']} | {s['completed']} / {s['planned']} | {accuracy} | {s['parse_failures']} | "
            f"{s['forced_closure']} | {s['answer_truncation']} | {s['mean_generated_tokens'] or 0:.1f} | {s['mean_elapsed_seconds'] or 0:.2f} |"
        )
    lines += [
        "",
        "Accuracy uses completed jobs, counting parse failures as incorrect. Pending/failed jobs are shown in JSON/CSV; partial runs are provisional.",
        "",
        f"These accuracies measure the configured {config['answer_tokens']}-token answer allowance. "
        "Answer truncation can materially affect the comparison; they do not establish unconstrained reasoning accuracy. "
        "Audit acceptance means the saved records and scoring were reviewed, not that the protocol or dataset is free of limitations.",
        "",
        f"Paired comparison: {paired['questions']} complete questions; thinking minus direct accuracy = {paired['thinking_minus_direct_accuracy']}; 95% interval = {paired['ci95']}. Bootstrap resamples whole questions, retaining repeated samples.",
        "",
        f"All attempts and setup: {elapsed / 3600:.3f} hours; {tokens_charged:,} charged tokens (includes conservative interrupted reservations).",
        "",
        f"Manual audit: {audit['verified_reviews']} verified reviews; {audit['scorer_defects']} scorer defects. At least 50 reviews with no unresolved scorer defects are required for pilot acceptance.",
        "",
        f"Projection: {projection_questions} questions × {projection_samples} samples × {len(config['modes'])} modes.",
    ]
    if projected_hours is not None:
        lines += [f"Estimated inference time at observed speed: {projected_hours:.2f} hours."]
    if hourly_rate is not None and projected_hours is not None:
        lines += [
            f"At the supplied hypothetical ${hourly_rate:.3f}/hour: ${projected_hours * hourly_rate:.2f}."
        ]
    else:
        lines += [
            "No cloud hourly rate supplied; dollar estimate is unavailable. Use `--hourly-rate` for an explicit scenario."
        ]
    if actual_billing is not None:
        lines += [
            f"Actual cloud billing recorded separately in `billing.json`: ${actual_billing:.2f}."
        ]
    lines += [
        projection["scope"] + ". " + projection["cloud_warning"],
        "",
        "Active roadmap cloud ceiling: $10 foundation, $15 signal, $30 main, $30 shared replication and confirmation, $15 conditional extensions and buffer ($100 total). No cloud instance is launched by this package. Actual billing must be tracked separately; limits cannot stop idle rental charges.",
        "",
        "Reasoning and answer token counts include generated control/EOS tokens. Inserted closure tokens are separate. The answer stage reprocesses the same assistant prefix; its timing includes that overhead, including forced closure. Raw output excludes inserted tokens; effective output and token IDs retain reconstruction details.",
    ]
    if config["backend"] == "fake":
        lines += [
            "",
            "SYNTHETIC PIPELINE CHECK: fake outputs and timings cannot support model or cost conclusions.",
        ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    _plot(out, summaries, config["backend"])
    return out


def _plot(out, summaries, backend):
    import os

    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    os.environ.setdefault("XDG_CACHE_HOME", str(Path(".cache").resolve()))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), constrained_layout=True)
    colors = ["#246A9F", "#D47A2A"][: len(summaries)]
    for ax, field, title in zip(
        axes,
        ["accuracy_completed", "mean_generated_tokens", "mean_elapsed_seconds"],
        ["Accuracy", "Generated tokens / response", "Seconds / response"],
    ):
        ax.bar(
            [f"{s['mode']}\nn={s['completed']}/{s['planned']}" for s in summaries],
            [s[field] or 0 for s in summaries],
            color=colors,
        )
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
        if field == "accuracy_completed":
            ax.set_ylim(0, 1)
    suffix = " — SYNTHETIC" if backend == "fake" else ""
    if any(s["completed"] != s["planned"] for s in summaries):
        suffix += " — PARTIAL"
    fig.suptitle("Direct vs thinking" + suffix)
    fig.savefig(out / "comparison.png", dpi=180)
    fig.savefig(out / "comparison.pdf")
    plt.close(fig)
