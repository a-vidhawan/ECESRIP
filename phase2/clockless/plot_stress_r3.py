#!/usr/bin/env python3
"""
Plots for Round 3 (targeted) stress tests.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LogNorm

RES = os.path.join(os.path.dirname(__file__), "results")
PLOT_DIR = os.path.join(RES, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

N = 16
PATTERNS_INT = [0xfca6, 0x1b95, 0xa6b6, 0xbd07]
PAT_LABELS = ["P0=0xfca6", "P1=0x1b95", "P2=0xa6b6", "P3=0xbd07"]

MODE_COLORS = {"depth": "#e74c3c", "even_odd": "#2980b9", "noise": "#27ae60"}
MODE_ALPHA  = {"depth": 0.85,     "even_odd": 0.85,      "noise": 0.6}


def _load(name):
    path = os.path.join(RES, f"stress_r3_{name}.csv")
    if not os.path.exists(path):
        print(f"  [skip] {path} not found")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  Loaded {name}: {len(df)} rows")
    return df


def plot_universal_oscillators():
    df = _load("universal_osc")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP E: Universal Oscillator Surgery\n"
                 "32 states that oscillate in BOTH depth & even_odd modes", fontsize=12)

    by_todd = df.groupby("t_odd").apply(
        lambda x: {
            "settled": (x.outcome != "oscillated").mean(),
            "correct": (x.outcome == "correct").mean(),
            "oscillated": (x.outcome == "oscillated").mean(),
        }
    ).apply(pd.Series)

    ax = axes[0]
    ax.plot(by_todd.index, by_todd["settled"], "b-o", markersize=5, label="settled rate")
    ax.plot(by_todd.index, by_todd["correct"], "g-s", markersize=5, label="correct rate")
    ax.plot(by_todd.index, by_todd["oscillated"], "r-^", markersize=5, label="oscillation rate")
    ax.axvline(x=10, color="gray", ls="--", alpha=0.7, label="T_EVEN=10")
    ax.set_xlabel("T_ODD")
    ax.set_ylabel("Fraction")
    ax.set_title("Universal Oscillators vs T_ODD")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    # Heatmap: per-state settled rate vs T_ODD
    ax2 = axes[1]
    states = sorted(df["init_state"].unique())
    t_odds = sorted(df["t_odd"].unique())
    mat = np.zeros((len(states), len(t_odds)))
    for j, t_odd in enumerate(t_odds):
        sub = df[df["t_odd"] == t_odd]
        for i, st in enumerate(states):
            row = sub[sub["init_state"] == st]
            if not row.empty:
                mat[i, j] = (row.outcome != "oscillated").mean()
    im = ax2.imshow(mat, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1,
                    extent=[t_odds[0]-0.5, t_odds[-1]+0.5, len(states)-0.5, -0.5])
    plt.colorbar(im, ax=ax2, label="settled rate")
    ax2.axvline(x=10, color="white", ls="--", alpha=0.8, lw=1.5)
    ax2.set_xlabel("T_ODD")
    ax2.set_ylabel("State index")
    ax2.set_title("Per-State Settled Rate")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_E_universal_osc.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_spurious_basin():
    df = _load("spurious_basin")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP F: Attractor Basin Sizes\nWhich fixed points capture the most states?", fontsize=12)

    sp_int = set([
        0x0000, 0x5555, 0xaaaa, 0xffff,  # corners
    ])  # we'll compute from data

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        settled = sub[sub.outcome.isin(["correct", "spurious", "wrong_pattern", "stored_attractor"])]
        counts = settled["result_state"].value_counts()
        total = len(sub)

        pat_hexes = {f"{p:04x}" for p in PATTERNS_INT}
        colors = ["#2ecc71" if s in pat_hexes else "#e74c3c" for s in counts.index[:20]]
        bars = ax.bar(range(min(len(counts), 20)), counts.values[:20] / total,
                      color=colors, alpha=0.8)
        ax.set_xticks(range(min(len(counts), 20)))
        ax.set_xticklabels([s for s in counts.index[:20]], rotation=75, fontsize=7)
        ax.set_xlabel("Attractor (hex)")
        ax.set_ylabel("Fraction of all states")
        ax.set_title(f"{mode}: Attractor Basin Fractions")
        ax.grid(True, axis="y", alpha=0.3)
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(color="#2ecc71", label="stored"),
                            Patch(color="#e74c3c", label="spurious")], fontsize=8)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_F_spurious_basin.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_neuron_fault():
    df = _load("neuron_fault")
    if df.empty:
        return
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("EXP G: Neuron Fault Injection\nRecall rate when each neuron is forced to 0 or 1", fontsize=12)

    for row_i, mode in enumerate(["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        for col_i, fault_val in enumerate([0, 1]):
            ax = axes[row_i][col_i]
            fsub = sub[sub["fault_val"] == fault_val]
            for eta in [0.0, 0.10, 0.20]:
                esub = fsub[fsub["eta"].round(2) == round(eta, 2)]
                per_n = esub.groupby("fault_neuron").apply(
                    lambda x: (x.outcome == "correct").mean()
                ).values
                ax.plot(range(N), per_n, marker="o", markersize=4,
                        label=f"η={eta:.0%}", alpha=0.8)
            ax.set_xlabel("Neuron index")
            ax.set_ylabel("Correct recall rate")
            ax.set_title(f"{mode}: fault_val={fault_val}")
            ax.legend(fontsize=8)
            ax.set_ylim(0, 1.05)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0.5, color="gray", ls="--", alpha=0.5)
            ax.set_xticks(range(N))

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_G_neuron_fault.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_partial_completion():
    df = _load("partial")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP I: Partial Pattern Completion\n"
                 "How many bits must be correct for >50% recall?", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        grouped = sub.groupby("k_correct").apply(
            lambda x: pd.Series({
                "correct": (x.outcome == "correct").mean(),
                "settled": (x.outcome != "oscillated").mean(),
                "oscillated": (x.outcome == "oscillated").mean(),
            })
        )
        ax.plot(grouped.index, grouped["correct"], "g-o", markersize=5, label="correct")
        ax.plot(grouped.index, grouped["settled"], "b-s", markersize=5, label="settled")
        ax.plot(grouped.index, grouped["oscillated"], "r-^", markersize=5, label="oscillated")
        ax.axhline(y=0.5, color="gray", ls="--", alpha=0.7, label="50% threshold")
        threshold = grouped[grouped["correct"] >= 0.5].index.min()
        if not np.isnan(threshold):
            ax.axvline(x=threshold, color="orange", ls=":", lw=2, alpha=0.8,
                       label=f"k≥{threshold} → 50%")
        ax.axvline(x=N//2, color="gray", ls="-.", alpha=0.4, label="N/2=8")
        ax.set_xlabel("Number of correctly-set bits (k)")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}: Partial Completion")
        ax.legend(fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, N+1, 2))

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_I_partial_completion.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_symmetry_crisis():
    df = _load("symmetry")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP K: T_ODD Symmetry Crisis (T_EVEN=10)\n"
                 "Fine-grained mapping of convergence vs. T_ODD ratio", fontsize=12)

    by_todd = df.groupby(["t_odd", "eta"]).apply(
        lambda x: pd.Series({
            "correct": (x.outcome == "correct").mean(),
            "settled": (x.outcome != "oscillated").mean(),
        })
    ).reset_index()

    ax = axes[0]
    for eta in sorted(by_todd["eta"].unique()):
        sub = by_todd[by_todd["eta"].round(2) == round(eta, 2)]
        ax.plot(sub["t_odd"], sub["settled"], marker="o", markersize=4,
                label=f"η={eta:.0%}", alpha=0.85)
    ax.axvline(x=10, color="gray", ls="--", alpha=0.7, label="T_EVEN=10")
    ax.set_xlabel("T_ODD")
    ax.set_ylabel("Settled rate")
    ax.set_title("Settled Rate vs T_ODD")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    for eta in sorted(by_todd["eta"].unique()):
        sub = by_todd[by_todd["eta"].round(2) == round(eta, 2)]
        ax2.plot(sub["t_odd"], sub["correct"], marker="s", markersize=4,
                 label=f"η={eta:.0%}", alpha=0.85)
    ax2.axvline(x=10, color="gray", ls="--", alpha=0.7, label="T_EVEN=10")
    ax2.set_xlabel("T_ODD")
    ax2.set_ylabel("Correct recall rate")
    ax2.set_title("Correct Rate vs T_ODD")
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_K_symmetry_crisis.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_timeout_sweep():
    df = _load("timeout")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP L: Timeout Sensitivity\n"
                 "How much simulation time is needed for reliable settling?", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        by_timeout = sub.groupby("timeout").apply(
            lambda x: pd.Series({
                "correct": (x.outcome == "correct").mean(),
                "settled": (x.outcome != "oscillated").mean(),
            })
        ).reset_index()
        ax.semilogx(by_timeout["timeout"], by_timeout["correct"], "g-o",
                    markersize=6, label="correct", linewidth=2)
        ax.semilogx(by_timeout["timeout"], by_timeout["settled"], "b-s",
                    markersize=6, label="settled", linewidth=2)
        ax.axhline(y=0.99, color="gray", ls="--", alpha=0.5, label="99% line")
        ax.set_xlabel("Simulation timeout (ns)")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}: Timeout Sensitivity")
        ax.legend()
        ax.set_ylim(0, 1.05)
        ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_L_timeout.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_anti_corr():
    df = _load("anti_corr")
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("EXP J: Anti-Correlated & Maximally-Distant Initialization\n"
                 "Starting from bitwise complement of patterns (max Hamming distance)", fontsize=12)

    for ax, mode in zip(axes, ["depth", "even_odd"]):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        by_hd = sub.groupby("hamming_in").apply(
            lambda x: pd.Series({
                "correct": (x.outcome == "correct").mean(),
                "settled": (x.outcome != "oscillated").mean(),
                "oscillated": (x.outcome == "oscillated").mean(),
                "n": len(x),
            })
        ).reset_index()
        ax.plot(by_hd["hamming_in"], by_hd["correct"], "g-o", label="correct", markersize=5)
        ax.plot(by_hd["hamming_in"], by_hd["settled"], "b-s", label="settled", markersize=5)
        ax.plot(by_hd["hamming_in"], by_hd["oscillated"], "r-^", label="oscillated", markersize=5)
        ax.axvline(x=8, color="gray", ls="--", alpha=0.5, label="N/2=8")
        ax.set_xlabel("Hamming distance to nearest pattern")
        ax.set_ylabel("Rate")
        ax.set_title(f"{mode}")
        ax.legend()
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "r3_J_anti_corr.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    print("Plotting Round 3 results…")
    plot_universal_oscillators()
    plot_spurious_basin()
    plot_neuron_fault()
    plot_partial_completion()
    plot_symmetry_crisis()
    plot_timeout_sweep()
    plot_anti_corr()
    print(f"\nAll R3 plots saved to: {PLOT_DIR}")


if __name__ == "__main__":
    main()
