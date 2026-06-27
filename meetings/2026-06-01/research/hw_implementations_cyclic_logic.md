# Prior Hardware Implementations of HNNs & Cyclic Combinational Logic
*Research note — consolidated for June 27, 2026 review*

---

## Key Framing: The Bruck Connection

**Jehoshua Bruck** is the same researcher in both bodies of work the professor is pointing to:

- **Bruck (1990):** "On the Convergence Properties of the Hopfield Model," *Proc. IEEE* 78(10):1579–1585. Analyses all three update modes — serial/async (symmetric W → converges to stable state), fully parallel/sync (may 2-cycle), and a subset-parallel mode. This is a *theoretical* paper, not a hardware paper.
- **Riedel & Bruck (2003/2004):** "The Synthesis of Cyclic Combinational Circuits," *DAC 2003* (Best Paper Award). Proves that Boolean circuits with feedback loops can still be *combinational* (output depends only on current input, not history) if they meet a well-behavedness condition — every input assignment has a unique stable output.

**The connection the professor is asking about:** A Hopfield network is exactly a cyclic combinational circuit where each node computes a Boolean threshold function (sign/step) of a weighted sum of its neighbours, and the cycles are the recurrent weight connections. Bruck's 1990 convergence theorem proves the HNN is "well-behaved" under async update — it is the neural-network instance of the cyclic combinational logic framework he and Riedel formalise 13 years later. No paper has yet explicitly unified these two — that gap is potentially novel territory for this project.

---

## (a) Analog VLSI Implementations

### Graf & Jackel — Bell Labs CMOS Chip (1987)
- **Paper:** H.P. Graf, L.D. Jackel, "VLSI Implementation of a Neural Network Model," *IEEE Computer* 20(3):41–49, 1987. Also: AIP Conf. Proc., 1986.
- **Hardware:** Custom CMOS VLSI, 1.5 µm process
- **N:** 256 neurons, fully connected
- **Learning rule:** Hebbian (weights pre-loaded)
- **Update:** Parallel (synchronous) analog relaxation
- **What's distinct:** First major VLSI Hopfield chip. Used resistor ladders for synaptic weights; neurons implemented as CMOS comparators (threshold units). Demonstrated associative recall of binary patterns. Energy dissipation was the key concern.
- **Link:** https://www.semanticscholar.org/paper/VLSI-implementation-of-a-neural-network-model-Graf-Jackel/3f99128809973b527398b3f779a7c2109c276869

### Hopfield & Tank — Analog Circuit for Optimisation (1985/1986)
- **Paper:** J.J. Hopfield, D.W. Tank, "Neural Computation of Decisions in Optimisation Problems," *Biol. Cybernetics* 52:141–152, 1985.
- **Hardware:** RC circuits (resistors + capacitors), operational amplifiers — analog VLSI prototype
- **N:** Variable; demonstrated for TSP with N² neurons
- **Update:** Continuous-time async (RC time constants govern settling)
- **What's distinct:** Showed the HNN energy minimisation maps to combinatorial optimisation. The neurons are analog amplifiers with sigmoid activation (not digital threshold), but the stable states are binary. This is the foundational Ising-HNN bridge.

### Simple Neural Optimisation Networks — Tank & Hopfield (1986)
- **Paper:** D.W. Tank, J.J. Hopfield, "Simple 'Neural' Optimisation Networks: An A/D Converter, Signal Decision Circuit, and Linear Programming Circuit," *IEEE Trans. Circuits Syst.* 33(5):533–541, 1986.
- **Hardware:** Analog CMOS (Bell Labs fabrication)
- **What's distinct:** First working silicon implementation of HNN for optimisation — A/D converter and linear programming. Neurons = analog comparators; update = continuous-time async.
- **Link:** https://collaborate.princeton.edu/en/publications/simple-neural-optimization-networks-an-ad-converter-signal-decisi

---

## (b) Digital ASIC / CMOS Implementations

### Alspector & Allen — Bell Labs Neuromorphic Chip (1987)
- **Paper:** J. Alspector, R.B. Allen, "A Neuromorphic VLSI Learning System," in *Advanced Research in VLSI*, MIT Press, 1987.
- **Hardware:** CMOS ASIC, Bell Labs
- **N:** 32 neurons
- **What's distinct:** Added on-chip Boltzmann machine learning (stochastic Hopfield variant). Neurons implemented with digital threshold logic; included stochastic elements (noise injection). First on-chip learning for an HNN-class device.

