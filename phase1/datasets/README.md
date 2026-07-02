# Phase 1 Datasets

All datasets used to test and verify the LUT-HNN implementation.
Listed in ascending order of N (network size required).

---

## Associative Memory (Pattern Storage)

| Dataset | N | Patterns | Source | Notes |
|---------|---|----------|--------|-------|
| Random bipolar (synthetic) | any | any | Generated | Controllable load α = M/N |
| MNIST digits (8×8 patch) | 64 | 10 | LeCun et al. 1998 | Binarized at mean pixel |
| MNIST digits (16×16) | 256 | 10–100 | LeCun et al. 1998 | Heavier; needs sparse W |
| Olivetti faces (32×32) | 1024 | 40 | AT&T Labs | Classic HNN demo |

---

## Ising / Optimization Benchmarks

These map NP-hard or physics problems to the Ising Hamiltonian
    H = -½ Σᵢⱼ Jᵢⱼ sᵢ sⱼ - Σᵢ hᵢ sᵢ
and use W = J, bias = h in the HNN.

### SK Spin Glass (Sherrington-Kirkpatrick)

| Instance | N | J distribution | Best known | Community status |
|----------|---|----------------|------------|-----------------|
| SK-N16 | 16 | Gaussian(0,1/N) | Exact (brute force) | Standard physics benchmark |
| SK-N64 | 64 | Gaussian(0,1/N) | Simulated annealing | Ising machine testbed |
| SK-N128 | 128 | Gaussian(0,1/N) | Literature values | Common in Ising papers |

**Source:** Generated locally (standard; see Sherrington & Kirkpatrick 1975).
**Why use it:** Completely connected (every J≠0), hardest random instances,
no planted solution, ground state energy density known analytically in N→∞.
Used in virtually every Ising machine paper (D-Wave, CIM, OIM, etc.).

### MAX-CUT — G-set Benchmark (Helmberg & Rendl 1998)

| Graph | N | Edges | Best known cut | Notes |
|-------|---|-------|----------------|-------|
| G1 | 800 | 19176 | 11624 | Dense random |
| G14 | 800 | 4694 | 3064 | Sparse random |
| G22 | 2000 | 19990 | 13359 | Larger |
| G55 | 5000 | 12498 | 10294 | Very large |
| Rudy-N16-d50 | 16 | ~57 | Exact | Generated; small for LUT |
| Rudy-N32-d50 | 32 | ~237 | Exact (BnB) | Generated |

**Source:** http://www.stanford.edu/~yyye/yyye/Gset/ (or generate with Rudy tool).
**Encoding to Ising:** For graph G=(V,E,w), W_ij = w_ij/2 for (i,j)∈E, else 0.
Ground state = maximum cut.
**Community status:** The G-set is THE standard MAX-CUT benchmark; every
SDP/Ising/quantum paper reports on G1 and G14 at minimum.

### Number Partitioning (NPP)

| Instance | N | Number range | Hardness |
|----------|---|-------------|---------|
| Easy partition | 16 | [1, 100] | Usually solves in 1 sweep |
| Phase-transition | 20 | [1, 2^20] | Near κ=1.0 (hardest) |
| Hard instances | 32 | [1, 2^32] | Requires many restarts |

**Encoding:** Given integers {a₁,...,aₙ}, minimize (Σᵢ aᵢ sᵢ)².
Expanding: H = Σᵢ aᵢ² - 2 Σᵢ<ⱼ aᵢaⱼ sᵢsⱼ (constant + Ising terms).
So W_ij = 2*a_i*a_j for i≠j, h_i = 0.
Ground state energy = (Σ aᵢ sᵢ)² minimized → s encodes the partition.
**User note:** As you observed, for NPP the "problem" is fully captured in W and
the initial state; HNN dynamics find the solution with no modification to the engine.

### Random 3-Regular Graphs (MaxCut)

| Instance | N | Degree | Max cut fraction | Notes |
|----------|---|--------|-----------------|-------|
| RRG-N16-k3 | 16 | 3 | ~0.875 | Generated; N must be even |
| RRG-N32-k3 | 32 | 3 | ~0.875 | Sparse, good for sparse LUT |
| RRG-N64-k3 | 64 | 3 | ~0.875 | Only 2^3=8 LUT entries/neuron! |

**Source:** Generated with networkx (random_regular_graph).
**Why use it:** Every neuron has exactly k=3 neighbors → LUT has only 2^3=8 entries.
Perfect for demonstrating sparse connectivity advantage: N=64, k=3 → 64×8 = 512
total LUT entries vs 64×2^63 for dense. The MaxCut fraction for 3-regular
random graphs is known analytically (~0.875) for comparison.

---

## Loading Examples

```python
from phase1.datasets.loaders import (
    random_bipolar_patterns,
    sk_spin_glass,
    maxcut_instance,
    number_partitioning,
    random_regular_maxcut,
    binarized_mnist,
)

# Associative memory
patterns = random_bipolar_patterns(N=16, M=3, seed=42)

# Ising optimization — returns (W, h, metadata)
W, h, meta = sk_spin_glass(N=64, seed=0)
W, h, meta = maxcut_instance('G1')            # downloads G-set
W, h, meta = number_partitioning(N=20, seed=7)
W, h, meta = random_regular_maxcut(N=32, k=3, seed=1)
```
