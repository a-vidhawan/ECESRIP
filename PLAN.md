# LUT-HNN Research Plan
*Last updated: 2026-07-09*

**Goal:** Implement a Hopfield associative memory on FPGA by enumerating each neuron's update function as a Boolean truth table and synthesizing it into LUT fabric — no multipliers, no adders, pure combinational logic. Three hardware tracks: (A) no pruning, (B) maximum pruning while retaining all stored patterns, (C) gradient-descent + sparsity-aware alternative to pseudo-inverse.

---

## Status at a Glance

| Phase | What | Status |
|---|---|---|
| 1 | Simulation + learning rules | ✅ Done |
| 1 | Truth table generation (dense + sparse) | ✅ Done |
| 1 | Pruning sweep (all 3 rules, post-hoc) | ✅ Done |
| 1 | Degree-targeted comparison (5 methods) | ✅ Done |
| 1 | Recall sweep (large N, no truth tables) | ✅ Done |
| 2 | CSV → PLA conversion (csv_to_pla.py) | ✅ Done |
| 2 | Espresso batch runner (run_espresso.sh) | ✅ Done |
| 2 | Minimized PLA → SystemVerilog (pla_to_sv.py) | ✅ Done |
| 2 | Run Espresso: no-prune case | ⬜ Next |
| 2 | Run Espresso: max-prune case | ⬜ Next |
| 2 | Espresso combined multi-output PLA | ⬜ Next |
| 3 | ABC multi-level synthesis script | ⬜ Next |
| 3 | Gate/LUT count comparison table | ⬜ Next |
| 3 | Timing closure + Vivado synthesis run | ⬜ Later |
| 4 | L1-SVM joint-symmetric LP per neuron | ✅ Done |
| 4 | Perceptron + L1 proximal (ISTA) | ✅ Done |
| 4 | RigL dynamic sparse training | ✅ Done |
| 4 | Degree sweep: GD vs pseudo-inverse | ✅ Done |

---

## Phase 1 — Simulation (Done)

### What exists

| File | Purpose |
|---|---|
| `sim/python/hopfield_net.py` | Core HNN: Hebbian, Storkey, Pseudoinverse, async-cyclic update |
| `phase1/verify_binary_encoding.py` | Proves {0,1} ↔ {−1,+1} equivalence (100/100 A==B, A==D) |
| `phase1/hnn_to_truth_table.py` | Generates dense + sparse truth tables → JSON + CSV |
| `phase1/pruning.py` | All pruning methods: magnitude, L1-Storkey, masked retrain (Storkey + PI) |
| `phase1/run_pruning_sweep.py` | s sweep for all 3 rules, records fixed-pts + recall |
| `phase1/run_recall_sweep.py` | M × s × noise sweep, pure simulation (handles large N) |
| `phase1/run_degree_comparison.py` | 5 methods at matched target degree → best method ID |
| `phase1/results/` | CSV outputs from all sweeps |

### Key findings

- **Pseudo-inverse is most pruning-tolerant**: holds all fixed points through s=0.75 (deg ~5.6 for N=16, M=4)
- **Best pruning method**: `storkey_retrain` (prune mask → re-run Storkey on mask) — at deg 12, N=32: η=15% recall jumps from 0.50 → 0.76 vs post-hoc
- **Pseudo-inverse masked retrain** is counterintuitively worse at low degree: LS minimizes squared error but does not guarantee strict sign fixed-point condition
- **L1 Storkey** has a sharp transition, can't target specific degrees — ruled out for hardware
- **Compression at s=0.75**: 341× sparse vs dense LUT entries (N=16)

---

## Phase 2 — Logic Minimization

### What exists

| File | Purpose |
|---|---|
| `phase2/csv_to_pla.py` | Truth table JSON → per-neuron `.pla` files with physical index labels |
| `phase2/run_espresso.sh` | Batch-runs Espresso, reports term count before/after |
| `phase2/pla_to_sv.py` | Minimized PLA → SOP `assign` statements + optional FSM wrapper |
| `phase2/pla/storkey_s0p75/` | Pre-generated PLA files for N=16, 4 patterns, s=0.75 (341× compression) |
| `phase2/README.md` | Pipeline overview + quick start |

### Next steps

#### A. No-pruning case (dense pseudo-inverse, all patterns guaranteed)

