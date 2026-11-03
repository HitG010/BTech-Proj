"""Rebuild the short paper's numbers from one self-contained cache file.

export (on the machine holding artifacts/): load the completed studies through
their guarded loaders and write a single cache of per-state outcomes, features,
extracted direct answers, and the recorded decisions of the control families.

check (anywhere, from the cache alone): rerun the historical fits, cost curves,
refit-inclusive intervals, and agreement simulation with the frozen audit code;
recompute every Table 1 and Table 2 value and the Figure 1 points; and compare
each with the published value.

Neither step generates a response, calls a scorer, or opens a reference answer.
"""

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from reasoning_budget import repeat_stats as historical
from reasoning_budget.storage import digest, envelope, verified

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/research/data-efficiency-v1"
DEFAULT_CACHE = BASE / "paper-cache-v1" / "paper-cache.json"
FIGURE_MANIFEST = ROOT / "papers/thinking-selection/short/figures/output/manifest.json"
FORMAT = "thinking-selection-paper-cache-v1"
K4 = ("k4_A_to_B", "k4_B_to_A")
SOLVERS = ("qwen3-0.6b", "qwen3-1.7b")

# Recorded decisions of the control families (their fitting needs encoders,
# teacher forcing, or neural training that the cache does not rerun).
# name: (report path under BASE, keys to the conditions, condition names for
#        A->B and B->A, policy key, bootstrap seed of its averaged interval)
FAMILIES = {
    "cpu_selected": ("repeat-cpu-feasibility-v1/report.json", ("conditions",),
                     ("k4_A_to_B", "k4_B_to_A"), "selected_new", 20261002),
    "neural_selected": ("repeat-contrastive-pilot-v1/report.json", ("statistics", "conditions"),
                        ("A4_to_B4", "B4_to_A4"), "nested_selected", 20261004),
    "clm_zero_shot": ("repeat-clm-probe-v1/report.json", ("statistics", "conditions"),
                      ("k4_A_to_B", "k4_B_to_A"), "clm_zero_shot", 20261006),
    "clm_calibrated": ("repeat-clm-probe-v1/report.json", ("statistics", "conditions"),
                       ("k4_A_to_B", "k4_B_to_A"), "clm_calibrated", 20261006),
    "pca8_ridge": ("repeat-clm-probe-v1/report.json", ("statistics", "conditions"),
                   ("k4_A_to_B", "k4_B_to_A"), "raw_encoder_ridge", 20261006),
    "clm_raw_selected": ("repeat-clm-probe-v1/report.json", ("statistics", "conditions"),
                         ("k4_A_to_B", "k4_B_to_A"), "nested_selected", 20261006),
    "token_learned_error": ("token-deferral-v1/report.json", ("statistics", "conditions"),
                            ("k4_A_to_B", "k4_B_to_A"), "learned_error_score", 20261030),
    "token_min_threshold": ("token-deferral-v1/report.json", ("statistics", "conditions"),
                            ("k4_A_to_B", "k4_B_to_A"), "min_token_threshold", 20261030),
    "token_gain_ridge": ("token-deferral-v1/report.json", ("statistics", "conditions"),
                         ("k4_A_to_B", "k4_B_to_A"), "token_gain_ridge", 20261030),
}

LABELS = {
    "always_direct": "Always direct", "always_think": "Always think",
    "oracle": "Hindsight oracle (not deployable)", "confidence": "Confidence",
    "combined": "Predeclared learner (combined Ridge)",
    "cpu_selected": "Regularized/compressed (CPU family)",
    "neural_selected": "Compact neural objectives", "clm_zero_shot": "Released CLM, zero-shot",
    "clm_calibrated": "Released CLM, calibrated", "pca8_ridge": "Same encoder, PCA8/Ridge",
    "clm_raw_selected": "CLM/raw learned family",
    "token_learned_error": "Token-level learned error score",
    "token_min_threshold": "Minimum-token threshold", "token_gain_ridge": "Token-level gain Ridge",
    "agreement": "Two-draft agreement (simulated)",
}

