# Methods Reference
*All learning, pruning, retrain, and GD-based methods in this repo*

---

## Quick-reference table

| Method | Where | Capacity | Degree control | Fixed pts | Noise robustness |
|---|---|---|---|---|---|
| Hebbian | `sim/python/hopfield_net.py` | 0.138N | post-hoc only | ✗ guaranteed | Low |
| Storkey | `sim/python/hopfield_net.py` | ~0.22N | post-hoc / L1 | ✗ guaranteed | Medium |
| Pseudoinverse | `sim/python/hopfield_net.py` | N | post-hoc / masked LS | ✓ always | High |
| Storkey + L1 (ISTA) | `phase1/pruning.py` | ~0.22N | via λ (coarse) | ✗ not guaranteed | Medium |
| Storkey + mask retrain | `phase1/pruning.py` | ~0.22N | exact via mask | ✓ usually | Medium–High |
| PI + magnitude prune | `phase1/pruning.py` | N | via s | ✓ until s too large | High |
| PI + mask LS retrain | `phase1/pruning.py` | N | exact via mask | ✗ risky at low deg | Medium |
| L1-SVM LP | `phase1/train_gd.py` | ≈0.64N | minimum-degree LP | ✓ always | Low |
| Perceptron + L1 | `phase1/train_gd.py` | ≈0.64N | via λ + degree cap | ✓ when converged | Medium |
| RigL | `phase1/train_gd.py` | ≈0.64N | exact budget | ✓ usually | Medium–High |

---

## 1. Learning methods (how W is trained from patterns)

### 1a. Hebbian rule
**File:** `sim/python/hopfield_net.py` → `_train_hebbian()`  
**Call:** `HopfieldNetwork(N, rule=HEBBIAN).train(patterns)`

```
W = (1/N) Σ_μ ξ^μ (ξ^μ)ᵀ      diagonal zeroed
```

The original Hopfield (1982) rule. Each pattern adds its outer product to W. Simple, closed-form, no iteration.

- **Capacity:** ~0.138N — beyond this spurious attractors dominate
- **Weights:** symmetric, zero-mean, std ≈ √M/N
- **Fixed points:** not guaranteed — patterns are approximate attractors
- **Pruning:** post-hoc magnitude only (no retraining possible — rule is a one-shot sum)

---

### 1b. Storkey rule
**File:** `sim/python/hopfield_net.py` → `_train_storkey()`  
**Call:** `HopfieldNetwork(N, rule=STORKEY).train(patterns)`

```
W ← W + (1/N)[ξ^μ (ξ^μ)ᵀ - h^μ (ξ^μ)ᵀ - ξ^μ (h^μ)ᵀ]    h^μ = W ξ^μ
```

Incremental rule: each pattern is presented once. The correction terms `h^μ (ξ^μ)ᵀ` reduce crosstalk from previously stored patterns.

- **Capacity:** ~0.22N (≈60% higher than Hebbian at same quality)
- **Weights:** symmetric, zero-mean
- **Fixed points:** approximately guaranteed up to capacity
- **Pruning:** post-hoc magnitude, L1 during training (ISTA), or mask retrain

---

### 1c. Pseudoinverse rule
**File:** `sim/python/hopfield_net.py` → `_train_pseudoinverse()`  
**Call:** `HopfieldNetwork(N, rule=PSEUDOINVERSE).train(patterns)`

```
W = Ξ (ΞᵀΞ)⁻¹ Ξᵀ    where Ξ = [ξ¹ | ξ² | … | ξᴹ] ∈ ℝᴺˣᴹ
```

Moore-Penrose pseudoinverse of the pattern matrix. Finds minimum-norm W that makes all patterns **exact fixed points**. Requires O(N³) matrix inversion — offline only.

- **Capacity:** N (all patterns guaranteed as fixed points when M < N and patterns linearly independent)
- **Weights:** minimum-norm for the task
- **Fixed points:** ✓ guaranteed for all stored patterns (up to capacity)
- **Pruning:** most tolerant — see Sections 2 and 3

---

## 2. Post-hoc pruning (applied after training, no retraining)

### 2a. Magnitude pruning
**File:** `phase1/pruning.py` → `prune_magnitude(W, s, eps)`  
**Works with:** all three learning rules

```
threshold = s × std(off-diagonal |W_ij|)
W_ij ← 0   if |W_ij| < threshold
```

The only pruning available for Hebbian (rule is closed-form, no retraining handle). For Storkey and PI it serves as a baseline.

