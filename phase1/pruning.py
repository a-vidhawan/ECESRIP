"""
pruning.py
==========
Weight pruning for all three Hopfield learning rules.

Three strategies, matched to each rule:

  Hebbian        → post-hoc magnitude pruning only (rule is closed-form, no retraining)
  Storkey        → L1 proximal during training (shrinks weights while learning)
  Pseudoinverse  → post-hoc magnitude pruning + iterative verify-and-prune
                   (robust enough that post-hoc works well; iterative tightens further)

All pruners return a pruned W and a report dict.

Usage
-----
    from phase1.pruning import prune_magnitude, train_storkey_l1, prune_pseudoinverse
    from phase1.pruning import pruning_report, verify_fixed_points
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
from hopfield_net import HopfieldNetwork, HEBBIAN, STORKEY, PSEUDOINVERSE, ASYNC_CYCLIC


# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────

def verify_fixed_points(W: np.ndarray, patterns: np.ndarray) -> tuple[int, int]:
    """Return (n_fixed, M): how many stored patterns are still exact fixed points."""
    M, N = patterns.shape
    n_fixed = 0
    for p in patterns:
        if all(
            (1.0 if float(W[i] @ p) >= 0 else -1.0) == p[i]
            for i in range(N)
        ):
            n_fixed += 1
    return n_fixed, M


def pruning_report(W_dense: np.ndarray, W_pruned: np.ndarray,
                   patterns: np.ndarray, eps: float = 1e-8) -> dict:
    """
    Compare dense and pruned weight matrices.

    Returns a dict with:
        n_fixed / M         — fixed points preserved
        pct_zeroed          — fraction of off-diagonal weights set to zero
        mean_degree         — avg non-zero connections per neuron after pruning
        max_degree          — max non-zero connections per neuron
        sparse_lut_entries  — Σᵢ 2^dᵢ (total LUT entries across all neurons)
        dense_lut_entries   — N × 2^N
        compression_ratio   — dense / sparse
    """
    N = W_dense.shape[0]
    n_fixed, M = verify_fixed_points(W_pruned, patterns)

    degrees = (np.abs(W_pruned) > eps).sum(axis=1).astype(int)
    sparse_lut = int(sum(2 ** int(d) for d in degrees))
    dense_lut = N * (1 << N)

    off_dense  = np.abs(W_dense[np.triu_indices(N, k=1)])
    off_pruned = np.abs(W_pruned[np.triu_indices(N, k=1)])
    pct_zeroed = float((off_pruned == 0).mean() - (off_dense == 0).mean())

    return {
        "n_fixed": n_fixed,
        "M": M,
        "fixed_pts_kept": f"{n_fixed}/{M}",
        "pct_zeroed": round(pct_zeroed * 100, 1),
        "mean_degree": round(float(degrees.mean()), 1),
        "max_degree": int(degrees.max()),
        "sparse_lut_entries": sparse_lut,
        "dense_lut_entries": dense_lut,
        "compression_ratio": round(dense_lut / max(sparse_lut, 1), 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Method 1 — Hebbian: post-hoc magnitude pruning
# ─────────────────────────────────────────────────────────────────────────────

def prune_magnitude(
    W: np.ndarray,
    s: float = 0.25,
    eps: float = 1e-8,
) -> np.ndarray:
    """
    Post-hoc magnitude pruning: zero out |W_ij| < s × std(W).

    Works for any weight matrix. The only pruning method available
    for Hebbian (closed-form rule, no retraining possible).

    Parameters
    ----------
    W : (N, N) weight matrix
    s : threshold multiplier (fraction of std to use as cutoff)
        Typical values: 0.1 (light), 0.25 (moderate), 0.5 (aggressive)

    Returns
    -------
    W_pruned : (N, N) with small weights zeroed, diagonal forced to zero
    """
    off = W[np.triu_indices(W.shape[0], k=1)]
    threshold = s * float(np.std(off[np.abs(off) > eps]))
    W_pruned = W.copy()
    W_pruned[np.abs(W_pruned) < threshold] = 0.0
    np.fill_diagonal(W_pruned, 0.0)
    return W_pruned


def prune_hebbian(
    patterns: np.ndarray,
    s: float = 0.25,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Train with Hebbian rule then apply magnitude pruning.

    Returns
    -------
    W_dense  : trained weight matrix before pruning
    W_pruned : weight matrix after pruning
    report   : pruning_report dict
    """
    M, N = patterns.shape
    net = HopfieldNetwork(N, rule=HEBBIAN)
    net.train(patterns)
    W_dense = net.W.copy()
    W_pruned = prune_magnitude(W_dense, s=s)
    report = pruning_report(W_dense, W_pruned, patterns)
    return W_dense, W_pruned, report


