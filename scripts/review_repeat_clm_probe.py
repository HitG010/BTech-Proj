"""Fresh-process cached CLM accounting/head review; never refits or encodes."""

import argparse
import os

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.storage import digest, verified
from scripts import repeat_clm_probe as probe
from scripts.repeat_cpu_feasibility import load_panel
from scripts.review_router_feasibility import close, interval, measured
from scripts.verify_phase2_repeat import verify

OUTPUT = probe.local.BASE / "repeat-clm-review-v1"


def functional_projection(values, weights, cfg):
    """Independent functional evaluation of the released head checkpoint."""
    import torch.nn.functional as F
    activation = {"gelu": F.gelu, "relu": F.relu, "silu": F.silu}[cfg.get("activation", "gelu")]
    x = activation(F.linear(values, weights["inp.weight"], weights["inp.bias"]))
    for i in range(cfg["depth"] - 2):
        h = F.linear(x, weights[f"hidden.{i}.weight"], weights[f"hidden.{i}.bias"])
        if cfg.get("layernorm", False):
            h = F.layer_norm(h, (cfg["width"],), weights[f"norms.{i}.weight"], weights[f"norms.{i}.bias"], eps=1e-5)
        h = activation(h)
        x = x + h if cfg.get("residual", False) else h
    return F.normalize(F.linear(x, weights["out.weight"], weights["out.bias"]), dim=-1)


def review_heads(states, actions, head):
    import torch
    torch.set_num_threads(1)
    ck = torch.load(probe.local.ENV / "assets/heads/CLM_v0.1-8B.pt", map_location="cpu", weights_only=True)
    cfg = ck["cfg"]
    scale = float(torch.as_tensor(ck["logit_scale"]).float().exp().clamp(max=100.))
    close(scale, head["scale"])
    if cfg != head["checkpoint_cfg"]:
        raise ValueError("Head configuration changed")
    logits = []
    with torch.inference_mode():
        za = functional_projection(torch.from_numpy(actions), ck["action_head"], cfg)
        for vector in states.reshape(-1, 4096):
            zs = functional_projection(torch.from_numpy(vector[None]), ck["state_head"], cfg)
            logits.append((scale * (zs @ za.T)).numpy()[0])
    logits = np.asarray(logits).reshape(50, 8, 2)
    maximum = float(np.max(np.abs(logits - np.asarray(head["logits"]))))
    if maximum > 1e-4:
        raise ValueError("Independent released-head score reproduction differs")
    expected = np.asarray(head["logits"])[..., 1] - np.asarray(head["logits"])[..., 0]
    np.testing.assert_allclose(np.asarray(head["margins"]), expected, atol=1e-5, rtol=0)
    return {"functional_projection_maximum_logit_difference": maximum,
        "checkpoint_and_margin_arithmetic_pass": True, "synthetic_inference_or_encoder_rerun": False}


