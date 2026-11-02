"""Render the short paper's accuracy–cost figure from the tracked report only.

Reads docs/deferral-curves-report.md (pinned by SHA-256), extracts the reported
points, and writes PDF/SVG/PNG plus a manifest. No study data, score cache, or
reference is read, and no value is re-estimated.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / "docs/deferral-curves-report.md"
REPORT_SHA256 = "92863d455eeeb03092dc1974835768b1e732ec5af347ad25dc2f52ec396b8316"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
NAME = "figure-1-accuracy-cost"
LAMBDA_GRID = [0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3]
PANELS = (("repeat_qwen3_1.7b", "A. Repeat panel, Qwen3-1.7B"),
          ("two_solver_qwen3_0.6b", "B. Two-solver panel, Qwen3-0.6B"),
          ("two_solver_qwen3_1.7b", "C. Two-solver panel, Qwen3-1.7B"))
STYLE = {"surface": "#ffffff", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e3df",
         "confidence": "#2a78d6", "combined": "#eb6834", "other": "#9a9893"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(text):
    text = text.strip().replace("−", "-").replace(",", "")
    return float(text[:-1]) / 100 if text.endswith("%") else float(text)


def section(text, name):
    start = text.index(f"### {name}\n")
    ends = [i for i in (text.find("\n### ", start + 1), text.find("\n## ", start + 1)) if i != -1]
    return text[start:min(ends)]


def rows(block):
    return [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in block.splitlines() if line.startswith("| ") and "---" not in line]


def extract(text):
    data = {}
    for key, _ in PANELS:
        block = section(text, key)
        table = rows(block.split("λ sweep")[0])
        points = {r[0]: {"accuracy": number(r[1]), "tokens": number(r[2])}
                  for r in table[1:]}
        sweep_rows = rows(block.split("λ sweep")[1])[1:]
        sweep = []
        for r in sweep_rows:
            acc, tok = (number(x) for x in r[1].split("/"))
            item = {"lambda": float(r[0]), "confidence": {"accuracy": acc, "tokens": tok}}
            if key.startswith("repeat"):
                acc, tok = (number(x) for x in r[2].split("/"))
                item["combined"] = {"accuracy": acc, "tokens": tok}
            sweep.append(item)
        if [s["lambda"] for s in sweep] != LAMBDA_GRID:
            raise ValueError(f"Unexpected λ grid in {key}")
        data[key] = {"points": points, "sweep": sweep}
    agreement = next(r for r in rows(text.split("## C. Two-draft agreement baseline")[1])
                     if r[0] == "repeat_qwen3_1.7b")
    data["repeat_qwen3_1.7b"]["points"]["two_draft_agreement (simulated)"] = {
        "accuracy": number(agreement[1]), "tokens": number(agreement[2])}
    return data


def check(data):
    repeat = data["repeat_qwen3_1.7b"]["points"]
    expected = {"always_direct": (0.895, 221.14), "always_escalate": (0.945, 1610.97),
                "oracle": (0.97, 342.02), "confidence": (0.9275, 628.47),
                "combined": (0.89, 757.13)}
    for name, (acc, tok) in expected.items():
        if abs(repeat[name]["accuracy"] - acc) > 1e-9 or abs(repeat[name]["tokens"] - tok) > 1e-9:
            raise ValueError(f"Unexpected reported value: {name}")
    if len(repeat) != 20:
        raise ValueError(f"Expected 20 repeat-panel points, found {len(repeat)}")
    for key, _ in PANELS:
        at05 = next(s for s in data[key]["sweep"] if s["lambda"] == 0.05)["confidence"]
        point = data[key]["points"]["confidence"]
        if (abs(at05["accuracy"] - point["accuracy"]) > 0.0005
                or abs(at05["tokens"] - point["tokens"]) > 0.05):
            raise ValueError(f"λ=.05 sweep point differs from policy table: {key}")


def draw(data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                         "axes.edgecolor": STYLE["ink2"], "axes.labelcolor": STYLE["ink"],
                         "xtick.color": STYLE["ink2"], "ytick.color": STYLE["ink2"],
                         "svg.hashsalt": "deferral-curves-v1", "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.75), facecolor=STYLE["surface"])
    for ax, (key, title) in zip(axes, PANELS):
        panel = data[key]
        pts = panel["points"]
        ax.set_facecolor(STYLE["surface"])
        ax.grid(True, color=STYLE["grid"], linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        d, e, o = pts["always_direct"], pts["always_escalate"], pts["oracle"]
        ax.plot([d["tokens"], e["tokens"]], [100 * d["accuracy"], 100 * e["accuracy"]],
                color=STYLE["ink2"], linewidth=1.0, linestyle=(0, (4, 3)), zorder=2,
                label="Random escalation at equal cost")
        if key.startswith("repeat"):
            for name, p in pts.items():
                if name in {"always_direct", "always_escalate", "oracle", "confidence",
                            "combined", "accept", "escalate"}:
                    continue
                ax.plot(p["tokens"], 100 * p["accuracy"], "o", markersize=3.6,
                        color=STYLE["other"], markeredgecolor=STYLE["surface"],
                        markeredgewidth=0.6, zorder=3,
                        label="Other tested rules, λ=.05" if name == "question_only" else None)
                if name.startswith("two_draft_agreement"):
                    ax.annotate("Two-draft agreement", (p["tokens"], 100 * p["accuracy"]),
                                xytext=(60, 95.4), textcoords="data", ha="left", va="center",
                                color=STYLE["ink2"], fontsize=6.2,
                                arrowprops={"arrowstyle": "-", "color": STYLE["ink2"],
                                            "linewidth": 0.6, "shrinkA": 1, "shrinkB": 1.5})
            series = (("combined", STYLE["combined"], "Combined learner (refitted per λ)"),
                      ("confidence", STYLE["confidence"], "Confidence (refitted per λ)"))
        else:
            series = (("confidence", STYLE["confidence"], "Confidence (refitted per λ)"),)
        for name, color, label in series:
            xs = [s[name]["tokens"] for s in panel["sweep"]]
            ys = [100 * s[name]["accuracy"] for s in panel["sweep"]]
            ax.plot(xs, ys, "-", color=color, linewidth=1.5, zorder=4, label=label)
            ax.plot(xs, ys, "o", markersize=3.2, color=color, markeredgecolor=STYLE["surface"],
                    markeredgewidth=0.6, zorder=5)
            p = pts[name]
            ax.plot(p["tokens"], 100 * p["accuracy"], "o", markersize=6.5, color=color,
                    markeredgecolor=STYLE["surface"], markeredgewidth=1.2, zorder=6)
        ax.plot([d["tokens"], e["tokens"]], [100 * d["accuracy"], 100 * e["accuracy"]], "D",
                markersize=4.6, color=STYLE["ink"], markeredgecolor=STYLE["surface"],
                markeredgewidth=0.8, zorder=6, label="Always direct (left), always think (right)")
        ax.plot(o["tokens"], 100 * o["accuracy"], "s", markersize=5, color=STYLE["ink"],
                markeredgecolor=STYLE["surface"], markeredgewidth=0.8, zorder=6,
                label="Hindsight oracle")
        ax.set_title(title, loc="left", fontsize=7.8, color=STYLE["ink"], pad=4)
        ax.set_xlabel("Output tokens per state")
        ax.set_xlim(0, 1750)
        low = min(100 * d["accuracy"], min(100 * s["confidence"]["accuracy"]
                                            for s in panel["sweep"]))
        ax.set_ylim(low - 2.5, 100 * o["accuracy"] + 1.5)
    axes[0].set_ylabel("Scored accuracy (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    order = ["Confidence (refitted per λ)", "Combined learner (refitted per λ)",
             "Other tested rules, λ=.05", "Random escalation at equal cost",
             "Always direct (left), always think (right)", "Hindsight oracle"]
    by_label = dict(zip(labels, handles))
    fig.legend([by_label[k] for k in order], order, loc="lower center", ncol=3, frameon=False,
               fontsize=6.8, bbox_to_anchor=(0.5, -0.03), labelcolor=STYLE["ink"])
    fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=1.2)
    OUTPUT.mkdir(exist_ok=True)
    paths = {}
    for ext in ("pdf", "svg", "png"):
        (OUTPUT / ext).mkdir(exist_ok=True)
        path = OUTPUT / ext / f"{NAME}.{ext}"
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite completed export: {path}")
        kwargs = {"dpi": 300} if ext == "png" else {"metadata": {"CreationDate": None}
                                                    if ext == "pdf" else {"Date": None}}
        fig.savefig(path, facecolor=STYLE["surface"], bbox_inches="tight", **kwargs)
        paths[ext] = str(path.relative_to(ROOT))
    return paths


def main():
    if sha256(REPORT) != REPORT_SHA256:
        raise SystemExit("Report changed since the display plan was frozen")
    data = extract(REPORT.read_text())
    check(data)
    if "--check" in sys.argv:
        print(json.dumps({k: len(v["points"]) for k, v in data.items()}))
        return
    paths = draw(data)
    manifest = {"report": str(REPORT.relative_to(ROOT)), "report_sha256": REPORT_SHA256,
                "renderer_sha256": sha256(__file__),
                "plan_sha256": sha256(HERE / "plan.md"), "values": data,
                "outputs": {ext: {"path": p, "sha256": sha256(ROOT / p)}
                            for ext, p in paths.items()}}
    with (OUTPUT / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(json.dumps(manifest["outputs"], indent=2))


if __name__ == "__main__":
    main()
