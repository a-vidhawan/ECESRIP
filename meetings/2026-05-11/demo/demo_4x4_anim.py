"""
Animated 4×4 Hopfield recall demo  (N=16)

Backed entirely by HopfieldNetwork from sim/python/.
Two panels animate in lockstep:
  Left  — 4×4 pixel grid (neuron states)
  Right — network graph: nodes coloured by state, edges green/red by weight sign

Each animation frame = one neuron update in async-cyclic order.
Frames are grouped so you can see every individual flip.

Run:
    python demo_4x4_anim.py          # interactive window + saves demo_4x4_anim.gif
    python demo_4x4_anim.py --nosave # interactive only (faster start)
"""

import sys
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
import networkx as nx

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import add_noise

# ── config ────────────────────────────────────────────────────────────────────
_RAW = {
    '0': [0,1,1,0,
          1,0,0,1,
          1,0,0,1,
          0,1,1,0],
    '1': [0,1,1,0,
          0,0,1,0,
          0,0,1,0,
          0,1,1,1],
    '7': [1,1,1,1,
          0,0,0,1,
          0,0,1,0,
          0,1,0,0],
}
DIGITS  = ['0', '1', '7']
SIZE    = 4
N       = SIZE * SIZE
N_FLIPS = 4
SEED    = 42
MAX_SWEEPS = 20

# edge display: show only the TOP_K strongest edges (avoids visual clutter)
TOP_K   = 40   # out of 120 possible edges for N=16

INTERVAL_MS = 180   # ms between frames

# ── helpers ───────────────────────────────────────────────────────────────────
def bipolar(bits):
    return np.array([1. if b else -1. for b in bits])

BG     = '#0d0d0d'
AX_BG  = '#111111'

def state_color(val):
    """White for +1 neuron (ON), near-black for -1 (OFF)."""
    return '#ffffff' if val > 0 else '#1a1a1a'

def edge_color(w):
    return '#27ae60' if w > 0 else '#e74c3c'   # green / red

# ── train the real network ────────────────────────────────────────────────────
patterns = np.array([bipolar(_RAW[d]) for d in DIGITS])
net = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)

# ── build full async-cyclic update trace ─────────────────────────────────────
# Each entry in `frames` is a complete N-vector of bipolar states.
# We record the state AFTER every individual neuron update.
rng     = np.random.default_rng(SEED)
target  = patterns[0]
corrupt = add_noise(target, n_flips=N_FLIPS, rng=rng)

frames         = [corrupt.copy()]   # frame 0 = initial corrupted
neuron_updated = [-1]               # which neuron just flipped (-1 = none yet)
sweep_of_frame = [0]                # which sweep this frame belongs to

s = corrupt.copy()
converged_sweep = None

for sweep in range(1, MAX_SWEEPS + 1):
    s_prev = s.copy()
    for i in range(N):
        h = float(net.W[i] @ s)
        new_val = 1.0 if h > 0 else (-1.0 if h < 0 else s[i])
        s[i] = new_val
        frames.append(s.copy())
        neuron_updated.append(i)
        sweep_of_frame.append(sweep)
    if np.array_equal(s, s_prev):
        converged_sweep = sweep
        break

recalled     = s.copy()
n_sweeps     = converged_sweep if converged_sweep else MAX_SWEEPS
hamming_out  = int((recalled != target).sum())
total_frames = len(frames)

# ── build graph (fixed topology, weights from net.W) ─────────────────────────
G   = nx.Graph()
G.add_nodes_from(range(N))

# collect all edges sorted by |weight|, keep TOP_K
all_edges = [(i, j, net.W[i, j])
             for i in range(N) for j in range(i+1, N)
             if net.W[i, j] != 0]
all_edges.sort(key=lambda e: abs(e[2]), reverse=True)
top_edges = all_edges[:TOP_K]

for i, j, w in top_edges:
    G.add_edge(i, j, weight=w)

