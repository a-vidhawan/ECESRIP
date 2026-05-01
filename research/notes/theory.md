# Theoretical Foundations — LUT-Based Hopfield Network Hardware

**Project:** ECESRIP — Hopfield Network on FPGA via Truth Table Enumeration  
**Student:** Aarav Vidhawan

---

## 1. Hopfield Network Fundamentals

### 1.1 Neurons and State Representation

A Hopfield network consists of **N fully connected binary neurons**. Each neuron i has a state:

```
s_i ∈ {-1, +1}   (bipolar representation)
```

The full network state at time t is the vector:

```
s(t) = [s_1(t), s_2(t), ..., s_N(t)]^T  ∈ {-1, +1}^N
```

There are 2^N possible states. The network dynamics are a trajectory through this discrete state space.

**Binary vs bipolar:** Hardware implementations often use binary {0, 1} rather than bipolar {-1, +1}. The mapping is:

```
b_i = (s_i + 1) / 2       bipolar → binary
s_i = 2*b_i - 1           binary → bipolar
```

This matters for truth table generation: the truth table enumerates all 2^N binary input combinations (b_1, ..., b_N) ∈ {0,1}^N, computes the bipolar local field, and outputs the new binary state.

---

### 1.2 Weight Matrix

Neuron interactions are encoded in an **N×N weight matrix W** with elements w_ij. The weight w_ij represents the coupling strength from neuron j to neuron i.

Two structural constraints are required for convergence (see Section 3):

1. **Symmetry:** `w_ij = w_ji` for all i, j — interactions are bidirectional and equal
2. **Zero diagonal:** `w_ii = 0` for all i — no neuron has a self-connection

These constraints mean W is a real symmetric matrix with zeros on the diagonal.

---

### 1.3 Neuron Update Rule

The **local field** (or net input) at neuron i given state s is:

```
h_i(s) = Σ_{j≠i} w_ij · s_j   =   Σ_j w_ij · s_j      (since w_ii = 0)
```

The update rule for neuron i is:

```
s_i ← sign(h_i(s))
```

where sign(x) = +1 if x ≥ 0, else -1. (Tie-breaking at h_i = 0 is arbitrary; typically s_i is left unchanged.)

**In hardware terms:** h_i is a weighted sum over all other neuron states. For bipolar binary inputs with integer weights, the sign of h_i is a Boolean function of the N binary inputs b_1, ..., b_N. This is the function we enumerate as a truth table.

The computation for neuron i in the bipolar domain:

```
h_i = Σ_j w_ij · s_j
    = Σ_j w_ij · (2*b_j - 1)
    = 2*(Σ_j w_ij · b_j) - Σ_j w_ij
    = 2*(W[i] · b) - Σ_j |w_ij|    [if weights are ±1 then Σ w_ij = 0 by symmetry; general case uses the raw sum]
```

Output of neuron i (binary):

```
b_i_new = 1   if   (W[i] · b) ≥ (1/2) · Σ_j w_ij
          0   otherwise
```

This threshold function of the binary input vector b is what gets enumerated and minimized into a SOP (Sum of Products) Boolean expression.

---

### 1.4 Energy Function

Hopfield (1982) defined a scalar **energy function** (Lyapunov function):

```
E(s) = -1/2 · Σ_i Σ_j w_ij · s_i · s_j  +  Σ_i θ_i · s_i
```

where θ_i are per-neuron thresholds (bias terms; set to 0 for zero-threshold Hopfield networks).

In matrix form:

```
E(s) = -1/2 · s^T · W · s  +  θ^T · s
```

**Key property:** E is bounded. Since s ∈ {-1,+1}^N is a finite discrete space, E takes on at most 2^N distinct values, and:

```
E_min = -1/2 · Σ_{i,j} |w_ij|      (rough lower bound)
E_max =  1/2 · Σ_{i,j} |w_ij|      (rough upper bound)
```

The energy landscape over {-1,+1}^N determines the network's attractor structure. Local minima of E are stable states (fixed points) of the dynamics. This is the core connection: **training configures W so that stored patterns are local energy minima.**

---

## 2. Learning Rules

### 2.1 Hebbian Learning (Outer Product Rule)

The Hebbian rule stores a set of M bipolar patterns {ξ^1, ξ^2, ..., ξ^M}, each ξ^μ ∈ {-1,+1}^N, by summing their outer products:

