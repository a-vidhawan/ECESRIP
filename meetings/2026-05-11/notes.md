# Meeting Notes — 2026-05-11

**Supervisor meeting — ~45-60 min**

---

## 1. State of the Codebase (5 min)

**Walk through `sim/python/`:**

- `hopfield_net.py` — `HopfieldNetwork(N, rule, update_mode)`. Single-line switches:
  - `RULE = STORKEY` / `HEBBIAN`
  - `UPDATE_MODE = ASYNC_CYCLIC` (1) / `ASYNC_RANDOM` (2) / `SYNC` (3)
- `datasets.py` — `load(RANDOM / MNIST_8 / MNIST_28, N, M, seed)`
- `benchmark.py` — sweeps N ∈ {6…16}, M up to 0.30N, 9 noise levels, 50 trials, exports CSV

**Numbers to quote:**
- Storkey and Hebbian both hit zero spurious rate below load = 0.138N (matches theory exactly)
- Above capacity: Hebbian N=8 load=0.38 → 79% spurious; Storkey same point → ~0% — this is the headline Storkey vs Hebbian result
- Basin width scales with N at fixed load: N=16 M=1 → basin=6 bits; N=6 M=1 → basin=2 bits
- Convergence stays at 1 sweep below capacity, rises above it — consistent with energy landscape flattening

**Live run:**
```bash
cd sim/python
python benchmark.py   # edit N_VALUES = [8] and N_TRIALS = 20 first for speed
```
Point at the CSV: show the load column crossing 0.138N and the spurious_rate jumping.

---

## 2. Demo: Hopfield Recall (5-10 min)

Two demos in `meetings/2026-05-11/demo/`. Open MNIST first for impact; fall back to random if he asks for the energy/math story.

**MNIST-8 (`demo_mnist.py`)** — N=64, stores 3 binarized digits, corrupts one with 20% pixel flips, shows before/after as 8×8 grids side-by-side.
```bash
cd meetings/2026-05-11/demo
python demo_mnist.py
```

**Random-pattern (`demo_random.py`)** — N=16, 2 patterns, step-by-step convergence with energy printed at each sweep. Shows energy monotonically decreasing to the fixed point.
```bash
python demo_random.py
```

Key point to make: *"The energy function is our correctness certificate — every update either decreases energy or leaves it flat. That's the proof that this circuit terminates."*

---

## 3. Update Order — Why It Matters for This Design (10 min)

*This is the theoretical piece to establish before talking about the synthesis pipeline. Frame it as "I went and looked at this carefully because it directly determines the correctness of the hardware."*

---

### The core question

When the LUT circuit runs, neurons don't all update simultaneously — some schedule has to decide which neuron fires when. That scheduling choice is not cosmetic. It determines whether the circuit is **provably guaranteed to terminate** or just *probably* terminates.

---

### What the theory actually says

**Async update (one neuron at a time, any order) → always converges to a fixed point.**

The proof is the energy function argument: each single-neuron flip either decreases energy or leaves it flat. Since the state space is finite (2^N states) and energy is bounded, the sequence must terminate. This holds for *any* fair schedule — cyclic, random, whatever — because the proof only needs one neuron to update at a time.

*"The energy function is the correctness certificate. As long as we only flip one neuron per step, I have a formal proof that this circuit terminates."*

**Sync update (all neurons simultaneously) → fixed point OR a 2-cycle, and you can't distinguish which ahead of time.**

Goles and Olivos proved in 1980 that with symmetric weights, synchronous update either converges to a stable state or falls into a 2-cycle — two states that each produce the other, so the network oscillates forever. Same weights, same initial state, different update mode → completely different outcome. A "run until stable" termination condition would hang indefinitely on a 2-cycle.

*"The 2-cycle is not an edge case — it can happen with a simple 4-neuron network. It's a structural consequence of updating all neurons at once."*

---

### Does the specific order matter within async?

Convergence guarantee: **no** — any fair order converges.

Which attractor you land in: **yes** — different orderings from the same starting state can reach different fixed points.

The set of all fixed points is determined solely by W. But the basin of attraction boundaries shift with the update schedule. Cyclic order (counter 0→N-1) is fully deterministic and reproducible, so for hardware this is fine — the behavior is consistent even if a different order would reach a different attractor.

*"This is actually analogous to gradient descent finding different local minima depending on step direction. The fixed point set is the same; the path through the energy landscape changes."*

---

### Hardware implication — what I'm planning

Serial async with a cyclic counter: one neuron latches its new LUT output per clock cycle, counter increments, convergence check runs after each full sweep. This is the only mode with a formal termination proof.

Sync mode is still worth implementing as an optional mode for throughput experiments — if we want to show "how many clock cycles to convergence," sync is faster per cycle. But it needs a 2-cycle detector: compare state at t with state at t-2, flag if equal and state at t-1 is different.

---

### Question to ask

> *"For the primary design I'm going with serial async — one neuron per clock cycle. This matches the convergence proof exactly and means only one input bit changes per cycle at any given LUT, which also helps with the hazard analysis. The sync mode I'll add as a comparison point but with a 2-cycle safety check. Does that framing work, or do you want the primary result to be synchronous and treat async as the fallback?"*

