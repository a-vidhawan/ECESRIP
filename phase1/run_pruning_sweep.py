"""
run_pruning_sweep.py
====================
Sweep pruning threshold s (as a multiplier of std(W)) and measure how
HNN accuracy degrades. For each (rule, s) pair:

  - Prune W by zeroing |W_ij| < s * std(W)
  - Measure: fixed point survival, recall accuracy vs noise, convergence speed
  - Compare bipolar reference (A) vs LUT lookup (D) to confirm equivalence
  - Report LUT compression ratio and mean degree

After the sweep, exports sparse truth tables for specified s values.

Results
-------
    phase1/results/pruning_sweep_N{N}_M{M}_seed{seed}.csv   (per-row metrics)
    phase1/results/truth_tables/rule_s{s}/                  (truth tables)

Usage
-----
    # Default sweep (N=16, M=4, all 3 rules)
    python phase1/run_pruning_sweep.py

    # Custom
    python phase1/run_pruning_sweep.py --N 16 --M 6 --seed 0 --trials 200

    # Export truth tables for specific s values
    python phase1/run_pruning_sweep.py --export-s 0.5 0.75 1.0
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
sys.path.insert(0, str(_REPO / "hardware" / "hopfield_hw" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hopfield_net import HopfieldNetwork, HEBBIAN, STORKEY, PSEUDOINVERSE, ASYNC_CYCLIC
from truth_table_gen import save_json, save_csv as save_tt_csv
from pruning import (
    prune_magnitude, verify_fixed_points, pruning_report, sweep_pruning_threshold
)
from sparse_hopfield import enumerate_sparse_truth_tables
from verify_binary_encoding import (
    build_lut_arrays, run_D_lut, bipolar_to_binary, binary_to_bipolar
)

RESULTS_DIR = Path(__file__).parent / "results"

# ─────────────────────────────────────────────────────────────────────────────
# Core: recall accuracy on a single (W, patterns) configuration
# ─────────────────────────────────────────────────────────────────────────────

def measure_recall(
    W: np.ndarray,
    patterns: np.ndarray,
    noise_fracs: list[float],
    n_trials: int,
    max_sweeps: int,
    rng: np.random.Generator,
    also_lut: bool = True,
) -> list[dict]:
    """
    For each noise level, run n_trials recall attempts and return metrics.

    also_lut: if True, also runs LUT (D) and checks agreement with bipolar (A).
    Returns one dict per noise_frac.
    """
    N = W.shape[0]
    M = len(patterns)

    # Build LUT once if needed
    lut = build_lut_arrays(W) if also_lut else None

    rows = []
    for noise_frac in noise_fracs:
        n_flip = max(0, round(noise_frac * N))
        correct_A = 0
        correct_D = 0
        agree_AD  = 0
        total_sweeps = 0
        n_converged  = 0

        for _ in range(n_trials):
            p_idx = rng.integers(M)
            pat = patterns[p_idx]

            # Generate noisy initial state
            s0 = pat.copy()
            if n_flip > 0:
                flip_idx = rng.choice(N, size=n_flip, replace=False)
                s0[flip_idx] *= -1.0

            # Simulator A — bipolar reference
            net = HopfieldNetwork(N, update_mode=ASYNC_CYCLIC)
            net.W = W
            sA, n_sw, converged = net.run(s0.copy(), max_sweeps=max_sweeps)
            total_sweeps += n_sw
            n_converged  += int(converged)
            if np.array_equal(sA, pat):
                correct_A += 1

            # Simulator D — LUT
            if lut is not None:
                b0 = bipolar_to_binary(s0)
                bD = run_D_lut(lut, b0, max_sweeps=max_sweeps)
                sD = binary_to_bipolar(bD)
                if np.array_equal(sD, pat):
                    correct_D += 1
                if np.array_equal(sA, sD):
                    agree_AD += 1

        rows.append({
            "noise_frac":       round(noise_frac, 3),
            "n_flip":           n_flip,
            "recall_A":         round(correct_A / n_trials, 4),
            "recall_D":         round(correct_D / n_trials, 4) if lut else None,
            "agree_AD":         round(agree_AD  / n_trials, 4) if lut else None,
            "mean_sweeps":      round(total_sweeps / n_trials, 2),
            "converge_frac":    round(n_converged  / n_trials, 4),
        })

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Full sweep: rule × s × noise_frac
# ─────────────────────────────────────────────────────────────────────────────

def run_sweep(
    patterns: np.ndarray,
    s_values:     list[float],
    noise_fracs:  list[float],
    n_trials:     int  = 100,
    max_sweeps:   int  = 50,
    rules:        list[str] | None = None,
    seed:         int  = 42,
    also_lut:     bool = True,
    verbose:      bool = True,
) -> list[dict]:
    """
    Full sweep over rules × s values × noise levels.

    Returns a flat list of result dicts (one per rule × s × noise_frac).
    """
    if rules is None:
        rules = ["hebbian", "storkey", "pseudoinverse"]

    rule_map = {"hebbian": HEBBIAN, "storkey": STORKEY, "pseudoinverse": PSEUDOINVERSE}
    M, N = patterns.shape
    rng = np.random.default_rng(seed)
    all_rows = []

    for rule_name in rules:
        # Train dense W once per rule
        net = HopfieldNetwork(N, rule=rule_map[rule_name])
        net.train(patterns)
        W_dense = net.W.copy()

        off = W_dense[np.triu_indices(N, k=1)]
        std = float(np.std(off[np.abs(off) > 1e-8]))

        if verbose:
            print(f"\n{'─'*60}")
            print(f"Rule: {rule_name.upper()}  |  std(W)={std:.4f}")
            print(f"{'─'*60}")

        for s in s_values:
            # Prune
            W_pruned = prune_magnitude(W_dense, s=s)
            threshold = s * std

            # Structural stats
            degrees = (np.abs(W_pruned) > 1e-8).sum(axis=1)
            mean_deg = float(degrees.mean())
            max_deg  = int(degrees.max())
            sparse_lut = int(sum(2**int(d) for d in degrees))
            compress   = round(N * (1 << N) / max(sparse_lut, 1), 1)
            n_zero_frac = float((np.abs(W_pruned) < 1e-8).mean() -
                                (np.abs(W_dense)  < 1e-8).mean())
            n_fixed, _ = verify_fixed_points(W_pruned, patterns)

            if verbose:
                print(f"  s={s:.2f} | threshold={threshold:.4f} | "
                      f"{n_zero_frac*100:.1f}% zeroed | "
                      f"deg {mean_deg:.1f} | {n_fixed}/{M} fp | {compress:.0f}× compress")

            # Recall accuracy at each noise level
            noise_rows = measure_recall(
                W_pruned, patterns, noise_fracs,
                n_trials=n_trials, max_sweeps=max_sweeps,
                rng=rng, also_lut=also_lut,
            )

            for nr in noise_rows:
                all_rows.append({
                    "rule":            rule_name,
                    "N":               N,
                    "M":               M,
                    "load":            round(M / N, 4),
                    "s":               s,
                    "threshold":       round(threshold, 6),
                    "pct_zeroed":      round(n_zero_frac * 100, 1),
                    "n_fixed":         n_fixed,
                    "frac_fixed":      round(n_fixed / M, 4),
                    "mean_degree":     round(mean_deg, 2),
                    "max_degree":      max_deg,
                    "sparse_lut":      sparse_lut,
                    "compression":     compress,
                    **nr,
                })

    return all_rows


# ─────────────────────────────────────────────────────────────────────────────
# Truth table export for selected (rule, s) pairs
# ─────────────────────────────────────────────────────────────────────────────

def export_truth_tables(
    patterns: np.ndarray,
    export_s: list[float],
    rules:    list[str] | None = None,
    out_dir:  Path | None = None,
    verbose:  bool = True,
) -> None:
    """
    For each (rule, s) pair in export_s, train, prune, and export sparse truth tables.

    Output layout:
        out_dir/
          {rule}_s{s}/
            sparse_truth_tables.json
            W_pruned.npy
            tt_csv/
              tt_neuron_000.csv  ...
    """
    if rules is None:
        rules = ["hebbian", "storkey", "pseudoinverse"]
    if out_dir is None:
        out_dir = RESULTS_DIR / "truth_tables"

    rule_map = {"hebbian": HEBBIAN, "storkey": STORKEY, "pseudoinverse": PSEUDOINVERSE}
    M, N = patterns.shape

    for rule_name in rules:
        net = HopfieldNetwork(N, rule=rule_map[rule_name])
        net.train(patterns)
        W_dense = net.W.copy()

        for s in export_s:
            W_pruned = prune_magnitude(W_dense, s=s)
            n_fixed, _ = verify_fixed_points(W_pruned, patterns)

            tag = f"{rule_name}_s{s:.2f}".replace(".", "p")
            dest = out_dir / tag
            dest.mkdir(parents=True, exist_ok=True)

            # Save pruned W
            np.save(dest / "W_pruned.npy", W_pruned)

            # Sparse truth tables (2^dᵢ per neuron)
            sparse_tables = enumerate_sparse_truth_tables(W_pruned)
            import json
            sparse_data = {
                "rule": rule_name, "N": N, "M": M, "s": s,
                "n_fixed": n_fixed,
                "neurons": [
                    {"idx": tt.neuron_idx, "neighbors": tt.neighbors,
                     "on_set": tt.on_set, "lut_size": tt.lut_size}
                    for tt in sparse_tables
                ]
            }
            with open(dest / "sparse_truth_tables.json", "w") as f:
                json.dump(sparse_data, f, indent=2)

            # Dense truth tables for small N (full 2^N enumeration)
            if N <= 20:
                from truth_table_gen import enumerate_truth_tables
                dense_tables = enumerate_truth_tables(W_pruned)
                save_tt_csv(dense_tables, dest / "tt_csv")
                from truth_table_gen import save_json as tt_save_json
                tt_save_json(dense_tables, dest / "truth_tables.json")

            if verbose:
                total_sparse = sum(tt.lut_size for tt in sparse_tables)
                print(f"  {tag}: {n_fixed}/{M} fp | "
                      f"sparse LUT {total_sparse} entries | "
                      f"→ {dest}/")


# ─────────────────────────────────────────────────────────────────────────────
# Save results to CSV
# ─────────────────────────────────────────────────────────────────────────────

def save_results(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResults → {path}  ({len(rows)} rows)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sweep pruning threshold and measure HNN accuracy degradation."
    )
    parser.add_argument("--N",       type=int,   default=16)
    parser.add_argument("--M",       type=int,   default=4)
    parser.add_argument("--seed",    type=int,   default=42)
    parser.add_argument("--trials",  type=int,   default=200,
                        help="Recall trials per (rule, s, noise) point")
    parser.add_argument("--max-sweeps", type=int, default=50)
    parser.add_argument("--rules",   nargs="+",
                        default=["hebbian", "storkey", "pseudoinverse"],
                        choices=["hebbian", "storkey", "pseudoinverse"])
    parser.add_argument("--s-values", nargs="+", type=float,
                        default=[0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
                        help="Pruning threshold multipliers to sweep")
    parser.add_argument("--noise",   nargs="+", type=float,
                        default=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40],
                        help="Noise levels (fraction of bits flipped)")
    parser.add_argument("--export-s", nargs="*", type=float, default=None,
                        help="Export truth tables for these s values (default: none)")
    parser.add_argument("--no-lut",  action="store_true",
                        help="Skip LUT (D) verification for speed")
    parser.add_argument("--out",     type=str, default=None,
                        help="Output CSV path (default: phase1/results/pruning_sweep_...csv)")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    patterns = rng.choice([-1.0, 1.0], size=(args.M, args.N))

    print(f"Pruning sweep — N={args.N}, M={args.M}, "
          f"trials={args.trials}, seed={args.seed}")
    print(f"Rules:    {args.rules}")
    print(f"s values: {args.s_values}")
    print(f"Noise:    {args.noise}")

    t0 = time.time()
    rows = run_sweep(
        patterns,
        s_values=args.s_values,
        noise_fracs=args.noise,
        n_trials=args.trials,
        max_sweeps=args.max_sweeps,
        rules=args.rules,
        seed=args.seed,
        also_lut=not args.no_lut,
    )
    print(f"\nSweep done in {time.time()-t0:.1f}s")

    out_path = Path(args.out) if args.out else (
        RESULTS_DIR / f"pruning_sweep_N{args.N}_M{args.M}_seed{args.seed}.csv"
    )
    save_results(rows, out_path)

    if args.export_s:
        print(f"\nExporting truth tables for s = {args.export_s} …")
        export_truth_tables(
            patterns,
            export_s=args.export_s,
            rules=args.rules,
            out_dir=RESULTS_DIR / "truth_tables",
        )

    print("\nDone.")