```
W = (1/N) · Σ_{μ=1}^{M} ξ^μ (ξ^μ)^T  −  I
```

The subtracted identity matrix enforces the zero-diagonal constraint (w_ii = 0). The 1/N normalization keeps weight magnitudes bounded.

**Intuition:** Each pattern ξ^μ contributes a rank-1 matrix ξ^μ(ξ^μ)^T. The (i,j) entry of this matrix is ξ^μ_i · ξ^μ_j, which is +1 if neurons i and j agree in pattern μ and -1 if they disagree. After summing M patterns, w_ij is large and positive when i and j co-activate across many patterns, and large and negative when they are typically anti-correlated. This is Hebb's rule: "neurons that fire together, wire together."

**Stability check:** A stored pattern ξ^μ is a fixed point of the network if and only if, for every neuron i:

```
sign(h_i(ξ^μ)) = ξ^μ_i
```

Substituting the Hebbian W:

```
h_i(ξ^μ) = Σ_j w_ij · ξ^μ_j
          = (1/N) · Σ_j [Σ_ν ξ^ν_i ξ^ν_j] · ξ^μ_j   (excluding j=i via zero diagonal)
          = ξ^μ_i  +  (1/N) · Σ_{ν≠μ} ξ^ν_i · (Σ_j ξ^ν_j ξ^μ_j)
```

The first term is the **signal** (always has sign ξ^μ_i). The second term is the **cross-talk noise** from the other M-1 patterns. When M is small relative to N, the cross-talk is small and the signal dominates — the pattern is reliably recalled. As M grows, cross-talk accumulates and eventually corrupts recall.

---

### 2.2 Storkey Learning Rule

The Storkey rule (Storkey 1997) is an incremental rule that adds one pattern at a time while accounting for the current state of the weight matrix. When adding pattern ξ^μ:

```
W^μ = W^{μ-1}  +  (1/N) · [ ξ^μ(ξ^μ)^T  −  h^μ(ξ^μ)^T  −  ξ^μ(h^μ)^T ]
```

where h^μ is the "local field matrix" — the net input each neuron would receive from all others under pattern ξ^μ with the current weights:

```
h^μ_i = Σ_{j≠i} W^{μ-1}_{ij} · ξ^μ_j
```

**Why it's better than Hebbian:** The extra correction terms `h^μ(ξ^μ)^T + ξ^μ(h^μ)^T` reduce cross-talk between patterns. Intuitively, the rule not only reinforces the target pattern but also partially cancels the interference from previously stored patterns.

**Trade-off:** Storkey requires O(N²) operations per pattern (to compute h^μ for all neurons), the same asymptotic cost as Hebbian. The improvement is in quality at or near the capacity limit, not in computational cost.

---

### 2.3 Capacity Analysis

**Hebbian capacity (Amit, Gutfreund & Sompolinsky 1985):** Using statistical mechanics (replica theory), the maximum number of patterns reliably retrievable is:

```
M_max ≈ 0.138 · N      (Hebbian rule)
```

More precisely, for M = α·N with α < 0.138, almost all stored patterns are fixed points with high probability (over random pattern draws). For α > 0.138, retrieval fails for a finite fraction of patterns.

**Storkey capacity:** Empirically and analytically higher quality near saturation, with approximately the same 0.14N threshold but significantly better recall accuracy at loadings M/N between 0.10 and 0.14.

**What happens above capacity:** The network still converges (the energy argument is independent of capacity), but it converges to **spurious states** — attractors that are not stored patterns. The most common spurious states are:
- **Mixture states:** sign(ξ^μ ± ξ^ν ± ξ^ρ) for odd linear combinations of stored patterns
- **Negatives:** −ξ^μ (if W is symmetric, the negative of a stored pattern is always also a fixed point)

**Implication for our hardware:** We must stay below M ≈ 0.14N to guarantee reliable recall. The truth table enumerates all 2^N input combinations exactly, so the hardware faithfully implements whatever W encodes — including spurious attractors if W is overloaded.

---

### 2.4 Modern Hopfield Networks (reference point)

Ramsauer et al. (2020) introduced a continuous-valued generalization with an exponential storage capacity M ∝ exp(N). This is achieved by replacing the linear local field with a softmax-based interaction. The update rule becomes:

