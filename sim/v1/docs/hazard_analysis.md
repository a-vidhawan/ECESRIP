# Hazard Analysis & Elimination

## What is a Logic Hazard?

A hazard is a spurious, momentary output glitch caused by different propagation delays through alternative paths in a combinational circuit.  For Hopfield hardware the concern is specifically **static-1 hazards** in the SOP neuron-update logic: the output *should* stay at 1 throughout a variable transition, but briefly drops to 0 due to unequal gate delays.

In a synchronous design a static-1 hazard on a combinational signal is masked by the clock edge as long as the glitch settles before the setup window.  Our RTL uses registered outputs everywhere, so static-1 hazards are harmless for normal FPGA operation.

However, they are eliminated by construction anyway, for two reasons:
1. The belt-and-suspenders argument: if the generated logic is ever reused asynchronously (e.g., used to drive an asynchronous RAM, or embedded in an asynchronous FIFO), hazards would matter.
2. It is a useful research deliverable to have formally hazard-free logic.

---

## How Hazards Arise in SOP Logic

Consider a two-variable function f = AB + A'C.  The prime implicants are AB and A'C.

Transition: A: 1→0, B=1, C=1.

- Before: AB = 1, A'C = 0, f = 1. ✓
- After:  AB = 0, A'C = 1, f = 1. ✓
- During: if the NOT gate inverting A is slower than the AND gate reading A, then for a moment both AB = 0 and A'C = 0, giving f = 0. ✗ — static-1 hazard.

The consensus of AB and A'C with respect to A is BC (drop A from one, A' from the other, AND the rest).  Adding BC to the cover gives f = AB + A'C + BC.  Now BC = 1 throughout the transition (B=1, C=1), holding f = 1. ✓

---

## Algorithm in logic_minimize.py

After the initial Q-M cover is computed, `_make_hazard_free()` iterates:

1. For every pair of adjacent ON-set minterms (Hamming distance 1) where no single cover term spans both, add the consensus prime implicant.
2. Repeat until no new terms are needed (fixed point, guaranteed to terminate because the set of prime implicants is finite).

The consensus implicant is computed as: take the two minterms, find the differing bit position, set that position to don't-care, then expand to a prime implicant (absorb additional don't-cares as long as no OFF-set minterms are covered).

The resulting cover is a **hazard-free SOP**: for any single-variable transition between two ON-set minterms, there is always a product term evaluating to 1 throughout the transition.

---

## Hazard Mitigation in the RTL

### Approach 1: Synchronous Design (primary)

All combinational outputs (from `neuron_logic_bank`) feed into D flip-flops (`neuron_bank`).  Glitches settle before the next rising edge.  This eliminates propagation of any transient to the network state.

### Approach 2: Hazard-Free SOP Cover (secondary)

The generated logic itself is hazard-free by construction.  This matters if:
- The combinational block is used without registration (asynchronous path).
- Formal verification tools check for glitches on combinational outputs.
- The design is ported to an ASIC where timing margins are tighter.

### What about dynamic hazards?

A dynamic hazard is a multiple-transition glitch (output changes 0→1→0→1 instead of 0→1).  Dynamic hazards arise in multi-level (non-SOP) logic.  Because the generated logic is strictly two-level (SOP), dynamic hazards cannot occur.

### What about hazards on control signals?

All control signals from `update_ctrl` are registered.  The `o_load` signal to `neuron_bank` changes only on clock edges, never asynchronously.  The FSM is designed to assert `o_load` for exactly one clock cycle per update step.  No glitch on `o_load` is possible.

---

## Verification Plan

1. **Exhaustive functional check** (`tb_neuron_update.sv`): apply all 2^N input vectors, compare generated logic output against the reference threshold comparator.  A mismatch indicates an error in the Python minimization.

2. **Fixed-point recall test** (`tb_hopfield_top.sv`): load stored patterns (and noisy probes), run the network, verify it converges to the correct attractor.

3. **Timing simulation** (post-synthesis): run ModelSim with back-annotated SDF.  Verify that setup/hold violations are absent.  The hazard-free SOP cover ensures that even if timing were close, no static hazard can cause a wrong output latch.

4. **Formal assertion** (optional, Symbiyosys / JasperGold): assert that for every pair of adjacent ON-set minterms, the SV expression evaluates to 1 at both inputs.  This is a bounded model-check over the combinational cone only.
