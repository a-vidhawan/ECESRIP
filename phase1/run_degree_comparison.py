"""
run_degree_comparison.py
========================
Compare all pruning strategies at matched target degrees.

For a fair comparison, we binary-search the pruning parameter (s or lam)
so every method hits approximately the same mean neuron degree. Then we
measure:
  - Fixed points preserved (n_fixed / M)
  - Recall accuracy at 0%, 15%, 30% noise

Methods compared
----------------
  storkey_posthoc      Dense Storkey → magnitude prune
  storkey_l1           Storkey with L1 during training (ISTA)
  storkey_retrain      Dense Storkey → magnitude prune → re-run Storkey on mask
  pseudo_posthoc       Dense pseudoinverse → magnitude prune
  pseudo_retrain       Dense pseudoinverse → magnitude prune → masked LS retrain

Usage
-----
    python phase1/run_degree_comparison.py
    python phase1/run_degree_comparison.py --N 32 --M 8 --trials 300
    python phase1/run_degree_comparison.py --N 16 --M 4 --degrees 3 4 5 6 8 10
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hopfield_net import HopfieldNetwork, STORKEY, PSEUDOINVERSE, ASYNC_CYCLIC
from pruning import (
    prune_magnitude,
    train_storkey_l1,
    prune_storkey_retrain,
    prune_pseudoinverse,
    prune_pseudoinverse_retrain,
    retrain_storkey_masked,
    retrain_pseudoinverse_masked,
    verify_fixed_points,
    pruning_report,
)

RESULTS_DIR = Path(__file__).parent / "results"


# ─────────────────────────────────────────────────────────────────────────────
# Degree-targeted pruning helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mean_degree(W: np.ndarray, eps: float = 1e-8) -> float:
    return float((np.abs(W) > eps).sum(axis=1).mean())


def _bisect_s(train_fn, patterns, target_deg, lo=0.0, hi=3.0, tol=0.05, n_iter=20):
    """
    Binary-search magnitude threshold s so mean_degree ≈ target_deg.
    train_fn(s) → W_pruned
    """
    for _ in range(n_iter):
        mid = (lo + hi) / 2
        W = train_fn(mid)
        d = _mean_degree(W)
        if abs(d - target_deg) < tol:
            break
        if d > target_deg:
            lo = mid
        else:
            hi = mid
    return train_fn(mid), mid


def _bisect_lam(patterns, target_deg, lo=0.0, hi=5.0, tol=0.05, n_iter=20):
    """Binary-search L1 lambda for Storkey so mean_degree ≈ target_deg."""
    for _ in range(n_iter):
        mid = (lo + hi) / 2
        _, W, _ = train_storkey_l1(patterns, lam=mid)
        d = _mean_degree(W)
        if abs(d - target_deg) < tol:
            break
        if d > target_deg:
            lo = mid
        else:
            hi = mid
    return W, mid


# ─────────────────────────────────────────────────────────────────────────────
# Recall measurement
# ─────────────────────────────────────────────────────────────────────────────

def measure_recall(W, patterns, noise_frac, n_trials, rng):
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
# Main comparison
# ─────────────────────────────────────────────────────────────────────────────

def run_comparison(
    N: int,
    M: int,
    target_degrees: list[int],
    noise_fracs: list[float],
    n_trials: int,
    seed: int,
    verbose: bool = True,
) -> list[dict]:
    rng = np.random.default_rng(seed)
    patterns = rng.choice([-1.0, 1.0], size=(M, N))

    # Pre-train dense baselines
    net_s = HopfieldNetwork(N, rule=STORKEY)
    net_s.train(patterns)
    W_storkey_dense = net_s.W.copy()

    net_p = HopfieldNetwork(N, rule=PSEUDOINVERSE)
    net_p.train(patterns)
    W_pseudo_dense = net_p.W.copy()

    rows = []
    noise_header = "  ".join(f"η={nf:.0%}" for nf in noise_fracs)

    if verbose:
        print(f"\nDegree comparison — N={N}, M={M} (α={M/N:.2f}), seed={seed}")
        print(f"Noise levels: {noise_fracs}")
        print(f"\n{'Method':>22} {'deg':>5} {'fp':>6}  {noise_header}")
        print("─" * (30 + 8 * len(noise_fracs)))

    for target_deg in target_degrees:
        if verbose:
            print(f"\n  ── target degree ≈ {target_deg} ──")

        method_results = []

        # 1. Storkey post-hoc
        W_sp, s_sp = _bisect_s(
            lambda s: prune_magnitude(W_storkey_dense, s=s),
            patterns, target_deg
        )
        method_results.append(("storkey_posthoc", W_sp, s_sp, None))

        # 2. Storkey L1
        W_l1, lam_l1 = _bisect_lam(patterns, target_deg)
        method_results.append(("storkey_l1", W_l1, None, lam_l1))

        # 3. Storkey retrain (use same mask as post-hoc, then retrain)
        W_sr = retrain_storkey_masked(patterns, W_sp)
        method_results.append(("storkey_retrain", W_sr, s_sp, None))

        # 4. Pseudoinverse post-hoc
        W_pp, s_pp = _bisect_s(
            lambda s: prune_magnitude(W_pseudo_dense, s=s),
            patterns, target_deg
        )
        method_results.append(("pseudo_posthoc", W_pp, s_pp, None))

        # 5. Pseudoinverse masked retrain (same mask as post-hoc, then retrain)
        W_pr = retrain_pseudoinverse_masked(patterns, W_pp)
        method_results.append(("pseudo_retrain", W_pr, s_pp, None))

        for method_name, W, s_val, lam_val in method_results:
            actual_deg = _mean_degree(W)
            n_fixed, _ = verify_fixed_points(W, patterns)
            degrees = (np.abs(W) > 1e-8).sum(axis=1)
            sparse_lut = int(sum(2 ** int(d) for d in degrees))

            recalls = [
                measure_recall(W, patterns, nf, n_trials, rng)
                for nf in noise_fracs
            ]

            param_str = f"s={s_val:.3f}" if s_val is not None else f"lam={lam_val:.3f}"

            row = {
                "N": N, "M": M, "load": round(M/N, 4),
                "seed": seed,
                "target_degree": target_deg,
                "method": method_name,
                "param": param_str,
                "actual_degree": round(actual_deg, 2),
                "n_fixed": n_fixed,
                "frac_fixed": round(n_fixed / M, 4),
                "sparse_lut": sparse_lut,
                "compression": round(N * (1 << N) / max(sparse_lut, 1), 1),
            }
            for nf, r in zip(noise_fracs, recalls):
                row[f"recall_{int(nf*100):02d}"] = r
            rows.append(row)

            if verbose:
                fp_str = f"{n_fixed}/{M}"
                recall_str = "  ".join(f"{r:.2f}" for r in recalls)
                print(f"  {method_name:>22} {actual_deg:>5.1f} {fp_str:>6}  {recall_str}"
                      f"   ({param_str})")

    return rows


def save_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows → {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare pruning strategies at matched target neuron degrees."
    )
    parser.add_argument("--N",       type=int,   default=16)
    parser.add_argument("--M",       type=int,   default=4)
    parser.add_argument("--degrees", nargs="+",  type=int,
                        default=[4, 5, 6, 8, 10, 12])
    parser.add_argument("--noise",   nargs="+",  type=float,
                        default=[0.0, 0.15, 0.30])
    parser.add_argument("--trials",  type=int,   default=300)
    parser.add_argument("--seed",    type=int,   default=42)
    parser.add_argument("--out",     type=str,   default=None)
    args = parser.parse_args()

    t0 = time.time()
    rows = run_comparison(
        N=args.N,
        M=args.M,
        target_degrees=args.degrees,
        noise_fracs=args.noise,
        n_trials=args.trials,
        seed=args.seed,
    )
    print(f"\nDone in {time.time()-t0:.1f}s")

    out_path = (Path(args.out) if args.out else
                RESULTS_DIR / f"degree_comparison_N{args.N}_M{args.M}_seed{args.seed}.csv")
    save_csv(rows, out_path)