```
ξ_new = X · softmax(β · X^T · ξ)
```

where X is the matrix of stored patterns and β is an inverse temperature. At β → ∞ this reduces to the classical nearest-pattern projection.

**Why we use classical Hopfield:** The exponential-capacity version does not produce a Boolean threshold function — it requires floating-point softmax, which cannot be enumerated as a truth table. Classical Hopfield with bipolar thresholding is the only variant that maps directly to a LUT. The modern version is included here as a reference point for capacity comparison.

---

## 3. Dynamics and Convergence Theory

### 3.1 Fixed Points and Attractors

A state s* ∈ {-1,+1}^N is a **fixed point** (stable state) if and only if every neuron is already in its correct updated state:

```
s*_i = sign(Σ_j w_ij · s*_j)   for all i
```

Equivalently, no single-neuron update changes the state. Fixed points are the attractors of the Hopfield dynamics — the network converges to them and stays there.

The set of fixed points is determined entirely by W. It does not depend on the update schedule. Stored patterns (and their negatives, and spurious mixtures) that satisfy the above condition are all fixed points simultaneously.

---

### 3.2 Energy Monotonicity — The Convergence Proof

**Theorem (Hopfield 1982):** Under asynchronous single-neuron updates with symmetric W and zero diagonal, the energy E(s) is non-increasing. Since E is bounded below and the state space is finite, the network must reach a fixed point in a finite number of steps.

**Proof:** When neuron i is updated, all other states remain fixed. The energy change is:

```
ΔE = E(s_new) - E(s_old)
   = -1/2 · [s^T_new · W · s_new  −  s^T_old · W · s_old]
```

Only the i-th component of s changes, so expanding and using symmetry of W (w_ij = w_ji):

```
ΔE = -(Σ_j w_ij · s_j) · Δs_i
   = -h_i · Δs_i
```

where Δs_i = s_i(new) − s_i(old). The update rule sets s_i(new) = sign(h_i), so:

- If h_i > 0: s_i(new) = +1. If s_i was already +1, Δs_i = 0, ΔE = 0. If s_i was −1, Δs_i = +2, ΔE = −2h_i < 0.
- If h_i < 0: s_i(new) = −1. If s_i was already −1, Δs_i = 0, ΔE = 0. If s_i was +1, Δs_i = −2, ΔE = +2h_i < 0 (since h_i < 0).
- If h_i = 0: s_i is unchanged by convention, ΔE = 0.

In all cases **ΔE ≤ 0**. Each update that actually changes a neuron's state strictly decreases E. Since the state space {-1,+1}^N is finite (2^N states) and E is strictly bounded, the sequence of states must terminate — the network reaches a state where no update changes any neuron, i.e., a fixed point. □

**Why symmetry is necessary:** The cross-terms in ΔE cancel only because w_ij = w_ji. For asymmetric W, the effective energy per update picks up a residual (w_ij − w_ji)·s_i·s_j term that can be positive, breaking the monotone descent.

**Why zero diagonal is necessary:** A nonzero w_ii adds a term w_ii·s_i² to the local field. For w_ii < 0 (self-inhibition), a neuron whose state is already correct may be driven to flip by its own negative self-weight, causing perpetual oscillation. The canonical counterexample W = −I never converges.

---

### 3.3 Convergence Speed

The energy proof guarantees convergence in at most as many steps as there are distinct energy levels. In the worst case, this is exponential in N, and indeed finding a stable Hopfield state is **PLS-complete** (Schaffer & Yannakakis 1991) — no polynomial-time algorithm is known in general.

In practice, for well-separated stored patterns with M ≪ 0.14N, convergence typically takes O(N) single-neuron updates (a small constant number of full sweeps). Near or above capacity, convergence can take many more sweeps as the network wanders among near-flat regions of the energy landscape.

**Hardware implication:** A sequential update controller cycling through all N neurons once constitutes one "sweep." A practical convergence detector checks whether any state changed during a full sweep; if none did, the circuit has reached a fixed point. For safe hardware design, set a maximum iteration count (e.g., 10·N sweeps) as a timeout.

---

## 4. Update Order — Does It Matter?

### 4.1 Asynchronous vs Synchronous Update Modes

