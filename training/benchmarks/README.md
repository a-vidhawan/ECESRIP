# Benchmarks

## Protocol

### Step 1: Generate and Train

```python
from hopfield_train import HopfieldNetwork, random_patterns

N = 10
M = 1   # start at M=1, sweep up to ~0.3N
patterns = random_patterns(N, M, seed=42)

net_hebb = HopfieldNetwork(N)
net_hebb.train_hebbian(patterns)

net_stor = HopfieldNetwork(N)
net_stor.train_storkey(patterns)
```

### Step 2: Test Recall Under Noise

```python
def recall_accuracy(net, patterns, num_flips, num_trials=100, max_iters=50):
    """Fraction of trials where the network correctly recalls the original pattern."""
    N = net.N
    correct = 0
    total = 0
    rng = np.random.default_rng(0)
    for pattern in patterns:
        for _ in range(num_trials):
            noisy = pattern.copy()
            flip_idx = rng.choice(N, size=num_flips, replace=False)
            noisy[flip_idx] *= -1
            result = net.update_async(noisy, max_iters=max_iters)
            if np.array_equal(result, pattern):
                correct += 1
            total += 1
    return correct / total
```

### Step 3: Sweep Parameters

```python
results = []
for N in [8, 10, 12, 14]:
    for M in range(1, int(0.3 * N) + 1):
        patterns = random_patterns(N, M)
        net = HopfieldNetwork(N)
        net.train_hebbian(patterns)
        for k in range(1, N // 2 + 1):
            acc = recall_accuracy(net, patterns, num_flips=k)
            results.append({'N': N, 'M': M, 'k': k, 'accuracy': acc, 'rule': 'hebbian'})
```

---

## Metrics

| Metric | Definition | Target |
|---|---|---|
| **Recall accuracy** | P(converge to correct pattern \| k flips) | > 95% at k=1 for M ≤ 0.14N |
| **Basin of attraction width** | Max k with recall accuracy > 95% | Maximize |
| **Spurious state rate** | P(converge to non-stored state) | Minimize |
| **Convergence iterations** | Mean async updates to fixed point | Minimize (faster = better hardware) |
| **Capacity ratio** | M/N at which recall drops below 95% | Should match ~0.14 for Hebbian |

---

## Comparison: Python Model vs SystemVerilog

The ground truth is the Python model. The SystemVerilog output from the pipeline must produce identical fixed-point attractors.

```bash
# Run Python model and log all attractors
python python/pipeline.py --N 8 --P 1 --rule hebbian --out out/

# Compare attractor outputs (after RTL simulation in Vivado/ModelSim)
# The testbench tb_hopfield_top.sv logs all state sequences to a CSV
# diff out/python_attractors.csv out/rtl_attractors.csv
```

**Expected result:** Zero differences. Any discrepancy indicates a bug in truth table generation, logic minimization, or SystemVerilog export.

---

## Known Results from Literature

- Hebbian: ~0.138N reliable capacity (Hopfield 1982)
- Storkey: similar capacity but higher recall quality at saturation (Storkey & Valabregue 1999)
- Hebbian spurious states: ~2^(0.6N) spurious attractors exist at capacity
- Basin of attraction: ~N/6 bits of noise tolerance at M = 0.05N (well below capacity)
- Convergence: typically < 10 async update cycles for N ≤ 20
