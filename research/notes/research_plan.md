# Research Plan

## Overview

Build a Hopfield neural network on an FPGA by converting each neuron's update logic into a Boolean truth table and synthesizing it into LUTs. Validate it as associative memory, then explore adaptation to Ising machine optimization.

---

## Phase 1: Higher-Level Hopfield Network (Python Simulation)

- Parameterizable Python class: N neurons, storing M patterns of N-bit vectors
- Two learning rules: Hebbian and Storkey
- Async and sync update modes
- Energy function and overlap metric
- **N=16 → 65K rows in truth table** — need smart/sparse approach at N>16
- Implementation: `sim/v1/python/hopfield_train.py`

---

## Phase 2: Generate Truth Tables

- Enumerate all 2^N possible input combinations for each neuron
- Bipolar-to-binary mapping: `b_j = (s_j + 1) / 2`
- Compute local field: `h_i = 2*(W[i] · b) - Σ|W[i]|`
- Output: 1 if `h_i ≥ 0`, else 0
- Export to PLA format for Espresso:
  - Use `-dhazard` flag to insert redundant minterms for hazard-free SOP
  - Hazard-free: prevents glitches in asynchronous feedback loop
- Implementation: `sim/v1/python/truth_table_gen.py`

**Open question (red):** Is our hazard-free SOP approach sufficient for the asynchronous feedback loop? What about metastability at the inputs when two neurons change simultaneously?

---

## Phase 3: Logic Synthesis

- Run Espresso minimizer on each neuron's PLA file
- Convert minimized SOP to SystemVerilog
- One `neuron_update_i` module per neuron (SOP implementation)
- `neuron_logic_bank` wrapper connects all neurons
- Implementation: `sim/v1/python/logic_minimize.py`, `sim/v1/python/sv_export.py`

---

## Phase 4: Simulate and Verify

- RTL simulation: `sim/v1/rtl/tb/tb_hopfield_top.sv`, `tb_neuron_update.sv`
- Compare SystemVerilog output vs Python model on same input patterns
- Check: does the RTL converge to the same attractors as the Python model?
- C simulation for fast parameter sweep: `sim/v1/c_sim/`

---

## Phase 5: Evaluate as Associative Memory

Metrics to sweep over (N and M values):

- **Recall accuracy**: fraction of test patterns correctly recalled under bit-flip noise
- **Noise tolerance**: how many bits can be corrupted before recall fails?
- **Spurious states**: fraction of convergent states that are not stored patterns
- **Basin of attraction width**: maximum Hamming distance from pattern where recall still succeeds
- **Convergence iterations**: how many update cycles to reach steady state?
- **Fraction outside training set**: test on patterns not in the training set

**Feasibility sweep:**
- Sweep M from 1 to 0.3N (beyond Hebbian capacity ~0.14N)
- Sweep N from 4 to 20 (noting where truth table size becomes impractical)
- Compare Python model (ground truth benchmark) vs SystemVerilog implementation (test)

---

## Phase 6: Adaptation to Ising Machines

Once Hopfield LUT hardware is validated:

- Map NP-complete problem instances to Hopfield weight matrix W = J_ij
- Generate truth tables directly from problem-specific weights (no learning)
- Run LUT circuit as Ising annealer — measure solution quality vs classical solvers
- Target problems: Max-Cut, graph coloring, combinatorial optimization

See `research/papers/ising_machines.md` for relevant papers.

---

## Key Constraints & Feasibility

| N | Truth table rows | Espresso time | Feasibility |
|---|---|---|---|
| ≤ 10 | ≤ 1,024 | < 1s | Easy |
| ≤ 14 | ≤ 16,384 | ~seconds | Feasible |
| ≤ 16 | ≤ 65,536 | ~minutes | Borderline |
| > 16 | > 65K | hours/infeasible | Need sparse (F strongest weights) |

**Capacity rule:** M ≤ 0.14N (Hebbian), M ≤ ~0.14N with better quality (Storkey).

---

## Open Questions

1. **Hazard-free correctness:** Does Espresso's `-dhazard` flag produce a cover that is provably hazard-free for all input transitions in the asynchronous feedback loop? What about multi-input transitions (two neurons changing simultaneously)?
2. **Metastability:** Can the asynchronous loop enter a metastable state? How to detect and break it?
3. **Sparse connectivity for large N:** Which F weights to keep — strongest (by magnitude), random (LogicNets expander), or learned?
4. **Ising adaptation:** When weights are set by a problem instance (not learned), does the capacity analysis still hold? What is the annealing quality vs simulated annealing?
