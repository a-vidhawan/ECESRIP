#!/usr/bin/env python3
"""
Plots for additional stress tests (run_additional_stress.py results).
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = os.path.join(os.path.dirname(__file__), "results")
PLOT_DIR = os.path.join(RES, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

N = 16
PATTERNS_INT = [0xfca6, 0x1b95, 0xa6b6, 0xbd07]


def _load(name, prefix="stress_add_"):
    path = os.path.join(RES, f"{prefix}{name}.csv")
    if not os.path.exists(path):
        print(f"  [skip] {path} not found")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  Loaded {name}: {len(df)} rows")
    return df


def plot_noise_scale():
    df = _load("noise_scale")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP A: Delay Noise Scale Sweep\n"
                 "How much delay perturbation (±scale units) affects settling?", fontsize=12)

    # Group by (noise_scale, noise_seed): compute mean correct and settled
    grp = df.groupby(["noise_scale", "noise_seed"]).apply(
        lambda x: pd.Series({
            "correct": (x.outcome == "correct").mean(),
            "settled": (x.outcome != "oscillated").mean(),
        })
    ).reset_index()

    ax = axes[0]
    by_scale = grp.groupby("noise_scale").agg(
        correct_mean=("correct", "mean"),
        correct_std=("correct", "std"),
        settled_mean=("settled", "mean"),
        settled_std=("settled", "std"),
    ).reset_index()
    ax.errorbar(by_scale["noise_scale"], by_scale["correct_mean"],
                yerr=by_scale["correct_std"],
                marker="o", color="#2ecc71", linewidth=2, markersize=6,
                label="correct (mean ± std)")
    ax.errorbar(by_scale["noise_scale"], by_scale["settled_mean"],
                yerr=by_scale["settled_std"],
                marker="s", color="#3498db", linewidth=2, markersize=6,
                label="settled (mean ± std)")
    ax.set_xlabel("Delay noise scale (±units)")
    ax.set_ylabel("Rate")
    ax.set_title("Mean ± Std over Seeds")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    # Boxplot per scale
    ax2 = axes[1]
    scales = sorted(grp["noise_scale"].unique())
    data_correct = [grp[grp["noise_scale"] == s]["correct"].values for s in scales]
    bp = ax2.boxplot(data_correct, positions=range(len(scales)), widths=0.5,
                     patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#2ecc71")
        patch.set_alpha(0.7)
    ax2.set_xticks(range(len(scales)))
    ax2.set_xticklabels([f"{s}" for s in scales])
    ax2.set_xlabel("Delay noise scale")
    ax2.set_ylabel("Correct rate")
    ax2.set_title("Seed-to-Seed Variance")
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "add_A_noise_scale.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_large_noise():
    df = _load("large_noise")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP B: Large Noise Seed Sweep (scale=2.0)\n"
                 "50 random delay configurations — seed-to-seed variance", fontsize=12)

    grp = df.groupby("noise_seed").apply(
        lambda x: pd.Series({
            "correct": (x.outcome == "correct").mean(),
            "settled": (x.outcome != "oscillated").mean(),
        })
    ).reset_index()

    ax = axes[0]
    ax.plot(grp["noise_seed"], grp["correct"], "g-o", markersize=4, alpha=0.8, label="correct")
    ax.plot(grp["noise_seed"], grp["settled"], "b-s", markersize=4, alpha=0.8, label="settled")
    ax.axhline(grp["correct"].mean(), color="green", ls="--", alpha=0.7,
               label=f"mean correct={grp['correct'].mean():.1%}")
    ax.axhline(grp["settled"].mean(), color="blue", ls="--", alpha=0.7,
               label=f"mean settled={grp['settled'].mean():.1%}")
    ax.set_xlabel("Noise seed")
    ax.set_ylabel("Rate")
    ax.set_title("Per-Seed Results")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.hist(grp["correct"], bins=20, alpha=0.7, color="#2ecc71", label="correct")
    ax2.hist(grp["settled"], bins=20, alpha=0.7, color="#3498db", label="settled")
    ax2.set_xlabel("Rate")
    ax2.set_ylabel("Count")
    ax2.set_title("Distribution Across Seeds")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "add_B_large_noise.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_ratio_sweep():
    df = _load("ratio_sweep")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP C: T_ODD/T_EVEN Ratio Sweep (T_EVEN=10 fixed)\n"
                 "Symmetry crisis: ratio=1.0 causes massive oscillation", fontsize=12)

    by_ratio = df.groupby(["ratio", "eta"]).apply(
        lambda x: pd.Series({
            "correct": (x.outcome == "correct").mean(),
            "settled": (x.outcome != "oscillated").mean(),
        })
    ).reset_index()

    ax = axes[0]
    for eta in sorted(by_ratio["eta"].unique()):
        sub = by_ratio[by_ratio["eta"].round(2) == round(eta, 2)]
        ax.semilogx(sub["ratio"], sub["settled"], marker="o", markersize=5,
                    label=f"η={eta:.0%}", alpha=0.85)
    ax.axvline(x=1.0, color="red", ls="--", alpha=0.7, label="ratio=1 (crisis)")
    ax.set_xlabel("T_ODD/T_EVEN ratio")
    ax.set_ylabel("Settled rate")
    ax.set_title("Convergence vs Ratio")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(True, which="both", alpha=0.3)

    ax2 = axes[1]
    for eta in sorted(by_ratio["eta"].unique()):
        sub = by_ratio[by_ratio["eta"].round(2) == round(eta, 2)]
        ax2.semilogx(sub["ratio"], sub["correct"], marker="s", markersize=5,
                     label=f"η={eta:.0%}", alpha=0.85)
    ax2.axvline(x=1.0, color="red", ls="--", alpha=0.7, label="ratio=1 (crisis)")
    ax2.set_xlabel("T_ODD/T_EVEN ratio")
    ax2.set_ylabel("Correct recall rate")
    ax2.set_title("Recall vs Ratio")
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "add_C_ratio_sweep.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    print("Plotting additional stress test results…")
    plot_noise_scale()
    plot_large_noise()
    plot_ratio_sweep()
    print(f"\nAll additional plots saved to: {PLOT_DIR}")


if __name__ == "__main__":
    main()
