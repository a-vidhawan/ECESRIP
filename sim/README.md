# sim/ — Training, Benchmarking, and Pipeline

## Setup

```bash
cd sim
pip install -r requirements.txt
```

`scikit-learn` and `scikit-image` are only needed for MNIST datasets; `numpy` alone is sufficient for random-pattern benchmarks.

---

## Quick Start

```bash
cd sim/python

# Run the full benchmark sweep (random patterns, Storkey, async-cyclic)
python benchmark.py

# Results saved to sim/results/benchmark_<rule>_<mode>_<dataset>_<timestamp>.csv
```

---

## Changing Parameters

All knobs live at the top of each file — one line per setting.

### Learning rule (`hopfield_net.py` or `benchmark.py`)

```python
RULE = STORKEY   # change to HEBBIAN for Hebbian learning
```

### Update mode (`hopfield_net.py` or `benchmark.py`)

```python
UPDATE_MODE = ASYNC_CYCLIC   # 1 — sequential cyclic (default, hardware-aligned)
                             # 2 — ASYNC_RANDOM: random permutation each sweep
                             # 3 — SYNC: fully synchronous (risk of 2-cycles)
```

### Dataset (`benchmark.py`)

```python
DATASET = RANDOM    # random ±1 patterns (any N)
                    # MNIST_8  — binarized MNIST at 8×8  (N=64, auto-downloads)
                    # MNIST_28 — binarized MNIST at 28×28 (N=784)
```

### Sweep parameters (`benchmark.py`)

```python
N_VALUES    = [6, 8, 10, 12, 14, 16]   # neuron counts
MAX_LOAD    = 0.30                      # sweep M up to MAX_LOAD * N
NOISE_FRACS = [0.0, 0.05, ..., 0.40]  # bit-flip fractions
N_TRIALS    = 50                        # trials per (N, M, noise) point
N_SPURIOUS  = 100                       # random-init trials for spurious rate
MAX_SWEEPS  = 40                        # max update sweeps per convergence run
```

---

## Using the Classes Directly

```python
from hopfield_net import HopfieldNetwork, STORKEY, ASYNC_CYCLIC
from datasets import load, add_noise, RANDOM
import numpy as np

net = HopfieldNetwork(N=10, rule=STORKEY, update_mode=ASYNC_CYCLIC)

patterns = load(RANDOM, N=10, M=5, seed=0)
net.train(patterns)

rng = np.random.default_rng(1)
noisy = add_noise(patterns[0], n_flips=2, rng=rng)
s_final, n_sweeps, converged = net.run(noisy)

print(s_final, n_sweeps, converged)
print("Energy:", net.energy(s_final))
```

---

## Output Format

Each row in the CSV corresponds to one `(N, M, noise_frac)` combination:

| Column | Description |
|---|---|
| `N`, `M`, `load` | Network size, patterns stored, load ratio $M/N$ |
| `noise_frac`, `noise_k` | Bit-flip fraction and absolute count |
| `recall_accuracy` | Fraction of trials recovering the original pattern |
| `basin_width` | Max $k$ where `recall_accuracy ≥ 0.90` |
| `spurious_rate` | Fraction of random inits landing in a non-stored attractor |
| `mean_convergence_iters` | Mean sweeps to reach a fixed point |
| `converged_fraction` | Fraction of runs that converged within `MAX_SWEEPS` |

---

## File Map

```
sim/
├── README.md              ← this file
├── requirements.txt
├── python/
│   ├── hopfield_net.py    # HopfieldNetwork class + update mode constants
│   ├── datasets.py        # load(), random_patterns(), add_noise(), MNIST loaders
│   └── benchmark.py       # sweep + metrics + CSV export
├── data/                  # MNIST cache (created on first MNIST run)
└── results/               # benchmark CSVs (created on first benchmark run)
```
