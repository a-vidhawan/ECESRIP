"""
Demo: 4×4 digit Hopfield recall (N=16, hardware-realistic size).

Shows:
  - Store 3 hand-crafted 4×4 digit patterns in a N=16 Hopfield network (Storkey)
  - Corrupt one digit with ~25% pixel flips (4 bits)
  - Recall and display: stored patterns | original | corrupted | recalled

N=16 is the largest size at which truth table enumeration (2^16 rows) is
borderline feasible — this demo reflects the actual hardware target.

Run from this directory:
    python demo_mnist.py
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import add_noise

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
except ImportError:
    print("matplotlib required: pip install matplotlib")
    sys.exit(1)

# ── config ────────────────────────────────────────────────────────────────────
N_FLIPS = 4     # bits to corrupt out of 16  (25%)
SEED    = 42
SIZE    = 4     # grid size (4×4 = N=16)
# ─────────────────────────────────────────────────────────────────────────────

# Hand-crafted 4×4 digit patterns
_DIGITS = {
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

def _to_bipolar(bits):
    return np.array([1.0 if b else -1.0 for b in bits])

patterns = np.array([_to_bipolar(_DIGITS[d]) for d in ['0', '1', '7']])
N_PATTERNS = len(patterns)
N = SIZE * SIZE   # 16

print(f"4×4 digit patterns (0, 1, 7)  N={N}  M={N_PATTERNS}")

net = HopfieldNetwork(N=N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)
print(f"Trained Storkey network  N={N}  M={N_PATTERNS}")

rng     = np.random.default_rng(SEED)
target  = patterns[0]   # corrupt the '0'
corrupt = add_noise(target, n_flips=N_FLIPS, rng=rng)
recalled, n_sweeps, converged = net.run(corrupt)

hamming_in  = int((corrupt  != target).sum())
hamming_out = int((recalled != target).sum())

print(f"\nCorrupted {N_FLIPS}/{N} bits (Hamming = {hamming_in})")
print(f"Converged in {n_sweeps} sweep(s)  |  Hamming after recall = {hamming_out}")
print("✓ Perfect recall" if hamming_out == 0
      else f"Partial recall — {hamming_out} bits differ from original")

# ── plot ──────────────────────────────────────────────────────────────────────
def to_img(s):
    return ((s + 1) / 2).reshape(SIZE, SIZE)

fig = plt.figure(figsize=(10, 4.5))
# cols: 3 stored patterns | gap | original | corrupted | recalled
gs = gridspec.GridSpec(1, N_PATTERNS + 1 + 3, figure=fig,
                       wspace=0.08, width_ratios=[1,1,1, 0.4, 1,1,1])

# stored patterns
for i, (d, p) in enumerate(zip(['0','1','7'], patterns)):
    ax = fig.add_subplot(gs[0, i])
    ax.imshow(to_img(p), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.set_title(f"Stored '{d}'", fontsize=10)
    ax.axis('off')

# divider (blank axis)
fig.add_subplot(gs[0, 3]).axis('off')

# recall triplet
titles = ['Original', f'Corrupted\n({N_FLIPS} bits flipped)', 'Recalled']
images = [target, corrupt, recalled]
for col, (img, title) in enumerate(zip(images, titles), start=4):
    ax = fig.add_subplot(gs[0, col])
    ax.imshow(to_img(img), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.set_title(title, fontsize=10)
    ax.axis('off')

e_in  = net.energy(corrupt)
e_out = net.energy(recalled)
fig.text(0.5, 0.01,
         f'Energy: {e_in:.2f}  →  {e_out:.2f}   (ΔE = {e_out-e_in:.2f},  {n_sweeps} sweep(s),  '
         f'{"perfect recall ✓" if hamming_out == 0 else f"Hamming={hamming_out}"})',
         ha='center', fontsize=10, color='#333333')

fig.suptitle(f'Hopfield 4×4 Digit Recall  (N={N}, M={N_PATTERNS}, Storkey, async-cyclic)',
             fontweight='bold', fontsize=11, y=1.02)

plt.savefig('demo_mnist_result.png', bbox_inches='tight', dpi=150)
print("\nSaved → demo_mnist_result.png")
plt.show()
