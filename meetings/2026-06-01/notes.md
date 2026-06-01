# Meeting Notes — June 1, 2026

**Agenda: Ising Machine Connections + Gradient-Based HNN Training**

---

## 1. Pseudo-Inverse Rule (done)
- Added to `hopfield_net.py` alongside Hebbian and Storkey
- Capacity scales to **N** (vs Hebbian 0.138N, Storkey ~0.22N)
- Demo (`demo_pseudoinverse.py`): fixed-point rate stays ~99% up to M=14 for N=16
- **Ask**: is it worth extending the demo to larger N to show the scaling empirically?

---

## 2. HNN ↔ Ising Machine Equivalence
- HNN energy E = −½ sᵀWs maps exactly to Ising Hamiltonian H = −Σ Jᵢⱼ σᵢ σⱼ
- Via Wᵢⱼ = 2Jᵢⱼ; optimisation problems become pattern-storage problems
- **QUBO** (binary 0/1) ↔ Ising ↔ HNN: all three are equivalent with simple variable substitution
- Key code changes needed: bias vector b in hopfield_net.py, `from_ising(J,h)` / `from_qubo(Q)` classmethods

---

## 3. NP-Hard Problem Datasets
- **MaxCut**: weight matrix Wᵢⱼ = −wᵢⱼ, no bias; minimising energy = maximising cut
  - Benchmarks: Gset (G1–G81), BiqMac, MaxCutBench 2024
- **TSP** (Hopfield-Tank 1985): N² neurons, four penalty terms; TSPLIB for benchmarks
  - Parameter tuning is the key challenge — worth discussing strategy with supervisor
- Other: number partitioning (simplest), graph coloring, vertex cover, k-SAT

---

## 4. Hardware Ising Machine Landscape
- D-Wave (quantum annealing), Fujitsu DA (ASIC SA), Toshiba SBM (FPGA deterministic)
- **Patel et al. FPGA-RBM**: tanh LUT + LFSR p-bits — 10⁷× faster than D-Wave on MaxCut
- Our LUT-HNN sits in this space: want to benchmark against these on MaxCut

---

## 5. Gradient-Based Training — Top Methods
- **Perceptron SGD / 3-threshold rule**: ~0.64N capacity, local, maps to on-chip FSM — implement next
- **Equilibrium Propagation**: exact backprop gradient via two settle phases; reuses existing settle circuit
- **MPF**: analytic gradient on single-bit-flip neighbours; ≥1 pattern/neuron; good for offline training

---

## Next Steps to Propose
1. Add bias vector + Ising/QUBO classmethods to `hopfield_net.py`
2. Implement perceptron SGD rule → demo capacity improvement to ~0.64N
3. Run MaxCut on small Gset graph — validate Ising mode vs known optimum
4. Discuss TSP parameter tuning strategy
5. Phase 2 hardware: fold bias bᵢ into LUT truth table (Espresso handles it transparently)
