# Ising Machines & NP-Complete Problems — Paper References

Ising machines and Hopfield networks are mathematically equivalent — they share the same cyclic (recurrent) update structure, but with a different update rule. This makes Ising machines a natural extension target once the Hopfield hardware is validated.

**Ising model energy:**  
`E = -Σ_{i<j} J_ij · s_i · s_j - Σ_i h_i · s_i`  
where `s_i ∈ {-1, +1}`, `J_ij` are couplings, `h_i` are biases.

**Connection to Hopfield:**  
Hopfield energy = `E = -½ · s^T · W · s`. Same form — `J_ij` maps to `W_ij`. Both minimize energy by iterative spin/neuron updates. Hopfield is used as associative memory; Ising machines are used to solve combinatorial optimization (NP-complete problems like Max-Cut, TSP, graph coloring).

---

## Papers

### [1] Ising Formulation of NP Problems

**Link:** (from research notes)

**Key points:**
- Shows how NP-complete problems (Max-Cut, graph coloring, vertex cover, etc.) can be reformulated as Ising Hamiltonians
- Groundwork for using Ising machines as hardware solvers
- Foundational paper — read before the hardware Ising papers

---

### [2] Ising Machines as Hardware Solvers of Combinatorial Optimization Problems

**Link:** (from research notes)

**Key points:**
- Survey of Ising machine hardware implementations
- Covers annealing-based approaches, FPGA-based solvers, photonic Ising machines
- Useful for understanding the broader hardware landscape we're entering

---

### [3] Hopfield vs Ising: A Comparison on the SoC FPAA

**Link:** (from research notes)

**Key points:**
- Direct comparison of Hopfield network vs Ising machine on a System-on-Chip Field Programmable Analog Array
- Very relevant: shows practical differences in implementation when targeting the same substrate
- Gives concrete performance numbers to benchmark against

---

### [4] Programmable 200 GOPS Hopfield-Inspired Photonic Ising Machine

**Link:** (from research notes)

**Key points:**
- Photonic (optical) implementation — different technology but illustrates the scale achievable
- 200 GOPS throughput — sets a performance target context
- "Hopfield-Inspired" framing shows the equivalence is well-established in the community

---

### [5] Decomposing Large-Scale Ising Problems on FPGAs: A Hybrid Hardware Approach

**Link:** (from research notes)

**Key points:**
- Addresses the scaling problem: large Ising problems exceed single FPGA capacity
- Hybrid approach: decompose the problem, solve sub-problems in parallel
- Directly relevant for thinking about how to scale our Hopfield LUT design beyond N=16

---

## Adaptation Path for This Project

Once the Hopfield LUT hardware is validated as associative memory:

1. **Reformulate as Ising solver**: Map an NP-complete problem (e.g., Max-Cut) to a Hopfield weight matrix `W = J_ij`
2. **Train/set weights** directly (no Hebbian learning — weights come from the problem instance)
3. **Generate truth tables** per neuron from the problem-specific weight matrix
4. **Run the LUT circuit** — it anneals to a low-energy (near-optimal) solution
5. **Evaluate solution quality** vs classical solvers (greedy, simulated annealing)

This is the "Adaptation to Ising Machines" phase described in the research plan.
