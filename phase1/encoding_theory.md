# Binary Encoding Theory: {0,1} ↔ {-1,+1} Equivalence

## Overview

The classical Hopfield network uses bipolar neurons sᵢ ∈ {-1, +1}.
Hardware implementations prefer binary bits bᵢ ∈ {0, 1}.
This document derives the exact substitution that makes these equivalent,
and shows why a threshold term is mandatory.

---

## 1. Bipolar Update Rule (reference)

For neuron i, the asynchronous update is:

```
sᵢ ← sign(hᵢ)    where hᵢ = Σⱼ Wᵢⱼ sⱼ
```

If hᵢ = 0, we hold the current state (tie-breaking to 0 is also valid).
The Hopfield energy is:

```
E = -½ sᵀ W s
```

which decreases monotonically under async updates (Hopfield 1982).

---

## 2. Substitution: bⱼ = (sⱼ + 1) / 2

Let bⱼ ∈ {0, 1} with the linear map:

```
sⱼ = 2bⱼ - 1    ↔    bⱼ = (sⱼ + 1) / 2
```

Substituting into the net input:

```
hᵢ = Σⱼ Wᵢⱼ sⱼ
   = Σⱼ Wᵢⱼ (2bⱼ - 1)
   = 2 Σⱼ Wᵢⱼ bⱼ  -  Σⱼ Wᵢⱼ
       ───────────    ─────────
       binary dot     threshold θᵢ
```

Define:

```
θᵢ  = Σⱼ Wᵢⱼ = row_sum(W)[i]
```

Then:

```
hᵢ = 2 (Wᵢ · b) - θᵢ
```

Since only the sign of hᵢ matters for the update:

```
sign(hᵢ) > 0  ↔  Wᵢ · b > θᵢ/2  ↔  bᵢ_new = 1
sign(hᵢ) < 0  ↔  Wᵢ · b < θᵢ/2  ↔  bᵢ_new = 0
```

The factor of 2 cancels when comparing sides, so the binary update rule is:

```
┌─────────────────────────────────────────────────────────┐
│  bᵢ ← step( Wᵢ · b - θᵢ/2 )                           │
│                                                         │
│  where  θᵢ = Σⱼ Wᵢⱼ   and   step(x) = 1 if x > 0     │
└─────────────────────────────────────────────────────────┘
```

Equivalently (dividing hᵢ by 2 does not change its sign):

```
bᵢ ← step( 2(Wᵢ · b) - θᵢ )
```

This is exactly what `truth_table_gen.py` computes:

```python
H = 2.0 * (all_inputs @ W.T) - row_sums[np.newaxis, :]
```

---

## 3. Why Omitting the Threshold Gives Wrong Dynamics

Without θᵢ, the update becomes:

```
bᵢ ← step( Wᵢ · b )   ← WRONG
```

This is not a bijective transformation of the bipolar rule. The fixed points
of the binary-no-threshold system are generally different from the fixed points
of the bipolar system. Simulation C in `verify_binary_encoding.py` demonstrates
this explicitly — the network converges to different attractors.

Intuitively: when all inputs bⱼ = 0 (state = all -1 in bipolar), the binary
dot product Wᵢ · b = 0 regardless of Wᵢ, but the bipolar net input hᵢ = Σ Wᵢⱼ(-1)
= -θᵢ which can be nonzero. The threshold term restores this asymmetry.

---

## 4. Energy Function in Binary Coordinates

Substituting sᵢ = 2bᵢ - 1:

```
E = -½ sᵀWs
  = -½ (2b-1)ᵀ W (2b-1)
  = -2 bᵀWb + 2 bᵀ W 1 - ½ 1ᵀW1
  = -2 bᵀWb + 2 θᵀb + const
```

where θᵢ = Σⱼ Wᵢⱼ.

This is a QUBO (Quadratic Unconstrained Binary Optimization):

```
E_qubo(b) = -2 bᵀWb + 2 θᵀb + const
```

The HNN minimizes E_qubo while minimizing E_bipolar — they are the same problem
shifted by a constant (which doesn't affect which state is optimal).

---

## 5. LUT Captures the Threshold Implicitly

The truth table for neuron i is precomputed by enumerating all 2^N inputs:

```
for each b ∈ {0,1}^N:
    hᵢ = 2*(Wᵢ · b) - θᵢ
    lut[i][b] = 1 if hᵢ > 0 else 0
```

After this precomputation, **the threshold is baked in forever**. At runtime,
the LUT lookup `b_i_new = lut[i][state]` is a single memory access — no
multiplication, no addition, no comparator, no threshold subtraction.

This is the core efficiency argument of LUT-HNN:

```
Runtime per neuron update:
  Classical HNN:   N multiplications + N additions + 1 comparison
  LUT-HNN:         1 memory access
```

---

## 6. Summary Table

| Property | Bipolar {-1,+1} | Binary {0,1}+threshold | Binary naive (wrong) | LUT |
|----------|-----------------|----------------------|---------------------|-----|
| Update | sᵢ ← sign(Wᵢ·s) | bᵢ ← step(2Wᵢ·b - θᵢ) | bᵢ ← step(Wᵢ·b) | bᵢ ← lut[i][state] |
| Attractors | Same as ground truth | **Same as bipolar** | **Different — wrong** | **Same as bipolar** |
| Runtime ops/neuron | N MACs + 1 cmp | N MACs + 1 sub + 1 cmp | N MACs + 1 cmp | 1 LUT read |
| Hardware resources | BRAM+DSP+CMP | BRAM+DSP+CMP | BRAM+DSP+CMP | LUT fabric only |

---

## References

- Hopfield, J.J. (1982). "Neural networks and physical systems with emergent collective computational abilities." PNAS.
- Lucas, A. (2014). "Ising formulations of many NP problems." Frontiers in Physics. (QUBO connection)
- Glover, F., Kochenberger, G., Hennig, R. (2022). "Quantum Bridge Analytics I: a tutorial on formulating and using QUBO models." Annals of Operations Research. (QUBO survey)
