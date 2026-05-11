"""
Demo: Random-pattern Hopfield recall with energy trace.

Shows:
  - Store 2 patterns in a N=16 network (Storkey)
  - Corrupt pattern 0 with 30% bit flips
  - Run async-cyclic update sweep by sweep
  - Print state and energy at each step until convergence

Run from this directory:
    python demo_random.py
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import random_patterns, add_noise

# ── config ────────────────────────────────────────────────────────────────────
N        = 16
M        = 2
NOISE    = 0.30   # fraction of bits to flip
SEED     = 7
# ─────────────────────────────────────────────────────────────────────────────

rng = np.random.default_rng(SEED)

patterns = random_patterns(N, M, seed=SEED)
net = HopfieldNetwork(N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
net.train(patterns)

target  = patterns[0]
corrupt = add_noise(target, n_flips=int(NOISE * N), rng=rng)
hamming_init = int((corrupt != target).sum())

print(f"N={N}  M={M}  rule=Storkey  update=async-cyclic")
print(f"Noise: {int(NOISE*N)}/{N} bits flipped (Hamming distance = {hamming_init})\n")

def bits(s):
    return ''.join('█' if x > 0 else '░' for x in s)

def row(label, s, energy, hamming):
    marker = ' ✓' if hamming == 0 else f'  (Δ={hamming})'
    print(f"  {label:<12} E={energy:+.3f}  {bits(s)}{marker}")

print(f"  {'Label':<12} {'Energy':>10}  State")
print(f"  {'-'*12} {'-'*10}  {'-'*N}")
row('Target',    target,  net.energy(target),  0)
row('Corrupt',   corrupt, net.energy(corrupt), hamming_init)
print()

# step through sweeps manually to show energy per sweep
s = corrupt.copy()
for sweep in range(1, 21):
    s_prev = s.copy()
    order = np.arange(N)
    for i in order:
        h_i = float(net.W[i] @ s)
        if h_i > 0:   s[i] =  1.0
        elif h_i < 0: s[i] = -1.0

    e      = net.energy(s)
    hamming = int((s != target).sum())
    row(f'Sweep {sweep}', s, e, hamming)

    if np.array_equal(s, s_prev):
        print(f"\n  Converged at sweep {sweep}.")
        if hamming == 0:
            print("  ✓ Recovered stored pattern exactly.")
        else:
            print(f"  Converged to a different attractor (Hamming={hamming} from target).")
        break
