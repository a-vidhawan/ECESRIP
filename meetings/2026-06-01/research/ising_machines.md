# Research Notes: HNN as Ising Machines — Combinatorial Optimization

*Branch: may19 — 2026-05-19*

---

## 1. Ising Machine Formulation and Equivalence to HNN Energy

### 1.1 The Ising Hamiltonian

```
H = −Σᵢ<ⱼ Jᵢⱼ σᵢ σⱼ  −  Σᵢ hᵢ σᵢ
```

σᵢ ∈ {−1, +1} are spins, Jᵢⱼ are pairwise couplings (symmetric), hᵢ is an external field. Finding the ground state (minimum H) is NP-hard in general.

### 1.2 Exact Correspondence to HNN

| Ising | HNN |
|---|---|
| Spin σᵢ | Neuron sᵢ |
| Coupling Jᵢⱼ | Wᵢⱼ / 2 |
| External field hᵢ | Bias bᵢ (currently missing) |
| Ground state | Fixed point of minimum energy |

Setting **Wᵢⱼ = 2Jᵢⱼ** (i≠j), Wᵢᵢ = 0, **bᵢ = hᵢ** gives:

```
E_HNN = −½ sᵀWs − bᵀs  ≡  H_Ising  (up to a constant)
```

The async-cyclic update sᵢ ← sign(Wᵢ·s + bᵢ) performs gradient descent on this energy — every update is non-increasing in E (Hopfield 1982, Goles & Olivos 1980).

### 1.3 QUBO Conversion

Binary {0,1} variables xᵢ relate to bipolar spins via xᵢ = (σᵢ + 1)/2. Any QUBO `min xᵀQx` maps to Ising via:

```
Jᵢⱼ = −Qᵢⱼ/4                          (off-diagonal, i ≠ j)
hᵢ  = −(Qᵢᵢ + Σⱼ Qᵢⱼ + Σⱼ Qⱼᵢ) / 4   (linear / bias term)
```

**References**
- Hopfield, J.J. (1982). *Neural networks and physical systems with emergent collective computational abilities.* PNAS 79:2554.
- Goles, E. & Olivos, J. (1980). *Periodic behaviour of generalized threshold functions.* Discrete Mathematics 30:187.
- Lucas, A. (2014). *Ising formulations of many NP problems.* Frontiers in Physics 2:5. https://doi.org/10.3389/fphy.2014.00005

---

## 2. Model Changes: Memory-Recall HNN → Ising Solver

### 2.1 Primary Missing Piece: Bias Vector

Our current `hopfield_net.py` has no bias b. Every combinatorial problem with linear penalty terms requires it.

**`__init__` change:**
```python
self.b = np.zeros(N)
```

**`run()` change (one line):**
```python
# was:   h_i = float(self.W[i] @ s)
h_i = float(self.W[i] @ s) + self.b[i]
```

**`energy()` change:**
```python
def energy(self, s):
    return -0.5 * float(s @ self.W @ s) - float(self.b @ s)
```

### 2.2 W Construction Shifts from Training to Problem Encoding

In memory-recall mode, W comes from Storkey/Hebbian pattern training. In optimization mode, W is set directly from the problem's coupling matrix:

```python
@classmethod
def from_ising(cls, J, h=None, **kwargs):
    N = J.shape[0]
    net = cls(N, **kwargs)
    net.W = 2.0 * J
    np.fill_diagonal(net.W, 0)
    net.b = h if h is not None else np.zeros(N)
    return net

@classmethod
def from_qubo(cls, Q, **kwargs):
    N = Q.shape[0]
    J = np.zeros((N, N))
    h = np.zeros(N)
    for i in range(N):
        for j in range(i+1, N):
            J[i,j] = J[j,i] = -Q[i,j] / 4.0
        h[i] = -(Q[i,i] + Q[i,:].sum() + Q[:,i].sum()) / 4.0
    return cls.from_ising(J, h, **kwargs)
```

### 2.3 Convergence Criterion Shifts

- Memory-recall: stop at fixed point; return final state.
- Optimization: track `best_s, best_E` across the entire run — the fixed point is a local minimum, not necessarily the ground state. Return the **best state seen**, not just the final state.

### 2.4 Simulated Annealing to Escape Local Minima

Deterministic async updates get trapped. Add stochastic Boltzmann acceptance:

