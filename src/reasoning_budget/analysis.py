"""Pilot analysis: headroom, decision relevance, budgets, confidence, and projections."""

import collections
import math
from pathlib import Path

import numpy as np

from .data import load_gold
from .reporting import paired_statistics, score_run
from .runner import load_run
from .scoring import _boxes, numeric
from .storage import atomic_json

# Full programme per model as (questions, responses per mode). Each response unit
# is one direct and one thinking generation; the training cache is 400 × 8 pairs.
PROGRAMME = {
    "training_cache": (400, 8),
    "validation": (100, 2),
    "gsm8k_test": (500, 2),
    "svamp": (500, 2),
    "procedural": (500, 2),
}
FORCED_CLOSURE_GATE = 0.05
POWER_N = 500
# Two-sided alpha 0.05 at 80% power: (1.96 + 0.84) standard errors.
POWER_MULTIPLIER = 2.8


def _dist(values):
    if not values:
        return None
    a = np.asarray(values, dtype=float)
    return {
        "mean": float(a.mean()),
        "p50": float(np.quantile(a, 0.5)),
        "p90": float(np.quantile(a, 0.9)),
        "max": float(a.max()),
    }


def _bare_number(text):
    try:
        numeric(text)
        return True
    except ValueError:
        return False


def _confidence(rows, scores):
    from sklearn.metrics import roc_auc_score

    out = {}
    for key in ["mean_generated_logprob", "mean_generated_logprob_raw"]:
        pairs = [
            (r["result"].get(key), scores[r["job"]["id"]]["correct"])
            for r in rows
            if r["result"].get(key) is not None
        ]
        labels = [c for _, c in pairs]
        entry = {"n": len(pairs), "auroc": None, "mean_correct": None, "mean_incorrect": None}
        if pairs:
            correct = [v for v, c in pairs if c]
            incorrect = [v for v, c in pairs if not c]
            entry["mean_correct"] = float(np.mean(correct)) if correct else None
            entry["mean_incorrect"] = float(np.mean(incorrect)) if incorrect else None
            if len(set(labels)) == 2:
                entry["auroc"] = float(roc_auc_score(labels, [v for v, _ in pairs]))
        out[key] = entry
    both = [
        (r["result"].get("mean_generated_logprob"), r["result"].get("mean_generated_logprob_raw"))
        for r in rows
    ]
    both = [(w, raw) for w, raw in both if w is not None and raw is not None]
    out["raw_not_above_post_warper_fraction"] = (
        sum(raw <= w + 1e-9 for w, raw in both) / len(both) if both else None
    )
    return out


