"""
run_recall_sweep.py
===================
Sweep M (patterns stored) × s (pruning threshold) and measure recall accuracy.
No truth table generation — pure simulation, handles large N.

Produces a CSV with one row per (rule, M, s, noise_frac) combination showing
how recall degrades as you store more patterns AND prune more aggressively.

Usage
-----
    # Default: N=32, M=1..8, all rules, s=0..1
    python phase1/run_recall_sweep.py

    # Larger network
    python phase1/run_recall_sweep.py --N 64 --max-M 12 --trials 200

    # Single rule, fine-grained s sweep
    python phase1/run_recall_sweep.py --N 32 --rules storkey --s-values 0 0.25 0.5 0.75 1.0 1.25
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

from hopfield_net import HopfieldNetwork, HEBBIAN, STORKEY, PSEUDOINVERSE, ASYNC_CYCLIC
from pruning import prune_magnitude, verify_fixed_points

RESULTS_DIR = Path(__file__).parent / "results"


def recall_accuracy(
    W: np.ndarray,
    patterns: np.ndarray,
    noise_frac: float,
    n_trials: int,
    max_sweeps: int,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """
    Run n_trials recall attempts at a given noise level.
    Returns (recall_acc, mean_sweeps, converge_frac).
    """
    N = W.shape[0]
    M = len(patterns)
    n_flip = max(0, round(noise_frac * N))

    correct = 0
    total_sw = 0
    total_conv = 0

    net = HopfieldNetwork(N, update_mode=ASYNC_CYCLIC)
    net.W = W

    for _ in range(n_trials):
        p_idx = rng.integers(M)
        pat = patterns[p_idx]
        s0 = pat.copy()
        if n_flip > 0:
            s0[rng.choice(N, size=n_flip, replace=False)] *= -1.0
        s_final, n_sw, conv = net.run(s0, max_sweeps=max_sweeps)
        correct   += int(np.array_equal(s_final, pat))
        total_sw  += n_sw
        total_conv += int(conv)

    return (
        round(correct   / n_trials, 4),
        round(total_sw  / n_trials, 2),
        round(total_conv / n_trials, 4),
    )


def run_sweep(
    N: int,
    M_values: list[int],
    s_values: list[float],
    noise_fracs: list[float],
    rules: list[str],
    n_trials: int,
    max_sweeps: int,
    seed: int,
    verbose: bool = True,
) -> list[dict]:
    rule_map = {"hebbian": HEBBIAN, "storkey": STORKEY, "pseudoinverse": PSEUDOINVERSE}
    rng = np.random.default_rng(seed)
    rows = []

    for rule_name in rules:
        if verbose:
            print(f"\n{'═'*65}")
            print(f"  {rule_name.upper()}   N={N}")
            print(f"{'═'*65}")
            print(f"  {'M':>3} {'α':>5} {'s':>5} {'%zero':>6} "
                  f"{'fp':>5} {'deg':>5}  " +
                  "  ".join(f"η={nf:.0%}" for nf in noise_fracs))
            print(f"  {'-'*60}")

        # Generate one large pattern set and slice it per M
        max_M = max(M_values)
        all_patterns = rng.choice([-1.0, 1.0], size=(max_M, N))

        for M in M_values:
            patterns = all_patterns[:M]

            # Train once per M
            net = HopfieldNetwork(N, rule=rule_map[rule_name])
            net.train(patterns)
            W_dense = net.W.copy()

            off = W_dense[np.triu_indices(N, k=1)]
            off_nz = off[np.abs(off) > 1e-8]
            dense_std  = float(np.std(off_nz))  if len(off_nz) else 0.0
            dense_mean = float(np.mean(off_nz)) if len(off_nz) else 0.0

            for s in s_values:
                W = prune_magnitude(W_dense, s=s)

                degrees = (np.abs(W) > 1e-8).sum(axis=1)
                mean_deg = float(degrees.mean())
                n_zero_added = float(
                    (np.abs(W) < 1e-8).mean() - (np.abs(W_dense) < 1e-8).mean()
                )
                n_fixed, _ = verify_fixed_points(W, patterns)

                off_p = W[np.triu_indices(N, k=1)]
                off_p_nz = off_p[np.abs(off_p) > 1e-8]
                pruned_mean = float(np.mean(off_p_nz)) if len(off_p_nz) else 0.0
                pruned_std  = float(np.std(off_p_nz))  if len(off_p_nz) else 0.0

                recall_at_noise = []
                for noise_frac in noise_fracs:
                    acc, mean_sw, conv_frac = recall_accuracy(
                        W, patterns, noise_frac, n_trials, max_sweeps, rng
                    )
                    recall_at_noise.append(acc)
                    rows.append({
                        "rule":         rule_name,
                        "N":            N,
                        "M":            M,
                        "load":         round(M / N, 4),
                        "s":            s,
                        "threshold":    round(s * dense_std, 6),
                        "pct_zeroed":   round(n_zero_added * 100, 1),
                        "W_mean":       round(pruned_mean, 6),
                        "W_std":        round(pruned_std, 6),
                        "n_fixed":      n_fixed,
                        "frac_fixed":   round(n_fixed / M, 4),
                        "mean_degree":  round(mean_deg, 2),
                        "noise_frac":   noise_frac,
                        "n_flip":       max(0, round(noise_frac * N)),
                        "recall":       acc,
                        "mean_sweeps":  mean_sw,
                        "converge_frac": conv_frac,
                    })

                if verbose:
                    recalls_str = "  ".join(f"{r:.2f}" for r in recall_at_noise)
                    print(f"  M={M:>2} α={M/N:.2f} s={s:.2f} "
                          f"{n_zero_added*100:>5.1f}% "
                          f"{n_fixed}/{M:>2} "
                          f"d={mean_deg:>4.1f}  {recalls_str}")

    return rows


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows → {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sweep M and pruning threshold s, measure recall accuracy."
    )
    parser.add_argument("--N",        type=int, default=32)
    parser.add_argument("--max-M",    type=int, default=None,
                        help="Maximum M to sweep (default: floor(0.6*N) for Storkey capacity)")
    parser.add_argument("--M-values", nargs="+", type=int, default=None,
                        help="Explicit M values (overrides --max-M)")
    parser.add_argument("--rules",    nargs="+", default=["storkey", "pseudoinverse"],
                        choices=["hebbian", "storkey", "pseudoinverse"])
    parser.add_argument("--s-values", nargs="+", type=float,
                        default=[0.0, 0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--noise",    nargs="+", type=float,
                        default=[0.0, 0.10, 0.20, 0.30])
    parser.add_argument("--trials",   type=int, default=200)
    parser.add_argument("--max-sweeps", type=int, default=50)
    parser.add_argument("--seed",     type=int, default=42)
    parser.add_argument("--out",      type=str, default=None)
    args = parser.parse_args()

    N = args.N
    if args.M_values:
        M_values = args.M_values
    else:
        max_M = args.max_M or max(2, int(0.6 * N))
        # Sample M values: every 1 for small N, every 2-4 for large N
        step = max(1, N // 16)
        M_values = list(range(1, max_M + 1, step))
        if max_M not in M_values:
            M_values.append(max_M)

    print(f"Recall sweep — N={N}, M={M_values}, trials={args.trials}, seed={args.seed}")
    print(f"Rules: {args.rules}  |  s: {args.s_values}  |  noise: {args.noise}")

    t0 = time.time()
    rows = run_sweep(
        N=N,
        M_values=M_values,
        s_values=args.s_values,
        noise_fracs=args.noise,
        rules=args.rules,
        n_trials=args.trials,
        max_sweeps=args.max_sweeps,
        seed=args.seed,
    )
    print(f"\nDone in {time.time()-t0:.1f}s")

    out_path = Path(args.out) if args.out else (
        RESULTS_DIR / f"recall_sweep_N{N}_seed{args.seed}.csv"
    )
    save_csv(rows, out_path)
