"""Frozen, outcome-independent answer-cap calibration over an existing pilot."""

from pathlib import Path

import numpy as np
import yaml

from .config import from_dict
from .data import load_gold, save_dataset
from .records import Question
from .reporting import bootstrap, create_audit, paired_statistics, report
from .runner import (
    _usage,
    build_run_identity,
    implementation_digest,
    load_run,
    manifest_implementation,
    require_implementation,
    run,
)
from .scoring import SCORING_VERSION, score_record
from .storage import atomic_json, digest, envelope, read_json, run_lock, verified


def select_questions(questions, count, seed):
    """Selection accepts questions only, never gold or generation outcomes."""
    if type(count) is not int or not 1 <= count <= len(questions):
        raise ValueError("count must be positive and no larger than the pilot pool")
    if type(seed) is not int or seed < 0:
        raise ValueError("selection seed must be a nonnegative integer")
    return sorted(
        questions,
        key=lambda q: (digest({"selection_seed": seed, "question": q.to_dict()}), q.id),
    )[:count]


def prepare(baseline, output, count=25, seed=20260914):
    baseline, output = Path(baseline).resolve(), Path(output).resolve()
    manifest = verified(baseline / "manifest.json")
    config = manifest["identity"]["config"]
    if (
        config["split"] != "pilot"
        or config["answer_tokens"] != 256
        or config["samples"] != 2
        or set(config["modes"]) != {"direct", "thinking"}
    ):
        raise ValueError("Calibration requires a 256-token pilot with two samples of both modes")
    questions = select_questions(
        [Question(**q) for q in manifest["identity"]["questions"]], count, seed
    )
    # Select first. Gold is copied only to the isolated scoring artifact.
    gold = load_gold(config["data_dir"])
    if digest(gold) != manifest["scoring_gold_sha256"]:
        raise ValueError("Baseline scoring reference changed")
    configs = {}
    closure = manifest["identity"]["backend"]["closure_tokens"]
    for cap in [512, 1024]:
        values = config | {
            "name": f"answer-cap-{cap}-calibration",
            "data_dir": str(output / "data"),
            "output_dir": str(Path(config["output_dir"]).resolve()),
            "answer_tokens": cap,
            "limits": {
                # Allow the full worst-case allocation plus 10% for explicit retries.
                "max_tokens": int(
                    count * 2 * (2 * cap + config["reasoning_tokens"] + closure) * 1.1
                ),
                "max_elapsed_seconds": 7200,
                "job_seconds": config["limits"]["job_seconds"],
            },
        }
        configs[str(cap)] = from_dict(values).to_dict()
    study = {
        "schema_version": 1,
        "baseline": str(baseline),
        "baseline_run_id": manifest["run_id"],
        "baseline_manifest_sha256": digest(manifest),
        "selection_seed": seed,
        "selection_algorithm": "sha256-question-identity-v1",
        "question_ids": [q.id for q in questions],
        "questions_sha256": digest([q.to_dict() for q in questions]),
        "caps": [256, 512, 1024],
        "configs": configs,
        "scoring": "Unchanged strict completion-aware scorer; no prefix-derived observations",
        "human_review": "Required before accepting the replacement full pilot",
    }
    with run_lock(output):
        path = output / "study.json"
        if path.exists() and verified(path) != study:
            raise ValueError("Calibration study already frozen with different content")
        save_dataset(
            output / "data",
            questions,
            {q.id: gold[q.id] for q in questions},
            {
                "parent_run_id": manifest["run_id"],
                "selection_seed": seed,
                "selection_algorithm": study["selection_algorithm"],
            },
        )
        for cap, values in configs.items():
            (output / f"answer-{cap}.yaml").write_text(yaml.safe_dump(values, sort_keys=False))
        atomic_json(path, envelope(study))
    return output


