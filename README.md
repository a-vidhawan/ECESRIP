# ECESRIP — LUT-Based Hopfield Neural Network on FPGA

**Student:** Aarav Vidhawan  
**Project:** SRIP (Student Research Internship Program)

## Research Goal

Implement a Hopfield neural network on an FPGA by converting each neuron's update logic into a Boolean truth table and synthesizing that directly into Look-Up Tables (LUTs). This eliminates multipliers entirely — the network becomes pure combinational logic.

The key insight: since Hopfield neurons take bipolar {+1, −1} inputs (binary), each neuron's update rule `s_i = sign(Σ w_ij · s_j)` is a Boolean function. Enumerate all 2^N input combinations → truth table → Espresso logic minimization → synthesize as SOP in SystemVerilog. The resulting circuit is an asynchronous Hopfield machine that iterates to a fixed point.

**Open research question:** No prior work has enumerated a Hopfield/RNN as truth tables for LUT hardware. The feedback (recurrent) aspect makes hazard-free logic design non-trivial — this is the novel contribution.

---

## Repository Layout

```
ECESRIP/
├── research/
│   ├── papers/
│   │   ├── hopfield_hardware.md   # FPGA Hopfield hardware papers
│   │   ├── ising_machines.md      # Ising machines & NP-complete solvers
│   │   └── lut_approach.md        # LUT-based NN papers (NullaNet, LogicNets, etc.)
│   └── notes/
│       └── research_plan.md       # Overall research plan & open questions
├── sim/
│   └── v1/                        # Claude v1 Python simulation framework
│       ├── python/                # HopfieldNetwork class, truth table gen, pipeline
│       ├── rtl/                   # SystemVerilog RTL (top, neuron bank, testbenches)
│       ├── c_sim/                 # C simulation for fast sweep
│       ├── docs/                  # Architecture notes, hazard analysis, pipeline docs
│       └── scripts/               # run_pipeline.sh, synth_vivado.tcl
├── training/
│   ├── README.md                  # Benchmark research summary
│   ├── datasets/
│   │   └── README.md              # Dataset catalogue & usage guide
│   └── benchmarks/
│       └── README.md              # Benchmark protocol & metrics
└── hardware/
    └── README.md                  # Hardware implementation (future)
```

---

## Iterative Research Workflow

```
Train Hopfield net (Python)
        │
        ▼
Generate truth tables per neuron
        │
        ▼
Boolean minimization (Espresso, hazard-free)
        │
        ▼
Export SOP → SystemVerilog
        │
        ▼
FPGA synthesis + timing analysis (Vivado)
        │
        ▼
Evaluate: recall accuracy, basin of attraction,
          spurious states, convergence speed
        │
        └──► Compare vs Python model (ground truth)
             Sweep N and M, find feasible ranges
             ─► Adapt to Ising Machine formulation
```

---

## Quick Start

```bash
# Install Python deps
pip install numpy scipy

# Run full pipeline: N=8 neurons, P=1 pattern, Hebbian rule
cd sim/v1
python python/pipeline.py --N 8 --P 1 --rule hebbian --out out/

# Run benchmarks
python python/pipeline.py --N 10 --P 14 --rule storkey --out out/
```

See `sim/v1/docs/pipeline.md` for full CLI reference.

---

## Key Constraints

| N (neurons) | Truth table rows | Feasibility |
|---|---|---|
| ≤ 10 | ≤ 1,024 | Comfortable, fits distributed LUTs |
| ≤ 14 | ≤ 16,384 | Feasible, may need BRAM |
| ≤ 16 | ≤ 65,536 | Borderline; Espresso runtime grows |
| > 16 | > 65K | Requires sparse connectivity (F strongest weights) |

Capacity rule: reliably store M ≈ 0.14 × N patterns (Hebbian); Storkey achieves higher quality near saturation.