# Published values: short paper Table 1 (= manuscript v0.7 Table 3 plus reference
# rows), Table 2 (= v0.7 Table 5), and quoted text values. Utility differences
# and intervals carry six decimals, lifts four, accuracies two percent decimals.
TABLE1 = {
    "always_direct": {"accuracy": .895, "tokens": 221.14, "delta": -.012133,
                      "ci90": [-.034069, .007486], "lift": 0.0},
    "always_think": {"accuracy": .945, "tokens": 1610.97, "delta": -.031625, "lift": 0.0},
    "oracle": {"accuracy": .97, "tokens": 342.02, "delta": .056823, "lift": .0707},
    "confidence": {"accuracy": .9275, "tokens": 628.47, "delta": 0.0, "lift": .0178},
    "combined": {"accuracy": .89, "tokens": 757.13, "delta": -.043933,
                 "ci90": [-.064068, -.025246], "lift": -.0243},
    "cpu_selected": {"accuracy": .9075, "tokens": 514.22, "delta": -.014287,
                     "ci90": [-.025680, -.004425], "lift": .0020},
    "neural_selected": {"accuracy": .8925, "tokens": 604.82, "delta": -.033817,
                        "ci90": [-.052515, -.017266], "lift": -.0163},
    "clm_zero_shot": {"accuracy": .9475, "tokens": 1550.53, "delta": -.026103,
                      "ci90": [-.058826, .016513], "lift": .0047},
    "clm_calibrated": {"accuracy": .885, "tokens": 443.71, "delta": -.033262,
                       "ci90": [-.053818, -.015171], "lift": -.0180},
    "pca8_ridge": {"accuracy": .89, "tokens": 330.81, "delta": -.022617,
                   "ci90": [-.043758, -.004464], "lift": -.0089},
    "clm_raw_selected": {"accuracy": .8875, "tokens": 406.34, "delta": -.028893,
                         "ci90": [-.049575, -.010922], "lift": -.0142},
    "token_learned_error": {"accuracy": .8875, "tokens": 570.33, "delta": -.037093,
                            "ci90": [-.061320, -.012740], "lift": -.0201},
    "token_min_threshold": {"accuracy": .91, "tokens": 483.20, "delta": -.010236,
                            "ci90": [-.027213, .005476], "lift": .0056},
    "token_gain_ridge": {"accuracy": .90, "tokens": 483.21, "delta": -.020237,
                         "ci90": [-.035444, -.007115], "lift": -.0044},
    "agreement": {"accuracy": .9225, "tokens": 597.69, "delta": -.003461,
                  "ci90": [-.021222, .011806], "lift": .0140},
}
TABLE2 = {
    "repeat_combined_minus_selected_baseline": {
        "point": -.016204, "fixed": [-.033276, -.000635], "refit": [-.042296, .020701],
        "repartition": [-.036404, -.004875]},
    "repeat_combined_minus_confidence": {
        "point": -.043933, "fixed": [-.064068, -.025246], "refit": [-.057621, .007865],
        "repartition": [-.050609, -.029268]},
    "repeat_confidence_minus_accept": {
        "point": .012133, "fixed": [-.007486, .034069], "refit": [-.026994, .027814],
        "repartition": [.002526, .015153]},
    "two_solver_qwen3_0.6b_confidence_minus_accept": {
        "point": .152677, "fixed": [.085535, .220375], "refit": [.068168, .219945],
        "repartition": [.130551, .167709]},
    "two_solver_qwen3_1.7b_confidence_minus_accept": {
        "point": -.030540, "fixed": [-.056066, -.006071], "refit": [-.050563, .009868],
        "repartition": [-.036918, -.016126]},
}
TEXT = {
    "repeat_rescues": 30, "repeat_harms": 10, "repeat_both_correct": 348, "repeat_both_wrong": 12,
    "confidence_escalations": 100, "confidence_escalated_rescues": 17,
    "confidence_escalated_harms": 4, "confidence_escalated_both_wrong": 4,
    "combined_escalations": 162, "combined_escalated_rescues": 4,
    "confidence_oracle_share": .176,
    "qwen3-0.6b_confidence_accuracy": .8125, "qwen3-0.6b_confidence_tokens": 1062.52,
    "qwen3-0.6b_confidence_lift": .0620,
    "qwen3-1.7b_confidence_accuracy": .8359, "qwen3-1.7b_confidence_tokens": 682.56,
    "qwen3-1.7b_confidence_lift": -.0183,
    "qwen3-0.6b_agreement_minus_confidence": -.028021,
    "qwen3-1.7b_agreement_minus_confidence": .007996,
    "qwen3-0.6b_agreement_minus_accept": .124656,
    "qwen3-1.7b_agreement_minus_accept": -.022545,
    "agreement_second_draft_cost": .011057,
    "agreement_free_draft_difference": .007596,
}
TOLERANCE = {"accuracy": 5e-5, "tokens": 5e-3, "delta": 5e-7, "ci90": 5e-7, "lift": 5e-5,
             "point": 5e-7, "fixed": 5e-7, "refit": 5e-7, "repartition": 5e-7,
             "count": 0, "share": 5e-4, "sweep_accuracy": 5e-5, "sweep_tokens": 0.05}
