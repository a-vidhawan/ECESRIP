"""
Capacity threshold comparison demo  (N=64, 8×8 random patterns)

Shows what happens to recall quality as load M/N crosses the theoretical
Storkey capacity (~0.138N ≈ 9 patterns for N=64).

Three rows — each row trains a fresh network and attempts recall of
pattern 0 from a 20%-corrupted version:
  Row 1 — M =  4  (well below threshold, ~0.06N)
  Row 2 — M =  9  (near threshold,       ~0.14N)
  Row 3 — M = 14  (above threshold,      ~0.22N)

Columns per row:
  [Target] [Corrupted] [Recalled] [All stored patterns thumbnail]

Run:
    python demo_capacity.py
Saves: demo_capacity.png

For an animated sweep over M, run:
    python demo_capacity.py --animate
Saves: demo_capacity_sweep.gif
"""

import sys
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, PillowWriter

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import random_patterns, add_noise

# ── config ────────────────────────────────────────────────────────────────────
N          = 64
SIZE       = 8
NOISE_FRAC = 0.20
SEED       = 42
MAX_SWEEPS = 40
M_VALUES   = [4, 9, 14]          # below / near / above  0.138×64 ≈ 8.8

CAPACITY   = 0.138 * N           # ~8.8

CMAP_PAT   = 'gray'


# ── helpers ───────────────────────────────────────────────────────────────────
def img(s):
    return ((s + 1) / 2).reshape(SIZE, SIZE)


def load_label(M):
    load = M / N
    if M < CAPACITY * 0.85:
        regime = 'below threshold'
    elif M <= CAPACITY * 1.15:
        regime = 'near threshold'
    else:
        regime = 'above threshold'
    return f'M = {M}  (load {load:.2f},  {regime})'


def badge(hamming, ax):
    """Overlay a ✓ or ✗ badge on axes ax."""
    if hamming == 0:
        txt, col = '✓ Perfect recall', '#27ae60'
    else:
        txt, col = f'✗  Δ = {hamming} bits', '#e74c3c'
    ax.text(0.5, -0.12, txt, transform=ax.transAxes,
            ha='center', va='top', fontsize=8.5,
            color=col, fontweight='bold')


def run_trial(M, seed):
    pats    = random_patterns(N, M, seed=seed)
    net     = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
    net.train(pats)
    rng     = np.random.default_rng(seed + 1)
    target  = pats[0]
    corrupt = add_noise(target, n_flips=int(NOISE_FRAC * N), rng=rng)
    recalled, n_sweeps, converged = net.run(corrupt, max_sweeps=MAX_SWEEPS, rng=rng)
    hamming = int((recalled != target).sum())
    return dict(pats=pats, net=net, target=target,
                corrupt=corrupt, recalled=recalled,
                n_sweeps=n_sweeps, hamming=hamming)


