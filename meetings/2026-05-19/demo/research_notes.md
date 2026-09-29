# Hopfield Network Research Notes
## May 19 Meeting Prep — Deep Dive: Training & Inference

---

## 1. What Is a Binary (Classic) Hopfield Network?

A Hopfield Network is a **fully-connected recurrent neural network** used as an associative memory (content-addressable memory). It stores a set of binary or bipolar patterns and retrieves them from partial or noisy inputs.

**Key properties:**
- **Neurons:** N units, each with state s_i ∈ {-1, +1} (bipolar) or {0, 1} (binary). This codebase uses **bipolar** convention.
- **Weights:** Symmetric N×N matrix W, with W_ij = W_ji and W_ii = 0 (no self-connections).
- **Deterministic dynamics:** Updates follow a threshold rule — no stochastic component.
- **Energy function (Lyapunov):** Guarantees convergence under asynchronous updates.

**Binary vs. Continuous Hopfield Networks:**

| Feature | Binary / Classic (this project) | Continuous (Modern) |
|---|---|---|
| Neuron states | ±1 (bipolar) or {0,1} | Real-valued, sigmoidal |
| Energy function | E = −½ sᵀWs | E = −½ xᵀWx + Σ g(x_i) |
| Training rule | Hebbian / Storkey | Same; modern variant uses exponential energy |
| Capacity | ~0.138N (Hebbian) | Much higher (exponential in feature dim) |
| Hardware mapping | Direct (binary RTL) | Requires DAC/ADC in analog HW |
| Convergence | Always (async update) | Always (if W symmetric, positive semi-definite) |

The **modern Hopfield Network** (Ramsauer et al., 2020) replaces the quadratic energy with an exponential, yielding exponential memory capacity — but it is continuous and harder to implement in digital hardware. This project focuses on the **classic binary version** for hardware synthesis.

---

## 2. Training Methods

### 2.1 Hebbian Learning (Outer-Product Rule)

The simplest and most widely used training rule. Introduced by Hopfield (1982).

**Formula:**
```
W = (1/N) Σ_μ  ξ^μ (ξ^μ)ᵀ        (sum over all P patterns)
W_ii = 0  (diagonal zeroed)
```

**In code (`hopfield_train.py`):**
```python
def train_hebbian(self, patterns):
    W = np.zeros((self.N, self.N))
    for xi in patterns:
        W += np.outer(xi, xi)
    W /= self.N
    np.fill_diagonal(W, 0.0)
    self.W = W
```

**Properties:**
- **One-shot learning** — the full weight matrix is computed in a single pass.
- Patterns are stored as local energy minima.
- **Capacity limit:** ~0.138N patterns before recall degrades (Amit et al., 1985).
  - For N=64 neurons: ~8 patterns reliably stored.
  - For N=256 neurons: ~35 patterns.
- **Spurious memories:** Other energy minima exist (e.g., bitwise inverses of stored patterns). These are false attractors.
- **Interference:** With P close to capacity, patterns begin to overlap in weight space and contaminate each other.

**Why it works:** Each term ξ_i ξ_j contributes positively to W_ij when two neurons agree in a pattern, and negatively when they disagree. At recall time, the network is driven toward the state with the highest overlap with the query.

---

### 2.2 Storkey Learning Rule

An improved rule proposed by Storkey & Valabregue (1999) that achieves higher capacity.

**Formula (incremental per pattern):**
```
W ← W + (1/N) [ξξᵀ − hξᵀ − ξhᵀ]
where  h_i = Σ_{k≠i} W_ik ξ_k  (pre-synaptic local field)
W_ii = 0  after each update
```

**In code (`hopfield_train.py`):**
```python
def train_storkey(self, patterns):
    W = np.zeros((self.N, self.N))
    for xi in patterns:
        h = W @ xi - np.diag(W) * xi   # local field (exclude diagonal)
        dW = np.outer(xi, xi) - np.outer(h, xi) - np.outer(xi, h)
        W += dW / self.N
        np.fill_diagonal(W, 0.0)
    self.W = W
```

