# Clockless HNN Settling: Exhaustive Stress Test Findings

## Overview

Five rounds of stress testing were conducted on a clockless Hopfield Neural Network (HNN) 
implementation using SystemVerilog async settling simulation. The network stores N=16 neurons, 
M=4 patterns. Tests spanned >500,000 SV simulation runs.

---

## Architecture Under Test

- **Network**: N=16 neuron HNN with LUT-based update function (pseudo_maxprune)
- **Stored patterns**: P0=0xfca6, P1=0x1b95, P2=0xa6b6, P3=0xbd07
- **Fixed points**: 20 total (4 stored + 16 spurious)
- **Delay modes**:
  - `depth`: per-neuron delay = 1 + ceil(log2(term_count+1)), max_depth=10
  - `even_odd`: bipartite T_EVEN / T_ODD delays
  - `noise`: depth + ±ε random perturbation

---

## Key Findings

### 1. Full State Space Structure (EXP P: Python Synchronous Sim)

| Category | Count | Fraction |
|----------|-------|----------|
| Fixed points → stored patterns | 6,260 | 9.55% |
| Fixed points → spurious attractors | 19,840 | 30.27% |
| Cyclic states (oscillate) | 39,436 | 60.17% |

**60.2% of all 2^16 states oscillate under synchronous Hopfield dynamics.** The async clockless 
design is specifically beneficial for breaking these cycles.

**Pattern basin sizes** (synchronous sim):
- P0=0xfca6: 4,000 states (largest basin)
- P2=0xa6b6: 1,285 states
- P3=0xbd07: 875 states
- P1=0x1b95: **100 states** (structural weakness — tiny basin!)

### 2. Clockless SV Performance Summary

| Mode | Correct | Settled | Oscillated |
|------|---------|---------|------------|
| depth (low noise η≤30%) | ~33-60% | ~65-80% | ~20-35% |
| even_odd (low noise η≤30%) | ~37-64% | ~97-99% | ~1-3% |
| depth (adversarial, HD≥5) | ~6% | ~51% | ~49% |
| even_odd (adversarial) | ~10% | ~97% | ~3% |

**Key insight**: `even_odd` mode breaks 97% of the 60% cycling states, converting them to 
fixed points. However, most convert to SPURIOUS attractors (74.7% of settled states).

### 3. T_ODD / T_EVEN Symmetry Crisis

**Critical finding**: When T_ODD = T_EVEN (symmetric bipartite delays), the network enters a 
"symmetry crisis":
- At ratio=1.0: only **64.3% settled** (vs 99.4% for ratio≠1)
- Crisis is sharp: ratio=0.9 gives 96.8% settled, ratio=1.1 gives 95.1%

**Secondary crises at integer ratios**:
- ratio=2.0 (T_ODD=20, T_EVEN=10): settled drops to 93-95% from 99%+
- ratio=2.0 (T_EVEN=12, T_ODD=24): settled drops to 95.0%

**Rule**: Any bipartite timing where T_ODD/T_EVEN = integer (especially 1 or 2) causes 
oscillation crises. Use asymmetric ratios (e.g., 2.4x, 3x, or any non-integer).

### 4. Universal Oscillators (EXP E)

**32 states oscillate in BOTH depth and even_odd modes** — universal oscillators:
- 18.8% (6/32) settle at T_ODD < 20 and T_ODD ≥ 46
- 0% settle at T_ODD ∈ [20, 45]
- This is a TIMEOUT artifact: the oscillation period at T_ODD=20 exceeds the timeout
- True universal oscillators do NOT converge under any even_odd configuration

### 5. Exhaustive Basin Test (EXP T: HD≤5 from patterns)

| Hamming Distance | Depth: Correct | Depth: Settled | Even_Odd: Correct | Even_Odd: Settled |
|------------------|---------------|----------------|-------------------|-------------------|
| 0 | 100% | 100% | 100% | 100% |
| 1 | 81.5% | 88.9% | 96.3% | 100% |
| 2 | 58.5% | 78.5% | ~90% | ~99% |
| 3 | 40.0% | 68.6% | ~75% | ~99% |
| 4 | 25.0% | 64.8% | ~55% | ~98% |
| 5 | 15.7% | 59.0% | ~40% | ~97% |

**Even HD=1 neighbors oscillate 11.1% in depth mode.** The 8 HD=1 cycling states are:
- P1: bits 4, 9, 11, 12 flipped (4 states)
- P2: bits 11, 12 flipped (2 states)
- P3: bits 4, 9 flipped (2 states)
- P0: NO HD=1 cycling states (most robustly stored pattern)

### 6. Critical Neurons (EXP G: Fault Injection)

