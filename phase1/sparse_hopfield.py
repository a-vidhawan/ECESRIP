"""
sparse_hopfield.py
==================
Sparse Hopfield network training and sparse LUT generation.

Two approaches:
  1. Magnitude pruning  — train dense, zero out small |W_ij|
  2. L1 proximal step  — apply soft-thresholding after each Storkey update

The key output is a SPARSE truth table: for each neuron i, only the dᵢ
non-zero neighbours appear in the table, so size = 2^dᵢ instead of 2^N.

Usage
-----
    python phase1/sparse_hopfield.py --N 16 --M 4 --lam 0.05 --target-degree 6
    python phase1/sparse_hopfield.py --N 16 --dataset rrg --k 3
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
sys.path.insert(0, str(_REPO / "hardware" / "hopfield_hw" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from truth_table_gen import NeuronTruthTable


# ─────────────────────────────────────────────────────────────────────────────
# Sparse truth table
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SparseNeuronTruthTable:
    """
    Truth table for one neuron that only tracks its non-zero neighbours.

    Attributes
    ----------
    neuron_idx  : int   — global neuron index
    N           : int   — total network size
    neighbors   : list  — sorted list of neighbour indices (len = dᵢ)
    on_set      : list  — minterms (over the dᵢ local inputs) where output = 1
    """
    neuron_idx: int
    N: int
    neighbors: List[int] = field(default_factory=list)
    on_set: List[int] = field(default_factory=list)

    @property
    def degree(self) -> int:
        return len(self.neighbors)

    @property
    def lut_size(self) -> int:
        return 1 << self.degree

    def lookup(self, full_state: np.ndarray) -> int:
        """
        Given the full N-bit state, return this neuron's output bit.
        Projects full_state to the local neighborhood and looks up the table.
        """
        local_bits = tuple(int(full_state[j]) for j in self.neighbors)
        d = self.degree
        m = sum(b << (d - 1 - k) for k, b in enumerate(local_bits))
        return 1 if m in self.on_set else 0

    def to_array(self) -> np.ndarray:
        """Dense uint8 array of length 2^dᵢ; entry m = output for that local minterm."""
        arr = np.zeros(self.lut_size, dtype=np.uint8)
        for m in self.on_set:
            arr[m] = 1
        return arr


def enumerate_sparse_truth_tables(
    W: np.ndarray,
    eps: float = 1e-8,
    tie_break: int = 1,
) -> List[SparseNeuronTruthTable]:
    """
    Enumerate per-neuron update truth tables using only non-zero connections.

    Parameters
    ----------
    W         : (N, N) weight matrix (symmetric, zero diagonal)
    eps       : weights with |W_ij| <= eps are treated as zero
    tie_break : output bit when h_i == 0 exactly

    Returns
    -------
    List of N SparseNeuronTruthTable objects
    """
    W = np.asarray(W, dtype=np.float64)
    N = W.shape[0]
    tables = []

    for i in range(N):
        # Find non-zero neighbours of neuron i
        neighbors = sorted(j for j in range(N) if abs(W[i, j]) > eps)
        d = len(neighbors)
        w_local = W[i, neighbors]   # shape (d,)

        # Compute threshold: θᵢ = Σⱼ Wᵢⱼ (sum over ALL j, not just neighbors;
        # but since non-neighbors have W=0, this is just sum over neighbors)
        theta_i = float(w_local.sum())

        # Enumerate 2^d local inputs
        on_set = []
        for m in range(1 << d):
            # Decode local bits (MSB first)
            b_local = np.array([(m >> (d - 1 - k)) & 1 for k in range(d)], dtype=float)
            h_i = 2.0 * float(w_local @ b_local) - theta_i
            if h_i > 0:
                out = 1
            elif h_i < 0:
                out = 0
            else:
                out = tie_break
            if out == 1:
                on_set.append(m)

        tables.append(SparseNeuronTruthTable(
            neuron_idx=i, N=N, neighbors=neighbors, on_set=on_set
        ))

    return tables


# ─────────────────────────────────────────────────────────────────────────────
# Sparse training
# ─────────────────────────────────────────────────────────────────────────────

def train_sparse_storkey(
    patterns: np.ndarray,
    lam: float = 0.0,
    target_degree: Optional[int] = None,
    eps: float = 1e-8,
) -> np.ndarray:
    """
    Storkey learning with optional L1 soft-thresholding (ISTA-style).

    After each pattern is presented, a proximal step zeros out small weights:
        W ← sign(W) * max(|W| - lam/N, 0)

    Parameters
    ----------
    patterns      : (M, N) bipolar {-1, +1}
    lam           : L1 regularization strength (0 = no regularization)
    target_degree : if set, prune to at most this many connections per neuron
    eps           : pruning threshold

    Returns
    -------
    W : (N, N) sparse weight matrix
    """
    patterns = np.asarray(patterns, dtype=float)
    M, N = patterns.shape
    W = np.zeros((N, N))

    for p in patterns:
        h = W @ p
        W += (np.outer(p, p) - np.outer(h, p) - np.outer(p, h)) / N
        np.fill_diagonal(W, 0)

        if lam > 0:
            # Proximal operator for L1 (soft thresholding)
            threshold = lam / N
            W = np.sign(W) * np.maximum(np.abs(W) - threshold, 0)
            np.fill_diagonal(W, 0)

    if target_degree is not None:
        W = prune_to_degree(W, target_degree)

    return W


def prune_to_degree(W: np.ndarray, target_degree: int) -> np.ndarray:
    """
    Prune W so each neuron has at most target_degree non-zero connections.
    Keeps the largest |W_ij| per row (symmetric: keeps max of row and col).
    """
    N = W.shape[0]
    W_pruned = W.copy()

    for i in range(N):
        row = np.abs(W_pruned[i]).copy()
        row[i] = 0   # diagonal always zero
        if (row > 0).sum() > target_degree:
            kth = np.partition(row, -target_degree)[-target_degree]
            mask = row < kth
            W_pruned[i, mask] = 0
            W_pruned[mask, i] = 0   # keep symmetry

    return W_pruned


def verify_fixed_points(
    W: np.ndarray,
    patterns: np.ndarray,
    eps: float = 1e-8,
) -> Tuple[int, int]:
    """
    Check how many stored patterns are still exact fixed points after pruning.

    Returns (n_fixed, M)
    """
    M, N = patterns.shape
    n_fixed = 0
    for p in patterns:
        is_fp = True
        for i in range(N):
            h_i = float(W[i] @ p)
            expected = 1.0 if h_i >= 0 else -1.0
            if p[i] != expected:
                is_fp = False
                break
        if is_fp:
            n_fixed += 1
    return n_fixed, M


# ─────────────────────────────────────────────────────────────────────────────
# Sparsity reporting
# ─────────────────────────────────────────────────────────────────────────────

def sparsity_report(W: np.ndarray, eps: float = 1e-8) -> dict:
    """Report sparsity statistics and LUT sizing for a weight matrix."""
    N = W.shape[0]
    nonzero_per_row = (np.abs(W) > eps).sum(axis=1)
    sparse_lut = int(sum(2 ** int(d) for d in nonzero_per_row))
    dense_lut = N * (1 << N)
    return {
        "N": N,
        "mean_degree": float(nonzero_per_row.mean()),
        "max_degree":  int(nonzero_per_row.max()),
        "min_degree":  int(nonzero_per_row.min()),
        "degree_histogram": {
            int(d): int((nonzero_per_row == d).sum())
            for d in sorted(set(nonzero_per_row))
        },
        "sparse_lut_entries": sparse_lut,
        "dense_lut_entries":  dense_lut,
        "compression_ratio": dense_lut / max(sparse_lut, 1),
        "lut6_cells_needed":  sum(
            max(1, (2 ** int(d)) // 64)
            for d in nonzero_per_row
        ),
    }


def print_sparsity_report(report: dict) -> None:
    print(f"\nSparsity Report (N={report['N']})")
    print(f"  Degree: mean={report['mean_degree']:.1f}, "
          f"min={report['min_degree']}, max={report['max_degree']}")
    print(f"  Degree histogram: {report['degree_histogram']}")
    print(f"  Sparse LUT entries : {report['sparse_lut_entries']:,}")
    print(f"  Dense  LUT entries : {report['dense_lut_entries']:,}")
    print(f"  Compression ratio  : {report['compression_ratio']:.0f}×")
    print(f"  Approx LUT-6 cells : {report['lut6_cells_needed']:,}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sparse Hopfield training and LUT generation."
    )
    parser.add_argument("--N", type=int, default=16)
    parser.add_argument("--M", type=int, default=4, help="Patterns to store")
    parser.add_argument("--lam", type=float, default=0.0, help="L1 regularization")
    parser.add_argument("--target-degree", type=int, default=None,
                        help="Max connections per neuron after pruning")
    parser.add_argument("--dataset", type=str, default="random",
                        choices=["random", "rrg"])
    parser.add_argument("--k", type=int, default=3, help="Degree for RRG")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None,
                        help="Output dir for sparse truth tables (JSON)")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    N = args.N

    if args.dataset == "rrg":
        from datasets.loaders import random_regular_maxcut
        W, _, meta = random_regular_maxcut(N=N, k=args.k, seed=args.seed)
        patterns = None
        print(f"Random {args.k}-regular MaxCut graph, N={N}")
    else:
        patterns = rng.choice([-1.0, 1.0], size=(args.M, N))
        print(f"Training Storkey on {args.M} random patterns, N={N}, λ={args.lam}")
        W = train_sparse_storkey(patterns, lam=args.lam, target_degree=args.target_degree)

        n_fp, M = verify_fixed_points(W, patterns)
        print(f"  Stored patterns still fixed points: {n_fp}/{M}")
        if n_fp < M:
            print(f"  WARNING: {M - n_fp} patterns lost — reduce λ or relax target_degree")

    report = sparsity_report(W)
    print_sparsity_report(report)

    # Enumerate sparse truth tables
    sparse_tables = enumerate_sparse_truth_tables(W)

    print(f"\nSparse truth table sizes (2^dᵢ):")
    for tt in sparse_tables[:min(8, N)]:
        bar = "█" * tt.degree
        print(f"  neuron {tt.neuron_idx:3d}: degree={tt.degree}, "
              f"lut_size={tt.lut_size:4d}  {bar}")
    if N > 8:
        print(f"  ... ({N - 8} more neurons)")

    # Quick verification: sparse LUT agrees with dense update
    from verify_binary_encoding import run_B_binary_threshold, bipolar_to_binary

    n_agree = 0
    n_test = 20
    for _ in range(n_test):
        s0 = rng.choice([-1.0, 1.0], size=N)
        b0 = bipolar_to_binary(s0)

        bB = run_B_binary_threshold(W, b0)

        # Run sparse LUT to convergence (same termination as B)
        b_lut = b0.copy()
        for _ in range(50):
            b_prev = b_lut.copy()
            for i in range(N):
                b_lut[i] = float(sparse_tables[i].lookup(b_lut))
            if np.array_equal(b_lut, b_prev):
                break

        n_agree += np.array_equal(bB, b_lut)

    print(f"\nSparse LUT vs Binary+threshold agreement: {n_agree}/{n_test}")

    if args.out:
        import json
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "N": N,
            "sparsity": report,
            "neurons": [
                {"idx": tt.neuron_idx, "neighbors": tt.neighbors,
                 "on_set": tt.on_set, "lut_size": tt.lut_size}
                for tt in sparse_tables
            ]
        }
        out_path = out_dir / "sparse_truth_tables.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        np.save(out_dir / "W_sparse.npy", W)
        print(f"\nSaved sparse truth tables → {out_path}")
        print(f"Saved W → {out_dir / 'W_sparse.npy'}")
