# Meeting Notes — June 1, 2026

**Agenda: Adjoint Method → Gradient-Based HNN Training → Ising Machine NP-Hard Datasets**

---

## 1. The Adjoint Method

The adjoint method originates in optimal control theory (Pontryagin, 1950s). The core problem: minimise a loss L that depends on the output of a system defined by a constraint, not an explicit formula.

**Setup:** system constraint F(z, θ) = 0 defines state z implicitly. Differentiating:

```
dz/dθ = −[∂F/∂z]⁻¹ · ∂F/∂θ
→ dL/dθ = −(∂L/∂z) · [∂F/∂z]⁻¹ · ∂F/∂θ
```

Solve one linear system for the adjoint variable λ, then a dot product. **One linear solve regardless of system depth** — this is the efficiency gain over unrolling.

**Backprop is the adjoint method** applied to a chain of layer constraints. The backward-pass deltas are the adjoint variables. The same principle generalises to:

- **Recurrent BP** (Almeida/Pineda 1987) — adjoint through an RNN fixed point; iterate a linear recurrence, O(1) memory
- **Neural ODEs** (Chen et al. 2018) — adjoint variable satisfies its own ODE running backwards in time; constant memory regardless of integration depth
- **DEQ** (Bai et al. 2019) — solve for the fixed point z\* directly with a root-finder, then apply the implicit function theorem once: `∂L/∂θ = −(∂L/∂z*)ᵀ [I − ∂f/∂z*]⁻¹ ∂f/∂θ`
- **Equilibrium Propagation** (Scellier & Bengio 2017) — the β-nudge physically approximates the adjoint linear solve using the network's own dynamics; exact in the β→0 limit

The unifying idea: **don't differentiate through the process that found z\*, differentiate through the constraint that z\* satisfies.**

---

## 2. Gradient-Based Training Methods for HNNs

### A. Perceptron SGD / Three-Threshold Rule

**Core idea:** Define a loss that is positive whenever a stored pattern is not a stable fixed point. For every neuron i in pattern ξ, check if it gets the right sign from its local field h_i = W_i · ξ. If not, apply a Hebbian correction.

- Achieves the **Gardner bound: ~0.64N capacity** — 4× Hebbian
- Update is a single margin check (one-bit compare)
- Online and incremental: W updates after every pattern
- Three-threshold variant (Alemi et al. 2015) adds a forgetting term, approaches the theoretical maximum
- **L1 sparsity extension:** add λ|W|₁ penalty to the margin loss; weights not needed to stabilise any pattern are driven to zero; threshold small weights to exactly zero after each update — controls sparsity directly via λ with no circuit changes

**On our FPGA:** margin check lives in the same pipeline as async settle. Training = settle + compare + accumulate. simple on-chip FSM

---

### B. Equilibrium Propagation (Scellier & Bengio, 2017)

**Core idea:** Free phase — run to fixed point s\*. Clamped phase — nudge output neurons toward target by adding β·C(s,y) to the energy, settle to s^β. Weight update = difference of outer products divided by β.

EP is the adjoint method with the physics doing the linear solve. The β-nudge moves s\* in the direction [I − ∂f/∂s\*]⁻¹(∂L/∂s\*), which is exactly the adjoint vector. In the β→0 limit this converges to the exact backprop gradient.

- Proven equivalent to BPTT via the implicit function theorem
- Both phases reuse the existing async settle circuit — no additional hardware for training
- Binary neurons: s^β − s\* is a sparse set of bit-flips → XOR-based weight increment
- EqSpike (Laydevant et al. 2021): demonstrated on neuromorphic silicon at 2–3 orders lower energy than GPU

**On our FPGA:** phase 1 = normal inference. Phase 2 = inference with clamped output bits. Weight BRAM accumulates the XOR difference. β is a fixed hardware constant.

---

### C. Contrastive Hebbian Learning / CD-1 (Hinton 2002)

**Core idea:** Two-phase rule. Free phase — settle to s⁻ (unclamped). Clamped phase — hard-clamp output neurons to the target, settle to s⁺. Weight update = η[s⁺(s⁺)ᵀ − s⁻(s⁻)ᵀ]. Supervised, reuses the settle circuit. Outer-product difference is naturally sparse when most neurons don't change state between phases.

