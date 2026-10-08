"""Turns results/*.json into results/RESULTS.md (tables) and results/*.png (charts).

Usage:  python3 bench/make_report.py
"""
import json
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import ROOT  # noqa: E402

RES = ROOT / "results"
FWS = ["React", "Angular", "Vue", "Svelte"]
# Categorical slots 1-4 of the validated reference palette, fixed per framework.
COLORS = {"React": "#2a78d6", "Angular": "#eb6834", "Vue": "#1baf7a", "Svelte": "#eda100"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
RENDER = ["render-100", "render-500", "render-1000"]
CHANGE = ["update-50", "delete-50"]
LABEL = {
    "render-100": "Render 100", "render-500": "Render 500", "render-1000": "Render 1000",
    "update-50": "Update 50 (of 1000)", "delete-50": "Delete 50 (of 1000)",
}
METRIC = "scriptLayout"  # state change -> DOM committed -> style + layout done


def load(name):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


def quartiles(xs):
    q = st.quantiles(xs, n=4)
    return q[0], st.median(xs), q[2]


def samples(d, fw, sc, metric=METRIC):
    return [r[metric] for r in d["raw"][fw][sc]]


def table(d, metric=METRIC):
    head = "| Operation | " + " | ".join(FWS) + " | Fastest |\n|---|" + "---:|" * len(FWS) + "---|\n"
    rows = []
    for sc in RENDER + CHANGE:
        meds = {fw: round(st.median(samples(d, fw, sc, metric)), 1) for fw in FWS}
        lo = min(meds.values())
        best = [fw for fw in FWS if meds[fw] == lo]  # ties share the win
        cells = [f"**{meds[fw]:.1f}**" if fw in best else f"{meds[fw]:.1f}" for fw in FWS]
        rows.append(f"| {LABEL[sc]} | " + " | ".join(cells) + f" | {' = '.join(best)} |")
    return head + "\n".join(rows) + "\n"


def relative_table(d):
    """Each framework's median as a multiple of the fastest one (1.00 = fastest)."""
    head = "| Operation | " + " | ".join(FWS) + " |\n|---|" + "---:|" * len(FWS) + "\n"
    rows = []
    for sc in RENDER + CHANGE:
        meds = {fw: st.median(samples(d, fw, sc)) for fw in FWS}
        lo = min(meds.values())
        rows.append(f"| {LABEL[sc]} | " + " | ".join(f"{meds[fw] / lo:.2f}×" for fw in FWS) + " |")
    return head + "\n".join(rows) + "\n"


def breakdown_table(d):
    """script vs layout vs to-next-frame for the 1000-row render."""
    head = "| Framework | Script (ms) | Style + layout (ms) | Script + layout (ms) | To next frame (ms) |\n|---|---:|---:|---:|---:|\n"
    rows = []
    for fw in FWS:
        s = st.median(samples(d, fw, "render-1000", "script"))
        lay = st.median(samples(d, fw, "render-1000", "layout"))
        sl = st.median(samples(d, fw, "render-1000", "scriptLayout"))
        pt = st.median(samples(d, fw, "render-1000", "paint"))
        rows.append(f"| {fw} | {s:.1f} | {lay:.1f} | {sl:.1f} | {pt:.1f} |")
    return head + "\n".join(rows) + "\n"


def memory_table(d):
    head = ("| Framework | Heap, empty app (MB) | Heap, 1000 tasks (MB) | Heap added by 1000 tasks (MB) "
            "| DOM nodes, 1000 tasks | JS bundle (KB, gzip) |\n|---|---:|---:|---:|---:|---:|\n")
    rows = []
    for fw in FWS:
        m = d["summary"][fw]["memory"]
        b = d["bundles"][fw]
        rows.append(f"| {fw} | {m['emptyHeapMB']:.2f} | {m['heap1000MB']:.2f} | {m['deltaMB']:.2f} "
                    f"| {m['domNodes1000']:,} | {b['jsGzipKB']:.1f} |")
    return head + "\n".join(rows) + "\n"


def style_axis(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=10)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def grouped(ax, d, scenarios, metric=METRIC):
    n = len(FWS)
    width = 0.8 / n
    for i, fw in enumerate(FWS):
        xs, meds, lo, hi = [], [], [], []
        for j, sc in enumerate(scenarios):
            q1, med, q3 = quartiles(samples(d, fw, sc, metric))
            xs.append(j - 0.4 + width * (i + 0.5))
            meds.append(med); lo.append(med - q1); hi.append(q3 - med)
        ax.bar(xs, meds, width=width, color=COLORS[fw], label=fw,
               edgecolor="white", linewidth=1.5)  # 2px-ish surface gap between bars
        ax.errorbar(xs, meds, yerr=[lo, hi], fmt="none", ecolor=MUTED, elinewidth=0.9, capsize=2)
    ax.set_xticks(range(len(scenarios)), [LABEL[s] for s in scenarios])


def chart(d, path, subtitle):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [3, 2, 2]})
    grouped(axes[0], d, RENDER)
    style_axis(axes[0], "Initial rendering", "ms (median; whiskers = interquartile range)")
    grouped(axes[1], d, CHANGE)
    style_axis(axes[1], "Updating and deleting 50 tasks", "ms (median; whiskers = IQR)")

    mem = [d["summary"][fw]["memory"]["deltaMB"] for fw in FWS]
    axes[2].bar(range(len(FWS)), mem, color=[COLORS[f] for f in FWS], width=0.6, edgecolor="white", linewidth=1.5)
    for i, v in enumerate(mem):
        axes[2].text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9, color=INK)
    axes[2].set_xticks(range(len(FWS)), FWS)
    style_axis(axes[2], "JS heap added by 1000 tasks", "MB (after forced GC)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=4, frameon=False, fontsize=10)
    fig.suptitle(f"To-do list DOM benchmark — {subtitle}", x=0.01, ha="left", fontsize=13, color=INK)
    fig.text(0.01, 0.905, "Lower is better. Time = state change → DOM committed → style & layout complete.",
             fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def meta_line(d):
    m = d["meta"]
    v = ", ".join(f"{k} {x}" for k, x in m["frameworks"].items())
    return (f"{m['browser']} · {m['platform']} · CPU throttling {m['cpuThrottling']}× · "
            f"{m['mode']} · {m['samplesPerCell']} samples per cell · {v} · run {m['date']}")


def main():
    cold, warm, cpu4 = load("results-cold-cpu1x.json"), load("results-warm-cpu1x.json"), load("results-cold-cpu4x.json")
    out = ["# Benchmark results\n",
           "Generated by `bench/make_report.py` from the JSON files in this folder. "
           "All times are **medians in milliseconds** for *script + layout* (state change → framework "
           "updates the DOM → browser finishes style recalculation and layout). **Bold** = fastest.\n"]
    if cold:
        chart(cold, RES / "chart-cold.png", "cold start (fresh page per sample)")
        out += ["## 1. Cold start — the headline numbers\n",
                "Every sample loads a fresh page and performs the operation once, like a real user's first interaction.\n",
                f"<sub>{meta_line(cold)}</sub>\n", table(cold),
                "\nRelative to the fastest framework (1.00× = fastest):\n", relative_table(cold),
                "\n![Cold-start benchmark chart](chart-cold.png)\n",
                "\n### Where the time goes — rendering 1000 tasks (cold)\n", breakdown_table(cold),
                "\n### Memory and bundle size\n", memory_table(cold),
                "\nHeap measured through the Chrome DevTools Protocol (`Performance.getMetrics`) after two forced "
                "garbage collections, median of 5 page loads.\n"]
    if warm:
        chart(warm, RES / "chart-warm.png", "warm / steady state (5 warm-up rounds)")
        out += ["\n## 2. Warm (steady state)\n",
                "Same operations, but each sample first repeats the operation 5 times on the same page so V8 has "
                "optimised every code path — this is closer to the methodology of the well-known "
                "js-framework-benchmark.\n", f"<sub>{meta_line(warm)}</sub>\n", table(warm),
                "\nRelative to the fastest:\n", relative_table(warm), "\n![Warm benchmark chart](chart-warm.png)\n"]
    if cpu4:
        out += ["\n## 3. Cold start on a slow device (4× CPU throttling)\n",
                "Chrome DevTools CPU throttling (`Emulation.setCPUThrottlingRate`) approximates a mid-range phone.\n",
                f"<sub>{meta_line(cpu4)}</sub>\n", table(cpu4), "\nRelative to the fastest:\n", relative_table(cpu4)]
    out += ["\n## Optimisation experiments\n",
            "See [EXPERIMENTS.md](EXPERIMENTS.md): what `React.memo` is worth (it halves update time and cuts "
            "deletion time by ~3×) and whether Svelte's whitespace text nodes cost anything (they don't).\n"]
    out += ["\n## Raw data\n",
            "Every individual sample (script, layout, script+layout and to-next-frame timings) is in the "
            "`results-*.json` files. DevTools traces of one cold *Render 1000* per framework are in "
            "`traces/` — open them in Chrome DevTools → Performance → *Load profile*.\n"]
    (RES / "RESULTS.md").write_text("\n".join(out))
    print("wrote results/RESULTS.md and charts")


if __name__ == "__main__":
    main()
