# Phase 1 — LUT-HNN Verification & Encoding

## Goal

Verify that the core mathematical claim of LUT-HNN is correct **before** touching any hardware:

> Replacing {-1,+1} bipolar neurons with {0,1} binary neurons (with an implicit threshold)
> produces identical attractor dynamics — and that the precomputed truth-table LUT
> captures this exactly.

## Structure

```
phase1/
├── README.md                   ← this file
├── verify_binary_encoding.py   ← 4-way simulator comparison (main verification)
├── hnn_to_truth_table.py       ← end-to-end: train HNN → export truth tables
├── sparse_hopfield.py          ← L1-regularized sparse training + sparse LUT gen
├── encoding_theory.md          ← math derivation of {0,1}↔{-1,+1} equivalence
├── sparse_connectivity.md      ← theory + scaling analysis for sparse W
└── datasets/
    ├── README.md               ← dataset catalog with N, source, benchmark status
    └── loaders.py              ← loaders for all benchmark datasets
```

## Quick Start

```bash
# 1. Verify binary encoding is equivalent to bipolar (must pass all assertions)
python phase1/verify_binary_encoding.py

# 2. Train on a dataset and export truth tables
python phase1/hnn_to_truth_table.py --dataset mnist8 --out phase1/out/

# 3. Explore sparse connectivity tradeoffs
python phase1/sparse_hopfield.py --N 16 --patterns 4 --lam 0.05
```

## The Four Simulators (verify_binary_encoding.py)

| Label | Description | Expected |
|-------|-------------|----------|
| **A** | Bipolar {-1,+1}, existing `hopfield_net.py` | Ground truth |
| **B** | Binary {0,1} + threshold θᵢ = ½ΣⱼWᵢⱼ | Must match A exactly |
| **C** | Binary {0,1}, no threshold (naive) | **Wrong** — different attractors |
| **D** | LUT lookup via `truth_table_gen.py` | Must match A and B exactly |

The verification trains on identical patterns, runs all four from identical noisy
initial states, and asserts A == B == D while reporting that C diverges.

## Ising/Optimization Connection

For NP-hard problems mapped to Ising Hamiltonians:

    H = -½ Σᵢⱼ Jᵢⱼ sᵢ sⱼ  (s ∈ {-1,+1})

The HNN weight matrix is simply **W = J**. Finding the ground state of H is
equivalent to finding a fixed-point attractor of the HNN.  The same LUT
truth-table approach applies: precompute each neuron's update function from J,
burn it into LUTs, and let the cyclic combinational circuit settle.

Problems supported in `datasets/loaders.py`:
- SK spin glass (random Gaussian J) — physics benchmark
- MAX-CUT on G-set graphs — combinatorial optimization benchmark
- Number Partitioning — NP-complete, direct Ising encoding
- Random 3-regular graphs — controlled graph structure
- Binarized MNIST — associative memory benchmark
