# Research Notes: Adjoint Methods and SGD for Binary Hopfield Networks

*Branch: may19 — 2026-05-19*

---

## Notation Baseline

| Symbol | Meaning |
|---|---|
| s ∈ {−1,+1}^N | Bipolar neuron state |
| W ∈ ℝ^{N×N} | Symmetric weight matrix (W = Wᵀ, diag = 0) |
| E(s) = −½ sᵀWs | Hopfield energy |
| ξ^μ | Stored pattern μ |
| s* | Fixed-point attractor: sᵢ* = sign(Wᵢ·s*) |

Classical rules (Hebbian, Storkey, pseudo-inverse) are closed-form and non-iterative. The methods below replace or augment them with gradient-based optimisation over W.

---

## 1. Contrastive Hebbian Learning (CHL) / Boltzmann Training

**Core idea.** Run the network to a free-phase fixed point s⁻ (unclamped), then run again with output units nudged toward the target to produce s⁺ (clamped). The weight update is the difference of outer products:

```
ΔW = η [ s⁺(s⁺)ᵀ − s⁻(s⁻)ᵀ ]
```

For Boltzmann machines the exact log-likelihood gradient is:

```
∂ log p(v) / ∂w_{ij} = ⟨sᵢsⱼ⟩_data − ⟨sᵢsⱼ⟩_model
```

Contrastive Divergence (CD-k, Hinton 2002) approximates the model expectation with k Gibbs steps — CD-1 is practical for hardware (one update pass per training example).

**Adjoint connection.** Movellan (1990) showed that CHL is equivalent to the adjoint/sensitivity gradient of the energy through the recurrent dynamics, exact in the small-nudge (β→0) limit.

**Advantages over Hebbian/Storkey.** Supervised; reduces spurious attractors by contrasting desired vs. actual attractors; capacity empirically above 0.138N.

**FPGA relevance.** Both phases reuse the existing async settle circuit. Weight increments are outer products → BRAM accumulators. CD-1 minimises the second settling phase.

**References**
- Movellan, J. (1990). *Contrastive Hebbian Learning in the Continuous Hopfield Model.* Connectionist Models Summer School.
- Hinton, G. (2002). *Training Products of Experts by Minimizing Contrastive Divergence.* Neural Computation 14(8).

---

## 2. Equilibrium Propagation (EP)

**Core idea.** EP computes the exact backprop gradient of a supervised loss L(s*, y) w.r.t. W using only local Hebbian updates and two settling phases — no explicit error propagation wiring.

Define the nudged energy:

```
F_β(s, W) = E(s, W) + β · C(s, y)
```

where C(s, y) is a cost (e.g., squared error on output units), s* = argmin_s E, s^β = argmin_s F_β. The weight gradient is:

```
∂L/∂W_{ij} = lim_{β→0} (1/β) [ −sᵢ^β sⱼ^β + sᵢ* sⱼ* ] / 2
```

so the update rule is:

```
ΔW_{ij} ∝ (sᵢ* sⱼ* − sᵢ^β sⱼ^β) / β
```

Scellier & Bengio (2017) proved this is mathematically equivalent to BPTT via the implicit function theorem on the fixed-point equation.

**Advantages.** Computes the true backprop gradient; only local synaptic updates; works for any symmetric energy, not just quadratic Hopfield.

**FPGA relevance.**
- *EqSpike* (Laydevant et al. 2021): spiking EP on neuromorphic silicon, 2–3 orders of magnitude lower energy than GPU.
- *Memristor crossbar* (2023): implements both EP phases simultaneously in analog hardware.
- Binary neurons (sign activations): s^β − s* consists of sparse discrete bit flips → XOR-based update logic.
- Finite-β (non-infinitesimal) avoids numerical precision issues on fixed-point hardware.

**References**
- Scellier, B. & Bengio, Y. (2017). *Equilibrium Propagation.* Frontiers in Computational Neuroscience 11:24. arXiv:1602.05179
- Ernoult, M. et al. (2020). *Continual Weight Updates and Convolutional Architectures for EP.* arXiv:2005.04169
- Laborieux, A. et al. (2021). *Scaling EP to Deep ConvNets.* Frontiers in Neuroscience. PMC7930909
- Høier, R. & Zach, C. (2024). *Two Tales of Single-Phase Contrastive Hebbian Learning.* ICML 2024. arXiv:2402.08573
- Laydevant et al. (2021). *EqSpike.* arXiv:2010.07859