def review_statistics(panel, statistics, spec, margins, encoder_seconds, head_seconds):
    ids, count = panel["ids"], 0
    metrics_by_condition = {}
    for name, (train_draws, eval_draws) in spec["conditions"].items():
        condition = statistics["conditions"][name]
        if condition["train_draws"] != train_draws or condition["evaluation_draws"] != eval_draws:
            raise ValueError("Condition draw boundary changed")
        if len(condition["folds"]) != 5:
            raise ValueError("Outer fold coverage changed")
        for detail in condition["folds"]:
            train = [i for i, qid in enumerate(ids) if panel["folds"][qid] != detail["fold"]]
            test = [i for i, qid in enumerate(ids) if panel["folds"][qid] == detail["fold"]]
            if (detail["train_indices"] != train or detail["test_indices"] != test
                    or detail["train_ids"] != [ids[i] for i in train]
                    or detail["test_ids"] != [ids[i] for i in test]
                    or detail["train_draws"] != train_draws or detail["evaluation_draws"] != eval_draws):
                raise ValueError("Fold group boundary changed")
            if detail["ridge_fits"] != 30 or detail["pca_fits"] != 5 or len(detail["inner_splits"]) != 4:
                raise ValueError("Frozen fit bound changed")
            for split in detail["inner_splits"]:
                a, b = set(split["train_indices"]), set(split["validation_indices"])
                if a & b or a | b != set(train) or split["draws"] != train_draws:
                    raise ValueError("Inner boundary leaked or lost questions")
            for family in spec["families"]:
                expected_setting = max(((a, h) for a in spec["alphas"] for h in spec["thresholds"]),
                    key=lambda pair: (detail["inner_utility"][probe.config_key(family, *pair)], *pair))
                setting = detail["settings"][family]
                if (setting["alpha"], setting["threshold"]) != expected_setting:
                    raise ValueError("Family setting was not selected from inner utility")
                close(setting["inner_utility"], detail["inner_utility"][probe.config_key(family, *expected_setting)])
                selected_key = probe.config_key(family, *expected_setting)
                for i in test:
                    rows = condition["per_question"][ids[i]]["policies"]
                    if rows[family]["decisions"] != rows[selected_key]["decisions"]:
                        raise ValueError("Selected family actions differ from selected configuration")
            selected = max(spec["families"], key=lambda f: detail["settings"][f]["inner_utility"])
            if selected != detail["selected_family"]:
                raise ValueError("Family was not selected from inner utility")
            for i in test:
                rows = condition["per_question"][ids[i]]["policies"]
                if rows["nested_selected"]["decisions"] != rows[selected]["decisions"]:
                    raise ValueError("Nested selected actions differ")
                np.testing.assert_array_equal(rows["clm_zero_shot"]["decisions"], margins[i, eval_draws] > 0)
                original = panel["primary"]["statistics"]["conditions"][name]["per_question"][ids[i]]["policies"]["confidence"]
                if rows["confidence"]["decisions"] != original["decisions"]:
                    raise ValueError("Historical confidence action mismatch")
                for policy in ("clm_zero_shot", *spec["families"], "nested_selected"):
                    record = rows[policy]
                    overhead = np.asarray(record["observed_router_seconds_by_draw"])
                    family = selected if policy == "nested_selected" else policy
                    lower = encoder_seconds[i, eval_draws].copy()
                    if family in ("clm_zero_shot", "clm_calibrated"):
                        lower += head_seconds[i, eval_draws]
                    if overhead.shape != (len(eval_draws),) or not np.isfinite(overhead).all() or np.any(overhead + 1e-12 < lower):
                        raise ValueError("Timing proxy omits measured encoder/head work")
                    close(record["cached_solver_plus_observed_router_seconds"], record["seconds"] + overhead.mean())
        metrics_by_condition[name] = {}
        for policy, summary in condition["summary"].items():
            rows = [condition["per_question"][qid]["policies"][policy] for qid in ids]
            actions = np.asarray([row["decisions"] for row in rows])
            values = measured(panel["d"][:, eval_draws], panel["t"][:, eval_draws], actions)
            metrics_by_condition[name][policy] = values
            for metric in ("accuracy", "tokens", "seconds", "utility", "escalation_rate"):
                for i, row in enumerate(rows):
                    close(row[metric], values[metric][i])
                close(summary[f"mean_{metric}"], values[metric].mean())
            close(summary["pairs"], actions.size)
            close(summary["escalations"], actions.sum())
            for reported, metric in (("positive_gain_escalations", "positive_gain_escalations"),
                ("nonpositive_gain_escalations", "nonpositive_gain_escalations"),
                ("harmful_escalations", "harmed"), ("missed_positive_gain_opportunities", "missed_positive_gains")):
                close(summary[reported], values[metric].sum())
            confidence = np.asarray([condition["per_question"][qid]["policies"]["confidence"]["utility"] for qid in ids])
            delta = values["utility"] - confidence
            close(summary["delta_vs_confidence"]["mean"], delta.mean())
            np.testing.assert_allclose(summary["delta_vs_confidence"]["ci90"], interval(delta, spec["bootstrap_seed"]), atol=1e-10, rtol=0)
            if "cached_solver_plus_observed_router_seconds" in summary:
                close(summary["cached_solver_plus_observed_router_seconds"], np.mean([
                    row["cached_solver_plus_observed_router_seconds"] for row in rows]))
            count += actions.size
    for policy, summary in statistics["averages_vs_confidence"].items():
        differences = [metrics_by_condition[name][policy]["utility"] - metrics_by_condition[name]["confidence"]["utility"]
                       for name in ("k4_A_to_B", "k4_B_to_A")]
        average = (differences[0] + differences[1]) / 2
        close(summary["mean"], average.mean())
        close(summary["A_to_B"], differences[0].mean())
        close(summary["B_to_A"], differences[1].mean())
        np.testing.assert_allclose(summary["ci90"], interval(average, spec["bootstrap_seed"]), atol=1e-10, rtol=0)
        screen = statistics["screens"][policy]
        loo = (average.sum() - average) / (len(average) - 1)
        expected = {"average_at_least_0.01": average.mean() >= .01,
            "both_directions_positive": differences[0].mean() > 0 and differences[1].mean() > 0,
            "all_leave_one_question_out_positive": np.all(loo > 0)}
        if screen["gates"] != expected or screen["passes"] != all(expected.values()) or screen["scale_acquisition"]:
            raise ValueError("Exploratory screen mismatch")
    delta = np.mean([metrics_by_condition[name]["clm_calibrated"]["utility"] - metrics_by_condition[name]["raw_encoder_ridge"]["utility"]
                     for name in ("k4_A_to_B", "k4_B_to_A")], axis=0)
    close(statistics["calibrated_clm_minus_raw_control"]["mean"], delta.mean())
    np.testing.assert_allclose(statistics["calibrated_clm_minus_raw_control"]["ci90"], interval(delta, spec["bootstrap_seed"]), atol=1e-10, rtol=0)
    if statistics["fit_count"] != 450 or statistics["pca_fit_count"] != 75:
        raise ValueError("Total fit accounting mismatch")
    return {"decisions_checked": count, "fold_selection_and_accounting_pass": True,
            "historical_confidence_preserved": True, "fixed_fit_intervals_and_screens_pass": True}