# ── static comparison figure ──────────────────────────────────────────────────
def make_comparison_figure():
    trials = {M: run_trial(M, SEED) for M in M_VALUES}

    fig = plt.figure(figsize=(14, len(M_VALUES) * 3.6 + 1.2), facecolor='white')
    fig.suptitle(
        f'Hopfield Capacity Threshold  (N={N}, Storkey, async-cyclic, '
        f'noise={int(NOISE_FRAC*100)}%,  capacity ≈ 0.138N = {CAPACITY:.1f})',
        fontweight='bold', fontsize=12, y=0.99)

    # 4 data cols + 1 thumbnail col per row
    n_rows = len(M_VALUES)
    outer  = gridspec.GridSpec(n_rows, 1, figure=fig,
                               hspace=0.55, top=0.94, bottom=0.04,
                               left=0.04, right=0.97)

    col_titles = ['Target\n(pattern 0)', f'Corrupted\n({int(NOISE_FRAC*N)} bits flipped)',
                  'Recalled', 'All stored patterns']
    col_w = [1, 1, 1, 0.12, 2.0]   # widths; index 3 is spacer

    for row_idx, M in enumerate(M_VALUES):
        t   = trials[M]
        pats = t['pats']

        inner = gridspec.GridSpecFromSubplotSpec(
            1, 5, subplot_spec=outer[row_idx],
            width_ratios=col_w, wspace=0.25)

        # --- col 0: target ---
        ax0 = fig.add_subplot(inner[0, 0])
        ax0.imshow(img(t['target']), cmap=CMAP_PAT, vmin=0, vmax=1,
                   interpolation='nearest')
        ax0.axis('off')
        e_t = t['net'].energy(t['target'])

        # --- col 1: corrupted ---
        ax1 = fig.add_subplot(inner[0, 1])
        ax1.imshow(img(t['corrupt']), cmap=CMAP_PAT, vmin=0, vmax=1,
                   interpolation='nearest')
        ax1.axis('off')
        e_c = t['net'].energy(t['corrupt'])

        # --- col 2: recalled ---
        ax2 = fig.add_subplot(inner[0, 2])
        ax2.imshow(img(t['recalled']), cmap=CMAP_PAT, vmin=0, vmax=1,
                   interpolation='nearest')
        ax2.axis('off')
        badge(t['hamming'], ax2)
        e_r = t['net'].energy(t['recalled'])

        # --- col 3: spacer, col 4: thumbnail grid of all patterns ---
        n_cols_thumb = min(M, 10)
        n_rows_thumb = (M + n_cols_thumb - 1) // n_cols_thumb
        ax_th = fig.add_subplot(inner[0, 4])
        ax_th.axis('off')

        # tile all patterns into a single image
        tile_h = n_rows_thumb * SIZE + (n_rows_thumb - 1)
        tile_w = n_cols_thumb * SIZE + (n_cols_thumb - 1)
        tile   = np.ones((tile_h, tile_w)) * 0.5   # grey separator
        for k, p in enumerate(pats):
            r_k = k // n_cols_thumb
            c_k = k % n_cols_thumb
            ry  = r_k * (SIZE + 1)
            cx  = c_k * (SIZE + 1)
            tile[ry:ry+SIZE, cx:cx+SIZE] = img(p)

        ax_th.imshow(tile, cmap=CMAP_PAT, vmin=0, vmax=1,
                     interpolation='nearest', aspect='auto')
        ax_th.set_title(f'All {M} stored patterns', fontsize=8, pad=3)

        # row-level annotation
        load = M / N
        if t['hamming'] == 0:
            recall_str = f'✓ perfect recall  ({t["n_sweeps"]} sweeps, {t["n_sweeps"]*N} cycles)'
            col_border = '#27ae60'
        else:
            recall_str = f'✗ spurious state  Δ={t["hamming"]} bits  ({t["n_sweeps"]} sweeps)'
            col_border = '#e74c3c'

        row_title = (f'{load_label(M)}   |   '
                     f'E: {e_c:.2f} → {e_r:.2f}  (target: {e_t:.2f})   |   '
                     f'{recall_str}')

        for ax, ct in zip([ax0, ax1, ax2], col_titles[:3]):
            ax.set_title(ct, fontsize=8.5, pad=3)

        # coloured spine to mark success/failure at a glance
        for ax in [ax0, ax1, ax2]:
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_color(col_border)
                sp.set_linewidth(2)

        fig.text(0.50, ax0.get_position().y1 + 0.005,
                 row_title,
                 ha='center', va='bottom', fontsize=8.5,
                 color='#222222',
                 transform=fig.transFigure)

    # legend
    handles = [
        mpatches.Patch(edgecolor='#27ae60', facecolor='none', lw=2,
                       label='Perfect recall'),
        mpatches.Patch(edgecolor='#e74c3c', facecolor='none', lw=2,
                       label='Spurious / failed recall'),
        plt.Line2D([0],[0], ls='--', color='#555', lw=1.2,
                   label=f'Capacity ≈ 0.138N = {CAPACITY:.1f}'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3,
               fontsize=9, frameon=True, framealpha=0.92,
               edgecolor='#cccccc', bbox_to_anchor=(0.5, 0.0))

    return fig


# ── animated M-sweep ──────────────────────────────────────────────────────────
def make_sweep_animation():
    """Animate recall quality as M increases from 1 to 18."""
    M_sweep = list(range(1, 19))
    trials  = {M: run_trial(M, SEED) for M in M_sweep}

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), facecolor='white')
    fig.patch.set_facecolor('white')
    titles = ['Target (pattern 0)',
              f'Corrupted  ({int(NOISE_FRAC*N)} bits, {int(NOISE_FRAC*100)}%)',
              'Recalled']

    imgs = []
    for ax, title in zip(axes, titles):
        ax.axis('off')
        ax.set_title(title, fontsize=10, pad=4)
        im = ax.imshow(np.zeros((SIZE, SIZE)), cmap=CMAP_PAT, vmin=0, vmax=1,
                       interpolation='nearest', animated=True)
        imgs.append(im)
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(2.5)

    # capacity line indicator
    cap_txt = fig.text(0.5, 0.93, '', ha='center', fontsize=11,
                       fontweight='bold')
    status_txt = fig.text(0.5, 0.02, '', ha='center', fontsize=9,
                          color='#333')

    def update(M):
        t = trials[M]
        imgs[0].set_data(img(t['target']))
        imgs[1].set_data(img(t['corrupt']))
        imgs[2].set_data(img(t['recalled']))

        load = M / N
        if t['hamming'] == 0:
            col      = '#27ae60'
            recall_s = '✓ Perfect recall'
        else:
            col      = '#e74c3c'
            recall_s = f'✗ Spurious state  (Δ = {t["hamming"]} bits)'

        for ax in axes:
            for sp in ax.spines.values():
                sp.set_color(col)

        regime = ('below threshold' if M < CAPACITY * 0.85
                  else 'near threshold' if M <= CAPACITY * 1.15
                  else 'ABOVE threshold')
        cap_txt.set_text(
            f'M = {M} patterns  (load = {load:.3f},  {regime},  '
            f'capacity ≈ {CAPACITY:.1f})')
        cap_txt.set_color(col)

        e_c = t['net'].energy(t['corrupt'])
        e_r = t['net'].energy(t['recalled'])
        status_txt.set_text(
            f'Energy: {e_c:.2f} → {e_r:.2f}   |   '
            f'{t["n_sweeps"]} sweeps = {t["n_sweeps"]*N} clock cycles   |   '
            f'{recall_s}')
        status_txt.set_color(col)

        return imgs + [cap_txt, status_txt]

    anim = FuncAnimation(fig, update, frames=M_sweep,
                         interval=900, blit=False, repeat=True,
                         repeat_delay=2000)
    return fig, anim


# ── main ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--animate', action='store_true',
                    help='also produce animated M-sweep GIF')
args, _ = parser.parse_known_args()

print(f"N={N}  capacity≈{CAPACITY:.1f}  noise={int(NOISE_FRAC*100)}%  seed={SEED}")

# static comparison
print("Building comparison figure…")
fig_cmp = make_comparison_figure()
out_cmp = Path(__file__).parent / 'demo_capacity.png'
fig_cmp.savefig(str(out_cmp), bbox_inches='tight', dpi=140, facecolor='white')
print(f"  Saved → {out_cmp.name}")

if args.animate:
    print("Building animated M-sweep…")
    fig_sw, anim_sw = make_sweep_animation()
    out_sw = Path(__file__).parent / 'demo_capacity_sweep.gif'
    anim_sw.save(str(out_sw), writer=PillowWriter(fps=1), dpi=110)
    print(f"  Saved → {out_sw.name}")

plt.show()
