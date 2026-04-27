# LUT-Based Neural Network Approaches — Paper References

Papers on using Look-Up Tables (LUTs) for neural network inference. These are the direct ancestors of our approach.

**Core idea shared with our project:** Since neuron outputs are Boolean (binary/bipolar), the neuron's computation can be expressed as a truth table enumerated over all possible input combinations, then synthesized into FPGA LUTs.

**Key gap in the literature:** None of these papers have applied this to a Hopfield/RNN (recurrent neural network). The feedback aspect — where neuron outputs loop back as inputs — makes hazard-free asynchronous design non-trivial. **This is our novel contribution.**

---

## [1] NullaNet: Training Deep Neural Networks for Reduced-Memory-Access Inference

**ArXiv:** [1807.08716](https://arxiv.org/abs/1807.08716)

**Relevance:** FOUNDATIONAL — first to do neuron update logic → truth table enumeration.

**Key points:**
- Models neuron computation as McCulloch-Pitts Boolean function
- Stores the Boolean function directly in LUTs (no arithmetic at inference)
- Introduces **Incompletely Specified Functions (ISFs)**: ON-set (output=1), OFF-set (output=0), Don't-Care set (output undefined — used to simplify logic)
- Binary quantization only
- Scalability constrained by number of neuron inputs (truth table grows as 2^N)
- Provides approximate inference — ISF is lossy for unseen input combinations

**Connection to our work:**
- NullaNet's McCulloch-Pitts model IS the Hopfield update rule: `s_i = sign(Σ w_ij · s_j)`
- We need binary (we already have it) — no approximation needed since we enumerate all inputs exactly
- We use a fully-specified truth table (no ISF), which is exact

---

## [2] LogicNets: Co-Designed Neural Networks and Circuits for Extreme-Throughput Applications

**ArXiv:** [2004.03021](https://arxiv.org/abs/2004.03021)

**Relevance:** HIGH — systematic neuron-as-truth-table toolflow (L-LUT → P-LUT).

**Key points:**
- Generates Logical LUTs (L-LUTs) by enumerating all function values from quantized inputs/outputs
- Maps L-LUTs to Physical LUTs (P-LUTs) via logic synthesis tools — **zero accuracy loss during mapping**
- Uses **high sparse connectivity** (fan-in F ≪ N) based on expander graph theory to keep table size at 2^(βF) where β is bit width
- Supports multi-bit quantization (not just binary)
- Table size = `2^(βF)` — key formula for our feasibility analysis

**Connection to our work:**
- Our approach is exactly LogicNets' L-LUT enumeration, applied to a Hopfield network
- For Hopfield: β=1 (bipolar maps to binary), so table size = 2^F where F is the fan-in (= N for fully connected, or F strongest weights for sparse)
- LogicNets uses expander graphs for random sparse connectivity; we could use the F strongest weights per neuron (more principled for Hopfield)

---

## [3] NeuraLUT: Hiding Neural Network Density in Boolean Synthesizable Functions

**ArXiv:** [2403.00849](https://arxiv.org/abs/2403.00849)

**Relevance:** MEDIUM-HIGH — extends enumeration beyond single neurons (sub-network-as-LUT).

**Key points:**
- Maps entire sub-networks (MLPs) to a single L-LUT rather than one neuron per LUT
- Enhances expressive capacity, reduces circuit-level model layers
- Internal MLP computations done at floating-point precision (not constrained by quantization)
- Reduces LUT resource consumption and latency compared to per-neuron approach

**Connection to our work:**
- For Hopfield, sub-network-as-LUT would mean grouping several neurons into a joint truth table — interesting for future work if individual neuron tables are too sparse to be efficient

---

## [4] Weightless Neural Networks for Efficient Edge Inference

**ArXiv:** [2203.01479](https://arxiv.org/abs/2203.01479)

**Relevance:** MEDIUM — RAM as pure lookup architecture (no weights, no arithmetic).

**Key points:**
- Weightless/RAM-based neuron: neuron = addressed RAM, no multiply-accumulate
- Different philosophy: learned lookup table stored in RAM cells
- Very area-efficient for edge devices

**Connection to our work:**
- Our BRAM-based fallback for large N (N>14) is similar — store the truth table in BRAM, address it with the neuron input vector

---

## [5] A Survey on LUT-Based Deep Neural Networks Implemented in FPGAs

**ArXiv:** [2506.07367](https://arxiv.org/abs/2506.07367)

**Relevance:** HIGH — comprehensive review of the full NN→LUT space.

**Key points:**
- Reviews LUTNet, NullaNet, LogicNets, PolyLUT, PolyLUT-Add, NeuraLUT, AmigoLUT, CompressedLUT, ReducedLUT, DiffLogicNet, DWN, TreeLUT (12 architectures)
- LUTNet: replaces XNOR computations with K-LUT implementations of arbitrary K-input Boolean functions
- PolyLUT: replaces linear transformations with multivariate polynomial functions of degree D; table size stays 2^(βF) because the polynomial feature expansion is absorbed into the enumeration, not the LUT size
- AmigoLUT: ensemble of smaller LUT-based DNNs — linear scaling of LUT resources with number of models
- **Key note from survey:** "Nothing has Hopfield/RNN enumerated as Truth Tables yet — the feedback aspect of the recurrent architecture is what's tricky. Hazard issues with this?"

**This survey confirms the novelty of our approach.**

---

## Summary: How Our Approach Relates

| Architecture | Type | Fan-in | Quantization | Exact? | Feedback? |
|---|---|---|---|---|---|
| NullaNet | Neuron→LUT | N (full) | Binary | Approximate (ISF) | No |
| LogicNets | Neuron→LUT | F ≪ N (sparse) | Multi-bit | Exact | No |
| NeuraLUT | Subnet→LUT | F inputs | Float internal | Exact | No |
| **Our approach** | **Neuron→LUT** | **N (or F sparse)** | **Binary (bipolar)** | **Exact** | **YES — Hopfield** |

The feedback column is what makes this novel. Every prior approach is feedforward. Ours is recurrent with asynchronous combinational feedback — requiring hazard-free Boolean logic.