---

## 3. Modern Energy-Based Learning (EBM Perspective)

### 3a. Minimum Probability Flow (MPF)

Treat the HNN as a probabilistic model p(s) ∝ exp(−E(s)/T). MPF (Sohl-Dickstein et al. 2011) fits binary energy models without estimating the partition function:

```
L_MPF(W) = Σ_{s∈data} Σ_{s'~Flip-one(s)} exp( ½(E(s,W) − E(s',W)) )
```

The gradient is analytic, local, and enforces that flipping any single bit from a stored pattern increases energy. Provably achieves capacity ≥ 1 pattern/neuron (vs. Hebbian 0.138N).

**References**
- Sohl-Dickstein, J., Battaglino, P., & DeWeese, M. (2011). *Minimum Probability Flow Learning.* Physical Review Letters.
- Hillar, C., Sohl-Dickstein, J., & Koepsell, K. (2012). *Efficient and Optimal Binary Hopfield Storage Using MPF.* arXiv:1204.2916

### 3b. Modern / Dense Hopfield Networks

Krotov & Hopfield (2016) replaced the quadratic energy with a polynomial interaction F(x) = x^n, giving capacity scaling as N^{n−1}. Ramsauer et al. (2021) use a log-sum-exp energy; the update rule is **identical to softmax attention** in Transformers, enabling end-to-end SGD/Adam training of memory patterns.

**FPGA relevance.** Polynomial energy (integer n) maps to fixed-point LUT arithmetic. Binary-quantized modern Hopfield (argmax instead of softmax) recovers classical binary update; computable with bit-serial multipliers.

**References**
- Krotov, D. & Hopfield, J. (2016). *Dense Associative Memory for Pattern Recognition.* NeurIPS 2016. arXiv:1606.01164
- Ramsauer, H. et al. (2021). *Hopfield Networks is All You Need.* ICLR 2021. arXiv:2008.02217

---

## 4. SGD on the Fixed-Point / Overlap Loss (Perceptron Rule)

**Core idea.** Define a margin loss measuring how well patterns are stable fixed points:

```
L(W) = Σ_μ Σᵢ max(0, −ξᵢ^μ · (Wᵢ · ξ^μ))
```

This is positive when neuron i gets the wrong sign from pattern μ. The gradient:

```
∂L/∂W_{ij} = −Σ_{μ: margin violated at i} ξᵢ^μ ξⱼ^μ
```

This is the perceptron learning rule applied per-neuron — guaranteed to converge to the Gardner bound (capacity ≈ 2N/π ≈ **0.64N**) when a solution exists.

The **three-threshold learning rule** (Alemi et al. 2015) approaches maximal recurrent network capacity:

```
ΔW_{ij} ∝ (h_i − θ₁)₊ ξⱼ − (h_i − θ₂)₊ ξⱼ − (h_i − θ₃)₊ ξⱼ
```

where h_i = Wᵢ · ξ and θ₁ < θ₂ < θ₃.

**Advantages.** Achieves 0.64N capacity (vs. Hebbian 0.138N); local, incremental, mini-batch compatible. The margin violation check is a single-bit comparison — directly implementable as an on-chip FSM.

**References**
- Alemi, A. et al. (2015). *A Three-Threshold Learning Rule Approaches the Maximal Capacity of Recurrent Neural Networks.* PLoS Computational Biology. arXiv:1508.00429
- Gardner, E. (1988). *The space of interactions in neural network models.* J. Physics A.

---

## 5. Adjoint-State / Implicit Differentiation Through Fixed Points

**Core idea.** Treat the fixed-point condition F(s*, W) = s* − sign(Ws*) = 0 as defining s*(W) implicitly. The adjoint gradient of any loss L(s*(W)) w.r.t. W is obtained by differentiating F=0:

```
ds*/dW = −(∂F/∂s*)⁻¹ · ∂F/∂W
```

