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

> ## ⚠ Read `../paper/CLAIMS_AUDIT.md` before reusing anything below
>
> This document was appended to round by round and never reconciled. Later rounds
> contradict earlier ones in three places, all marked inline:
>
> - **Finding #4 is RETRACTED** — the "universal oscillators" all settle under a
>   graph-coloured schedule.
> - **Finding #3 is REVISED** — the "symmetry crisis" is the degenerate case of
>   the value-distinctness rule, not an integer-ratio effect.
> - **The `noise` mode is not a third condition.** With the canonical settings
>   (seed 99, scale 0.5) it emits delays *byte-identical* to `depth`, because
>   `round(d + U(-0.5, 0.5))` almost always returns `d`. Every "noise" row in
>   findings #2 and #5–#13 duplicates `depth`, so any statement of the form "all
>   three modes agree" is circular. Noise *sweeps* at scale ≥ 2.0 are genuine.
> - **Finding #16 is superseded by #17** (don't-care minimisation).

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

> **REVISED by round 7 — the rule below is wrong. See finding #14.**
> Ratio = 1.0 means T_ODD = T_EVEN, i.e. *every neuron shares one delay value*.
> That is the degenerate case of the value-distinctness rule, not a timing
> resonance. Commensurate delays settle perfectly well (100% on the hardest
> states, 3 schemes) provided the values differ, so integer ratios per se are
> harmless — only equality is fatal. The residual dip at ratio 2.0 is unexplained
> and too small to build on; do not cite it without re-running.

~~**Rule**: Any bipartite timing where T_ODD/T_EVEN = integer (especially 1 or 2) causes
oscillation crises. Use asymmetric ratios (e.g., 2.4x, 3x, or any non-integer).~~

### 4. Universal Oscillators (EXP E)

> **RETRACTED by round 6 — see finding #14.** These are not universal
> oscillators. Every graph-coloured schedule settles all 32 of them (18 schemes,
> 100%). They were artifacts of parity collisions, not intrinsic limit cycles;
> the original claim generalised from having tried only even_odd variants.

**32 states oscillate in BOTH depth and even_odd modes:**
- 18.8% (6/32) settle at T_ODD < 20 and T_ODD ≥ 46
- 0% settle at T_ODD ∈ [20, 45]
- ~~True universal oscillators do NOT converge under any even_odd configuration~~
  — true only *within* even_odd; false in general

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

### 14. The Scheduling Rule (Rounds 6-7)

The `even_odd` schedule assigns delays by index parity (`i % 2`), which is blind to
the coupling graph. Extracting that graph from the PLAs (43 edges, 35.8% dense)
shows parity leaves **19/43 (44.2%) of coupled pairs latching at the same sim
time** -- including hub neuron 14 (degree 11, 386 terms) firing in lockstep with
6 of its 11 neighbours. Depth mode is 14/43 (32.6%), with seven neurons sharing
delay 3. Every "weak bit" found independently by fault injection (4, 9, 11, 12)
appears in the parity conflict list.

**Round 7 ran the 2x2 separating the two candidate mechanisms** (20 schemes,
4,276 unique states):

| condition | universal oscillators settled |
|---|---|
| proper colouring + distinct incommensurate delays | **100%** (15/15 schemes) |
| proper colouring + distinct commensurate delays | **100%** (3/3 schemes) |
| proper colouring + *identical* delays (`all_equal`) | **0%** |
| distinct incommensurate delays, *no* colouring (`parity_primes`) | **0%** |

**THE RULE: no two coupled neurons may share a delay VALUE.** Necessary and
sufficient. Colouring is just the algorithm that achieves it with the fewest
distinct values; incommensurability is *not* required for settling and only
shifts which attractor is reached (recall varied 6-34% on the oscillators while
settling stayed pinned at 100%). Verifying on class *labels* instead of delay
*values* misses the `all_equal` failure mode entirely.

Robustness across 12 permutations of the same primes over the same classes:
universal-oscillator settling **sd = 0.00**. Not numerology.

**Best schedule found -- geometric ladder `[2,4,8,16,32,64]` on the 6-colouring:**

| test set | settled | oscillated |
|---|---|---|
| all HD<=3 states (2,784) | **100.00%** | 0 |
| universal oscillators (32) | **100.00%** | 0 |
| random (1,500) | 99.87% | 0.1% |

No state in the round-7 corpus fails to settle under at least one colouring
schedule. Prime ladders score ~3 points better on recall but up to 5 points
worse on settling -- prefer powers of two when reliable settling is the priority.

### 15. Recall Is a Loading Problem, Not a Scheduling Problem

Once scheduling is fixed, the residual failures are almost entirely *spurious
attractors*, not oscillation (random states under colouring: 75.8% spurious,
1.7% oscillated). Conditional on settling, accuracy barely moves (53.4% -> 60.5%).
The network settles reliably onto the wrong attractor.

A scan of pseudoinverse nets under idealised random-async updates shows recall
is governed by loading alpha = M/N:

| N | M | alpha | correct @ HD<=3 |
|---|---|---|---|
| 16 | 4 | 0.250 | 79% |
| 24 | 4 | 0.167 | 99% |
| 32 | 4 | **0.125** | **100%** |
| 16 | 8 | 0.500 | 31% |

**No schedule can reach perfect recall on the current network.** At M/N = 4/16 =
0.25 the 4 stored patterns compete with 16 spurious fixed points. Near-perfect
recall needs alpha <~ 0.125-0.19, i.e. N=32 for the same 4 patterns -- a Phase-1
change, not a Phase-2 one. (Caveat: the scan uses unpruned pseudoinverse nets
while the network under test is max-pruned, so the alpha trend transfers but the
absolute numbers do not.)

