"""
Animated 2-cycle demo — sync vs async-cyclic side by side.

Searches for an initial state that produces a sync 2-cycle, then
animates both update modes from the same starting point:
  Top row    — SYNC:  oscillates A↔B forever (red)
  Bottom row — ASYNC: converges to a fixed point (green)

Run:
    python demo_2cycle_anim.py
Saves: demo_2cycle_anim.gif
"""

import sys, argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))
from hopfield_net import HopfieldNetwork, STORKEY, SYNC, ASYNC_CYCLIC

# ── patterns (4×4, N=16, M=4 → above capacity 0.138×16≈2.2) ──────────────────
_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
    'X': [1,0,0,1, 0,1,1,0, 0,1,1,0, 1,0,0,1],
}
DIGITS   = ['0', '1', '7', 'X']
SIZE, N  = 4, 16

def bipolar(bits): return np.array([1. if b else -1. for b in bits])
patterns = np.array([bipolar(_RAW[d]) for d in DIGITS])

net_s = HopfieldNetwork(N=N, rule=STORKEY, update_mode=SYNC)
net_a = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net_s.train(patterns); net_a.train(patterns)

def sync_step(W, s):
    s_new = np.sign(W @ s)
    s_new[s_new == 0] = s[s_new == 0]
    return s_new

def is_2cycle(hist):
    return (len(hist) >= 3 and
            np.array_equal(hist[-1], hist[-3]) and
            not np.array_equal(hist[-1], hist[-2]))

# find 2-cycle start
rng, found = np.random.default_rng(0), False
for _ in range(10000):
    s0 = rng.choice([-1., 1.], size=N)
    hist = [s0.copy()]
    for _ in range(60):
        hist.append(sync_step(net_s.W, hist[-1]))
        if is_2cycle(hist): found = True; break
    if found: break

assert found, "No 2-cycle found — increase attempts"

# ── build histories (fixed N_DISPLAY sweeps each) ─────────────────────────────
N_DISPLAY   = 10   # sweeps to show for each mode
HOLD_FREEZE = 6    # extra frames to hold at the end

# sync: record one state per sweep
sync_hist = [s0.copy()]
sync_outcome = 'running'
for _ in range(N_DISPLAY):
    sync_hist.append(sync_step(net_s.W, sync_hist[-1]))
    if is_2cycle(sync_hist): sync_outcome = '2-cycle'; break
    if np.array_equal(sync_hist[-1], sync_hist[-2]): sync_outcome = 'converged'; break
while len(sync_hist) <= N_DISPLAY + 1:
    sync_hist.append(sync_step(net_s.W, sync_hist[-1]))

# async: record one state per sweep
async_hist = [s0.copy()]
async_outcome = 'running'
s = s0.copy()
for sweep in range(N_DISPLAY):
    s_prev = s.copy()
    for i in range(N):
        h = float(net_a.W[i] @ s)
        if h > 0: s[i] = 1.
        elif h < 0: s[i] = -1.
    async_hist.append(s.copy())
    if np.array_equal(s, s_prev): async_outcome = f'converged (sweep {sweep+1})'; break

# pad both to same length, hold on last state
n_frames = max(len(sync_hist), len(async_hist)) + HOLD_FREEZE
while len(sync_hist)  < n_frames: sync_hist.append(sync_hist[-1])
while len(async_hist) < n_frames: async_hist.append(async_hist[-1])

# ── figure ────────────────────────────────────────────────────────────────────
BG, AX_BG = '#0d0d0d', '#111111'
RED, GREEN, ORANGE = '#e74c3c', '#27ae60', '#f39c12'
CMAP = ListedColormap([AX_BG, '#ffffff'])

def img(s): return ((s+1)/2).reshape(SIZE, SIZE)

fig = plt.figure(figsize=(14, 6.5), facecolor=BG)
fig.patch.set_facecolor(BG)
fig.suptitle(
    f'Sync vs Async-Cyclic — 2-Cycle Demo  '
    f'(N={N}, M={len(DIGITS)}, Storkey, load={len(DIGITS)/N:.2f} > 0.138)',
    color='white', fontsize=12, fontweight='bold', y=0.97)

outer = gridspec.GridSpec(2, 1, figure=fig, hspace=0.52,
                          top=0.91, bottom=0.08, left=0.04, right=0.97)