def review():
    plan = probe.checked_plan()
    report = verified(probe.OUTPUT / "report.json")
    panel = load_panel(probe.STUDY)
    if (report["plan_sha256"] != digest(plan) or report["panel_identity"] != panel["identity"]
            or panel["identity"] != plan["panel_identity"] or report["spec"] != plan["spec"]):
        raise ValueError("Frozen plan or panel identity differs")
    if probe.local.validate_assets() != plan["assets"]:
        raise ValueError("Frozen public asset changed")
    request = verified(probe.OUTPUT / "encoder-request.json")
    encoder = verified(probe.OUTPUT / "encoder-report.json")
    if digest(request) != plan["request_sha256"] or digest(encoder) != report["encoder_report_sha256"]:
        raise ValueError("Encoder request/report changed")
    if file_hash(probe.OUTPUT / "encoder-features.npz") != encoder["feature_file_sha256"]:
        raise ValueError("Encoder feature bytes changed")
    with np.load(probe.OUTPUT / "encoder-features.npz", allow_pickle=False) as values:
        states, actions = values["states"], values["actions"]
    probe.validate_endpoint(encoder, request, states, actions)
    double_norms = np.sqrt(np.sum(states.astype(np.float64)**2, axis=-1))
    if np.max(np.abs(double_norms - 1)) > 1e-5:
        raise ValueError("Independent embedding normalization check failed")
    head = verified(probe.OUTPUT / "released-head-report.json")
    if head["plan_sha256"] != digest(plan):
        raise ValueError("Head report identity differs")
    head_check = review_heads(states, actions, head)
    margins = np.asarray(head["margins"])
    seconds = np.asarray([r["total_seconds"] for r in encoder["rows"][:400]]).reshape(50, 8)
    accounting = review_statistics(panel, report["statistics"], plan["spec"], margins, seconds, np.asarray(head["state_head_seconds"]))
    original = verify(probe.STUDY)
    if report["primary_gates_unchanged"] != panel["primary"]["statistics"]["gates"]:
        raise ValueError("Primary gates changed")
    process = verified(probe.OUTPUT / "encoder-process.json")
    if (process["exit_code"] or process["termination"] is not None
            or process["maximum_polled_worker_rss_bytes"] > plan["spec"]["maximum_polled_worker_rss_bytes"]
            or process["wall_seconds"] > plan["spec"]["worker_wall_seconds"] + 1):
        raise ValueError("Encoder process endpoint failed")
    if not report["no_solver_generation"] or not report["no_new_references"] or report["cloud_spend_usd"]:
        raise ValueError("Study boundary differs")
    return {"plan_sha256": digest(plan), "report_sha256": digest(report),
        "review_script_sha256": file_hash(__file__), "accounting": accounting, "heads": head_check,
        "protected_originals_verified": original["protected_originals_verified"],
        "cached_encoder_geometry_and_resource_pass": True,
        "no_refitting_encoder_execution_reference_access": True,
        "primary_gates_and_allocations_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = review()
    probe.new(OUTPUT / "verification.json", result)
    render(verified(probe.OUTPUT / "report.json")["statistics"], OUTPUT)
    print({"verified": True, "verification_sha256": digest(result), "decisions": result["accounting"]["decisions_checked"]})


def render(statistics, output):
    os.environ.setdefault("MPLCONFIGDIR", str(probe.local.BASE / "plot-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    policies = ["clm_zero_shot", "clm_calibrated", "raw_encoder_ridge", "nested_selected"]
    labels = ["Released CLM: zero-shot", "Released CLM: calibrated", "Matched raw encoder: Ridge", "Training-selected family"]
    rows = [statistics["averages_vs_confidence"][policy] for policy in policies]
    centers = np.asarray([row["mean"] for row in rows])
    y = np.arange(4)
    fig, ax = plt.subplots(figsize=(9, 4.4), layout="constrained")
    ax.axvline(0, color="#64748b", linewidth=1)
    for i, row in enumerate(rows):
        ax.plot(row["ci90"], [i, i], color="#2563eb", linewidth=2)
    ax.scatter(centers, y, color="#2563eb", label="Both-half average; 90% interval", zorder=3)
    ax.scatter([row["A_to_B"] for row in rows], y - .13, marker="^", color="#b45309", label="A4 → B4")
    ax.scatter([row["B_to_A"] for row in rows], y + .13, marker="v", color="#047857", label="B4 → A4")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Utility difference versus confidence (λ = .05)")
    fig.suptitle("Cached CLM diagnostic: 50 reused question groups", x=.02, ha="left", fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=.15)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.03), frameon=False, fontsize=8, ncol=3)
    fig.supxlabel("Fixed-fit question bootstrap; quantized adaptation; no independent confirmation.", fontsize=8)
    for extension in ("png", "pdf"):
        path = output / f"utility-comparison.{extension}"
        with path.open("xb") as stream:
            fig.savefig(stream, format=extension, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
