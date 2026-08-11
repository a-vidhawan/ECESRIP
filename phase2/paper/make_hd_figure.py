#!/usr/bin/env python3
"""Recall vs corruption level, in absolute bits and as a fraction of N."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "..", "clockless", "results", "hd_sweep.json")))
BLUE, VERM, GREEN, ORANGE, PINK = "#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d4"
plt.rcParams.update({"font.family": "serif", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 150,
    "savefig.bbox": "tight"})

cases = sorted({(r["N"], r["M"]) for r in rows})
style = {(64,8):(ORANGE,"^"),(64,16):(ORANGE,"s"),(64,32):(ORANGE,"o"),
         (128,16):(GREEN,"s"),(128,32):(GREEN,"o"),
         (256,16):(BLUE,"s"),(256,32):(BLUE,"o")}
fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8))
for N, M in cases:
    d = [r for r in rows if r["N"] == N and r["M"] == M]
    c, mk = style.get((N, M), (PINK, "d"))
    lbl = f"N={N}, M={M}"
    axes[0].plot([r["hd"] for r in d], [100*r["recall"] for r in d],
                 mk+"-", color=c, lw=1.8, ms=5, label=lbl, zorder=3)
    axes[1].plot([100*r["hd_frac"] for r in d], [100*r["recall"] for r in d],
                 mk+"-", color=c, lw=1.8, ms=5, label=lbl, zorder=3)
axes[0].set_xlabel("corrupted bits (absolute HD)", fontsize=8.5)
axes[0].set_title("Absolute corruption", fontsize=9.5, loc="left", pad=8)
axes[1].set_xlabel("corrupted bits as % of N", fontsize=8.5)
axes[1].set_title("Relative corruption", fontsize=9.5, loc="left", pad=8)
for ax in axes:
    ax.set_ylabel("recall (%)", fontsize=8.5); ax.set_ylim(-4, 106)
axes[1].axvline(50, color=MUTED, ls="--", lw=1.1)
axes[1].text(44, 55, "HD = N/2\n(no information left)", fontsize=7.5,
             color=MUTED, ha="right")
axes[0].legend(frameon=False, fontsize=7.5, loc="upper right")
fig.suptitle("Bigger networks tolerate far more corruption — both in absolute "
             "bits and as a fraction of the pattern",
             fontsize=10, color=INK, y=1.03)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(HERE, "figures", f"fig9_hd_sweep.{ext}"))
print("wrote figures/fig9_hd_sweep.png/.pdf")
for N, M in cases:
    d = [r for r in rows if r["N"] == N and r["M"] == M]
    ok = [r for r in d if r["recall"] >= 0.90]
    if ok:
        b = max(ok, key=lambda r: r["hd"])
        print(f"  N={N:>3} M={M:>2}: >=90% recall out to HD={b['hd']:>2} "
              f"({100*b['hd_frac']:.0f}% of bits)")
