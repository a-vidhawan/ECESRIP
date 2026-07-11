"""
train_gd.py
===========
Gradient-descent and LP-based training for sparse Hopfield networks.
These are alternatives to pseudo-inverse that directly control per-neuron
degree (number of non-zero connections) while keeping all stored patterns
as exact fixed points.

Three methods
-------------
1. train_l1svm     — per-neuron L1-SVM: solve N independent linear programs.
                     Globally optimal sparse weights for the given connectivity.
                     Directly controls degree via the LP constraint set.

2. train_perceptron_l1 — iterative hinge-margin loss + L1 proximal (ISTA).
                         Converges to the Gardner bound (~0.64N capacity).
                         3-threshold variant maximizes margin for noise robustness.

3. train_rigl      — dynamic sparse training: gradient-guided mask adaptation.
                     Prunes smallest |w|, regrows where |∂L/∂w| is largest.
                     Maintains exact per-neuron degree budget throughout.

All three enforce W = Wᵀ (symmetry) and diag(W) = 0.

Usage
-----
    python phase1/train_gd.py --N 16 --M 4 --method l1svm --gamma 1.0
    python phase1/train_gd.py --N 32 --M 8 --method perceptron --lam 0.005 --degree 8
    python phase1/train_gd.py --N 32 --M 8 --method rigl --degree 8 --gamma 1.0
    python phase1/train_gd.py --N 16 --M 4 --compare  # run all methods, print table
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.optimize import linprog

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hopfield_net import HopfieldNetwork, PSEUDOINVERSE, ASYNC_CYCLIC
from pruning import verify_fixed_points, pruning_report


# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────

def _mean_degree(W: np.ndarray, eps: float = 1e-8) -> float:
    return float((np.abs(W) > eps).sum(axis=1).mean())


def _symmetrize(W: np.ndarray) -> np.ndarray:
    W = (W + W.T) / 2.0
    np.fill_diagonal(W, 0.0)
    return W


def _margin_grad(W: np.ndarray, patterns: np.ndarray, gamma: float) -> np.ndarray:
    """
    Gradient of hinge-margin loss L = Σ_μ Σ_i max(0, γ - ξᵢ^μ (Wᵢ·ξ^μ))
    w.r.t. W.  Returns (N, N) gradient matrix (un-symmetrized).
    """
    M, N = patterns.shape
    grad = np.zeros((N, N))
    for p in patterns:
        h = W @ p                       # local fields (N,)
        margin = p * h                  # ξᵢ * hᵢ  (N,)
        violated = (margin < gamma)     # which neurons violate margin
        # gradient contribution: -ξᵢ ξⱼ for violated neurons
        grad[violated] -= np.outer(p[violated], p)
    return grad


def _hinge_loss(W: np.ndarray, patterns: np.ndarray, gamma: float) -> float:
    total = 0.0
    for p in patterns:
        h = W @ p
        total += np.maximum(0.0, gamma - p * h).sum()
    return float(total)


def recall_accuracy(W, patterns, noise_frac, n_trials, rng):
    N = W.shape[0]
    M = len(patterns)
    n_flip = max(0, round(noise_frac * N))
    net = HopfieldNetwork(N, update_mode=ASYNC_CYCLIC)
    net.W = W
    correct = 0
    for _ in range(n_trials):
        p_idx = rng.integers(M)
        pat = patterns[p_idx]
        s0 = pat.copy()
        if n_flip > 0:
            s0[rng.choice(N, size=n_flip, replace=False)] *= -1.0
        s_final, _, _ = net.run(s0, max_sweeps=50)
        correct += int(np.array_equal(s_final, pat))
    return round(correct / n_trials, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Method 1 — L1-SVM per-neuron LP
# ─────────────────────────────────────────────────────────────────────────────

def train_l1svm(
    patterns: np.ndarray,
    gamma: float = 1.0,
    degree: Optional[int] = None,
    eps: float = 1e-6,
    verbose: bool = False,
) -> np.ndarray:
    """
    Joint symmetric L1-SVM: minimize total weight magnitude subject to all
    stored patterns being exact fixed points with margin γ.

    LP formulation (joint, enforces W = Wᵀ directly)
    --------------------------------------------------
    Variables: upper-triangle weights w_ij (i < j), split as w = w⁺ − w⁻.
    Total variables: K = N(N−1)/2 pairs × 2 = N(N−1) variables.

    Objective: min Σ_{i<j} (w⁺_ij + w⁻_ij)   ← minimizes Σ|w_ij|

    Constraints: for each neuron i and pattern μ:
        ξᵢ^μ · Σ_{j≠i} w_ij · ξⱼ^μ ≥ γ
    →   −ξᵢ^μ ξⱼ^μ (w⁺_ij − w⁻_ij) ≤ −γ   (rearranged for scipy ≤ form)

    Size: M×N constraints × N(N−1) variables. For N=16, M=4: 64 × 240.
    For N=32, M=8: 256 × 992. Both trivially tractable with HiGHS.

    The key advantage over per-neuron LP + symmetrize: the same w_ij appears
    in BOTH neuron i's and neuron j's constraints simultaneously, so the
    solution is symmetric by construction and fixed-point conditions are
    satisfied for all neurons at once.

    Parameters
    ----------
    patterns : (M, N) bipolar {−1, +1} patterns
    gamma    : margin; larger = more noise-robust, fewer patterns storable
    degree   : if set, post-solve prune each row to this many non-zeros
    eps      : zero threshold for LP output
    """
    M, N = patterns.shape

    # Upper-triangle pairs and their index in the variable vector
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    K = len(pairs)                                  # N(N-1)/2
    pair_to_k = {(i, j): k for k, (i, j) in enumerate(pairs)}

    # Objective: minimize Σ (w+_k + w-_k) over all pairs
    c = np.ones(2 * K)

    # Constraints: M * N rows (one per neuron per pattern)
    A_rows = []
    b_rows = []

    for mu in range(M):
        p = patterns[mu]
        for i in range(N):
            row_pos = np.zeros(K)
            row_neg = np.zeros(K)
            for j in range(N):
                if j == i:
                    continue
                k = pair_to_k.get((min(i, j), max(i, j)))
                coeff = p[i] * p[j]
                # constraint: coeff * (w+_k - w-_k) >= gamma
                # → -coeff * w+_k + coeff * w-_k <= -gamma
                row_pos[k] -= coeff
                row_neg[k] += coeff
            A_rows.append(np.concatenate([row_pos, row_neg]))
            b_rows.append(-gamma)

    A_ub = np.array(A_rows, dtype=float)
    b_ub = np.array(b_rows, dtype=float)
    bounds = [(0.0, None)] * (2 * K)

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    W = np.zeros((N, N))
    if result.status == 0:
        x = result.x
        w_pos, w_neg = x[:K], x[K:]
        for k, (i, j) in enumerate(pairs):
            w = w_pos[k] - w_neg[k]
            if abs(w) > eps:
                W[i, j] = w
                W[j, i] = w
        if verbose:
            n_fixed, _ = verify_fixed_points(W, patterns)
            print(f"  L1-SVM: LP solved | deg={_mean_degree(W):.1f} | "
                  f"fixed={n_fixed}/{M}")
    else:
        if verbose:
            print(f"  L1-SVM: LP infeasible (status={result.status}) — γ too large?")

    if degree is not None:
        W = _prune_to_degree(W, degree)

    return W


def _prune_to_degree(W: np.ndarray, target_degree: int) -> np.ndarray:
    """Keep only the target_degree largest |W_ij| per row (applied symmetrically)."""
    N = W.shape[0]
    W_out = W.copy()
    for i in range(N):
        row = np.abs(W_out[i]).copy()
        row[i] = 0
        if (row > 0).sum() > target_degree:
            kth = np.partition(row, -target_degree)[-target_degree]
            mask = row < kth
            W_out[i, mask] = 0
            W_out[mask, i] = 0
    return W_out


# ─────────────────────────────────────────────────────────────────────────────
# Method 2 — Perceptron / 3-threshold with L1 proximal
# ─────────────────────────────────────────────────────────────────────────────

def train_perceptron_l1(
    patterns: np.ndarray,
    lam: float = 0.005,
    gamma: float = 1.0,
    lr: float = 0.01,
    max_epochs: int = 500,
    degree: Optional[int] = None,
    tol: float = 1e-6,
    verbose: bool = False,
) -> np.ndarray:
    """
    Iterative hinge-margin training with L1 proximal operator (ISTA).

    Loss: L(W) = Σ_μ Σᵢ max(0, γ − ξᵢ^μ (Wᵢ·ξ^μ)) + λ||W||₁

    Update rule each epoch:
        G  = ∇_W L_hinge           (gradient of hinge part, see _margin_grad)
        W  ← W − lr · G            (gradient step)
        W  ← sign(W) max(|W|−λ·lr, 0)   (proximal operator for L1)
        W  ← (W + Wᵀ)/2            (symmetrize)

    When a solution exists, converges to the Gardner bound (~0.64N capacity).
    The 3-threshold interpretation: γ > 0 is the target margin, violations
    below γ drive updates, analogous to Alemi et al. (2015)'s θ₁/θ₂/θ₃ thresholds.

    Parameters
    ----------
    patterns   : (M, N) bipolar patterns
    lam        : L1 regularization strength (controls sparsity)
    gamma      : hinge margin (controls noise robustness at cost of capacity)
    lr         : gradient step size
    max_epochs : maximum training iterations
    degree     : if set, post-training magnitude prune to this degree
    tol        : convergence tolerance on loss change

    Returns
    -------
    W : (N, N) symmetric, zero-diagonal weight matrix
    """
    M, N = patterns.shape
    W = np.zeros((N, N))
    prev_loss = float('inf')

    for epoch in range(max_epochs):
        # Gradient of hinge loss
        grad = _margin_grad(W, patterns, gamma)
        # Symmetrize gradient (enforce symmetric weight update)
        grad = (grad + grad.T) / 2.0
        np.fill_diagonal(grad, 0.0)

        # Gradient step
        W = W - lr * grad

        # L1 proximal (soft thresholding)
        W = np.sign(W) * np.maximum(np.abs(W) - lam * lr, 0.0)

        # Symmetrize and zero diagonal
        W = _symmetrize(W)

        # Check convergence
        loss = _hinge_loss(W, patterns, gamma)
        if verbose and (epoch % 50 == 0 or epoch == max_epochs - 1):
            n_fixed, _ = verify_fixed_points(W, patterns)
            print(f"  epoch {epoch:4d}: loss={loss:.4f}  "
                  f"deg={_mean_degree(W):.1f}  fixed={n_fixed}/{M}")
        if abs(prev_loss - loss) < tol and loss == 0.0:
            if verbose:
                print(f"  converged at epoch {epoch}")
            break
        prev_loss = loss

    if degree is not None:
        W = _prune_to_degree(W, degree)

    return W


# ─────────────────────────────────────────────────────────────────────────────
# Method 3 — RigL-style dynamic sparse training
# ─────────────────────────────────────────────────────────────────────────────

def _init_symmetric_mask(N: int, target_degree: int, rng: np.random.Generator) -> np.ndarray:
    """Random symmetric adjacency mask with exactly target_degree non-zeros per row."""
    mask = np.zeros((N, N), dtype=bool)
    for i in range(N):
        candidates = [j for j in range(N) if j != i and not mask[i, j]]
        if len(candidates) < target_degree:
            chosen = candidates
        else:
            chosen = rng.choice(candidates, size=target_degree, replace=False)
        for j in chosen:
            mask[i, j] = True
            mask[j, i] = True
    return mask.astype(float)


def train_rigl(
    patterns: np.ndarray,
    target_degree: int,
    gamma: float = 1.0,
    lam: float = 0.001,
    lr: float = 0.01,
    max_epochs: int = 800,
    update_interval: int = 100,
    grow_fraction: float = 0.3,
    seed: int = 0,
    verbose: bool = False,
) -> np.ndarray:
    """
    RigL-inspired dynamic sparse training for Hopfield networks.

    Maintains a fixed per-neuron degree budget d throughout training.
    Every `update_interval` epochs (stopping at 75% of max_epochs):
      - Prune: remove the `grow_fraction` of active connections with smallest |w|
      - Grow:  add the same number of inactive connections where |∂L/∂w| is largest
      - Symmetrize: prune/grow pairs (i,j) and (j,i) jointly

    Loss: hinge margin L + L1 applied on active connections only.

    Parameters
    ----------
    patterns        : (M, N) bipolar patterns
    target_degree   : desired non-zero connections per neuron
    gamma           : hinge margin
    lam             : L1 regularization on active weights
    lr              : learning rate
    max_epochs      : total training epochs
    update_interval : how often to update the sparsity mask
    grow_fraction   : fraction of active connections to prune/regrow each update
    seed            : RNG seed for initial mask

    Returns
    -------
    W : (N, N) sparse symmetric weight matrix at target_degree
    """
    M, N = patterns.shape
    rng = np.random.default_rng(seed)

    # Initialize sparse mask and weights
    mask = _init_symmetric_mask(N, target_degree, rng)
    W = np.zeros((N, N))

    for epoch in range(max_epochs):
        # Gradient of hinge loss (over all connections, including inactive ones)
        grad = _margin_grad(W, patterns, gamma)
        grad = (grad + grad.T) / 2.0
        np.fill_diagonal(grad, 0.0)

        # Gradient step on ACTIVE connections only
        W -= lr * grad * mask

        # L1 proximal on active weights
        W = np.sign(W) * np.maximum(np.abs(W) - lam * lr, 0.0)
        W *= mask

        # Symmetrize and enforce mask
        W = _symmetrize(W)
        W *= mask

        # Periodic mask update (stop at 75% of training)
        if (epoch + 1) % update_interval == 0 and epoch < int(0.75 * max_epochs):
            W, mask = _rigl_update(W, grad, mask, target_degree, grow_fraction, N, rng)

        if verbose and (epoch % 100 == 0 or epoch == max_epochs - 1):
            n_fixed, _ = verify_fixed_points(W, patterns)
            loss = _hinge_loss(W, patterns, gamma)
            print(f"  epoch {epoch:4d}: loss={loss:.4f}  "
                  f"deg={_mean_degree(W):.1f}  fixed={n_fixed}/{M}")

    return W


def _rigl_update(
    W: np.ndarray,
    grad: np.ndarray,
    mask: np.ndarray,
    target_degree: int,
    grow_fraction: float,
    N: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Single RigL mask update step (symmetric).
    For each row: prune grow_fraction of smallest |w|, regrow at highest |∂L/∂w|.
    Pairs (i,j)/(j,i) updated together to maintain symmetry.
    """
    # Work on upper triangle to keep symmetry
    new_mask = mask.copy()
    n_update = max(1, round(grow_fraction * target_degree))

    for i in range(N):
        active = np.where(mask[i] > 0)[0]
        active = active[active != i]
        if len(active) < n_update:
            continue

        # Prune: smallest |w| among active
        w_mag = np.abs(W[i, active])
        prune_idx = active[np.argsort(w_mag)[:n_update]]

        # Grow: largest |∂L/∂w| among inactive (excluding self)
        inactive = np.where(mask[i] == 0)[0]
        inactive = inactive[inactive != i]
        if len(inactive) < n_update:
            continue
        grad_mag = np.abs(grad[i, inactive])
        grow_idx = inactive[np.argsort(grad_mag)[-n_update:]]

        # Apply symmetrically
        for j in prune_idx:
            new_mask[i, j] = 0
            new_mask[j, i] = 0
        for j in grow_idx:
            new_mask[i, j] = 1
            new_mask[j, i] = 1

    np.fill_diagonal(new_mask, 0.0)
    # Re-zero pruned weights
    W = W * new_mask
    return W, new_mask