- Capacity above Hebbian empirically; no tight bound like Gardner's
- CD-1 (one Gibbs step for the free phase) is practical for hardware — one settle pass per training example
- Produces sparse weight updates when network is near-correct: only co-active neurons across the two phases contribute

**On our FPGA:** identical settle circuit for both phases. Weight BRAM accumulates the outer-product difference. Useful if supervised labelled-recall is needed alongside optimisation.

---

### D. Minimum Probability Flow (MPF, Sohl-Dickstein et al. 2011)

**Core idea:** Treat the HNN as p(s) ∝ exp(−E(s)/T). Minimise the probability of spontaneously flipping any single bit away from a stored pattern. The loss gradient is fully analytic — no sampling, no partition function.

- Provably achieves **≥ 1 pattern per neuron** (Hillar et al. 2012)
- Gradient touches only the N single-bit-flip neighbours of each pattern → sparse updates
- Offline training: run Adam on the full pattern set, quantise W, burn to BRAM
- Combine with STE: maintain real-valued W̃ during training, snap to integers for FPGA

**On our FPGA:** inference unchanged. Result is a denser, better-optimised W than Hebbian.

---

## 3. HNN ↔ Ising Machine Connection

- HNN energy E = −½ sᵀWs maps exactly to H = −Σ Jᵢⱼ σᵢ σⱼ − Σ hᵢ σᵢ
- **Wᵢⱼ = 2Jᵢⱼ**, **bᵢ = hᵢ** — one-to-one
- QUBO: xᵢ = (σᵢ+1)/2; Jᵢⱼ = −Qᵢⱼ/4; hᵢ = −(Qᵢᵢ + Σⱼ Qᵢⱼ)/4
- Code changes needed: bias vector b in hopfield_net.py; `from_ising(J,h)` and `from_qubo(Q)` classmethods

---

## 4. NP-Hard Problem Datasets

### MaxCut

Encoding: Wᵢⱼ = −wᵢⱼ for edges, no bias. Minimising HNN energy = maximising the cut.

| Benchmark                  | Link                                      | Notes                                     |
| -------------------------- | ----------------------------------------- | ----------------------------------------- |
| **Gset**             | https://web.stanford.edu/~yyye/yyye/Gset/ | G1–G81, N=800–10000, standard reference |
| **BiqMac**           | https://biqmac.aau.at/biqmaclib.html      | Sparse + dense graphs, known optima       |
| **MaxCutBench 2024** | https://github.com/maxcut/benchmark       | Modern suite with SOTA comparisons        |

Start with **G1** (N=800, 19176 edges) — known optimum 11624, widely cited.

---

### Travelling Salesman (Hopfield-Tank 1985)

Encoding: N² neurons (city × position). Four penalty terms enforce valid tours.

| Benchmark               | Link                                                       | Notes                         |
| ----------------------- | ---------------------------------------------------------- | ----------------------------- |
| **TSPLIB95**      | http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/     | eil51 (N=51), berlin52 (N=52) |
| **TSPLIB mirror** | https://people.sc.fsu.edu/~jburkardt/datasets/tsp/tsp.html | Easy programmatic download    |

Start with **eil51** (51 cities, known optimum 426). Key challenge: tuning the four penalty coefficients A,B,C,D.

---

### Number Partitioning

Split a set of integers into two subsets with equal sum. Maps to HNN with no bias: σᵢ = ±1 encodes partition membership.

- Encoding: Wᵢⱼ = −aᵢ aⱼ; minimising E gives balanced partition
- Dataset: Mertens hard instances — https://homepages.uni-pisa.it/~mertens/npb/npb.html
- Simplest NP problem on this hardware — good first Ising demo after MaxCut

---

### Graph Coloring

Assign k colours to N vertices, no two adjacent vertices share a colour. Encoding: N×k binary neurons.

- Penalty for adjacent same-colour nodes + penalty for each node having exactly one colour
- Dataset: DIMACS — https://mat.tepper.cmu.edu/COLOR/instances.html (start with queen5_5 or myciel3)
- More complex encoding — Phase 2
