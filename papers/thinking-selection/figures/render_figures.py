"""Export three frozen report displays; never load experiment data or fit models."""

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/thinking-selection-r5-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INK = "#172b40"
GRAY = "#526273"
BLUE = "#176a91"
ORANGE = "#b65d12"
TEAL = "#17816f"
LIGHT = "#e1e7ed"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def verify_freeze():
    manifest_path = HERE / "frozen-export.json"
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["export_file_sha256"].items():
        data = (ROOT / relative).read_bytes()
        if digest(data) != expected:
            raise RuntimeError(f"Changed frozen export file: {relative}")
        if data != git("show", f"HEAD:{relative}"):
            raise RuntimeError(f"Export file must be committed: {relative}")
    relative = str(manifest_path.relative_to(ROOT))
    if manifest_path.read_bytes() != git("show", f"HEAD:{relative}"):
        raise RuntimeError("Manifest must be committed before rendering")
    for relative, expected in manifest["source_sha256"].items():
        data = git("show", f"{manifest['source_commit']}:{relative}")
        if digest(data) != expected:
            raise RuntimeError(f"Frozen source mismatch: {relative}")
    inputs = json.loads((HERE / "display-inputs.json").read_text())
    if inputs["source_commit"] != manifest["source_commit"]:
        raise RuntimeError("Input/source checkpoint mismatch")
    return manifest, inputs, digest(manifest_path.read_bytes())


def page(size, spec):
    fig = plt.figure(figsize=size, facecolor="white")
    fig.text(.035, .955, spec["title"], fontsize=19, weight="bold", color=INK)
    fig.text(.035, .913, spec["subtitle"], fontsize=10.5, color=GRAY)
    fig.text(.035, .027, spec["footer"], fontsize=10, color=GRAY)
    return fig


def box(ax, x, y, w, h, edge=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                              facecolor="#f7f9fb", edgecolor=edge, linewidth=1.2))


def study_map(spec):
    fig = page((12, 7.5), spec)
    ax = fig.add_axes([0, .055, 1, .83])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    blocks = {b["id"]: b for b in spec["blocks"]}
    b = blocks["repeat"]
    box(ax, .035, .10, .345, .80)
    ax.text(.05, .86, b["title"], fontsize=13, weight="bold", color=INK, va="top")
    ax.text(.05, .807, b["subtitle"], fontsize=10.3, color=GRAY, va="top")
    for section, top in zip(b["sections"], [.70, .48, .26]):
        ax.plot([.05, .36], [top+.033, top+.033], color=LIGHT, lw=1)
        ax.text(.05, top, section["title"], fontsize=10.2, weight="bold", color=BLUE, va="top")
        ax.text(.05, top-.058, section["body"], fontsize=10.1, color=INK, va="top", linespacing=1.6)
    b = blocks["diagnostic"]
    box(ax, .465, .60, .50, .30)
    ax.text(.48, .862, b["title"], fontsize=13, weight="bold", color=INK, va="top")
    ax.text(.48, .81, b["subtitle"], fontsize=10.4, color=GRAY, va="top")
    ax.text(.48, .733, b["body"], fontsize=11, color=INK, va="top", linespacing=1.6)
    for ident, x, w in [("cap", .465, .23), ("fresh", .735, .23)]:
        b = blocks[ident]
        box(ax, x, .10, w, .365, edge=TEAL if ident == "fresh" else BLUE)
        ax.text(x+.013, .431, b["title"], fontsize=11.8, weight="bold", color=INK, va="top")
        ax.text(x+.013, .377, b["subtitle"], fontsize=9.5, color=GRAY, va="top")
        ax.text(x+.013, .305, b["body"], fontsize=9.6, color=INK, va="top", linespacing=1.65)
    arrow_kw = dict(arrowstyle="-|>", mutation_scale=13, lw=1.2, color=GRAY, linestyle=(0, (4, 3)))
    ax.add_patch(FancyArrowPatch((.388, .735), (.457, .735), **arrow_kw))
    ax.text(.422, .78, spec["arrows"][0]["label"], ha="center", fontsize=8.5, color=GRAY)
    for x, label in [(.58, spec["arrows"][1]["label"]), (.85, spec["arrows"][2]["label"])]:
        ax.add_patch(FancyArrowPatch((x, .59), (x, .474), **arrow_kw))
        ax.text(x+.012, .535, label, fontsize=9, color=GRAY, va="center")
    return fig