# These two published differences were computed from utilities already rounded
# to six decimals, so each can be off by up to 1e-6.
DERIVED = {("always_think", "delta"): 1.5e-6, ("oracle", "delta"): 1.5e-6}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def as_list(array):
    return np.asarray(array).tolist()


# ------------------------------------------------------------------ export

def nested(report, keys):
    for key in keys:
        report = report[key]
    return report


def family_decisions(report, keys, conditions, policy, ids, confidence):
    """Recorded k4 decisions for one family, checked against the primary confidence."""
    found = nested(report, keys)
    out = {}
    for ours, theirs in zip(K4, conditions):
        rows = found[theirs]["per_question"]
        decisions = []
        for qid in ids:
            policies = rows[qid]["policies"]
            if policies["confidence"]["decisions"] != confidence[ours][qid]:
                raise ValueError(f"Confidence decisions differ from the primary report: {policy}")
            choice = policies[policy]["decisions"]
            if len(choice) != 4 or any(type(v) is not bool for v in choice):
                raise ValueError(f"Expected four boolean decisions: {policy}/{theirs}/{qid}")
            decisions.append(choice)
        out[ours] = decisions
    return out


def public_identity(identity):
    """Hashes only: no absolute local paths or machine environment in a public cache."""
    out = {k: v for k, v in identity.items() if k not in ("study", "runtime_environment")}
    if "study" in identity:
        out["study"] = Path(identity["study"]).name
    return out


def build_payload(repeat, two_solver, families, provenance):
    ids, q, z, d, t, fold_of, answers, statuses = repeat
    two_ids, two_folds, panels = two_solver
    return {
        "format": FORMAT,
        "provenance": provenance,
        "repeat": {"question_ids": list(ids), "folds": as_list(fold_of),
                   "question_features": as_list(q), "draft_features": as_list(z),
                   "direct": as_list(d), "thinking": as_list(t),
                   "direct_answers": as_list(answers), "direct_parser_status": as_list(statuses)},
        "two_solver": {"question_ids": list(two_ids), "folds": as_list(two_folds),
                       "panels": {s: {k: as_list(v) for k, v in panels[s].items()}
                                  for s in SOLVERS}},
        "family_decisions": families,
        "contents": "per-state scored outcomes, charged tokens, seconds, draft features, "
                    "question features, extracted direct answers and parser status, and "
                    "recorded k4 decisions of the control families; no response text, "
                    "reference answer, or sealed allocation",
    }


