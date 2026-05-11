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

## 3. Moving to Truth Tables — The Synthesis Transition (5 min)

**State of play:** Python side of Phase 1 is essentially complete. Next step is:

```
weights W  →  enumerate 2^N truth table per neuron  →  PLA file  →  Espresso  →  SOP  →  SystemVerilog
```

The pipeline doesn't exist yet — this is the next thing to build.

**Question to ask:**
> *"For the Phase 1 clocked baseline, I'm planning serial async update — one neuron latches its new value per clock cycle. This directly matches the convergence proof and means only one input bit changes per cycle across all LUTs. The alternative is latching all neurons simultaneously (synchronous parallel), which is faster but risks 2-cycles that never terminate. I'm leaning serial — does that align with what you'd want to show?"*

Expected answer: serial is correct; synchronous parallel is fine as a comparison point but not the primary design.

---

## 4. Two Open Technical Questions (10-15 min)

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

## 5. AOB / Next Steps

- If Phase 1 synthesis pipeline sign-off → start `truth_table_gen.py` + Espresso wrapper next week
- FPGA target confirmed as Cyclone V (Quartus + ModelSim) — check if lab access is arranged
- Phase 2 scope decision depends on Q1 answer above
- Phase 3 (Ising) deferred until Phase 1 RTL is validated
