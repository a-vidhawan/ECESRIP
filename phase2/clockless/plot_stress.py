#!/usr/bin/env python3
"""
Comprehensive visualization of clockless HNN stress test results.
Produces multi-panel figures from stress_*.csv files.
"""

import os, sys, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LogNorm
from scipy import stats

RES  = os.path.join(os.path.dirname(__file__), "results")
PLOT = os.path.join(RES, "plots")
os.makedirs(PLOT, exist_ok=True)

MODE_COLORS = {"depth": "#2196F3", "even_odd": "#FF5722", "noise": "#4CAF50"}
MODE_LABELS = {"depth": "Depth (LUT-based)", "even_odd": "Even/Odd bipartite",
               "noise": "Depth + ε noise"}


def load(name: str) -> pd.DataFrame:
    path = os.path.join(RES, f"stress_{name}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df


def savefig(fig, name: str):
    path = os.path.join(PLOT, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


# ─── Figure 1: Noise sweep ────────────────────────────────────────────────────
def plot_noise_sweep():
    df = load("noise_sweep")
    if df.empty:
        return
    print("Plotting noise sweep…")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Clockless HNN: Noise Sweep (η = 0→60%)", fontsize=14, fontweight="bold")

    metrics = [
        ("correct",     "Correct Recall Rate",   "Fraction of tests → correct pattern"),
        ("settled",     "Convergence Rate",       "Fraction of tests that settle"),
        ("settle_time", "Mean Settle Time (ns)",  "Mean simulation time to stable state"),
    ]

    for ax, (col, title, ylabel) in zip(axes, metrics):
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            if sub.empty:
                continue
            grp = sub.groupby("eta")[col].mean()
            ax.plot(grp.index * 100, grp.values * (1 if col != "settle_time" else 1),
                    color=MODE_COLORS[mode], label=MODE_LABELS[mode],
                    linewidth=2, marker="o", markersize=4)
            ax.fill_between(
                grp.index * 100,
                sub.groupby("eta")[col].mean() - sub.groupby("eta")[col].sem(),
                sub.groupby("eta")[col].mean() + sub.groupby("eta")[col].sem(),
                alpha=0.15, color=MODE_COLORS[mode]
            )
        ax.set_xlabel("Noise level η (%)", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        if col in ("correct", "settled"):
            ax.set_ylim(-0.05, 1.05)
        ax.set_xlim(-1, 62)

    plt.tight_layout()
    savefig(fig, "01_noise_sweep")


# ─── Figure 2: Hamming distance sweep ────────────────────────────────────────
def plot_hamming_sweep():
    df = load("hamming")
    if df.empty:
        return
    print("Plotting Hamming sweep…")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Clockless HNN: Hamming Distance Sweep (exact k bits flipped)",
                 fontsize=14, fontweight="bold")

    for mode in ["depth", "even_odd", "noise"]:
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        grp_c = sub.groupby("hamming_in")["correct"].mean()
        grp_s = sub.groupby("hamming_in")["settled"].mean()
        axes[0].plot(grp_c.index, grp_c.values, color=MODE_COLORS[mode],
                     label=MODE_LABELS[mode], linewidth=2, marker="o", markersize=4)
        axes[1].plot(grp_s.index, grp_s.values, color=MODE_COLORS[mode],
                     label=MODE_LABELS[mode], linewidth=2, marker="s", markersize=4)

    for ax in axes:
        ax.axvline(x=8, color="gray", linestyle="--", alpha=0.5, label="N/2=8")
        ax.set_xlabel("Hamming distance to target pattern", fontsize=11)
        ax.set_xlim(0.5, 16.5)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Correct recall rate", fontsize=11)
    axes[0].set_title("Correct Recall vs. Hamming Distance", fontsize=12)
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("Convergence rate (settled)", fontsize=11)
    axes[1].set_title("Convergence Rate vs. Hamming Distance", fontsize=12)
    axes[1].set_ylim(-0.05, 1.05)

    plt.tight_layout()
    savefig(fig, "02_hamming_sweep")


# ─── Figure 3: T_ODD sensitivity ─────────────────────────────────────────────
def plot_timing_sweep():
    df = load("timing_sweep")
    if df.empty:
        return
    if "t_odd" not in df.columns:
        return
    print("Plotting T_ODD sweep…")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("even_odd Mode: T_ODD Sweep (T_EVEN = 10 fixed)",
                 fontsize=14, fontweight="bold")

    t_odds = sorted(df["t_odd"].unique())
    eta_levels = sorted(df["eta"].unique())
    cmap = plt.get_cmap("plasma")
    colors = [cmap(i / max(1, len(eta_levels) - 1)) for i in range(len(eta_levels))]

    for ax, col, ylabel, title in [
        (axes[0], "settled", "Convergence rate", "Settled Rate vs. T_ODD"),
        (axes[1], "correct", "Correct recall rate", "Correct Rate vs. T_ODD"),
    ]:
        for eta, color in zip(eta_levels, colors):
            sub = df[df.eta.round(2) == round(eta, 2)]
            grp = sub.groupby("t_odd")[col].mean()
            ax.plot(grp.index, grp.values, color=color, marker="o", linewidth=2,
                    label=f"η={eta:.2f}")
        ax.axvline(x=10, color="gray", linestyle="--", alpha=0.6, label="T_EVEN=10")
        ax.set_xlabel("T_ODD (time units)", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    savefig(fig, "03_timing_sweep")


# ─── Figure 4: Delay scale sensitivity ───────────────────────────────────────
def plot_delay_scale():
    df = load("delay_scale")
    if df.empty:
        return
    if "delay_scale" not in df.columns:
        return
    print("Plotting delay scale…")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Depth Mode: Delay Scale Sensitivity",
                 fontsize=14, fontweight="bold")

    eta_levels = sorted(df["eta"].unique())
    cmap = plt.get_cmap("viridis")
    colors = [cmap(i / max(1, len(eta_levels) - 1)) for i in range(len(eta_levels))]

    scales = sorted(df["delay_scale"].unique())
    for ax, col, ylabel, title in [
        (axes[0], "settled", "Convergence rate", "Settled Rate vs. Delay Scale"),
        (axes[1], "correct", "Correct recall rate", "Correct Rate vs. Delay Scale"),
    ]:
        for eta, color in zip(eta_levels, colors):
            sub = df[df.eta.round(2) == round(eta, 2)]
            grp = sub.groupby("delay_scale")[col].mean()
            ax.plot(grp.index, grp.values, color=color, marker="o", linewidth=2,
                    label=f"η={eta:.2f}")
        ax.axvline(x=1.0, color="gray", linestyle="--", alpha=0.6, label="baseline")
        ax.set_xlabel("Delay scale factor", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    savefig(fig, "04_delay_scale")


# ─── Figure 5: Oscillation map ───────────────────────────────────────────────
def plot_oscillation():
    df = load("oscillation")
    if df.empty:
        return
    print("Plotting oscillation map…")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Clockless HNN: Oscillation / Attractor Map (State Space Survey)",
                 fontsize=14, fontweight="bold")

    outcome_colors = {
        "correct":         "#4CAF50",
        "stored_attractor": "#8BC34A",
        "wrong_pattern":   "#FFC107",
        "spurious":        "#FF9800",
        "oscillated":      "#F44336",
        "not_fixed_point": "#9C27B0",
    }

    for ax, mode in zip(axes, ["depth", "even_odd", "noise"]):
        sub = df[df["mode"] == mode].copy()
        if sub.empty:
            ax.set_title(f"{mode}")
            continue
        # Use Hamming distance to nearest pattern as x, outcome as color
        sub["init_int"] = sub["init_state"].apply(lambda x: int(x, 16))
        sub["result_int"] = sub["result_state"].apply(lambda x: int(x, 16))

        # Plot as scatter: x=Hamming to nearest, y=settle_time, color=outcome
        for outcome, color in outcome_colors.items():
            pts = sub[sub.outcome == outcome]
            if not pts.empty:
                ax.scatter(pts["hamming_in"], pts["settle_time"],
                           c=color, alpha=0.4, s=4, label=outcome.replace("_", " "))

        ax.set_xlabel("Hamming distance to nearest pattern", fontsize=10)
        ax.set_ylabel("Settle time (ns)", fontsize=10)
        ax.set_title(f"{MODE_LABELS[mode]}", fontsize=11)
        ax.legend(fontsize=7, markerscale=2)
        ax.grid(alpha=0.2)

    plt.tight_layout()
    savefig(fig, "05_oscillation_map")


# ─── Figure 6: Outcome breakdown by mode ─────────────────────────────────────
def plot_outcome_breakdown():
    # Combine all experiments for a cross-mode view
    dfs = []
    for name in ["noise_sweep", "hamming", "random", "adversarial", "extreme"]:
        d = load(name)
        if not d.empty:
            d["exp"] = name
            dfs.append(d)
    if not dfs:
        return
    df = pd.concat(dfs, ignore_index=True)
    print("Plotting outcome breakdown…")

    outcome_order = ["correct", "wrong_pattern", "stored_attractor",
                     "spurious", "oscillated", "not_fixed_point"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Outcome Breakdown by Mode (All Experiments)", fontsize=14, fontweight="bold")

    for ax, mode in zip(axes, ["depth", "even_odd", "noise"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        counts = sub["outcome"].value_counts()
        # Ensure all outcomes are represented
        for o in outcome_order:
            if o not in counts:
                counts[o] = 0
        counts = counts.reindex([o for o in outcome_order if o in counts.index or counts.get(o, 0) > 0])

        colors_list = ["#4CAF50", "#FFC107", "#8BC34A", "#FF9800", "#F44336", "#9C27B0"]
        valid = [o for o in outcome_order if o in counts.index]
        vals = [counts[o] for o in valid]
        colors_valid = [colors_list[outcome_order.index(o)] for o in valid]

        wedges, texts, autotexts = ax.pie(
            vals, labels=[o.replace("_", "\n") for o in valid],
            colors=colors_valid, autopct="%1.1f%%",
            pctdistance=0.75, startangle=90
        )
        ax.set_title(f"{MODE_LABELS[mode]}\n(N={len(sub)} tests)", fontsize=11)

    plt.tight_layout()
    savefig(fig, "06_outcome_breakdown")


# ─── Figure 7: Settle time distribution ──────────────────────────────────────
def plot_settle_time_dist():
    df = load("noise_sweep")
    if df.empty:
        return
    print("Plotting settle time distributions…")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Settle Time Distribution (Noise Sweep, Settled Tests Only)",
                 fontsize=14, fontweight="bold")

    eta_show = [0.0, 0.15, 0.30, 0.45]
    ax_flat = axes.flatten()

    for ax, eta in zip(ax_flat, eta_show):
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[(df["mode"] == mode) & (df.eta.round(2) == round(eta, 2)) & df.settled]
            if sub.empty:
                continue
            times = sub["settle_time"].values
            ax.hist(times, bins=40, alpha=0.5, color=MODE_COLORS[mode],
                    label=f"{mode} (n={len(times)})", density=True)
        ax.set_xlabel("Settle time (ns)", fontsize=10)
        ax.set_ylabel("Density", fontsize=10)
        ax.set_title(f"η = {eta*100:.0f}%", fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    savefig(fig, "07_settle_time_dist")


# ─── Figure 8: Adversarial states ────────────────────────────────────────────
def plot_adversarial():
    df = load("adversarial")
    if df.empty:
        return
    print("Plotting adversarial states…")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Adversarial States (≥5 Hamming from ALL patterns)",
                 fontsize=14, fontweight="bold")

    # Bar chart: outcome breakdown per mode
    ax = axes[0]
    outcomes = ["correct", "wrong_pattern", "stored_attractor",
                "spurious", "oscillated", "not_fixed_point"]
    colors_list = ["#4CAF50", "#FFC107", "#8BC34A", "#FF9800", "#F44336", "#9C27B0"]
    x = np.arange(len(["depth", "even_odd", "noise"]))
    width = 0.15
    bottom = np.zeros(3)
    for i, (o, c) in enumerate(zip(outcomes, colors_list)):
        heights = []
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            heights.append((sub.outcome == o).mean())
        ax.bar(x + i * width, heights, width, bottom=0, label=o.replace("_", " "), color=c)
        bottom += np.array(heights)
    ax.set_xticks(x + width * len(outcomes) / 2)
    ax.set_xticklabels(["depth", "even_odd", "noise"])
    ax.set_ylabel("Fraction of tests")
    ax.set_title("Outcome Distribution (Adversarial States)")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)

    # Scatter: settle_time vs hamming_in
    ax2 = axes[1]
    for mode in ["depth", "even_odd", "noise"]:
        sub = df[df["mode"] == mode]
        settled = sub[sub.settled]
        ax2.scatter(settled["hamming_in"], settled["settle_time"],
                    alpha=0.3, s=6, color=MODE_COLORS[mode], label=mode)
    ax2.set_xlabel("Hamming distance to nearest pattern")
    ax2.set_ylabel("Settle time (ns)")
    ax2.set_title("Settle Time for Adversarial States")
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    savefig(fig, "08_adversarial")


# ─── Figure 9: Mode comparison summary ───────────────────────────────────────
def plot_summary():
    print("Plotting summary comparison…")
    # Load all experiments
    all_dfs = {}
    for name in ["noise_sweep", "hamming", "random", "extreme", "adversarial",
                 "fp_verify", "oscillation"]:
        d = load(name)
        if not d.empty:
            all_dfs[name] = d

    if not all_dfs:
        return

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)
    fig.suptitle("Clockless HNN — Comprehensive Stress Test Summary",
                 fontsize=15, fontweight="bold")

    # Panel 1: noise sweep (correct rate)
    ax1 = fig.add_subplot(gs[0, 0])
    if "noise_sweep" in all_dfs:
        df = all_dfs["noise_sweep"]
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            grp = sub.groupby("eta")["correct"].mean()
            ax1.plot(grp.index * 100, grp.values, color=MODE_COLORS[mode],
                     label=mode, linewidth=2)
        ax1.set_xlabel("Noise η (%)")
        ax1.set_ylabel("Correct rate")
        ax1.set_title("Recall vs. Noise")
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)
        ax1.set_ylim(-0.05, 1.05)

    # Panel 2: convergence vs noise
    ax2 = fig.add_subplot(gs[0, 1])
    if "noise_sweep" in all_dfs:
        df = all_dfs["noise_sweep"]
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            grp = sub.groupby("eta")["settled"].mean()
            ax2.plot(grp.index * 100, grp.values, color=MODE_COLORS[mode],
                     label=mode, linewidth=2)
        ax2.set_xlabel("Noise η (%)")
        ax2.set_ylabel("Convergence rate")
        ax2.set_title("Convergence vs. Noise")
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3)
        ax2.set_ylim(-0.05, 1.05)

    # Panel 3: hamming sweep (settled rate)
    ax3 = fig.add_subplot(gs[0, 2])
    if "hamming" in all_dfs:
        df = all_dfs["hamming"]
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            grp = sub.groupby("hamming_in")["correct"].mean()
            ax3.plot(grp.index, grp.values, color=MODE_COLORS[mode],
                     label=mode, linewidth=2, marker="o", markersize=3)
        ax3.axvline(x=8, color="gray", ls="--", alpha=0.5, label="N/2")
        ax3.set_xlabel("Hamming distance k")
        ax3.set_ylabel("Correct rate")
        ax3.set_title("Recall vs. Hamming Dist")
        ax3.legend(fontsize=8)
        ax3.grid(alpha=0.3)
        ax3.set_ylim(-0.05, 1.05)

    # Panel 4: timing sweep (even_odd only)
    ax4 = fig.add_subplot(gs[1, 0])
    dt = load("timing_sweep")
    if not dt.empty and "t_odd" in dt.columns:
        eta_show = [0.0, 0.15, 0.30]
        cmap = plt.get_cmap("cool")
        colors_t = [cmap(i / 2) for i in range(3)]
        for eta, c in zip(eta_show, colors_t):
            sub = dt[dt.eta.round(2) == round(eta, 2)]
            grp = sub.groupby("t_odd")["settled"].mean()
            ax4.plot(grp.index, grp.values, color=c, marker="o", linewidth=2,
                     label=f"η={eta:.2f}")
        ax4.axvline(x=10, color="gray", ls="--", alpha=0.5, label="T_EVEN")
        ax4.set_xlabel("T_ODD (ns)")
        ax4.set_ylabel("Convergence rate")
        ax4.set_title("even_odd: T_ODD Sensitivity")
        ax4.legend(fontsize=8)
        ax4.grid(alpha=0.3)
        ax4.set_ylim(-0.05, 1.05)

    # Panel 5: delay scale sensitivity
    ax5 = fig.add_subplot(gs[1, 1])
    ds = load("delay_scale")
    if not ds.empty and "delay_scale" in ds.columns:
        eta_show = [0.0, 0.15, 0.30]
        cmap = plt.get_cmap("autumn")
        colors_d = [cmap(i / 2) for i in range(3)]
        for eta, c in zip(eta_show, colors_d):
            sub = ds[ds.eta.round(2) == round(eta, 2)]
            grp = sub.groupby("delay_scale")["settled"].mean()
            ax5.plot(grp.index, grp.values, color=c, marker="s", linewidth=2,
                     label=f"η={eta:.2f}")
        ax5.axvline(x=1.0, color="gray", ls="--", alpha=0.5, label="baseline")
        ax5.set_xlabel("Delay scale factor")
        ax5.set_ylabel("Convergence rate")
        ax5.set_title("Depth Mode: Delay Scale")
        ax5.legend(fontsize=8)
        ax5.grid(alpha=0.3)
        ax5.set_ylim(-0.05, 1.05)

    # Panel 6: oscillation heatmap by Hamming distance
    ax6 = fig.add_subplot(gs[1, 2])
    if "oscillation" in all_dfs:
        df_osc = all_dfs["oscillation"]
        hd_bins = np.arange(0.5, 17.5, 1)
        for mode in ["depth", "even_odd", "noise"]:
            sub = df_osc[df_osc["mode"] == mode]
            osc_rate = []
            hd_mids = []
            for hd in range(0, 17):
                pts = sub[sub.hamming_in == hd]
                if not pts.empty:
                    osc_rate.append((pts.outcome == "oscillated").mean())
                    hd_mids.append(hd)
            ax6.plot(hd_mids, osc_rate, color=MODE_COLORS[mode],
                     label=mode, linewidth=2, marker="^", markersize=4)
        ax6.axvline(x=8, color="gray", ls="--", alpha=0.5, label="N/2")
        ax6.set_xlabel("Hamming distance to nearest pattern")
        ax6.set_ylabel("Oscillation rate")
        ax6.set_title("Oscillation Rate vs. Hamming Dist")
        ax6.legend(fontsize=8)
        ax6.grid(alpha=0.3)
        ax6.set_ylim(-0.05, 1.05)

    savefig(fig, "09_summary")