def _validate_arm(study, cap, manifest, baseline_manifest):
    if manifest["identity"]["config"] != study["configs"][str(cap)]:
        raise ValueError("Calibration arm configuration differs from its frozen study")
    if digest(manifest["identity"]["questions"]) != study["questions_sha256"]:
        raise ValueError("Calibration arm question content differs")
    for key in ["environment", "backend", "protocol_version"]:
        if manifest["identity"].get(key) != baseline_manifest["identity"].get(key):
            raise ValueError(f"Calibration comparison changed {key}; use a new matched baseline")
    if manifest_implementation(manifest) != manifest_implementation(baseline_manifest):
        raise ValueError(
            "Calibration comparison changed implementation; use a new matched baseline"
        )


def run_study(directory, progress=print):
    directory = Path(directory)
    with run_lock(directory):
        study = verified(directory / "study.json")
        baseline_manifest = verified(Path(study["baseline"]) / "manifest.json")
        if digest(baseline_manifest) != study["baseline_manifest_sha256"]:
            raise ValueError("Baseline manifest changed")
        state_path = directory / "runs.json"
        state = verified(state_path) if state_path.exists() else {}
        for cap in [512, 1024]:
            config = from_dict(study["configs"][str(cap)])
            # Check comparability BEFORE model weights or generation, including on resume.
            from .backend import environment, make_backend

            backend = make_backend(config)
            prospective = {
                "identity": build_run_identity(
                    config,
                    read_json(directory / "data/questions.json"),
                    backend.metadata,
                    environment(),
                ),
                "implementation_sha256": implementation_digest(),
            }
            _validate_arm(study, cap, prospective, baseline_manifest)
            path = Path(config.output_dir) / digest(prospective["identity"])[:20]
            previous = state.get(str(cap))
            if previous and Path(previous).resolve() != path.resolve():
                raise ValueError("Calibration run identity changed during resume")
            state[str(cap)] = str(path.resolve())
            atomic_json(state_path, envelope(state))
            actual_path = run(config, backend=backend, progress=progress)
            if actual_path.resolve() != path.resolve():
                raise ValueError("Run identity changed between preflight and generation")
            report_study(directory)
            complete = all(r["status"] == "completed" for r in load_run(path)[1])
            if not complete:
                progress("Calibration paused: resume this study to retry incomplete work.")
                return directory
            # Release the completed arm's model before loading the next one.
            del backend
            import gc

            gc.collect()
        return directory


def _headroom(records, scores, samples):
    by_id = {s["job_id"]: s for s in scores}
    grouped = {}
    costs = {}
    for r in records:
        if r["status"] == "completed":
            j = r["job"]
            grouped.setdefault(j["question_id"], {}).setdefault(j["mode"], []).append(
                float(by_id[j["id"]]["correct"])
            )
            costs.setdefault(j["question_id"], {}).setdefault(j["mode"], []).append(
                sum(
                    r["result"][k] for k in ["reasoning_tokens", "answer_tokens", "inserted_tokens"]
                )
            )
    selected_costs, all_thinking_costs, direct_choices = [], [], 0
    for question_id, values in grouped.items():
        if not all(len(values.get(mode, [])) == samples for mode in ["direct", "thinking"]):
            continue
        chosen = max(
            ["direct", "thinking"],
            key=lambda mode: (
                float(np.mean(values[mode])),
                -float(np.mean(costs[question_id][mode])),
            ),
        )
        selected_costs.append(float(np.mean(costs[question_id][chosen])))
        all_thinking_costs.append(float(np.mean(costs[question_id]["thinking"])))
        direct_choices += chosen == "direct"
    pairs = [
        v
        for v in grouped.values()
        if all(len(v.get(m, [])) == samples for m in ["direct", "thinking"])
    ]
    means = [(float(np.mean(v["direct"])), float(np.mean(v["thinking"]))) for v in pairs]
    return {
        "complete_questions": len(means),
        "retrospective_sample_estimated_oracle_accuracy": float(
            np.mean([max(d, t) for d, t in means])
        )
        if means
        else None,
        "thinking_better_questions": sum(t > d for d, t in means),
        "direct_better_questions": sum(d > t for d, t in means),
        "tied_questions": sum(d == t for d, t in means),
        "retrospective_direct_choices": direct_choices,
        "retrospective_mean_charged_tokens": float(np.mean(selected_costs))
        if selected_costs
        else None,
        "always_thinking_mean_charged_tokens": float(np.mean(all_thinking_costs))
        if all_thinking_costs
        else None,
        "tie_break": "Choose lower observed mean charged tokens among modes with equal observed accuracy",
        "caveat": "Uses observed labels and two samples per mode; not a deployable policy or population bound.",
    }