```bash
# Generate truth tables with pseudo-inverse, no pruning
python phase1/hnn_to_truth_table.py \
  --rule pseudoinverse --s 0.0 \
  --N 16 --M 4 \
  --out phase1/results/truth_tables/pseudo_s0p00/

# Convert to PLA
python phase2/csv_to_pla.py \
  --input phase1/results/truth_tables/pseudo_s0p00/ \
  --out phase2/pla/pseudo_s0p00/

# Run Espresso (separate per-neuron)
bash phase2/run_espresso.sh phase2/pla/pseudo_s0p00/ phase2/pla_min/pseudo_s0p00/

# Generate SV
python phase2/pla_to_sv.py \
  --input phase2/pla_min/pseudo_s0p00/ \
  --out phase2/rtl/pseudo_dense.sv --N 16 --with-fsm
```

- ⬜ Run and record: terms before/after Espresso, literal count in SV

#### B. Max-pruning case (pseudo-inverse, prune until 1 pattern would be lost)

Use `prune_pseudoinverse(s=..., max_iter=10)` from `phase1/pruning.py` — it backs off s until all patterns are preserved. The resulting W is the most sparse weight matrix that still stores all M patterns exactly.

```bash
# Find max-pruning threshold for pseudo-inverse
python phase1/hnn_to_truth_table.py \
  --rule pseudoinverse --s 0.75 \   # or sweep to find boundary
  --N 16 --M 4 \
  --out phase1/results/truth_tables/pseudo_s0p75/

python phase2/csv_to_pla.py \
  --input phase1/results/truth_tables/pseudo_s0p75/ \
  --out phase2/pla/pseudo_s0p75/

bash phase2/run_espresso.sh phase2/pla/pseudo_s0p75/ phase2/pla_min/pseudo_s0p75/

python phase2/pla_to_sv.py \
  --input phase2/pla_min/pseudo_s0p75/ \
  --out phase2/rtl/pseudo_sparse.sv --N 16 --with-fsm
```

- ⬜ Run and record: actual degree achieved, LUT entry count, Espresso term reduction

#### C. Espresso shared/combined outputs

For small N (≤ 16), run Espresso on all N neurons together as one PLA with N outputs. This allows Espresso to find shared product terms across neurons — a single AND gate can feed multiple OR gates.

```bash
# Generate combined PLA (all N outputs in one file)
python phase2/csv_to_pla.py \
  --input phase1/results/truth_tables/pseudo_s0p75/ \
  --out phase2/pla/combined/ --combined

# Run Espresso on combined PLA
espresso -Dso_both phase2/pla/combined/combined.pla > phase2/pla_min/combined/combined.pla

# Parse multi-output minimized PLA → SV (pla_to_sv.py already handles multi-output)
```

- ⬜ Compare: separate vs combined — shared product term reduction, gate count
- Note: Espresso `-Dso_both` does exact two-level minimization sharing across outputs

---

## Phase 3 — Multi-Level Logic Synthesis

### Why

Espresso produces 2-level SOP (sum-of-products): one AND layer + one OR gate per neuron. This maps cleanly to FPGAs (each product term = one LUT config) but wastes gates on ASIC, and for large N even FPGA resource usage is high.

Multi-level synthesis (ABC or Yosys) converts the SOP into a deeper tree with fewer literals by factoring shared sub-expressions. Example: `(a&b&c) | (a&b&d)` → `(a&b)&(c|d)`.

### Tool: ABC (Berkeley Logic Synthesis)

```bash
# Install
sudo apt-get install abc   # or build from source: github.com/berkeley-abc/abc

# Quality optimization (resyn2 is ABC's built-in alias for this sequence)
abc -c "read_pla <file.pla>; strash; balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance; print_stats; write_verilog <out.v>"

# Map to FPGA k=6 LUTs
abc -c "read_pla <file.pla>; strash; resyn2; if -K 6; print_stats"
```

Typical reduction over Espresso SOP: 20–40% fewer AIG nodes via `resyn2`; after LUT mapping, 15–35% fewer 6-LUTs for N=10–16 neurons. Larger gains when multiple neurons share common sub-expressions that AIG rewriting can extract.

**Important caveat for async path:** ABC's multi-level rewrites do **not** preserve the hazard-free property of Espresso's `-Dhazard` SOP. For Phase 2 (async combinational feedback), stay with Espresso SOP only. ABC is for the clocked synthesis path.

### Plan

