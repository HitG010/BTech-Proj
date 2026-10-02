"""Independent read-only arithmetic review of power and synthetic CLM reports."""

import argparse
import math
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, envelope, verified

ROOT = Path("artifacts/research/data-efficiency-v1")


def independent_power(n, effect, sd, alpha):
    cutoff, shift = norm.ppf(1 - alpha / 2), abs(effect) * np.sqrt(n) / sd
    return float(norm.sf(cutoff - shift) + norm.cdf(-cutoff - shift))


def check_power(root):
    directory = root / "broader-signal-power-v1"
    report, plan = verified(directory / "report.json"), verified(directory / "analysis-plan.json")
    if report["plan_sha256"] != digest(plan):
        raise ValueError("Power plan identity changed")
    for path, expected in plan["source_sha256"].items():
        if file_hash(path) != expected:
            raise ValueError("Power source changed")
    for relative, expected in report["inputs"].items():
        if file_hash(root / relative) != expected:
            raise ValueError("Power input changed")
    checks, alpha = 0, report["spec"]["alpha"]
    for row in report["power_grid"]:
        effect, sd = row["effect"], row["sd"]
        for count, actual in row["power_by_n"].items():
            assert math.isclose(actual, independent_power(int(count), effect, sd, alpha), abs_tol=1e-12)
            checks += 1
        for target, count in row["required_questions"].items():
            assert independent_power(count, effect, sd, alpha) >= float(target)
            assert count == 2 or independent_power(count - 1, effect, sd, alpha) < float(target)
            checks += 1
    for row in report["detectable_effect_80pct"]:
        expected = brentq(lambda effect: independent_power(row["n"], effect, row["sd"], alpha) - .8,
                         0, row["sd"] * 10, xtol=1e-14)
        assert math.isclose(expected, row["effect"], abs_tol=1e-12)
        checks += 1
    budget = report["proposed_design_budget"]
    protocol = verified(root / "repeat-panel-v1/protocol.json")
    config = protocol["snapshot"]["config"]
    pair = config["answer_tokens"] * 2 + config["reasoning_tokens"] + protocol["snapshot"]["identity"]["backend"]["closure_tokens"]
    assert budget["maximum_reserved_tokens_per_pair"] == pair
    assert budget["maximum_response_tokens"] == pair * budget["questions"] * budget["solvers"] * report["spec"]["draws_per_mode_per_solver"]
    assert budget["responses"] == 2 * budget["total_pairs"]
    assert budget["collection_authorized_by_this_report"] is False
    assert all(row["mean"] < 0 and row["n_for_observed_positive_effect"] is None
               for row in report["development_description"].values())
    return {"report_sha256": digest(report), "normal_power_checks": checks,
            "reservation_accounting_pass": True, "input_and_source_hashes_preserved": True}


def check_clm(root):
    directory = root / "clm-local-preflight-v1"
    report, plan = verified(directory / "report.json"), verified(directory / "analysis-plan.json")
    if report["plan_sha256"] != digest(plan):
        raise ValueError("CLM plan identity changed")
    for path, expected in (plan["source_sha256"] | plan["protected_file_sha256"]).items():
        if file_hash(path) != expected:
            raise ValueError("Preflight source or protected input changed")
    assets = root / "clm-local-environment-v1/assets"
    for name, record in plan["assets"]["assets"].items():
        for filename, expected in record["files"].items():
            if file_hash(assets / name / filename) != expected:
                raise ValueError("Prepared public model asset changed")
    assert file_hash(assets / "official-heads.py") == plan["assets"]["head_code_sha256"]
    if report["status"] == "failed_engineering":
        return {"report_sha256": digest(report), "engineering_pass": False,
            "terminal_failure_preserved": True, "source_and_protected_inputs_preserved": True}
    encoder = verified(directory / "encoder-report.json")
    assert encoder == report["encoder"] and encoder["plan_sha256"] == digest(plan)
    assert file_hash(directory / "synthetic-embeddings.npz") == encoder["embedding_file_sha256"]
    with np.load(directory / "synthetic-embeddings.npz", allow_pickle=False) as record:
        vectors = record["vectors"]
    assert vectors.shape == (10, 4096) and np.isfinite(vectors).all()
    norms = np.sqrt(np.sum(vectors.astype(np.float64)**2, axis=1))
    assert np.max(np.abs(norms - 1)) <= 1e-5
    assert max(np.max(np.abs(vectors[i] - vectors[i+1])) for i in (0, 2, 4, 6)) <= 1e-5
    spec = plan["spec"]
    assert encoder["mlx_peak_bytes"] <= spec["maximum_observed_peak_mlx_bytes"]
    assert report["maximum_polled_worker_rss_bytes"] <= spec["maximum_observed_worker_rss_bytes"]
    assert report["worker_wall_seconds"] <= spec["worker_wall_seconds"] + spec["rss_poll_seconds"] + 1
    assert report["worker_exit_code"] == 0 and report["termination"] is None
    assert all(0 <= row["seconds"] <= spec["max_long_input_seconds"] for row in encoder["rows"])
    assert report["heads"]["binary_margin_identity_pass"]
    assert report["heads"]["maximum_arithmetic_difference"] <= spec["head_score_absolute_tolerance"]
    assert np.isfinite(np.asarray(report["heads"]["synthetic_logits"])).all()
    assert report["no_cached_panel_access"] and report["no_solver_generation"]
    return {"report_sha256": digest(report), "engineering_pass": True,
        "synthetic_vector_and_resource_gates_pass": True, "source_and_protected_inputs_preserved": True,
        "full_precision_or_task_semantic_equivalence_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--power-only", action="store_true")
    args = parser.parse_args()
    result = {"power": check_power(args.root), "review_script_sha256": file_hash(__file__),
              "no_fitting_encoder_execution_generation_reference_access": True}
    if not args.power_only:
        result["clm"] = check_clm(args.root)
    output = args.root / "local-research-review-v1"
    output.mkdir(exist_ok=True)
    import json
    name = "power-verification.json" if args.power_only else "verification.json"
    with (output / name).open("x") as stream:
        json.dump(envelope(result), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print({"verification_sha256": digest(result), "power_checks": result["power"]["normal_power_checks"],
           "clm": result.get("clm", {}).get("engineering_pass")})


if __name__ == "__main__":
    main()
