#!/usr/bin/env python3
"""Capacity frontier figure: storage and recall vs loading, per network size."""

import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "clockless", "results")
FIG = os.path.join(HERE, "figures")

BLUE, VERM, GREEN, ORANGE = "#0072B2", "#D55E00", "#009E73", "#E69F00"
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d4"
plt.rcParams.update({
    "font.family": "serif", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight",
})

rows = []
for f in ("nm_scaling.json", "nm_highalpha.json"):
    p = os.path.join(RES, f)
    if os.path.exists(p):
        rows += json.load(open(p))
# de-duplicate (N,M), keeping the last measurement
seen = {}
for r in rows:
    seen[(r["N"], r["M"])] = r
rows = sorted(seen.values(), key=lambda r: (r["N"], r["M"]))

Ns = sorted({r["N"] for r in rows})
colours = {32: ORANGE, 64: VERM, 128: GREEN, 256: BLUE}
marks = {32: "^", 64: "s", 128: "o", 256: "D"}

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))

ax = axes[0]
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    ax.plot([r["alpha"] for r in d], [100 * r["stored"] / r["M"] for r in d],
            marks[N] + "-", color=colours[N], lw=2, ms=6, label=f"N={N}", zorder=3)
ax.axvspan(0.55, 0.8, color=VERM, alpha=0.07, zorder=0)
ax.text(0.585, 50, "capacity cliff", fontsize=8, color=VERM, rotation=90, va="center")
ax.set_ylim(-4, 108)
ax.set_xlabel("loading  α = M / N", fontsize=8.5)
ax.set_ylabel("patterns stored as fixed points (%)", fontsize=8.5)
ax.set_title("Storage", fontsize=9.5, loc="left", pad=8)
ax.legend(frameon=False, fontsize=8, loc="lower left")

ax = axes[1]
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    ax.plot([r["alpha"] for r in d], [100 * r["recall_hd3"] for r in d],
            marks[N] + "-", color=colours[N], lw=2, ms=6, label=f"N={N}", zorder=3)
ax.axvline(0.138, color=MUTED, ls="--", lw=1.2, zorder=1)
ax.text(0.145, 30, "classical Hopfield\ncapacity α≈0.138", fontsize=7.5, color=MUTED)
ax.axvspan(0.55, 0.8, color=VERM, alpha=0.07, zorder=0)
ax.set_ylim(-4, 108)
ax.set_xlabel("loading  α = M / N", fontsize=8.5)
ax.set_ylabel("recall from HD≤3 corruption (%)", fontsize=8.5)
ax.set_title("Recall", fontsize=9.5, loc="left", pad=8)
ax.legend(frameon=False, fontsize=8, loc="lower left")

fig.suptitle("Margin-trained clockless HNN: perfect storage and recall to α≈0.5, "
             "then a sharp cliff",
             fontsize=10, color=INK, y=1.04)
fig.text(0.5, -0.07,
         "Fan-in grows with M (min(N−1, 4M)), so the high-α points use near-full "
         "connectivity — good for the network, expensive for a LUT implementation.",
         ha="center", fontsize=7.5, color=MUTED)
os.makedirs(FIG, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"fig8_capacity_frontier.{ext}"))
print("wrote figures/fig8_capacity_frontier.png/.pdf")

print("\nsummary — highest M with 100% storage AND >=95% recall@HD3:")
for N in Ns:
    d = [r for r in rows if r["N"] == N and r["stored"] == r["M"]
         and r["recall_hd3"] >= 0.95]
    if d:
        b = max(d, key=lambda r: r["M"])
        print(f"  N={N:>4}: M={b['M']:>3}  (alpha={b['alpha']:.3f}, "
              f"fan-in {b['fan_in']}, recall {100*b['recall_hd3']:.0f}%)")