In the continuous relaxation (tanh instead of sign) this is **Recurrent Backpropagation (RBP)** (Almeida 1987, Pineda 1987). For binary neurons, the Jacobian of sign is zero a.e., requiring a surrogate (see §6).

**Deep Equilibrium Models (DEQ, Bai et al. NeurIPS 2019)** formalise this for deep networks: instead of unrolling, solve the fixed-point equation directly and backpropagate through the implicit equation using the adjoint — **O(1) memory** regardless of depth.

```
∂L/∂θ = −(∂L/∂z*)ᵀ [∂f/∂z*|_{z*}]⁻ᵀ ∂f/∂θ|_{z*}
```

**FPGA relevance.** The linear solve (∂F/∂s*)⁻¹ v reduces to matrix-vector products for small N (≤ 256), feasible with existing LUT dot-product hardware. Training only — inference keeps binary sign.

**References**
- Almeida, L.B. (1987). *A Learning Rule for Asynchronous Perceptrons with Feedback.* IEEE ICNN.
- Pineda, F.J. (1987). *Generalization of back-propagation to recurrent neural networks.* Physical Review Letters 59(19).
- Bai, S., Kolter, J.Z., & Koltun, V. (2019). *Deep Equilibrium Models.* NeurIPS 2019. arXiv:1909.01377

---

## 6. Straight-Through Estimator (STE) for Binary Neurons

The sign(·) activation has zero gradient almost everywhere. The **Straight-Through Estimator** replaces it with a clipped identity in the backward pass:

```
Forward:  s = sign(h)
Backward: ∂L/∂h ≈ ∂L/∂s · 1_{|h| ≤ 1}   (clipped STE)
```

This enables end-to-end SGD on any loss while keeping binary forward-pass activations. Combined with EP or MPF, the workflow is:

1. Maintain **real-valued latent weights** W̃ during training.
2. Quantise W = Q(W̃) for forward pass (integers or ±1).
3. Relax binary updates with tanh(βh) for backward pass (or STE).
4. Run EP/MPF loss.
5. After training, snap W̃ → W and burn into FPGA BRAM/LUT.

**References**
- Bengio, Y., Léonard, N., & Courville, A. (2013). *Estimating or Propagating Gradients Through Stochastic Neurons.* arXiv:1308.3432
- Yin, P. et al. (2019). *Understanding STE in Training Activation Quantized Neural Nets.* ICLR 2019.
- Ghosh, S. et al. (2021). *AdaSTE: An Adaptive Straight-Through Estimator to Train Binary Neural Networks.* arXiv:2112.02880

---

## Summary Comparison

| Method | Capacity | Supervised? | Gradient source | FPGA friendliness |
|---|---|---|---|---|
| Hebbian (baseline) | 0.138N | No | Closed-form | Excellent |
| Storkey (baseline) | ~0.22N | No | Closed-form | Excellent |
| Pseudo-inverse | N | No | Closed-form | Excellent (offline) |
| CHL / CD | > Hebbian | Yes | Two-phase outer product | Good (reuse settle) |
| Equilibrium Propagation | Depends on loss | Yes | β-nudge difference | Good (EqSpike) |
| MPF | ≥ 1 pattern/neuron | No | Analytic neighbor flip | Good (sparse grad) |
| Perceptron / 3-threshold SGD | ≈ 0.64N | No | Local margin | Excellent (FSM) |
| DEQ adjoint | Depends | Yes | Linear solve at s* | Moderate |
| STE + EP/MPF | Depends on combo | Yes | Surrogate backward | Good (training only) |

## Key Takeaways for LUT-HNN

1. **Best capacity / hardware fit**: Perceptron/three-threshold SGD achieves ~0.64N, is local, incremental, maps to a simple on-chip FSM.
2. **Supervised training**: Equilibrium Propagation reuses the existing settle circuit for both phases; EqSpike shows neuromorphic silicon viability.
3. **End-to-end deep-learning workflow**: Modern Hopfield (Ramsauer et al.) → train with Adam → quantise weights for FPGA.
4. **Binary activations**: STE is standard in BNN toolchains; transparent to hardware (affects backward pass only).
5. **True gradient through fixed points**: DEQ adjoint is clean but requires a linear solve — feasible for N ≤ 256–512.