def utility(spec):
    fig = page((12, 6.8), spec)
    positions = [(0.61, .16), (.235, .265)]
    colors = [ORANGE, BLUE]
    for panel, (bottom, height), color in zip(spec["panels"], positions, colors):
        fig.text(.035, bottom+height+.08, panel["title"], color=INK, fontsize=13, weight="bold")
        fig.text(.035, bottom+height+.043, panel["comparator"], color=GRAY, fontsize=10)
        ax = fig.add_axes([.235, bottom, .425, height])
        n = len(panel["rows"])
        ax.set(xlim=tuple(map(float, spec["xlim"])), ylim=(-.55, n-.45))
        ax.invert_yaxis()
        ax.axvline(0, color=GRAY, lw=1.1, ls="--", zorder=1)
        ax.set_xticks([-.06, -.04, -.02, 0, .02])
        ax.grid(axis="x", color=LIGHT, lw=.7)
        ax.set_axisbelow(True)
        ax.set_yticks(range(n), [r["label"] for r in panel["rows"]], fontsize=10)
        ax.tick_params(axis="y", length=0, pad=10)
        ax.tick_params(axis="x", labelsize=10, colors=GRAY)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(LIGHT)
        for y, row in enumerate(panel["rows"]):
            mean, low, high = [float(row[k]) for k in ["mean", "low", "high"]]
            ax.errorbar(mean, y, xerr=[[mean-low], [high-mean]], fmt="D" if n == 1 else "o",
                        color=color, markersize=7, elinewidth=1.8, capsize=5, zorder=3)
            # Printed strings retain the source precision; arithmetic only positions the interval.
            ax.text(1.035, y, f"{row['mean']}  [{row['low']}, {row['high']}]",
                    transform=ax.get_yaxis_transform(), fontsize=9.3, va="center", color=INK)
        if n == 1:
            ax.tick_params(axis="x", labelbottom=False)
        else:
            ax.set_xlabel("Utility difference at $\\lambda=0.05$ (fractions)", fontsize=11, labelpad=9, color=INK)
    fig.text(.675, .835, "Mean [conditional 90% interval]", fontsize=9.3, color=GRAY)
    fig.text(.235, .102, "Negative values favor the stated comparator.", fontsize=10, color=GRAY)
    return fig


