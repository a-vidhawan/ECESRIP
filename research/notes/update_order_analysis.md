# Does Neuron Update Order Matter in Hopfield Networks?

*Research summary for ECE199 SRIP — May 2026*

---

## Short Answer

**Yes, significantly** — but in ways that matter differently for software vs. hardware. The update mode (async vs. sync) changes convergence guarantees, basin structure, and which attractors are reachable. The specific ordering within async (random vs. sequential) has subtler but real effects. For our LUT-based hardware design, this has direct implications for the control unit.

---

## 1. The Two Update Modes

### Asynchronous Update
One neuron is updated at a time. The selection can be:
- **Random**: pick a neuron uniformly at random each step (biologically plausible, theoretically clean)
- **Sequential**: cycle through neurons 1→2→…→N repeatedly
- **Greedy**: pick the neuron with the largest potential energy reduction

**Rule**: neuron i fires if `net_i = Σ_j w_ij * s_j > θ_i`, stays otherwise.

### Synchronous Update
All N neurons update simultaneously using the state from the *previous* timestep.

**Rule**: `s_i(t+1) = sign(Σ_j w_ij * s_j(t) - θ_i)` for all i at once.

Requires a global clock — natural for digital hardware, unnatural for biology.

---

## 2. Convergence Guarantees

This is where the modes diverge most sharply.

### Asynchronous: Guaranteed Convergence to Fixed Point

With symmetric weights (w_ij = w_ji) and zero self-connections (w_ii = 0), async update guarantees that the **energy function monotonically decreases or stays constant** at every update:

```
E = -½ Σ_ij w_ij * s_i * s_j + Σ_i θ_i * s_i
```

Flipping neuron i changes energy by: `ΔE = -Δs_i * net_i`

Since Δs_i and net_i have the same sign by the update rule, ΔE ≤ 0 always. Since the state space is finite (2^N states), the network **must** reach a fixed point in finite time.

**Proof sketch**: Energy is bounded below; each update either decreases it or leaves it constant. Once constant across all neurons, no update changes any state → fixed point reached.

### Synchronous: Convergence to Fixed Points OR 2-Cycles

With symmetric weights, synchronous update converges to either:
1. A **stable fixed point** (same guarantee as async), or
2. A **limit cycle of length 2** — the network oscillates between two complementary states indefinitely

The energy argument breaks down for synchronous updates because updating all neurons simultaneously can increase energy. Specifically: if two neurons i and j would each flip the other's field, flipping both simultaneously can increase the total energy.

**Example of a 2-cycle**: With N=2 neurons and weights w_12 = w_21 = -1:
- State (+1, +1): both neurons see negative net → both flip → (−1, −1)
- State (−1, −1): both see positive net → both flip → (+1, +1)
- Network oscillates forever, never converges

**Longer cycles (length > 2) are impossible** with symmetric weights — this was proven by Goles & Olivos (1980) and is a hard theoretical result.

---

## 3. Effect on Spurious States and Attractors

