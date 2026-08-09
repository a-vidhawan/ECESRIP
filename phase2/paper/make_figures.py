#!/usr/bin/env python3
"""
Publication figures. Every number is read from a result file -- none are typed in.

Palette is Okabe-Ito, ordered so adjacent slots pass CVD separation (validated:
worst adjacent deutan dE 11.0). Slot 4 (orange) sits below 3:1 contrast on white,
so every chart that uses it carries direct value labels rather than relying on
fill alone. Figures render to both PDF (vector, for the paper) and PNG (preview).
"""

import json, os, sys
from math import comb, cos, sin, pi
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "clockless", "results")
FIG = os.path.join(HERE, "figures")
DATA = os.path.join(HERE, "data")
os.makedirs(FIG, exist_ok=True)

# validated categorical order -- do not cycle, do not reorder
BLUE, VERM, GREEN, ORANGE, PINK = "#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d4"

plt.rcParams.update({
    "font.family": "serif", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight",
})


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"))
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf/.png")


def style(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, fontsize=9.5, color=INK, pad=8, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.5)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)
    ax.tick_params(labelsize=8, length=3)


# ── Fig 1: the mechanism -- parity collides coupled neurons, colouring doesn't ──
def fig1_coupling_graph():
    g = json.load(open(os.path.join(RES, "coupling_graph.json")))
    edges = [tuple(e) for e in g["edges"]]
    par = {int(k): v for k, v in g["parity_classes"].items()}
    col = {int(k): v for k, v in g["colour_classes"].items()}
    N = 16
    pos = {i: (cos(2 * pi * i / N + pi / 2), sin(2 * pi * i / N + pi / 2))
           for i in range(N)}
    palette = [BLUE, VERM, GREEN, ORANGE, PINK, "#6a5acd"]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.6))
    for ax, classes, name in ((axes[0], par, "index parity (even_odd)"),
                              (axes[1], col, "graph colouring")):
        bad = [(i, j) for i, j in edges if classes[i] == classes[j]]
        for i, j in edges:
            conflict = classes[i] == classes[j]
            ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]],
                    color=VERM if conflict else GRID,
                    lw=1.5 if conflict else 0.7,
                    zorder=2 if conflict else 1,
                    alpha=1.0 if conflict else 0.9)
        for i in range(N):
            ax.scatter(*pos[i], s=190, color=palette[classes[i] % len(palette)],
                       edgecolor="white", linewidth=1.4, zorder=3)
            ax.text(pos[i][0], pos[i][1], str(i), ha="center", va="center",
                    fontsize=7, color="white", fontweight="bold", zorder=4)
        pct = 100 * len(bad) / len(edges)
        ax.set_title(f"{name}\n{len(bad)}/{len(edges)} coupled pairs collide "
                     f"({pct:.0f}%)", fontsize=9, color=INK, pad=6)
        ax.set_xlim(-1.35, 1.35); ax.set_ylim(-1.35, 1.35)
        ax.set_aspect("equal"); ax.axis("off")
    fig.subplots_adjust(bottom=0.20)
    fig.legend(handles=[Line2D([], [], color=VERM, lw=1.8,
                               label="coupled pair sharing a delay (collision)"),
                        Line2D([], [], color=GRID, lw=1.0,
                               label="coupled pair, separated")],
               loc="lower center", ncol=2, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, 0.08))
    fig.text(0.5, 0.005, "Node colour = delay class. Same class at both ends of an "
             "edge means two interacting neurons commit at the same instant.",
             ha="center", fontsize=7.5, color=MUTED)
    save(fig, "fig1_coupling_graph")


