# Phase 2 — Logic Minimization & RTL Generation

Takes the per-neuron truth tables from Phase 1 and produces synthesizable hardware.

## Pipeline

```
phase1/results/truth_tables/
        │
        ▼
  csv_to_pla.py          Convert truth tables → PLA files (one per neuron)
        │
        ▼
   Espresso               External logic minimizer (must be installed)
        │
        ▼
  pla_to_sv.py           Convert minimized PLA → SystemVerilog module
        │
        ▼
  hopfield_lut.sv         Synthesizable output → Vivado / Yosys
```

## Quick start

```bash
# 1. Convert truth tables to PLA
python phase2/csv_to_pla.py \
  --input phase1/results/truth_tables/storkey_s0p75/ \
  --out   phase2/pla/

# 2. Run Espresso on all PLAs
bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/

# 3. Convert minimized PLAs to SystemVerilog
python phase2/pla_to_sv.py \
  --input phase2/pla_min/ \
  --out   phase2/rtl/hopfield_lut.sv \
  --module hopfield_lut
```

## Neuron tracking

Each neuron i has its own PLA file: `neuron_{i:03d}.pla`

The input variable labels in each PLA reflect the **actual neuron indices**,
not just sequential column numbers. For a sparse neuron with neighbors [2, 5, 7]:

```
.ilb b_2 b_5 b_7     ← physical neuron indices, not positions 0/1/2
.ob  f_3             ← output: next state of neuron 3
```

This means the generated SV correctly references `s[2]`, `s[5]`, `s[7]`
rather than generic bit positions, and connects up cleanly in the top-level module.

## Installing Espresso

```bash
# Ubuntu/Debian
sudo apt-get install espresso

# macOS
brew install espresso

# From source
git clone https://github.com/chipsalliance/espresso
cd espresso && mkdir build && cd build && cmake .. && make
sudo cp espresso /usr/local/bin/
```