**Asynchronous (serial) update:** One neuron i is selected and updated at each step. All other neurons hold their current values. The updated value of s_i is immediately visible to subsequently updated neurons.

**Synchronous (parallel) update:** All N neurons compute their new values simultaneously using the state vector from the previous time step. No neuron sees any other neuron's new value until the next round.

These are fundamentally different dynamical systems. The same weight matrix W produces different trajectories under the two modes.

---

### 4.2 Asynchronous Updates — Convergence Guarantee

As proven in Section 3.2, asynchronous single-neuron updates with symmetric W and zero diagonal always converge to a fixed point. This holds for **any fair update schedule** — any schedule in which every neuron is selected infinitely often. Cyclic (1, 2, ..., N, 1, 2, ...), random, stochastic — all are fair and all guarantee convergence.

The proof is schedule-independent: it only requires that ΔE ≤ 0 on every individual update, which holds regardless of which neuron was updated before.

---

### 4.3 Synchronous Updates — Risk of 2-Cycles

**Theorem (Goles & Olivos 1980; Bruck 1990):** Under synchronous updates with symmetric W, the network converges to either a **fixed point** or a **limit cycle of period exactly 2**.

A 2-cycle is a pair of states (s^A, s^B) such that the synchronous update of s^A produces s^B and the synchronous update of s^B produces s^A. The network oscillates indefinitely between them and never stabilizes.

**Canonical example:** A 4-neuron network with bipartite positive weights between group {1,2} and group {3,4}. Starting from s = (+1,+1,−1,−1), the synchronous update produces s' = (−1,−1,+1,+1), and the next update returns to s. This is a valid 2-cycle; neither state is a fixed point. A convergence detector waiting for "no state change" would never trigger.

**Bruck's proof via graph cuts:** Each state s partitions neurons into two sets {+1} and {−1}. The energy E(s) equals (up to sign and constant) the weighted cut value of this partition in the graph defined by W. Synchronous updates correspond to a "best response" move where all neurons simultaneously switch to the side that maximises their local field. Two complementary states can have equal cut value, creating the 2-cycle.

---

### 4.4 Block-Sequential Updates

A middle ground: partition neurons into blocks. Within each block, neurons update in parallel; across blocks, updates are sequential. Goles-Chacc et al. (1985) showed that block-sequential updates with symmetric W and sufficiently small blocks still converge to fixed points only (no 2-cycles). The condition is roughly that no block contains two neurons with a strong positive weight between them.

**Hardware relevance:** If you want to update K neurons per clock cycle (for throughput), a block-sequential schedule with K < N is provably safe as long as blocks are chosen to avoid strongly coupled pairs. Goemaere et al. (2024) showed that an even-odd split (neurons split into two alternating blocks) converges approximately 2× faster than fully synchronous while maintaining fixed-point guarantees.

---

### 4.5 Does the Specific Order Matter Within Asynchronous Updates?

**Convergence: no.** Any fair asynchronous schedule converges. Cyclic order is as correct as random order.

**Which attractor is reached: yes.** The specific order determines the trajectory through the energy landscape. Two different update orders starting from the **same initial state** can end at **different fixed points**.

This is expected and fundamental — it is the discrete analogue of gradient descent reaching different local minima depending on the step direction. The set of all fixed points is the same regardless of update order (it is determined by W alone), but the basin of attraction boundaries shift. For hardware with a fixed cyclic update order, recall behaviour is fully deterministic and reproducible.

**Tie-breaking at h_i = 0:** When the local field is exactly zero, the update is ambiguous. Different tie-breaking conventions (leave unchanged, flip, random) create different basin boundaries. In hardware, h_i = 0 corresponds to a comparator with equal inputs — a metastability risk in the threshold circuit.

---

### 4.6 Summary Table

| Update mode | Weight conditions | Converges to | 2-cycles possible | Order affects attractor? |
|---|---|---|---|---|
| Async serial, any fair order | w_ij=w_ji, w_ii=0 | Fixed points only | No | Yes |
| Synchronous (fully parallel) | w_ij=w_ji | Fixed points or 2-cycles | Yes | N/A |
| Synchronous | w_ij=−w_ji (antisymmetric) | Cycles of period ≤ 4 | Yes | N/A |
| Block-sequential (small blocks) | w_ij=w_ji | Fixed points only | No | Yes |
| Any mode | w_ij ≠ w_ji (asymmetric) | No guarantee | Possible | N/A |
| Any mode | w_ii < 0 | No guarantee | Possible | N/A |