def export(output):
    from scripts import audit_deferral_curves as audit
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing cache: {output}")
    repeat, primary, repeat_identity = audit.repeat_inputs()
    two_solver, _, two_identity = audit.two_solver_inputs()
    ids = repeat[0]
    confidence = {name: {qid: primary["statistics"]["conditions"][name]["per_question"][qid]
                         ["policies"]["confidence"]["decisions"] for qid in ids} for name in K4}
    reports, families = {}, {}
    for name, (path, keys, conditions, policy, _) in FAMILIES.items():
        if path not in reports:
            reports[path] = verified(BASE / path)
        families[name] = family_decisions(reports[path], keys, conditions, policy, ids, confidence)
    provenance = {
        "repeat_identity": public_identity(repeat_identity),
        "two_solver_identity": public_identity(two_identity),
        "family_reports": {p: {"payload_sha256": digest(r), "file_sha256": file_hash(BASE / p)}
                           for p, r in reports.items()},
        "exporter_sha256": file_hash(__file__),
        "audit_sha256": file_hash(ROOT / "scripts/audit_deferral_curves.py"),
        "no_generation_scoring_references": True,
    }
    payload = build_payload(repeat, two_solver, families, provenance)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(envelope(payload), stream, allow_nan=False)
        stream.write("\n")
    return {"cache": str(output), "payload_sha256": digest(payload),
            "file_sha256": file_hash(output), "bytes": output.stat().st_size}


# ------------------------------------------------------------------ cache

def load_cache(path):
    payload = verified(path)
    if payload.get("format") != FORMAT:
        raise ValueError(f"Not a {FORMAT} file: {path}")
    if set(payload["family_decisions"]) != set(FAMILIES):
        raise ValueError("Cache does not contain every control family")
    return payload


def arrays(payload):
    r, s = payload["repeat"], payload["two_solver"]
    repeat = (list(r["question_ids"]), np.asarray(r["question_features"], dtype=float),
              np.asarray(r["draft_features"], dtype=float), np.asarray(r["direct"], dtype=float),
              np.asarray(r["thinking"], dtype=float), np.asarray(r["folds"], dtype=int),
              np.asarray(r["direct_answers"], dtype=object),
              np.asarray(r["direct_parser_status"], dtype=object))
    panels = {}
    for solver in SOLVERS:
        raw = s["panels"][solver]
        panels[solver] = {k: (np.asarray(v, dtype=object) if k in ("answers", "statuses")
                              else np.asarray(v, dtype=float)) for k, v in raw.items()}
    two_solver = (list(s["question_ids"]), np.asarray(s["folds"], dtype=int), panels)
    families = {name: {c: np.asarray(v, dtype=bool) for c, v in conditions.items()}
                for name, conditions in payload["family_decisions"].items()}
    n = len(repeat[0])
    if (repeat[1].shape[0] != n or repeat[3].shape != (n, 8, 3) or repeat[4].shape != (n, 8, 3)
            or repeat[2].shape != (n, 8, 4) or any(v.shape != (n, 4) for f in families.values()
                                                  for v in f.values())):
        raise ValueError("Cache arrays have unexpected shapes")
    return repeat, two_solver, families


# ------------------------------------------------------------------ recompute

def family_row(decisions, d, t, confidence_utility, refs, seed):
    """Accuracy, tokens, and utility difference vs confidence from recorded decisions."""
    from scripts import audit_deferral_curves as audit
    everyone = np.arange(d.shape[0])
    metrics = {name: historical._rows(d, t, everyone, list(audit.K4[name][1]), decisions[name],
                                      0.05) for name in K4}
    a, b = (metrics[name]["utility"] - confidence_utility[name] for name in K4)
    delta = (a + b) / 2
    accuracy = float(np.mean([metrics[n]["accuracy"].mean() for n in K4]))
    tokens = float(np.mean([metrics[n]["tokens"].mean() for n in K4]))
    ci, _ = audit.fixed_means(delta, seed, 2000, [0.05, 0.95])
    return {"accuracy": accuracy, "tokens": tokens, "delta": float(delta.mean()), "ci90": ci,
            "lift": audit.position(accuracy, tokens, refs, 0.05)["lift_over_random"],
            "escalations": int(sum(decisions[n].sum() for n in K4))}


