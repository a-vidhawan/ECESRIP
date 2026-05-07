# ECESRIP — LUT-Based Hopfield Neural Network on FPGA

**Student:** Aarav Vidhawan  
**Project:** SRIP (Student Research Internship Program)

## Research Goal

Implement a Hopfield network on FPGA by converting each neuron's update rule $s_i = \text{sign}(\sum_j w_{ij} s_j)$ into a Boolean truth table and synthesizing it into LUTs — no multipliers, pure combinational logic. The feedback (recurrent) structure makes hazard-free design non-trivial; this is the novel contribution.

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
│       ├── research_plan.md       # Three-phase project plan & open questions
│       └── theory.md              # Theoretical foundations (with proofs)
├── sim/
│   ├── README.md                  # How to run training, benchmarks, pipeline
│   ├── python/                    # Training, datasets, benchmarking
│   └── requirements.txt
├── training/
│   ├── datasets/README.md
│   └── benchmarks/README.md
└── hardware/
    └── README.md                  # Hardware implementation (Phase 1+2)
```

---

## Three-Phase Plan

```
Phase 1 — Clocked (Baseline)
  Python model → truth tables → Espresso (standard) → clocked SV → ModelSim/Quartus

Phase 2 — Async Combinational
  Same truth tables → Espresso -Dhazard → strip flip-flops → wire feedback directly
  Compare vs Phase 1 to isolate async hazard effects

Phase 3 — Ising Machine
  Set W = J_ij from problem instance → same pipeline → fixed point ≈ solution
```

See `research/notes/research_plan.md` for full details.

---

## Key Constraints

| $N$ | Truth table rows | Feasibility |
|---|---|---|
| ≤ 10 | ≤ 1,024 | Easy — fits distributed LUTs |
| ≤ 14 | ≤ 16,384 | Feasible |
| ≤ 16 | ≤ 65,536 | Borderline — Espresso runtime grows |
| > 16 | > 65 K | Sparse connectivity required |

Capacity: $M \lesssim 0.14N$ (Hebbian), Storkey achieves better quality at the same load.
