# Research Plan

## Overview

Implement a Hopfield network on FPGA by enumerating each neuron's update function as a truth table and synthesizing it into LUTs — no multipliers, pure Boolean logic. Three phases: clocked baseline → async combinational → Ising machine.

---

## Phase 1 — Clocked LUT-Based Hopfield (Baseline)

**Goal:** Validate the truth-table approach with a debuggable synchronous design.

1. Train in Python (Hebbian or Storkey, single-line switch)
2. Enumerate truth table per neuron over all $2^N$ binary inputs
3. Minimize with Espresso (standard — no `-Dhazard` yet) → SOP per neuron
4. Emit SystemVerilog: combinational SOP + **flip-flop on every neuron output**, clocked
5. All neurons evaluate combinationally; results latch on clock edge
6. Simulate in ModelSim; synthesize to Cyclone V via Quartus
7. Verify: RTL attractors match Python model on identical inputs

---

## Phase 2 — Async Combinational Feedback

**Goal:** Remove flip-flops, wire neuron outputs directly back as inputs.

1. Re-run Espresso with `-Dhazard` on the same truth tables → hazard-free SOP
2. Strip flip-flops; `s_new[i]` feeds directly into all other LUT inputs
3. Circuit settles combinationally — or oscillates (this is the research question)
4. Compare Phase 2 waveforms against Phase 1 ground truth
   - Discrepancies are attributable to async hazards only, not incorrect Hopfield logic
5. Characterise: does the async circuit reach the same attractors? How often does it enter a 2-cycle?

**Novel contribution:** First hazard-free async Hopfield circuit via truth table enumeration.

---

## Phase 3 — Ising Machine Adaptation

**Goal:** Use the LUT hardware as an Ising annealer for NP-hard optimisation.

1. Set $W = J_{ij}$ from a problem instance directly (no learning)
2. Generate truth tables from problem-specific weights
3. Run LUT circuit; fixed point ≈ approximate solution
4. Benchmark vs simulated annealing on Max-Cut, graph colouring

See `research/papers/ising_machines.md`.

---

## LUT Feasibility

| $N$ | Rows per neuron | Espresso time | Feasibility |
|---|---|---|---|
| ≤ 10 | ≤ 1,024 | < 1 s | Easy |
| ≤ 14 | ≤ 16,384 | seconds | Feasible |
| ≤ 16 | ≤ 65,536 | minutes | Borderline |
| > 16 | > 65 K | infeasible | Keep $F$ strongest $|w_{ij}|$ per neuron |

Capacity: $M \lesssim 0.14N$ (Hebbian); Storkey gives better quality at the same load.

---

## Open Questions

1. Does `-Dhazard` SOP prevent convergence errors in the fully combinational loop, or only for single-variable input transitions?
2. How often does the Phase 2 circuit enter a 2-cycle vs a fixed point, as a function of $N$ and $M$?
3. For $N > 16$, what is the optimal weight pruning strategy (strongest-$F$, random expander, learned mask)?
4. Ising solution quality vs simulated annealing on standard G-set Max-Cut benchmarks.
