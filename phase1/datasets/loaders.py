"""
phase1/datasets/loaders.py
==========================
Loaders for all benchmark datasets used in Phase 1 verification.

Each Ising/optimization loader returns  (W, h, meta)  where:
    W    : (N, N) float64  — symmetric weight matrix, zero diagonal
    h    : (N,)   float64  — per-neuron bias (often zero)
    meta : dict            — dataset info (name, N, best-known values, etc.)

The associative memory loader returns:
    patterns : (M, N) float64 in {-1, +1}

All datasets are either generated locally (no download needed) or fetched
from well-known public URLs on first use (cached in phase1/datasets/cache/).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False

try:
    from sklearn.datasets import fetch_olivetti_faces
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

WMatrix  = np.ndarray  # (N, N)
BiasVec  = np.ndarray  # (N,)
Meta     = Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# Associative memory
# ─────────────────────────────────────────────────────────────────────────────

def random_bipolar_patterns(
    N: int,
    M: int,
    seed: int = 0,
) -> np.ndarray:
    """
    Generate M random bipolar patterns of length N.

    Parameters
    ----------
    N : int  — number of neurons
    M : int  — number of patterns to store
    seed : int

    Returns
    -------
    patterns : (M, N) array in {-1, +1}
    """
    rng = np.random.default_rng(seed)
    return rng.choice([-1.0, 1.0], size=(M, N))


def binarized_mnist(
    patch_size: int = 8,
    n_patterns: Optional[int] = None,
) -> Tuple[np.ndarray, Meta]:
    """
    Load binarized MNIST patterns (one per class 0-9).

    Requires scikit-learn (pip install scikit-learn).

    Parameters
    ----------
    patch_size : {8, 16, 28}
        Edge length of the square patch. N = patch_size².
        8  → N=64   (LUT feasible for small N, good demo)
        16 → N=256  (needs sparse W)
        28 → N=784  (full MNIST; dense LUT impractical)
    n_patterns : int or None
        How many patterns to return (default: one per digit class, 10 total).

    Returns
    -------
    patterns : (n_patterns, N) array in {-1, +1}
    meta     : dict with N, patch_size, notes
    """
    try:
        from sklearn.datasets import fetch_openml
        mnist = fetch_openml('mnist_784', version=1, as_frame=False, parser='liac-arff')
        X, y = mnist.data.astype(np.float32), mnist.target.astype(int)
    except Exception as e:
        raise RuntimeError(
            "Could not load MNIST via sklearn. "
            "Install with: pip install scikit-learn\n"
            f"Original error: {e}"
        ) from e

    N = patch_size * patch_size
    n_patterns = n_patterns or 10

    patterns = []
    for digit in range(min(n_patterns, 10)):
        idx = np.where(y == digit)[0][0]
        img = X[idx].reshape(28, 28)
        # Downsample / crop to patch_size × patch_size
        if patch_size < 28:
            step = 28 // patch_size
            img = img[::step, ::step][:patch_size, :patch_size]
        # Binarize at mean
        threshold = img.mean()
        p = np.where(img.flatten() > threshold, 1.0, -1.0)[:N]
        patterns.append(p)

    patterns = np.array(patterns)
    meta = {
        "name": f"MNIST-{patch_size}x{patch_size}",
        "N": N,
        "patch_size": patch_size,
        "n_patterns": len(patterns),
        "notes": "Binarized at per-image mean pixel value",
    }
    return patterns, meta


# ─────────────────────────────────────────────────────────────────────────────
# SK Spin Glass
# ─────────────────────────────────────────────────────────────────────────────

def sk_spin_glass(
    N: int,
    seed: int = 0,
    J_scale: float = 1.0,
) -> Tuple[WMatrix, BiasVec, Meta]:
    """
    Sherrington-Kirkpatrick (SK) spin glass instance.

    Couplings J_ij drawn i.i.d. from N(0, J²/N) with J=J_scale.
    The Hamiltonian is H = -Σ_{i<j} J_ij s_i s_j (fully connected).

    Standard benchmark in virtually every Ising machine paper.
    Ground state energy density approaches -0.7633*J as N→∞ (Parisi).

    Parameters
    ----------
    N       : number of spins
    seed    : RNG seed (different seeds = independent problem instances)
    J_scale : coupling scale (default 1.0)

    Returns
    -------
    W    : (N, N) symmetric weight matrix  (W_ij = J_ij for i≠j, 0 on diagonal)
    h    : (N,) bias vector (zero for SK)
    meta : dataset metadata
    """
    rng = np.random.default_rng(seed)
    # Draw upper triangle
    J_upper = rng.standard_normal(size=(N, N)) * J_scale / np.sqrt(N)
    W = np.triu(J_upper, k=1)
    W = W + W.T   # symmetrize
    h = np.zeros(N)

    meta = {
        "name": f"SK-N{N}-seed{seed}",
        "N": N,
        "seed": seed,
        "J_scale": J_scale,
        "type": "sk_spin_glass",
        "fully_connected": True,
        "parisi_energy_density": -0.7633 * J_scale,   # thermodynamic limit
        "notes": "J_ij ~ N(0, J²/N); ground state unknown for finite N",
    }
    return W, h, meta


# ─────────────────────────────────────────────────────────────────────────────
# MAX-CUT — G-set benchmark
# ─────────────────────────────────────────────────────────────────────────────

# Known best cuts for standard G-set instances (Helmberg & Rendl 1998 + literature)
GSET_BEST_KNOWN: Dict[str, int] = {
    'G1':  11624, 'G2':  11620, 'G3':  11622, 'G4':  11646, 'G5':  11631,
    'G6':  2178,  'G7':  2006,  'G8':  2005,  'G9':  2054,  'G10': 2000,
    'G11': 564,   'G12': 556,   'G13': 582,   'G14': 3064,  'G22': 13359,
    'G55': 10294,
}

_GSET_BASE_URL = "https://web.stanford.edu/~yyye/yyye/Gset/"


def maxcut_instance(
    name: str = 'G1',
    force_download: bool = False,
) -> Tuple[WMatrix, BiasVec, Meta]:
    """
    Load a G-set MAX-CUT benchmark instance.

    G-set (Helmberg & Rendl 1998) is THE standard MAX-CUT benchmark.
    Every SDP, Ising machine, and quantum algorithm paper reports G1 and G14.

    Encoding to Ising/HNN:
        W_ij = w_ij / 2  for each edge (i,j) with weight w_ij
        h_i  = 0
    Maximizing the cut is equivalent to minimizing -½ Σ w_ij (1 - s_i s_j),
    which is the same as minimizing H = -½ sᵀ W s.

    Parameters
    ----------
    name           : G-set instance name, e.g. 'G1', 'G14', 'G22'
    force_download : re-download even if cached

    Returns
    -------
    W, h, meta
    """
    cache_path = CACHE_DIR / f"{name}.txt"

    if not cache_path.exists() or force_download:
        url = f"{_GSET_BASE_URL}{name}"
        try:
            print(f"Downloading {name} from {url} …")
            urllib.request.urlretrieve(url, cache_path)
        except Exception as e:
            raise RuntimeError(
                f"Could not download G-set instance '{name}'. "
                f"Download manually from {url} and place at {cache_path}\n"
                f"Original error: {e}"
            ) from e

    # Parse G-set format: first line is "N M", then M lines of "u v w"
    with open(cache_path) as f:
        lines = f.read().splitlines()

    first = lines[0].split()
    N, M_edges = int(first[0]), int(first[1])
    W = np.zeros((N, N))

    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        u, v = int(parts[0]) - 1, int(parts[1]) - 1   # 1-indexed in file
        w = float(parts[2]) if len(parts) > 2 else 1.0
        W[u, v] += w / 2.0
        W[v, u] += w / 2.0

    h = np.zeros(N)
    best = GSET_BEST_KNOWN.get(name)

    meta = {
        "name": name,
        "N": N,
        "edges": M_edges,
        "type": "maxcut_gset",
        "best_known_cut": best,
        "notes": "Helmberg & Rendl 1998; W_ij = edge_weight/2",
    }
    return W, h, meta


def _make_gset_small(N: int = 16, density: float = 0.5, seed: int = 0) -> Tuple[WMatrix, BiasVec, Meta]:
    """
    Generate a small random weighted MaxCut instance for quick testing
    (same encoding as G-set but synthetic, so exact solution is brute-forceable).
    """
    if not _HAS_NX:
        rng = np.random.default_rng(seed)
        W = np.zeros((N, N))
        for i in range(N):
            for j in range(i + 1, N):
                if rng.random() < density:
                    w = float(rng.integers(1, 10))
                    W[i, j] = W[j, i] = w / 2.0
    else:
        import networkx as nx
        G = nx.erdos_renyi_graph(N, density, seed=seed)
        W = np.zeros((N, N))
        for u, v in G.edges():
            W[u, v] = W[v, u] = 0.5

    h = np.zeros(N)
    meta = {"name": f"MaxCut-N{N}-d{density:.0%}-seed{seed}", "N": N,
            "type": "maxcut_random", "exact_solvable": N <= 20}
    return W, h, meta


# ─────────────────────────────────────────────────────────────────────────────
# Number Partitioning (NP-complete)
# ─────────────────────────────────────────────────────────────────────────────

def number_partitioning(
    N: int,
    seed: int = 0,
    number_range: Optional[Tuple[int, int]] = None,
    hardness: str = 'easy',
) -> Tuple[WMatrix, BiasVec, Meta]:
    """
    Number Partitioning Problem encoded as an Ising/HNN instance.

    Goal: partition integers {a₁,…,aₙ} into two groups S⁺ and S⁻
    to minimize |Σ_{i∈S⁺} aᵢ - Σ_{i∈S⁻} aᵢ|.

    Ising encoding (Mertens 1998, Lucas 2014):
        H = (Σᵢ aᵢ sᵢ)²  where sᵢ ∈ {-1,+1}
          = Σᵢ aᵢ² + 2 Σᵢ<ⱼ aᵢaⱼ sᵢsⱼ
    So W_ij = -2*aᵢ*aⱼ for i≠j (the - sign because we MAXIMIZE -H).
    h_i = 0.  Ground state → minimum partition difference.

    Hardness parameter κ = N * log₂(max_a) / N (Borgs et al. 2001):
        κ < 1  → easy (solution exists with high prob)
        κ ≈ 1  → phase transition (hardest)
        κ > 1  → hard (perfect partition unlikely)

    Parameters
    ----------
    N           : number of integers to partition
    seed        : RNG seed
    number_range: (min, max) for random integers (default depends on hardness)
    hardness    : 'easy' | 'phase_transition' | 'hard'

    Returns
    -------
    W, h, meta  (meta includes the integer list `a` for verification)
    """
    rng = np.random.default_rng(seed)

    if number_range is None:
        if hardness == 'easy':
            number_range = (1, 100)
        elif hardness == 'phase_transition':
            number_range = (1, 2 ** N)   # κ ≈ 1 at this range
        else:
            number_range = (1, 2 ** (2 * N))

    a = rng.integers(number_range[0], number_range[1], size=N).astype(float)

    # W_ij = -2 * a_i * a_j (coupling that penalizes same sign = same partition)
    W = -2.0 * np.outer(a, a)
    np.fill_diagonal(W, 0)

    h = np.zeros(N)

    # Check if perfect partition exists (brute force only feasible for small N)
    perfect_exists = None
    if N <= 20:
        best_diff = float('inf')
        for mask in range(1 << N):
            s = np.array([(1 if (mask >> k) & 1 else -1) for k in range(N)])
            diff = abs(float(a @ s))
            if diff < best_diff:
                best_diff = diff
        perfect_exists = best_diff == 0

    meta = {
        "name": f"NPP-N{N}-{hardness}-seed{seed}",
        "N": N,
        "integers": a.tolist(),
        "sum": float(a.sum()),
        "hardness": hardness,
        "number_range": list(number_range),
        "perfect_partition_exists": perfect_exists,
        "notes": "W_ij = -2*a_i*a_j; ground state = minimum partition difference",
    }
    return W, h, meta


# ─────────────────────────────────────────────────────────────────────────────
# Random Regular Graphs — MaxCut
# ─────────────────────────────────────────────────────────────────────────────

def random_regular_maxcut(
    N: int,
    k: int = 3,
    seed: int = 0,
) -> Tuple[WMatrix, BiasVec, Meta]:
    """
    MAX-CUT on a random k-regular graph.

    Why this matters for LUT-HNN:
        Every neuron has exactly k neighbours → LUT has only 2^k entries.
        For k=3: 8 entries per neuron regardless of N.
        Demonstrates the sparse connectivity scaling advantage directly.

    Expected MaxCut fraction for k-regular random graphs:
        k=3 → ~0.875  (known analytically; Dembo et al. 2017)
        k=4 → ~0.850
        k=5 → ~0.829

    Requires: networkx (pip install networkx)

    Parameters
    ----------
    N    : number of nodes (must be even for k odd with k*N even)
    k    : degree of each node
    seed : RNG seed

    Returns
    -------
    W, h, meta
    """
    if not _HAS_NX:
        raise ImportError("networkx is required: pip install networkx")

    import networkx as nx
    G = nx.random_regular_graph(k, N, seed=seed)

    W = np.zeros((N, N))
    for u, v in G.edges():
        W[u, v] = W[v, u] = 0.5    # w=1 edge, MaxCut encoding W_ij = w/2

    h = np.zeros(N)

    # Adjacency list for sparse LUT generation
    neighbors = {i: sorted(G.neighbors(i)) for i in range(N)}

    meta = {
        "name": f"RRG-N{N}-k{k}-seed{seed}",
        "N": N,
        "k": k,
        "edges": G.number_of_edges(),
        "type": "maxcut_regular",
        "lut_entries_per_neuron": 2 ** k,
        "total_lut_entries": N * (2 ** k),
        "expected_cut_fraction": {3: 0.875, 4: 0.850, 5: 0.829}.get(k),
        "neighbors": neighbors,
        "notes": f"Each neuron has exactly {k} neighbours → {2**k}-entry LUT",
    }
    return W, h, meta


# ─────────────────────────────────────────────────────────────────────────────
# Brute-force ground state (small N only)
# ─────────────────────────────────────────────────────────────────────────────

def brute_force_ground_state(
    W: np.ndarray,
    h: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, float]:
    """
    Find the exact ground state by exhaustive search.

    Feasible only for N ≤ 20-22. Returns bipolar {-1,+1} state.

    H(s) = -½ sᵀWs - hᵀs
    """
    N = W.shape[0]
    if N > 24:
        raise ValueError(f"N={N} too large for brute force (max ~24).")
    if h is None:
        h = np.zeros(N)

    best_E = float('inf')
    best_s = None

    for mask in range(1 << N):
        s = np.array([(1.0 if (mask >> i) & 1 else -1.0) for i in range(N)])
        E = -0.5 * float(s @ W @ s) - float(h @ s)
        if E < best_E:
            best_E = E
            best_s = s.copy()

    return best_s, best_E


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: list all available datasets
# ─────────────────────────────────────────────────────────────────────────────

def list_datasets() -> None:
    """Print a summary of all available datasets."""
    print("=" * 60)
    print("Phase 1 Datasets")
    print("=" * 60)
    print()
    print("Associative Memory:")
    print("  random_bipolar_patterns(N, M, seed)")
    print("  binarized_mnist(patch_size={8,16,28})")
    print()
    print("Ising / Optimization:")
    print("  sk_spin_glass(N, seed)           — SK spin glass")
    print("  maxcut_instance(name)            — G-set (G1, G14, G22, ...)")
    print("  number_partitioning(N, hardness) — NPP (NP-complete)")
    print("  random_regular_maxcut(N, k)      — k-regular MaxCut")
    print()
    print("Utilities:")
    print("  brute_force_ground_state(W, h)   — exact solution (N ≤ 22)")
    print()
    print("G-set instances available:", list(GSET_BEST_KNOWN.keys()))


if __name__ == "__main__":
    list_datasets()

    print("\n--- Quick smoke test ---\n")
    # Associative memory
    p = random_bipolar_patterns(N=16, M=3, seed=42)
    print(f"Random patterns: {p.shape}, values in {set(p.flatten())}")

    # SK spin glass
    W, h, meta = sk_spin_glass(N=16, seed=0)
    print(f"SK N=16: W.shape={W.shape}, ||W||_F={np.linalg.norm(W):.3f}")

    # NPP
    W_npp, h_npp, meta_npp = number_partitioning(N=8, seed=0, hardness='easy')
    gs, E = brute_force_ground_state(W_npp)
    diff = abs(float(np.array(meta_npp['integers']) @ gs))
    print(f"NPP N=8: ground state diff={diff:.0f}, energy={E:.2f}")

    # RRG
    try:
        W_rrg, h_rrg, meta_rrg = random_regular_maxcut(N=16, k=3, seed=0)
        print(f"RRG N=16 k=3: {meta_rrg['edges']} edges, "
              f"{meta_rrg['lut_entries_per_neuron']} LUT entries/neuron")
    except ImportError:
        print("Skipping RRG test (networkx not installed)")
