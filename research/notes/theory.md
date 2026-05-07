# Theoretical Foundations — LUT-Based Hopfield Network Hardware

**Project:** ECESRIP — Hopfield Network on FPGA via Truth Table Enumeration  
**Student:** Aarav Vidhawan

---

## 1. Hopfield Network Fundamentals

### 1.1 State and Weights

$N$ fully connected bipolar neurons: $s_i \in \{-1, +1\}$, state vector $\mathbf{s} \in \{-1,+1\}^N$.

Weight matrix $W \in \mathbb{R}^{N \times N}$ must satisfy:
- **Symmetry:** $w_{ij} = w_{ji}$
- **Zero diagonal:** $w_{ii} = 0$

Both are required for guaranteed convergence (Section 3).

### 1.2 Update Rule

Local field at neuron $i$:

$$h_i(\mathbf{s}) = \sum_j w_{ij} s_j$$

Update: $s_i \leftarrow \text{sign}(h_i)$, with the convention $s_i$ unchanged if $h_i = 0$.

**Binary domain:** truth tables use $b_j = \frac{s_j+1}{2} \in \{0,1\}$. Substituting $s_j = 2b_j - 1$:

$$h_i = 2\sum_j w_{ij} b_j - \sum_j w_{ij}$$

The output bit $b_i^{\text{new}} = \mathbf{1}[h_i \geq 0]$ is the Boolean function enumerated in the truth table.

### 1.3 Energy Function

$$E(\mathbf{s}) = -\frac{1}{2}\mathbf{s}^\top W \mathbf{s} + \boldsymbol{\theta}^\top \mathbf{s}$$

$E$ is bounded over the finite state space $\{-1,+1\}^N$. Local minima of $E$ are fixed points (stable states). Training sets $W$ so that stored patterns become local minima.

---

## 2. Learning Rules

### 2.1 Hebbian (Outer Product)

$$W = \frac{1}{N}\sum_{\mu=1}^{M} \boldsymbol{\xi}^\mu (\boldsymbol{\xi}^\mu)^\top - I$$

The $-I$ term enforces $w_{ii} = 0$. Substituting into the local field of a stored pattern $\boldsymbol{\xi}^\mu$:

$$h_i(\boldsymbol{\xi}^\mu) = \underbrace{\xi^\mu_i}_{\text{signal}} + \underbrace{\frac{1}{N}\sum_{\nu \neq \mu} \xi^\nu_i \left(\sum_j \xi^\nu_j \xi^\mu_j\right)}_{\text{cross-talk noise}}$$

Cross-talk grows with $M$; above $M \approx 0.14N$ it overwhelms the signal.

### 2.2 Storkey Rule

Incremental — adds one pattern at a time while accounting for the current weight matrix:

$$W^\mu = W^{\mu-1} + \frac{1}{N}\left(\boldsymbol{\xi}^\mu(\boldsymbol{\xi}^\mu)^\top - \mathbf{h}^\mu(\boldsymbol{\xi}^\mu)^\top - \boldsymbol{\xi}^\mu(\mathbf{h}^\mu)^\top\right)$$

where $h^\mu_i = \sum_{j \neq i} W^{\mu-1}_{ij} \xi^\mu_j$. The correction terms reduce cross-talk, giving better recall quality at the same load ratio.

### 2.3 Capacity

$$M_{\max} \approx 0.138 \cdot N \quad \text{(Hebbian — Amit, Gutfreund \& Sompolinsky 1985)}$$

Above this the network still converges, but to **spurious states**: mixtures $\text{sign}(\pm\boldsymbol{\xi}^a \pm \boldsymbol{\xi}^b \pm \cdots)$ or negatives $-\boldsymbol{\xi}^\mu$ (always a fixed point when $\boldsymbol{\xi}^\mu$ is, by symmetry of $W$). Storkey achieves better quality at the same load but the same $\approx 0.14N$ threshold.

### 2.4 Why Not Modern Hopfield Networks?

Ramsauer et al. (2020) achieve $M \propto e^N$ via softmax interactions — floating-point, not a Boolean threshold function. Cannot be enumerated as a truth table. Classical Hopfield is the only variant that maps directly to a LUT.

---

## 3. Convergence Theory

### 3.1 Fixed Points

$\mathbf{s}^*$ is a fixed point iff $s^*_i = \text{sign}\!\left(\sum_j w_{ij} s^*_j\right)$ for all $i$ simultaneously. The fixed-point set is determined entirely by $W$ — independent of update schedule.

### 3.2 Energy Monotonicity (Hopfield 1982)