```python
def run_annealed(self, s_init, T_start=2.0, T_end=0.01,
                 n_sweeps=1000, schedule='geometric', rng=None):
    s = s_init.copy(); best_s = s.copy(); best_E = self.energy(s)
    for sweep in range(n_sweeps):
        t = sweep / (n_sweeps - 1)
        T = T_start * (T_end/T_start)**t  # geometric cooling
        for i in rng.permutation(self.N):
            h_i = float(self.W[i] @ s) + self.b[i]
            prob_up = 1.0 / (1.0 + np.exp(-2.0 * h_i / T))
            s[i] = 1.0 if rng.random() < prob_up else -1.0
        E = self.energy(s)
        if E < best_E: best_E = E; best_s = s.copy()
    return best_s, best_E
```

At T→0 this recovers deterministic async updates. Geometric cooling (α ≈ 0.95–0.99 per sweep) is standard. **Note:** stochastic updates on FPGA require an LFSR + sigmoid LUT — significant extra logic cost. Deterministic alternatives (SBM, §6.3) avoid this.

### 2.5 Summary of Code Changes

| Change | Where | Lines |
|---|---|---|
| `self.b = np.zeros(N)` in `__init__` | hopfield_net.py | 1 |
| `h_i + self.b[i]` in `run()` | hopfield_net.py | 2 |
| `−bᵀs` in `energy()` | hopfield_net.py | 1 |
| `from_ising()` classmethod | hopfield_net.py | ~10 |
| `from_qubo()` classmethod | hopfield_net.py | ~15 |
| `run_annealed()` method | hopfield_net.py | ~30 |
| Track `best_s, best_E` in runs | hopfield_net.py | ~5 |

**Hardware pipeline**: The bias bᵢ shifts each neuron's threshold in its truth table. The Espresso minimisation pipeline handles this transparently — no changes to `truth_table_gen.py` or `sv_export.py`, just regenerate the truth tables with the new W and b.

---

## 3. MaxCut Problem

### 3.1 Problem Definition

Given undirected weighted graph G = (V, E) with edge weights wₑ ≥ 0, partition V into S and V\S to maximise:

```
MaxCut(S) = Σ_{(i,j)∈E, i∈S, j∉S} w_{ij}
```

NP-hard (approximable to 0.878 by Goemans–Williamson SDP 1995).

### 3.2 HNN Encoding

Assign sᵢ ∈ {−1,+1}: sᵢ = +1 ↔ i ∈ S. Edge (i,j) is in the cut iff sᵢsⱼ = −1. So:

```
MaxCut = const − ½ Σ_{(i,j)∈E} w_{ij} sᵢsⱼ
```

**Minimising** the HNN energy E = −½ sᵀWs with **Wᵢⱼ = −w_{ij}** (negative!) for edges maximises the cut.

```python
W = np.zeros((N, N))
for (i, j, w) in edges:
    W[i,j] = W[j,i] = -w   # negative edge weight → anti-alignment preferred
# No bias needed for unweighted MaxCut (h = 0)
```

MaxCut is the **only major benchmark problem that needs no bias vector**.

### 3.3 Benchmark Datasets

| Dataset | Instances | Size (nodes) | URL |
|---|---|---|---|
| **Gset** | 71 (G1–G81) | 800–10,000 | http://web.stanford.edu/~yyye/yyye/Gset/ |
| **BiqMac** | ~100 | up to 3,000 | https://biqmac.aau.at/biqmaclib.html |
| **MaxCutBench** (2024) | Standardized | Various | arXiv:2406.11897 |
| **Stanford SNAP** | Large real graphs | Millions | https://snap.stanford.edu/data/ |

**References**
- Burer, S., Monteiro, R.D.C. & Zhang, Y. (2002). *Mathematical Programming 94.*
- Rendl, F., Rinaldi, G. & Wiegele, A. (2010). *Solving Max-Cut to Optimality.* Math. Programming 121:307.
- Böther, M. et al. (2024). *A Benchmark for Maximum Cut.* arXiv:2406.11897.

---

## 4. Travelling Salesman Problem (TSP)

### 4.1 Hopfield–Tank 1985 Formulation

**Reference**: Hopfield, J.J. & Tank, D.W. (1985). *'Neural' Computation of Decisions in Optimization Problems.* Biological Cybernetics 52:141.