**Two independent levers:** scheduling buys reliable *settling* (solved, ~100%);
loading buys correct *settling* (needs a wider network).

---

### 16. Scaling (scale_study.py)

Confirmed the alpha prediction on the real Phase-1 pipeline and pushed N as far
as it goes. The schedule simulator was validated against the SV measurements at
N=16 first (coloured pow2 100% settled / 0 value-conflicts; degenerate 74% / 43
conflicts) before any large-N number was taken seriously.

**The schedule scales indefinitely. The LUT does not.**

| N | M | fan-in | delay classes | max delay | settled | recall @HD<=3 | LUT entries/neuron |
|---|---|---|---|---|---|---|---|
| 1024 | 4 | 24 | 5 | 5 | 100% | 100% | 16.7M |
| 2048 | 4 | 24 | 6 | 6 | 100% | 100% | 16.7M |
| 4096 | 4 | 24 | 6 | 6 | 100% | 100% | 16.7M |

At N=4096 the network needs only **6 distinct delay values**, because a sparse
24-regular coupling graph has a tiny chromatic number regardless of N. Schedule
cost is O(N) storage and O(chi) distinct delays -- it does not grow with N in any
way that matters. Delay-pool choice is irrelevant: pow2, linear, linear2 and
primes all gave identical settling, confirming the rule that only DISTINCTNESS
between coupled neurons matters.

**The binding constraint is per-neuron LUT size = 2^fan-in**, and fan-in is set
by M, not N. Measured floor is d >~ 6M (d=24 for M=4): at d=12 only 2/4 patterns
survive as fixed points, because `retrain_pseudoinverse_masked` symmetrises after
the per-neuron least-squares fit and destroys the exact solution. So a LUT-based
HNN scales freely in N but **exponentially in M**. Practical ceiling is d ~ 16-20
(64K-1M entries); reaching larger M needs threshold gates (O(d) adders) instead
of truth tables.

**Two bugs found and fixed in the process:**
- `phase1/pruning.py::_prune_to_degree` silently no-opped. It selected by
  threshold (`row < kth`), which prunes nothing when a row is entirely tied --
  and a rank-M pseudoinverse W is exactly that (N=512, M=4 gave rows of 71
  identical magnitudes, so a requested degree of 12 returned 71). Now ranks with
  argsort. The canonical N=16 network never passed `target_degree`, so committed
  artifacts are unaffected.
- `schedule_hnn.py::verify` checked class labels rather than delay values, so it
  would have passed the `all_equal` schedule that measures 0% settling.

Magnitude pruning cannot pick a support at low rank for the same tie reason --
every candidate edge is equivalent. Supports must be chosen structurally and
retrained on (`--support regular`, degree-preserving edge swaps). Ring/circulant
supports fail (0-60% recall): local connectivity cannot store globally random
patterns.

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

### 17. Don't-Care Minimisation: the LUT Approach Does Scale

The pipeline emitted fully-specified truth tables (all 2^d rows, every one a
care condition) -- the worst case for two-level minimisation, and more than an
associative memory needs. It only has to be correct on states it visits.

Emitting `.type fr` PLAs containing only the care set -- the operating region
(Hamming radius h of a stored pattern) projected onto each neuron's support,
size M*sum_{j<=h} C(d,j), POLYNOMIAL in fan-in -- and minimising with espresso:

| fan-in | full table | full-table terms | care rows | **DC terms** | speedup |
|---|---|---|---|---|---|
| 16 | 65,536 | ~1,000-2,900 | 2,768 | **31-54** | 34.5x fewer |
| 24 | 16,777,216 | infeasible | 9,300 | **10-58** | -- |
| 32 | 4.3e9 | infeasible | 21,956 | **5-27** | -- |

Term count does not grow with fan-in -- it FALLS (avg 48 -> 27 -> 14). The care
set is 4 small Hamming balls, and a handful of cubes covers it however wide the
input. Espresso runtime is the limit (fan-in 48 timed out at 30 min), not term
count.

**This reverses finding #16.** Estimated area used the C(d,d/2) threshold bound
on fully-specified tables and put the crossover vs an adder tree at fan-in ~9.
With don't-cares the real numbers invert it:

| fan-in | DC-LUT GE (measured terms) | threshold-gate GE | winner |
|---|---|---|---|
| 16 | ~435 | 1,028 | **LUT 2.4x smaller** |
| 24 | ~351 | 1,687 | **LUT 4.8x smaller** |
| 32 | ~246 | 2,271 | **LUT 9x smaller** |

The LUT gets relatively BETTER as fan-in grows, because terms stay flat while
the adder tree grows linearly. The earlier "LUT loses above fan-in 9" conclusion
was an artifact of fully specifying functions we never needed fully specified.

**Correctness verified, not assumed** (verify_dc_recall.py). Don't-cares let
espresso assign the off-region freely, so it can invent fixed points or destroy
basins. Rebuilding the network from the espresso SOPs (N=256, fan-in 16, 12,357
terms over 256 neurons) and re-measuring under the colour schedule:

| test | exact settled | exact recall | SOP settled | SOP recall | agreement |
|---|---|---|---|---|---|
| HD=0,1,3 | 100% | 100% | 100% | 100% | **100%** |
| HD=5 (beyond the radius-3 care set) | 100% | 100% | 100% | 100% | **100%** |
| uniform random (off-region) | 100% | -- | 98% | -- | 2% |

Inside the operating region the minimised network is behaviourally identical,
and it generalises past the care radius (HD=5 still exact). Outside it the two
networks agree only 2% of the time -- expected, since that region was declared
free, and it still settles 98% rather than oscillating. **The tradeoff is real
and must be stated: behaviour on far-from-pattern inputs is unspecified.** That
is acceptable for associative recall and unacceptable if arbitrary states must
be handled.
