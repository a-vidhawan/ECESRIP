"""
Demo: 8×8 digit Hopfield recall  (N=64)

Stores 3 hand-crafted 8×8 binary digit patterns, corrupts one,
and shows the network recalling it — with energy trace.

Run:  python demo_8x8.py
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import add_noise

try:
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("matplotlib required: pip install matplotlib")

# ── patterns ──────────────────────────────────────────────────────────────────
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
    '7': [1,1,1,1,1,1,1,1,
          0,0,0,0,0,0,1,1,
          0,0,0,0,0,1,1,0,
          0,0,0,0,1,1,0,0,
          0,0,0,1,1,0,0,0,
          0,0,1,1,0,0,0,0,
          0,1,1,0,0,0,0,0,
          1,1,0,0,0,0,0,0],
}

DIGITS   = ['0', '1', '7']
SIZE     = 8          # 8×8 grid
N        = SIZE * SIZE  # 64 neurons
N_FLIPS  = 10         # ~16% corruption
SEED     = 42

def bipolar(bits): return np.array([1. if b else -1. for b in bits])

patterns = np.array([bipolar(_RAW[d]) for d in DIGITS])

# ── train ─────────────────────────────────────────────────────────────────────
net = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)

# ── recall with step-by-step trace ────────────────────────────────────────────
rng     = np.random.default_rng(SEED)
target  = patterns[0]
corrupt = add_noise(target, n_flips=N_FLIPS, rng=rng)

print(f"8×8 Hopfield Demo  |  N={N}  M={len(DIGITS)}  rule=Storkey  update=async-cyclic")
print(f"Corrupted digit '0' with {N_FLIPS}/{N} bit flips ({100*N_FLIPS//N}%)\n")
print(f"  {'Step':<14} {'Energy':>8}   {'Δ from target':>14}")
print(f"  {'-'*14} {'-'*8}   {'-'*14}")

def row(label, s):
    hmm = int((s != target).sum())
    tag = '✓ match' if hmm == 0 else f'{hmm} bits off'
    print(f"  {label:<14} {net.energy(s):>8.3f}   {tag}")

row('Target',    target)
row('Corrupted', corrupt)
print()

s = corrupt.copy()
energies = [net.energy(corrupt)]
for sweep in range(1, 21):
    s_prev = s.copy()
    for i in np.arange(N):
        h = float(net.W[i] @ s)
        if h > 0: s[i] = 1.
        elif h < 0: s[i] = -1.
    energies.append(net.energy(s))
    row(f'Sweep {sweep}', s)
    if np.array_equal(s, s_prev):
        recalled = s
        n_sweeps = sweep
        break

hamming_out = int((recalled != target).sum())
print(f"\n  Converged in {n_sweeps} sweep(s)  ({n_sweeps * N} neuron updates = {n_sweeps * N} clock cycles)")
print(f"  {'✓ Perfect recall' if hamming_out == 0 else f'Hamming distance from target = {hamming_out}'}")

# ── plot ──────────────────────────────────────────────────────────────────────
def img(s): return ((s + 1) / 2).reshape(SIZE, SIZE)

fig = plt.figure(figsize=(13, 5))
gs  = plt.GridSpec(2, 5, figure=fig, wspace=0.25, hspace=0.45,
                   width_ratios=[1, 1, 1, 0.15, 1.6])

# row 0: stored patterns
for col, (d, p) in enumerate(zip(DIGITS, patterns)):
    ax = fig.add_subplot(gs[0, col])
    ax.imshow(img(p), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.set_title(f"Stored '{d}'", fontsize=10)
    ax.axis('off')

# row 0 col 4: energy convergence trace
ax_e = fig.add_subplot(gs[0, 4])
ax_e.plot(range(len(energies)), energies, 'o-', color='#2196F3', lw=2, ms=6)
ax_e.set_xlabel('Sweep', fontsize=9)
ax_e.set_ylabel('Energy E(s)', fontsize=9)
ax_e.set_title('Energy vs sweep', fontsize=10)
ax_e.axhline(net.energy(target), ls='--', lw=1, color='green', label='Target energy')
ax_e.legend(fontsize=8, frameon=False)
ax_e.spines['top'].set_visible(False)
ax_e.spines['right'].set_visible(False)

# row 1: original | corrupted | recalled
for col, (title, state) in enumerate(
        zip(['Original', f'Corrupted\n({N_FLIPS}/{N} bits)', 'Recalled'],
            [target, corrupt, recalled])):
    ax = fig.add_subplot(gs[1, col])
    ax.imshow(img(state), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.set_title(title, fontsize=10)
    ax.axis('off')

e_in  = net.energy(corrupt)
e_out = net.energy(recalled)
fig.text(0.5, 0.01,
    f'Energy: {e_in:.2f} → {e_out:.2f}  (ΔE = {e_out-e_in:.2f},  '
    f'{n_sweeps} sweep(s),  {n_sweeps*N} clock cycles,  '
    f'{"perfect recall ✓" if hamming_out==0 else f"Δ={hamming_out}"})',
    ha='center', fontsize=10, color='#333')

fig.suptitle(f'Hopfield 8×8 Digit Recall  (N={N}, M={len(DIGITS)}, Storkey, async-cyclic)',
             fontweight='bold')
plt.savefig('result_8x8.png', bbox_inches='tight', dpi=150)
print("\n  Plot saved → result_8x8.png")
plt.show()
