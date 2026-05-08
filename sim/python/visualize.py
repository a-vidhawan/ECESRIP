"""
Visualisations for Hopfield network benchmark results.

Usage
-----
    python visualize.py                          # uses latest CSVs in sim/results/
    python visualize.py path/to/results/dir/     # explicit results directory
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

RESULTS_DIR = Path(__file__).parent.parent / 'results'
PLOTS_DIR   = Path(__file__).parent.parent / 'plots'

RULES   = ['storkey', 'hebbian']
COLOURS = {'storkey': '#2196F3', 'hebbian': '#F44336'}
LABELS  = {'storkey': 'Storkey', 'hebbian': 'Hebbian'}

plt.rcParams.update({
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 130,
})


# ── data loading ──────────────────────────────────────────────────────────────

def load_results(results_dir: Path) -> pd.DataFrame:
    frames = []
    for rule in RULES:
        pattern = f'*{rule}*.csv'
        files = sorted(results_dir.glob(pattern))
        if not files:
            print(f"  [warn] no CSV found for rule={rule} in {results_dir}")
            continue
        df = pd.read_csv(files[-1])   # take latest
        df['rule'] = rule
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No result CSVs found in {results_dir}")
    return pd.concat(frames, ignore_index=True)


# ── plot helpers ──────────────────────────────────────────────────────────────

def savefig(fig: plt.Figure, name: str, plots_dir: Path) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    path = plots_dir / f'{name}.png'
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved → {path.relative_to(plots_dir.parent.parent)}")


# ── plots ─────────────────────────────────────────────────────────────────────

MARKERS = {'storkey': 'o', 'hebbian': 's'}

def plot_recall_vs_noise(df: pd.DataFrame, plots_dir: Path) -> None:
    """Recall accuracy vs noise fraction, one subplot per N, Storkey vs Hebbian."""
    N_vals = sorted(df['N'].unique())

    for N in N_vals:
        sub = df[df['N'] == N]
        # pick up to 4 loads that actually exist for this N
        n_loads = sorted(sub['load'].unique())
        step = max(1, len(n_loads) // 4)
        load_picks = n_loads[::step][:4]

        fig, axes = plt.subplots(1, len(load_picks), figsize=(4*len(load_picks), 4),
                                 sharey=True)
        if len(load_picks) == 1:
            axes = [axes]

        for ax, load in zip(axes, load_picks):
            for rule in RULES:
                d = sub[(sub['rule'] == rule) & (np.isclose(sub['load'], load, atol=0.005))]
                if d.empty:
                    continue
                d = d.sort_values('noise_frac')
                ax.plot(d['noise_frac'], d['recall_accuracy'],
                        marker=MARKERS[rule], ms=5, lw=1.8,
                        color=COLOURS[rule], label=LABELS[rule])
            ax.axhline(0.5, ls='--', lw=0.8, color='grey')
            ax.set_title(f'load = {load:.2f}', fontsize=10)
            ax.set_xlabel('Noise fraction')
            ax.set_ylim(-0.05, 1.05)
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

        axes[0].set_ylabel('Recall accuracy')
        handles = [plt.Line2D([0],[0], color=COLOURS[r], marker=MARKERS[r], ms=5,
                               label=LABELS[r]) for r in RULES]
        fig.legend(handles=handles, loc='upper right', frameon=False)
        fig.suptitle(f'Recall accuracy vs noise  (N={N})', fontweight='bold')
        fig.tight_layout()
        savefig(fig, f'recall_vs_noise_N{N}', plots_dir)


def plot_basin_vs_load(df: pd.DataFrame, plots_dir: Path) -> None:
    """Basin width vs load ratio, one line per N, Storkey vs Hebbian."""
    N_vals = sorted(df['N'].unique())
    fig, axes = plt.subplots(1, len(N_vals), figsize=(4*len(N_vals), 4), sharey=False)
    if len(N_vals) == 1:
        axes = [axes]

    for ax, N in zip(axes, N_vals):
        sub = df[df['N'] == N]
        for rule in RULES:
            d = (sub[sub['rule'] == rule]
                 .groupby('load')['basin_width'].max()
                 .reset_index()
                 .sort_values('load'))
            ax.plot(d['load'], d['basin_width'],
                    marker='s', ms=5, color=COLOURS[rule], label=LABELS[rule])
        ax.axvline(0.138, ls='--', lw=0.8, color='grey', label='0.138N capacity')
        ax.set_xlabel('Load ratio M/N')
        ax.set_title(f'N = {N}')
        ax.set_ylabel('Basin width (bits)')
        ax.legend(fontsize=9, frameon=False)

    fig.suptitle('Basin of attraction width vs load ratio', fontweight='bold')
    fig.tight_layout()
    savefig(fig, 'basin_vs_load', plots_dir)


def plot_spurious_vs_load(df: pd.DataFrame, plots_dir: Path) -> None:
    """Spurious state rate vs load ratio, all N, Storkey vs Hebbian."""
    N_vals = sorted(df['N'].unique())
    fig, ax = plt.subplots(figsize=(7, 4))

    linestyles = ['-', '--', ':', '-.', (0,(3,1,1,1)), (0,(5,2))]

    for rule in RULES:
        for i, N in enumerate(N_vals):
            d = (df[(df['rule'] == rule) & (df['N'] == N)]
                 .groupby('load')['spurious_rate'].mean()
                 .reset_index()
                 .sort_values('load'))
            ax.plot(d['load'], d['spurious_rate'],
                    color=COLOURS[rule], ls=linestyles[i % len(linestyles)],
                    lw=1.8, label=f'{LABELS[rule]}  N={N}')

    ax.axvline(0.138, ls='--', lw=1, color='black', alpha=0.4, label='0.138N threshold')
    ax.set_xlabel('Load ratio M/N')
    ax.set_ylabel('Spurious state rate')
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.set_title('Spurious state rate vs load ratio', fontweight='bold')
    fig.tight_layout()
    savefig(fig, 'spurious_vs_load', plots_dir)


def plot_recall_heatmap(df: pd.DataFrame, plots_dir: Path) -> None:
    """Heatmap of recall accuracy over (load, noise_frac) per rule."""
    fig, axes = plt.subplots(1, len(RULES), figsize=(6*len(RULES), 4))
    if len(RULES) == 1:
        axes = [axes]

    # aggregate over N
    agg = (df.groupby(['rule', 'load', 'noise_frac'])['recall_accuracy']
             .mean().reset_index())

    for ax, rule in zip(axes, RULES):
        d = agg[agg['rule'] == rule]
        pivot = d.pivot(index='noise_frac', columns='load', values='recall_accuracy')
        pivot = pivot.sort_index(ascending=False)

        im = ax.imshow(pivot.values, aspect='auto', vmin=0, vmax=1,
                       cmap='RdYlGn', origin='upper')

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f'{v:.2f}' for v in pivot.columns], rotation=45, ha='right')
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([f'{v:.0%}' for v in pivot.index])
        ax.set_xlabel('Load ratio M/N')
        ax.set_ylabel('Noise fraction')
        ax.set_title(LABELS[rule], fontweight='bold')
        plt.colorbar(im, ax=ax, label='Recall accuracy')

    fig.suptitle('Recall accuracy heatmap (averaged over N)', fontweight='bold')
    fig.tight_layout()
    savefig(fig, 'recall_heatmap', plots_dir)


def plot_convergence(df: pd.DataFrame, plots_dir: Path) -> None:
    """Mean convergence sweeps vs load ratio at zero noise."""
    d0 = df[df['noise_frac'] == 0.0]
    fig, ax = plt.subplots(figsize=(6, 4))
    N_vals = sorted(d0['N'].unique())
    linestyles = ['-', '--', ':', '-.']

    for rule in RULES:
        for i, N in enumerate(N_vals):
            d = (d0[(d0['rule'] == rule) & (d0['N'] == N)]
                 .sort_values('load'))
            ax.plot(d['load'], d['mean_convergence_iters'],
                    color=COLOURS[rule], ls=linestyles[i % len(linestyles)],
                    lw=1.8, label=f'{LABELS[rule]}  N={N}')

    ax.axvline(0.138, ls='--', lw=1, color='black', alpha=0.4, label='0.138N threshold')
    ax.set_xlabel('Load ratio M/N')
    ax.set_ylabel('Mean sweeps to convergence')
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.set_title('Convergence speed vs load ratio (zero noise)', fontweight='bold')
    fig.tight_layout()
    savefig(fig, 'convergence_vs_load', plots_dir)


# ── main ──────────────────────────────────────────────────────────────────────

def main(results_dir: Path, plots_dir: Path) -> None:
    print(f"Loading results from {results_dir}")
    df = load_results(results_dir)
    print(f"  {len(df)} rows  |  N={sorted(df['N'].unique())}  "
          f"rules={sorted(df['rule'].unique())}\n")

    print("Generating plots…")
    plot_recall_vs_noise(df, plots_dir)
    plot_basin_vs_load(df, plots_dir)
    plot_spurious_vs_load(df, plots_dir)
    plot_recall_heatmap(df, plots_dir)
    plot_convergence(df, plots_dir)
    print(f"\nAll plots saved to {plots_dir}/")


if __name__ == '__main__':
    rdir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DIR
    main(rdir, PLOTS_DIR)