def make_row(row_idx, label, color, n_panels=N_DISPLAY+1):
    n_show = min(n_panels, 8)
    inner  = gridspec.GridSpecFromSubplotSpec(
        1, n_show + 1, subplot_spec=outer[row_idx],
        width_ratios=[1]*n_show + [2.0], wspace=0.12)

    axes  = [fig.add_subplot(inner[0, k]) for k in range(n_show)]
    ax_e  = fig.add_subplot(inner[0, n_show])

    for ax in axes:
        ax.set_facecolor(AX_BG)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color('#333333'); sp.set_linewidth(0.8)

    ax_e.set_facecolor(BG)
    for sp in ax_e.spines.values(): sp.set_color('#333333')

    # row label on the left
    pos = outer[row_idx].get_position(fig)
    fig.text(0.01, (pos.y0+pos.y1)/2, label, va='center', ha='left',
             fontsize=9, color=color, fontweight='bold',
             rotation=90, transform=fig.transFigure)
    return axes, ax_e

sync_axes,  sync_e_ax  = make_row(0, 'SYNC',         RED)
async_axes, async_e_ax = make_row(1, 'ASYNC-CYCLIC',  GREEN)

# static images for sweep index panels
def init_axes(axes, hist, color):
    imgs = []
    for k, ax in enumerate(axes):
        t = k if k < len(hist) else -1
        im = ax.imshow(img(hist[t]), cmap=CMAP, vmin=0, vmax=1,
                       interpolation='nearest', animated=True)
        ax.set_title(f't={k}', fontsize=7, color='#888888', pad=2)
        imgs.append(im)
    return imgs

sync_imgs  = init_axes(sync_axes,  sync_hist,  RED)
async_imgs = init_axes(async_axes, async_hist, GREEN)

# energy plots — animated lines
sync_e_line,  = sync_e_ax.plot([], [], 'o-', color=RED,   lw=1.5, ms=4)
async_e_line, = async_e_ax.plot([], [], 'o-', color=GREEN, lw=1.5, ms=4)

for ax, col, title in [(sync_e_ax, RED, 'Energy (sync)'),
                        (async_e_ax, GREEN, 'Energy (async)')]:
    ax.set_title(title, fontsize=8, color=col, pad=3)
    ax.tick_params(colors='#666666', labelsize=6)
    ax.set_xlabel('sweep', fontsize=6, color='#666666')

all_e = [net_s.energy(st) for st in sync_hist + async_hist]
e_min, e_max = min(all_e) - 0.5, max(all_e) + 0.5
for ax in (sync_e_ax, async_e_ax):
    ax.set_xlim(-0.5, n_frames - 0.5)
    ax.set_ylim(e_min, e_max)

status_txt = fig.text(0.5, 0.02, '', ha='center', fontsize=9,
                      color='#aaaaaa', transform=fig.transFigure)

# ── animation update ───────────────────────────────────────────────────────────
sync_energies  = [net_s.energy(st) for st in sync_hist]
async_energies = [net_s.energy(st) for st in async_hist]

def update(frame):
    # highlight most recent sweep in each row
    for k, (sim, aim) in enumerate(zip(sync_imgs, async_imgs)):
        t = min(frame, len(sync_hist)-1)
        sim.set_data(img(sync_hist[min(k, t)]))
        aim.set_data(img(async_hist[min(k, t)]))

        is_recent_s = (k == min(frame, len(sync_axes)-1))
        is_recent_a = (k == min(frame, len(async_axes)-1))

        for sp in sync_axes[k].spines.values():
            sp.set_color(RED if is_recent_s else '#333333')
            sp.set_linewidth(2 if is_recent_s else 0.8)
        for sp in async_axes[k].spines.values():
            sp.set_color(GREEN if is_recent_a else '#333333')
            sp.set_linewidth(2 if is_recent_a else 0.8)

    t = min(frame + 1, n_frames)
    sync_e_line.set_data(range(t),  sync_energies[:t])
    async_e_line.set_data(range(t), async_energies[:t])

    # detect outcomes for status bar
    is_2c = (frame >= 3 and
              np.array_equal(sync_hist[frame], sync_hist[frame-2]) and
              not np.array_equal(sync_hist[frame], sync_hist[frame-1]))
    sync_tag  = '⟳ 2-CYCLE' if '2-cycle' in sync_outcome else '✓ converged'
    async_tag = ('✓ ' + async_outcome) if 'converged' in async_outcome else 'running…'

    status_txt.set_text(
        f'Sweep {frame}   |   '
        f'Sync: {sync_tag}   |   Async-cyclic: {async_tag}   |   '
        f'Detection: s[t] == s[t−2]  AND  s[t] ≠ s[t−1]')

    return sync_imgs + async_imgs + [sync_e_line, async_e_line, status_txt]

anim = FuncAnimation(fig, update, frames=n_frames,
                     interval=600, blit=False, repeat=True, repeat_delay=1500)

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--nosave', action='store_true')
args, _ = parser.parse_known_args()

if not args.nosave:
    out = Path(__file__).parent / 'demo_2cycle_anim.gif'
    print(f"Saving {n_frames} frames → {out.name} …")
    anim.save(str(out), writer=PillowWriter(fps=2), dpi=110)
    print("  Done.")

plt.show()