**Properties:**
- **Sequential (online) learning** — weight matrix is updated one pattern at a time.
- **Capacity:** ~0.14N to ~0.22N depending on noise regime (slightly better than Hebbian).
- **Better near saturation:** Fewer spurious attractors near capacity.
- **Trade-off:** More expensive to compute (two extra matrix-vector products per pattern), and order-dependent (patterns added later are favored slightly).

**Key difference from Hebbian:** The correction terms `hξᵀ + ξhᵀ` subtract away interference from previously stored patterns, acting like a local error signal.

---

### 2.3 Pseudo-Inverse Rule (for reference)

Not in this codebase but worth knowing:

```
W = (1/N) Ξ (ΞᵀΞ)⁻¹ Ξᵀ    where Ξ = [ξ¹, ξ², ..., ξᴾ]
```

- **Exact recall** up to N patterns if patterns are linearly independent.
- Requires computing a matrix pseudo-inverse — expensive (O(N²P) or worse).
- Rarely used in hardware because it requires global information.

---

### 2.4 Training Method Comparison

| Property | Hebbian | Storkey | Pseudo-Inverse |
|---|---|---|---|
| **Capacity (α = P/N)** | ~0.138 | ~0.14–0.22 | 1.0 (exact up to N) |
| **Computation** | O(N²P) | O(N²P) | O(N²P + inversion) |
| **One-shot?** | Yes | No (sequential) | Yes (batch) |
| **Error correction** | None | Partial | Perfect (within capacity) |
| **Spurious states** | Many | Fewer | Fewest |
| **Hardware-friendly?** | ✅ Very | ✅ Yes | ⚠️ Expensive |
| **In this codebase** | ✅ Implemented | ✅ Implemented | ❌ Not implemented |

**For our use case (hardware synthesis):** Hebbian is preferred for its simplicity and the weight matrix being computed in one shot. Storkey is useful when pattern capacity near the limit is needed.

---

## 3. The Inference (Retrieval) Process

### 3.1 How Retrieval Works

Given a **probe state** s (which may be noisy or partial), the network iteratively updates neurons until it reaches a **fixed point** (energy minimum) that corresponds to a stored pattern.

**The update rule for each neuron:**
```
s_i ← sign(Σ_j W_ij s_j)   =   sign(h_i)
where h_i = Σ_j W_ij s_j   is the local field / net input to neuron i
```

- If h_i > 0: s_i becomes +1
- If h_i < 0: s_i becomes -1
- If h_i = 0: tie-break (convention: +1)

### 3.2 Asynchronous Update (the standard)

Neurons are updated **one at a time**, chosen at random (or in a fixed sequence):

```python
def update_async(self, state, steps, rng):
    s = state.copy()
    for _ in range(steps):
        i = rng.integers(0, self.N)   # pick random neuron
        h = self.W[i] @ s             # compute local field
        s[i] = 1 if h >= 0 else -1   # threshold update
    return s
```

**Why asynchronous converges:** Under random asynchronous updates with a symmetric weight matrix and zero diagonal, the energy function E = −½ sᵀWs is **monotonically non-increasing**. Each update either decreases energy or keeps it the same. Since the state space is finite, convergence is guaranteed.

**In C (`hopfield_sim.c`):**
```c
void hopfield_update_neuron(HopfieldNet *net, int i) {
    double h = 0.0;
    for (int j = 0; j < net->N; j++)
        h += HOP_W(net, i, j) * (double)net->state[j];
    net->state[i] = (h >= 0.0) ? 1 : -1;
}
```

### 3.3 Synchronous Update

All neurons updated **simultaneously** from the current state:

```python
def update_sync(self, state):
    return np.sign(self.W @ state)
```

