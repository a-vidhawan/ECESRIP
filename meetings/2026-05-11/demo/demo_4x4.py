"""
Demo: 4×4 digit Hopfield recall  (N=16)

Stores 3 hand-crafted 4×4 binary digit patterns, corrupts one,
and shows the network recalling it — with energy trace.

Run:  python demo_4x4.py
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

DIGITS   = ['0', '1', '7']
SIZE     = 4          # 4×4 grid
N        = SIZE * SIZE  # 16 neurons
N_FLIPS  = 4          # 25% corruption
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

print(f"4×4 Hopfield Demo  |  N={N}  M={len(DIGITS)}  rule=Storkey  update=async-cyclic")
print(f"Corrupted digit '0' with {N_FLIPS}/{N} bit flips\n")
print(f"  {'Step':<14} {'Energy':>8}   State")
print(f"  {'-'*14} {'-'*8}   {'-'*N}")

def row(label, s):
    bar = ''.join('█' if x > 0 else '░' for x in s)
    hmm = int((s != target).sum())
    tag = ' ✓' if hmm == 0 else f'  Δ={hmm}'
    print(f"  {label:<14} {net.energy(s):>8.3f}   {bar}{tag}")

row('Target',   target)
row('Corrupted', corrupt)
print()

s = corrupt.copy()
for sweep in range(1, 21):
    s_prev = s.copy()
    for i in np.arange(N):
        h = float(net.W[i] @ s)
        if h > 0: s[i] = 1.
        elif h < 0: s[i] = -1.
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

fig, axes = plt.subplots(1, 7, figsize=(11, 2.8))
for ax in axes: ax.axis('off')

# stored patterns
for col, (d, p) in enumerate(zip(DIGITS, patterns)):
    axes[col].imshow(img(p), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    axes[col].set_title(f"Stored '{d}'", fontsize=10)

axes[3].axis('off')   # spacer

for col, (title, state) in enumerate(
        zip(['Original', f'Corrupted\n({N_FLIPS} bits)', 'Recalled'],
            [target, corrupt, recalled]), start=4):
    axes[col].imshow(img(state), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    axes[col].set_title(title, fontsize=10)

e_in  = net.energy(corrupt)
e_out = net.energy(recalled)
fig.text(0.5, -0.04,
    f'Energy: {e_in:.2f} → {e_out:.2f}  (ΔE = {e_out-e_in:.2f},  '
    f'{n_sweeps} sweep(s),  {n_sweeps*N} clock cycles,  '
    f'{"perfect recall ✓" if hamming_out==0 else f"Δ={hamming_out}"})',
    ha='center', fontsize=10)

fig.suptitle(f'Hopfield 4×4 Digit Recall  (N={N}, M={len(DIGITS)}, Storkey, async-cyclic)',
             fontweight='bold', y=1.05)
plt.tight_layout()
plt.savefig('result_4x4.png', bbox_inches='tight', dpi=150)
print("\n  Plot saved → result_4x4.png")
plt.show()
