#!/usr/bin/env python3
"""
Plots for Round 4 and Round 5 stress tests.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

RES = os.path.join(os.path.dirname(__file__), "results")
PLOT_DIR = os.path.join(RES, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

N = 16
PATTERNS_INT = [0xfca6, 0x1b95, 0xa6b6, 0xbd07]
PAT_LABELS = ["P0", "P1", "P2", "P3"]
MODE_COLORS = {"depth": "#e74c3c", "even_odd": "#2980b9"}


def _load(name):
    path = os.path.join(RES, f"stress_r4_{name}.csv")
    if not os.path.exists(path):
        path2 = os.path.join(RES, f"stress_r5_{name}.csv")
        if os.path.exists(path2):
            path = path2
        else:
            print(f"  [skip] {name} not found")
            return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  Loaded {name}: {len(df)} rows")
    return df


def plot_bifurcation():
    df = _load("bifurcation")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP M: T_ODD Bifurcation (T_EVEN=10)\n"
                 "Universal oscillators vs. random patterns at T_ODD boundary", fontsize=12)

    # Separate universal oscillators (first 32 rows per t_odd) from random
    n_osc = 32
    by_todd = df.groupby("t_odd")
    t_odds = sorted(df["t_odd"].unique())

    u_settled, u_correct, r_settled, r_correct = [], [], [], []
    for t_odd in t_odds:
        sub = df[df["t_odd"] == t_odd]
        u = sub.iloc[:n_osc]
        r = sub.iloc[n_osc:]
        u_settled.append((u.outcome != "oscillated").mean())
        u_correct.append((u.outcome == "correct").mean())
        r_settled.append((r.outcome != "oscillated").mean())
        r_correct.append((r.outcome == "correct").mean())

    ax = axes[0]
    ax.plot(t_odds, u_settled, "r-o", label="univ_osc settled", markersize=5)
    ax.plot(t_odds, r_settled, "b-s", label="random settled", markersize=5)
    ax.axvline(x=10, color="gray", ls="--", alpha=0.7, label="T_EVEN=10")
    ax.set_xlabel("T_ODD")
    ax.set_ylabel("Settled rate")
    ax.set_title("Settled Rate")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(t_odds, u_correct, "r-o", label="univ_osc correct", markersize=5)
    ax2.plot(t_odds, r_correct, "b-s", label="random correct", markersize=5)
    ax2.axvline(x=10, color="gray", ls="--", alpha=0.7, label="T_EVEN=10")
    ax2.set_xlabel("T_ODD")
    ax2.set_ylabel("Correct rate")
    ax2.set_title("Correct Rate")
    ax2.legend()
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r4_M_bifurcation.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_lut_corruption():
    df = _load("lut_corrupt")
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("EXP N: LUT Entry Corruption\n"
                 "Recall degradation as fraction of LUT entries are randomly flipped", fontsize=12)

    by_pct = df.groupby("corruption_pct").agg(
        correct=("correct", "mean"),
        correct_std=("correct", "std"),
        settled=("settled", "mean"),
    ).reset_index()

    ax.errorbar(by_pct["corruption_pct"] * 100, by_pct["correct"],
                yerr=by_pct["correct_std"].fillna(0),
                marker="o", color="#2ecc71", label="correct", linewidth=2, markersize=6)
    ax.plot(by_pct["corruption_pct"] * 100, by_pct["settled"],
            marker="s", color="#3498db", label="settled", linewidth=2, markersize=6)
    ax.axhline(y=0.5, color="gray", ls="--", alpha=0.5, label="50% line")
    ax.set_xscale("symlog", linthresh=0.5)
    ax.set_xlabel("LUT corruption (%)")
    ax.set_ylabel("Rate")
    ax.set_title("LUT Corruption Tolerance")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r4_N_lut_corruption.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_interpolation():
    df = _load("interpolation")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP O: Pattern Interpolation\n"
                 "Walking Hamming path from P_i to P_j, measuring recall at each step", fontsize=12)

    pairs = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
    colors = plt.cm.tab10(np.linspace(0, 0.6, len(pairs)))

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        for ci, (src, tgt) in enumerate(pairs):
            pair_sub = sub[(sub["src_pat"] == src) & (sub["tgt_pat"] == tgt)]
            if pair_sub.empty:
                continue
            hd_total = pair_sub["interp_step"].max()
            by_step = pair_sub.groupby("interp_step").apply(
                lambda x: (x.outcome == "correct").mean()
            )
            norm_steps = by_step.index / max(1, hd_total)
            ax.plot(norm_steps, by_step.values, color=colors[ci], marker="o",
                    markersize=3, label=f"P{src}→P{tgt}", alpha=0.75)
        ax.axhline(y=0.5, color="gray", ls="--", alpha=0.5)
        ax.axvline(x=0.5, color="gray", ls="-.", alpha=0.3)
        ax.set_xlabel("Interpolation fraction (0=P_i, 1=P_j)")
        ax.set_ylabel("Correct recall rate")
        ax.set_title(f"{mode}: Pattern Interpolation")
        ax.legend(fontsize=7, ncol=2)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r4_O_interpolation.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_state_map():
    df = _load("state_map")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP P: Full State Space Map (Python Synchronous Sim)\n"
                 "All 65536 states mapped to their attractor", fontsize=12)

    # Recall by Hamming distance
    ax = axes[0]
    by_hd = df.groupby("hamming_to_nearest").apply(
        lambda x: pd.Series({
            "stored": (x.label == "stored").mean(),
            "spurious": (x.label == "spurious").mean(),
            "cycle": (x.label == "cycle").mean(),
            "n": len(x),
        })
    ).reset_index()
    ax.stackplot(by_hd["hamming_to_nearest"],
                 by_hd["stored"], by_hd["spurious"], by_hd["cycle"],
                 labels=["stored", "spurious", "cycle/timeout"],
                 colors=["#2ecc71", "#e74c3c", "#95a5a6"], alpha=0.8)
    ax.set_xlabel("Hamming distance to nearest stored pattern")
    ax.set_ylabel("Fraction of states")
    ax.set_title("Outcome Distribution by HD")
    ax.legend(loc="upper left")
    ax.set_xlim(0, N)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)

    # Basin size distribution
    ax2 = axes[1]
    basin_sizes = df[df["label"].isin(["stored", "spurious"])]["attractor"].value_counts()
    pat_hexes = {f"{p:04x}" for p in PATTERNS_INT}
    colors = ["#2ecc71" if s in pat_hexes else "#e74c3c" for s in basin_sizes.index[:20]]
    ax2.bar(range(min(20, len(basin_sizes))), basin_sizes.values[:20],
            color=colors, alpha=0.85)
    ax2.set_xticks(range(min(20, len(basin_sizes))))
    ax2.set_xticklabels([s for s in basin_sizes.index[:20]], rotation=75, fontsize=7)
    ax2.set_xlabel("Attractor")
    ax2.set_ylabel("Basin size (# states)")
    ax2.set_title("Top 20 Basins of Attraction")
    from matplotlib.patches import Patch
    ax2.legend(handles=[Patch(color="#2ecc71", label="stored"),
                         Patch(color="#e74c3c", label="spurious")], fontsize=9)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r4_P_state_map.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_confusion():
    df = _load("confusion")
    if df.empty:
        return
    pat_hexes = [f"{p:04x}" for p in PATTERNS_INT]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP Q: Pattern Confusion Matrix\n"
                 "Where do states near P_i converge to at different noise levels?", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        by_eta = sub.groupby(sub["eta"].round(2)).apply(
            lambda x: (x.outcome == "correct").mean()
        )
        ax.plot(by_eta.index, by_eta.values, "g-o", markersize=5, linewidth=2, label="correct")
        settled = sub.groupby(sub["eta"].round(2)).apply(
            lambda x: (x.outcome != "oscillated").mean()
        )
        ax.plot(settled.index, settled.values, "b-s", markersize=5, linewidth=2, label="settled")
        ax.axhline(y=0.5, color="gray", ls="--", alpha=0.5)
        ax.set_xlabel("Noise η")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}: Correct vs η")
        ax.legend()
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r4_Q_confusion.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_exhaustive_basin():
    df = _load("exhaustive_basin")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP T: Exhaustive HD≤5 Basin (SV Simulation)\n"
                 "Every state within Hamming distance 5 of any pattern", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        by_hd = sub.groupby("hamming_in").apply(
            lambda x: pd.Series({
                "correct": (x.outcome == "correct").mean(),
                "settled": (x.outcome != "oscillated").mean(),
                "n": len(x),
            })
        )
        ax.plot(by_hd.index, by_hd["correct"], "g-o", markersize=6, linewidth=2,
                label="correct")
        ax.plot(by_hd.index, by_hd["settled"], "b-s", markersize=6, linewidth=2,
                label="settled")
        for hd, row in by_hd.iterrows():
            ax.annotate(f"n={int(row.n)}", (hd, row.correct),
                        textcoords="offset points", xytext=(0, 8), fontsize=7,
                        ha="center")
        ax.axhline(y=0.5, color="gray", ls="--", alpha=0.5)
        ax.set_xlabel("Hamming distance to nearest pattern")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}: Basin Recall Curve")
        ax.legend()
        ax.set_ylim(0, 1.05)
        ax.set_xticks(range(6))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r5_T_exhaustive_basin.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_t_even_sweep():
    df = _load("t_even_sweep")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP U: T_EVEN Sweep (T_ODD=24 fixed)\n"
                 "How even-neuron timing affects convergence", fontsize=12)

    by_teven = df.groupby(["t_even", "eta"]).apply(
        lambda x: pd.Series({
            "correct": (x.outcome == "correct").mean(),
            "settled": (x.outcome != "oscillated").mean(),
        })
    ).reset_index()

    ax = axes[0]
    for eta in sorted(by_teven["eta"].unique()):
        sub = by_teven[by_teven["eta"].round(2) == round(eta, 2)]
        ax.plot(sub["t_even"], sub["settled"], marker="o", markersize=4,
                label=f"η={eta:.0%}", alpha=0.85)
    ax.axvline(x=24, color="gray", ls="--", alpha=0.7, label="T_ODD=24")
    ax.set_xlabel("T_EVEN")
    ax.set_ylabel("Settled rate")
    ax.set_title("Settled Rate vs T_EVEN")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    for eta in sorted(by_teven["eta"].unique()):
        sub = by_teven[by_teven["eta"].round(2) == round(eta, 2)]
        ax2.plot(sub["t_even"], sub["correct"], marker="s", markersize=4,
                 label=f"η={eta:.0%}", alpha=0.85)
    ax2.axvline(x=24, color="gray", ls="--", alpha=0.7, label="T_ODD=24 (equal)")
    ax2.set_xlabel("T_EVEN")
    ax2.set_ylabel("Correct rate")
    ax2.set_title("Correct Rate vs T_EVEN")
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r5_U_t_even_sweep.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_att_stability():
    df = _load("att_stability")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP V: Attractor Local Stability\n"
                 "Recall from 1-bit perturbations of each fixed point", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        # Per-attractor: fraction of 1-bit neighbors that return to same FP
        sub2 = sub.copy()
        sub2["return_same"] = sub2["result_state"] == sub2["source_fp"]
        by_fp = sub2.groupby(["source_fp", "is_stored"])["return_same"].mean().reset_index()
        by_fp.columns = ["source_fp", "is_stored", "return_rate"]
        stored = by_fp[by_fp["is_stored"]]
        spurious = by_fp[~by_fp["is_stored"]]
        ax.hist(spurious["return_rate"], bins=15, alpha=0.7, color="#e74c3c",
                label="spurious FPs", density=True)
        ax.hist(stored["return_rate"], bins=10, alpha=0.7, color="#2ecc71",
                label="stored FPs", density=True)
        ax.set_xlabel("Fraction of 1-bit neighbors returning to same FP")
        ax.set_ylabel("Density")
        ax.set_title(f"{mode}: Attractor Stability")
        ax.legend()
        ax.set_xlim(0, 1.05)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r5_V_att_stability.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_seq_perturb():
    df = _load("seq_perturb")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP W: Sequential Perturbation Recovery\n"
                 "k sequential random bit flips from a stored pattern", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        by_k = sub.groupby("k_flips").apply(
            lambda x: pd.Series({
                "correct": (x.outcome == "correct").mean(),
                "settled": (x.outcome != "oscillated").mean(),
                "mean_hd": x["hamming_in"].mean(),
            })
        )
        ax.plot(by_k.index, by_k["correct"], "g-o", markersize=6, linewidth=2,
                label="correct")
        ax.plot(by_k.index, by_k["settled"], "b-s", markersize=6, linewidth=2,
                label="settled")
        ax2 = ax.twinx()
        ax2.plot(by_k.index, by_k["mean_hd"], "k--", markersize=4, alpha=0.5,
                 label="mean HD")
        ax2.set_ylabel("Mean Hamming distance", color="gray")
        ax2.tick_params(axis="y", colors="gray")
        ax.axhline(y=0.5, color="gray", ls=":", alpha=0.5)
        ax.set_xlabel("k (number of sequential bit flips)")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}")
        ax.legend(loc="upper right")
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(1, 10))

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r5_W_seq_perturb.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    print("Plotting Round 4 & 5 results…")
    plot_bifurcation()
    plot_lut_corruption()
    plot_interpolation()
    plot_state_map()
    plot_confusion()
    plot_exhaustive_basin()
    plot_t_even_sweep()
    plot_att_stability()
    plot_seq_perturb()
    print(f"\nAll R4/R5 plots saved to: {PLOT_DIR}")


if __name__ == "__main__":
    main()