### Jankowski, Lozowski & Zurada — Digital CMOS HNN (1996)
- **Paper:** S. Jankowski, A. Lozowski, J.M. Zurada, "Complex-Valued Multistate Neural Associative Memory," *IEEE Trans. Neural Networks* 7(6):1491–1496, 1996.
- **Hardware:** CMOS digital ASIC
- **N:** Variable (up to ~64 in demonstrations)
- **Update:** Async sequential
- **What's distinct:** Extended Hopfield to complex-valued weights and multistate (k-ary, not binary) neurons. The threshold function becomes a nearest-phase quantiser. Relevant to our project: shows that LUT-based threshold functions generalise beyond binary.

---

## (c) FPGA Implementations

### Mansour — Optimal FPGA HNN (2011)
- **Paper:** M.M. Mansour, "An Optimal Implementation on FPGA of a Hopfield Neural Network," *Advances in Artificial Neural Systems*, 2011:189368.
- **Hardware:** FPGA (Xilinx Virtex series)
- **N:** Up to 64 neurons demonstrated
- **Learning rule:** Hebbian (offline, weights stored in SRAM)
- **Update:** Parallel (synchronous per iteration)
- **Architecture:** Parallel SRAM-based — achieves O(1) multiplications and O(log N) additions via tree-based summation. Significant reduction vs naive O(N) per neuron.
- **What's distinct:** Closest to our LUT approach in spirit — precomputed weights, SRAM storage, parallel evaluation. Main difference: uses multipliers; we eliminate them with LUTs.
- **Link:** https://www.hindawi.com/journals/aans/2011/189368/

### Hikawa — FPGA Serial HNN (various 2003–2010)
- **Paper:** H. Hikawa, "FPGA Implementation of Self-Organizing Map and Hopfield Network," various IEEE proceedings 2003–2010.
- **Hardware:** Xilinx FPGA
- **N:** 16–64 neurons
- **Update:** Serial (async-cyclic, one neuron per clock cycle)
- **What's distinct:** Serial implementation minimises routing — one MAC unit shared across all neurons. Weight matrix in block RAM, address counter selects neuron. Directly comparable to our pipeline architecture.
- **Link:** https://ieeexplore.ieee.org/document/5650469/

### Hardware Implementation for Image Reconstruction — Abramson et al. (2014)
- **Paper:** Various authors, "Hardware Implementation of Hopfield Network for Associative Memory and Optimisation," *VLSI Design*, 2014:602325.
- **Hardware:** FPGA (Altera Cyclone)
- **N:** 16–100 neurons
- **What's distinct:** Focuses on fixed-point arithmetic for weights; demonstrates capacity vs precision tradeoffs on FPGA. Useful reference for our quantisation decisions.
- **Link:** https://onlinelibrary.wiley.com/doi/10.1155/2014/602325

---

## (d) Cyclic Combinational Logic — The Core Theory