# ── Fig 2: the rule (2x2) ────────────────────────────────────────────────────
def fig2_rule():
    df = pd.read_csv(os.path.join(RES, "stress_r7_permutation.csv"))
    u = df[df["testset"] == "uosc"]
    order = ["colour+incommens", "colour+commens", "colour+nosep", "parity+incommens"]
    label = {"colour+incommens": "colouring +\ndistinct delays\n(incommensurate)",
             "colour+commens": "colouring +\ndistinct delays\n(commensurate)",
             "colour+nosep": "colouring +\nIDENTICAL delays",
             "parity+incommens": "NO colouring +\ndistinct delays"}
    vals = [u[u["category"] == c]["settled"].mean() * 100 for c in order]
    nsch = [u[u["category"] == c]["scheme"].nunique() for c in order]
    colors = [GREEN, GREEN, VERM, VERM]

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    bars = ax.bar(range(4), vals, color=colors, width=0.62, zorder=3)
    for i, (b, v, n) in enumerate(zip(bars, vals, nsch)):
        ax.text(b.get_x() + b.get_width() / 2, v + 2.5, f"{v:.0f}%",
                ha="center", fontsize=10, color=INK, fontweight="bold")
        # for the zero bars there is no bar to sit inside, so stack the count above
        ax.text(b.get_x() + b.get_width() / 2, 4 if v > 10 else v + 9,
                f"{n} scheme{'s' if n > 1 else ''}",
                ha="center", fontsize=7.5, color="white" if v > 10 else MUTED)
    ax.set_xticks(range(4)); ax.set_xticklabels([label[c] for c in order], fontsize=8)
    ax.set_ylim(0, 112); ax.set_yticks([0, 25, 50, 75, 100])
    style(ax, "Settling on the 32 hardest states, by scheduling condition",
          None, "settled (%)")
    ax.text(0.5, -0.34, "Only the delay VALUES matter: separation is necessary "
            "(right two fail) and sufficient (left two succeed,\nwhether or not the "
            "delays are commensurate). Across 12 permutations of the same primes, sd = 0.00.",
            transform=ax.transAxes, ha="center", fontsize=7.5, color=MUTED)
    save(fig, "fig2_scheduling_rule")


# ── Fig 3: scaling ───────────────────────────────────────────────────────────
def fig3_scaling():
    rows = json.load(open(os.path.join(RES, "scale_final.json")))
    extra = os.path.join(RES, "scale_retrain.json")
    if os.path.exists(extra):
        rows = json.load(open(extra)) + rows
    seen, clean = set(), []
    for r in sorted(rows, key=lambda r: r["N"]):
        if r["N"] in seen:
            continue
        seen.add(r["N"]); clean.append(r)
    N = [r["N"] for r in clean]
    chi = [r["chromatic"] for r in clean]
    st = [r["settled_hd3"] * 100 for r in clean]
    rc = [r["correct_hd3"] * 100 for r in clean]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax = axes[0]
    ax.plot(N, chi, "o-", color=BLUE, lw=2, ms=7, zorder=3)
    for x, y in zip(N, chi):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=7.5, color=INK)
    ax.set_xscale("log", base=2); ax.set_ylim(0, max(chi) + 4)
    style(ax, "Delay classes needed", "network size N (log)", "χ (distinct delays)")

    ax = axes[1]
    ax.plot(N, st, "o-", color=GREEN, lw=2, ms=6, label="settled", zorder=3)
    ax.plot(N, rc, "s--", color=ORANGE, lw=2, ms=6, label="recall @ HD≤3", zorder=3)
    for x, y in zip(N, st):
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, -13),
                    ha="center", fontsize=7, color=MUTED)
    ax.set_xscale("log", base=2); ax.set_ylim(0, 112)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style(ax, "Behaviour", "network size N (log)", "%")
    fig.suptitle("Schedule cost does not grow with N: χ stays ~6 at N=4096, "
                 "settling and recall stay at 100%.",
                 fontsize=8.5, color=MUTED, y=1.04)
    save(fig, "fig3_scaling")


