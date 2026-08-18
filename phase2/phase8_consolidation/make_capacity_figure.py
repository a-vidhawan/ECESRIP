#!/usr/bin/env python3
"""Capacity frontier figure: storage and recall vs loading, per network size.

Phase-8 re-make. Same layout and palette as paper/make_capacity_figure.py, but
driven by phase8_consolidation/results/nm_scaling_autokappa.json -- the sweep
run with `train_margin_auto` (largest feasible margin) instead of a fixed
kappa=1.

The old figure's "capacity cliff at alpha ~ 0.6" was an artifact of kappa=1:
past that loading the kappa=1 constraint system is simply infeasible and the
trainer returns weights that store nothing. With an adaptive margin the storage
curve does not fall at all over the range swept, and the binding limit becomes
recall, which degrades smoothly. The dashed overlay on the storage panel shows
the margin that had to be conceded to keep storage perfect.

Writes ../paper/figures/fig8_capacity_frontier.{png,pdf} -- deliberately the
same paths as the old figure, which this replaces.
"""

import json, os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "..", "paper", "figures")

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
main = os.path.join(RES, "nm_scaling_autokappa.json")
if os.path.exists(main):
    rows += json.load(open(main))
for p in sorted(glob.glob(os.path.join(RES, "nm_autokappa_N*.json"))):
    rows += json.load(open(p))
if not rows:
    raise SystemExit("no autokappa results found in " + RES)
# de-duplicate (N,M), keeping the last measurement
seen = {}
for r in rows:
    seen[(r["N"], r["M"])] = r
rows = sorted(seen.values(), key=lambda r: (r["N"], r["M"]))

Ns = sorted({r["N"] for r in rows})
colours = {32: ORANGE, 64: VERM, 128: GREEN, 256: BLUE}
marks = {32: "^", 64: "s", 128: "o", 256: "D"}

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))

# ---------------------------------------------------------------- storage
ax = axes[0]
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    ax.plot([r["alpha"] for r in d], [100 * r["stored"] / r["M"] for r in d],
            marks[N] + "-", color=colours[N], lw=2, ms=6, label=f"N={N}",
            zorder=3)
ax.set_ylim(-4, 108)
ax.set_xlabel("loading  α = M / N", fontsize=8.5)
ax.set_ylabel("patterns stored as fixed points (%)", fontsize=8.5)
ax.set_title("Storage — no cliff once κ adapts", fontsize=9.5, loc="left", pad=8)
ax.legend(frameon=False, fontsize=8, loc="lower left")

# the margin conceded to keep storage perfect, on a twin axis
axk = ax.twinx()
axk.grid(False)
axk.spines["top"].set_visible(False)
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    axk.plot([r["alpha"] for r in d], [r["kappa"] for r in d],
             ls=":", lw=1.2, color=colours[N], alpha=0.75, zorder=2)
axk.set_ylim(-0.04, 1.08)
axk.set_ylabel("selected margin κ  (dotted)", fontsize=8, color=MUTED)
axk.tick_params(axis="y", labelsize=7.5, colors=MUTED)
axk.spines["right"].set_visible(True)
axk.spines["right"].set_color(MUTED)

# ----------------------------------------------------------------- recall
ax = axes[1]
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    ax.plot([r["alpha"] for r in d], [100 * r["recall_hd3"] for r in d],
            marks[N] + "-", color=colours[N], lw=2, ms=6, label=f"N={N}",
            zorder=3)
ax.axvline(0.138, color=MUTED, ls="--", lw=1.2, zorder=1)
ax.text(0.145, 30, "classical Hopfield\ncapacity α≈0.138", fontsize=7.5,
        color=MUTED)
ax.set_ylim(-4, 108)
ax.set_xlabel("loading  α = M / N", fontsize=8.5)
ax.set_ylabel("recall from HD≤3 corruption (%)", fontsize=8.5)
ax.set_title("Recall — the binding limit", fontsize=9.5, loc="left", pad=8)
ax.legend(frameon=False, fontsize=8, loc="lower left")

# where recall crosses 95%, per N -- the useful frontier
best = []
for N in Ns:
    d = [r for r in rows if r["N"] == N and r["stored"] == r["M"]
         and r["recall_hd3"] >= 0.95]
    if d:
        best.append((N, max(d, key=lambda r: r["M"])))
if best:
    lo = min(b["alpha"] for _, b in best)
    hi = max(b["alpha"] for _, b in best)
    for a in (axes[0], axes[1]):
        a.axvspan(lo, hi, color=GREEN, alpha=0.07, zorder=0)
    axes[1].text(hi + 0.012, 62, "≥95% recall\nholds to here", fontsize=7.5,
                 color=MUTED)

fig.suptitle("Margin-trained clockless HNN: with an adaptive margin the storage "
             "cliff disappears — recall, not storage, sets capacity",
             fontsize=10, color=INK, y=1.04)
fig.text(0.5, -0.09,
         "Trained with train_margin_auto (largest feasible κ). The earlier cliff "
         "at α≈0.6 was the κ=1 feasibility boundary, not a capacity limit: κ "
         "falls below 1 exactly where the old curve collapsed, and storage stays "
         "perfect.\nFan-in grows with M (min(N−1, 4M)), so the high-α points use "
         "near-full connectivity — good for the network, expensive for a LUT "
         "implementation.",
         ha="center", fontsize=7.5, color=MUTED)
os.makedirs(FIG, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"fig8_capacity_frontier.{ext}"))
print("wrote paper/figures/fig8_capacity_frontier.png/.pdf")

print("\nselected kappa by (N, alpha):")
for N in Ns:
    d = [r for r in rows if r["N"] == N]
    print(f"  N={N:>4}: " + "  ".join(f"{r['alpha']:.2f}:κ{r['kappa']:g}"
                                      for r in d))

print("\nstorage: lowest alpha at which NOT all patterns are fixed points:")
for N in Ns:
    d = [r for r in rows if r["N"] == N and r["stored"] < r["M"]]
    print(f"  N={N:>4}: " + (f"alpha={min(r['alpha'] for r in d):.3f}" if d
                            else "never — 100% stored at every alpha swept"))

print("\nhighest M with 100% storage AND >=95% recall@HD3:")
for N, b in best:
    print(f"  N={N:>4}: M={b['M']:>3}  (alpha={b['alpha']:.3f}, "
          f"kappa={b['kappa']:g}, fan-in {b['fan_in']}, "
          f"recall {100*b['recall_hd3']:.0f}%)")