- **Parameter s:** 0 = no pruning; 0.75 = 51% zeroed; 1.0 = 62% zeroed (typical N=16)
- **Degree reduction:** mean degree goes from N−1 to ~5–8 at s=0.75–1.0
- **Fixed points:** for PI, survives up to s≈0.75–0.9 before first loss
- **Convenience wrappers:** `prune_hebbian()`, `prune_pseudoinverse(s, max_iter)` (with iterative backoff)

---

### 2b. Iterative verify-and-prune (pseudoinverse only)
**File:** `phase1/pruning.py` → `prune_pseudoinverse(patterns, s, target_degree, max_iter)`

```
loop:
    W_candidate = prune_magnitude(W_dense, s=current_s)
    if all patterns still fixed points: accept; break
    current_s *= 0.8     # back off threshold
```

Uses the pseudoinverse's tolerance to find the largest s that preserves all M patterns. Typically finds 2–3× more sparsity than a fixed s would safely give.

- **Additional option:** `target_degree` triggers `_prune_to_degree()` — keeps only the k largest |W_ij| per row after magnitude pruning

---

## 3. Prune → retrain (mask-constrained retraining)

The core idea: use pruning to identify a **sparsity mask** (which connections are allowed), then re-optimize weights on that mask. The mask is fixed; only the non-zero values are updated.

### 3a. Storkey masked retrain
**File:** `phase1/pruning.py`  
`retrain_storkey_masked(patterns, W_sparse)` — raw retrain given a mask  
`prune_storkey_retrain(patterns, s)` — full pipeline (train → prune → retrain)

```
mask = (|W_sparse| > ε)
W ← 0
for each pattern ξ^μ:
    W += Storkey update
    W *= mask           ← enforce sparsity after every step
```

Re-runs the Storkey rule but zeros out disallowed connections after each pattern. The surviving weights compensate for the removed ones.

- **When it helps:** recovers fixed points that post-hoc pruning loses. At N=32, deg=12: recall at η=15% jumps from 0.50 → 0.76
- **When it doesn't help:** if the mask is too sparse (deg ≤ 5), even retrained weights can't satisfy all patterns

---

### 3b. Pseudoinverse masked least-squares retrain
**File:** `phase1/pruning.py`  
`retrain_pseudoinverse_masked(patterns, W_sparse)` — raw retrain given a mask  
`prune_pseudoinverse_retrain(patterns, s, max_iter)` — full pipeline with backoff

```
for each neuron i:
    S_i = {j : W_sparse[i,j] ≠ 0}
    w_i* = argmin ||w||²  s.t.  P[:, S_i] w ≈ P[:, i]
         = lstsq(patterns[:, S_i], patterns[:, i])
W = (W + Wᵀ)/2     ← symmetrize
```

Solves the true sparse pseudoinverse per neuron — minimum-norm weights on the allowed connections that best satisfy the fixed-point equations.

- **Counterintuitive result:** this is mathematically "optimal" for the mask, but performs **worse** than post-hoc pruning at low degrees. Reason: least-squares minimizes squared error but does not guarantee `sign(h_i) = ξ_i` (the strict bipolar fixed-point condition). At high degree (≥12) where the mask has enough expressivity, it works fine.
- **Use at:** degree ≥ 12 only; avoid below that

---

## 4. GD-based training with sparsity (alternatives to pseudoinverse)

These methods use a gradient/optimization framework that allows direct sparsity control during training, rather than train-then-prune.

### 4a. Storkey + L1 (ISTA)
**File:** `phase1/pruning.py` → `train_storkey_l1(patterns, lam, post_s)`

```
W ← 0
for each pattern ξ^μ:
    W += Storkey update
    W ← sign(W) × max(|W| − λ/N, 0)   ← L1 proximal / soft-threshold
```

L1 regularization applied as a soft-threshold proximal step after each Storkey update. Encourages sparsity during learning.

- **Problem:** λ/N threshold has a sharp transition — below critical λ, nearly fully connected; above it, nearly all zeros. Cannot target a specific degree smoothly
- **Verdict:** useful only for moderate sparsity (30–50% zeroed); not suited for low-degree control

---

### 4b. L1-SVM joint symmetric LP
**File:** `phase1/train_gd.py` → `train_l1svm(patterns, gamma, degree)`

```
minimize    Σ_{i<j} |w_ij|
subject to  ξᵢ^μ (Σ_j w_ij ξⱼ^μ) ≥ γ    for all i, μ
```

Single global linear program over all N(N−1)/2 upper-triangle weights (split into w⁺ − w⁻ for L1 objective). Symmetric by construction — the same w_ij appears in both neuron i's and j's constraints simultaneously. Solved via scipy HiGHS.