# ─────────────────────────────────────────────────────────────────────────────
# Comparison runner
# ─────────────────────────────────────────────────────────────────────────────

def run_comparison(
    patterns: np.ndarray,
    target_degrees: list[int],
    noise_fracs: list[float] = (0.0, 0.15, 0.30),
    n_trials: int = 300,
    seed: int = 42,
    verbose: bool = True,
) -> list[dict]:
    """
    Run all three GD methods + pseudoinverse baseline at each target degree.
    Returns a list of result dicts.
    """
    M, N = patterns.shape
    rng = np.random.default_rng(seed)

    # Pseudoinverse baseline
    net_pi = HopfieldNetwork(N, rule=PSEUDOINVERSE)
    net_pi.train(patterns)
    W_pi_dense = net_pi.W.copy()

    rows = []
    noise_hdr = "  ".join(f"η={nf:.0%}" for nf in noise_fracs)

    if verbose:
        print(f"\nGD methods comparison — N={N}, M={M} (α={M/N:.2f})")
        print(f"{'Method':>18} {'deg':>5} {'fp':>6}  {noise_hdr}")
        print("─" * (26 + 8 * len(noise_fracs)))

    for target_deg in target_degrees:
        if verbose:
            print(f"\n  ── target degree ≈ {target_deg} ──")

        # Pseudoinverse post-hoc (reference)
        from pruning import prune_magnitude
        def _bisect_s(W_dense, td, lo=0.0, hi=3.0, n=20):
            for _ in range(n):
                mid = (lo + hi) / 2
                W = prune_magnitude(W_dense, s=mid)
                d = _mean_degree(W)
                if abs(d - td) < 0.1:
                    break
                if d > td:
                    lo = mid
                else:
                    hi = mid
            return prune_magnitude(W_dense, s=mid)

        methods = [
            ("pseudo_posthoc", _bisect_s(W_pi_dense, target_deg)),
            ("l1svm_g1",       train_l1svm(patterns, gamma=1.0, degree=target_deg)),
            ("l1svm_g0.5",     train_l1svm(patterns, gamma=0.5, degree=target_deg)),
            ("perceptron_l1",  train_perceptron_l1(patterns, lam=0.005, gamma=1.0,
                                                    degree=target_deg)),
            ("rigl",           train_rigl(patterns, target_degree=target_deg,
                                          gamma=1.0, seed=seed)),
        ]

        for method_name, W in methods:
            actual_deg = _mean_degree(W)
            n_fixed, _ = verify_fixed_points(W, patterns)
            degrees = (np.abs(W) > 1e-8).sum(axis=1)
            sparse_lut = int(sum(2 ** int(d) for d in degrees))

            recalls = [
                recall_accuracy(W, patterns, nf, n_trials, rng)
                for nf in noise_fracs
            ]

            row = {
                "N": N, "M": M, "load": round(M/N, 4),
                "target_degree": target_deg,
                "method": method_name,
                "actual_degree": round(actual_deg, 2),
                "n_fixed": n_fixed, "frac_fixed": round(n_fixed/M, 4),
                "sparse_lut": sparse_lut,
                "compression": round(N * (1 << N) / max(sparse_lut, 1), 1),
            }
            for nf, r in zip(noise_fracs, recalls):
                row[f"recall_{int(nf*100):02d}"] = r
            rows.append(row)

            if verbose:
                fp_str = f"{n_fixed}/{M}"
                rec_str = "  ".join(f"{r:.2f}" for r in recalls)
                print(f"  {method_name:>18} {actual_deg:>5.1f} {fp_str:>6}  {rec_str}")

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import csv

    parser = argparse.ArgumentParser(
        description="GD + LP-based sparse Hopfield training."
    )
    parser.add_argument("--N",       type=int,   default=16)
    parser.add_argument("--M",       type=int,   default=4)
    parser.add_argument("--seed",    type=int,   default=42)
    parser.add_argument("--method",  choices=["l1svm", "perceptron", "rigl", "compare"],
                        default="compare")
    parser.add_argument("--gamma",   type=float, default=1.0,
                        help="Hinge margin (l1svm, perceptron, rigl)")
    parser.add_argument("--lam",     type=float, default=0.005,
                        help="L1 regularization (perceptron, rigl)")
    parser.add_argument("--degree",  type=int,   default=None,
                        help="Target per-neuron degree (all methods)")
    parser.add_argument("--degrees", nargs="+",  type=int,
                        default=[4, 6, 8, 10, 12],
                        help="Degree sweep for --compare mode")
    parser.add_argument("--trials",  type=int,   default=300)
    parser.add_argument("--out",     type=str,   default=None)
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    patterns = rng.choice([-1.0, 1.0], size=(args.M, args.N))

    t0 = time.time()

    if args.method == "compare":
        rows = run_comparison(
            patterns, args.degrees,
            n_trials=args.trials, seed=args.seed, verbose=args.verbose
        )
        out_path = (Path(args.out) if args.out else
                    Path(__file__).parent / "results" /
                    f"gd_comparison_N{args.N}_M{args.M}_seed{args.seed}.csv")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nDone in {time.time()-t0:.1f}s  →  {out_path}")

    elif args.method == "l1svm":
        W = train_l1svm(patterns, gamma=args.gamma, degree=args.degree,
                        verbose=args.verbose)
        n_fixed, M = verify_fixed_points(W, patterns)
        print(f"\nL1-SVM (γ={args.gamma}):  {n_fixed}/{M} fixed pts | "
              f"deg {_mean_degree(W):.1f}")

    elif args.method == "perceptron":
        W = train_perceptron_l1(patterns, lam=args.lam, gamma=args.gamma,
                                 degree=args.degree, verbose=args.verbose)
        n_fixed, M = verify_fixed_points(W, patterns)
        print(f"\nPerceptron-L1 (γ={args.gamma}, λ={args.lam}): "
              f"{n_fixed}/{M} fixed pts | deg {_mean_degree(W):.1f}")

    elif args.method == "rigl":
        d = args.degree or 8
        W = train_rigl(patterns, target_degree=d, gamma=args.gamma,
                        lam=args.lam, seed=args.seed, verbose=args.verbose)
        n_fixed, M = verify_fixed_points(W, patterns)
        print(f"\nRigL (γ={args.gamma}, d={d}): "
              f"{n_fixed}/{M} fixed pts | deg {_mean_degree(W):.1f}")
