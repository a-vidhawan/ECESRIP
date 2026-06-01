# Meeting Notes — June 1, 2026

**Agenda: Gradient-Based HNN Training + Ising Machine NP-Hard Datasets**

---

## 1. Gradient-Based Training Methods for HNNs

### Why go beyond Hebbian?
Hebbian stores only ~0.138N patterns and has no way to fix mistakes. Gradient-based methods treat W as a learnable parameter and optimise a loss — giving higher capacity, supervised learning, and a path to FPGA-trainable hardware.

---

### A. Perceptron SGD / Three-Threshold Rule *(implement first)*
**Core idea:** Write down a loss that is positive whenever a stored pattern is *not* a fixed point. For every neuron i in every pattern ξ, check whether it got the right sign from its local field h_i = W_i · ξ. If not, add a Hebbian correction. That's it.

- Achieves the **Gardner bound: ~0.64N capacity** — more than 4× Hebbian
- Update is a single margin check (one-bit compare) → simple on-chip FSM, no extra hardware
- Online and incremental: can update W after every new pattern
- Three-threshold variant (Alemi et al. 2015, PLoS Comp. Bio.) adds a forgetting term to push the network to the true optimum and approaches the theoretical maximum

**On our FPGA:** the margin check lives in the same pipeline as the async settle. Training = settle + compare + accumulate. No second phase needed.

---

### B. Equilibrium Propagation (Scellier & Bengio, 2017)
**Core idea:** Run the network free until it settles — that's the *free phase* (s\*). Then gently nudge the output neurons toward the target answer by adding a small cost β·C(s,y) to the energy and settle again — that's the *clamped phase* (s^β). The weight gradient is the difference of outer products between the two settled states, divided by β.

- Mathematically proven to compute the **exact backprop gradient** using only local, Hebbian-style updates — no explicit error signal wired through the network
- Both phases **reuse the existing async settle circuit** — zero additional hardware cost for supervised training
- For binary neurons the two settled states differ in only a few bit positions → XOR logic for the weight increment
- EqSpike (Laydevant et al. 2021, neuromorphic silicon): 2–3 orders of magnitude lower energy per training step than GPU
- Supports any symmetric energy function, not just quadratic — future-proof for modern/dense Hopfield variants

**On our FPGA:** phase 1 = normal inference. Phase 2 = inference with clamped output bits. Weight BRAM accumulates the XOR difference. β can be a fixed hardware constant.

---

### C. Minimum Probability Flow (MPF, Sohl-Dickstein et al. 2011)
**Core idea:** Treat the HNN as a probability model p(s) ∝ exp(−E(s)/T). For every stored pattern, every single-bit-flip neighbour should have *higher* energy. MPF minimises the probability that the system would spontaneously "flow" out of a training pattern by a single spin flip. The resulting loss gradient is fully analytic — no sampling, no partition function.

- Provably achieves **≥ 1 pattern per neuron** (better than pseudo-inverse in some regimes, proven by Hillar et al. 2012)
- Gradient touches only the N single-bit-flip neighbours of each pattern → extremely sparse updates, fast in software
- Best used offline: run Adam for a few hundred steps on the full pattern set, then quantise W and burn to BRAM
- Natural fit with STE (Straight-Through Estimator): maintain real-valued W̃ during training, snap to integers for FPGA

**On our FPGA:** training is offline-only. The result is a denser, better-optimised W than Hebbian with no hardware changes to inference.

---

## 2. HNN ↔ Ising Machine Connection

- HNN energy E = −½ sᵀWs maps exactly to Ising Hamiltonian H = −Σ Jᵢⱼ σᵢ σⱼ − Σ hᵢ σᵢ
- **Wᵢⱼ = 2Jᵢⱼ**, **bᵢ = hᵢ** — one-to-one correspondence
- QUBO (binary 0/1 variables): xᵢ = (σᵢ+1)/2; Jᵢⱼ = −Qᵢⱼ/4; hᵢ = −(Qᵢᵢ + Σⱼ Qᵢⱼ)/4
- **Code changes needed:** add bias vector b to hopfield_net.py; add `from_ising(J,h)` and `from_qubo(Q)` classmethods

---

## 3. NP-Hard Problem Datasets

### MaxCut
Encode: Wᵢⱼ = −wᵢⱼ for edges (no bias). Minimising HNN energy = maximising the cut.

| Benchmark | Link | Notes |
|---|---|---|
| **Gset** | https://web.stanford.edu/~yyye/yyye/Gset/ | G1–G81, N=800–10000, standard reference |
| **BiqMac** | https://biqmac.aau.at/biqmaclib.html | Sparse + dense graphs, known optima |
| **MaxCutBench 2024** | https://github.com/maxcut/benchmark | Modern suite with SOTA comparisons |

Start with **G1** (N=800, 19176 edges) — known optimum 11624, widely cited.

---

### Travelling Salesman (Hopfield-Tank 1985)
Encoding: N² neurons (city × position). Four penalty terms enforce valid tours. Minimising energy finds shortest tour.

| Benchmark | Link | Notes |
|---|---|---|
| **TSPLIB95** | http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/ | eil51 (N=51), berlin52 (N=52) — start here |
| **TSPLIB mirror (networkx)** | https://people.sc.fsu.edu/~jburkardt/datasets/tsp/tsp.html | Easy programmatic download |

Start with **eil51** (51 cities, known optimum 426). Key challenge: tuning the four penalty coefficients A,B,C,D — ask supervisor for guidance on this.

---

### Number Partitioning
Given a set of integers, split into two subsets with equal (or near-equal) sum. Maps to HNN with no bias: σᵢ = ±1 encodes partition membership.

- **Encoding:** Wᵢⱼ = −aᵢ aⱼ (where aᵢ are the integers); minimising E gives balanced partition
- **Dataset:** Mertens hard instances — https://homepages.uni-pisa.it/~mertens/npb/npb.html
- Also: generate random instances (uniform integers 1–100, N=20–64) for quick validation
- Simplest NP problem to encode on our hardware — **recommend as the first Ising demo after MaxCut**

---

### Graph Coloring
Assign k colours to N vertices such that no two adjacent vertices share a colour. Maps to N×k binary neurons.

- **Encoding:** N×k neurons xᵢ,c; penalty for adjacent same-colour nodes, penalty for each node having exactly one colour
- **Dataset:** DIMACS coloring benchmarks — https://mat.tepper.cmu.edu/COLOR/instances.html
  - Start with **queen5_5** (25 nodes, 4-coloring) or **myciel3** (11 nodes)
- More complex encoding than MaxCut/partitioning — propose as a Phase 2 problem

---

## 4. Next Steps to Propose
1. Add bias vector + `from_ising` / `from_qubo` to `hopfield_net.py`
2. Implement **perceptron SGD** rule → demo 0.64N capacity
3. Demo **MaxCut on G1** — validate Ising mode vs known optimum 11624
4. Demo **number partitioning** — simplest bias-free Ising problem
5. Discuss TSP penalty coefficient tuning strategy with supervisor
6. Explore EP for supervised recall (longer term)