When neuron $i$ updates, only $s_i$ changes. The energy change is:

$$\Delta E = -h_i \cdot \Delta s_i$$

Since $s_i^{\text{new}} = \text{sign}(h_i)$, the sign of $\Delta s_i$ always agrees with $h_i$, so $\Delta E \leq 0$ on every update. Because $E$ is bounded below and the state space is finite, the network reaches a fixed point in finitely many steps. $\square$

**Why symmetry is necessary:** the cross-terms in $\Delta E$ cancel only when $w_{ij} = w_{ji}$.  
**Why zero diagonal:** $w_{ii} < 0$ (self-inhibition) can cause a neuron to always want to flip, preventing convergence ($W = -I$ never converges).

### 3.3 Convergence Speed

Finding a stable state is **PLS-complete** (Schaffer & Yannakakis 1991) — worst-case super-polynomial. In practice, well-separated patterns converge in $O(N)$ sweeps. Hardware should include a maximum-sweep timeout (e.g. $20N$ updates).

---

## 4. Update Order

### 4.1 Modes

| Mode | Description | Limit set | Order affects attractor? |
|---|---|---|---|
| **Async cyclic** ← recommended | One neuron/step, order $1\to2\to\cdots\to N$ | Fixed points only | Yes |
| Async random | One neuron/step, random permutation each sweep | Fixed points only | Yes |
| Synchronous | All $N$ neurons update simultaneously | Fixed points **or 2-cycles** | N/A |
| Block-sequential | $K$ neurons/step, alternating groups | Fixed points only (small blocks) | Yes |

**Async (any fair schedule) with symmetric $W$, $w_{ii}=0$:** the energy proof guarantees convergence to a fixed point regardless of order.

**Synchronous:** may enter a 2-cycle — two states $\mathbf{s}^A, \mathbf{s}^B$ alternating indefinitely; convergence detector never fires (Goles & Olivos 1980; Bruck 1990).

### 4.2 Order and Attractors

The specific update order doesn't affect *whether* the network converges — only *which* fixed point is reached from a given initial state. The fixed-point set is the same for all schedules.

**Hardware choice — async cyclic:** directly models the sequential update controller (cyclic counter), is deterministic and reproducible, and carries the full Hopfield convergence proof.

---

## 5. LUT-Based Hardware Approach

### 5.1 Truth Table Enumeration

For neuron $i$, enumerate all $2^N$ binary input vectors $\mathbf{b} \in \{0,1\}^N$:

1. Convert: $s_j = 2b_j - 1$  
2. Compute: $h_i = \sum_j w_{ij} s_j$  
3. Output: $b_i^{\text{new}} = \mathbf{1}[h_i \geq 0]$ (hold $b_i$ if $h_i = 0$)

Since $w_{ii} = 0$, input $b_i$ is a **don't-care** — the minimiser can use it freely to reduce logic.

### 5.2 Espresso Minimisation

PLA files are minimised by Espresso into a Sum of Products (SOP), mapping directly to a two-level AND-OR LUT network:

- **Phase 1 (clocked):** standard Espresso — minimal SOP
- **Phase 2 (async):** Espresso `-Dhazard` — adds consensus terms to prevent static-1 hazards

### 5.3 Scalability

| $N$ | Rows per neuron | Espresso time | Feasibility |
|---|---|---|---|
| ≤ 10 | ≤ 1,024 | < 1 s | Easy |
| ≤ 14 | ≤ 16,384 | seconds | Feasible |
| ≤ 16 | ≤ 65,536 | minutes | Borderline |
| > 16 | > 65 K | infeasible | Keep $F$ strongest $|w_{ij}|$ per neuron |

---

## 6. Hazard-Free Logic (Phase 2)

A **static-1 hazard** occurs when the output should stay at 1 during a single-input transition but glitches to 0 because the transition falls between two product terms with a coverage gap. In a combinational feedback loop, a glitch is a spurious input transition to downstream neurons and can corrupt the state trajectory.

**Consensus theorem:**

$$AB + \bar{A}C = AB + \bar{A}C + BC$$

$BC$ is the consensus term — logically redundant but covers the $A: 1\to 0$ transition where both $AB$ and $\bar{A}C$ may momentarily be 0. Espresso `-Dhazard` adds exactly these terms for every hazardous implicant pair.

**Limitation:** `-Dhazard` covers only single-variable input transitions. Near-simultaneous neuron updates create multi-input transitions — not covered. In Phase 1 this cannot happen (only one neuron changes per clock cycle). In Phase 2 it is an open research question.

