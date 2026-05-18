"""
Capacity threshold comparison demo  (N=64, 8×8 character patterns)

Black background. ON neuron = white, OFF neuron = black.
Patterns are recognisable characters so a spurious recalled state
is visibly scrambled vs the clean digit.

Three rows — each row trains a fresh Storkey network and attempts
to recall pattern '0' from a 20%-corrupted version:
  Row 1 — M =  4  (load 0.06,  well below 0.138N ≈ 8.8)  → perfect recall
  Row 2 — M =  9  (load 0.14,  near threshold)             → borderline
  Row 3 — M = 14  (load 0.22,  above threshold)            → spurious / scrambled

Run:
    python demo_capacity.py            # static comparison PNG
    python demo_capacity.py --animate  # + animated M-sweep GIF
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
from datasets import add_noise

# ── 14 hand-crafted 8×8 patterns (digits 0-9 + letters A E H L) ───────────────
_RAW = {
    '0': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          0,1,1,0,0,1,1,0,
          0,0,1,1,1,1,0,0],
    '1': [0,0,0,1,1,0,0,0,
          0,0,1,1,1,0,0,0,
          0,1,0,1,1,0,0,0,
          0,0,0,1,1,0,0,0,
          0,0,0,1,1,0,0,0,
          0,0,0,1,1,0,0,0,
          0,0,0,1,1,0,0,0,
          0,1,1,1,1,1,1,0],
    '2': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          0,0,0,0,0,1,1,0,
          0,0,0,0,1,1,0,0,
          0,0,0,1,1,0,0,0,
          0,0,1,1,0,0,0,0,
          0,1,1,0,0,0,0,0,
          1,1,1,1,1,1,1,1],
    '3': [0,1,1,1,1,1,1,0,
          0,0,0,0,0,1,1,0,
          0,0,0,0,1,1,0,0,
          0,0,1,1,1,1,0,0,
          0,0,0,0,1,1,0,0,
          0,0,0,0,0,1,1,0,
          0,1,0,0,0,1,1,0,
          0,1,1,1,1,1,0,0],
    '4': [0,0,0,0,1,1,0,0,
          0,0,0,1,1,1,0,0,
          0,0,1,1,0,1,1,0,
          0,1,1,0,0,1,1,0,
          1,1,0,0,0,1,1,0,
          1,1,1,1,1,1,1,1,
          0,0,0,0,0,1,1,0,
          0,0,0,0,0,1,1,0],
    '5': [1,1,1,1,1,1,1,1,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,1,1,1,1,0,0,
          0,0,0,0,0,1,1,0,
          0,0,0,0,0,1,1,0,
          1,1,0,0,0,1,1,0,
          0,1,1,1,1,1,0,0],
    '6': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,1,1,1,1,0,0,
          1,1,0,0,0,1,1,0,
          1,1,0,0,0,1,1,0,
          0,1,1,0,0,1,1,0,
          0,0,1,1,1,1,0,0],
    '7': [1,1,1,1,1,1,1,1,
          0,0,0,0,0,0,1,1,
          0,0,0,0,0,1,1,0,
          0,0,0,0,1,1,0,0,
          0,0,0,1,1,0,0,0,
          0,0,1,1,0,0,0,0,
          0,1,1,0,0,0,0,0,
          1,1,0,0,0,0,0,0],
    '8': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          0,1,1,0,0,1,1,0,
          0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          1,1,0,0,0,0,1,1,
          0,1,1,0,0,1,1,0,
          0,0,1,1,1,1,0,0],
    '9': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          1,1,0,0,0,0,1,1,
          0,1,1,0,0,1,1,1,
          0,0,1,1,1,1,1,0,
          0,0,0,0,0,1,1,0,
          0,0,0,0,1,1,0,0,
          0,0,1,1,1,0,0,0],
    'A': [0,0,1,1,1,1,0,0,
          0,1,1,0,0,1,1,0,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,1,1,1,1,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1],
    'E': [1,1,1,1,1,1,1,1,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,1,1,1,1,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,1,1,1,1,1,1],
    'H': [1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,1,1,1,1,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1],
    'L': [1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,0,0,0,0,0,0,
          1,1,1,1,1,1,1,1],
}

ALL_KEYS   = ['0','1','2','3','4','5','6','7','8','9','A','E','H','L']
M_VALUES   = [4, 9, 14]

SIZE       = 8
N          = SIZE * SIZE          # 64
NOISE_FRAC = 0.20
SEED       = 42
MAX_SWEEPS = 40
CAPACITY   = 0.138 * N            # ≈ 8.8

BG         = '#0d0d0d'            # near-black figure background
AX_BG      = '#111111'            # axes background
ON_COL     = '#ffffff'            # +1 neuron
OFF_COL    = '#111111'            # −1 neuron


def bipolar(bits):
    return np.array([1. if b else -1. for b in bits])


def img(s):
    """Bipolar state → 0/1 pixel grid (1 = white ON, 0 = black OFF)."""
    return ((s + 1) / 2).reshape(SIZE, SIZE)


def run_trial(key_list, seed):
    pats    = np.array([bipolar(_RAW[k]) for k in key_list])
    net     = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
    net.train(pats)
    rng     = np.random.default_rng(seed + 1)
    target  = pats[0]
    corrupt = add_noise(target, n_flips=int(NOISE_FRAC * N), rng=rng)
    recalled, n_sweeps, _ = net.run(corrupt, max_sweeps=MAX_SWEEPS, rng=rng)
    hamming  = int((recalled != target).sum())
    return dict(keys=key_list, pats=pats, net=net, target=target,
                corrupt=corrupt, recalled=recalled,
                n_sweeps=n_sweeps, hamming=hamming)


def make_thumb_tile(pats, ncols=5):
    """Tile all patterns into one image with 1-pixel separators."""
    M       = len(pats)
    nrows   = (M + ncols - 1) // ncols
    h       = nrows * SIZE + max(nrows - 1, 0)
    w       = ncols * SIZE + max(ncols - 1, 0)
    tile    = np.zeros((h, w))          # black separators
    for k, p in enumerate(pats):
        r = k // ncols
        c = k % ncols
        tile[r*(SIZE+1):r*(SIZE+1)+SIZE, c*(SIZE+1):c*(SIZE+1)+SIZE] = img(p)
    return tile


def style_ax(ax, border_color, lw=2.5):
    ax.set_facecolor(AX_BG)
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color(border_color)
        sp.set_linewidth(lw)
    ax.tick_params(left=False, bottom=False,
                   labelleft=False, labelbottom=False)


# ── static comparison figure ──────────────────────────────────────────────────
def make_comparison_figure():
    trials = {M: run_trial(ALL_KEYS[:M], SEED) for M in M_VALUES}

    fig = plt.figure(figsize=(15, len(M_VALUES) * 3.8 + 1.4), facecolor=BG)
    fig.suptitle(
        f'Hopfield Capacity Threshold  '
        f'(N={N}, Storkey, async-cyclic, noise={int(NOISE_FRAC*100)}%,  '
        f'capacity ≈ 0.138N = {CAPACITY:.1f})',
        fontweight='bold', fontsize=12, y=0.995, color='white')

    outer = gridspec.GridSpec(len(M_VALUES), 1, figure=fig,
                              hspace=0.72, top=0.955, bottom=0.04,
                              left=0.03, right=0.98)

    for row_idx, M in enumerate(M_VALUES):
        t    = trials[M]
        load = M / N

        if t['hamming'] == 0:
            border = '#27ae60'
            recall_str = f'✓  Perfect recall'
        else:
            border = '#e74c3c'
            recall_str = f'✗  Spurious state   Δ = {t["hamming"]} bits off'

        regime = ('well below threshold' if M < CAPACITY * 0.85
                  else 'near threshold' if M <= CAPACITY * 1.15
                  else 'ABOVE threshold')

        # inner grid: target | corrupted | recalled | spacer | thumbnails
        inner = gridspec.GridSpecFromSubplotSpec(
            1, 5, subplot_spec=outer[row_idx],
            width_ratios=[1, 1, 1, 0.08, 1.8], wspace=0.18)

        def make_ax(col):
            ax = fig.add_subplot(inner[0, col])
            style_ax(ax, border)
            return ax

        ax_t  = make_ax(0)
        ax_c  = make_ax(1)
        ax_r  = make_ax(2)
        ax_th = fig.add_subplot(inner[0, 4])
        style_ax(ax_th, '#444444', lw=1)

        imshow_kw = dict(cmap='gray', vmin=0, vmax=1,
                         interpolation='nearest')

        ax_t.imshow(img(t['target']),  **imshow_kw)
        ax_c.imshow(img(t['corrupt']), **imshow_kw)
        ax_r.imshow(img(t['recalled']), **imshow_kw)

        # big red X overlay when spurious
        if t['hamming'] > 0:
            for ax in (ax_r,):
                ax.plot([0, SIZE-1], [0, SIZE-1], color='#e74c3c',
                        lw=2.5, alpha=0.7, transform=ax.transData)
                ax.plot([0, SIZE-1], [SIZE-1, 0], color='#e74c3c',
                        lw=2.5, alpha=0.7, transform=ax.transData)

        # thumbnails of all stored patterns
        tile = make_thumb_tile(t['pats'], ncols=5)
        ax_th.imshow(tile, **imshow_kw, aspect='auto')
        ax_th.set_title(f'All {M} stored patterns',
                        fontsize=7.5, color='#aaaaaa', pad=3)

        # column titles
        e_c = t['net'].energy(t['corrupt'])
        e_r = t['net'].energy(t['recalled'])
        e_t = t['net'].energy(t['target'])

        ax_t.set_title(f"Target  '0'\nE = {e_t:.2f}",
                       fontsize=9, color='#cccccc', pad=3)
        ax_c.set_title(f"Corrupted  ({int(NOISE_FRAC*N)} bits)\nE = {e_c:.2f}",
                       fontsize=9, color='#cccccc', pad=3)
        ax_r.set_title(f"Recalled\nE = {e_r:.2f}",
                       fontsize=9, color=border, pad=3)

        # row label (left of row)
        row_label = (f'M = {M}   load = {load:.2f}   {regime}   |   '
                     f'{t["n_sweeps"]} sweeps = {t["n_sweeps"]*N} cycles   |   '
                     f'{recall_str}')
        y_pos = ax_t.get_position().y1 + 0.008
        fig.text(0.50, y_pos, row_label,
                 ha='center', va='bottom', fontsize=9,
                 color=border, fontweight='bold',
                 transform=fig.transFigure)

    # legend
    handles = [
        mpatches.Patch(edgecolor='#27ae60', facecolor='none', lw=2,
                       label='Perfect recall (≤ capacity)'),
        mpatches.Patch(edgecolor='#e74c3c', facecolor='none', lw=2,
                       label='Spurious state (> capacity)'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=2,
               fontsize=9, frameon=True,
               facecolor='#1a1a1a', edgecolor='#555555',
               labelcolor='white',
               bbox_to_anchor=(0.5, 0.00))

    return fig


# ── animated M-sweep ──────────────────────────────────────────────────────────
def make_sweep_animation():
    M_sweep = list(range(1, len(ALL_KEYS) + 1))
    trials  = {M: run_trial(ALL_KEYS[:M], SEED) for M in M_sweep}

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.5), facecolor=BG)
    fig.patch.set_facecolor(BG)
    col_titles = ["Target  '0'",
                  f"Corrupted  ({int(NOISE_FRAC*N)} bits)",
                  'Recalled']
    imshow_kw  = dict(cmap='gray', vmin=0, vmax=1, interpolation='nearest',
                      animated=True)

    imgs = []
    for ax, title in zip(axes, col_titles):
        ax.set_facecolor(AX_BG)
        ax.axis('off')
        ax.set_title(title, fontsize=10, color='#cccccc', pad=4)
        im = ax.imshow(np.zeros((SIZE, SIZE)), **imshow_kw)
        imgs.append(im)
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(2.5)

    cap_txt    = fig.text(0.5, 0.94, '', ha='center', fontsize=11,
                          fontweight='bold', color='white')
    status_txt = fig.text(0.5, 0.03, '', ha='center', fontsize=9,
                          color='#aaaaaa')
    # capacity marker line (static annotation on cap_txt area)
    fig.text(0.5, 0.88,
             f'Theoretical capacity  ≈  0.138 × N  =  {CAPACITY:.1f} patterns',
             ha='center', fontsize=8.5, color='#888888', style='italic')

    def update(M):
        t      = trials[M]
        load   = M / N
        border = '#27ae60' if t['hamming'] == 0 else '#e74c3c'
        recall = ('✓  Perfect recall'
                  if t['hamming'] == 0
                  else f'✗  Spurious  (Δ = {t["hamming"]} bits)')

        imgs[0].set_data(img(t['target']))
        imgs[1].set_data(img(t['corrupt']))
        imgs[2].set_data(img(t['recalled']))

        for ax in axes:
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_color(border)

        regime = ('below threshold' if M < CAPACITY * 0.85
                  else 'near threshold' if M <= CAPACITY * 1.15
                  else 'ABOVE threshold')
        cap_txt.set_text(f'M = {M} patterns stored   '
                         f'(load = {load:.3f},  {regime})')
        cap_txt.set_color(border)

        e_c = t['net'].energy(t['corrupt'])
        e_r = t['net'].energy(t['recalled'])
        status_txt.set_text(
            f'E: {e_c:.2f} → {e_r:.2f}   |   '
            f'{t["n_sweeps"]} sweeps = {t["n_sweeps"]*N} cycles   |   '
            f'{recall}')
        status_txt.set_color(border)

        return imgs + [cap_txt, status_txt]

    anim = FuncAnimation(fig, update, frames=M_sweep,
                         interval=950, blit=False,
                         repeat=True, repeat_delay=2500)
    return fig, anim


# ── main ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--animate', action='store_true')
args, _ = parser.parse_known_args()

print(f"N={N}  capacity≈{CAPACITY:.1f}  noise={int(NOISE_FRAC*100)}%  "
      f"patterns: {ALL_KEYS}")

print("Building comparison figure…")
fig_cmp = make_comparison_figure()
out_cmp = Path(__file__).parent / 'demo_capacity.png'
fig_cmp.savefig(str(out_cmp), bbox_inches='tight', dpi=150,
                facecolor=BG)
print(f"  Saved → {out_cmp.name}")

if args.animate:
    print("Building animated M-sweep…")
    fig_sw, anim_sw = make_sweep_animation()
    out_sw = Path(__file__).parent / 'demo_capacity_sweep.gif'
    anim_sw.save(str(out_sw), writer=PillowWriter(fps=1), dpi=115)
    print(f"  Saved → {out_sw.name}")

plt.show()
