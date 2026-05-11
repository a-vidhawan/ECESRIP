"""
Demo: MNIST-8 Hopfield recall (N=64, 8×8 binarized digits).

Shows:
  - Store 3 digit images in a N=64 Hopfield network (Storkey)
  - Corrupt one digit with 20% pixel flips
  - Recall and display: original | corrupted | recalled

Requires: scikit-learn (pip install scikit-learn)
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
NOISE = 0.20   # fraction of pixels to flip
SEED  = 42
# ─────────────────────────────────────────────────────────────────────────────

# Hand-crafted 8×8 binary digit patterns (no download needed)
_DIGITS = {
    '0': [0,1,1,1,1,1,1,0,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          1,1,0,0,0,0,1,1,
          0,1,1,1,1,1,1,0],
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

def _to_bipolar(bits):
    return np.array([1.0 if b else -1.0 for b in bits])

patterns = np.array([_to_bipolar(_DIGITS[d]) for d in ['0', '1', '7']])
N_PATTERNS = len(patterns)
print(f"Using hand-crafted 8×8 digit patterns (digits: 0, 1, 7)  N=64  M={N_PATTERNS}")

net = HopfieldNetwork(N=64, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)
print(f"Trained Storkey network  N=64  M={N_PATTERNS}")

rng     = np.random.default_rng(SEED)
target  = patterns[0]
n_flips = int(NOISE * 64)
corrupt = add_noise(target, n_flips=n_flips, rng=rng)
recalled, n_sweeps, converged = net.run(corrupt)

hamming_in  = int((corrupt  != target).sum())
hamming_out = int((recalled != target).sum())

print(f"\nCorrupted {n_flips}/64 pixels (Hamming = {hamming_in})")
print(f"Converged in {n_sweeps} sweep(s): Hamming after recall = {hamming_out}")
if hamming_out == 0:
    print("✓ Perfect recall")
else:
    print(f"Partial recall — {hamming_out} pixels differ from original")

# ── plot ──────────────────────────────────────────────────────────────────────
def to_img(s):
    """Bipolar {-1,+1} → grayscale [0,1] 8×8."""
    return ((s + 1) / 2).reshape(8, 8)

fig = plt.figure(figsize=(11, 5))
gs  = gridspec.GridSpec(2, N_PATTERNS + 3, figure=fig, wspace=0.15, hspace=0.4)

# top row: stored patterns
for i, p in enumerate(patterns):
    ax = fig.add_subplot(gs[0, i])
    ax.imshow(to_img(p), cmap='gray', vmin=0, vmax=1)
    ax.set_title(f'Stored {i}', fontsize=9)
    ax.axis('off')

# bottom row: corrupted → recalled (with arrow)
titles  = ['Original', 'Corrupted\n(20% flipped)', 'Recalled']
images  = [target, corrupt, recalled]
offsets = [N_PATTERNS, N_PATTERNS + 1, N_PATTERNS + 2]

for ax_col, img, title in zip(offsets, images, titles):
    ax = fig.add_subplot(gs[1, ax_col])
    ax.imshow(to_img(img), cmap='gray', vmin=0, vmax=1)
    ax.set_title(title, fontsize=9)
    ax.axis('off')

# energy annotation
e_corrupt  = net.energy(corrupt)
e_recalled = net.energy(recalled)
fig.text(0.5, 0.03,
         f'Energy: corrupt = {e_corrupt:.2f}  →  recalled = {e_recalled:.2f}   '
         f'(Δ = {e_recalled - e_corrupt:.2f},  {n_sweeps} sweep(s))',
         ha='center', fontsize=10, color='#333333')

fig.suptitle(f'Hopfield MNIST-8 Recall  (N=64, M={N_PATTERNS}, Storkey, async-cyclic)',
             fontweight='bold', fontsize=11)

plt.savefig('demo_mnist_result.png', bbox_inches='tight', dpi=130)
print("\nSaved → demo_mnist_result.png")
plt.show()
