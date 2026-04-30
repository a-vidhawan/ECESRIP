# GitHub Survey: Hopfield Network Implementations

Surveyed April 2026. Evaluated against our project needs:
- Bipolar {-1, +1} states (not binary {0,1})
- Parameterizable N (neurons) and M (patterns)
- Hebbian and/or Storkey training
- Async update (required for hardware-accurate simulation)
- Capacity/basin-of-attraction evaluation
- No deep learning framework dependency (we need truth table export, not backprop)

---

## Tier 1 — Most Relevant

### 1. TomMakesThings/Hopfield-Network
**Link:** https://github.com/TomMakesThings/Hopfield-Network  
**Stars:** ~200 | **Language:** Python (Jupyter notebook)

**What it does:**
- Trains on both Hebbian and Storkey rules
- Evaluates capacity by sweeping M from 1 to saturation
- Tracks spurious state rate and recall accuracy at each load level
- Visualizes weight matrix, stored patterns, and corrupted recall

**Pros:**
- Best capacity-analysis code in any public repo — sweeps M/N ratio and plots where recall breaks down
- Both Hebbian and Storkey implemented and compared side-by-side
- Spurious state detection built in (checks if attractor ∉ stored pattern set or its negatives)
- Uses bipolar {-1, +1} states — matches our hardware target exactly
- Clear, readable code with mathematical commentary

