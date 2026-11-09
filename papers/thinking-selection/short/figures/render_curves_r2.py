"""Render revision 2 of the short paper's accuracy-cost figure (presentation only).

Same source and values as the frozen first export: it reuses the frozen parser and
checks in render_curves.py, reads only docs/deferral-curves-report.md (pinned by
SHA-256), and refuses to draw unless every value equals the first export's
manifest. Changes are visual: tighter axes with the oracle marked off scale,
direct labels, distinguishable reference rules, and current names.

    python render_curves_r2.py --preview DIR   # draft images, no manifest
    python render_curves_r2.py                 # the one export, into output-r2/
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render_curves import REPORT, REPORT_SHA256, ROOT, check, extract, sha256  # noqa: E402

FIRST_MANIFEST = HERE / "output" / "manifest.json"
OUTPUT = HERE / "output-r2"
NAME = "figure-1-accuracy-cost-r2"
PANELS = (
    ("repeat_qwen3_1.7b", "A  Main panel, Qwen3-1.7B", "50 questions × 8 draws",
     (87.4, 95.6), (0, 1750)),
    ("two_solver_qwen3_0.6b", "B  Two-solver panel, Qwen3-0.6B", "64 questions × 2 draws",
     (59.0, 84.5), (0, 1500)),
    ("two_solver_qwen3_1.7b", "C  Two-solver panel, Qwen3-1.7B", "64 questions × 2 draws",
     (82.0, 88.6), (0, 1700)),
)
STYLE = {"surface": "#ffffff", "ink": "#0b0b0b", "ink2": "#52514e", "ink3": "#7d7b76",
         "grid": "#e9e8e4", "confidence": "#2a78d6", "learner": "#eb6834",
         "other": "#8f8d88"}
REFERENCE_NAMES = {"always_direct", "always_escalate", "oracle", "confidence", "combined",
                   "accept", "escalate"}


def load():
    if sha256(REPORT) != REPORT_SHA256:
        raise SystemExit("Report changed since the display plan was frozen")
    data = extract(REPORT.read_text())
    check(data)
    first = json.loads(FIRST_MANIFEST.read_text())["values"]
    if data != first:
        raise SystemExit("Values differ from the first export's manifest")
    return data


def angle(ax, p, q):
    a, b = ax.transData.transform(p), ax.transData.transform(q)
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def curve(ax, sweep, name, color):
    xs = [s[name]["tokens"] for s in sweep]
    ys = [100 * s[name]["accuracy"] for s in sweep]
    ax.plot(xs, ys, "-", color=color, linewidth=1.6, zorder=4, solid_capstyle="round")
    ax.plot(xs, ys, "o", markersize=3.0, color=color, markeredgecolor=STYLE["surface"],
            markeredgewidth=0.5, zorder=5)
    return xs, ys


def draw(data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.4,
                         "axes.edgecolor": STYLE["ink2"], "axes.labelcolor": STYLE["ink"],
                         "xtick.color": STYLE["ink2"], "ytick.color": STYLE["ink2"],
                         "xtick.labelsize": 6.8, "ytick.labelsize": 6.8,
                         "axes.linewidth": 0.7, "xtick.major.width": 0.7,
                         "ytick.major.width": 0.7, "svg.hashsalt": "deferral-curves-r2",
                         "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.55), facecolor=STYLE["surface"])
    fig.subplots_adjust(left=0.075, right=0.99, top=0.82, bottom=0.30, wspace=0.26)
    for ax, (key, title, subtitle, ylim, xlim) in zip(axes, PANELS):
        panel, pts = data[key], data[key]["points"]
        ax.set_facecolor(STYLE["surface"])
        ax.grid(True, axis="y", color=STYLE["grid"], linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        d, e, o = pts["always_direct"], pts["always_escalate"], pts["oracle"]
        dp, ep = (d["tokens"], 100 * d["accuracy"]), (e["tokens"], 100 * e["accuracy"])
        ax.plot(*zip(dp, ep), color=STYLE["ink3"], linewidth=1.0, linestyle=(0, (4, 3)),
                zorder=2)
        # Off-scale oracle: marker on the top edge with its value.
        ax.plot(o["tokens"], ylim[1], "^", markersize=5.2, color=STYLE["ink"], clip_on=False,
                zorder=7)
        ax.annotate(f"Oracle {100 * o['accuracy']:.1f}%", (o["tokens"], ylim[1]),
                    xytext=(5, -1), textcoords="offset points", ha="left", va="top",
                    fontsize=6.4, color=STYLE["ink"], annotation_clip=False)
        if key.startswith("repeat"):
            for name, p in pts.items():
                if name in REFERENCE_NAMES:
                    continue
                ax.plot(p["tokens"], 100 * p["accuracy"], "o", markersize=3.8,
                        markerfacecolor=STYLE["surface"], markeredgecolor=STYLE["other"],
                        markeredgewidth=0.9, zorder=3)
            agree = pts["two_draft_agreement (simulated)"]
            ax.annotate("Two-draft\nagreement", (agree["tokens"], 100 * agree["accuracy"]),
                        xytext=(1000, 90.95), ha="left", va="center", fontsize=6.2,
                        color=STYLE["ink2"], linespacing=0.95,
                        arrowprops={"arrowstyle": "-", "color": STYLE["ink3"],
                                    "linewidth": 0.6, "shrinkA": 0, "shrinkB": 2.5})
            clm = pts["released_clm_zero_shot (Table 3, reported)"]
            ax.annotate("Zero-shot CLM", (clm["tokens"], 100 * clm["accuracy"]),
                        xytext=(-5, 0), textcoords="offset points", ha="right",
                        va="center", fontsize=6.2, color=STYLE["ink2"])
            xs, ys = curve(ax, panel["sweep"], "combined", STYLE["learner"])
            ax.text(1080, 88.15, "Predeclared\nlearner", color=STYLE["learner"], fontsize=6.8,
                    fontweight="bold", ha="left", va="center", linespacing=0.95)
            ax.text(xs[0] + 25, ys[0], "λ=0", color=STYLE["learner"], fontsize=6.0,
                    ha="left", va="center")
            p = pts["combined"]
            ax.plot(p["tokens"], 100 * p["accuracy"], "o", markersize=6.2,
                    color=STYLE["learner"], markeredgecolor=STYLE["surface"],
                    markeredgewidth=1.1, zorder=6)
        xs, ys = curve(ax, panel["sweep"], "confidence", STYLE["confidence"])
        p = pts["confidence"]
        ax.plot(p["tokens"], 100 * p["accuracy"], "o", markersize=6.2,
                color=STYLE["confidence"], markeredgecolor=STYLE["surface"],
                markeredgewidth=1.1, zorder=6)
        ax.text(xs[0] + 25, ys[0], "λ=0", color=STYLE["confidence"], fontsize=6.0,
                ha="left", va="center" if key != "two_solver_qwen3_0.6b" else "bottom")
        label_at = {"repeat_qwen3_1.7b": (600, 93.45, "center"),
                    "two_solver_qwen3_0.6b": (690, 78.9, "right"),
                    "two_solver_qwen3_1.7b": (700, 82.45, "left")}[key]
        ax.text(label_at[0], label_at[1], "Confidence", color=STYLE["confidence"],
                fontsize=6.8, fontweight="bold", ha=label_at[2], va="center")
        ax.plot(*zip(dp, ep), "D", markersize=4.4, color=STYLE["ink"],
                markeredgecolor=STYLE["surface"], markeredgewidth=0.7, zorder=6, clip_on=False)
        # Direct label on the random-escalation line.
        t = {"repeat_qwen3_1.7b": 0.80, "two_solver_qwen3_0.6b": 0.66,
             "two_solver_qwen3_1.7b": 0.66}[key]
        mid = (dp[0] + t * (ep[0] - dp[0]), dp[1] + t * (ep[1] - dp[1]))
        ax.text(mid[0], mid[1], "random", rotation=angle(ax, dp, ep),
                rotation_mode="anchor", ha="center", va="bottom", fontsize=6.0,
                color=STYLE["ink3"], transform_rotates_text=False)
        ax.set_title(title, loc="left", fontsize=7.6, color=STYLE["ink"], pad=13,
                     fontweight="bold")
        ax.text(0, 1.045, subtitle, transform=ax.transAxes, fontsize=6.4, color=STYLE["ink3"],
                ha="left", va="bottom")
    axes[0].set_ylabel("Scored accuracy (%)")
    fig.supxlabel("Output tokens per state (draft included)", fontsize=7.2, y=0.155,
                  color=STYLE["ink"])
    handles = [
        Line2D([], [], color=STYLE["ink2"], marker="o", markersize=3, linewidth=1.4),
        Line2D([], [], color=STYLE["ink2"], marker="o", markersize=6, linewidth=0,
               markeredgecolor=STYLE["surface"]),
        Line2D([], [], color=STYLE["other"], marker="o", markersize=3.8, linewidth=0,
               markerfacecolor=STYLE["surface"], markeredgewidth=0.9),
        Line2D([], [], color=STYLE["ink3"], linewidth=1.0, linestyle=(0, (4, 3))),
        Line2D([], [], color=STYLE["ink"], marker="D", markersize=4.2, linewidth=0),
        Line2D([], [], color=STYLE["ink"], marker="^", markersize=5, linewidth=0),
    ]
    labels = ["Refitted at each λ from 0 to 0.3", "λ = 0.05, the primary cost",
              "Other rules in Table 1 at λ = 0.05", "Random escalation at equal cost",
              "Always direct (left), always think (right)", "Hindsight oracle, off scale"]
    order = [0, 3, 1, 4, 2, 5]
    fig.legend([handles[i] for i in order], [labels[i] for i in order], loc="lower center",
               ncol=3, frameon=False, fontsize=6.5, bbox_to_anchor=(0.53, -0.01),
               handletextpad=0.5, columnspacing=1.6, labelcolor=STYLE["ink"])
    return fig


def save(fig, directory, overwrite):
    paths = {}
    for ext in ("pdf", "svg", "png"):
        (directory / ext).mkdir(parents=True, exist_ok=True)
        path = directory / ext / f"{NAME}.{ext}"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite completed export: {path}")
        kwargs = {"dpi": 300} if ext == "png" else {"metadata": {"CreationDate": None}
                                                    if ext == "pdf" else {"Date": None}}
        fig.savefig(path, facecolor=STYLE["surface"], bbox_inches="tight", pad_inches=0.02,
                    **kwargs)
        paths[ext] = path
    return paths


def main():
    data = load()
    if "--preview" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--preview") + 1]).resolve()
        if target == OUTPUT.resolve() or HERE.resolve() in target.parents:
            raise SystemExit("Previews must be written outside the figures folder")
        print(json.dumps({e: str(p) for e, p in save(draw(data), target, True).items()}))
        return
    paths = save(draw(data), OUTPUT, False)
    manifest = {"report": str(REPORT.relative_to(ROOT)), "report_sha256": REPORT_SHA256,
                "first_export_manifest_sha256": sha256(FIRST_MANIFEST),
                "values_equal_first_export": True,
                "renderer_sha256": sha256(__file__),
                "plan_sha256": sha256(HERE / "plan-r2.md"), "values": data,
                "outputs": {e: {"path": str(p.relative_to(ROOT)), "sha256": sha256(p)}
                            for e, p in paths.items()}}
    with (OUTPUT / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(json.dumps(manifest["outputs"], indent=2))


if __name__ == "__main__":
    main()