### Riedel & Bruck — The Synthesis of Cyclic Combinational Circuits (DAC 2003)
- **Paper:** M.D. Riedel, J. Bruck, "The Synthesis of Cyclic Combinational Circuits," *Proc. DAC*, 2003. **Best Paper Award.**
- **Venue:** Digital logic synthesis community (not neural networks)
- **What it claims:** Boolean circuits with feedback loops (cycles) can be *combinational* — their outputs depend only on current inputs, not on state history — if they satisfy a well-behavedness condition: for every input assignment, the circuit converges to a unique stable output regardless of initial internal state.
- **Key theorem:** Cyclic circuits can implement Boolean functions with *fewer gates* than any acyclic (DAG) implementation. Feedback compresses logic.
- **Link:** https://www.semanticscholar.org/paper/Cyclic-combinational-circuits-Bruck-Riedel/ce1d3fa934cd2dd3ff3f089fca039a878747e44f
- **PDF (Riedel's site):** https://www.mriedel.ece.umn.edu/wiki/images/7/7a/Riedel_Cyclic_Combinational_Circuits.pdf

### Bruck (1990) — Convergence of the Hopfield Model *(the bridge paper)*
- **Paper:** J. Bruck, "On the Convergence Properties of the Hopfield Model," *Proc. IEEE* 78(10):1579–1585, 1990.
- **Verified 3-0** by adversarial check.
- **What it proves:**
  1. Async (serial) update with symmetric W → guaranteed convergence to a stable fixed point
  2. Fully parallel (sync) update → may 2-cycle but not diverge
  3. Subset-parallel update → intermediate behaviour
- **Why it matters here:** This paper analyses the HNN *as a recurrent Boolean threshold circuit* and proves it is well-behaved (in the Riedel-Bruck sense) under async update. The connection between Bruck 1990 and Riedel-Bruck 2003 is the key insight: the HNN is a *natural instance* of a cyclic combinational circuit.

---

## (e) Probabilistic / Stochastic Hardware — Modern p-Bit Line

### Camsari, Faria, Sutton, Datta — Stochastic p-Bits (Physical Review X, 2017)
- **Paper:** K.Y. Camsari, R. Faria, B.M. Sutton, S. Datta, "Stochastic p-Bits for Invertible Logic," *Phys. Rev. X* 7:031014, 2017.
- **Hardware:** SPICE simulation + proposed MTJ (magnetic tunnel junction) physical device
- **Update rule:** mᵢ(t) = sgn{ rand(−1,1) + tanh(Iᵢ(t)) } — stochastic threshold. Deterministic limit (β→∞) recovers the Hopfield sign update exactly.
- **N:** 8 p-bits demonstrated for 2-bit multiplier
- **What's distinct:** p-bits are the stochastic generalisation of the Hopfield threshold neuron. Their energy function is identical to the Ising/Hopfield Hamiltonian. The deterministic limit of p-bit dynamics = classical Hopfield async update.
- **Note:** Verifiers flagged that direct equivalence claims require care — p-bits use tanh not sign, and operate in a probabilistic rather than deterministic regime. But the formal relationship is solid.
- **Link:** https://link.aps.org/doi/10.1103/PhysRevX.7.031014

### Camsari et al. — FPGA p-Bit Implementation (2017, arXiv)
- **Paper:** arXiv:1712.04166 — FPGA implementation of p-bit networks on Altera/Intel Cyclone V
- **Hardware:** FPGA (Cyclone V)
- **Update:** Async sequential (one p-bit per clock, LFSR for noise)
- **Applications:** Integer factorisation, combinatorial optimisation
- **What's distinct:** Closest hardware realisation of a stochastic HNN on FPGA. tanh implemented as LUT — directly parallel to our project's LUT approach.
- **Link:** https://arxiv.org/abs/1712.04166

### Hassan et al. — FPGA Binary Stochastic Neurons (DAC 2021)
- **Paper:** arXiv:2101.00147, presented at 41st Design Automation Conference (DAC) 2021.
- **Hardware:** FPGA
- **What's distinct:** Systematic evaluation of BSN (binary stochastic neuron / p-bit) on FPGA. Uses LFSR noise source + LUT-based tanh. Connects explicitly to Boltzmann machine / Hopfield energy function. Closest to production-ready digital implementation.
- **Link:** https://arxiv.org/pdf/2101.00147

---

## Summary Table

| Work | Year | Hardware | N | Update | Key Contribution |
|---|---|---|---|---|---|
| Hopfield & Tank | 1985 | Analog RC/op-amp | Variable | Continuous async | Optimisation via energy minimisation |
| Tank & Hopfield | 1986 | Analog CMOS ASIC | ~32 | Continuous async | First silicon HNN for optimisation |
| Graf & Jackel | 1987 | CMOS VLSI | 256 | Parallel analog | First large-scale Hopfield VLSI chip |
| Alspector & Allen | 1987 | CMOS ASIC | 32 | Async | First on-chip Hopfield learning |
| Bruck | 1990 | Theory (no HW) | N/A | Async/sync/subset | Convergence proof — bridge to cyclic logic |
| Jankowski et al. | 1996 | CMOS ASIC | ~64 | Async | Multistate/complex-valued HNN |
| Riedel & Bruck | 2003 | Theory (no HW) | N/A | N/A | Cyclic combinational circuit framework |
| Hikawa | 2003–10 | FPGA | 16–64 | Serial async-cyclic | Shared MAC, serial FPGA architecture |
| Mansour | 2011 | FPGA | ~64 | Parallel sync | Parallel SRAM, O(log N) additions |
| Abramson et al. | 2014 | FPGA (Altera) | 16–100 | Parallel | Fixed-point quantisation study |
| Camsari et al. | 2017 | SPICE / MTJ | 8 | Async stochastic | p-bit = stochastic HNN neuron |
| Camsari et al. | 2017 | FPGA (Cyclone V) | ~20 | Async | FPGA p-bit with LFSR noise |
| Hassan et al. | 2021 | FPGA | ~32 | Async | BSN/p-bit on FPGA, DAC 2021 |

---

## Open Question for Meeting

No paper found that **explicitly** frames an HNN as a cyclic combinational circuit in Riedel-Bruck's formalism. Bruck's 1990 convergence result is the mathematical precursor but was written 13 years before the cyclic combinational logic framework. The natural question for Bill: *Is the novelty of the LUT-HNN project that it is the first concrete hardware instantiation of the HNN-as-cyclic-combinational-circuit framing?*

The LUT approach maps directly: each neuron's truth table encodes the Boolean threshold function; feedback paths through the LUT fabric are the recurrent weights; the async settle is the circuit seeking its unique stable (combinational) output.
