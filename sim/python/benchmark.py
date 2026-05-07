"""
Hopfield network benchmark suite.

Metrics
-------
recall_accuracy  : fraction of noisy-pattern trials that recover the original stored pattern
basin_width      : max flip count where recall_accuracy >= BASIN_THRESHOLD
spurious_rate    : fraction of random-init trials that land in a non-stored attractor
convergence_iter : mean sweeps to reach a fixed point

Quick usage
-----------
    python benchmark.py

Edit the CONFIG block below to change sweep parameters, dataset, rule, update mode.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np

from hopfield_net import (
    HopfieldNetwork,
    STORKEY, HEBBIAN,
    ASYNC_CYCLIC, ASYNC_RANDOM, SYNC,
)
from datasets import load, add_noise, dataset_N, RANDOM, MNIST_8, MNIST_28

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG — edit here to change the sweep
# ═══════════════════════════════════════════════════════════════════════════════

RULE        = STORKEY       # STORKEY or HEBBIAN
UPDATE_MODE = ASYNC_CYCLIC  # ASYNC_CYCLIC (1), ASYNC_RANDOM (2), or SYNC (3)
DATASET     = RANDOM        # RANDOM, MNIST_8, or MNIST_28

N_VALUES    = [6, 8, 10, 12, 14, 16]          # neuron counts to sweep
MAX_LOAD    = 0.30                             # sweep M up to MAX_LOAD * N
NOISE_FRACS = [0.0, 0.05, 0.10, 0.15, 0.20,
               0.25, 0.30, 0.35, 0.40]        # bit-flip fractions of N

N_TRIALS    = 50     # recall/basin trials per (N, M, noise) combination
N_SPURIOUS  = 100    # random-init trials per (N, M) for spurious rate
MAX_SWEEPS  = 40     # max update sweeps per run() call
BASIN_THRESHOLD = 0.90   # recall_accuracy must exceed this to count toward basin_width

OUTPUT_DIR  = Path(__file__).parent.parent / 'results'
SEED        = 42

# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Row:
    """One row of benchmark output."""
    rule: str
    update_mode: int
    dataset: str
    N: int
    M: int
    load: float               # M / N
    noise_frac: float         # k / N
    noise_k: int              # actual bits flipped
    recall_accuracy: float
    basin_width: int          # populated only for noise_frac == None sentinel
    spurious_rate: float
    mean_convergence_iters: float
    converged_fraction: float


def _mode_name(mode: int) -> str:
    return {ASYNC_CYCLIC: 'async_cyclic', ASYNC_RANDOM: 'async_random', SYNC: 'sync'}[mode]


def run_benchmark(
    rule: str = RULE,
    update_mode: int = UPDATE_MODE,
    dataset: str = DATASET,
    N_values: list[int] = N_VALUES,
    max_load: float = MAX_LOAD,
    noise_fracs: list[float] = NOISE_FRACS,
    n_trials: int = N_TRIALS,
    n_spurious: int = N_SPURIOUS,
    max_sweeps: int = MAX_SWEEPS,
    basin_threshold: float = BASIN_THRESHOLD,
    seed: int = SEED,
) -> list[dict]:
    """
    Full benchmark sweep over N and M.

    Returns list of result dicts (one per (N, M, noise_frac) combination).
    """
    results = []
    rng = np.random.default_rng(seed)

    for N in N_values:
        if dataset != RANDOM:
            N = dataset_N(dataset)   # override N for fixed-size datasets

        M_max = max(1, int(np.ceil(max_load * N)))

        for M in range(1, M_max + 1):
            patterns = load(dataset, N, M, seed=int(rng.integers(1 << 31)))
            if len(patterns) < M:
                print(f"  [skip] N={N} M={M}: dataset has fewer than M patterns")
                break

            net = HopfieldNetwork(N, rule=rule, update_mode=update_mode)
            net.train(patterns)

            # ── spurious state rate ────────────────────────────────────────
            spurious = 0
            for _ in range(n_spurious):
                s0 = rng.choice([-1.0, 1.0], size=N)
                s_final, _, _ = net.run(s0, max_sweeps=max_sweeps, rng=rng)
                if not _is_stored_or_neg(s_final, patterns):
                    spurious += 1
            spurious_rate = spurious / n_spurious

            # ── recall accuracy, convergence per noise level ───────────────
            noise_ks = [max(0, int(round(f * N))) for f in noise_fracs]
            basin_width = 0

            for noise_frac, noise_k in zip(noise_fracs, noise_ks):
                correct = 0
                total_iters = 0
                total_converged = 0

                for _ in range(n_trials):
                    # pick a random stored pattern
                    pat = patterns[rng.integers(M)]
                    s0 = add_noise(pat, noise_k, rng)
                    s_final, n_iters, converged = net.run(
                        s0, max_sweeps=max_sweeps, rng=rng
                    )
                    total_iters += n_iters
                    total_converged += int(converged)
                    if np.array_equal(s_final, pat):
                        correct += 1

                recall_acc = correct / n_trials
                if recall_acc >= basin_threshold:
                    basin_width = noise_k

                results.append(asdict(Row(
                    rule=rule,
                    update_mode=update_mode,
                    dataset=dataset,
                    N=N,
                    M=M,
                    load=round(M / N, 4),
                    noise_frac=noise_frac,
                    noise_k=noise_k,
                    recall_accuracy=round(recall_acc, 4),
                    basin_width=basin_width,
                    spurious_rate=round(spurious_rate, 4),
                    mean_convergence_iters=round(total_iters / n_trials, 2),
                    converged_fraction=round(total_converged / n_trials, 4),
                )))

            print(
                f"N={N:2d}  M={M:2d}  load={M/N:.2f}  "
                f"spurious={spurious_rate:.2f}  basin={basin_width}"
            )

        if dataset != RANDOM:
            break   # MNIST has fixed N, no outer N sweep

    return results


def _is_stored_or_neg(s: np.ndarray, patterns: np.ndarray) -> bool:
    """True if s equals any stored pattern or its negative."""
    for p in patterns:
        if np.array_equal(s, p) or np.array_equal(s, -p):
            return True
    return False


def save_csv(results: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved {len(results)} rows → {path}")


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(
        f"Benchmark  rule={RULE}  update={_mode_name(UPDATE_MODE)}"
        f"  dataset={DATASET}  N={N_VALUES}\n"
    )
    t0 = time.time()
    results = run_benchmark()
    elapsed = time.time() - t0

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    out_path = OUTPUT_DIR / f'benchmark_{RULE}_{_mode_name(UPDATE_MODE)}_{DATASET}_{timestamp}.csv'
    save_csv(results, out_path)
    print(f"\nDone in {elapsed:.1f}s")
