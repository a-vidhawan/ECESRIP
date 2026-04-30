# Training & Benchmarking

This directory contains everything for training Hopfield networks and evaluating them as associative memory. Hardware synthesis comes later — this phase is software-only.

---

## Benchmark Research Summary

### What Is Being Benchmarked?

A Hopfield network's job is **associative memory**: given a corrupted or partial input pattern, retrieve the nearest stored pattern. The benchmarks measure how well it does this.

### Standard Benchmark Protocol

The canonical benchmark used across most Hopfield network literature is:

1. **Generate random patterns**: Sample M bipolar {-1, +1} vectors of length N
2. **Train** using Hebbian or Storkey rule
3. **Test with bit-flip noise**: For each stored pattern, flip k random bits and run the network to convergence
4. **Measure**:
   - Did the network converge to the original pattern? (recall accuracy)
   - How many bits were corrupted before it failed? (basin of attraction width)
   - Did it converge to a spurious state? (spurious state rate)
   - How many update iterations to converge? (convergence speed)

### Key Capacity Results from Literature

| Rule | Reliable capacity | Quality near saturation |
|---|---|---|
| Hebbian (outer product) | M ≤ 0.138 × N | Degrades rapidly above 0.138N |
| Storkey | M ≤ ~0.14N reliable, better above | Higher quality at same loading |
| Modern Hopfield (Ramsauer 2020) | Exponential M ∝ exp(N) | Near-perfect recall; different architecture |

- **Hebbian formula:** `W = (1/N) Σ ξ_μ ξ_μ^T - I` (subtract identity to zero self-connections)
- **Storkey formula:** Incremental rule accounting for existing stored patterns; reduces cross-talk
- **Spurious states**: The network can converge to mixtures or negatives of stored patterns — these are attractors not in the training set

### Open-Source Implementations Found

| Repo | Rule | Features | Link |
|---|---|---|---|
| TomMakesThings/Hopfield-Network | Hebbian, Storkey | Capacity sweep, spurious state analysis | github.com/TomMakesThings/Hopfield-Network |
| Callum-C/HNN_Digit_Recognition | Hebbian, Storkey | MNIST/digit recognition benchmark | github.com/Callum-C/HNN_Digit_Recognition |
| takyamamoto/Hopfield-Network | Async, sync update | Visualization, convergence plots | github.com/takyamamoto/Hopfield-Network |

### Pattern Datasets

For our hardware project, the primary inputs are synthetic random ±1 patterns. However, real-world pattern tasks are also well-established:

| Dataset | N | Task | Notes |
|---|---|---|---|
| Random ±1 patterns | Any N | Capacity analysis | Primary benchmark; varies M/N ratio |
| Binary MNIST digits (8×8) | 64 | Digit recognition, noise robustness | Good for hardware demo |
| Binary MNIST digits (28×28) | 784 | Full MNIST | Too large for full enumeration (N>16 sparse needed) |
| CIFAR-10 (binarized) | 3072 | Image retrieval | Large-scale, research context |
| Graph node features (Cora/CiteSeer) | ~1433 | Graph-based associative memory | Modern Hopfield context |

**Recommended starting point:** Random ±1 patterns with N ∈ {8, 10, 12, 14, 16} and M swept from 1 to 0.3N. This directly maps to our truth table feasibility constraints.

### Benchmark Metrics Defined

```
recall_accuracy(N, M, k) = fraction of (pattern, noise_level_k) tests where
                            the network converges to the original stored pattern

basin_width(pattern_i) = maximum k such that recall_accuracy(k) > threshold (e.g., 95%)

spurious_rate(N, M) = fraction of random initializations that converge to
                       a state not in the stored pattern set (or its negative)

convergence_iters(N, M) = mean number of async update cycles to reach fixed point
```

### Benchmark Scripts Location

See `benchmarks/README.md` for the planned benchmark protocol.  
See `datasets/README.md` for dataset generation and management.

---

## Directory Layout

```
training/
├── README.md           ← this file (benchmark research summary)
├── datasets/
│   └── README.md       ← dataset catalogue and generation scripts
└── benchmarks/
    └── README.md       ← benchmark protocol, metrics, run instructions
```

---

## Getting Started

Simulation scripts will live in `sim/` once implemented. The pipeline will output truth tables, minimized SOP, and SystemVerilog ready for synthesis.