**Cons:**
- Jupyter notebook only — not importable as a library
- No async vs sync distinction (uses synchronous update only)
- No basin-of-attraction sweep (doesn't vary noise level systematically)
- No CSV/JSON export of results for downstream processing
- Not structured for large N sweeps (no vectorized 2^N enumeration)

**Verdict:** Best starting point for the capacity analysis and spurious state logic. Refactor into a proper class.

---

### 2. takyamamoto/Hopfield-Network
**Link:** https://github.com/takyamamoto/Hopfield-Network  
**Stars:** ~400 | **Language:** Python

**What it does:**
- Clean class-based implementation
- Both async and sync update rules
- Pattern corruption and recall test
- Visualizes convergence on image patterns (faces, animals)

**Pros:**
- Best async implementation — random neuron update order, correct convergence check
- Bipolar states
- Visual convergence demo is useful for presenting to professor
- Clean separation between train() and update() methods

**Cons:**
- Only Hebbian learning rule (no Storkey)
- No quantitative benchmark output — visual only
- No sweep over M or noise level
- No energy function tracking
- Not parameterizable beyond N (no M sweep utilities)

**Verdict:** Best async update implementation. Borrow the update loop.

---

### 3. zftan0709/Hopfield-Network
**Link:** https://github.com/zftan0709/Hopfield-Network  
**Stars:** ~50 | **Language:** Python

**What it does:**
- Directly compares async vs sync update on the same stored patterns
- Shows that sync leads to oscillation at higher loads, async does not
- Measures convergence iterations for both

**Pros:**
- The only public repo that directly benchmarks async vs sync convergence behavior
- Shows oscillation conditions — critical for our hardware (async is what we implement in LUT combinational logic)
- Convergence iteration count is tracked per-run

**Cons:**
- Hebbian only
- No capacity sweep
- Small N only (demo-scale)
- No energy function

**Verdict:** Use for the async vs sync convergence comparison experiment.

---

### 4. DenseLance/hopfield-networks
**Link:** https://github.com/DenseLance/hopfield-networks  
**Stars:** ~100 | **Language:** Python

**What it does:**
- Image restoration (Fashion MNIST)
- NP-hard problem mapping (graph coloring, TSP as Hopfield energy)
- Both sync and async update
- Demonstrates 100% recall accuracy on small Fashion MNIST subset

**Pros:**
- NP-hard problem formulation — directly relevant for Ising machine adaptation phase
- Shows how to set W from a problem instance rather than learning (relevant for our Ising work)
- Fashion MNIST as a real-world dataset for demo
- Energy minimization framing is explicit

**Cons:**
- No Storkey learning
- No systematic capacity/basin evaluation
- Code is notebook-style, hard to adapt
- Fashion MNIST at N=784 — way too large for our truth table approach without sparsity

**Verdict:** Reference for NP-hard/Ising adaptation phase. Mine the problem-to-weight-matrix formulation code.

---

### 5. felix-andreas/hopfieldnetwork (andreasfelix)
**Link:** https://github.com/andreasfelix/hopfieldnetwork  
**Stars:** ~80 | **Language:** Python

**What it does:**
- Clean, minimal, installable Python package (`pip install hopfieldnetwork`)
- Hebbian only, bipolar states
- Energy function tracking per step

**Pros:**
- Only one that's an actual pip-installable package
- Energy function tracked per update step — useful for convergence monitoring
- Very clean API: `net = HopfieldNetwork(n=100); net.train(patterns); net.retrieve(query)`

**Cons:**
- Hebbian only, no Storkey
- No evaluation metrics beyond visual
- No capacity sweep
- Single-threaded, no vectorization

**Verdict:** Clean API design to emulate. Energy tracking is a good feature to add to ours.

---

### 6. ml-jku/hopfield-layers ("Hopfield Networks is All You Need")
**Link:** https://github.com/ml-jku/hopfield-layers  
**Stars:** ~800 | **Language:** Python/PyTorch

**What it does:**
- Modern (continuous) Hopfield network with exponential capacity
- PyTorch layers for embedding into deep networks
- Attention-mechanism interpretation of Hopfield update rule
- Bit Pattern Set benchmark dataset included

**Pros:**
- Exponential capacity — stores exp(N/2) patterns vs ~0.14N for classic
- Best-maintained, most-starred Hopfield repo
- Bit Pattern Set dataset is clean and well-defined for benchmarking
- Shows the mathematical connection between Hopfield retrieval and transformer attention

**Cons:**
- Continuous states — NOT binary/bipolar. Incompatible with our LUT truth table approach.
- Requires PyTorch — heavy dependency
- Single-step convergence (one update = done) — no iterative async dynamic to enumerate
- Not useful for truth table generation since the update function is not a Boolean function

**Verdict:** Interesting for context and future directions, but NOT usable for our hardware project. The update rule is not a Boolean function and cannot be enumerated as a truth table.

---

### 7. kencyke/hopfield-mnist
**Link:** https://github.com/kencyke/hopfield-mnist  
**Stars:** ~30 | **Language:** Python

**What it does:**
- Stores binarized MNIST digit prototypes (one per class, N=784)
- Tests recall on noisy/corrupted queries
- Hebbian training

**Pros:**
- Shows the MNIST binarization pipeline end-to-end
- Good demo for showing what the network "remembers"

**Cons:**
- N=784 — completely impractical for our truth table approach
- Hebbian only
- No quantitative benchmarks, no sweep

**Verdict:** Reference only for the MNIST binarization code. Our hardware demo will use N≤16.

---

## Summary Table

| Repo | Rules | Update | N sweep | M sweep | Noise sweep | Spurious | Energy | Usable for HW? |
|---|---|---|---|---|---|---|---|---|
| TomMakesThings | Hebb+Storkey | Sync | No | ✓ | No | ✓ | No | Partial |
| takyamamoto | Hebb | **Async+Sync** | No | No | No | No | No | ✓ |
| zftan0709 | Hebb | Async+Sync | No | No | No | No | No | ✓ |
| DenseLance | Hebb | Both | No | No | No | No | ✓ | Reference |
| andreasfelix | Hebb | Async | No | No | No | No | ✓ | Partial |
| ml-jku | — | Continuous | — | — | — | — | — | ✗ |
| kencyke | Hebb | Sync | No | No | No | No | No | Reference |

---

## What None of Them Have

All existing repos are missing at least one thing we need:

1. **Truth table export** — none generate PLA/CSV truth tables for logic synthesis
2. **Full N/M/noise sweep with CSV output** — needed to characterize hardware feasibility
3. **Bipolar-to-binary mapping for enumeration** — `b_j = (s_j+1)/2` for truth table rows
4. **Storkey + async** in the same codebase
5. **Hardware-accurate simulation** — deterministic async update matching what the RTL does

Our `training/` framework fills all of these gaps. The key repos to draw from are TomMakesThings (capacity/spurious logic), takyamamoto (async update loop), and zftan0709 (async vs sync comparison).
