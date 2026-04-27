# Hopfield Network — Hardware Implementation Pipeline

A research-grade, fully parameterized pipeline that takes you from trained Hopfield-network weights all the way to **hazard-free SystemVerilog RTL** ready for FPGA or ASIC synthesis.

## Pipeline at a Glance

```
Patterns (binary / bipolar)
        │
        ▼
 [Python] hopfield_train.py
   Hebbian / Storkey learning → weight matrix W (N×N)
        │
        ▼
 [Python] truth_table_gen.py
   Enumerate all 2^N input states → per-neuron truth tables
        │
        ▼
 [Python] logic_minimize.py
   Quine-McCluskey minimization + hazard-free consensus cover
        │
        ▼
 [Python] sv_export.py
   Emit parameterized SystemVerilog from minimized Boolean cover
        │
        ▼
 [SystemVerilog] rtl/
   Hazard-free, synthesizable RTL (FPGA / ASIC)
        │
        ▼
 [C/C++] c_sim/
   Independent bit-accurate simulation for cross-verification
```

## Directory Structure

```
hopfield_hw/
├── README.md                   ← this file
├── docs/
│   ├── architecture.md         ← system architecture & design decisions
│   ├── pipeline.md             ← step-by-step pipeline walkthrough
│   └── hazard_analysis.md      ← hazard theory & elimination strategy
├── python/
│   ├── hopfield_train.py       ← Hebbian / Storkey weight learning
│   ├── truth_table_gen.py      ← enumerate neuron update → truth tables
│   ├── logic_minimize.py       ← Quine-McCluskey + hazard-free consensus
│   ├── sv_export.py            ← emit SystemVerilog from Boolean cover
│   └── pipeline.py             ← end-to-end driver script
├── c_sim/
│   ├── hopfield.h              ← shared types & API
│   ├── hopfield_train.c        ← weight computation in C
│   ├── hopfield_sim.c          ← async / sync network simulation
│   └── Makefile
├── rtl/
│   ├── hopfield_top.sv         ← top-level parameterized module
│   ├── neuron_bank.sv          ← neuron state registers
│   ├── weight_rom.sv           ← packed weight storage
│   ├── update_ctrl.sv          ← control FSM (async / sync update)
│   └── tb/
│       ├── tb_hopfield_top.sv  ← top-level testbench
│       └── tb_neuron_update.sv ← unit testbench for update logic
└── scripts/
    ├── run_pipeline.sh         ← train → TT → minimize → SV in one shot
    └── synth_vivado.tcl        ← Xilinx Vivado synthesis script
```

## Quick Start

```bash
# 1. Install Python deps
pip install numpy

# 2. Run the full pipeline (example: 8 neurons, store 3 patterns)
cd hopfield_hw
./scripts/run_pipeline.sh --neurons 8 --patterns data/patterns_8.txt

# 3. Simulate in C
cd c_sim && make && ./hopfield_sim

# 4. Simulate in SystemVerilog (requires ModelSim / Verilator)
cd rtl && vsim -do "do tb/tb_hopfield_top.sv"
```

## Parameterization

The single knob is `N` (number of neurons). Everything else scales:

| N   | Truth-table rows | Recommended flow              |
|-----|-----------------|-------------------------------|
| ≤ 8  | ≤ 256           | Full enumeration, Q-M exact   |
| 9–16 | ≤ 65 536        | Full enumeration, Q-M + Espresso |
| 17–20 | ≤ 1 M          | Per-neuron factored enumeration |
| > 20 | Astronomical   | Symbolic / BDD-based approach  |

## License

MIT — research use, attribution appreciated.
