"""
mnist_demo.py
=============
Trains a binary Hopfield network on binarised sklearn digit patterns (8×8)
and generates four visualisation images used in the May 19 presentation.

Outputs (written to ./viz/):
  stored_patterns.png     - the digit patterns stored in the network
  weight_matrix.png       - heatmap of the learned weight matrix W
  retrieval_demo.png      - noisy probe → convergence steps → recovered pattern
  energy_convergence.png  - Lyapunov energy as a function of async update steps

Usage:
  python mnist_demo.py

Dependencies: numpy, matplotlib, scikit-learn
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from sklearn.datasets import load_digits

OUT = Path("viz")
OUT.mkdir(exist_ok=True)

RNG = np.random.default_rng(42)
PALETTE = {
    "dark":    "#0D1B2A",
    "mid":     "#1B4F72",
    "accent":  "#2E86AB",
    "light":   "#A8DADC",
    "white":   "#F5F5F5",
    "neg":     "#C0392B",
    "pos":     "#1A7A4A",
    "neutral": "#95A5A6",
}

# ── helpers ──────────────────────────────────────────────────────────────────

def binarise(img: np.ndarray, threshold: float = 7.0) -> np.ndarray:
    """Map sklearn digit image (0-16 ints) to bipolar {-1, +1}."""
    return np.where(img.ravel() >= threshold, 1, -1).astype(np.int8)


def train_hebbian(patterns: list[np.ndarray]) -> np.ndarray:
    N = patterns[0].size
    W = np.zeros((N, N))
    for xi in patterns:
        W += np.outer(xi, xi)
    W /= N
    np.fill_diagonal(W, 0)
    return W


def async_update(W, state, steps, rng=None):
    if rng is None:
        rng = np.random.default_rng()
    s = state.copy().astype(np.float64)
    N = len(s)
    history = [s.copy()]
    for _ in range(steps):
        i = rng.integers(0, N)
        h = W[i] @ s
        s[i] = 1.0 if h >= 0 else -1.0
        history.append(s.copy())
    return np.int8(s), history


def energy(W, s):
    s = s.astype(np.float64)
    return float(-0.5 * s @ W @ s)


def overlap(xi, s):
    return float(xi @ s) / len(xi)


# ── data ─────────────────────────────────────────────────────────────────────

digits = load_digits()
# Pick one clear example of each digit class 0-4
chosen = []
labels = []
for d in range(5):
    idxs = np.where(digits.target == d)[0]
    chosen.append(digits.images[idxs[0]])
    labels.append(str(d))

patterns = [binarise(img) for img in chosen]
N = patterns[0].size            # 64 neurons (8×8)
P = len(patterns)               # 5 patterns
W = train_hebbian(patterns)

# ── Figure 1: stored patterns ─────────────────────────────────────────────────

fig, axes = plt.subplots(1, P, figsize=(11, 2.6), facecolor=PALETTE["dark"])
fig.suptitle("Stored Patterns (Digits 0–4,  8×8 grid  →  64 neurons)",
             color=PALETTE["white"], fontsize=13, fontweight="bold", y=1.02)
for ax, pat, lbl in zip(axes, patterns, labels):
    img = pat.reshape(8, 8)
    ax.imshow(img, cmap="RdYlGn", vmin=-1, vmax=1, interpolation="nearest")
    ax.set_title(f"Digit {lbl}", color=PALETTE["light"], fontsize=11)
    ax.axis("off")
plt.tight_layout(pad=0.4)
fig.savefig(OUT / "stored_patterns.png", dpi=150, bbox_inches="tight",
            facecolor=PALETTE["dark"])
plt.close()
print("saved stored_patterns.png")

# ── Figure 2: weight matrix heatmap ──────────────────────────────────────────

fig, ax = plt.subplots(figsize=(6.5, 5.8), facecolor=PALETTE["dark"])
im = ax.imshow(W, cmap="seismic", vmin=-np.abs(W).max(), vmax=np.abs(W).max())
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.ax.yaxis.set_tick_params(color=PALETTE["light"])
cbar.outline.set_edgecolor(PALETTE["light"])
plt.setp(cbar.ax.yaxis.get_ticklabels(), color=PALETTE["light"])
ax.set_title(f"Hebbian Weight Matrix W  ({N}×{N})\n"
             f"Trained on {P} patterns  |  diagonal = 0",
             color=PALETTE["white"], fontsize=12, fontweight="bold")
ax.set_xlabel("Neuron j", color=PALETTE["light"])
ax.set_ylabel("Neuron i", color=PALETTE["light"])
ax.tick_params(colors=PALETTE["neutral"])
for spine in ax.spines.values():
    spine.set_edgecolor(PALETTE["neutral"])
fig.patch.set_facecolor(PALETTE["dark"])
ax.set_facecolor(PALETTE["dark"])
plt.tight_layout()
fig.savefig(OUT / "weight_matrix.png", dpi=150, bbox_inches="tight",
            facecolor=PALETTE["dark"])
plt.close()
print("saved weight_matrix.png")

# ── Figure 3: retrieval demo ──────────────────────────────────────────────────
# Take digit "3", corrupt 12 bits, run 5 sync steps, show snapshots

target_idx = 3            # digit "3"
xi = patterns[target_idx]
n_flips = 12              # ~19 % noise

noisy = xi.copy()
flip_idx = RNG.choice(N, size=n_flips, replace=False)
noisy[flip_idx] *= -1

# Run sync steps, capture snapshots at 0,1,2,3,10,25
def sync_step(W, s):
    return np.sign(W @ s.astype(np.float64)).astype(np.int8)

snapshots = [noisy.copy()]
snap_labels = ["Noisy\nInput"]
s = noisy.copy()
current_step = 0
for step in [1, 2, 3, 10, 25]:
    while current_step < step:
        s = sync_step(W, s)
        current_step += 1
    snapshots.append(s.copy())
    snap_labels.append(f"Step {step}")

snapshots.append(xi.copy())
snap_labels.append("Original\n(stored)")

ncols = len(snapshots)
fig, axes = plt.subplots(1, ncols, figsize=(2.2 * ncols, 2.8), facecolor=PALETTE["dark"])
fig.suptitle(f'Retrieval Demo — Digit "3"  ({n_flips}/{N} bits flipped = {round(n_flips*100/N)}% noise)',
             color=PALETTE["white"], fontsize=12, fontweight="bold", y=1.04)

for ax, snap, lbl in zip(axes, snapshots, snap_labels):
    ax.imshow(snap.reshape(8, 8), cmap="RdYlGn", vmin=-1, vmax=1, interpolation="nearest")
    ov = overlap(xi, snap)
    color = PALETTE["pos"] if ov > 0.9 else PALETTE["accent"] if ov > 0.5 else PALETTE["neg"]
    ax.set_title(f"{lbl}\nm={ov:.2f}", color=color, fontsize=9, pad=3)
    ax.axis("off")

# Draw arrow between snapshots
for i in range(ncols - 2):   # skip before "Original"
    fig.add_artist(matplotlib.patches.FancyArrowPatch(
        posA=((i + 1) / ncols + 0.01, 0.5),
        posB=((i + 1) / ncols + 0.04, 0.5),
        arrowstyle="->,head_length=0.01,head_width=0.005",
        color=PALETTE["light"],
        transform=fig.transFigure,
        linewidth=1.5,
    ))

plt.tight_layout(pad=0.5)
fig.savefig(OUT / "retrieval_demo.png", dpi=150, bbox_inches="tight",
            facecolor=PALETTE["dark"])
plt.close()
print("saved retrieval_demo.png")

# ── Figure 4: energy convergence ─────────────────────────────────────────────
# Async update, log energy every step for all 5 stored patterns

fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=PALETTE["dark"])
step_colors = [PALETTE["accent"], "#E74C3C", "#F39C12", "#27AE60", "#9B59B6"]
MAX_STEPS = 200

for idx, (xi, lbl, col) in enumerate(zip(patterns, labels, step_colors)):
    noisy_p = xi.copy()
    flip_p = RNG.choice(N, size=8, replace=False)
    noisy_p[flip_p] *= -1

    s, history = async_update(W, noisy_p, MAX_STEPS, RNG)
    energies = [energy(W, np.int8(h)) for h in history]
    xs = list(range(len(energies)))

    # Subsample for clarity
    stride = max(1, len(xs) // 60)
    ax.plot([xs[i] for i in range(0, len(xs), stride)],
            [energies[i] for i in range(0, len(energies), stride)],
            color=col, linewidth=2, label=f"Digit {lbl}", alpha=0.9)

ax.axhline(y=0, color=PALETTE["neutral"], linewidth=0.6, linestyle="--")
ax.set_title("Lyapunov Energy During Async Retrieval\n"
             "E(s) = −½ sᵀWs   (monotonically non-increasing  →  convergence guaranteed)",
             color=PALETTE["white"], fontsize=11, fontweight="bold")
ax.set_xlabel("Async update steps", color=PALETTE["light"], fontsize=11)
ax.set_ylabel("Energy  E(s)", color=PALETTE["light"], fontsize=11)
ax.tick_params(colors=PALETTE["neutral"])
for spine in ax.spines.values():
    spine.set_edgecolor(PALETTE["neutral"])
ax.set_facecolor("#0D1B2A")
legend = ax.legend(facecolor="#1B2631", labelcolor=PALETTE["light"], fontsize=9)
fig.patch.set_facecolor(PALETTE["dark"])
plt.tight_layout()
fig.savefig(OUT / "energy_convergence.png", dpi=150, bbox_inches="tight",
            facecolor=PALETTE["dark"])
plt.close()
print("saved energy_convergence.png")

print("\nAll done — images in ./viz/")