- ⬜ Write `phase2/run_abc.sh`: batch-runs ABC on all `pla_min/*.pla`, outputs Verilog + stats
- ⬜ Compare gate counts: Espresso SOP vs ABC-optimized for both dense and sparse cases
- ⬜ Evaluate: Yosys as alternative (`synth -flatten; abc -g gates; stat`)
- ⬜ Record results in a table:

| Case | N | M | Espresso terms | ABC gates | LUT-6 count | Freq est |
|---|---|---|---|---|---|---|
| pseudo dense | 16 | 4 | ? | ? | ? | ? |
| pseudo sparse (s=0.75) | 16 | 4 | ? | ? | ? | ? |
| combined | 16 | 4 | ? | ? | ? | ? |

### Output artifacts

- `phase2/rtl/pseudo_dense.sv` — no-pruning SV (pla_to_sv.py output)
- `phase2/rtl/pseudo_sparse.sv` — max-pruning SV
- `phase2/rtl/pseudo_dense_abc.v` — ABC-optimized Verilog
- `phase2/rtl/pseudo_sparse_abc.v` — ABC-optimized Verilog
- `phase2/run_abc.sh` — batch synthesis script

---

## Phase 4 — Gradient Descent + Sparsity-Aware Training (Alternative to Pseudo-Inverse)

### Why

Pseudo-inverse finds minimum-norm weights satisfying all patterns exactly, but: (1) requires O(N³) matrix inversion — offline only; (2) no natural mechanism for targeted sparsity. A gradient-descent approach can directly optimize a sparsity-regularized loss.

### Best candidate A: L1-SVM per-neuron LP (principled, exact degree control)

For each neuron i, solve:
```
minimize    Σ_j |w_ij|
subject to  ξᵢ^μ (wᵢ · ξ^μ) ≥ γ    for all μ = 1 … M
```
This is a **linear program** — guaranteed globally optimal sparse weights. The L1 objective directly minimizes non-zero connections per neuron (principled degree control). Margin γ trades noise robustness vs sparsity; γ = 1 is a safe default for bipolar patterns. Scales as N independent LPs of size M × N — feasible up to N~100, M~50 with scipy/GLPK. Post-solve symmetrize: W = (W + Wᵀ)/2.

Known in literature: Bradley & Mangasarian (ICML 1998), Hillar & Sohl-Dickstein (arXiv:1204.2916). Connection to Gardner's optimal storage (1988); capacity approaches 0.64N when γ is small.

### Best candidate B: Perceptron / 3-threshold rule with L1 proximal (iterative)

```
L(W) = Σ_μ Σᵢ max(0, γ − ξᵢ^μ (Wᵢ · ξ^μ)) + λ||W||₁
```
Gradient for violated margin: ∂L/∂W_{ij} = −Σ_{μ: violated} ξᵢ^μ ξⱼ^μ + λ sign(W_{ij})

Perceptron convergence theorem guarantees this halts in finite steps when a solution exists. Converges to the Gardner bound ~0.64N capacity. The 3-threshold extension (Alemi et al. 2015, arXiv:1508.00429) uses three thresholds θ₁ < θ₂ < θ₃ to push toward maximum-margin solutions. Gradient of margin loss is cheap to evaluate even for zero-weight entries, enabling RigL-style mask adaptation.

### Dynamic sparse option: RigL-style mask adaptation

After each gradient step: prune fraction f of smallest-|w_ij| weights, regrow at positions where |∂L/∂w_ij| is largest among currently-zero entries. Maintains exact per-neuron degree budget throughout training. Symmetry constraint: prune/regrow pairs (i,j) and (j,i) jointly. Better than SET (random regrowth) because gradient guidance finds problem-adaptive connectivity. (Evci et al., ICML 2020)

### Implemented — `phase1/train_gd.py`

| Function | What it does |
|---|---|
| `train_l1svm(patterns, gamma, degree)` | Joint symmetric LP — minimum-degree exact storage |
| `train_perceptron_l1(patterns, lam, gamma, lr, max_epochs)` | ISTA hinge-margin + L1 |
| `train_rigl(patterns, target_degree, gamma, lam, lr, max_epochs)` | RigL dynamic sparse mask |
| `run_comparison(patterns, target_degrees, noise_fracs)` | All methods head-to-head |

### Key findings (N=32, M=8, α=0.25)