---

## 7. Hardware Architecture

### 7.1 Phase 1 — Clocked

```
State Register  s[0..N-1]  ◄─────────────────────────┐
      │ (broadcast all N bits)                         │
      ▼                                                │
Neuron LUT Bank: LUT_0 … LUT_{N-1}  (combinational)   │
      │ s_new[0..N-1]                                  │
      ▼                                                │
Update Controller (cyclic counter 0→N-1→0)             │
  Each cycle: s_new[i] → s[i] via write-enable  ───────┘
  After full sweep: converged = (s ^ s_prev == 0)
```

One neuron updates per clock cycle → only one input bit changes per cycle → single-input transition guarantee at all LUTs.

### 7.2 Phase 2 — Async

Remove flip-flops. Route each `s_new[i]` directly back as input to all other LUTs. Circuit settles combinationally. Hazard-free SOP prevents glitches on single-variable transitions.

### 7.3 Convergence Detection

$$\text{converged} = \bigoplus_{i}(s_i \oplus s_{\text{prev},i}) = 0$$

In SystemVerilog: `done = (s ^ s_prev) == '0;`

### 7.4 Module Hierarchy

```
hopfield_top.sv
├── neuron_logic_bank.sv   ← N auto-generated neuron_update_i modules (SOP)
├── state_reg.sv           ← N flip-flops with per-bit write-enable
└── update_ctrl.sv         ← cyclic counter + convergence detector
```

---

## 8. Hopfield–Ising Equivalence

The Ising Hamiltonian:

$$\mathcal{H} = -\sum_{i<j} J_{ij} s_i s_j - \sum_i h_i s_i$$

is identical to the Hopfield energy under $J_{ij} \leftrightarrow w_{ij}$, $h_i \leftrightarrow -\theta_i$. Any NP-hard problem encodable as an Ising Hamiltonian can be encoded as $W$ and solved approximately by the LUT circuit relaxing to a fixed point.

| Problem | Encoding |
|---|---|
| Max-Cut | $J_{ij} = -w_{ij}^{\text{graph}}$; ground state = maximum cut |
| Graph colouring | Penalty for adjacent same-colour assignments |
| Vertex cover | Edge-coverage reward + cover-size penalty |
| SAT | Per-clause penalty terms |

The circuit finds local energy minima (greedy local search). Multiple random restarts or noise injection are needed for higher-quality solutions.

---

## 9. Open Questions

1. Does `-Dhazard` SOP prevent all convergence errors in the Phase 2 combinational loop, or only those caused by single-variable transitions?
2. How often does the Phase 2 circuit enter a 2-cycle vs a fixed point, as a function of $N$ and $M$?
3. For $N > 16$: optimal weight pruning — strongest-$F$, random expander (LogicNets), or learned mask?
4. Ising solution quality vs simulated annealing on standard G-set Max-Cut benchmarks.
5. Empirical convergence-time distribution near $M = 0.14N$ — how does it scale with $N$?
6. Metastability at $h_i = 0$: frequency as a function of $N$, $M$, and weight distribution.

---

## References

1. Hopfield, J.J. (1982). *PNAS* 79(8):2554–2558.
2. Hopfield, J.J. (1984). *PNAS* 81(10):3088–3092.
3. Amit, D.J., Gutfreund, H. & Sompolinsky, H. (1985). *Physical Review A* 32(2):1007.
4. Goles, E. & Olivos, J. (1980). *Discrete Mathematics* 30(2):187–189.
5. Goles-Chacc, E., Fogelman-Soulie, F. & Pellegrin, D. (1985). *Discrete Applied Mathematics* 12(3):261–277.
6. Bruck, J. (1990). *Proceedings of the IEEE* 78(10):1579–1585.
7. Schaffer, M. & Yannakakis, M. (1991). *SIAM J. Computing* 20(1):56–87.
8. Storkey, A.J. (1997). *ICANN*, LNCS 1327:451–456.
9. Lucas, A. (2014). *Frontiers in Physics* 2:5.
10. Ramsauer, H. et al. (2020). *ICLR 2021*, arXiv:2008.02217.
11. Umuroglu, Y. et al. (2020). *FPL 2020*, arXiv:2004.03021.
12. Sousa, F. et al. (2014). *Advances in Artificial Neural Systems*, Hindawi, 602325.
13. Goemaere, C., Deleu, J. & Demeester, T. (2024). *ECAI 2024*, arXiv:2311.15673.
14. IEEE CAS (1994). *IEEE Trans. Circuits Syst. I*, DOI:10.1109/81.363543.