- **What it gives:**
  - Globally optimal: minimum total |W| that stores all patterns with margin γ
  - All patterns are exact fixed points ✓ (constraint enforces this)
  - Degree determined by M/N ratio, not γ: at α=0.25, N=32 → degree ~9 vs PI's 31
  - 2^9 = 512 vs 2^31 LUT entries — dramatic hardware reduction
- **Tradeoff:** noise recall at η=15% = 0.36 vs pseudoinverse's 0.71 at the same M/N
- **Complexity:** M×N constraints, N(N−1) variables. Feasible up to N~150, M~100
- **Parameters:** `gamma` — margin (does not control degree; only affects field size). `degree` — post-solve magnitude prune to cap connections (cannot add connections LP didn't find)

---

### 4c. Perceptron + L1 proximal (ISTA)
**File:** `phase1/train_gd.py` → `train_perceptron_l1(patterns, lam, gamma, lr, max_epochs, degree)`

```
Loss: L(W) = Σ_μ Σᵢ max(0, γ − ξᵢ^μ (Wᵢ·ξ^μ)) + λ||W||₁

Each epoch:
    G = ∇_W L_hinge        (−ξᵢ ξⱼ for violated margin neurons)
    G = (G + Gᵀ)/2         (symmetrize gradient)
    W ← W − lr·G           (gradient step)
    W ← sign(W)·max(|W|−λ·lr, 0)   (L1 proximal)
    W ← (W + Wᵀ)/2        (symmetrize weights)
```

The perceptron convergence theorem guarantees this halts in finite steps when a solution exists. Capacity approaches the Gardner bound (~0.64N) — well above Hebbian/Storkey.

- **3-threshold interpretation:** γ > 0 means only neurons with `ξᵢ^μ h_i < γ` (narrow margin) get updates — equivalent to Alemi et al. (2015)'s three-threshold rule that maximizes margins
- **With enough λ:** gradually zeroes small weights → sparsity. But λ tuning is sensitive; at current defaults (λ=0.005) it behaves nearly like pseudoinverse (degree ~31)
- **With degree cap:** post-training `_prune_to_degree()` gives exact degree control
- **Best use:** when you want high capacity (>0.22N) with moderate sparsity and can tune λ

---

### 4d. RigL dynamic sparse training
**File:** `phase1/train_gd.py` → `train_rigl(patterns, target_degree, gamma, lam, lr, max_epochs)`

```
Initialize: random symmetric mask (target_degree connections/neuron)
W ← 0

Every epoch:
    G = ∇_W L_hinge + L1 proximal   (on active connections only)
    W ← W − lr·G·mask               (gradient step, mask-constrained)
    W = (W + Wᵀ)/2·mask             (symmetrize within mask)

Every update_interval epochs (until 75% of training):
    Prune: remove grow_fraction of active connections with smallest |w|
    Grow:  add same count from inactive connections with largest |∂L/∂w|
    (All prune/grow done as symmetric pairs (i,j)+(j,i))
```

Adapted from Evci et al. (ICML 2020). The gradient of the hinge loss is cheap to compute even for zero-weight connections, enabling principled connectivity search.

- **Key advantage:** connectivity adapts to the problem — finds which neurons need to be connected based on gradient signal, not just magnitude
- **At N=32 deg=14:** recall at η=15% = **0.85** vs pseudoinverse post-hoc 0.77 at same degree
- **Current limitation:** initial symmetric mask init overshoots target degree (actual ~2× target); to fix: use Erdős–Rényi or k-regular graph initialization
- **Parameters:** `target_degree` — degree budget per neuron; `grow_fraction` — fraction of connections swapped each update; `update_interval` — epochs between mask updates

---

## 5. Methods from literature (research notes, not yet implemented)

*Documented in `meetings/2026-06-01/research/sgd_adjoint_methods.md`*

### 5a. Contrastive Hebbian Learning (CHL) / Contrastive Divergence
```
ΔW = η [s⁺(s⁺)ᵀ − s⁻(s⁻)ᵀ]
```
Two-phase: free settling (s⁻) then clamped settling (s⁺). CD-1 approximation makes it tractable. Supervised. Reduces spurious attractors. Both phases reuse existing settle circuit — natural for FPGA reuse.

### 5b. Equilibrium Propagation (EP)
```
ΔW_ij ∝ (sᵢ*sⱼ* − sᵢ^β sⱼ^β) / β
```
Proven equivalent to BPTT via implicit function theorem (Scellier & Bengio 2017). Implemented in EqSpike neuromorphic silicon. Binary neuron variant: s⁺ − s⁻ are sparse discrete bit flips → XOR-based update logic.

### 5c. Minimum Probability Flow (MPF)
```
L_MPF = Σ_{s∈data} Σ_{s'∈1-bit-flip(s)} exp(½(E(s,W) − E(s',W)))
```
Analytic gradient, no partition function. Capacity ≥ 1 pattern/neuron. Compatible with L1 penalty. (Hillar, Sohl-Dickstein & Koepsell 2012, arXiv:1204.2916)

### 5d. Straight-Through Estimator (STE)
Forward: `s = sign(h)`. Backward: `∂L/∂h ≈ ∂L/∂s · 1_{|h|≤1}`. Enables end-to-end SGD with binary neurons. Used with real-valued latent weights quantized to ±1 for FPGA. Transparent to hardware — only affects backward pass.

### 5e. Deep Equilibrium Models (DEQ) adjoint
```
∂L/∂θ = −(∂L/∂z*)ᵀ [∂f/∂z*]⁻ᵀ ∂f/∂θ
```
O(1) memory backpropagation through fixed-point equations (Bai, Kolter & Koltun, NeurIPS 2019). Requires linear solve at fixed point — feasible for N ≤ 512 with LU factorization.

---

## 6. Capacity summary

| Method | Theoretical capacity | Notes |
|---|---|---|
| Hebbian | **0.138N** | Hopfield (1982) |
| Storkey | **~0.22N** | ~60% above Hebbian |
| Pseudoinverse | **N** | Exact, offline only, M < N |
| Perceptron / 3-threshold | **≈0.64N** | Gardner bound (1988) |
| MPF | **≥ 1 patt/neuron** | Hillar & Sohl-Dickstein (2012) |
| Modern Hopfield (poly energy) | **Nⁿ⁻¹** | Krotov & Hopfield (2016) |
| Modern Hopfield (log-sum-exp) | **Exponential in N** | Ramsauer et al. (2021) — softmax attention |

---

## 7. Sparsity / degree control — method comparison

At **N=32, M=8 (α=0.25)**, all patterns preserved:

| Method | Degree | LUT entries | Recall η=15% |
|---|---|---|---|
| Pseudoinverse dense | 31 | 2^31 ≈ 2B | 0.89 |
| PI post-hoc (s=0.95) | 12 | ~2^12 × 32 ≈ 130k | 0.71 |
| Storkey masked retrain (deg 12) | 12 | ~130k | **0.76** |
| RigL (target deg 8, actual ~14) | 14 | ~262k | **0.85** |
| L1-SVM | **9** | ~2^9 × 32 = 16k | 0.36 |
| Perceptron-L1 (tuned) | 11 | ~66k | 0.59 |

**Fundamental tradeoff:** minimum degree (minimum LUT) vs. noise robustness. L1-SVM gives the theoretical minimum degree. RigL gives best recall at matched degree but overshoots degree target. Pseudoinverse post-hoc is the best fixed-point guarantee at intermediate degrees.

---

## 8. Which method to use

| Goal | Recommended method |
|---|---|
| Guaranteed storage of all patterns, best recall | Pseudoinverse (dense) |
| All patterns, minimum hardware (LUT size) | L1-SVM LP |
| All patterns, moderate hardware, good recall | PI post-hoc prune (s=0.75) |
| High capacity (>0.22N), tunable sparsity | Perceptron-L1 (tune λ) |
| Best recall at fixed degree budget | RigL + Storkey-retrain |
| Maximum pattern count (supervised, FPGA reuse) | CHL / Equilibrium Propagation |

---

## 9. File locations

| File | Contains |
|---|---|
| `sim/python/hopfield_net.py` | `HopfieldNetwork`, Hebbian/Storkey/PI train, async-cyclic run |
| `phase1/pruning.py` | `prune_magnitude`, `train_storkey_l1`, `prune_pseudoinverse`, `retrain_storkey_masked`, `retrain_pseudoinverse_masked`, `sweep_pruning_threshold`, `pruning_report` |
| `phase1/train_gd.py` | `train_l1svm`, `train_perceptron_l1`, `train_rigl`, `run_comparison` |
| `phase1/run_pruning_sweep.py` | CLI sweep: s × rule × N × M → CSV |
| `phase1/run_recall_sweep.py` | CLI sweep: M × s × noise → recall CSV |
| `phase1/run_degree_comparison.py` | 5-method degree-targeted comparison |
| `phase1/results/` | All output CSVs |
| `meetings/2026-06-01/research/sgd_adjoint_methods.md` | CHL, EP, MPF, STE, DEQ — theory + FPGA notes |
| `phase1/encoding_theory.md` | {0,1} ↔ {−1,+1} equivalence proof and threshold correction |
