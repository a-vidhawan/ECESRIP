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
    """Keep only the target_degree largest |W_ij| per row (symmetric).

    Ties must be broken explicitly. A threshold test of the form
    ``row < kth`` keeps every entry whose magnitude equals the k-th largest,
    so when a row is entirely tied it prunes nothing and the cap silently
    no-ops. That is the common case, not a corner case: a pseudoinverse W
    built from M bipolar patterns is rank-M, and for small M the off-diagonal
    magnitudes collapse onto a single value -- e.g. N=512, M=4 leaves rows of
    71 identical magnitudes, so a requested degree of 12 returned 71.

    Ranking with argsort takes exactly target_degree entries regardless of
    ties, using index order as the deterministic tie-break.
    """
    N = W.shape[0]
    keep = np.zeros(W.shape, dtype=bool)
    for i in range(N):
        row = np.abs(W[i]).copy()
        row[i] = 0.0
        nz = np.nonzero(row)[0]
        if nz.size <= target_degree:
            keep[i, nz] = True
            continue
        order = nz[np.argsort(-row[nz], kind="stable")]
        keep[i, order[:target_degree]] = True
    # An edge survives only if BOTH endpoints kept it, matching the original
    # symmetric-removal semantics and guaranteeing degree <= target_degree.
    keep &= keep.T
    return np.where(keep, W, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Method 2b — Storkey: prune-then-retrain (mask-constrained Storkey)
# ─────────────────────────────────────────────────────────────────────────────

def retrain_storkey_masked(
    patterns: np.ndarray,
    W_sparse: np.ndarray,
) -> np.ndarray:
    """
    Re-run the Storkey rule but hard-zero masked connections after every step.

    Given a sparsity pattern (from any pruning method), this finds the best
    Storkey weights that fit within that connectivity pattern. The mask is
    fixed throughout; only non-zero entries in W_sparse are allowed to grow.

    Parameters
    ----------
    patterns : (M, N) bipolar patterns
    W_sparse : weight matrix whose non-zero positions define the allowed mask

    Returns
    -------
    W_retrained : (N, N) Storkey weights constrained to the mask
    """
    M, N = patterns.shape
    mask = (np.abs(W_sparse) > 1e-8).astype(float)
    np.fill_diagonal(mask, 0.0)

    W = np.zeros((N, N))
    for p in patterns:
        h = W @ p
        W += (np.outer(p, p) - np.outer(h, p) - np.outer(p, h)) / N
        np.fill_diagonal(W, 0.0)
        W *= mask  # enforce sparsity pattern every step
    return W


def prune_storkey_retrain(
    patterns: np.ndarray,
    s: float = 0.75,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Storkey post-hoc prune → masked retrain.

    Steps:
      1. Train dense Storkey
      2. Prune with magnitude threshold s to get sparsity mask
      3. Re-run Storkey constrained to that mask (retrain_storkey_masked)
      4. Verify fixed points

    This usually recovers fixed points that post-hoc pruning loses, because
    the remaining weights can redistribute to compensate for the removed ones.

    Parameters
    ----------
    patterns : (M, N) bipolar patterns
    s        : magnitude threshold multiplier for the initial prune
    """
    M, N = patterns.shape
    net = HopfieldNetwork(N, rule=STORKEY)
    net.train(patterns)
    W_dense = net.W.copy()

    W_mask = prune_magnitude(W_dense, s=s)
    W_retrained = retrain_storkey_masked(patterns, W_mask)

    report = pruning_report(W_dense, W_retrained, patterns)
    return W_dense, W_retrained, report


# ─────────────────────────────────────────────────────────────────────────────
# Method 3b — Pseudoinverse: masked constrained least-squares retrain
# ─────────────────────────────────────────────────────────────────────────────

def retrain_pseudoinverse_masked(
    patterns: np.ndarray,
    W_sparse: np.ndarray,
) -> np.ndarray:
    """
    Constrained pseudoinverse: for each neuron i, solve a masked least-squares
    problem using only the connections allowed by W_sparse's non-zero pattern.

    For neuron i with allowed neighbors S_i = {j : W_sparse[i,j] != 0}:
        w_i* = argmin ||w||² s.t. P[:, S_i] w ≈ P[:, i]

    This is just np.linalg.lstsq applied per-row with a column mask.
    The result is then symmetrized: W = (W + W^T) / 2.

    This is the most principled sparse method: it finds the minimum-norm
    weights on the allowed connections that best satisfy the fixed-point
    equations — the true sparse pseudoinverse.

    Parameters
    ----------
    patterns : (M, N) bipolar patterns
    W_sparse : weight matrix whose non-zero positions define the allowed mask

    Returns
    -------
    W_retrained : (N, N) symmetric, zero-diagonal weight matrix
    """
    M, N = patterns.shape
    mask = (np.abs(W_sparse) > 1e-8).astype(float)
    np.fill_diagonal(mask, 0.0)

    W_new = np.zeros((N, N))
    for i in range(N):
        S_i = np.where(mask[i] > 0)[0]
        if len(S_i) == 0:
            continue
        A = patterns[:, S_i]   # (M, |S_i|)
        b = patterns[:, i]     # (M,)
        w_i, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        W_new[i, S_i] = w_i

    # Symmetrize and zero diagonal
    W_new = (W_new + W_new.T) / 2.0
    np.fill_diagonal(W_new, 0.0)
    return W_new


def prune_pseudoinverse_retrain(
    patterns: np.ndarray,
    s: float = 0.75,
    max_iter: int = 8,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Pseudoinverse post-hoc prune → masked constrained-LS retrain.

    Steps:
      1. Train dense pseudoinverse
      2. Prune at threshold s to get sparsity mask
      3. Solve masked least squares per neuron (retrain_pseudoinverse_masked)
      4. If fixed points still lost, back off s by 0.8× and repeat

    This gives the globally optimal weights for the chosen sparsity pattern
    and substantially outperforms plain post-hoc pruning at matched degree.

    Parameters
    ----------
    patterns : (M, N) bipolar patterns
    s        : initial magnitude threshold multiplier
    max_iter : max backoff iterations if fixed points are lost
    """
    M, N = patterns.shape
    net = HopfieldNetwork(N, rule=PSEUDOINVERSE)
    net.train(patterns)
    W_dense = net.W.copy()

    current_s = s
    W_retrained = W_dense.copy()

    for it in range(max_iter):
        W_mask = prune_magnitude(W_dense, s=current_s)
        W_candidate = retrain_pseudoinverse_masked(patterns, W_mask)
        n_fixed, _ = verify_fixed_points(W_candidate, patterns)
        if n_fixed == M:
            W_retrained = W_candidate
            break
        current_s *= 0.8
    else:
        W_retrained = W_candidate

    report = pruning_report(W_dense, W_retrained, patterns)
    report["final_s"] = round(current_s, 4)
    report["iterations"] = it + 1
    return W_dense, W_retrained, report


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