def recompute(repeat, two_solver, families, processes=1, skip_refit=False):
    from scripts import audit_deferral_curves as audit
    spec = copy.deepcopy(audit.SPEC)
    if skip_refit:
        spec["refit"].update(bootstrap_draws=2, repartitions=2)
    with threadpool_limits(1):
        stats = audit.analyze(repeat, two_solver, processes, spec)
        ids, q, z, d, t, fold_of, _, _ = repeat
        base = audit.historical_spec()
        confidence_utility = {
            name: audit.run_condition(q, z, d, t, fold_of, *audit.K4[name], base)[1]
            ["confidence"]["utility"] for name in K4}
    curve = stats["curves"]["repeat_qwen3_1.7b"]
    state = audit.repeat_states(d, t, z, audit.K4)
    refs = audit.references(state, 0.05)
    conf = curve["policies"]["confidence"]
    refit = stats["refit_uncertainty"]
    table1 = {}
    for name, key in (("always_direct", "always_direct"), ("always_think", "always_escalate"),
                      ("oracle", "oracle")):
        p = curve["references"][key]
        table1[name] = {"accuracy": p["accuracy"], "tokens": p["tokens"],
                        "delta": p["utility"] - conf["utility"], "lift": p["lift_over_random"]}
    accept = refit["repeat_confidence_minus_accept"]["fixed_action_ci90"]
    table1["always_direct"]["ci90"] = [-accept[1], -accept[0]]
    table1["confidence"] = {"accuracy": conf["accuracy"], "tokens": conf["tokens"], "delta": 0.0,
                            "lift": conf["lift_over_random"]}
    comb = curve["policies"]["combined"]
    table1["combined"] = {"accuracy": comb["accuracy"], "tokens": comb["tokens"],
                          "delta": refit["repeat_combined_minus_confidence"]["point"],
                          "ci90": refit["repeat_combined_minus_confidence"]["fixed_action_ci90"],
                          "lift": comb["lift_over_random"]}
    for name, (_, _, _, _, seed) in FAMILIES.items():
        table1[name] = family_row(families[name], d, t, confidence_utility, refs, seed)
    agree = stats["agreement"]["repeat_qwen3_1.7b"]["primary_k4"]
    table1["agreement"] = {"accuracy": agree["accuracy"], "tokens": agree["tokens"],
                           "delta": agree["versus_confidence"]["mean"],
                           "ci90": agree["versus_confidence"]["ci90"],
                           "lift": audit.position(agree["accuracy"], agree["tokens"], refs,
                                                  0.05)["lift_over_random"]}
    table2 = {name: {"point": r["point"], "fixed": r["fixed_action_ci90"],
                     "refit": None if skip_refit else r["refit_ci90"],
                     "repartition": None if skip_refit else [
                         r["repartition"]["quantiles_05_50_95"][0],
                         r["repartition"]["quantiles_05_50_95"][2]]}
              for name, r in refit.items()}
    dc, tc = state["dc"], state["tc"]
    text = {"repeat_rescues": int(((dc == 0) & (tc == 1)).sum()),
            "repeat_harms": int(((dc == 1) & (tc == 0)).sum()),
            "repeat_both_correct": int(((dc == 1) & (tc == 1)).sum()),
            "repeat_both_wrong": int(((dc == 0) & (tc == 0)).sum()),
            "confidence_escalations": conf["escalations"],
            "confidence_escalated_rescues": conf["escalated_rescues"],
            "confidence_escalated_harms": conf["escalated_harms"],
            "confidence_escalated_both_wrong": conf["escalated_both_wrong"],
            "combined_escalations": comb["escalations"],
            "combined_escalated_rescues": comb["escalated_rescues"],
            "confidence_oracle_share": conf["oracle_share"],
            "agreement_second_draft_cost": agree["second_draft_utility_cost"],
            "agreement_free_draft_difference":
                agree["free_second_draft_difference_vs_confidence_descriptive"]}
    for solver in SOLVERS:
        key = "two_solver_" + solver.replace("-", "_")
        c = stats["curves"][key]["policies"]["confidence"]
        text[f"{solver}_confidence_accuracy"] = c["accuracy"]
        text[f"{solver}_confidence_tokens"] = c["tokens"]
        text[f"{solver}_confidence_lift"] = c["lift_over_random"]
        text[f"{solver}_agreement_minus_confidence"] = \
            stats["agreement"][key]["versus_confidence"]["mean"]
        text[f"{solver}_agreement_minus_accept"] = stats["agreement"][key]["versus_accept"]["mean"]
    sweeps = {}
    for key in ("repeat_qwen3_1.7b", "two_solver_qwen3_0.6b", "two_solver_qwen3_1.7b"):
        rows = []
        for row in stats["curves"][key]["lambda_sweep"]:
            item = {"lambda": row["lambda"], "confidence": {
                "accuracy": row["policies"]["confidence"]["accuracy"],
                "tokens": row["policies"]["confidence"]["tokens"]}}
            if key.startswith("repeat"):
                item["combined"] = {"accuracy": row["policies"]["combined"]["accuracy"],
                                    "tokens": row["policies"]["combined"]["tokens"]}
            rows.append(item)
        sweeps[key] = rows
    return {"table1": table1, "table2": table2, "text": text, "sweeps": sweeps,
            "processes": int(processes), "refit_skipped": bool(skip_refit)}


