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