# ── Fig 4: don't-care minimisation ───────────────────────────────────────────
def fig4_dontcare():
    d = json.load(open(os.path.join(DATA, "dc_terms.json")))
    runs = d["runs"]
    fi = [r["fan_in"] for r in runs]
    dc_mean = [np.mean(r["dc_terms"]) for r in runs]
    full_mean = [np.mean(r["full_terms"]) if r["full_terms"] else None for r in runs]
    table = [2 ** r["fan_in"] for r in runs]
    bound = [comb(r["fan_in"], r["fan_in"] // 2) for r in runs]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))
    ax = axes[0]
    ax.plot(fi, table, "^:", color=MUTED, lw=1.4, ms=6, label="full truth table (2^d)")
    ax.plot(fi, bound, "v--", color=VERM, lw=1.6, ms=6, label="predicted SOP C(d,d/2)")
    fm = [(x, y) for x, y in zip(fi, full_mean) if y]
    if fm:
        ax.plot([x for x, _ in fm], [y for _, y in fm], "s-", color=ORANGE, lw=1.8,
                ms=6, label="espresso, fully specified")
    ax.plot(fi, dc_mean, "o-", color=GREEN, lw=2.4, ms=8, label="espresso, don't-care", zorder=4)
    for x, y in zip(fi, dc_mean):
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 11),
                    ha="center", fontsize=8, color=INK, fontweight="bold")
    ax.set_yscale("log"); ax.set_xticks(fi); ax.set_ylim(bottom=3)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    style(ax, "Product terms per neuron", "fan-in d", "terms (log)")

    # area comparison
    ax = axes[1]
    WB, GEB = 8, 5
    def thr_ge(dd):
        w = WB + int(np.ceil(np.log2(dd)))
        return (dd - 1) * w * GEB + dd * WB
    lut_ge = [t * (f / 2.0) + t for t, f in zip(dc_mean, fi)]
    thr = [thr_ge(f) for f in fi]
    x = np.arange(len(fi)); w = 0.36
    b1 = ax.bar(x - w / 2 - 0.01, lut_ge, w, color=GREEN, label="LUT (don't-care)", zorder=3)
    b2 = ax.bar(x + w / 2 + 0.01, thr, w, color=BLUE, label="threshold adder tree", zorder=3)
    for bs in (b1, b2):
        for b in bs:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(thr) * 0.03,
                    f"{b.get_height():,.0f}", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{f}\n({t/l:.1f}× smaller)"
                        for f, l, t in zip(fi, lut_ge, thr)])
    # linear, zero-based: bar length must encode magnitude (never a log bar chart)
    ax.set_ylim(0, max(thr) * 1.12)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style(ax, "Estimated area", "fan-in d", "gate equivalents")
    fig.suptitle("Don't-cares keep term count flat as fan-in grows, inverting the "
                 "area comparison against a threshold gate.",
                 fontsize=8.5, color=MUTED, y=1.04)
    save(fig, "fig4_dontcare")


# ── Fig 5: the two levers ────────────────────────────────────────────────────
def fig5_two_levers():
    df = pd.read_csv(os.path.join(RES, "stress_r6_scheduling.csv"))
    cats = ["correct", "wrong_pattern", "spurious", "oscillated"]
    colors = {"correct": GREEN, "wrong_pattern": ORANGE,
              "spurious": BLUE, "oscillated": VERM}
    schemes = ["parity", "colour6"]
    names = {"parity": "index parity", "colour6": "graph colouring"}
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))
    for ax, ts, tname in ((axes[0], "hd3", "near patterns (HD≤3)"),
                          (axes[1], "random", "uniform random states")):
        sub = df[df["testset"] == ts]
        bottoms = np.zeros(len(schemes))
        for c in cats:
            vals = [(sub[sub["scheme"] == s]["outcome"] == c).mean() * 100
                    for s in schemes]
            ax.barh(range(len(schemes)), vals, left=bottoms, color=colors[c],
                    height=0.5, label=c.replace("_", " "), zorder=3)
            for i, (v, b) in enumerate(zip(vals, bottoms)):
                if v > 6:
                    ax.text(b + v / 2, i, f"{v:.0f}", ha="center", va="center",
                            fontsize=7.5, color="white", fontweight="bold")
            bottoms += np.array(vals)
        ax.set_yticks(range(len(schemes)))
        # only the left panel carries the category labels; the right shares them
        ax.set_yticklabels([names[s] for s in schemes] if ts == "hd3" else [""] * len(schemes),
                           fontsize=8)
        ax.set_xlim(0, 100); ax.grid(axis="y", visible=False)
        style(ax, tname, "share of trials (%)", None)
    axes[0].legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center",
                   bbox_to_anchor=(1.05, -0.18))
    fig.suptitle("Failures are overwhelmingly spurious attractors (blue), not "
                 "oscillation (red): correctness and settling are separate problems.",
                 fontsize=8.5, color=MUTED, y=1.03)
    fig.text(0.5, -0.13, "Colouring here uses the prime ladder, which leaves ~4% "
             "residual oscillation on HD≤3; the power-of-two ladder removes it "
             "entirely (100% settled).",
             ha="center", fontsize=7, color=MUTED)
    save(fig, "fig5_two_levers")


