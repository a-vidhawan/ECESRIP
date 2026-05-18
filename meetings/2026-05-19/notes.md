# Meeting Notes — 2026-05-19

**Supervisor meeting**

---

## Agenda

1. Slides walkthrough *(Google Slides — share screen)*
2. Live demos
3. Open questions / next steps sign-off

---

## 1. Slides (Google Slides — walk through first)

Cover in order:

- Hopfield network recap: energy function, bipolar neurons, weight matrix
- Hebbian vs Storkey learning rules (one slide each with the math)
- Update order: why async-cyclic is the only hardware-safe mode
- LUT synthesis pipeline: W → truth table → Espresso → SOP → SystemVerilog
- Phase 1 / 2 / 3 roadmap

---

## 2. Live Demos

Run from `meetings/2026-05-11/demo/`:

```bash
# 1. Recall grid — purple/gold, 8 sklearn digits, energy curves
python demo_recall_grid.py

# 2. Animated per-neuron recall — 4×4 digits, weight graph
python demo_4x4_anim.py --nosave

# 3. Capacity threshold — what happens above 0.138N
python demo_capacity.py
```

**Key number to quote:** network stores 8 patterns (M=8 < 0.138×64 ≈ 8.8), corrupts each by 25%, recovers all perfectly in ≤ 2 sweeps = ≤ 128 clock cycles.

---

## 3. Demo Program Capabilities

| Demo | N | Patterns | Rule | Visual output | Key point shown |
|---|---|---|---|---|---|
| `demo_recall_grid.py` | 64 | 8 sklearn digits (0–7) | Storkey | Purple/gold grid: corrupted → recalled + energy curve per step | Clean recall below capacity; energy monotone |
| `demo_4x4_anim.py` | 16 | 3 hand-crafted digits (0,1,7) | Storkey | Animated: pixel grid + weight graph, per-neuron update | Async-cyclic update order; weight edge signs |
| `demo_8x8.py` | 64 | 3 hand-crafted digits (0,1,7) | Storkey | Static: stored patterns + energy-vs-sweep panel | Energy convergence trace |
| `demo_4x4.py` | 16 | 3 hand-crafted digits (0,1,7) | Storkey | Static PNG + terminal trace | Step-by-step convergence, clock cycle count |
| `demo_random.py` | 16 | 2 random patterns | Storkey | Terminal only: energy per sweep | Minimal working example; energy argument |
| `demo_capacity.py` | 64 | 4 / 9 / 14 hand-crafted chars | Storkey | 3-row comparison: below/near/above threshold | Spurious state at M > 0.138N; red × on failure |
| `demo_capacity_sweep.gif` | 64 | 1→14 (animated) | Storkey | Animated GIF: M sweep showing recall cliff | Capacity threshold crossing |

---

## 4. Open Questions

### Q1 — N target for hardware
- N ≤ 10: comfortable, fits distributed LUTs
- N ≤ 16: feasible, Espresso borderline slow
- N > 16: needs sparse connectivity (keep F strongest weights → $2^F$ rows)

*"Are we going deep on a fixed N (say N=10 or N=12) — rigorous hazard analysis, FPGA timing, basin characterisation — or push N as large as possible?"*

### Q2 — Hazard analysis scope
- Espresso `-Dhazard` covers single-variable transitions only
- Phase 2 (combinational feedback): multiple inputs may change near-simultaneously
- Option (a): informal argument via energy function
- Option (b): Speed-Independent or QDI synthesis (changes tool entirely)

*"Is engineering-level RTL-vs-Python match sufficient, or do we need a formal multi-input hazard proof?"*

### Q3 — Espresso contact
*"Can you connect me with the grad student using Espresso? Even a 30-min call to see their invocation and output format."*

---

## 5. Next Steps (pending sign-off)

- [ ] `truth_table_gen.py` — enumerate $2^N$ rows per neuron, export `.pla`
- [ ] Espresso wrapper — call from Python, parse SOP output
- [ ] SystemVerilog emitter — SOP → `always_comb` blocks
- [ ] ModelSim testbench — compare RTL output to Python model state-by-state
- [ ] Confirm FPGA target: Cyclone V, Quartus + ModelSim
