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
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            from .backend import environment

            print(json.dumps(environment(), indent=2))
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
