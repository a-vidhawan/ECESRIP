# System Architecture

## Overview

The Hopfield hardware pipeline converts trained associative-memory weights into synthesizable, hazard-free digital logic.  There are three layers:

**Python** trains the network and produces a combinational description of each neuron's update function.  **SystemVerilog RTL** implements that logic in hardware with a synchronous, hazard-free datapath.  **C simulation** provides an independent reference model for cross-checking both layers.

---

## Layer 1 — Python Pipeline

### hopfield_train.py

Implements the Hopfield weight-learning rules.

**Hebbian rule:**
W_ij = (1/N) Σ_μ ξ_i^μ ξ_j^μ, with W_ii = 0.

Theoretical maximum capacity is approximately 0.138 N patterns before recall starts to fail.

**Storkey rule:**
W ← W + (1/N)(ξξᵀ - hξᵀ - ξhᵀ) where h_i = Σ_{k≠i} W_ik ξ_k.

Achieves slightly higher practical capacity and better recall quality near saturation.

Both rules produce a symmetric N×N weight matrix saved as a NumPy `.npy` file.

---

### truth_table_gen.py

Enumerates the Boolean update function for each neuron.

The synchronous update rule is: s_i(t+1) = sign(Σ_j W_ij · s_j(t)) where s_j ∈ {-1, +1}.

Hardware uses binary encoding: b_j = (s_j + 1)/2 ∈ {0, 1}.  The net input in binary variables is:

h_i(b) = 2·(W_i · b) − Σ_j W_ij

b_i_new = 1 if h_i ≥ 0, else 0.

This defines one Boolean function f_i : {0,1}^N → {0,1} per neuron, enumerated over all 2^N inputs.

**Scaling:** full enumeration is practical up to about N = 20 (1M rows).  For larger N, a symbolic/BDD approach is needed.

---

### logic_minimize.py

Two-level Boolean minimization with hazard-free augmentation.

**Quine-McCluskey (Q-M):** generates the complete set of prime implicants by iterative pairwise merging of minterms differing in exactly one variable.  Essential prime implicants (minterms covered by only one PI) are selected first; remaining minterms are covered greedily.

**Hazard-free cover:** A static-1 hazard exists when two adjacent minterms (differing in exactly one bit) are both in the ON-set but no single product term in the cover spans both.  During a transition on that variable, the gate evaluating the output may briefly output 0 due to unequal propagation delays.

The remedy is the consensus theorem: add the product term that covers both minterms (the "consensus" of the two PIs separated by the transitioning variable).  This term evaluates to 1 throughout the transition, holding the output high.  The algorithm iterates until no adjacent ON-set pair lacks a common cover term.

---

### sv_export.py

Converts minimized covers to SystemVerilog SOP expressions:

```systemverilog
assign b_out = (b_in[7] & ~b_in[3]) | (b_in[5] & b_in[2]) | ...;
```

One module is generated per neuron, plus a `neuron_logic_bank` wrapper instantiating all N modules.

---

## Layer 2 — SystemVerilog RTL

### Datapath

```
i_pattern ──► neuron_bank ──► neuron_logic_bank ──┐
               (state reg)    (comb. next-state)   │
                  ▲                                │
                  └─────── update_ctrl ◄───────────┘
                            (FSM)
```

All registered paths:
- `neuron_bank` is a plain D flip-flop array.  The `i_load` strobe is registered inside `update_ctrl`, so there are no glitches on the load enable.
- `neuron_logic_bank` outputs feed directly into `neuron_bank.d_next`.  Combinational glitches are invisible to the downstream registers (masking at the clock edge).
- `update_ctrl` outputs are all registered before leaving the module.

### update_ctrl FSM

Four states: IDLE → COMPUTE → CHECK_FP → DONE.

In SYNC mode one full state update happens per clock cycle.  In ASYNC (round-robin) mode N cycles constitute one full update round before the fixed-point check.

Fixed-point detection compares the state word before and after each round; equality means convergence.

### weight_rom

Synchronous single-port ROM.  One-cycle read latency.  Zero diagonal enforced in hardware.

---

## Layer 3 — C Simulation

Provides an independent, word-accurate model of both learning rules and both update modes.  Intended use: cross-check Python results before RTL simulation, and provide a fast stimulus generator for large N.

---

## Key Design Decisions

**Why enumerate truth tables rather than implement the threshold comparator directly?**  The threshold comparator requires N multiply-accumulate operations per neuron per update — expensive in area and latency for large N.  The enumerated-and-minimized SOP requires only a few AND/OR gates regardless of N (though the number of product terms grows with N).  For research-scale N (≤ 20) the generated logic is smaller and faster than the arithmetic alternative.

**Why synchronous design for hazard mitigation?**  The primary hazard concern in SOP logic is static-1 glitches when a variable transitions and two overlapping PIs are not bridged by a consensus term.  Registering all outputs masks these glitches at clock edges.  The hazard-free SOP cover is an additional safety measure for any path where the combinational output is sampled asynchronously (e.g., an FPGA with asynchronous read ports).

**Why support both Hebbian and Storkey?**  Hebbian is simpler and its capacity limits are well understood.  Storkey is drop-in compatible but gives better results near saturation, which is relevant for research comparing hardware recall quality versus theoretical capacity.