def diagnostic(spec):
    fig = page((12, 6.5), spec)
    styles = {"Accept direct": ("s", BLUE), "Always escalate": ("^", ORANGE), "Confidence": ("o", TEAL)}
    # Offset labels in points; no connecting curve or inferred intervals.
    offsets = [dict(zip(styles, [(8, 17), (-10, 18), (10, -32)])),
               dict(zip(styles, [(8, 17), (-8, -32), (-5, 19)]))]
    for index, (panel, left) in enumerate(zip(spec["panels"], [.08, .565])):
        ax = fig.add_axes([left, .21, .395, .55])
        ax.set(xlim=tuple(map(float, spec["xlim"])), ylim=tuple(map(float, spec["ylim"])))
        ax.set_title(panel["solver"], fontsize=14, weight="bold", color=INK, pad=43)
        ax.text(.5, 1.05, f"{panel['positive_questions']}/{panel['question_count']} questions: positive realized gain in either draw",
                transform=ax.transAxes, ha="center", color=GRAY, fontsize=9.3)
        ax.set_xticks([0, 500, 1000, 1500])
        ax.set_yticks([55, 65, 75, 85, 95])
        ax.grid(color=LIGHT, lw=.7)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(LIGHT)
        ax.tick_params(labelsize=10, colors=GRAY)
        ax.set_xlabel("Charged output tokens / state", fontsize=11, labelpad=9, color=INK)
        if index == 0:
            ax.set_ylabel("Scored accuracy (%)", fontsize=11, labelpad=9, color=INK)
        for point in panel["points"]:
            policy = point["policy"]
            marker, color = styles[policy]
            x, y = float(point["tokens"]), float(point["accuracy"])
            ax.scatter([x], [y], s=80, marker=marker, color=color, edgecolors="white", linewidths=.7, zorder=3)
            dx, dy = offsets[index][policy]
            label = f"{policy}\n{point['accuracy']}% | {float(point['tokens']):,.2f} tokens"
            ax.annotate(label, (x, y), xytext=(dx, dy), textcoords="offset points",
                        fontsize=9.3, ha="right" if dx < 0 else "left", va="center", color=INK,
                        bbox=dict(boxstyle="round,pad=.25", facecolor="white", edgecolor="none", alpha=.93))
    fig.text(.08, .10, "Each label is a reported point estimate. No accuracy/token uncertainty bars are inferred.", fontsize=10, color=GRAY)
    return fig


def main():
    manifest, inputs, manifest_sha = verify_freeze()
    output = ROOT / manifest["output_root"]
    receipt_path = HERE / "export-record.json"
    if receipt_path.exists() or any(output.glob("*/*")):
        raise RuntimeError("Export exists: preserve it; use a separately pinned revision")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                         "axes.labelcolor": INK, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "svg.hashsalt": "thinking-selection-r5-v1"})
    records = []
    for spec, draw in zip(inputs["figures"], [study_map, utility, diagnostic]):
        fig = draw(spec)
        fig.canvas.draw()
        # Artifact bounds check. Layout collisions also require visual review.
        renderer = fig.canvas.get_renderer()
        for text in fig.findobj(match=matplotlib.text.Text):
            if not text.get_visible() or not text.get_text():
                continue
            bb = text.get_window_extent(renderer)
            if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > fig.bbox.width+1 or bb.y1 > fig.bbox.height+1:
                raise RuntimeError(f"Text outside canvas in {spec['id']}: {text.get_text()}")
        for fmt in ["pdf", "svg", "png"]:
            dest = output / fmt / f"{spec['id']}.{fmt}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            metadata = {"Creator": "Frozen report-only R5 Matplotlib export", "Title": spec["title"]}
            if fmt == "pdf":
                metadata.update(CreationDate=None, ModDate=None, Subject=spec["caption"])
            elif fmt == "svg":
                metadata.update(Date=None, Description=spec["caption"])
            else:
                metadata["Description"] = spec["caption"]
            fig.savefig(dest, format=fmt, dpi=240, facecolor="white", metadata=metadata)
            records.append({"path": str(dest.relative_to(ROOT)), "sha256": digest(dest.read_bytes()),
                            "bytes": dest.stat().st_size})
        plt.close(fig)
    receipt = {"schema": "thinking-selection-display-export-v1", "completed_utc": datetime.now(timezone.utc).isoformat(),
               "freeze_commit": git("rev-parse", "HEAD").decode().strip(), "manifest_sha256": manifest_sha,
               "source_commit": manifest["source_commit"], "python": sys.version,
               "matplotlib": matplotlib.__version__, "platform": platform.platform(),
               "source_hashes_verified": True, "export_hashes_verified": True,
               "statistical_reestimation": False, "outputs": records,
               "visual_review": "pending; see separate review.md after inspection"}
    receipt_path.write_text(json.dumps(receipt, indent=2)+"\n")
    print(f"Exported {len(records)} files; receipt: {receipt_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