- Faster per-step (parallel hardware-friendly).
- Does NOT always decrease energy → can oscillate between two states (2-cycles).
- In hardware (RTL), this maps directly to a one-clock-cycle combinational update.
- Convergence to fixed points is not guaranteed, but 2-cycles are bounded.

### 3.4 Fixed-Point Detection

In the hardware FSM (`update_ctrl.sv`):
```
IDLE → COMPUTE → CHECK_FP → DONE
```
At `CHECK_FP`, the state word before and after the update round is compared. If identical → convergence.

### 3.5 Energy Function (Lyapunov)

```
E(s) = −½ sᵀ W s = −½ Σ_{i,j} W_ij s_i s_j
```

**Key properties:**
- E is bounded below (W is a finite symmetric matrix).
- Each async update decreases E or leaves it unchanged.
- Fixed points correspond to local minima of E.
- Stored patterns are (ideally) the global or deep local minima.
- Spurious memories are shallow local minima.

**Energy proof sketch:** When neuron i flips from s_i to s_i':
```
ΔE = −(s_i' − s_i) · h_i
```
Since s_i' = sign(h_i), if h_i > 0 then s_i' = +1 ≥ s_i, so (s_i' − s_i) ≥ 0, and ΔE = −(positive)(positive) ≤ 0.

---

## 4. Binary Encoding for Hardware

The codebase uses a bipolar-to-binary mapping for hardware:

```
Bipolar:  s_j ∈ {-1, +1}
Binary:   b_j = (s_j + 1) / 2  ∈ {0, 1}

Net input in binary:  h_i(b) = 2·(W_i · b) − Σ_j W_ij
b_i_new = 1 if h_i ≥ 0, else 0
```

This maps each neuron's update function to a Boolean function f_i : {0,1}^N → {0,1}, which is then enumerated into a truth table and minimized (Quine-McCluskey) for RTL synthesis.

---

## 5. Key Numbers / Dataset Specs

| Quantity | Formula | N=8 | N=16 | N=64 | N=256 |
|---|---|---|---|---|---|
| Hebbian capacity (α=0.138) | 0.138·N | ~1 | ~2 | ~8 | ~35 |
| Storkey capacity (α=0.14) | 0.14·N | ~1 | ~2 | ~9 | ~36 |
| Truth table rows | 2^N | 256 | 65,536 | 1.8×10¹⁹ | — |
| Weight matrix size | N² | 64 | 256 | 4,096 | 65,536 |
| Practical RT enumeration | N≤20 | ✅ | ✅ | ❌ | ❌ |

---

## 6. Recurrent Neural Networks vs. Hopfield Networks

**Hopfield is a specific type of RNN** with special structure:

| Property | General RNN | Hopfield Network |
|---|---|---|
| Connectivity | Directed, feedforward + recurrent | Fully connected, undirected (symmetric W) |
| Training | Backpropagation through time (BPTT) | Hebbian / Storkey (one-shot) |
| Temporal dynamics | Sequential data, sequence-to-sequence | Fixed-point retrieval (no time dimension) |
| Gradient flow | Vanishing/exploding gradients | Not applicable (no gradient-based training) |
| Use case | Language, time series | Associative memory, optimization |
| Energy function | Not guaranteed | Always exists; convergence guaranteed |
| Stability | Depends on architecture | Always stable (async update) |

**The key insight:** Hopfield Networks don't process sequences — they are memories. The "recurrence" is purely for relaxation to a stored attractor, not for processing temporal structure.

---

## 7. Open Questions / Things to Verify

- [ ] What training dataset are we using for the hardware demo? (random bipolar patterns? MNIST 8x8?)
- [ ] Is N fixed for the demo, or parameterized? (current code: parameterized via --N flag)
- [ ] Storkey vs. Hebbian — which rule to use for the final hardware demo?
- [ ] What is the target FPGA? (Vivado script targets Artix-7 by default)
- [ ] Do we need >8 neurons for the demo? (Truth table enumeration breaks at N>20)