# grid layout matching the 4×4 pixel positions
pos = {i: (i % SIZE, SIZE - 1 - i // SIZE) for i in range(N)}

# precompute fixed edge colours and widths
w_vals  = np.array([d['weight'] for _, _, d in G.edges(data=True)])
w_abs   = np.abs(w_vals)
w_norm  = w_abs / (w_abs.max() + 1e-9)   # 0…1
e_colors = [edge_color(w) for w in w_vals]
e_widths  = 0.5 + 3.5 * w_norm           # 0.5…4 px

edge_list = list(G.edges())

# ── figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(13, 5.5), facecolor=BG)
fig.patch.set_facecolor(BG)

# GridSpec: [stored0] [stored1] [stored2] | gap | [pixel_grid] | gap | [graph]
gs = fig.add_gridspec(1, 7, width_ratios=[1, 1, 1, 0.3, 1.6, 0.3, 2.5],
                      left=0.03, right=0.97, top=0.86, bottom=0.10, wspace=0.05)

# stored pattern thumbnails (static)
ax_stored = [fig.add_subplot(gs[0, k]) for k in range(3)]
for ax, (d, p) in zip(ax_stored, zip(DIGITS, patterns)):
    ax.set_facecolor(AX_BG)
    ax.imshow(((p + 1) / 2).reshape(SIZE, SIZE),
              cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.set_title(f"Stored '{d}'", fontsize=9, pad=3, color='#cccccc')
    ax.axis('off')

# animated pixel grid
ax_pix = fig.add_subplot(gs[0, 4])
ax_pix.set_facecolor(AX_BG)
pix_img = ax_pix.imshow(((corrupt + 1) / 2).reshape(SIZE, SIZE),
                         cmap='gray', vmin=0, vmax=1, interpolation='nearest',
                         animated=True)
pix_title = ax_pix.set_title('Corrupted input', fontsize=10, pad=4,
                              color='#cccccc')
ax_pix.axis('off')

# animated graph
ax_g = fig.add_subplot(gs[0, 6])
ax_g.set_facecolor(AX_BG)
ax_g.axis('off')

# draw static edges once
nx.draw_networkx_edges(G, pos, edgelist=edge_list,
                       edge_color=e_colors, width=e_widths,
                       ax=ax_g, alpha=0.55)

# draw nodes (will be updated each frame via scatter)
node_scat = nx.draw_networkx_nodes(
    G, pos,
    node_color=[state_color(v) for v in corrupt],
    node_size=260,
    linewidths=1.2,
    ax=ax_g
)
node_scat.set_edgecolor('#666666')

ax_g.set_title('Neuron states & weights', fontsize=10, pad=4,
               color='#cccccc')

# highlight ring for the currently-updating neuron
highlight_ring, = ax_g.plot([], [], 'o',
                              markersize=18, markerfacecolor='none',
                              markeredgecolor='#f39c12', markeredgewidth=2.5,
                              zorder=5, animated=True)

# bottom status text
status_txt = fig.text(0.5, 0.02, '', ha='center', fontsize=9, color='#aaaaaa')

# legend
leg_handles = [
    mpatches.Patch(color='#ffffff', label='Neuron ON (+1)',
                   edgecolor='#555555'),
    mpatches.Patch(color='#1a1a1a', label='Neuron OFF (−1)',
                   edgecolor='#555555'),
    plt.Line2D([0],[0], color='#27ae60', lw=2, label='Positive weight'),
    plt.Line2D([0],[0], color='#e74c3c', lw=2, label='Negative weight'),
    plt.Line2D([0],[0], marker='o', color=BG, markersize=10,
               markerfacecolor='none', markeredgecolor='#f39c12',
               markeredgewidth=2, label='Active neuron'),
]
fig.legend(handles=leg_handles, loc='lower right', fontsize=8,
           frameon=True, facecolor='#1a1a1a', edgecolor='#444444',
           labelcolor='white',
           bbox_to_anchor=(0.98, 0.02))

fig.suptitle(
    f'4×4 Hopfield Recall  (N={N}, M={len(DIGITS)}, Storkey, async-cyclic)',
    fontweight='bold', fontsize=12, y=0.97, color='white')

# ── animation update function ─────────────────────────────────────────────────
def update(frame_idx):
    state  = frames[frame_idx]
    neuron = neuron_updated[frame_idx]
    sweep  = sweep_of_frame[frame_idx]

    # pixel grid
    pix_img.set_data(((state + 1) / 2).reshape(SIZE, SIZE))

    hamming = int((state != target).sum())
    if frame_idx == 0:
        pix_title.set_text(f'Corrupted  (Δ={N_FLIPS} bits)')
    elif hamming == 0:
        pix_title.set_text(f'Sweep {sweep} — ✓ recalled!')
    else:
        pix_title.set_text(f'Sweep {sweep}  (Δ={hamming} bits)')

    # graph nodes
    node_scat.set_facecolor([state_color(state[i]) for i in range(N)])

    # highlight ring on the active neuron
    if neuron >= 0:
        nx_val, ny_val = pos[neuron]
        highlight_ring.set_data([nx_val], [ny_val])
    else:
        highlight_ring.set_data([], [])

    # status bar
    e = net.energy(state)
    if frame_idx == 0:
        msg = f'Initial corrupted state  |  Energy = {e:.3f}'
    else:
        step_in_sweep = (frame_idx - 1) % N + 1
        msg = (f'Sweep {sweep}  step {step_in_sweep}/{N}  '
               f'neuron {neuron}  |  Energy = {e:.3f}')
        if frame_idx == total_frames - 1:
            msg += (f'  →  converged in {n_sweeps} sweep(s),  '
                    f'{n_sweeps*N} clock cycles  '
                    f'{"✓ perfect recall" if hamming_out==0 else f"Δ={hamming_out}"}')

    status_txt.set_text(msg)

    return pix_img, node_scat, highlight_ring, pix_title, status_txt


anim = FuncAnimation(fig, update, frames=total_frames,
                     interval=INTERVAL_MS, blit=False, repeat=True,
                     repeat_delay=2000)

# ── save / show ───────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--nosave', action='store_true')
args, _ = parser.parse_known_args()

if not args.nosave:
    out = Path(__file__).parent / 'demo_4x4_anim.gif'
    print(f"Saving animation → {out.name}  ({total_frames} frames) …")
    anim.save(str(out), writer=PillowWriter(fps=1000 // INTERVAL_MS),
              dpi=110)
    print("  Done.")

plt.show()