Both modes produce spurious attractors (local minima that aren't stored patterns), but the set of attractors can differ between modes:

### Common Spurious Attractors in Both Modes
- **Inverted patterns**: −ξ^μ for each stored pattern ξ^μ. Since the weight matrix is symmetric, if ξ is a fixed point, so is −ξ.
- **Mixture states** ("spin-glass" attractors): superpositions of an odd number of patterns, e.g., ½(ξ^1 + ξ^2 − ξ^3). These emerge when patterns are not orthogonal.

### Sync-Specific Spurious Attractors
Synchronous update generates **additional spurious attractors** not present in async mode. These are the period-2 oscillatory states — they look like spurious "memories" in hardware if you sample the wrong clock edge.

### Basins of Attraction
The energy landscape is **not symmetric** — some attractors have larger basins than others. Under async update, basins tend to be smoother (gradient descent on the energy surface). Under sync update, the effective "landscape" changes because multiple neurons shift simultaneously, carving out different basin boundaries.

**Practical consequence**: A test pattern corrupted with k% noise may converge to the correct stored pattern under async but fall into a spurious state under sync (or vice versa), especially near the capacity limit.

---

## 4. Effects on Capacity

The theoretical storage capacity (~0.138N patterns for Hebbian learning, per Amit et al. 1987) was derived assuming asynchronous updates. Under synchronous update:

- Capacity is **similar in the low-load regime** (P << 0.138N)
- **Degrades faster** near and above capacity because sync errors compound: a single wrong flip at t propagates to affect all neurons at t+1
- The 0.138N bound assumes Gaussian statistics of overlaps; synchronous correlations violate the independence assumptions in the derivation

---

## 5. Random vs. Sequential Async Ordering

Within asynchronous update, does it matter whether we pick neurons randomly or in fixed order 1,2,…,N?

### Convergence Speed
- Random ordering: O(N log N) updates expected to reach each neuron once (coupon collector's problem)
- Sequential ordering: exactly N updates per full sweep — more predictable

### Which Attractor is Reached
This is subtle and often overlooked. The same initial state can converge to **different attractors** depending on the update sequence:

- If neurons are updated in order 1→2→…→N, early neurons can shift the field seen by later ones, biasing the trajectory toward certain attractors
- Random ordering removes this systematic bias, making the basin boundaries closer to the "true" energy landscape basins
- Sequential ordering can create **hidden correlations** that slightly distort which patterns are reachable

### Biological Plausibility
Random async is considered the most biologically plausible (neurons fire based on noisy internal dynamics, not a global clock or fixed schedule). Hopfield's original 1982 paper assumed random async.

### For Hardware
Sequential async is easiest to implement in hardware — a simple counter selects the next neuron. Random async requires a pseudo-random number generator (LFSR or similar). Our current `update_ctrl.sv` uses sequential ordering.

---

## 6. Summary Table

| Property | Async (Random) | Async (Sequential) | Synchronous |
|----------|---------------|-------------------|-------------|
| Convergence guarantee | Fixed point ✓ | Fixed point ✓ | Fixed point or 2-cycle |
| Energy monotonicity | Yes | Yes | Not guaranteed |
| Spurious attractors | Standard set | Standard set + ordering bias | Standard set + 2-cycles |
| Capacity (Hebbian) | ~0.138N | ~0.138N (slight bias) | Slightly lower |
| Hardware complexity | Medium (needs PRNG) | Low (counter) | Low (single clock) |
| Bio plausibility | High | Medium | Low |
| Update speed | O(N log N) per pass | O(N) per pass | O(1) per pass (all parallel) |

---

## 7. Implications for Our LUT Hardware Design

Our current `update_ctrl.sv` implements **sequential async** with a registered FSM — this is the right default choice for hardware. Key takeaways for the design:

1. **Sequential async is safe**: Energy monotonicity is guaranteed → always converges. Good.

2. **Watch for ordering bias in testing**: When evaluating recall accuracy, use the same update order for all test patterns, or average over multiple orderings. Otherwise you're testing the schedule's bias, not the network's capacity.

3. **Sync mode as an option**: Our RTL has a sync mode flag. Use it for **speed benchmarking** (all neurons update in 1 clock cycle), but don't expect convergence — use it for a fixed number of iterations, not until-stable termination. Document this clearly.

4. **2-cycle detection in sync mode**: If we expose sync mode externally, add a 2-cycle detector: compare s(t) with s(t-2) and flag if equal. This catches the most common failure mode.

5. **PRNG for true random async**: For maximal research flexibility (and to reproduce results from papers using random async), add an LFSR to `update_ctrl.sv` as an optional mode. Low-cost: 16-bit LFSR is ~16 flip-flops.

---

## 8. Key References

- **Hopfield (1982)**: Original proof of async convergence via energy function. PNAS 79(8):2554–2558.
- **Goles & Olivos (1980)**: Proof that sync Hopfield with symmetric weights has only fixed points and 2-cycles. *Discrete Applied Mathematics*.
- **Amit, Gutfreund & Sompolinsky (1987)**: Statistical mechanics derivation of 0.138N capacity.
- **"Synchronous vs asynchronous behavior of Hopfield's CAM neural net"** — Optica / Applied Optics (1987). Direct experimental comparison. [ResearchGate](https://www.researchgate.net/publication/44649443_Synchronous_vs_asynchronous_behavior_of_Hopfield_s_CAM_neural_net)
- **"On the Dynamics of a Recurrent Hopfield Network"** (arXiv:1502.02444) — Analysis of cycle lengths and energy landscape.
- **Wikipedia: Hopfield network** — Good summary of both modes with energy proofs. [Link](https://en.wikipedia.org/wiki/Hopfield_network)
- **Scholarpedia: Hopfield network** — More rigorous treatment. [Link](http://www.scholarpedia.org/article/Hopfield_network)
