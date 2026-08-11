#!/usr/bin/env python3
"""Recall surface over N, loading alpha, and corruption fraction."""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "..", "clockless", "results", "nmhd_grid.json")))
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d4"
BLUE, VERM, GREEN, ORANGE, PINK = "#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"
plt.rcParams.update({"font.family": "serif", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "figure.dpi": 150,
    "savefig.bbox": "tight"})

Ns = sorted({r["N"] for r in rows})
alphas = sorted({r["alpha"] for r in rows})
hfs = sorted({round(r["hd_frac"], 3) for r in rows})

# ---- heatmaps: one panel per N, sequential single-hue ramp (magnitude)
fig, axes = plt.subplots(1, len(Ns), figsize=(4.0*len(Ns), 3.9))
for ax, N in zip(np.atleast_1d(axes), Ns):
    Z = np.full((len(alphas), len(hfs)), np.nan)
    for r in rows:
        if r["N"] != N: continue
        Z[alphas.index(r["alpha"]), hfs.index(round(r["hd_frac"], 3))] = 100*r["recall"]
    im = ax.imshow(Z, aspect="auto", origin="lower", cmap="viridis",
                   vmin=0, vmax=100, interpolation="nearest")
    ax.set_xticks(range(len(hfs)))
    ax.set_xticklabels([f"{100*h:.0f}" for h in hfs], fontsize=7)
    ax.set_yticks(range(len(alphas)))
    ax.set_yticklabels([f"{a:.3f}" for a in alphas], fontsize=7.5)
    ax.set_xlabel("corruption (% of N)", fontsize=8.5)
    if N == Ns[0]: ax.set_ylabel("loading  α = M / N", fontsize=8.5)
    ax.set_title(f"N = {N}", fontsize=9.5, loc="left", pad=6)
    for i in range(len(alphas)):
        for j in range(len(hfs)):
            if np.isnan(Z[i, j]): continue
            ax.text(j, i, f"{Z[i,j]:.0f}", ha="center", va="center", fontsize=5.6,
                    color="white" if Z[i, j] < 55 else "black")
cb = fig.colorbar(im, ax=np.atleast_1d(axes).tolist(), fraction=0.02, pad=0.015)
cb.set_label("recall (%)", fontsize=8.5)
fig.suptitle("Recall over all three knobs. Value in each cell is recall %; "
             "M is scaled with N so columns are comparable across panels.",
             fontsize=9.5, color=INK, y=1.02)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(HERE, "figures", f"fig10_nmhd_heatmap.{ext}"))
plt.close(fig)
print("wrote figures/fig10_nmhd_heatmap.png/.pdf")

# ---- the usable envelope: largest corruption still at >=90%, vs alpha
fig, ax = plt.subplots(figsize=(6.0, 3.6))
cols = {64: ORANGE, 128: GREEN, 256: BLUE}
mks = {64: "^", 128: "s", 256: "o"}
for N in Ns:
    xs, ys = [], []
    for a in alphas:
        d = [r for r in rows if r["N"] == N and r["alpha"] == a and r["recall"] >= 0.90]
        xs.append(a); ys.append(100*max([r["hd_frac"] for r in d], default=0))
    ax.plot(xs, ys, mks[N]+"-", color=cols[N], lw=2, ms=7, label=f"N={N}", zorder=3)
    for x, y in zip(xs, ys):
        if y > 0:
            ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=7, color=cols[N])
ax.set_xlabel("loading  α = M / N", fontsize=8.5)
ax.set_ylabel("largest corruption still ≥90% recalled\n(% of bits)", fontsize=8.5)
ax.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.legend(frameon=False, fontsize=8)
ax.set_title("Usable operating envelope", fontsize=9.5, loc="left", pad=8)
fig.text(0.5, -0.06, "The N=256, α=0.5 point stores 0/128 patterns, so its envelope is "
         "zero. Cause not yet established:\nits training run took 30× longer than every "
         "other cell, so this may be the optimiser hitting its iteration cap "
         "rather than a capacity limit.",
         ha="center", fontsize=7.5, color=MUTED)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(HERE, "figures", f"fig11_envelope.{ext}"))
print("wrote figures/fig11_envelope.png/.pdf")