def analyze(run_dir, cloud_tokens_per_second=None, four_b_slowdown=2.5, hourly_rate=None):
    run_dir = Path(run_dir)
    manifest, records = load_run(run_dir)
    artifact = score_run(run_dir)
    scores = {s["job_id"]: s for s in artifact["scores"]}
    config = manifest["identity"]["config"]
    gold = load_gold(config["data_dir"])
    modes, samples = config["modes"], config["samples"]
    complete = [r for r in records if r["status"] == "completed"]
    by_mode = {m: [r for r in complete if r["job"]["mode"] == m] for m in modes}

    mode_stats = {}
    for mode, rows in by_mode.items():
        results = [r["result"] for r in rows]
        mode_scores = [scores[r["job"]["id"]] for r in rows]
        n = len(rows)
        untruncated = [s for r, s in zip(results, mode_scores) if not r["answer_truncated"]]
        generated = [
            r["reasoning_tokens"] + r["inserted_tokens"] + r["answer_tokens"] for r in results
        ]
        elapsed = sum(r["elapsed_seconds"] for r in results)
        mode_stats[mode] = {
            "completed": n,
            "planned": sum(r["job"]["mode"] == mode for r in records),
            "accuracy": sum(s["correct"] for s in mode_scores) / n if n else None,
            "untruncated": len(untruncated),
            "accuracy_untruncated": (
                sum(s["correct"] for s in untruncated) / len(untruncated) if untruncated else None
            ),
            "answer_truncated": sum(r["answer_truncated"] for r in results),
            "forced_closure": sum(r["forced_closure"] for r in results),
            "forced_closure_rate": sum(r["forced_closure"] for r in results) / n if n else None,
            "termination": dict(collections.Counter(r["termination"] for r in results)),
            "parser_status": dict(collections.Counter(s["parser_status"] for s in mode_scores)),
            "reasoning_tokens": _dist([r["reasoning_tokens"] for r in results]),
            "answer_tokens": _dist([r["answer_tokens"] for r in results]),
            "generated_tokens": _dist(generated),
            "elapsed_seconds": _dist([r["elapsed_seconds"] for r in results]),
            "tokens_per_second": sum(generated) / elapsed if elapsed else None,
        }
    thinking_rate = mode_stats.get("thinking", {}).get("forced_closure_rate")
    gate = {
        "forced_closure_rate": thinking_rate,
        "gate": FORCED_CLOSURE_GATE,
        "passes": thinking_rate is not None and thinking_rate <= FORCED_CLOSURE_GATE,
        "reasoning_tokens": config["reasoning_tokens"],
    }

    per_question = {}
    for r in complete:
        per_question.setdefault(r["job"]["question_id"], {}).setdefault(
            r["job"]["mode"], []
        ).append(float(scores[r["job"]["id"]]["correct"]))
    full = {
        q: m
        for q, m in per_question.items()
        if all(len(m.get(mode, [])) == samples for mode in modes)
    }
    headroom = {"questions_with_all_samples": len(full)}
    power = None
    if full and {"direct", "thinking"} <= set(modes):
        matrix = collections.Counter(
            (int(sum(m["direct"])), int(sum(m["thinking"]))) for m in full.values()
        )
        means = [
            (float(np.mean(m["direct"])), float(np.mean(m["thinking"]))) for m in full.values()
        ]
        diffs = [t - d for d, t in means]
        thinking_better = int(sum(t > d for d, t in means))
        direct_better = int(sum(d > t for d, t in means))
        headroom.update(
            {
                "outcome_matrix": [
                    {"direct_correct": d, "thinking_correct": t, "questions": c}
                    for (d, t), c in sorted(matrix.items())
                ],
                "always_direct_accuracy": float(np.mean([d for d, _ in means])),
                "always_thinking_accuracy": float(np.mean([t for _, t in means])),
                "oracle_best_mode_accuracy": float(np.mean([max(d, t) for d, t in means])),
                "thinking_better_questions": thinking_better,
                "direct_better_questions": direct_better,
                "decision_relevant_fraction": (thinking_better + direct_better) / len(full),
                "both_always_correct": int(sum(d == 1 and t == 1 for d, t in means)),
                "both_always_wrong": int(sum(d == 0 and t == 0 for d, t in means)),
                "sample_disagreement": {
                    mode: float(sum(len(set(m[mode])) > 1 for m in full.values()) / len(full))
                    for mode in modes
                },
                "paired": paired_statistics(records, artifact["scores"], samples, config["seed"]),
            }
        )
        if len(diffs) > 1:
            sd = float(np.std(diffs, ddof=1))
            se = sd / math.sqrt(POWER_N)
            power = {
                "per_question_difference_sd": sd,
                "questions": POWER_N,
                "standard_error": se,
                "minimum_detectable_difference_80_power": POWER_MULTIPLIER * se,
                "note": (
                    "Upper bound: policies that agree on most questions have a smaller "
                    "paired-difference SD than thinking versus direct."
                ),
            }

    confidence = _confidence(by_mode.get("direct", []), scores) if "direct" in modes else None

    projection = None
    if all(mode_stats[m]["tokens_per_second"] for m in modes) and all(
        mode_stats[m]["generated_tokens"] for m in modes
    ):
        mean_tokens = {m: mode_stats[m]["generated_tokens"]["mean"] for m in modes}
        seconds_each = {m: mean_tokens[m] / mode_stats[m]["tokens_per_second"] for m in modes}
        components = {}
        for name, (questions, per_mode) in PROGRAMME.items():
            n = questions * per_mode
            tokens = n * sum(mean_tokens.values())
            local = n * sum(seconds_each.values())
            components[name] = {
                "responses_per_mode": n,
                "tokens": tokens,
                "local_hours_small": local / 3600,
                "local_hours_large_assumed": local * four_b_slowdown / 3600,
                "cloud_hours_small": (
                    tokens / cloud_tokens_per_second / 3600 if cloud_tokens_per_second else None
                ),
                "cloud_hours_large_assumed": (
                    tokens * four_b_slowdown / cloud_tokens_per_second / 3600
                    if cloud_tokens_per_second
                    else None
                ),
            }
        totals = {
            key: sum(c[key] for c in components.values())
            for key in [
                "tokens",
                "local_hours_small",
                "local_hours_large_assumed",
            ]
        }
        if cloud_tokens_per_second:
            totals["cloud_hours_small"] = sum(c["cloud_hours_small"] for c in components.values())
            totals["cloud_hours_large_assumed"] = sum(
                c["cloud_hours_large_assumed"] for c in components.values()
            )
            if hourly_rate is not None:
                totals["cloud_cost_scenario_usd"] = (
                    totals["cloud_hours_small"] + totals["cloud_hours_large_assumed"]
                ) * hourly_rate
        projection = {
            "basis": "observed mean generated tokens and tokens/second per mode in this run",
            "large_model_slowdown_assumption": four_b_slowdown,
            "cloud_tokens_per_second_scenario": cloud_tokens_per_second,
            "hourly_rate_scenario_usd": hourly_rate,
            "components": components,
            "totals": totals,
            "scope": "generation only; excludes setup, idle time, retries and analysis",
        }

    prescreen = {"parser_failures": [], "decorated_boxes": [], "truncated": {}}
    for mode in modes:
        prescreen["truncated"][mode] = mode_stats[mode]["answer_truncated"]
    for r in complete:
        s = scores[r["job"]["id"]]
        final = r["result"]["final_answer"]
        qid = r["job"]["question_id"]
        if s["parser_status"] not in {"ok", "incomplete"}:
            prescreen["parser_failures"].append(
                {
                    "job_id": r["job"]["id"],
                    "mode": r["job"]["mode"],
                    "status": s["parser_status"],
                    "gold": gold[qid],
                    "tail": final[-200:],
                }
            )
        elif s["parser_status"] == "ok":
            boxes, _ = _boxes(final)
            decorated = [b for b in boxes if not _bare_number(b)]
            if decorated:
                prescreen["decorated_boxes"].append(
                    {
                        "job_id": r["job"]["id"],
                        "mode": r["job"]["mode"],
                        "boxes": decorated[:3],
                        "extracted": s["extracted_answer"],
                        "gold": gold[qid],
                        "correct": s["correct"],
                    }
                )

    result = {
        "run_id": manifest["run_id"],
        "scoring_version": artifact["scoring_version"],
        "complete": all(r["status"] == "completed" for r in records),
        "modes": mode_stats,
        "forced_closure_gate": gate,
        "headroom": headroom,
        "power": power,
        "confidence": confidence,
        "projection": projection,
        "prescreen": prescreen,
    }
    out = run_dir / "report"
    out.mkdir(exist_ok=True)
    atomic_json(out / "analysis.json", result)
    (out / "analysis.md").write_text(_markdown(config, result))
    return out


