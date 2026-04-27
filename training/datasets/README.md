# Datasets

## Primary: Synthetic Random Patterns

The core dataset for our benchmarks. Generated programmatically — no download needed.

```python
import numpy as np

def random_patterns(N, M, seed=42):
    """Generate M random bipolar {-1, +1} patterns of length N."""
    rng = np.random.default_rng(seed)
    return rng.choice([-1, 1], size=(M, N))
```

**Parameters to sweep:**
- N ∈ {4, 6, 8, 10, 12, 14, 16} (feasibility limited by 2^N truth table)
- M ∈ {1, 2, ..., floor(0.3 × N)} (beyond 0.14N to study saturation regime)
- Noise levels k ∈ {1, 2, ..., N//2} (number of bits flipped)

---

## Secondary: Binary MNIST (for demo / hardware validation)

8×8 downsampled binary MNIST digits make a nice N=64 demo. At N=64, full truth table enumeration is impossible — this would require the sparse connectivity approach (F strongest weights).

```python
# Binarize 8x8 MNIST
from sklearn.datasets import load_digits
import numpy as np

digits = load_digits()
X = digits.data  # shape (1797, 64), values 0-16
X_binary = np.where(X > 8, 1, -1)  # bipolar binarization
```

**Use case:** Once sparse connectivity is implemented, test on 10 digit classes (one pattern per class) with handwritten digit inputs as queries.

---

## Notes on Dataset Size vs Hardware Feasibility

| N | Max full-enum M (Hebbian 0.14N) | Truth table size | Hardware path |
|---|---|---|---|
| 8 | 1 | 256 rows | Distributed LUT |
| 10 | 1 | 1,024 rows | Distributed LUT |
| 12 | 1 | 4,096 rows | Distributed LUT or BRAM |
| 14 | 1-2 | 16,384 rows | BRAM |
| 16 | 2 | 65,536 rows | BRAM (borderline) |
| 64 | 8 | 2^64 (impossible) | Sparse F-LUT (F ≤ 10) |

For N > 16: keep only the F largest-magnitude weights per neuron, reducing truth table to 2^F rows.
