"""Command line entry points for the A–C experiment pipeline."""

import argparse
import json
import sys

from .config import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rb", description="Reasoning-budget experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Report package versions and device availability")
    prepare = sub.add_parser("prepare", help="Prepare fixtures or freeze GSM8K splits")
    prepare.add_argument("dataset", choices=["fixtures", "gsm8k"])
    prepare.add_argument("--output")
    prepare.add_argument("--seed", type=int, default=20260909)
    prepare.add_argument("--revision", default="main")
    prepare.add_argument("--cache-dir", default=".cache/huggingface")
    for command in ["smoke", "generate"]:
        p = sub.add_parser(command, help="Execute or resume generation jobs")
        p.add_argument(
            "--config", default="configs/smoke.yaml" if command == "smoke" else "configs/pilot.yaml"
        )
    score = sub.add_parser("score", help="Score saved answers using separate gold artifact")
    score.add_argument("run_dir")
    report = sub.add_parser("report", help="Score and report a saved run")
    report.add_argument("run_dir")
    report.add_argument("--hourly-rate", type=float)
    report.add_argument("--projection-questions", type=int, default=1100)
    report.add_argument("--projection-samples", type=int, default=2)
    audit = sub.add_parser("audit", help="Create a deterministic manual-review artifact")
    audit.add_argument("run_dir")
    audit.add_argument("--count", type=int, default=50)
    routing = sub.add_parser("routing", help="Exploratory pilot routing without new generations")
    routing.add_argument("run_dir")
    routing.add_argument("--output", default="artifacts/routing")
    routing.add_argument("--seed", type=int, default=20260917)
    learning = sub.add_parser("learnability", help="Disjoint stronger-router baseline study")
    learning_sub = learning.add_subparsers(dest="learning_command", required=True)
    learning_prepare = learning_sub.add_parser("prepare")
    learning_prepare.add_argument("--config", default="configs/pilot-calibrated.yaml")
    learning_prepare.add_argument("--output", default="artifacts/learnability/baselines-v1")
    for action in ["run", "fit", "report"]:
        learning_sub.add_parser(action).add_argument("study_dir")
    probe = sub.add_parser("probe", help="First-draft continuation study on fresh questions")
    probe_sub = probe.add_subparsers(dest="probe_command", required=True)
    probe_prepare = probe_sub.add_parser("prepare")
    probe_prepare.add_argument("--config", default="configs/pilot-calibrated.yaml")
    probe_prepare.add_argument("--output", default="artifacts/probe/continuation-v1")
    for action in ["run", "fit", "report"]:
        probe_sub.add_parser(action).add_argument("study_dir")
    power = sub.add_parser("power", help="Prospective power planning from completed diagnostic")
    power.add_argument("study_dir")
    power.add_argument("--data-dir", default="artifacts/data/gsm8k")
    confirmation = sub.add_parser("confirm", help="Fixed independent frozen-router confirmation")
    confirm_sub = confirmation.add_subparsers(dest="confirm_command", required=True)
    confirm_prepare = confirm_sub.add_parser("prepare")
    confirm_prepare.add_argument("--parent", default="artifacts/probe/continuation-v1")
    confirm_prepare.add_argument("--output", default="artifacts/confirmation/frozen-router-v1")
    confirm_prepare.add_argument("--data-dir", default="artifacts/data/gsm8k")
    confirm_prepare.add_argument("--artifacts", default="artifacts")
    confirm_prepare.add_argument("--cache-dir", default=".cache/huggingface")
    for action in ["run", "report", "status"]:
        command = confirm_sub.add_parser(action)
        command.add_argument("study_dir")
        if action == "run":
            command.add_argument("--batches", type=int)
    calibration = sub.add_parser("calibrate", help="Freeze, run, or report answer-cap calibration")
    calibration_sub = calibration.add_subparsers(dest="calibration_command", required=True)
    calibration_prepare = calibration_sub.add_parser("prepare")
    calibration_prepare.add_argument("--baseline", required=True)
    calibration_prepare.add_argument("--output", default="artifacts/calibration/answer-cap-v1")
    calibration_prepare.add_argument("--count", type=int, default=25)
    calibration_prepare.add_argument("--seed", type=int, default=20260914)
    for command in ["run", "report", "confirm"]:
        calibration_sub.add_parser(command).add_argument("study_dir")
    calibration_audit = calibration_sub.add_parser("audit")
    calibration_audit.add_argument("study_dir")
    calibration_audit.add_argument("--count", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            from .backend import environment

            print(json.dumps(environment(), indent=2))
        elif args.command == "confirm":
            from .confirmation import evaluate, prepare, run_study, status
            from .storage import run_lock

            def progress(message):
                print(message, flush=True)

            if args.confirm_command == "prepare":
                print(
                    prepare(args.parent, args.output, args.data_dir, args.artifacts, args.cache_dir)
                )
            elif args.confirm_command == "run":
                print(run_study(args.study_dir, progress, args.batches))
            elif args.confirm_command == "status":
                print(json.dumps(status(args.study_dir), indent=2))
            else:
                with run_lock(args.study_dir):
                    print(evaluate(args.study_dir, progress))
        elif args.command == "power":
            from .power import analyze

            print(analyze(args.study_dir, args.data_dir))
        elif args.command == "probe":
            from .probe_study import evaluate, freeze_models, prepare, run_study
            from .storage import run_lock

            def progress(message):
                print(message, flush=True)

            if args.probe_command == "prepare":
                print(prepare(args.config, args.output))
            elif args.probe_command == "run":
                print(run_study(args.study_dir, progress))
            else:
                with run_lock(args.study_dir):
                    if args.probe_command == "fit":
                        freeze_models(args.study_dir, progress)
                        print(f"{args.study_dir}/models.json")
                    else:
                        print(evaluate(args.study_dir, progress))
        elif args.command == "learnability":
            from .learnability import evaluate, freeze_models, prepare, run_study
            from .storage import run_lock

            def progress(message):
                print(message, flush=True)

            if args.learning_command == "prepare":
                print(prepare(args.config, args.output))
            elif args.learning_command == "run":
                print(run_study(args.study_dir, progress))
            else:
                with run_lock(args.study_dir):
                    if args.learning_command == "fit":
                        freeze_models(args.study_dir, progress)
                        print(f"{args.study_dir}/models.json")
                    else:
                        print(evaluate(args.study_dir, progress))
        elif args.command == "routing":
            from .routing import explore

            print(
                explore(
                    args.run_dir,
                    args.output,
                    args.seed,
                    progress=lambda message: print(message, flush=True),
                )
            )
        elif args.command == "calibrate":
            from .calibration import (
                confirm_pilot,
                create_study_audit,
                prepare,
                report_study,
                run_study,
            )

            if args.calibration_command == "prepare":
                print(prepare(args.baseline, args.output, args.count, args.seed))
            elif args.calibration_command == "run":
                print(
                    run_study(args.study_dir, progress=lambda message: print(message, flush=True))
                )
            elif args.calibration_command == "audit":
                print(create_study_audit(args.study_dir, args.count))
            elif args.calibration_command == "confirm":
                print(
                    confirm_pilot(
                        args.study_dir, progress=lambda message: print(message, flush=True)
                    )
                )
            else:
                print(report_study(args.study_dir))
        elif args.command == "prepare":
            from .data import prepare_fixtures, prepare_gsm8k

            output = args.output or f"artifacts/data/{args.dataset}"
            print(
                prepare_fixtures(output)
                if args.dataset == "fixtures"
                else prepare_gsm8k(output, args.seed, args.revision, args.cache_dir)
            )
        elif args.command in {"smoke", "generate"}:
            from .runner import run

            config = load_config(args.config)
            if args.command == "smoke":
                from .data import prepare_fixtures

                if (
                    config.split != "smoke"
                    or config.samples != 1
                    or set(config.modes) != {"direct", "thinking"}
                ):
                    raise ValueError("smoke requires split=smoke, samples=1 and both modes")
                prepare_fixtures(config.data_dir)
            path = run(config, progress=lambda message: print(message, flush=True))
            print(path)
        elif args.command == "score":
            from .reporting import score_run

            artifact = score_run(args.run_dir)
            print(f"Scored {len(artifact['scores'])} expected jobs: {args.run_dir}/scores.json")
        elif args.command == "report":
            from .reporting import report

            print(
                report(
                    args.run_dir,
                    args.hourly_rate,
                    args.projection_questions,
                    args.projection_samples,
                )
            )
        elif args.command == "audit":
            from .reporting import create_audit

            if args.count < 1:
                raise ValueError("audit count must be positive")
            print(create_audit(args.run_dir, args.count))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"rb: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
