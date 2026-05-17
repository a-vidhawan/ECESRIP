# Step-by-Step Pipeline Walkthrough

This document walks through a complete run for N=8 neurons storing 3 patterns.

---

## Step 1 — Train the network

```bash
cd hopfield_hw/python
python hopfield_train.py --N 8 --P 3 --rule hebbian --seed 42 --out ../weights_8.npy
```

Output:
```
Trained HopfieldNetwork(N=8, patterns_stored=3) via hebbian rule.
Weight matrix:
[[ 0.     0.125  0.25  ...]
  ...]

  Pattern 0: flip bit 3 → ✓ recalled  (overlap=1.000)
  Pattern 1: flip bit 7 → ✓ recalled  (overlap=1.000)
  Pattern 2: flip bit 1 → ✓ recalled  (overlap=1.000)
Weights saved to ../weights_8.npy
```

---

## Step 2 — Enumerate truth tables

```bash
python truth_table_gen.py \
    --weights ../weights_8.npy \
    --out     ../tt \
    --json    ../tt/truth_tables.json
```

Output:
```
Loaded 8×8 weight matrix from ../weights_8.npy
Enumerating 2^8 = 256 input combinations per neuron …
CSVs written to ../tt/
JSON written to ../tt/truth_tables.json

Neuron | ON-set size | OFF-set size | const?
------------------------------------------------
      0 |         128 |          128 |      -
      1 |         136 |          120 |      -
      ...
```

Each CSV has 256 rows and looks like:

```
b_0, b_1, b_2, b_3, b_4, b_5, b_6, b_7, f_i
0,   0,   0,   0,   0,   0,   0,   0,   0
0,   0,   0,   0,   0,   0,   0,   1,   0
...
```

---

## Step 3 — Minimize Boolean functions

```bash
python logic_minimize.py --tt-json ../tt/truth_tables.json
```

Output:
```
Minimized Boolean covers:
  Neuron   0  (12 product terms):
    -1-10--1   →   (b[6] & ~b[4] & b[0])
    ...
  Neuron   1  (9 product terms):
    ...
```

The hazard-free augmentation adds extra consensus terms to the cover.  These appear as additional rows in the product-term list.

---

## Step 4 — Emit SystemVerilog

```bash
python sv_export.py \
    --tt-json ../tt/truth_tables.json \
    --out     ../rtl/neuron_logic_generated.sv
```

Output:
```
SystemVerilog written to ../rtl/neuron_logic_generated.sv  (8 neurons, 8 modules)
```

The generated file contains modules `neuron_update_0` … `neuron_update_7` and `neuron_logic_bank`.

---

## Alternative: run all steps at once

```bash
python pipeline.py \
    --N 8 --P 3 --rule hebbian --seed 42 \
    --out ../build_8
```

Output directory `../build_8/` will contain:
```
build_8/
├── weights.npy
├── truth_tables/
│   ├── tt_neuron_000.csv … tt_neuron_007.csv
│   └── truth_tables.json
├── covers/
│   └── covers.json
└── rtl/
    └── neuron_logic_generated.sv
```

---

## Step 5 — Simulate in C

```bash
cd hopfield_hw/c_sim
make
./hopfield_sim --N 8 --P 3 --rule hebbian --seed 42
```

Output:
```
=== Hopfield Network Simulation ===
  N=8  P=3  rule=hebbian  seed=42

Pattern 0: converged in 1 iter(s)  RECALL OK  overlap=1.0000
Pattern 1: converged in 2 iter(s)  RECALL OK  overlap=1.0000
Pattern 2: converged in 1 iter(s)  RECALL OK  overlap=1.0000
```

---

## Step 6 — Simulate in SystemVerilog

### Copy generated logic to RTL directory

```bash
cp ../build_8/rtl/neuron_logic_generated.sv ../rtl/
```

### Run unit testbench (exhaustive truth-table check)

```bash
# ModelSim
vlog -sv ../rtl/neuron_logic_generated.sv ../rtl/tb/tb_neuron_update.sv
vsim -do "vsim work.tb_neuron_update; run -all"
```

Expected output:
```
=== Neuron Update Unit Test  N=8 ===
Running exhaustive check over all 2^8 = 256 input vectors …
Results: 256 PASS  0 FAIL
=== All 256 input combinations VERIFIED ===
```

### Run top-level testbench

```bash
vlog -sv ../rtl/*.sv ../rtl/tb/tb_hopfield_top.sv
vsim -do "vsim work.tb_hopfield_top; run -all"
```

---

## Step 7 — Synthesize for FPGA

```bash
cd hopfield_hw
vivado -mode batch -source scripts/synth_vivado.tcl
```

The synthesis script targets Xilinx Artix-7 by default.  Edit `scripts/synth_vivado.tcl` to change the part.

---

## Parameterization guide

| N | Full enumeration? | Q-M time | Recommended |
|---|---|---|---|
| ≤ 8 | Yes (256 rows) | < 1 s | Run as-is |
| 9–12 | Yes (up to 4 096 rows) | < 10 s | Run as-is |
| 13–16 | Yes (up to 65 536 rows) | ~minutes | Consider Espresso |
| 17–20 | Yes (up to 1 M rows) | hours | Use per-neuron factoring |
| > 20 | No | — | BDD / symbolic approach |

For N > 16, replace `logic_minimize.py` with an Espresso interface (call the external `espresso` binary with the `.pla` file format, which `truth_table_gen.py` can emit by minor extension).