**Encoding.** N² binary neurons V_{xi}: city x at position i in the tour.

**Energy (penalty + objective):**

```
E = A/2 Σₓ (Σᵢ V_{xi} − 1)²         [each city appears once]
  + B/2 Σᵢ (Σₓ V_{xi} − 1)²         [each position has one city]
  + C/2 (Σₓᵢ V_{xi} − N)²           [total count = N]
  + D/2 Σₓ≠y Σᵢ d_{xy} V_{xi}(V_{y,i+1} + V_{y,i−1})   [distance]
```

Weight matrix W is N²×N²; bias vector b is length N². The key weakness: tuning A, B, C, D is delicate — too-small constraint weights → invalid tours; too-large → random tours. Only ~1–8% of runs from random starts yield valid tours for N=10 (Wilson & Pawley 1988).

### 4.2 Benchmark Datasets

| Dataset | Notes | URL |
|---|---|---|
| **TSPLIB** | 100+ instances, N=51 to 1,812,000, real-world geography | http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/ |
| **Waterloo TSP** | Known optimal solutions | http://www.math.uwaterloo.ca/tsp/data/ |
| **Random Euclidean** | Uniform [0,1]², standard for scaling studies | Fixed seeds / Concorde benchmark |

**References**
- Reinelt, G. (1991). *TSPLIB.* ORSA J. Computing 3:376.
- Wilson, G.V. & Pawley, G.S. (1988). *On the stability of the Hopfield–Tank TSP algorithm.* Biological Cybernetics 58:63.

---

## 5. Other Standard Combinatorial Problems

All from Lucas (2014) — explicit QUBO/Ising formulations for all of Karp's 21 NP-complete problems.

| Problem | Ising spins needed | Notes |
|---|---|---|
| **MaxCut** | N | No bias; simplest encoding |
| **Number partitioning** | N | Already in Ising form: Wᵢⱼ = −2nᵢnⱼ |
| **Graph coloring** (k-color) | N·k | Penalty per violated edge + per-vertex color constraint |
| **Vertex cover** | N | Penalty per uncovered edge |
| **k-SAT** | N | Each clause → energy penalty when violated |
| **Clique** | O(N²) | |
| **Hamiltonian cycle** | O(N²) | |
| **Integer LP** | Poly (with slack vars) | |

**Note on number partitioning.** Given numbers n₁,…,nₙ assign sᵢ ∈ {−1,+1}; minimise (Σᵢ nᵢsᵢ)² = Σᵢⱼ nᵢnⱼ sᵢsⱼ. The weight matrix is Wᵢⱼ = −2nᵢnⱼ, no bias. Second simplest embedding after MaxCut — good first demo for Ising mode.

**References**
- Lucas, A. (2014). *Ising formulations of many NP problems.* Frontiers in Physics 2:5.
- Mertens, S. (2004). *Number partitioning as random energy model.* Eur. Phys. J. B 36:557. arXiv:cond-mat/0402010.

---

## 6. Hardware Ising Machines — Landscape

### 6.1 D-Wave Quantum Annealer

- Superconducting qubits, Chimera/Pegasus topology, up to 5,627 qubits.
- Quantum annealing (tunneling, not thermal). Cryogenic (15 mK).
- **Limitation**: Sparse connectivity requires minor embedding for dense problems (blows up qubit count). Performance often comparable to or slower than classical SA on structured problems.

### 6.2 Fujitsu Digital Annealer (DA)

- Custom CMOS ASIC; all-to-all connectivity; up to 8,192 vars (Gen 2), 100,000 (Gen 3).
- Parallel simulated annealing with dynamic escape. Per-spin logic in dedicated digital circuits.
- **Reference**: Aramon, M. et al. (2019). *Physics-Inspired Optimization for QUBO Using a Digital Annealer.* Frontiers in Physics 7:48. arXiv:1806.08815

### 6.3 Toshiba Simulated Bifurcation Machine (SBM)

- Multi-FPGA (Xilinx Alveo) implementation of the Simulated Bifurcation Algorithm (SBA).
- SBA simulates nonlinear oscillators via Hamilton's equations — **deterministic** (no stochastic sampling). All N spins update in parallel per clock cycle.
- 100,000 spins demonstrated; 0.5 ms for large MaxCut instances.
- **Most relevant prior art for our LUT-HNN**: also FPGA-based, also deterministic, but uses ODE integration rather than truth-table lookup.
- **Reference**: Goto, H., Tatsumura, K. & Dixon, A.R. (2019). *Combinatorial optimization by simulated bifurcation.* Science Advances 5:eaav2372. Tatsumura, K. et al. (2019). *FPGA-Based Simulated Bifurcation Machine.* FPGA '19.