Expected answer: serial async is correct for the primary design; sync as a comparison is reasonable. Listen for whether he wants both modes benchmarked in the evaluation or just the provably correct one.

---

## 4. Moving to Truth Tables — The Synthesis Transition (5 min)

**State of play:** Python side of Phase 1 is essentially complete. Next step is:

```
weights W  →  enumerate 2^N truth table per neuron  →  PLA file  →  Espresso  →  SOP  →  SystemVerilog
```

The pipeline doesn't exist yet — this is the next thing to build.

---

## 5. Two Open Technical Questions (10-15 min)

### Q1 — Hazard-Free Coverage Limitation (Phase 2)

**Setup:**
- Espresso `-Dhazard` produces a SOP that is hazard-free for *single-variable* input transitions
- In Phase 2 (fully combinational feedback), multiple neurons can change near-simultaneously → multi-input transitions → the single-variable guarantee does not apply

**The question:**
> *"Does the single-transition guarantee provide enough correctness for Phase 2, or do we need a formally stronger model? My read of the options is:*
> *(a) Argue informally: the energy function tolerates glitches because any spurious transition either decreases energy (fine) or is resolved by the next update cycle (acceptable)*
> *(b) Use Speed Independent or Quasi-Delay-Insensitive circuit synthesis — formally correct for arbitrary gate delays, but changes the synthesis tool entirely and moves away from Espresso/SOP*
> *My instinct is (a) is sufficient for a first result and (b) is future work — but this determines how strong the correctness claim in the paper can be."*

What to listen for: does he want a formal proof of correctness or is engineering-level validation (RTL simulation matching Python model) sufficient for the contribution?

### Q2 — Scaling Beyond N=16

**Setup:** Truth table has $2^N$ rows per neuron. At N=16 → 65K rows (Espresso borderline). At N=32 → 4B rows (impossible).

**The three options — pitch each briefly:**

| Option | Method | Scales? | Preserves TT framing? | Hazard-free? |
|---|---|---|---|---|
| **BDD/ABC synthesis** | Binary Decision Diagrams via ABC tool | Yes, to ~N=32 | Yes | Unclear |
| **Sparse connectivity** | Keep F strongest weights per neuron, 2^F rows | Yes, any N | Yes | Yes (same pipeline) |
| **Arithmetic decomposition** | Adder tree + comparator for $\sum w_{ij}s_j$ | Unlimited | No — abandons Boolean framing | Different analysis |

**The question:**
> *"The sparse option is the most natural extension — it keeps the entire truth table pipeline and just limits fan-in to F strongest weights per neuron. LogicNets does exactly this for feed-forward nets. The question is whether a sparse Hopfield network still has interesting convergence properties and whether the contribution story holds at larger N. Do you think the sparse route is worth pursuing, or does abandoning the dense weight matrix weaken the result?"*

What to listen for: whether he wants to push N larger or go deeper on the N≤16 case (more rigorous hazard analysis, FPGA results, Ising adaptation).

---

## 6. Questions for Him

### Q — What N are we actually targeting?

The truth table blows up at 2^N rows per neuron. The Python benchmark sweeps N ∈ {6…16} but the hardware feasibility is:

- N ≤ 10: comfortable, fits distributed LUTs
- N ≤ 14: feasible, likely needs BRAM
- N ≤ 16: borderline, Espresso gets slow
- N > 16: needs sparse connectivity (keep F strongest weights → 2^F rows)

*"Is the goal to push N as large as possible, or to go deep on a fixed N (say N=10 or N=12) — rigorous hazard analysis, FPGA timing, basin characterization — and treat that as the full contribution?"*

This answer determines whether I build the sparse extension or focus on correctness at small N.

---

### Q — Hardware target and languages

Need to pin down:

*"What FPGA are we targeting and what toolchain? Last I noted it was Cyclone V with Quartus + ModelSim, but I want to confirm. And is SystemVerilog the right output language from the pipeline, or do you want plain Verilog for compatibility with older tools?"*

Also ask:
*"Beyond Python (training + truth table gen) and SystemVerilog (RTL), is there anything else I should be learning — TCL for Quartus scripting, C for simulation cross-checks, or anything else you'd expect in the final submission?"*

---

### Q — Connect me with the grad student using Espresso

*"I'm at the point where the next concrete step is wrapping Espresso — calling it from Python, parsing the SOP output, and exporting to SystemVerilog. You mentioned there's a grad student already using Espresso in the lab. Can you connect us? Even a 30-minute call to see how they're invoking it and what the output format looks like would save me a lot of time."*

---

## 7. AOB / Next Steps

- If Phase 1 synthesis pipeline sign-off → start `truth_table_gen.py` + Espresso wrapper next week
- FPGA target confirmed as Cyclone V (Quartus + ModelSim) — check if lab access is arranged
- Phase 2 scope decision depends on Q1 answer above
- Phase 3 (Ising) deferred until Phase 1 RTL is validated
