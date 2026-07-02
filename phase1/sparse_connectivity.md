# Sparse Connectivity in LUT-HNN

## The Scaling Problem

The fundamental barrier to large-N LUT-HNN is the truth table size:

```
Dense network, neuron i: 2^N entries  (all N inputs matter)
```

For N=16: 32,768 entries — feasible on Basys 3 (BRAM).
For N=20: 524,288 entries — tight.
For N=24: 16M entries — impractical.
For N=64: 2^64 ≈ 10^19 — physically impossible.

**Sparse connectivity is the only path to large N.**

---

## The Key Insight: Local Inputs Only

If neuron i is connected to only dᵢ other neurons (Wᵢⱼ ≠ 0 for only dᵢ values of j),
then the truth table for neuron i depends only on those dᵢ inputs:

```
Sparse truth table, neuron i: 2^dᵢ entries  (only dᵢ inputs matter)
```

The remaining N - dᵢ inputs are irrelevant — they don't affect hᵢ at all.

### Example: Random 3-Regular Graph MaxCut

- N = 64 neurons, each with exactly k = 3 neighbors
- Dense LUT: 2^63 entries per neuron — impossible
- Sparse LUT: 2^3 = 8 entries per neuron — trivial
- Total LUT entries: 64 × 8 = 512 — fits in a handful of 6-LUTs

This is why `random_regular_maxcut(N=64, k=3)` is in the benchmark suite.

---

## Formal Definition

For a weight matrix W with zero diagonal, define:

```
Nᵢ = { j : Wᵢⱼ ≠ 0 }   (neighborhood of neuron i)
dᵢ = |Nᵢ|               (degree of neuron i)
```

The sparse truth table for neuron i has:
- **Input variables**: bits b_j for j ∈ Nᵢ (ordered by index)
- **Size**: 2^dᵢ rows
- **Entry at row m**: output bit for the subset state encoded by m

The full state b ∈ {0,1}^N is projected to b[Nᵢ] ∈ {0,1}^dᵢ before table lookup.

---

## Hardware Mapping

Each LUT-6 primitive on a Xilinx FPGA has 6 inputs and 1 output = 64 entries.
For a neuron with dᵢ inputs:

| dᵢ | LUT entries | LUT-6 cells needed |
|----|-------------|---------------------|
| 1  | 2           | 1                   |
| 3  | 8           | 1                   |
| 6  | 64          | 1 (fits exactly)    |
| 7  | 128         | 2                   |
| 10 | 1,024       | 16                  |
| 12 | 4,096       | 64                  |
| 16 | 65,536      | 1,024               |

For N=64 with k=10: 64 × 16 = 1,024 LUT-6 cells.
Basys 3 has 20,800 LUT-6 cells — room for ~20 such networks simultaneously.

---

## How to Achieve Sparsity

### Option 1: Problem Structure (Best)

Many problems already have sparse structure:
- **k-regular graphs**: MaxCut on 3-regular graphs → dᵢ = 3 for all i
- **Grid/lattice graphs**: 2D Ising model → dᵢ = 4
- **Sparse SK instances**: truncate small |Wᵢⱼ| below threshold

### Option 2: L1-Regularized Training (Learned Sparsity)

During training, add an L1 penalty to push small weights to exactly zero:

```
W* = argmin  training_loss(W) + λ ‖W‖₁
```

After training, zero out |Wᵢⱼ| < ε (hardware threshold).

For associative memory: use Storkey + L1 proximal step.
See `sparse_hopfield.py` for implementation.

### Option 3: Structured Pruning

Train dense, then iteratively zero out the smallest |Wᵢⱼ| while checking
that stored patterns remain fixed points. Stop when dᵢ ≤ d_target.

---

## Capacity vs Sparsity Tradeoff

For the Hopfield network, the classic capacity is:
```
M_max ≈ 0.14 N    (Hebbian rule, dense)
M_max ≈ 0.60 N    (Storkey rule, dense)
```

With sparsity (degree k per neuron), capacity scales roughly as:
```
M_max ≈ c * k / log(N)   (Hopfield 1982 sparse bound)
```

So for N=64, k=10: M_max ~ 10/6 ≈ 1-2 patterns reliably.
For N=64, k=16: M_max ~ 16/6 ≈ 2-3 patterns.

The tradeoff: more patterns → denser W → bigger LUTs.

For **optimization problems** (Ising/MaxCut/NPP), sparsity is determined by
the problem structure, not by the number of patterns. The "capacity" concept
doesn't apply — there's only one Hamiltonian to minimize.

---

## Measuring Sparsity in Practice

```python
import numpy as np

def sparsity_report(W: np.ndarray, eps: float = 1e-8) -> dict:
    N = W.shape[0]
    nonzero_per_row = (np.abs(W) > eps).sum(axis=1)
    return {
        "N": N,
        "mean_degree": float(nonzero_per_row.mean()),
        "max_degree":  int(nonzero_per_row.max()),
        "min_degree":  int(nonzero_per_row.min()),
        "total_lut_entries": int(sum(2**d for d in nonzero_per_row)),
        "dense_lut_entries": N * (1 << N),
        "compression_ratio": N * (1 << N) / sum(2**d for d in nonzero_per_row),
    }
```

---

## References

- Hopfield, J.J. (1982). "Neural networks and physical systems…" PNAS. (sparse capacity bound)
- Storkey, A. (1997). "Increasing the capacity of a Hopfield network without sacrificing functionality." ICANN.
- Dembo, A., Montanari, A., Sen, S. (2017). "Extremal cuts of sparse random graphs." Annals of Probability. (MaxCut on regular graphs)
- Lucas, A. (2014). "Ising formulations of many NP problems." Frontiers in Physics. (sparse Ising problems)