def report_study(directory):
    directory = Path(directory)
    study = verified(directory / "study.json")
    baseline_manifest, baseline_records = load_run(study["baseline"])
    require_implementation(
        baseline_manifest, baseline_records, manifest_implementation(baseline_manifest)
    )
    if digest(baseline_manifest) != study["baseline_manifest_sha256"]:
        raise ValueError("Baseline manifest changed")
    selected = set(study["question_ids"])
    baseline_records = [r for r in baseline_records if r["job"]["question_id"] in selected]
    gold = load_gold(directory / "data")
    parent_gold = load_gold(baseline_manifest["identity"]["config"]["data_dir"])
    if digest(parent_gold) != baseline_manifest["scoring_gold_sha256"]:
        raise ValueError("Baseline gold changed")
    if gold != {q: parent_gold[q] for q in selected}:
        raise ValueError("Calibration gold differs from baseline")
    state_path = directory / "runs.json"
    state = verified(state_path) if state_path.exists() else {}
    rows, arms, paired_cap = [], {}, []
    base_scores = {
        s["job_id"]: s
        for s in [score_record(r, gold[r["job"]["question_id"]]) for r in baseline_records]
    }
    base_map = {
        (r["job"]["question_id"], r["job"]["mode"], r["job"]["sample"]): r for r in baseline_records
    }
    for cap in study["caps"]:
        if cap == 256:
            manifest, records, path = baseline_manifest, baseline_records, study["baseline"]
        elif str(cap) in state:
            path = state[str(cap)]
            if not (Path(path) / "manifest.json").exists():
                continue  # Preflight journal exists before the generation manifest.
            manifest, records = load_run(path)
            _validate_arm(study, cap, manifest, baseline_manifest)
            require_implementation(manifest, records, manifest_implementation(baseline_manifest))
        else:
            continue
        if len(records) != len(selected) * 4:
            raise ValueError("Calibration arm does not contain exactly four jobs per question")
        for r in records:
            j = r["job"]
            base = base_map[(j["question_id"], j["mode"], j["sample"])]
            if j["seed"] != base["job"]["seed"]:
                raise ValueError("Generation seeds differ across answer caps")
        scores = [score_record(r, gold[r["job"]["question_id"]]) for r in records]
        score_map = {s["job_id"]: s for s in scores}
        arms[str(cap)] = {
            "run_id": manifest["run_id"],
            "path": str(path),
            "selected_records_sha256": digest(records),
            "complete": all(r["status"] == "completed" for r in records),
            "paired_modes": paired_statistics(records, scores, 2, study["selection_seed"]),
            "headroom": _headroom(records, scores, 2),
        }
        if cap != 256:
            tokens, seconds = _usage(Path(path))
            arms[str(cap)]["charged_tokens_all_attempts"] = tokens
            arms[str(cap)]["elapsed_seconds_including_setup"] = seconds
        for mode in ["direct", "thinking"]:
            completed = [
                r for r in records if r["status"] == "completed" and r["job"]["mode"] == mode
            ]
            count = len(completed)
            groups, differences = {}, {}
            for r in completed:
                j = r["job"]
                score = score_map[j["id"]]
                groups.setdefault(j["question_id"], []).append(float(score["correct"]))
                base = base_map[(j["question_id"], mode, j["sample"])]
                if base["status"] == "completed":
                    differences.setdefault(j["question_id"], []).append(
                        float(score["correct"]) - float(base_scores[base["job"]["id"]]["correct"])
                    )
            means = [np.mean(v) for v in groups.values() if len(v) == 2]
            delta = [np.mean(v) for v in differences.values() if len(v) == 2]
            rows.append(
                {
                    "answer_cap": cap,
                    "mode": mode,
                    "completed": count,
                    "planned": len(selected) * 2,
                    "accuracy": sum(score_map[r["job"]["id"]]["correct"] for r in completed) / count
                    if count
                    else None,
                    "accuracy_ci95": bootstrap(means, study["selection_seed"]),
                    "answer_truncation": sum(r["result"]["answer_truncated"] for r in completed),
                    "forced_closure": sum(r["result"]["forced_closure"] for r in completed),
                    "other_parse_failures": sum(
                        score_map[r["job"]["id"]]["parser_status"] != "ok"
                        and not r["result"]["answer_truncated"]
                        for r in completed
                    ),
                    "mean_generated_tokens": float(
                        np.mean(
                            [
                                r["result"]["reasoning_tokens"] + r["result"]["answer_tokens"]
                                for r in completed
                            ]
                        )
                    )
                    if count
                    else None,
                    "mean_elapsed_seconds": float(
                        np.mean([r["result"]["elapsed_seconds"] for r in completed])
                    )
                    if count
                    else None,
                }
            )
            paired_cap.append(
                {
                    "answer_cap": cap,
                    "mode": mode,
                    "complete_questions": len(delta),
                    "accuracy_minus_256": float(np.mean(delta)) if delta else None,
                    "ci95": bootstrap(delta, study["selection_seed"]),
                }
            )
    artifact = {
        "study_sha256": digest(study),
        "scoring_version": SCORING_VERSION,
        "backend": baseline_manifest["identity"]["config"]["backend"],
        "synthetic": baseline_manifest["identity"]["config"]["backend"] == "fake",
        "complete": len(arms) == 3 and all(a["complete"] for a in arms.values()),
        "question_count": len(selected),
        "modes": rows,
        "arms": arms,
        "paired_cap_comparisons": paired_cap,
        "bootstrap_unit": "whole question; two samples retained; intervals exploratory, no multiplicity adjustment",
        "human_review_status": "pending",
        "baseline_cost": "Reused subset of existing pilot; baseline timing excludes pilot setup",
        "measurement": "Actual independent capped generation calls with matched seeds; no token-prefix simulations",
    }
    out = directory / "report"
    atomic_json(out / "summary.json", artifact)
    lines = [
        "# Answer allowance calibration",
        "",
        f"Complete: {artifact['complete']}. Questions: {len(selected)}; two samples per mode.",
        "",
        "| Answer cap | Mode | Complete/planned | Accuracy | Truncated | Forced closure | Mean tokens | Mean seconds |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        acc = f"{row['accuracy']:.1%}" if row["completed"] else "n/a"
        lines.append(
            f"| {row['answer_cap']} | {row['mode']} | {row['completed']}/{row['planned']} | {acc} | {row['answer_truncation']} | {row['forced_closure']} | {row['mean_generated_tokens'] or 0:.1f} | {row['mean_elapsed_seconds'] or 0:.2f} |"
        )
    lines += [
        "",
        "Strict completion-aware scoring is unchanged. Partial runs are provisional.",
        "",
        "Selected original 256-token pilot responses are reused without modifying their artifacts.",
        "Actual longer-cap generations retain model, decoder, prompt, precision, backend, and seeds.",
        "",
        "Paired question-bootstrap intervals and observed routing headroom are in summary.json.",
        "Headroom uses observed labels and is not a deployable policy or population bound.",
        "",
        "Human review: pending. These exploratory calibration results do not authorize a test-set conclusion.",
    ]
    if artifact["synthetic"]:
        lines += [
            "",
            "SYNTHETIC PIPELINE CHECK: these outputs cannot support model or cost conclusions.",
        ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return out


def create_study_audit(directory, count=50):
    """Export a stratified human-review worksheet without overwriting reviews."""
    directory = Path(directory)
    if type(count) is not int or count < 1:
        raise ValueError("audit count must be a positive integer")
    with run_lock(directory):
        path = directory / "human-audit.json"
        if path.exists():
            raise ValueError(f"Audit already exists; edit it in place: {path}")
        summary = read_json(report_study(directory) / "summary.json")
        if not summary["complete"]:
            raise ValueError("Finish all calibration arms before freezing the human audit")
        study = verified(directory / "study.json")
        questions = {q["id"]: q for q in read_json(directory / "data/questions.json")}
        gold = load_gold(directory / "data")
        groups = []
        for cap, arm in summary["arms"].items():
            records = [r for r in load_run(arm["path"])[1] if r["job"]["question_id"] in questions]
            for mode in ["direct", "thinking"]:
                groups.append(
                    sorted(
                        [(cap, arm["run_id"], r) for r in records if r["job"]["mode"] == mode],
                        key=lambda v: digest(
                            {"seed": study["selection_seed"], "job": v[2]["job"]["id"]}
                        ),
                    )
                )
        selected = []
        while len(selected) < count and any(groups):
            for group in groups:
                if group and len(selected) < count:
                    selected.append(group.pop(0))
        rows = []
        for cap, run_id, record in selected:
            job = record["job"]
            rows.append(
                {
                    "answer_cap": int(cap),
                    "run_id": run_id,
                    "job_id": job["id"],
                    "record_sha256": digest(record),
                    "question": questions[job["question_id"]],
                    "gold": gold[job["question_id"]],
                    "result": record["result"],
                    "score": score_record(record, gold[job["question_id"]]),
                    "review": "pending",
                    "notes": "",
                }
            )
        atomic_json(
            path,
            {
                "study_sha256": digest(study),
                "scoring_version": SCORING_VERSION,
                "reviewer": "",
                "reviewer_type": "human",
                "status": "pending",
                "instructions": "A person must inspect each question, final answer and score, enter their name, and record a decision with notes. An agent must not fill this as human review.",
                "rows": rows,
            },
        )
        return path


def confirmation_report(study_dir, run_dir):
    """Separate cap-selection questions from the other pilot questions."""
    study_dir, run_dir = Path(study_dir), Path(run_dir)
    study = verified(study_dir / "study.json")
    decision = verified(study_dir / "protocol-decision.json")
    if decision["calibration_study_sha256"] != digest(study):
        raise ValueError("Protocol decision refers to a different calibration study")
    manifest, records = load_run(run_dir)
    if manifest["identity"]["config"] != decision["chosen_config"]:
        raise ValueError("Confirmation run differs from the frozen configuration")
    gold = load_gold(manifest["identity"]["config"]["data_dir"])
    if digest(gold) != manifest["scoring_gold_sha256"]:
        raise ValueError("Confirmation scoring reference changed")
    selected = set(study["question_ids"])
    groups = {
        "all_pilot": records,
        "used_for_cap_selection": [r for r in records if r["job"]["question_id"] in selected],
        "not_used_for_cap_selection": [
            r for r in records if r["job"]["question_id"] not in selected
        ],
    }
    summaries = {}
    for name, rows in groups.items():
        scores = [score_record(r, gold[r["job"]["question_id"]]) for r in rows]
        mode_rows = []
        by_id = {s["job_id"]: s for s in scores}
        for mode in ["direct", "thinking"]:
            complete = [r for r in rows if r["job"]["mode"] == mode and r["status"] == "completed"]
            mode_rows.append(
                {
                    "mode": mode,
                    "completed": len(complete),
                    "planned": sum(r["job"]["mode"] == mode for r in rows),
                    "accuracy": sum(by_id[r["job"]["id"]]["correct"] for r in complete)
                    / len(complete)
                    if complete
                    else None,
                    "answer_truncation": sum(r["result"]["answer_truncated"] for r in complete),
                }
            )
        summaries[name] = {
            "planned_questions": len({r["job"]["question_id"] for r in rows}),
            "complete": all(r["status"] == "completed" for r in rows),
            "modes": mode_rows,
            "paired_modes": paired_statistics(rows, scores, 2, study["selection_seed"]),
            "headroom": _headroom(rows, scores, 2),
        }
    artifact = {
        "run_id": manifest["run_id"],
        "scoring_version": SCORING_VERSION,
        "protocol_decision_sha256": digest(decision),
        "records_sha256": digest(records),
        "groups": summaries,
        "human_review_status": "pending",
        "interpretation": "Questions not used for cap selection form a pilot confirmation subset, not the sealed official test split. Human audit remains required for acceptance.",
    }
    out = run_dir / "report"
    atomic_json(out / "calibration-confirmation.json", artifact)
    lines = [
        "# Calibrated pilot confirmation",
        "",
        "| Group | Mode | Completed/planned | Accuracy | Truncated |",
        "|---|---|---:|---:|---:|",
    ]
    for group, value in summaries.items():
        for row in value["modes"]:
            accuracy = f"{row['accuracy']:.1%}" if row["completed"] else "n/a"
            lines.append(
                f"| {group} | {row['mode']} | {row['completed']}/{row['planned']} | {accuracy} | {row['answer_truncation']} |"
            )
    lines += [
        "",
        artifact["interpretation"],
        "",
        "Partial results are provisional; paired intervals and routing diagnostics are in calibration-confirmation.json.",
    ]
    (out / "calibration-confirmation.md").write_text("\n".join(lines) + "\n")
    return out


def confirm_pilot(directory, progress=print):
    """Run the frozen full pilot, then automatically report and prepare its audit."""
    directory = Path(directory)
    with run_lock(directory):
        study = verified(directory / "study.json")
        decision = verified(directory / "protocol-decision.json")
        if decision["calibration_study_sha256"] != digest(study):
            raise ValueError("Protocol decision refers to a different calibration study")
        if digest(decision["chosen_config"]) != decision["chosen_config_sha256"]:
            raise ValueError("Frozen confirmation configuration changed")
        config = from_dict(decision["chosen_config"])
        if (
            config.split != "pilot"
            or config.samples != 2
            or set(config.modes) != {"direct", "thinking"}
        ):
            raise ValueError("Confirmation must use pilot questions and two samples per mode")
        from .data import load_questions

        questions = load_questions(config.data_dir, config.split)
        if len(questions) != 100:
            raise ValueError("Confirmation requires the full 100-question pilot")
        by_id = {q.id: q.to_dict() for q in questions}
        if (
            any(q not in by_id for q in study["question_ids"])
            or digest([by_id[q] for q in study["question_ids"]]) != study["questions_sha256"]
        ):
            raise ValueError("Confirmation pilot differs from the frozen calibration questions")
        from .backend import environment, make_backend

        backend = make_backend(config)
        baseline = verified(Path(study["baseline"]) / "manifest.json")
        actual = {
            "environment": environment(),
            "backend": backend.metadata,
            "protocol_version": build_run_identity(
                config, questions, backend.metadata, environment()
            )["protocol_version"],
        }
        if any(actual[k] != baseline["identity"].get(k) for k in actual):
            raise ValueError("Confirmation changed environment or generation implementation")
        if implementation_digest() != manifest_implementation(baseline):
            raise ValueError("Confirmation changed generation implementation")
        path = run(config, backend=backend, progress=progress)
        atomic_json(directory / "confirmation-run.json", envelope({"path": str(path.resolve())}))
        report(path)
        confirmation_report(directory, path)
        _, rows = load_run(path)
        if all(r["status"] == "completed" for r in rows) and not (path / "audit.json").exists():
            create_audit(path, count=50)
        progress(f"Confirmation report: {path / 'report/calibration-confirmation.md'}")
        return path