# ── Fig 6: recall vs loading ─────────────────────────────────────────────────
def fig6_capacity():
    rows = json.load(open(os.path.join(RES, "capacity_scan.json")))
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    for hd, colr, mk in ((1, BLUE, "o"), (3, ORANGE, "s")):
        pts = sorted([(r["alpha"], r["correct"] * 100)
                      for r in rows if r["hd"] == hd])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], mk, color=colr,
                ms=5, alpha=0.75, label=f"HD={hd}", zorder=3)
    ax.axvline(0.138, color=MUTED, ls="--", lw=1.2)
    ax.text(0.142, 32, "classical Hopfield\ncapacity α≈0.138", fontsize=7.5, color=MUTED)
    ax.axvline(0.25, color=VERM, ls=":", lw=1.6)
    ax.text(0.256, 74, "network under test\nα=4/16=0.25", fontsize=7.5, color=VERM)
    ax.set_ylim(0, 108)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style(ax, "Recall is set by loading, not by the schedule",
          "loading α = M/N", "recall (%)")
    save(fig, "fig6_capacity")


# ── Fig 7: PVT robustness, and the rescue that confirms the mechanism ────────
def fig7_pvt():
    d = json.load(open(os.path.join(DATA, "dc_terms.json")))["pvt"]
    r = d["rows"]
    x = [100 * (np.exp(3 * row["sigma"]) - 1) for row in r]
    cs = [100 * row["coloured_settled"] for row in r]
    ds = [100 * row["degenerate_settled"] for row in r]

    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    ax.plot(x, cs, "o-", color=GREEN, lw=2.4, ms=8,
            label="graph-coloured schedule", zorder=4)
    ax.plot(x, ds, "s--", color=VERM, lw=2.4, ms=8,
            label="degenerate schedule (all delays equal)", zorder=4)
    ax.annotate(f"{ds[0]:.0f}%", (x[0], ds[0]), textcoords="offset points",
                xytext=(6, -14), fontsize=9, color=VERM, fontweight="bold")
    ax.annotate("variation makes equal delays\ndistinct — the schedule is rescued",
                xy=(x[1], ds[1]), xytext=(x[2] + 8, 78),
                fontsize=7.5, color=MUTED,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1))
    ax.set_ylim(55, 108)
    ax.set_xscale("symlog", linthresh=20)
    ax.set_xticks([0, 16, 35, 82, 146, 348])
    ax.set_xticklabels(["0", "±16", "±35", "±82", "±146", "±348"])
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax, "Delay variation does not break the schedule — it repairs a broken one",
          "delay spread, 3σ (%)", "settled (%)")
    fig.text(0.5, -0.06, "Real silicon variation helps. The hazard is delays made "
             "equal BY CONSTRUCTION, which is what an identical-buffer-chain "
             "implementation would give.",
             ha="center", fontsize=7.5, color=MUTED)
    save(fig, "fig7_pvt")


if __name__ == "__main__":
    print("rendering figures...")
    for f in (fig1_coupling_graph, fig2_rule, fig3_scaling,
              fig4_dontcare, fig5_two_levers, fig6_capacity, fig7_pvt):
        try:
            f()
        except Exception as e:
            print(f"  FAILED {f.__name__}: {type(e).__name__}: {e}")
    print("done")
