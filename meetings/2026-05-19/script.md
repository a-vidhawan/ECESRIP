# Presentation Script — 2026-05-19

**~30–40 min total. Professor is technical — skip trivia, go straight to math and decisions.**

---

## Slide order (Google Slides)

1. Title
2. What is a Hopfield Network?
3. Energy function
4. Learning Rules — overview & comparison table
5. Hebbian learning (math)
6. Storkey learning (math)
7. Pseudo-inverse learning (math + why we didn't use it)
8. Local & incremental — why it matters
9. Inference: the voting rule
10. Update order: async vs sync
11. The 2-cycle problem (sync)
12. Convergence proof (energy argument)
13. LUT synthesis pipeline
14. Phase 1 / 2 / 3 roadmap
15. Results & demos

---

## Slide-by-slide script

---

### 1. Title
Just introduce yourself and the project name. One sentence:
> "This project is about implementing a Hopfield associative memory directly in FPGA lookup tables — no multipliers, no adders at inference time, just truth tables."

---

### 2. What is a Hopfield Network?

> "A Hopfield network is a fully-connected recurrent network of N binary neurons. Each neuron is bipolar: it's either +1 or −1. We store patterns in the weight matrix W during a training phase, then at inference we feed in a corrupted version of a pattern and let the network settle to the nearest stored memory."

Point at any diagram. Key numbers:
> "For N=64 neurons — an 8×8 pixel image — the Storkey rule can store up to about 8 patterns perfectly. That's the capacity limit we'll come back to."

---

### 3. Energy Function

$$E(\mathbf{s}) = -\frac{1}{2}\mathbf{s}^\top W \mathbf{s}$$

> "Every valid stored pattern sits at a local minimum of this energy landscape. The network's job at inference is to roll downhill from wherever the corrupted input lands. The energy function is not just a nice analogy — it's the correctness certificate for the hardware. I'll come back to why."

---

### 4. Learning Rules — comparison table

| Rule | Capacity | Incremental? | Local? | Hardware cost |
|---|---|---|---|---|
| Hebbian | ~0.138N | Yes | Yes | Minimal |
| Storkey | ~0.2N (empirical) | Yes | Yes | Moderate |
| Pseudo-inverse | Up to N | **No** | **No** | Matrix inversion |

> "Three rules, three different trade-offs. We're using Storkey. Let me walk through each."

---

### 5. Hebbian Learning

$$W_{ij} = \frac{1}{N} \sum_{\mu=1}^{M} \xi_i^\mu \xi_j^\mu, \qquad W_{ii} = 0$$

> "One-shot, closed form. For each pattern you take the outer product with itself and accumulate. It's the direct neural analogue of Hebb's rule — neurons that fire together wire together. The problem is capacity: above about 0.138N stored patterns, the patterns start interfering with each other and the network falls into spurious states instead of the stored ones."

---

### 6. Storkey Learning

$$W \leftarrow W + \frac{1}{N}\left(\xi^\mu(\xi^\mu)^\top - h(\xi^\mu)^\top - \xi^\mu h^\top\right)$$

where $h_i = \sum_{j \neq i} W_{ij} \xi_j^\mu$ is the **local field** — what the current weight matrix predicts for neuron $i$ given the new pattern.

> "Storkey adds one pattern at a time. Before adding pattern μ, it computes the local field h — essentially how much the existing weights would already predict the new pattern. The two correction terms subtract out that interference. The result is a pattern that sits more orthogonally to everything already stored. Capacity improves noticeably over Hebbian, especially above 0.138N."

> "Critically: the update is **incremental** — you process one pattern at a time — and **local** — the weight between neurons i and j only depends on the states of i and j, plus a correction that's still computable from the local neighbourhood. These properties matter a lot for hardware, which I'll explain in a moment."

---

### 7. Pseudo-inverse Learning

$$W = \Xi (\Xi^\top \Xi)^{-1} \Xi^\top$$

where $\Xi$ is the $N \times M$ matrix of all stored patterns.

> "The pseudo-inverse rule is the theoretically optimal learning rule — it can store up to N linearly independent patterns perfectly, which is the absolute ceiling. The weight matrix becomes the projection operator onto the subspace spanned by the stored patterns."

> "So why didn't we use it? Two reasons."

> "First, it's **not incremental**. To add one new pattern you have to recompute the entire pseudo-inverse — that's an $O(N^2 M + M^3)$ operation over all patterns simultaneously. Hebbian and Storkey just do a rank-1 update."

> "Second, it's **not local**. Each weight $W_{ij}$ depends on ALL M patterns through the matrix inversion. You can't compute it from just the states of neurons i and j."

> "For our project specifically — we train offline in Python and burn the result into a static LUT — we *could* use pseudo-inverse and it would work. But it's worth explaining the distinction because: (a) it makes the Storkey choice principled, (b) if we ever wanted online relearning in hardware, pseudo-inverse requires a hardware matrix inverter which is extremely expensive, whereas Storkey is a rank-1 update that could plausibly be implemented in a small circuit."

---

### 8. Local & Incremental — Why it matters for hardware

> "Local means: $W_{ij}$ is determined by neurons $i$ and $j$ only. This maps to hardware as — each LUT only needs to know its own fan-in neighbourhood. No global communication during weight computation."

> "Incremental means: you can train by adding patterns one at a time, doing a bounded amount of work per pattern. For a hardware device that needs to store new memories after manufacture — say a medical device learning new patient-specific patterns — incremental rules mean you only need a small fixed update circuit, not a full retraining engine."

> "Pseudo-inverse has neither property. It's fine for offline use, but it can't be made into a simple hardware learning block."

---

### 9. Inference: The Voting Rule

$$s_i \leftarrow \text{sign}\left(\sum_{j \neq i} W_{ij} s_j\right)$$

> "Inference is a voting rule. Each neuron looks at all its neighbours, weights their votes by the connection strength, and flips to whichever side wins. That's it. No multiply-accumulate in the traditional sense — at fixed integer weights this becomes a lookup: given the binary states of all N−1 neighbours, what should neuron i be? That's exactly what a truth table encodes."

> "The sum $h_i = W_i \cdot s$ is a dot product. Its **sign** is the only thing that matters, not its magnitude. This is the key insight that makes LUT synthesis possible — we only need to classify the sign of an integer sum, not compute the sum itself."

---

### 10. Update Order: Async vs Sync

> "When neurons update, they can't all update simultaneously in hardware — some schedule must decide which neuron fires when. This choice is not cosmetic. It determines whether the circuit is **provably guaranteed to terminate**."

**Async (one neuron at a time):** Any fair ordering — cyclic, random — converges to a fixed point. The energy function argument proves it: a single-neuron flip can only decrease or maintain energy, never increase it. Finite state space + monotone energy = must terminate.

**Sync (all neurons simultaneously):** Goles & Olivos (1980) proved that with symmetric weights, synchronous update either converges OR falls into a **2-cycle** — two states that each map to the other, oscillating forever. Same weights, same initial state, different update mode → completely different behaviour.

> "We're using async-cyclic: neurons update in order 0→1→2→...→N−1, repeat. Fully deterministic, reproducible, and the only mode with a formal termination proof."

---

### 11. The 2-Cycle Problem (live demo)

```bash
python demo_sync_2cycle.py
```

> "Watch the top row — synchronous update. The state flips between two configurations and never settles. The energy oscillates between two fixed values instead of decreasing. The bottom row is the same network, same starting state, but async-cyclic — it converges to a fixed point in a few sweeps."

> "Detection is simple: compare state at time t with state at t−2. If they're equal and neither equals t−1, you're in a 2-cycle. A hardware implementation of sync mode would need this detector to avoid hanging."

> "This is why the primary design is async. Sync is useful for throughput benchmarking — it updates all N neurons in one clock cycle instead of N — but you need the 2-cycle detector and you lose the formal correctness guarantee."

---

### 12. Convergence Proof

For async update of neuron $i$:

$$\Delta E = E_\text{new} - E_\text{old} = -h_i \cdot \Delta s_i$$

Since $s_i$ flips to $\text{sign}(h_i)$, we always have $h_i \cdot \Delta s_i \geq 0$, so $\Delta E \leq 0$.

> "Every single-neuron update either lowers the energy or leaves it flat. Energy is bounded below. The state space is finite. Therefore the sequence must terminate at a fixed point. This is the formal correctness certificate — the hardware is provably correct by the energy argument, not just empirically tested."

---

### 13. LUT Synthesis Pipeline

```
W (N×N weights, Python)
    ↓  truth_table_gen.py
N truth tables (2^N rows each, .pla format)
    ↓  Espresso minimizer
N minimal SOP expressions
    ↓  sv_emitter.py
SystemVerilog always_comb blocks
    ↓  Quartus synthesis → Cyclone V
LUT-mapped netlist
```

> "Each neuron becomes one combinational block. Its input is all other neuron states; its output is one bit. We enumerate all 2^N input combinations — the truth table — then Espresso minimises the Boolean expression, and we emit SystemVerilog. No arithmetic at inference time, just logic."

> "The LUT framing is exact: a Xilinx/Intel LUT-K is literally a 2^K-row truth table in SRAM. We're synthesis-time-enumerating exactly what the FPGA would store anyway."

> "Feasibility: N≤10 is comfortable (~1K rows), N=16 is borderline (~64K rows, Espresso gets slow). Beyond that, we'd need sparse connectivity — keep only the F strongest weights per neuron, giving 2^F rows. That's Phase 2 scope."

---

### 14. Phase 1 / 2 / 3 roadmap

| Phase | Description | Status |
|---|---|---|
| **1** | Python training → truth tables → Espresso → clocked SystemVerilog → ModelSim/Quartus | Python ✓, synthesis pipeline next |
| **2** | Same truth tables → async combinational feedback (strip flip-flops) | After Phase 1 RTL validated |
| **3** | Ising machine — encode NP-hard problem as W, run hardware to find ground state | After Phase 2 |

> "Python side of Phase 1 is complete — training, benchmarking, capacity characterisation, demos all running. The next concrete step is `truth_table_gen.py` followed by the Espresso wrapper."

---

### 15. Demos (live, in order)

```bash
# 1 — recall grid: purple/gold, sklearn digits, energy curves
python demo_recall_grid.py

# 2 — animated per-neuron recall + weight graph
python demo_4x4_anim.py --nosave

# 3 — capacity threshold: below/near/above 0.138N
python demo_capacity.py

# 4 — sync 2-cycle vs async convergence
python demo_sync_2cycle.py
```

**Key numbers to land:**
- M=8 patterns, N=64: perfect recall in ≤ 2 sweeps = ≤ 128 clock cycles
- 2-cycle found in 8 random starts — not an edge case, a structural consequence of sync
- Storkey vs Hebbian: same 0.138N crossover below capacity, Storkey dramatically lower spurious rate above it

---

## Questions to ask

1. **N target:** "Go deep on N=10–12 with rigorous hazard analysis, or push N larger with sparse connectivity?"
2. **Hazard scope:** "Is RTL-vs-Python simulation match sufficient correctness, or do we need a formal multi-input hazard proof for the paper?"
3. **Espresso contact:** "Can you connect me with the grad student using Espresso?"

---

## Timing guide

| Section | Time |
|---|---|
| Slides 1–4 (intro, energy, learning table) | 5 min |
| Slides 5–8 (Hebbian, Storkey, Pseudo-inv, Local/incremental) | 8 min |
| Slides 9–12 (inference, update order, 2-cycle, convergence proof) | 8 min |
| Slides 13–14 (pipeline, roadmap) | 4 min |
| Demos | 8 min |
| Questions | 5 min |
| **Total** | **~38 min** |
