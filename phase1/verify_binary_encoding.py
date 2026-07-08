"""
verify_binary_encoding.py
=========================
Four-way comparison of Hopfield network update dynamics to verify that
{0,1} binary encoding with implicit threshold is exactly equivalent to
the {-1,+1} bipolar reference — and that the LUT truth-table lookup
replicates both exactly.

Simulators
----------
A  (bipolar reference) : {-1,+1} update via hopfield_net.py — ground truth
B  (binary+threshold)  : {0,1} update with θᵢ = ½ Σⱼ Wᵢⱼ baked in
C  (binary naive WRONG): {0,1} update without threshold — EXPECTED TO DIVERGE
D  (LUT lookup)        : Precomputed truth-table via truth_table_gen.py

All four run from identical initial states on identical weight matrices.
The script asserts A == B == D and reports that C produces different attractors.

Usage
-----
    python phase1/verify_binary_encoding.py [--N 8] [--M 3] [--trials 50]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Add repo root to path so we can import sim/ and hardware/ modules
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
sys.path.insert(0, str(_REPO / "hardware" / "hopfield_hw" / "python"))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from truth_table_gen import enumerate_truth_tables


# ─────────────────────────────────────────────────────────────────────────────
# Simulator A — bipolar {-1,+1} reference
# ─────────────────────────────────────────────────────────────────────────────

def run_A_bipolar(
    W: np.ndarray,
    s_init_bipolar: np.ndarray,
    max_sweeps: int = 50,
) -> np.ndarray:
    """
    Standard bipolar {-1,+1} Hopfield update (async cyclic).
    Uses hopfield_net.HopfieldNetwork directly.
    """
    N = W.shape[0]
    net = HopfieldNetwork(N, update_mode=ASYNC_CYCLIC)
    net.W = W.copy()
    s_final, _, _ = net.run(s_init_bipolar.copy(), max_sweeps=max_sweeps)
    return s_final   # {-1,+1}


# ─────────────────────────────────────────────────────────────────────────────
# Simulator B — binary {0,1} with threshold (correct)
# ─────────────────────────────────────────────────────────────────────────────

def run_B_binary_threshold(
    W: np.ndarray,
    b_init: np.ndarray,
    max_sweeps: int = 50,
) -> np.ndarray:
    """
    Binary {0,1} async cyclic update with per-neuron threshold.

    The threshold is derived from the {-1,+1} ↔ {0,1} substitution s_j = 2b_j - 1:

        h_i(s) = Σⱼ Wᵢⱼ sⱼ
               = Σⱼ Wᵢⱼ (2bⱼ - 1)
               = 2 Σⱼ Wᵢⱼ bⱼ  -  Σⱼ Wᵢⱼ
                   ^^^^^^^^^       ^^^^^^^^
                   dot product    threshold θᵢ

    So: b_i ← step(2*(W[i]·b) - row_sum[i])
             = step(W[i]·b - θᵢ)   where θᵢ = ½ * row_sum[i]

    (The factor of 2 cancels with the half; the sign of h_i is all that matters.)
    """
    N = W.shape[0]
    row_sums = W.sum(axis=1)   # θᵢ = row_sums[i] / 2 (but the /2 cancels)
    b = b_init.astype(float).copy()

    for _ in range(max_sweeps):
        b_prev = b.copy()
        for i in range(N):
            # h_i = 2*(W[i] @ b) - row_sums[i]   (same formula as truth_table_gen.py)
            h_i = 2.0 * float(W[i] @ b) - row_sums[i]
            if h_i > 0:
                b[i] = 1.0
            elif h_i < 0:
                b[i] = 0.0
            # h_i == 0: hold current state
        if np.array_equal(b, b_prev):
            break
    return b   # {0,1}


# ─────────────────────────────────────────────────────────────────────────────
# Simulator C — binary {0,1} WITHOUT threshold (naive, WRONG)
# ─────────────────────────────────────────────────────────────────────────────

def run_C_binary_naive(
    W: np.ndarray,
    b_init: np.ndarray,
    max_sweeps: int = 50,
) -> np.ndarray:
    """
    Binary {0,1} async cyclic update WITHOUT the threshold correction.

    This is the naive mistake: treating {0,1} bits as if they were {-1,+1}
    by just computing W[i]@b instead of 2*(W[i]@b) - row_sum[i].

    Expected result: different (wrong) attractors compared to A and B.
    This simulator exists to demonstrate WHY the threshold is critical.
    """
    N = W.shape[0]
    b = b_init.astype(float).copy()

    for _ in range(max_sweeps):
        b_prev = b.copy()
        for i in range(N):
            h_i = float(W[i] @ b)   # MISSING threshold — incorrect for binary
            if h_i > 0:
                b[i] = 1.0
            elif h_i < 0:
                b[i] = 0.0
        if np.array_equal(b, b_prev):
            break
    return b   # {0,1} — but wrong attractors


# ─────────────────────────────────────────────────────────────────────────────
# Simulator D — LUT truth-table lookup
# ─────────────────────────────────────────────────────────────────────────────

def build_lut_arrays(W: np.ndarray) -> list[np.ndarray]:
    """
    Precompute LUT arrays from weight matrix W using truth_table_gen.

    Returns a list of N arrays, each of length 2^N.
    lut[i][m] = output bit of neuron i for minterm m.
    """
    tables = enumerate_truth_tables(W, tie_break=1)
    N = W.shape[0]
    lut = []
    for tt in tables:
        arr = np.zeros(1 << N, dtype=np.uint8)
        arr[tt.on_set] = 1
        lut.append(arr)
    return lut


def _state_to_minterm(b: np.ndarray) -> int:
    """Convert binary state vector to integer minterm index (MSB = b[0])."""
    N = len(b)
    m = 0
    for j in range(N):
        if b[j]:
            m |= 1 << (N - 1 - j)
    return m


def run_D_lut(
    lut: list[np.ndarray],
    b_init: np.ndarray,
    max_sweeps: int = 50,
) -> np.ndarray:
    """
    Binary {0,1} async cyclic update via LUT truth-table lookup.

    Each neuron update b_i ← lut[i][minterm(b)] is a single array index.
    This is exactly what the FPGA hardware does at runtime.
    """
    N = len(lut)
    b = b_init.astype(float).copy()

    for _ in range(max_sweeps):
        b_prev = b.copy()
        for i in range(N):
            m = _state_to_minterm(b)
            b[i] = float(lut[i][m])
        if np.array_equal(b, b_prev):
            break
    return b   # {0,1}


# ─────────────────────────────────────────────────────────────────────────────
# Conversion helpers
# ─────────────────────────────────────────────────────────────────────────────

def bipolar_to_binary(s: np.ndarray) -> np.ndarray:
    """Convert {-1,+1} → {0,1}."""
    return ((s + 1) / 2).astype(float)


def binary_to_bipolar(b: np.ndarray) -> np.ndarray:
    """Convert {0,1} → {-1,+1}."""
    return (2 * b - 1).astype(float)


# ─────────────────────────────────────────────────────────────────────────────
# Main verification experiment
# ─────────────────────────────────────────────────────────────────────────────

def run_verification(
    N: int = 8,
    M: int = 3,
    trials: int = 50,
    noise_rate: float = 0.2,
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """
    Train a Hopfield network on M random patterns, then run all 4 simulators
    from `trials` different noisy initial states.

    Asserts A == B == D and measures how often C diverges from them.

    Returns
    -------
    dict with keys: n_agree_AB, n_agree_AD, n_disagree_C, n_trials
    """
    rng = np.random.default_rng(seed)

    # ── Train network (Storkey rule, bipolar)
    net = HopfieldNetwork(N, rule=STORKEY, update_mode=ASYNC_CYCLIC)
    patterns_bipolar = rng.choice([-1.0, 1.0], size=(M, N))
    net.train(patterns_bipolar)
    W = net.W

    # ── Precompute LUTs
    lut = build_lut_arrays(W)

    # ── Run trials
    results = {"n_agree_AB": 0, "n_agree_AD": 0, "n_disagree_C": 0, "n_trials": trials}
    ab_mismatches = []
    ad_mismatches = []

    for t in range(trials):
        # Pick a random stored pattern and corrupt noise_rate fraction of bits
        p_idx = rng.integers(M)
        s0 = patterns_bipolar[p_idx].copy()
        flip_mask = rng.random(N) < noise_rate
        s0[flip_mask] *= -1.0

        b0 = bipolar_to_binary(s0)

        # Run all four simulators
        sA = run_A_bipolar(W, s0)
        bB = run_B_binary_threshold(W, b0)
        bC = run_C_binary_naive(W, b0)
        bD = run_D_lut(lut, b0)

        # Convert A to binary for comparison
        bA = bipolar_to_binary(sA)

        agree_AB = np.array_equal(bA, bB)
        agree_AD = np.array_equal(bA, bD)
        disagree_C = not np.array_equal(bA, bC)

        if agree_AB:
            results["n_agree_AB"] += 1
        else:
            ab_mismatches.append(t)

        if agree_AD:
            results["n_agree_AD"] += 1
        else:
            ad_mismatches.append(t)

        if disagree_C:
            results["n_disagree_C"] += 1

    if verbose:
        print(f"\n{'='*60}")
        print(f"Encoding Verification  N={N}, M={M}, trials={trials}, noise={noise_rate:.0%}")
        print(f"{'='*60}")
        print(f"  A==B (bipolar == binary+threshold):  "
              f"{results['n_agree_AB']}/{trials}  "
              f"{'PASS ✓' if results['n_agree_AB'] == trials else 'FAIL ✗'}")
        print(f"  A==D (bipolar == LUT lookup):        "
              f"{results['n_agree_AD']}/{trials}  "
              f"{'PASS ✓' if results['n_agree_AD'] == trials else 'FAIL ✗'}")
        print(f"  C≠A  (naive binary gives WRONG att): "
              f"{results['n_disagree_C']}/{trials}  "
              f"{'(expected — threshold is critical)' if results['n_disagree_C'] > 0 else '(suspiciously correct — check W)'}")
        if ab_mismatches:
            print(f"\n  WARNING: A≠B on trials {ab_mismatches}")
        if ad_mismatches:
            print(f"\n  WARNING: A≠D on trials {ad_mismatches}")

    return results


def run_optimization_verification(
    N: int = 12,
    seed: int = 0,
    verbose: bool = True,
) -> None:
    """
    Verify on an Ising optimization instance (SK spin glass).
    Confirms that LUT dynamics find the same states as bipolar reference.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from datasets.loaders import sk_spin_glass, brute_force_ground_state

    W, h, meta = sk_spin_glass(N=N, seed=seed)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Optimization Verification — {meta['name']}")
        print(f"{'='*60}")

    lut = build_lut_arrays(W)
    rng = np.random.default_rng(seed)

    energies_A, energies_D = [], []
    for _ in range(20):
        s0 = rng.choice([-1.0, 1.0], size=N)
        b0 = bipolar_to_binary(s0)

        sA = run_A_bipolar(W, s0)
        bD = run_D_lut(lut, b0)
        sD = binary_to_bipolar(bD)

        eA = -0.5 * float(sA @ W @ sA)
        eD = -0.5 * float(sD @ W @ sD)
        energies_A.append(eA)
        energies_D.append(eD)

    # Brute force ground state for small N
    if N <= 18:
        gs, E_gs = brute_force_ground_state(W)
        if verbose:
            print(f"  Ground state energy (exact): {E_gs:.4f}")

    if verbose:
        print(f"  HNN (bipolar A) — mean energy: {np.mean(energies_A):.4f} ± {np.std(energies_A):.4f}")
        print(f"  LUT (D)         — mean energy: {np.mean(energies_D):.4f} ± {np.std(energies_D):.4f}")
        n_match = sum(abs(a - d) < 1e-9 for a, d in zip(energies_A, energies_D))
        print(f"  A and D find identical states: {n_match}/20")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify binary {0,1} encoding equivalence for LUT-HNN."
    )
    parser.add_argument("--N", type=int, default=8, help="Number of neurons")
    parser.add_argument("--M", type=int, default=3, help="Patterns to store")
    parser.add_argument("--trials", type=int, default=100, help="Number of random initial states")
    parser.add_argument("--noise", type=float, default=0.2, help="Bit-flip noise rate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--optim-N", type=int, default=12,
                        help="N for optimization (SK spin glass) verification")
    args = parser.parse_args()

    # Part 1: Associative memory verification
    res = run_verification(N=args.N, M=args.M, trials=args.trials,
                           noise_rate=args.noise, seed=args.seed)

    # Hard assertions
    assert res["n_agree_AB"] == res["n_trials"], \
        f"FAIL: Binary+threshold (B) disagrees with bipolar (A) on {res['n_trials'] - res['n_agree_AB']} trials!"
    assert res["n_agree_AD"] == res["n_trials"], \
        f"FAIL: LUT (D) disagrees with bipolar (A) on {res['n_trials'] - res['n_agree_AD']} trials!"

    print("\nAll assertions passed — {0,1} binary encoding with threshold is")
    print("exactly equivalent to {-1,+1} bipolar, and LUT lookup matches both.")

    # Part 2: Optimization verification
    run_optimization_verification(N=args.optim_N, seed=args.seed)

    print("\nVerification complete.")
