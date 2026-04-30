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