def _fmt(value, kind="f"):
    if value is None:
        return "n/a"
    if kind == "%":
        return f"{value:.1%}"
    if kind == "i":
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _markdown(config, result):
    lines = [
        f"# Analysis: {config['name']}",
        "",
        f"Run `{result['run_id']}`; scorer `{result['scoring_version']}`; complete: {result['complete']}.",
        "",
        "## Modes",
        "",
        "| Mode | Completed | Accuracy | Untruncated | Accuracy untruncated | Truncated | Forced closure | Generated tokens mean / p90 / max | Seconds mean / p90 | Tokens per second |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, s in result["modes"].items():
        g, e = s["generated_tokens"] or {}, s["elapsed_seconds"] or {}
        lines.append(
            f"| {mode} | {s['completed']} / {s['planned']} | {_fmt(s['accuracy'], '%')} | {s['untruncated']} | "
            f"{_fmt(s['accuracy_untruncated'], '%')} | {s['answer_truncated']} | {s['forced_closure']} | "
            f"{_fmt(g.get('mean'), 'i')} / {_fmt(g.get('p90'), 'i')} / {_fmt(g.get('max'), 'i')} | "
            f"{_fmt(e.get('mean'))} / {_fmt(e.get('p90'))} | {_fmt(s['tokens_per_second'])} |"
        )
    for mode, s in result["modes"].items():
        lines += [
            "",
            f"{mode}: termination {s['termination']}; parser {s['parser_status']}.",
        ]
    gate = result["forced_closure_gate"]
    lines += [
        "",
        "## Forced-closure gate",
        "",
        f"Thinking forced closure at {gate['reasoning_tokens']} reasoning tokens: "
        f"{_fmt(gate['forced_closure_rate'], '%')} against a {gate['gate']:.0%} gate; "
        f"passes: {gate['passes']}.",
    ]
    h = result["headroom"]
    if "outcome_matrix" in h:
        lines += [
            "",
            "## Headroom and decision relevance",
            "",
            f"Questions with every sample in both modes: {h['questions_with_all_samples']}.",
            "",
            "| Direct correct of n | Thinking correct of n | Questions |",
            "|---:|---:|---:|",
        ]
        for row in h["outcome_matrix"]:
            lines.append(
                f"| {row['direct_correct']} | {row['thinking_correct']} | {row['questions']} |"
            )
        lines += [
            "",
            f"Always direct {_fmt(h['always_direct_accuracy'], '%')}; always thinking "
            f"{_fmt(h['always_thinking_accuracy'], '%')}; oracle best mode per question "
            f"{_fmt(h['oracle_best_mode_accuracy'], '%')} (optimistic, chosen on the same samples).",
            "",
            f"Thinking better on {h['thinking_better_questions']} questions; direct better on "
            f"{h['direct_better_questions']}; decision-relevant fraction "
            f"{_fmt(h['decision_relevant_fraction'], '%')}; both always correct "
            f"{h['both_always_correct']}; both always wrong {h['both_always_wrong']}.",
            "",
            f"Within-mode sample disagreement: {h['sample_disagreement']}.",
            "",
            f"Paired thinking minus direct: {_fmt(h['paired']['thinking_minus_direct_accuracy'])} "
            f"with whole-question bootstrap 95% interval {h['paired']['ci95']}.",
        ]
    if result["power"]:
        p = result["power"]
        lines += [
            "",
            "## Power",
            "",
            f"Per-question paired-difference SD {_fmt(p['per_question_difference_sd'])}; at "
            f"{p['questions']} test questions the standard error is {_fmt(p['standard_error'])} and the "
            f"minimum detectable difference at 80% power is {_fmt(p['minimum_detectable_difference_80_power'])} "
            f"accuracy points (fraction). {p['note']}",
        ]
    if result["confidence"]:
        lines += ["", "## Direct-mode confidence", ""]
        for key, c in result["confidence"].items():
            if isinstance(c, dict):
                lines.append(
                    f"- `{key}`: n={c['n']}, AUROC {_fmt(c['auroc'])}, mean when correct "
                    f"{_fmt(c['mean_correct'])}, when incorrect {_fmt(c['mean_incorrect'])}."
                )
            else:
                lines.append(
                    f"- raw log-probability not above post-warper: {_fmt(c, '%')} of rows."
                )
    if result["projection"]:
        pr = result["projection"]
        lines += [
            "",
            "## Programme projection",
            "",
            f"Basis: {pr['basis']}. Large-model slowdown assumed {pr['large_model_slowdown_assumption']}×. "
            f"Cloud scenario: {pr['cloud_tokens_per_second_scenario']} tokens/s.",
            "",
            "| Component | Responses per mode | Tokens | Local hours small | Local hours large | Cloud hours small | Cloud hours large |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for name, c in pr["components"].items():
            lines.append(
                f"| {name} | {c['responses_per_mode']:,} | {_fmt(c['tokens'], 'i')} | "
                f"{_fmt(c['local_hours_small'])} | {_fmt(c['local_hours_large_assumed'])} | "
                f"{_fmt(c['cloud_hours_small'])} | {_fmt(c['cloud_hours_large_assumed'])} |"
            )
        t = pr["totals"]
        lines += [
            "",
            f"Totals: {_fmt(t['tokens'], 'i')} tokens per model; local {_fmt(t['local_hours_small'])} h small "
            f"and {_fmt(t['local_hours_large_assumed'])} h large; cloud "
            f"{_fmt(t.get('cloud_hours_small'))} h small and {_fmt(t.get('cloud_hours_large_assumed'))} h large; "
            f"cost scenario {_fmt(t.get('cloud_cost_scenario_usd'))} USD. {pr['scope']}.",
        ]
    ps = result["prescreen"]
    lines += [
        "",
        "## Scorer pre-screen",
        "",
        f"Truncated answers per mode: {ps['truncated']}. Parser failures other than truncation: "
        f"{len(ps['parser_failures'])}. Boxes that needed LaTeX cleaning: {len(ps['decorated_boxes'])}.",
    ]
    for row in ps["parser_failures"][:50]:
        lines.append(
            f"- {row['mode']} `{row['job_id'][:12]}` {row['status']} gold={row['gold']}: "
            f"`{row['tail'][-120:]!r}`"
        )
    for row in ps["decorated_boxes"][:50]:
        lines.append(
            f"- {row['mode']} `{row['job_id'][:12]}` boxes={row['boxes']} extracted={row['extracted']} "
            f"gold={row['gold']} correct={row['correct']}"
        )
    return "\n".join(lines) + "\n"
