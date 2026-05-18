"""
Recall grid demo — purple/gold aesthetic, sklearn built-in digits (N=64)

Loads the sklearn 8×8 handwritten digit dataset (no internet needed).
Picks the best representative image per class, binarises, trains a
Storkey Hopfield network, corrupts each stored pattern, and shows:

    [corrupted] → [recalled]   + energy-vs-step curve

in a 4-row × 2-column grid (8 examples).

Run:
    python demo_recall_grid.py
Saves: demo_recall_grid.png
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
from sklearn.datasets import load_digits

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))
from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import add_noise

# ── config ────────────────────────────────────────────────────────────────────
N_CLASSES  = 8          # patterns to store (below 0.138×64 ≈ 8.8 capacity)
NOISE_FRAC = 0.25       # fraction of bits to corrupt
SEED       = 42
MAX_SWEEPS = 40
SIZE       = 8

PURPLE     = '#2d0047'  # background
GOLD       = '#FFD700'  # ON neuron
AX_BG      = '#3a005e'  # axes background
ARROW_COL  = '#4da6ff'  # blue arrow
ENERGY_COL = '#ff4444'  # energy curve

CMAP = ListedColormap([PURPLE, GOLD])   # 0 → purple, 1 → gold

# ── load & binarise sklearn built-in 8×8 digits ───────────────────────────────
raw   = load_digits()
X     = raw.images       # (1797, 8, 8)  values 0–16
y     = raw.target

X_bin  = np.where(X >= 8, 1.0, -1.0).reshape(len(X), -1)   # (1797, 64)

# for each class pick the image closest to its class centroid
classes  = list(range(N_CLASSES))
patterns = []
labels   = []
for cls in classes:
    mask  = y == cls
    imgs  = X_bin[mask]
    mean  = imgs.mean(axis=0)
    best  = np.argmin(((imgs - mean) ** 2).sum(axis=1))
    patterns.append(imgs[best])
    labels.append(str(cls))

patterns = np.array(patterns)          # (N_CLASSES, 64)

# ── train ─────────────────────────────────────────────────────────────────────
net = HopfieldNetwork(N=SIZE*SIZE, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)

# ── recall each pattern, record per-step energy ───────────────────────────────
rng = np.random.default_rng(SEED)

results = []
for idx, (pat, lbl) in enumerate(zip(patterns, labels)):
    corrupt = add_noise(pat, n_flips=int(NOISE_FRAC * SIZE * SIZE), rng=rng)

    energies = [net.energy(corrupt)]
    s = corrupt.copy()
    for sweep in range(MAX_SWEEPS):
        s_prev = s.copy()
        for i in range(SIZE * SIZE):
            h = float(net.W[i] @ s)
            if h > 0:   s[i] =  1.0
            elif h < 0: s[i] = -1.0
            energies.append(net.energy(s))
        if np.array_equal(s, s_prev):
            break

    hamming = int((s != pat).sum())
    results.append(dict(label=lbl, corrupt=corrupt, recalled=s,
                        target=pat, energies=energies, hamming=hamming))

# ── figure ────────────────────────────────────────────────────────────────────
N_EX   = len(results)
N_COLS = 2
N_ROWS = (N_EX + N_COLS - 1) // N_COLS

fig = plt.figure(figsize=(13, N_ROWS * 3.0 + 1.0), facecolor=PURPLE)
fig.patch.set_facecolor(PURPLE)

fig.suptitle(
    f'Hopfield Recall  (N=64, M={N_CLASSES}, Storkey, '
    f'noise={int(NOISE_FRAC*100)}%,  capacity≈8.8)',
    color=GOLD, fontsize=12, fontweight='bold', y=0.98)

# outer grid: N_ROWS rows × 2 columns
outer = gridspec.GridSpec(N_ROWS, N_COLS, figure=fig,
                          hspace=0.55, wspace=0.30,
                          top=0.93, bottom=0.04,
                          left=0.04, right=0.97)

imshow_kw = dict(cmap=CMAP, vmin=0, vmax=1, interpolation='nearest')

def img(s):
    return ((s + 1) / 2).reshape(SIZE, SIZE)

for ex_idx, res in enumerate(results):
    row = ex_idx // N_COLS
    col = ex_idx % N_COLS

    # each cell: 3 columns — [corrupted] [recalled] [energy]
    inner = gridspec.GridSpecFromSubplotSpec(
        1, 3, subplot_spec=outer[row, col],
        width_ratios=[1, 1, 1.5], wspace=0.10)

    ax_c  = fig.add_subplot(inner[0, 0])   # corrupted
    ax_r  = fig.add_subplot(inner[0, 1])   # recalled
    ax_e  = fig.add_subplot(inner[0, 2])   # energy

    for ax in (ax_c, ax_r):
        ax.imshow(img(res['corrupt'] if ax is ax_c else res['recalled']),
                  **imshow_kw)
        ax.set_facecolor(AX_BG)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color('#555555'); sp.set_linewidth(0.8)

    ax_c.imshow(img(res['corrupt']),  **imshow_kw)
    ax_r.imshow(img(res['recalled']), **imshow_kw)

    success = res['hamming'] == 0
    border  = GOLD if success else '#e74c3c'

    ax_c.set_title('corrupted image', fontsize=7, color='#cccccc', pad=2)
    ax_r.set_title('reconstructed image', fontsize=7, color=border, pad=2)

    # red-border recalled panel if spurious
    for sp in ax_r.spines.values():
        sp.set_color(border); sp.set_linewidth(2)

    # blue arrow between corrupted and recalled (as text on ax_c)
    ax_c.annotate('', xy=(1.18, 0.5), xytext=(1.0, 0.5),
                  xycoords='axes fraction', textcoords='axes fraction',
                  arrowprops=dict(arrowstyle='->', color=ARROW_COL,
                                  lw=2.0))

    # energy plot
    ax_e.set_facecolor(PURPLE)
    ax_e.plot(res['energies'], color=ENERGY_COL, lw=1.2)
    ax_e.set_title('energy', fontsize=7, color='#cccccc', pad=2)
    ax_e.tick_params(colors='#888888', labelsize=6)
    ax_e.set_xlabel('step', fontsize=6, color='#888888')
    for sp in ax_e.spines.values():
        sp.set_color('#444444'); sp.set_linewidth(0.6)
    ax_e.yaxis.tick_right()
    ax_e.yaxis.set_label_position('right')

    # result badge below recalled panel
    badge = '✓' if success else f'✗ Δ={res["hamming"]}'
    fig.text(
        ax_r.get_position().x0 + ax_r.get_position().width / 2,
        ax_r.get_position().y0 - 0.015,
        badge, ha='center', va='top',
        fontsize=8, color=border, fontweight='bold',
        transform=fig.transFigure)

# ── footer ────────────────────────────────────────────────────────────────────
n_perfect = sum(1 for r in results if r['hamming'] == 0)
footer = (f'{n_perfect}/{N_EX} patterns recalled perfectly.  '
          f'All have been reconstructed into the original images.'
          if n_perfect == N_EX else
          f'{n_perfect}/{N_EX} patterns recalled perfectly  '
          f'({N_EX - n_perfect} spurious — above capacity).')
fig.text(0.5, 0.01, footer, ha='center', fontsize=9,
         color=GOLD, fontweight='bold', transform=fig.transFigure)

out = Path(__file__).parent / 'demo_recall_grid.png'
fig.savefig(str(out), bbox_inches='tight', dpi=150, facecolor=PURPLE)
print(f"Saved → {out.name}")
plt.show()