| Method | Actual deg | fp | η=0% | η=15% | η=30% | Notes |
|---|---|---|---|---|---|---|
| pseudo_posthoc (d≈12) | 12 | 8/8 | 1.00 | 0.71 | 0.19 | Reference |
| **l1svm** | **9** | **8/8** | **1.00** | **0.36** | **0.04** | Minimum degree, poor noise |
| perceptron_l1 (d≈12) | 11 | 8/8 | 1.00 | 0.59 | 0.14 | Needs higher λ for sparsity |
| rigl (target d=8) | ~20 | 8/8 | 1.00 | 0.76 | 0.26 | Best recall, overshoots degree |

**L1-SVM key insight**: finds the *theoretically minimum degree* to store M patterns exactly. At α=0.25, that's deg~9 vs pseudo-inverse's deg~31 — saves 2^9=512 vs 2^31 LUT entries. However noise robustness is lower (recall at η=15%: 0.36 vs 0.71). This is the fundamental sparsity-recall tradeoff.

**Perceptron-L1 + RigL**: at matched degree, perceptron-L1 with tuned λ matches pseudo-inverse recall; RigL with gradient-guided regrowth exceeds both at higher degree budget.

- ⬜ Tune perceptron-L1 λ sweep to find the sparsity-recall Pareto front
- ⬜ Fix RigL degree targeting (symmetric mask init overshoots; use Erdős–Rényi init)
- ⬜ Key references: Gardner (1988), Alemi et al. (arXiv:1508.00429), Hillar & Sohl-Dickstein (arXiv:1204.2916), Evci et al. (ICML 2020 — RigL)

### Secondary option: Minimum Probability Flow (MPF)

Loss = Σ_{s∈data} Σ_{s'∈1-bit-flip(s)} exp(½(E(s,W) − E(s',W))). Analytic gradient, no partition function, ≥ 1 pattern/neuron capacity (Hillar & Sohl-Dickstein 2012). Implement as `phase1/train_mpf.py` if L1-SVM capacity is insufficient at high M/N.

### Server note

UCSD server for Espresso: `ssh avidhawan@lambda-alpha.ucsd.edu` (pw = username). Espresso binary at `~/espresso`.
Run Espresso on server with: `bash phase2/run_espresso.sh <pla_in> <pla_out> "" ~/espresso`

---

## Open Questions

1. **Shared outputs gain**: How many product terms can Espresso share across the N neuron outputs in the combined PLA? Expected: large gain for similar neurons (symmetric W).
2. **ABC gain over Espresso**: For the specific SOP structure Hopfield produces (many terms with repeated literals), does ABC's `rewrite` pass find significant factoring opportunities?
3. **GD vs pseudo-inverse at matched degree**: Does the perceptron rule with L1 achieve better noise robustness than pseudo-inverse at the same mean degree? Hypothesis: yes, because GD can directly maximize the margin γ while pseudo-inverse minimizes ||W||.
4. **Max-prune boundary**: At what s does pseudo-inverse lose its first fixed point as a function of α = M/N? The iterative verify-and-prune in `pruning.py` finds this per instance — we should sweep α.
5. **Multi-level vs 2-level on FPGA**: For Xilinx 6-input LUTs, SOP product terms of length ≤ 6 fit in a single LUT anyway. Does multi-level help or hurt FPGA synthesis specifically?

---

## File Map

```
ECESRIP/
├── PLAN.md                          ← this file
├── sim/python/hopfield_net.py       ← core HNN simulation
├── phase1/
│   ├── hnn_to_truth_table.py        ← truth table generator
│   ├── pruning.py                   ← all pruning methods (5 total)
│   ├── run_degree_comparison.py     ← 5-method degree comparison
│   ├── run_recall_sweep.py          ← M×s×noise recall sweep
│   └── results/                     ← CSVs from all sweeps
├── phase2/
│   ├── csv_to_pla.py               ← truth tables → PLA
│   ├── run_espresso.sh             ← batch Espresso runner
│   ├── pla_to_sv.py                ← minimized PLA → SystemVerilog
│   ├── pla/                        ← raw PLA files (input to Espresso)
│   ├── pla_min/                    ← minimized PLA files (Espresso output)
│   └── rtl/                        ← generated SV (pla_to_sv.py output)
├── research/
│   ├── notes/research_plan.md      ← original Phases 1-3 plan
│   └── notes/                      ← theory, update-order analysis
└── meetings/2026-06-01/research/
    ├── sgd_adjoint_methods.md      ← CHL, EP, MPF, perceptron GD, STE
    └── hw_implementations_cyclic_logic.md
```