---

## 5. LUT-Based Hardware Approach

### 5.1 Core Idea

Each neuron's update function `s_i = sign(Σ_j w_ij · s_j)` is a Boolean function of N binary inputs. Since the input domain {0,1}^N is finite, this function can be fully characterised by enumerating all 2^N input combinations and recording the output for each. This enumeration is the **truth table** for neuron i.

An FPGA LUT (Look-Up Table) is precisely a small SRAM that stores a truth table and looks up the output for a given input address. A K-input LUT on a modern FPGA (K=6 for Xilinx 7-series, UltraScale) stores 2^K = 64 bits. By using logic synthesis to map a large truth table to a network of K-LUTs, each neuron's full Boolean function is implemented without any multipliers or adders.

---

### 5.2 Truth Table Enumeration

For each neuron i, enumerate all 2^N binary input vectors b = (b_1, ..., b_N) ∈ {0,1}^N:

1. Convert to bipolar: s_j = 2·b_j − 1
2. Compute local field: h_i = Σ_j w_ij · s_j
3. Compute output: out_i = 1 if h_i ≥ 0, else 0
4. Record the row (b_1, ..., b_N, out_i) in the truth table

Note that input b_i (neuron i's own current state) also appears in the input vector. However since w_ii = 0, it does not affect h_i. The b_i input column is therefore a **don't-care** for neuron i's truth table — it can be used as a free variable during minimisation to reduce logic.

**Special case h_i = 0 (tie):** We set out_i = b_i (hold current state). This prevents unnecessary transitions and reduces glitch risk.

---

### 5.3 PLA Format and Espresso Minimisation

Truth tables are exported in **PLA (Programmable Logic Array) format** for input to the Espresso logic minimiser:

```
.i N          # N inputs
.o 1          # 1 output
.p <rows>     # number of product terms
<input_pattern> <output>
...
.end
```

Each row is a minterm: a string of N bits (0, 1, or − for don't-care) followed by the output bit.

**Espresso** minimises the truth table into a minimal Sum of Products (SOP) — a two-level AND-OR logic expression. SOP maps directly to LUT networks: each product term is an AND gate (or partial LUT), and the final OR combines them.

The minimised SOP for neuron i is then exported as a SystemVerilog `assign` statement:

```systemverilog
assign s_new[i] = (s[2] & ~s[5] & s[7]) | (~s[1] & s[3]) | ...;
```

---

### 5.4 Hazard-Free Minimisation

A standard SOP minimisation (e.g., Quine-McCluskey or plain Espresso) is **not** hazard-free. A **static-1 hazard** occurs when the output should remain 1 but a momentary glitch to 0 appears during a single-variable input transition, because the transition falls between two product terms with a gap in coverage.

In an asynchronous feedback loop, a glitch on neuron i's output becomes a spurious input transition to all neurons j that have w_ji ≠ 0. This can trigger incorrect state transitions and corrupt the convergence trajectory.

**Espresso `-dhazard` flag** produces a hazard-free SOP by adding **consensus (redundant) terms**. For every pair of prime implicants P and Q in the cover where a single-variable transition could cause a hazard, the consensus term P·Q is added. The consensus term covers the hazardous transition, ensuring the output stays at 1 throughout.

Formally, a SOP cover is hazard-free for all single-variable input transitions if and only if for every pair of minterms m_a and m_b that differ in exactly one variable and both map to output 1, there exists a prime implicant in the cover that contains both m_a and m_b.

**Cost:** Hazard-free SOPs are slightly larger (more product terms) than minimal SOPs. This is the correct trade-off for asynchronous circuits — correctness over minimality.

---

### 5.5 Scalability

Truth table size grows as 2^N. Logic minimisation (Espresso) runtime grows super-exponentially with N in the worst case. Practical limits:

| N | Truth table rows per neuron | Espresso time (typical) | Feasibility |
|---|---|---|---|
| ≤ 10 | ≤ 1,024 | < 1 s | Easy — fits distributed LUTs |
| ≤ 14 | ≤ 16,384 | seconds | Feasible |
| ≤ 16 | ≤ 65,536 | minutes | Borderline |
| > 16 | > 65,536 | hours / infeasible | Requires sparse connectivity |

**Sparse connectivity for large N:** Keep only the F strongest weights per neuron (by magnitude). Each neuron's truth table then has 2^F rows instead of 2^N. LogicNets (Umuroglu et al. 2020) uses expander graphs (F ≈ 6) for random sparse connectivity. For Hopfield, taking the F largest |w_ij| per neuron is more principled — it preserves the most information per weight.

---

## 6. Asynchronous Circuit Theory

### 6.1 Hazard Classification

In combinational logic, a **hazard** is a momentary incorrect output value during a transition, caused by unequal propagation delays through different logic paths.

**Static-1 hazard:** The output should remain 1 throughout an input transition, but momentarily glitches to 0.

**Static-0 hazard:** The output should remain 0 throughout, but momentarily glitches to 1.

**Dynamic hazard:** The output should make a single transition (0→1 or 1→0) but makes multiple transitions (0→1→0→1 or similar) before settling.

For Hopfield hardware, **static-1 hazards** are the primary concern. When a neuron's output should stay at its current value but glitches, downstream neurons see a spurious input change and may incorrectly update.

---

### 6.2 The Consensus Theorem

The algebraic foundation for hazard-free SOP is the **consensus theorem**:

```
A·B  +  Ā·C  =  A·B  +  Ā·C  +  B·C
```

The term B·C is the **consensus term** of the two implicants A·B and Ā·C. It is logically redundant (the equation holds without it) but eliminates the hazard: during the transition A: 1→0, both A·B and Ā·C may be 0 momentarily, causing a glitch. The consensus term B·C covers this transition because if B=1 and C=1 during the transition on A, then B·C=1 holds continuously.

A SOP is **hazard-free** for single-variable transitions if and only if it contains the consensus term for every pair of implicants that share a single-variable transition on a variable where one has the variable uncomplemented and the other has it complemented. Espresso `-dhazard` adds exactly these terms.

---

### 6.3 Multi-Input Transitions and Metastability

Hazard-free SOP with `-dhazard` guarantees glitch-free behaviour for **single-variable input transitions** only. In the Hopfield feedback loop, two neurons may update in rapid succession, causing a two-variable transition at a third neuron's input. This is a **multi-input transition** and is not covered by the single-variable hazard-free guarantee.

This is an open question for the fully combinational design: if two neurons i and j update nearly simultaneously, neuron k (connected to both) sees a two-variable transition on its inputs b_i and b_j. The output of neuron k's LUT during this transition is unspecified by the hazard-free cover and may glitch.

**Mitigation strategies:**
1. **Registered neurons with sequential update controller** (recommended): Clock all neuron outputs into flip-flops. A sequencer enables one neuron to load its new LUT output per clock cycle. Only one neuron changes state per cycle, guaranteeing single-variable transitions at all other neurons' inputs. This makes the hazard-free SOP guarantee fully applicable.
2. **Settling time budget**: In a fully combinational design, allow sufficient propagation delay for all ripple effects to settle before sampling outputs. Requires careful timing analysis.
3. **Glitch filtering**: Add hysteresis or minimum-pulse-width filters at neuron outputs. Increases area and delay.

Option 1 is strongly preferred for a first implementation.

---

## 7. Hardware Architecture

### 7.1 Recommended Architecture: Registered Sequential Update

Based on the convergence theory (Section 4) and hazard analysis (Section 6), the recommended hardware architecture is:

```
                    ┌─────────────────────────────────┐
                    │         State Register           │
                    │   s[0] s[1] s[2] ... s[N-1]     │
                    └──────────┬──────────────────────┘
                               │ (all N bits broadcast)
                    ┌──────────▼──────────────────────┐
                    │       Neuron LUT Bank            │
                    │  LUT_0  LUT_1  ...  LUT_{N-1}   │
                    │  (hazard-free SOP per neuron)    │
                    └──────────┬──────────────────────┘
                               │ s_new[0..N-1]
                    ┌──────────▼──────────────────────┐
                    │     Update Controller (FSM)      │
                    │  Selects neuron i each cycle     │
                    │  Writes s_new[i] → s[i]          │
                    │  Detects convergence             │
                    └─────────────────────────────────┘
```

- **State register:** N flip-flops holding the current network state s[0..N-1].
- **Neuron LUT bank:** N combinational blocks, each implementing one neuron's hazard-free SOP. All N LUTs compute continuously from the current state register.
- **Update controller:** A cyclic counter (0, 1, ..., N-1, 0, ...) that enables one flip-flop to load its new value per clock cycle.

This implements true asynchronous sequential updates in hardware — exactly the model that the Hopfield convergence proof covers.

---

### 7.2 Convergence Detection

The network has converged when a full sweep of all N neurons produces zero state changes. Implementation:

```systemverilog
logic changed;    // set if any neuron changed in current sweep
logic [N-1:0] s_prev;  // state at start of sweep

// At start of each sweep: snapshot current state
// During sweep: if s_new[i] != s[i] when updating neuron i, set changed=1
// At end of sweep: if ~changed → convergence, assert done signal
```

A simple XOR of s_prev and s (current state) after each full sweep detects any difference. If `s ^ s_prev == 0`, the network is at a fixed point.

---

### 7.3 SystemVerilog Module Hierarchy

```
hopfield_top.sv
├── neuron_logic_bank.sv       # instantiates N neuron_update_i modules
│   ├── neuron_update_0.sv     # hazard-free SOP for neuron 0
│   ├── neuron_update_1.sv     # hazard-free SOP for neuron 1
│   └── ...
├── state_reg.sv               # N flip-flops with per-bit write enable
└── update_ctrl.sv             # cyclic counter + convergence detector
```

Each `neuron_update_i.sv` is auto-generated by the Python pipeline from Espresso output. The module has a single combinational `assign` statement — a flat SOP expression.

---

## 8. Hopfield–Ising Equivalence

### 8.1 The Ising Model

The Ising model from statistical physics describes a system of N binary spins s_i ∈ {-1,+1} with pairwise couplings J_ij and external fields h_i. Its Hamiltonian (energy function) is:

```
H = -Σ_{i<j} J_ij · s_i · s_j  −  Σ_i h_i · s_i
```

The ground state (minimum energy configuration) of an Ising model is the solution to a combinatorial optimisation problem. Finding the ground state is NP-hard in general (equivalent to Max-Cut, which is NP-complete).

---

### 8.2 Mapping to Hopfield

The Hopfield energy function is:

```
E = -1/2 · Σ_i Σ_j w_ij · s_i · s_j  +  Σ_i θ_i · s_i
```

This is identical to the Ising Hamiltonian under the correspondence:

```
J_ij  ↔  w_ij      (coupling = weight)
h_i   ↔  −θ_i     (external field = negative threshold)
```

The factor of 1/2 and the i=j exclusion are conventions; both are equivalent up to constants and the zero-diagonal constraint.

**Consequence:** Any NP-hard combinatorial optimisation problem that can be encoded as an Ising Hamiltonian can equally be encoded as a Hopfield weight matrix. The LUT hardware then acts as an Ising machine — a physical system that relaxes to a low-energy state, yielding an approximate solution to the optimisation problem.

---

### 8.3 Encoding NP-Complete Problems

The standard approach (Lucas 2014, "Ising formulations of many NP problems"):

| Problem | Encoding approach |
|---|---|
| Max-Cut | J_ij = −w_{ij} (graph edge weight); ground state = maximum cut |
| Graph colouring | Penalty terms for adjacent same-colour nodes |
| Vertex cover | Penalty for uncovered edges + reward for small cover |
| Travelling Salesman | Position-city one-hot encoding with distance penalties |
| SAT | Clause-penalty encoding |

For our hardware: given a problem instance, compute W = J_ij directly (no Hebbian learning). Generate truth tables from W. Synthesise. Apply an initial spin configuration (e.g., random) and let the circuit iterate to a low-energy fixed point. The fixed point is an approximate solution.

**Quality vs classical solvers:** The Hopfield LUT machine finds local energy minima, not global minima. It is equivalent to greedy local search. For high-quality solutions, simulated annealing (adding noise to escape local minima) or multiple random restarts are needed. This is an active research area in Ising machine hardware.

---

## 9. Open Questions

1. **Multi-input transition hazards:** The hazard-free SOP from Espresso `-dhazard` covers single-variable input transitions. In the fully combinational feedback loop, near-simultaneous neuron updates cause multi-input transitions. Is the hazard-free cover still sufficient? Under what conditions can multi-input glitches corrupt the fixed-point trajectory? Does the registered sequential architecture fully eliminate this concern?

2. **Metastability at h_i = 0:** When the local field is exactly zero, the threshold comparator is at its decision boundary. In a real CMOS circuit this is a metastability event — the output can take arbitrarily long to resolve. How frequently does this occur for random patterns and Hebbian/Storkey weights? Can we bound the probability as a function of N and M?

3. **Sparse connectivity and recall quality:** For N > 16, we must prune to the F strongest weights per neuron. How does pruning degrade recall accuracy and basin width? Is there an optimal pruning strategy (strongest weights, random expander, learned mask) that minimises quality loss for a given F?

4. **Ising machine solution quality:** When W is set by a problem instance (not by Hebbian learning), the energy landscape is problem-specific and may have many shallow local minima far from the global optimum. How does the LUT Hopfield machine compare to simulated annealing, QAOA, or other Ising solvers on standard benchmarks (Max-Cut on G-set graphs)?

5. **PLS-completeness and worst-case convergence:** Finding a stable state is PLS-complete (Schaffer & Yannakakis 1991). For adversarially chosen W, convergence could require exponentially many update steps. For the weight matrices produced by Hebbian/Storkey training on random patterns, what is the empirically observed worst-case convergence time as a function of N and M?

6. **2-cycle detection in hardware:** If the update controller is extended to support synchronous (parallel) updates for throughput experiments, 2-cycles must be detected and broken. One approach: detect a 2-cycle by comparing the current state with the state from two sweeps ago (s(t) == s(t-2) && s(t) != s(t-1)). What is the overhead of this detector, and how should the circuit respond (random perturbation, switch to serial mode)?

---

## References

1. Hopfield, J.J. (1982). "Neural networks and physical systems with emergent collective computational abilities." *PNAS*, 79(8):2554–2558.
2. Hopfield, J.J. (1984). "Neurons with graded response have collective computational properties like those of two-state neurons." *PNAS*, 81(10):3088–3092.
3. Amit, D.J., Gutfreund, H., & Sompolinsky, H. (1985). "Statistical mechanics of neural networks near saturation." *Physical Review A*, 32(2):1007–1018.
4. Goles, E., & Olivos, J. (1980). "Periodic behaviour of generalized threshold functions." *Discrete Mathematics*, 30(2):187–189.
5. Goles-Chacc, E., Fogelman-Soulie, F., & Pellegrin, D. (1985). "Decreasing energy functions as a tool for studying threshold networks." *Discrete Applied Mathematics*, 12(3):261–277.
6. Bruck, J. (1990). "On the convergence properties of the Hopfield model." *Proceedings of the IEEE*, 78(10):1579–1585.
7. Schaffer, M., & Yannakakis, M. (1991). "Simple local search problems that are hard to solve." *SIAM Journal on Computing*, 20(1):56–87.
8. Storkey, A.J. (1997). "Increasing the capacity of a Hopfield network without sacrificing functionality." *ICANN*, LNCS 1327:451–456.
9. Lucas, A. (2014). "Ising formulations of many NP problems." *Frontiers in Physics*, 2:5.
10. Ramsauer, H. et al. (2020). "Hopfield Networks is All You Need." *ICLR 2021*, arXiv:2008.02217.
11. Umuroglu, Y. et al. (2020). "LogicNets: Co-Designed Neural Networks and Circuits for Extreme-Throughput Applications." *FPL 2020*, arXiv:2004.03021.
12. Sousa, F. et al. (2014). "Architecture Analysis of an FPGA-Based Hopfield Neural Network." *Advances in Artificial Neural Systems*, Hindawi, Article 602325.
13. Goemaere, C., Deleu, J., & Demeester, T. (2024). "Accelerating Hopfield Network Dynamics: Beyond Synchronous Updates and Forward Euler." *ECAI 2024 ML-DE Workshop*, arXiv:2311.15673.
14. IEEE Circuits and Systems (1994). "Global convergence of the Hopfield neural network with nonzero diagonal elements." *IEEE Trans. Circuits Syst. I*, DOI:10.1109/81.363543.