# ------------------------------------------------------------------ compare

def close(actual, expected, tolerance):
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(close(a, e, tolerance) for a, e in zip(actual, expected)))
    return actual is not None and abs(float(actual) - float(expected)) <= tolerance + 1e-12


def compare(results, table1=TABLE1, table2=TABLE2, text=TEXT, figure=None):
    checks = []

    def add(group, item, field, actual, expected, tolerance):
        checks.append({"group": group, "item": item, "field": field, "actual": actual,
                       "expected": expected, "tolerance": tolerance,
                       "passed": close(actual, expected, tolerance)})

    for name, expected in table1.items():
        for field, value in expected.items():
            add("table1", name, field, results["table1"][name].get(field), value,
                DERIVED.get((name, field), TOLERANCE[field]))
    for name, expected in table2.items():
        for field, value in expected.items():
            actual = results["table2"][name][field]
            if actual is None:
                checks.append({"group": "table2", "item": name, "field": field,
                               "actual": None, "expected": value, "skipped": True,
                               "passed": True})
                continue
            add("table2", name, field, actual, value, TOLERANCE[field])
    for name, value in text.items():
        tolerance = (TOLERANCE["count"] if isinstance(value, int)
                     else TOLERANCE["share"] if name.endswith("share")
                     else TOLERANCE["accuracy"] if name.endswith(("accuracy", "lift"))
                     else TOLERANCE["tokens"] if name.endswith("tokens")
                     else TOLERANCE["delta"])
        add("text", name, "value", results["text"][name], value, tolerance)
    if figure is not None:
        for key, expected_rows in figure.items():
            for got, expected in zip(results["sweeps"][key], expected_rows["sweep"]):
                for series in ("confidence", "combined"):
                    if series not in expected:
                        continue
                    label = f"{key} λ={expected['lambda']:g} {series}"
                    add("figure", label, "accuracy", got[series]["accuracy"],
                        expected[series]["accuracy"], TOLERANCE["sweep_accuracy"])
                    add("figure", label, "tokens", got[series]["tokens"],
                        expected[series]["tokens"], TOLERANCE["sweep_tokens"])
    return checks


def figure_values(path=FIGURE_MANIFEST):
    if not Path(path).exists():
        return None
    values = json.loads(Path(path).read_text())["values"]
    return {key: {"sweep": values[key]["sweep"]} for key in
            ("repeat_qwen3_1.7b", "two_solver_qwen3_0.6b", "two_solver_qwen3_1.7b")}


def fmt(value, digits=6):
    if value is None:
        return "n/a"
    if isinstance(value, list):
        return "[" + ", ".join(fmt(v, digits) for v in value) + "]"
    return f"{value:+.{digits}f}"


