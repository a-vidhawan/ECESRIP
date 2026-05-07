"""
Dataset utilities for Hopfield network benchmarking.

Supported datasets
------------------
RANDOM   : random ±1 patterns            (any N)
MNIST_8  : binarized MNIST at 8×8        (N=64)
MNIST_28 : binarized MNIST at 28×28      (N=784)

All loaders return (M, N) arrays with values in {-1, +1}.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path

# ── dataset type constants ────────────────────────────────────────────────────
RANDOM   = 'random'    # random bipolar patterns — primary capacity benchmark
MNIST_8  = 'mnist_8'   # MNIST downsampled to 8×8  (64 neurons)
MNIST_28 = 'mnist_28'  # MNIST full resolution 28×28 (784 neurons)

_CACHE_DIR = Path(__file__).parent.parent / 'data'

# ── public API ────────────────────────────────────────────────────────────────

def load(dataset: str, N: int, M: int, seed: int = 0) -> np.ndarray:
    """
    Load M patterns of length N from the requested dataset.

    Parameters
    ----------
    dataset : one of RANDOM, MNIST_8, MNIST_28
    N       : pattern length (neurons). Ignored for MNIST_* (fixed by resolution).
    M       : number of patterns to return
    seed    : random seed for reproducibility

    Returns
    -------
    patterns : (M, N) array with values in {-1, +1}
    """
    if dataset == RANDOM:
        return random_patterns(N, M, seed)
    if dataset == MNIST_8:
        return _mnist(M, target_size=8, seed=seed)
    if dataset == MNIST_28:
        return _mnist(M, target_size=28, seed=seed)
    raise ValueError(f"Unknown dataset '{dataset}'. Use RANDOM, MNIST_8, or MNIST_28.")


def random_patterns(N: int, M: int, seed: int = 0) -> np.ndarray:
    """M random bipolar patterns of length N."""
    rng = np.random.default_rng(seed)
    return rng.choice([-1.0, 1.0], size=(M, N))


def add_noise(pattern: np.ndarray, n_flips: int, rng: np.random.Generator) -> np.ndarray:
    """
    Return a copy of pattern with n_flips bits randomly flipped.

    Parameters
    ----------
    pattern : (N,) bipolar array
    n_flips : number of bits to flip
    rng     : numpy Generator for reproducibility
    """
    noisy = pattern.copy()
    idx = rng.choice(len(pattern), size=n_flips, replace=False)
    noisy[idx] *= -1
    return noisy


def dataset_N(dataset: str, target_size: int | None = None) -> int:
    """Return the neuron count N for a given dataset type."""
    if dataset == RANDOM:
        if target_size is None:
            raise ValueError("Must supply target_size for RANDOM dataset.")
        return target_size
    if dataset == MNIST_8:
        return 64
    if dataset == MNIST_28:
        return 784
    raise ValueError(f"Unknown dataset '{dataset}'.")


# ── MNIST loader ──────────────────────────────────────────────────────────────

def _mnist(M: int, target_size: int, seed: int) -> np.ndarray:
    """
    Load MNIST, binarize (threshold at pixel mean), downsample to target_size×target_size,
    return M randomly selected patterns as bipolar {-1, +1} vectors.

    Requires: scikit-learn  (pip install scikit-learn)
    Downloads MNIST on first call and caches to sim/data/.
    """
    try:
        from sklearn.datasets import fetch_openml
    except ImportError:
        raise ImportError(
            "scikit-learn is required for MNIST loading.\n"
            "Install with:  pip install scikit-learn"
        )

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / f'mnist_{target_size}.npy'

    if cache_file.exists():
        all_patterns = np.load(cache_file)
    else:
        print(f"Downloading MNIST and building {target_size}×{target_size} binary cache…")
        mnist = fetch_openml('mnist_784', version=1, as_frame=False,
                             data_home=str(_CACHE_DIR), parser='auto')
        X = mnist.data.astype(np.float32)  # (70000, 784)

        if target_size != 28:
            X = _downsample(X, target_size)  # (70000, target_size²)

        # binarize: threshold at per-image mean, map to {-1, +1}
        thresholds = X.mean(axis=1, keepdims=True)
        all_patterns = np.where(X >= thresholds, 1.0, -1.0)
        np.save(cache_file, all_patterns)
        print(f"Cached {len(all_patterns)} patterns to {cache_file}")

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(all_patterns), size=min(M, len(all_patterns)), replace=False)
    return all_patterns[idx]


def _downsample(X: np.ndarray, target_size: int) -> np.ndarray:
    """
    Downsample each 28×28 MNIST image to target_size×target_size via block averaging.
    X : (n_samples, 784)
    Returns (n_samples, target_size²)
    """
    from skimage.transform import resize as sk_resize
    try:
        n = X.shape[0]
        out = np.empty((n, target_size * target_size), dtype=np.float32)
        for i in range(n):
            img = X[i].reshape(28, 28)
            img_small = sk_resize(img, (target_size, target_size),
                                  anti_aliasing=True, mode='reflect')
            out[i] = img_small.ravel()
        return out
    except ImportError:
        # fallback: simple block average without scikit-image
        n = X.shape[0]
        block = 28 // target_size
        out = np.empty((n, target_size * target_size), dtype=np.float32)
        imgs = X.reshape(n, 28, 28)
        for r in range(target_size):
            for c in range(target_size):
                block_vals = imgs[:, r*block:(r+1)*block, c*block:(c+1)*block]
                out[:, r*target_size + c] = block_vals.mean(axis=(1, 2))
        return out
