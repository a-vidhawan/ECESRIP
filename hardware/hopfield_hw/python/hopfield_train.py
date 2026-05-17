"""
hopfield_train.py
=================
Weight-learning routines for a Hopfield associative memory.

Supported rules
---------------
* Hebbian (outer-product) rule  — classic, O(N²P) time
* Storkey rule                  — higher capacity, O(N²P) time

Neuron convention
-----------------
States are **bipolar**: s ∈ {-1, +1}.
Patterns are stored as numpy arrays of shape (N,) with entries in {-1, +1}.
The weight matrix W is (N×N), symmetric, with zero diagonal.

Usage
-----
    from hopfield_train import HopfieldNetwork
    net = HopfieldNetwork(N=8)
    net.train_hebbian(patterns)          # list of N-dim ±1 vectors
    print(net.W)                         # 8×8 float weight matrix

    # Or save/load weights
    net.save_weights("weights_8.npy")
    net2 = HopfieldNetwork.load("weights_8.npy")
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import List, Union


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class HopfieldNetwork:
    """
    A fully-connected Hopfield associative memory.

    Parameters
    ----------
    N : int
        Number of neurons (must be ≥ 2).
    """

    def __init__(self, N: int) -> None:
        if N < 2:
            raise ValueError(f"N must be ≥ 2, got {N}")
        self.N: int = N
        self.W: np.ndarray = np.zeros((N, N), dtype=np.float64)
        self._patterns: List[np.ndarray] = []

    # ------------------------------------------------------------------
    # Learning rules
    # ------------------------------------------------------------------

    def train_hebbian(self, patterns: List[np.ndarray]) -> None:
        """
        Hebbian (outer-product) learning rule.

        W ← W + (1/N) * ξ ξᵀ  for each pattern ξ
        Diagonal is zeroed after each update (no self-connections).

        Parameters
        ----------
        patterns : list of 1-D ±1 arrays of length N
        """
        patterns = [_validate_pattern(p, self.N) for p in patterns]
        W = np.zeros((self.N, self.N), dtype=np.float64)
        for xi in patterns:
            W += np.outer(xi, xi)
        W /= self.N
        np.fill_diagonal(W, 0.0)
        self.W = W
        self._patterns = list(patterns)

    def train_storkey(self, patterns: List[np.ndarray]) -> None:
        """
        Storkey learning rule.

        Achieves higher pattern capacity (~0.14 N) versus Hebbian (~0.138 N)
        with better retrieval quality near saturation.

        The update for each pattern ξ is:
            W ← W + (1/N)(ξξᵀ - hξᵀ - ξhᵀ)
        where h_i = Σ_{k≠i} W_ik ξ_k  (local field without i→i).

        Parameters
        ----------
        patterns : list of 1-D ±1 arrays of length N
        """
        patterns = [_validate_pattern(p, self.N) for p in patterns]
        W = np.zeros((self.N, self.N), dtype=np.float64)
        for xi in patterns:
            # h_i = sum_{k≠i} W_ik * xi_k
            h = W @ xi - np.diag(W) * xi          # (N,)
            dW = (np.outer(xi, xi)
                  - np.outer(h, xi)
                  - np.outer(xi, h))
            W += dW / self.N
            np.fill_diagonal(W, 0.0)
        self.W = W
        self._patterns = list(patterns)

    # ------------------------------------------------------------------
    # Retrieval (for verification / Python-side testing)
    # ------------------------------------------------------------------

    def update_async(
        self,
        state: np.ndarray,
        steps: int = 100,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """
        Asynchronous update: pick one random neuron per step, apply sign rule.

        Parameters
        ----------
        state  : initial state vector of length N, entries ±1
        steps  : total neuron update steps
        rng    : optional numpy random generator for reproducibility

        Returns
        -------
        Converged state vector.
        """
        if rng is None:
            rng = np.random.default_rng()
        s = _validate_pattern(state, self.N).astype(np.float64)
        for _ in range(steps):
            i = rng.integers(0, self.N)
            h = self.W[i] @ s
            s[i] = 1.0 if h >= 0 else -1.0
        return s.astype(np.int8)

    def update_sync(self, state: np.ndarray) -> np.ndarray:
        """
        Synchronous update: update all neurons simultaneously.

        Parameters
        ----------
        state : current state vector, entries ±1

        Returns
        -------
        Next state vector.
        """
        s = _validate_pattern(state, self.N).astype(np.float64)
        return np.sign(self.W @ s).astype(np.int8)

    def energy(self, state: np.ndarray) -> float:
        """
        Lyapunov energy  E = -½ sᵀ W s.
        Energy decreases (or stays equal) with every asynchronous update.
        """
        s = _validate_pattern(state, self.N).astype(np.float64)
        return float(-0.5 * s @ self.W @ s)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_weights(self, path: Union[str, Path]) -> None:
        """Save weight matrix to a .npy file."""
        np.save(str(path), self.W)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "HopfieldNetwork":
        """Load a network from a previously saved .npy weight file."""
        W = np.load(str(path))
        if W.ndim != 2 or W.shape[0] != W.shape[1]:
            raise ValueError("Weight file must contain a square 2-D array.")
        net = cls(W.shape[0])
        net.W = W
        return net

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def pattern_overlap(self, state: np.ndarray) -> np.ndarray:
        """
        Compute overlap m_μ = (1/N) ξ^μ · s for every stored pattern.
        Returns array of shape (P,).  Values near ±1 indicate recall.
        """
        s = _validate_pattern(state, self.N).astype(np.float64)
        return np.array(
            [(xi @ s) / self.N for xi in self._patterns], dtype=np.float64
        )

    def __repr__(self) -> str:
        return (
            f"HopfieldNetwork(N={self.N}, "
            f"patterns_stored={len(self._patterns)})"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_pattern(p: np.ndarray, N: int) -> np.ndarray:
    """Ensure p is a 1-D ±1 integer array of length N."""
    p = np.asarray(p, dtype=np.int8).ravel()
    if p.shape != (N,):
        raise ValueError(f"Pattern must have length {N}, got {p.shape}")
    if not np.all(np.abs(p) == 1):
        raise ValueError("Pattern entries must be ±1 (bipolar convention).")
    return p


def random_patterns(N: int, P: int, seed: int | None = None) -> List[np.ndarray]:
    """
    Generate P random bipolar patterns of length N.

    Parameters
    ----------
    N    : number of neurons
    P    : number of patterns
    seed : optional RNG seed

    Returns
    -------
    List of P arrays, each shape (N,), entries in {-1, +1}.
    """
    rng = np.random.default_rng(seed)
    return [
        rng.choice([-1, 1], size=N).astype(np.int8)
        for _ in range(P)
    ]


# ---------------------------------------------------------------------------
# CLI entry-point (quick smoke test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train a Hopfield network and verify recall."
    )
    parser.add_argument("--N", type=int, default=8, help="Number of neurons")
    parser.add_argument("--P", type=int, default=3, help="Number of patterns to store")
    parser.add_argument(
        "--rule", choices=["hebbian", "storkey"], default="hebbian"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None,
                        help="Save weights to this .npy file")
    args = parser.parse_args()

    patterns = random_patterns(args.N, args.P, seed=args.seed)
    net = HopfieldNetwork(args.N)

    if args.rule == "hebbian":
        net.train_hebbian(patterns)
    else:
        net.train_storkey(patterns)

    print(f"Trained {net} via {args.rule} rule.")
    print(f"Weight matrix:\n{net.W}\n")

    rng = np.random.default_rng(args.seed + 1)
    for idx, xi in enumerate(patterns):
        # Corrupt one bit
        noisy = xi.copy()
        flip_idx = rng.integers(0, args.N)
        noisy[flip_idx] = -noisy[flip_idx]
        recovered = net.update_async(noisy, steps=10 * args.N, rng=rng)
        match = np.array_equal(recovered, xi)
        print(
            f"  Pattern {idx}: flip bit {flip_idx} → "
            f"{'✓ recalled' if match else '✗ missed'}"
            f"  (overlap={net.pattern_overlap(recovered)[idx]:.3f})"
        )

    if args.out:
        net.save_weights(args.out)
        print(f"\nWeights saved to {args.out}")