def markdown(results, checks, cache_sha256):
    failed = [c for c in checks if not c["passed"]]
    skipped = [c for c in checks if c.get("skipped")]
    lines = ["# Reproduction from the paper cache", "",
             f"Cache SHA-256 `{cache_sha256}`. Worker processes: {results['processes']}. "
             f"Checks: {len(checks)}; failed: {len(failed)}; skipped: {len(skipped)}.", "",
             f"**{'All published values reproduced.' if not failed else 'MISMATCHES FOUND.'}**",
             "", "## Table 1 (repeat panel, λ = .05)", "",
             "| Rule | Accuracy | Tokens | Utility vs confidence [90%] | Lift (points) |",
             "|---|---:|---:|---|---:|"]
    for name, row in results["table1"].items():
        ci = f" {fmt(row['ci90'], 3)}" if row.get("ci90") is not None else ""
        lines.append(f"| {LABELS[name]} | {100 * row['accuracy']:.2f}% | {row['tokens']:.2f} | "
                     f"{fmt(row['delta'], 3)}{ci} | {100 * row['lift']:+.2f} |")
    lines += ["", "## Table 2 (refit-inclusive intervals)", "",
              "| Contrast | Point | Fixed actions | With refitting | Fold repartitions |",
              "|---|---:|---|---|---|"]
    for name, row in results["table2"].items():
        lines.append(f"| {name} | {fmt(row['point'], 3)} | {fmt(row['fixed'], 3)} | "
                     f"{fmt(row['refit'], 3)} | {fmt(row['repartition'], 3)} |")
    if failed:
        lines += ["", "## Mismatches", "", "| Group | Item | Field | Actual | Expected |",
                  "|---|---|---|---|---|"]
        for c in failed:
            lines.append(f"| {c['group']} | {c['item']} | {c['field']} | {fmt(c['actual'])} | "
                         f"{fmt(c['expected'])} |")
    if skipped:
        lines += ["", "Refit-inclusive and repartition columns were skipped (`--skip-refit`)."]
    return "\n".join(lines) + "\n"


def check(cache, output, processes=1, skip_refit=False, figure=FIGURE_MANIFEST, expected=None):
    """`expected` = (table1, table2, text); defaults to the published values."""
    output = Path(output)
    if (output / "reproduction.json").exists():
        raise FileExistsError(f"Reproduction already written in {output}; choose --output")
    payload = load_cache(cache)
    repeat, two_solver, families = arrays(payload)
    results = recompute(repeat, two_solver, families, processes, skip_refit)
    table1, table2, text = expected or (TABLE1, TABLE2, TEXT)
    checks = compare(results, table1, table2, text,
                     figure=figure_values(figure) if figure else None)
    cache_sha256 = file_hash(cache)
    report = {"cache_sha256": cache_sha256, "cache_payload_sha256": digest(payload),
              "results": results, "checks": checks,
              "passed": all(c["passed"] for c in checks),
              "no_generation_scoring_references": True}
    output.mkdir(parents=True, exist_ok=True)
    with (output / "reproduction.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False, default=float)
        stream.write("\n")
    with (output / "reproduction.md").open("x") as stream:
        stream.write(markdown(results, checks, cache_sha256))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    e = sub.add_parser("export", help="write the cache from the completed studies")
    e.add_argument("--output", type=Path, default=DEFAULT_CACHE)
    c = sub.add_parser("check", help="rebuild the published numbers from the cache")
    c.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    c.add_argument("--output", type=Path, default=Path("reproduction-output"))
    c.add_argument("--processes", type=int, default=min(4, os.cpu_count() or 1))
    c.add_argument("--skip-refit", action="store_true",
                   help="skip the 2,000-resample refit bootstrap (Table 2 refit columns)")
    args = parser.parse_args()
    if args.command == "export":
        print(json.dumps(export(args.output), indent=2))
        return
    report = check(args.cache, args.output, args.processes, args.skip_refit)
    failed = [c for c in report["checks"] if not c["passed"]]
    print(f"{len(report['checks'])} checks, {len(failed)} failed; "
          f"see {args.output / 'reproduction.md'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