Forcing any single neuron to a constant value (0 or 1) and testing recall at η=0:
- All neurons: correct ≥ 75% when forced (surprisingly robust)
- **Neuron 9** (even_odd, force=0): drops to **50% correct** — most critical
- Neurons 4, 8, 9, 0 are most sensitive in depth mode
- Bits 4, 9, 11, 12 are the "weak bits" (consistent with HD=1 cycling analysis)

### 7. Partial Pattern Completion (EXP I)

Starting with exactly k correct bits out of N=16:
- **Depth mode**: need k ≥ 11 (68.75%) bits correct for ≥50% recall
- **Even_odd mode**: need k ≥ 10 (62.5%) bits correct for ≥50% recall

### 8. Pattern Confusion Matrix (EXP Q, at η=30%)

**Depth mode:**
```
       P0    P1    P2    P3   spur   osc
P0:  0.47  0.00  0.04  0.04  0.17  0.27
P1:  0.01  0.07  0.00  0.02  0.50  0.41   ← P1 almost always wrong
P2:  0.09  0.00  0.23  0.00  0.26  0.42
P3:  0.08  0.01  0.03  0.18  0.23  0.46
```

**Even_odd mode:**
```
       P0    P1    P2    P3   spur   osc
P0:  0.58  0.00  0.03  0.05  0.32  0.02
P1:  0.05  0.07  0.04  0.04  0.78  0.02   ← 78% spurious!
P2:  0.20  0.00  0.34  0.00  0.43  0.03
P3:  0.21  0.03  0.06  0.16  0.53  0.02
```

**P1 is structurally weak**: even_odd settles P1 inputs 98% of the time, but 78% go to 
spurious attractors. This is consistent with P1's tiny 100-state basin.

### 9. LUT Corruption Robustness (EXP N)

Randomly flipping LUT output bits (simulates manufacturing defects):
- 0.1% corruption: recall 56% (baseline ~60%)
- 1% corruption: recall 57% (nearly same!)
- 10% corruption: recall 50%
- 20% corruption: recall 31%

**LUT is remarkably robust** — correct rate degrades gracefully. Even at 10% bit corruption, 
the network still achieves ~50% recall.

### 10. Pattern Interpolation (EXP O)

Walking the Hamming path between pattern pairs (P0→P1, P0→P2, etc.):
- The recall "switch point" (where network switches allegiance from Psrc to Ptgt) occurs 
  roughly at the midpoint of the Hamming path in Hamming space
- P0↔P3 have the sharpest transition (large inter-pattern HD)
- P1 has the shallowest basin (transition starts far from P1)

### 11. Cascade Retrieval (EXP H)

Starting from corrupted P_src, retrieving, then immediately trying P_tgt:
- **Depth**: step1 correct=68.9%, step2 correct=69.9% — SAME performance!
- **Even_odd**: step1 correct=74.2%, step2 correct=73.8% — SAME!

The network shows no "interference" from the first retrieval. Each retrieval is independent.

### 12. Anti-Correlated States (EXP J)

Bitwise complement of stored patterns (maximum HD=16):
- Both modes settle to 100% (even_odd) or 93.7% (depth)
- **0% correct** — complements go to spurious attractors exclusively
- This confirms complements are in large spurious basins, not stored pattern basins

### 13. Noise Scale / Delay Variation (EXP A/B)

Varying delay perturbation scale (±ε units around depth-mode values):
- Scale 0.0 to 5.0: mean correct varies 60-65% (noise seed matters)
- At scale=2.0, seed-to-seed variance is significant: 60-100% settled across 50 seeds
- Some seeds with large scale happen to avoid oscillating states (100% settled)
- Other seeds create delays that happen to amplify oscillations (84.9% settled)

---

## Design Recommendations

1. **Use even_odd mode** for reliability: 97-99% settling rate vs 65-80% for depth mode
2. **Avoid T_ODD/T_EVEN = integer ratios**: Use ratios like 2.4x or 3.2x to stay clear of crises
3. **P1=0x1b95 has structural weakness**: Small basin → poor recall. Consider re-training network
4. **Neurons 4, 9, 11, 12 are critical bits**: Faults on these neurons cause most recall failures
5. **Depth mode oscillation ceiling**: ~35-50% of random states oscillate regardless of timeout
6. **LUT corruption resilience**: 10% corruption only causes ~10% recall degradation
7. **Basin depth requires ≥10-11 bits correct** for reliable recall (deep noise rejection)
8. **Complements never recover**: States at HD=16 from patterns converge to spurious attractors

---

## Test Infrastructure Summary

- **Total tests run**: ~500,000+ SV simulations
- **Infrastructure**: iverilog 12.0, `forever+disable` pattern (no fork/join_any)
- **Test vectors**: `$readmemh` with absolute paths
- **Timing**: `timescale 1ns/1ps` in ALL modules (critical for NBA delays)
- **Rounds**: 5 rounds + additional sweep (run_clockless_stress.py, run_additional_stress.py, run_stress_round3-5.py)
