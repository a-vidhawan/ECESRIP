"""
Sync update 2-cycle demo.

Demonstrates that synchronous update can produce a 2-cycle — two states
that each map to the other — so the network oscillates forever instead
of converging. Compares sync vs async-cyclic on the same network and
initial state.

Detection method: compare state[t] == state[t-2] AND state[t] != state[t-1].

Run:
    python demo_sync_2cycle.py
Saves: demo_sync_2cycle.png
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))
from hopfield_net import HopfieldNetwork, STORKEY, SYNC, ASYNC_CYCLIC
from datasets import add_noise

# ── deliberately find a 2-cycle ───────────────────────────────────────────────
# Strategy: train a small N=16 Storkey net slightly above capacity (load > 0.138),
# then sweep random initial states until sync update produces a 2-cycle.

N    = 16
SIZE = 4
SEED = 0

def bipolar(bits):
    return np.array([1. if b else -1. for b in bits])

# hand-crafted 4×4 patterns — same as demo_4x4.py
_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
    'X': [1,0,0,1, 0,1,1,0, 0,1,1,0, 1,0,0,1],   # extra pattern → above capacity
}
DIGITS   = ['0', '1', '7', 'X']                   # M=4 > 0.138×16 ≈ 2.2
patterns = np.array([bipolar(_RAW[d]) for d in DIGITS])

net_sync  = HopfieldNetwork(N=N, rule=STORKEY, update_mode=SYNC)
net_async = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net_sync.train(patterns)
net_async.train(patterns)   # same W

def sync_step(W, s):
    s_new = np.sign(W @ s)
    s_new[s_new == 0] = s[s_new == 0]   # tie-break: hold
    return s_new

def is_2cycle(hist):
    if len(hist) >= 3:
        if np.array_equal(hist[-1], hist[-3]) and not np.array_equal(hist[-1], hist[-2]):
            return True
    return False

# search for a 2-cycle initial state
rng = np.random.default_rng(SEED)
found = False
for attempt in range(5000):
    s0 = rng.choice([-1., 1.], size=N)
    hist = [s0.copy()]
    for _ in range(60):
        hist.append(sync_step(net_sync.W, hist[-1]))
        if is_2cycle(hist):
            found = True
            break
    if found:
        break

if not found:
    print("No 2-cycle found with this seed/network — try increasing attempts.")
    sys.exit(0)

cycle_a = hist[-3].copy()   # state A
cycle_b = hist[-2].copy()   # state B  (A→B→A→B…)

print(f"2-cycle found after {attempt+1} random starts, {len(hist)-1} sync steps.")
print(f"  State A energy: {net_sync.energy(cycle_a):.4f}")
print(f"  State B energy: {net_sync.energy(cycle_b):.4f}")
print(f"  A == B: {np.array_equal(cycle_a, cycle_b)}")
verify_ab = sync_step(net_sync.W, cycle_a)
verify_ba = sync_step(net_sync.W, cycle_b)
print(f"  sync(A) == B: {np.array_equal(verify_ab, cycle_b)}")
print(f"  sync(B) == A: {np.array_equal(verify_ba, cycle_a)}")

# ── run both modes from s0, record per-sweep history ─────────────────────────
MAX_SWEEPS = 20

# sync trace
sync_hist   = [s0.copy()]
sync_status = 'running'
for _ in range(MAX_SWEEPS):
    s_next = sync_step(net_sync.W, sync_hist[-1])
    sync_hist.append(s_next)
    if is_2cycle(sync_hist):
        sync_status = '2-cycle detected'
        break
    if np.array_equal(sync_hist[-1], sync_hist[-2]):
        sync_status = 'converged'
        break

# async trace (same s0, same W)
async_hist   = [s0.copy()]
async_status = 'running'
s = s0.copy()
for sweep in range(MAX_SWEEPS):
    s_prev = s.copy()
    for i in range(N):
        h = float(net_async.W[i] @ s)
        if h > 0:   s[i] =  1.0
        elif h < 0: s[i] = -1.0
    async_hist.append(s.copy())
    if np.array_equal(s, s_prev):
        async_status = 'converged'
        break

sync_energies  = [net_sync.energy(st)  for st in sync_hist]
async_energies = [net_sync.energy(st)  for st in async_hist]

# ── figure ────────────────────────────────────────────────────────────────────
BG      = '#0d0d0d'
AX_BG   = '#111111'
PURPLE  = '#2d0047'
GOLD    = '#FFD700'
GREEN   = '#27ae60'
RED     = '#e74c3c'
BLUE    = '#2196F3'

CMAP    = ListedColormap([AX_BG, '#ffffff'])   # OFF=dark, ON=white

def img(s):
    return ((s + 1) / 2).reshape(SIZE, SIZE)

fig = plt.figure(figsize=(14, 7), facecolor=BG)
fig.patch.set_facecolor(BG)
fig.suptitle(
    f'Sync vs Async — 2-Cycle Demonstration  '
    f'(N={N}, M={len(DIGITS)}, Storkey, load={len(DIGITS)/N:.2f} > 0.138)',
    color='white', fontsize=12, fontweight='bold', y=0.98)

imshow_kw = dict(cmap=CMAP, vmin=0, vmax=1, interpolation='nearest')

outer = gridspec.GridSpec(2, 1, figure=fig,
                          hspace=0.55, top=0.92, bottom=0.07,
                          left=0.04, right=0.97)

# ── row 0: SYNC ───────────────────────────────────────────────────────────────
n_show_sync = min(len(sync_hist), 8)
sync_inner  = gridspec.GridSpecFromSubplotSpec(
    1, n_show_sync + 1, subplot_spec=outer[0],
    width_ratios=[1]*n_show_sync + [2.0], wspace=0.15)

for k in range(n_show_sync):
    ax = fig.add_subplot(sync_inner[0, k])
    ax.set_facecolor(AX_BG)
    ax.imshow(img(sync_hist[k]), **imshow_kw)
    ax.set_xticks([]); ax.set_yticks([])
    label = f't={k}' if k < n_show_sync - 1 else f't={k}\n({sync_status})'
    col   = RED if '2-cycle' in sync_status and k >= n_show_sync - 2 else 'white'
    ax.set_title(label, fontsize=7.5, color=col, pad=2)
    for sp in ax.spines.values():
        sp.set_color(RED if ('2-cycle' in sync_status and k >= n_show_sync - 2)
                     else '#444444')
        sp.set_linewidth(2 if ('2-cycle' in sync_status and k >= n_show_sync - 2) else 0.8)

ax_se = fig.add_subplot(sync_inner[0, n_show_sync])
ax_se.set_facecolor(BG)
ax_se.plot(sync_energies, 'o-', color=RED, lw=1.5, ms=5)
ax_se.axhline(net_sync.energy(cycle_a), ls='--', lw=1, color='#ff9999',
              label='Cycle A energy')
ax_se.axhline(net_sync.energy(cycle_b), ls=':', lw=1, color='#ffcccc',
              label='Cycle B energy')
ax_se.set_title('Energy (sync)', fontsize=8, color=RED, pad=3)
ax_se.tick_params(colors='#888888', labelsize=7)
ax_se.legend(fontsize=7, frameon=False, labelcolor='#aaaaaa')
ax_se.set_xlabel('sweep', fontsize=7, color='#888888')
for sp in ax_se.spines.values():
    sp.set_color('#333333')

# row label
fig.text(0.01, (outer[0].get_position(fig).y0 + outer[0].get_position(fig).y1)/2,
         'SYNC\nupdate', va='center', ha='left', fontsize=9,
         color=RED, fontweight='bold', rotation=90,
         transform=fig.transFigure)

# ── row 1: ASYNC ──────────────────────────────────────────────────────────────
n_show_async = min(len(async_hist), 8)
async_inner  = gridspec.GridSpecFromSubplotSpec(
    1, n_show_async + 1, subplot_spec=outer[1],
    width_ratios=[1]*n_show_async + [2.0], wspace=0.15)

for k in range(n_show_async):
    ax = fig.add_subplot(async_inner[0, k])
    ax.set_facecolor(AX_BG)
    ax.imshow(img(async_hist[k]), **imshow_kw)
    ax.set_xticks([]); ax.set_yticks([])
    is_last = k == n_show_async - 1
    label   = f't={k}' + ('\n(converged ✓)' if is_last and 'converged' in async_status else '')
    ax.set_title(label, fontsize=7.5,
                 color=GREEN if (is_last and 'converged' in async_status) else 'white',
                 pad=2)
    for sp in ax.spines.values():
        sp.set_color(GREEN if (is_last and 'converged' in async_status) else '#444444')
        sp.set_linewidth(2 if (is_last and 'converged' in async_status) else 0.8)

ax_ae = fig.add_subplot(async_inner[0, n_show_async])
ax_ae.set_facecolor(BG)
ax_ae.plot(async_energies, 'o-', color=GREEN, lw=1.5, ms=5)
ax_ae.set_title('Energy (async-cyclic)', fontsize=8, color=GREEN, pad=3)
ax_ae.tick_params(colors='#888888', labelsize=7)
ax_ae.set_xlabel('sweep', fontsize=7, color='#888888')
for sp in ax_ae.spines.values():
    sp.set_color('#333333')

fig.text(0.01, (outer[1].get_position(fig).y0 + outer[1].get_position(fig).y1)/2,
         'ASYNC\ncyclic', va='center', ha='left', fontsize=9,
         color=GREEN, fontweight='bold', rotation=90,
         transform=fig.transFigure)

# ── 2-cycle states callout ─────────────────────────────────────────────────────
fig.text(0.5, 0.02,
    f'2-cycle: state A ↔ state B  (energies {net_sync.energy(cycle_a):.2f} ↔ '
    f'{net_sync.energy(cycle_b):.2f})  |  '
    f'Detection: s[t] == s[t−2]  AND  s[t] ≠ s[t−1]  |  '
    f'Async-cyclic: fixed point reached in {len(async_hist)-1} sweep(s) ✓',
    ha='center', fontsize=8, color='#aaaaaa', transform=fig.transFigure)

out = Path(__file__).parent / 'demo_sync_2cycle.png'
fig.savefig(str(out), bbox_inches='tight', dpi=150, facecolor=BG)
print(f"Saved → {out.name}")
plt.show()