### 6.4 FPGA RBM Ising Solver (Patel et al. 2020/2022)

- FPGA-accelerated stochastic p-bits (probabilistic bits): tanh LUT + LFSR + comparator per neuron.
- 10⁷× speedup vs. D-Wave 2000Q on MaxCut; 10⁵× on SK spin glass.
- **Direct connection to our project**: each p-bit uses a tanh activation LUT — analogous to our truth-table neurons. Key difference: stochastic updates require LFSR hardware, our deterministic update does not.
- **Reference**: Patel, S., Canoza, P. & Salahuddin, S. (2022). *Logically synthesized and hardware-accelerated RBMs for combinatorial optimization.* Nature Electronics 5:130. arXiv:2007.13489

### 6.5 Our LUT-HNN vs. the Field

| Feature | Our LUT-HNN | Fujitsu DA | Toshiba SBM | Patel FPGA-RBM |
|---|---|---|---|---|
| Technology | FPGA (LUTs) | ASIC | FPGA | FPGA |
| Update | Deterministic sign (async) | Parallel SA | Deterministic SBA | Stochastic p-bit |
| Spin count | N (small, LUT-limited) | 8K–100K | 100K | Problem-dependent |
| External field / bias | **Not yet** | Yes | Yes | Yes |
| Annealing | None | Yes | No | Implicit (temp.) |
| Logic repr. | Espresso SOP per neuron | Parallel adders | ODE integrators | tanh LUT + LFSR |
| Reconfigurability | Full (re-synthesize W) | Fixed HW | Fixed HW | FPGA reconfig |
| Key differentiator | Boolean minimization of update function via Espresso — no arithmetic at inference | ASIC speed | Deterministic parallel FPGA | Stochastic hardware |

**Observation.** Our approach synthesizes each neuron's update as a Boolean function (truth table → Espresso → SOP → SystemVerilog). This eliminates multiply-accumulate hardware entirely. For optimization mode, W changes per problem instance, requiring re-synthesis — this is fine for a reconfigurable solver at moderate N, and directly analogous to how Patel et al. "logically synthesize" their RBM.

---

## 7. Recommended Next Steps (Code)

Priority order for adding Ising/optimization support to `hopfield_net.py`:

1. **Add bias vector** (`self.b`) — trivial, unblocks all other problems.
2. **Add `from_ising()` and `from_qubo()` classmethods** — standard interface for problem encoding.
3. **Update `energy()`** to include `−bᵀs`.
4. **Track `best_s, best_E`** in `run()` — needed for optimization mode where final ≠ best.
5. **Add `run_annealed()`** — stochastic SA for escaping local minima.
6. **Demo: MaxCut on small graph** — validate Ising mode; compare deterministic vs. annealed solve quality.
7. **Demo: Number partitioning** — simplest bias-free Ising problem after MaxCut.

---

## Key References (Consolidated)

- Hopfield, J.J. (1982). PNAS 79:2554.
- Goles, E. & Olivos, J. (1980). Discrete Mathematics 30:187.
- Hopfield, J.J. & Tank, D.W. (1985). Biological Cybernetics 52:141.
- Lucas, A. (2014). Frontiers in Physics 2:5. https://doi.org/10.3389/fphy.2014.00005
- Aramon, M. et al. (2019). Frontiers in Physics 7:48. arXiv:1806.08815
- Goto, H. et al. (2019). Science Advances 5:eaav2372.
- Patel, S. et al. (2022). Nature Electronics 5:130. arXiv:2007.13489
- Mohseni, N., McMahon, P.L. & Byrnes, T. (2022). Nature Reviews Physics 4:363. arXiv:2204.00276
- Rendl, F., Rinaldi, G. & Wiegele, A. (2010). Math. Programming 121:307. [BiqMac: biqmac.aau.at]
- Böther, M. et al. (2024). arXiv:2406.11897.
- Reinelt, G. (1991). ORSA J. Computing 3:376. [TSPLIB: comopt.ifi.uni-heidelberg.de]