# ─── Figure 10: Extreme noise cliff ──────────────────────────────────────────
def plot_extreme():
    df_n = load("noise_sweep")
    df_e = load("extreme")
    if df_n.empty or df_e.empty:
        return
    print("Plotting extreme noise cliff…")

    df = pd.concat([df_n, df_e], ignore_index=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Clockless HNN: Full Noise Sweep (0→100%) — Hard Cliff Analysis",
                 fontsize=14, fontweight="bold")

    for ax, col, ylabel in [
        (axes[0], "correct", "Correct Recall Rate"),
        (axes[1], "settled", "Convergence Rate"),
    ]:
        for mode in ["depth", "even_odd", "noise"]:
            sub = df[df["mode"] == mode]
            if sub.empty:
                continue
            grp = sub.groupby("eta")[col].mean()
            ax.plot(grp.index * 100, grp.values, color=MODE_COLORS[mode],
                    label=MODE_LABELS[mode], linewidth=2)
        ax.axvline(x=50, color="gray", ls="--", alpha=0.5, label="η=50%")
        ax.set_xlabel("Noise level η (%)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{ylabel} vs. η")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlim(-1, 102)

    plt.tight_layout()
    savefig(fig, "10_extreme_cliff")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=== Generating stress test plots ===")
    plot_noise_sweep()
    plot_hamming_sweep()
    plot_timing_sweep()
    plot_delay_scale()
    plot_oscillation()
    plot_outcome_breakdown()
    plot_settle_time_dist()
    plot_adversarial()
    plot_summary()
    plot_extreme()
    print(f"\nAll plots saved to: {PLOT}")


if __name__ == "__main__":
    main()