# ─────────────────────────────────────────────────────────────────────────────
# Method 2 — Storkey: L1 proximal during training
# ─────────────────────────────────────────────────────────────────────────────

def train_storkey_l1(
    patterns: np.ndarray,
    lam: float = 0.05,
    post_s: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Storkey learning with L1 soft-thresholding after each pattern.

    After presenting each pattern, small weights are shrunk toward zero:
        W_ij ← sign(W_ij) × max(|W_ij| - lam/N, 0)

    This is ISTA (iterative shrinkage-thresholding) applied to Storkey,
    enforcing sparsity during learning rather than after.

    Parameters
    ----------
    patterns : (M, N) bipolar patterns
    lam      : L1 penalty strength. Start at 0.01 and increase until
               fixed point loss becomes unacceptable.
    post_s   : optional additional post-hoc magnitude pruning (s multiplier)
               applied after L1 training. Set 0 to skip.

    Returns
    -------
    W_dense  : Storkey weights WITHOUT L1 (for comparison)
    W_pruned : Storkey weights WITH L1 (and optional post-hoc pruning)
    report   : pruning_report dict
    """
    M, N = patterns.shape

    # Dense baseline
    net_dense = HopfieldNetwork(N, rule=STORKEY)
    net_dense.train(patterns)
    W_dense = net_dense.W.copy()

    # L1 Storkey
    W = np.zeros((N, N))
    for p in patterns:
        h = W @ p
        W += (np.outer(p, p) - np.outer(h, p) - np.outer(p, h)) / N
        np.fill_diagonal(W, 0)
        # Proximal operator (soft thresholding)
        threshold = lam / N
        W = np.sign(W) * np.maximum(np.abs(W) - threshold, 0)
        np.fill_diagonal(W, 0)

    W_pruned = W.copy()
    if post_s > 0:
        W_pruned = prune_magnitude(W_pruned, s=post_s)

    report = pruning_report(W_dense, W_pruned, patterns)
    return W_dense, W_pruned, report


# ─────────────────────────────────────────────────────────────────────────────
# Method 3 — Pseudoinverse: post-hoc + iterative verify-and-prune
# ─────────────────────────────────────────────────────────────────────────────

def prune_pseudoinverse(
    patterns: np.ndarray,
    s: float = 0.5,
    target_degree: Optional[int] = None,
    max_iter: int = 10,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Pseudoinverse training with iterative verify-and-prune.

    Strategy:
      1. Train with pseudoinverse (all patterns are exact fixed points)
      2. Apply magnitude pruning at threshold s × std
      3. Verify fixed points; if any lost, tighten threshold (s *= 0.8)
      4. Repeat until fixed points preserved or max_iter reached

    Pseudoinverse is the most pruning-tolerant rule because it minimises
    the weight magnitudes needed to keep patterns as fixed points.
    Starting at s=0.5 is safe: typically preserves all patterns.

    Parameters
    ----------
    patterns     : (M, N) bipolar patterns
    s            : initial magnitude threshold multiplier
    target_degree: if set, also prune to this max connections per neuron
    max_iter     : max refinement steps

    Returns
    -------
    W_dense  : pseudoinverse weights before pruning
    W_pruned : pruned weights
    report   : pruning_report dict
    """
    M, N = patterns.shape
    net = HopfieldNetwork(N, rule=PSEUDOINVERSE)
    net.train(patterns)
    W_dense = net.W.copy()

    W_pruned = W_dense.copy()
    current_s = s

    for it in range(max_iter):
        W_candidate = prune_magnitude(W_dense, s=current_s)

        if target_degree is not None:
            W_candidate = _prune_to_degree(W_candidate, target_degree)

        n_fixed, _ = verify_fixed_points(W_candidate, patterns)
        if n_fixed == M:
            W_pruned = W_candidate
            break
        # Back off: reduce threshold and try again
        current_s *= 0.8
    else:
        # Settle for best found
        W_pruned = W_candidate

    report = pruning_report(W_dense, W_pruned, patterns)
    report["final_s"] = round(current_s, 4)
    report["iterations"] = it + 1
    return W_dense, W_pruned, report


def _prune_to_degree(W: np.ndarray, target_degree: int) -> np.ndarray:
    """Keep only the target_degree largest |W_ij| per row (symmetric)."""
    N = W.shape[0]
    W_out = W.copy()
    for i in range(N):
        row = np.abs(W_out[i]).copy()
        row[i] = 0
        if (row > 0).sum() > target_degree:
            kth = np.partition(row, -target_degree)[-target_degree]
            mask = (row < kth) & (row > 0)
            W_out[i, mask] = 0
            W_out[mask, i] = 0
    return W_out


# ─────────────────────────────────────────────────────────────────────────────
# Sweep: threshold vs accuracy (for plotting)
# ─────────────────────────────────────────────────────────────────────────────

def sweep_pruning_threshold(
    patterns: np.ndarray,
    s_values: list[float] = None,
    rules: list[str] = None,
) -> list[dict]:
    """
    Sweep pruning threshold s and record fixed point survival for all rules.

    Returns a list of dicts suitable for direct plotting / CSV export.
    """
    if s_values is None:
        s_values = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0]
    if rules is None:
        rules = ['hebbian', 'storkey', 'pseudoinverse']

    M, N = patterns.shape
    rows = []

    for rule_name in rules:
        rule = {'hebbian': HEBBIAN, 'storkey': STORKEY, 'pseudoinverse': PSEUDOINVERSE}[rule_name]
        net = HopfieldNetwork(N, rule=rule)
        net.train(patterns)
        W_dense = net.W.copy()
        off = W_dense[np.triu_indices(N, k=1)]
        std = float(np.std(off[np.abs(off) > 1e-8]))

        for s in s_values:
            threshold = s * std
            W_pruned = W_dense.copy()
            W_pruned[np.abs(W_pruned) < threshold] = 0.0
            np.fill_diagonal(W_pruned, 0.0)

            n_fixed, _ = verify_fixed_points(W_pruned, patterns)
            degrees = (np.abs(W_pruned) > 1e-8).sum(axis=1)
            sparse_lut = int(sum(2 ** int(d) for d in degrees))

            rows.append({
                "rule": rule_name,
                "s": s,
                "threshold": round(threshold, 6),
                "n_fixed": n_fixed,
                "M": M,
                "frac_fixed": round(n_fixed / M, 4),
                "pct_zeroed": round(float((np.abs(W_pruned) < 1e-8).mean() * 100 -
                                          (np.abs(W_dense) < 1e-8).mean() * 100), 1),
                "mean_degree": round(float(degrees.mean()), 2),
                "sparse_lut_entries": sparse_lut,
                "compression_ratio": round(N * (1 << N) / max(sparse_lut, 1), 1),
            })

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CLI — quick demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prune Hopfield weights, all 3 rules.")
    parser.add_argument("--N",   type=int, default=16)
    parser.add_argument("--M",   type=int, default=4)
    parser.add_argument("--s",   type=float, default=0.5, help="Magnitude threshold multiplier")
    parser.add_argument("--lam", type=float, default=0.05, help="L1 lambda for Storkey")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sweep", action="store_true", help="Run full threshold sweep")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    patterns = rng.choice([-1.0, 1.0], size=(args.M, args.N))

    if args.sweep:
        print(f"Threshold sweep — N={args.N}, M={args.M}\n")
        rows = sweep_pruning_threshold(patterns)
        print(f"{'Rule':>13} {'s':>5} {'fixed':>7} {'%zeroed':>8} {'deg':>5} {'compress':>9}")
        print("-" * 55)
        for r in rows:
            print(f"{r['rule']:>13} {r['s']:>5.2f} "
                  f"{r['n_fixed']}/{r['M']:>2}  "
                  f"{r['pct_zeroed']:>7.1f}%  "
                  f"{r['mean_degree']:>5.1f}  "
                  f"{r['compression_ratio']:>8.0f}×")
    else:
        print(f"\nPruning demo — N={args.N}, M={args.M}, s={args.s}, lam={args.lam}\n")

        _, Wh, rh = prune_hebbian(patterns, s=args.s)
        print(f"Hebbian + magnitude(s={args.s}):  "
              f"{rh['fixed_pts_kept']} fixed pts | "
              f"{rh['pct_zeroed']:.1f}% zeroed | "
              f"deg {rh['mean_degree']:.1f} | "
              f"{rh['compression_ratio']:.0f}× compression")

        _, Ws, rs = train_storkey_l1(patterns, lam=args.lam)
        print(f"Storkey + L1(lam={args.lam}):     "
              f"{rs['fixed_pts_kept']} fixed pts | "
              f"{rs['pct_zeroed']:.1f}% zeroed | "
              f"deg {rs['mean_degree']:.1f} | "
              f"{rs['compression_ratio']:.0f}× compression")

        _, Wp, rp = prune_pseudoinverse(patterns, s=args.s)
        print(f"Pseudoinverse + prune(s={args.s}): "
              f"{rp['fixed_pts_kept']} fixed pts | "
              f"{rp['pct_zeroed']:.1f}% zeroed | "
              f"deg {rp['mean_degree']:.1f} | "
              f"{rp['compression_ratio']:.0f}× compression")
