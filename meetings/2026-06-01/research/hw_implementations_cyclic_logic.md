# Prior Hardware Implementations of HNNs & Cyclic Combinational Logic
*Research note — consolidated June 27–28, 2026*

---

## The Critical Finding Up Front

**Every existing digital HNN hardware implementation uses a compute-then-threshold architecture:** multiply-accumulate the weighted sum at runtime, then pass through a digital comparator. No implementation precomputes the entire Boolean threshold function as a lookup table and uses direct wire feedback — which is what the LUT-HNN approach does. This is the architectural gap.

The LUT-HNN frames each neuron as a precomputed Boolean truth table: given all N−1 neighbour states as inputs, the LUT output is sign(Σ Wᵢⱼ sⱼ) for every possible input combination, evaluated once at synthesis time and stored. The recurrent connections are literal feedback wires. This is exactly a cyclic combinational circuit in the Riedel-Bruck sense — and no prior work instantiates HNN hardware this way.

---

## The Bruck Connection

**Jehoshua Bruck** appears in both threads:

- **Bruck (1990):** "On the Convergence Properties of the Hopfield Model," *Proc. IEEE* 78(10):1579–1585. Proves convergence for three update modes — serial async (guaranteed), fully parallel sync (may 2-cycle), subset-parallel (intermediate). Adversarially verified 3-0.
- **Riedel & Bruck (2003):** "The Synthesis of Cyclic Combinational Circuits," DAC 2003 (**Best Paper Award**). Proves Boolean circuits with feedback can be combinational (output depends only on current input, not history) if every input has a unique stable output. PDF: https://www.mriedel.ece.umn.edu/wiki/images/7/7a/Riedel_Cyclic_Combinational_Circuits.pdf

The Hopfield network under async update is exactly a cyclic combinational circuit: each neuron computes a Boolean threshold function, feedback paths are the recurrent weights, and Bruck 1990 proves it is well-behaved. No paper unifies these two explicitly — the LUT-HNN is the first concrete hardware realisation of this framing.

---

## (a) Analog VLSI Implementations

### Hopfield & Tank — Analog Circuit for Optimisation (1985)
- **Paper:** J.J. Hopfield, D.W. Tank, "Neural Computation of Decisions in Optimisation Problems," *Biol. Cybernetics* 52:141–152, 1985
- **Hardware:** RC circuits + operational amplifiers (Bell Labs analog prototype)
- **N:** Variable; demonstrated for TSP with N² neurons
- **Activation:** Continuous sigmoid via op-amp gain curve; stable states are binary ±1
- **Update:** Continuous-time async (RC time constants govern settling)

### Tank & Hopfield — Simple Neural Optimisation Networks (1986)
- **Paper:** D.W. Tank, J.J. Hopfield, *IEEE Trans. Circuits Syst.* 33(5):533–541, 1986
- **Hardware:** Analog CMOS (Bell Labs silicon)
- **Activation:** Analog comparator / op-amp saturation as threshold
- **Link:** https://collaborate.princeton.edu/en/publications/simple-neural-optimization-networks-an-ad-converter-signal-decisi

### Graf & Jackel — Bell Labs CMOS Chip (1987)
- **Paper:** H.P. Graf, L.D. Jackel, "VLSI Implementation of a Neural Network Model," *IEEE Computer* 20(3):41–49, 1987
- **Hardware:** Custom CMOS VLSI, 1.5 µm process
- **N:** 256 neurons, fully connected
- **Activation:** CMOS comparator (differential pair) as analog threshold. Neurons are threshold units; weights via resistor ladders
- **Update:** Parallel analog relaxation
- **Link:** https://www.semanticscholar.org/paper/VLSI-implementation-of-a-neural-network-model-Graf-Jackel/3f99128809973b527398b3f779a7c2109c276869

### An Analog VLSI Implementation of Hopfield's Neural Network (1989)
- **Venue:** IEEE Micro (1989); IEEE Xplore doc 42986; ACL: https://dl.acm.org/doi/abs/10.1109/40.42986
- **Hardware:** Custom analog CMOS VLSI
- **N:** 14 neurons, 196 synapses
- **Activation:** Differential-pair op-amp comparator — fully analog continuous-time; NOT digital
- **Link:** https://ieeexplore.ieee.org/document/42986/

### Alspector & Allen — Bell Labs Neuromorphic with On-Chip Learning (1987)
- **Hardware:** CMOS ASIC, Bell Labs; N=32
- **Activation:** Digital threshold logic with stochastic noise injection; first on-chip HNN learning

---

## (b) Digital ASIC / CMOS Implementations

### Jankowski, Lozowski & Zurada — Digital CMOS HNN (1996)
- **Paper:** *IEEE Trans. Neural Networks* 7(6):1491–1496, 1996
- **Hardware:** CMOS digital ASIC; N up to ~64
- **Activation:** Nearest-phase quantiser (multistate extension of sign function); digital threshold unit
- **Update:** Async sequential
- **What's distinct:** Multistate (k-ary) extension — shows threshold function generalises beyond binary

### VLSI Implementation of Associative CAM Based on Hopfield Network (2010)
- **URL:** https://www.researchgate.net/publication/251974387
- **Hardware:** Custom VLSI/ASIC (CMOS); dedicated threshold circuitry per neuron cell
- **Activation:** Digital comparator in each neuron cell — runtime MAC + compare

---

## (c) FPGA Implementations — All Use Runtime MAC + Comparator

Every FPGA implementation found uses the same pattern: compute weighted sum at runtime (multiply-accumulate or shifts), then apply a digital comparator. None precompute the threshold function as a LUT truth table.

| Paper | Year | N | Activation implementation | Link |
|---|---|---|---|---|
| FPGA HNN for CSP (3× speedup) | 1997 | — | Digital comparator | https://ieeexplore.ieee.org/document/708089/ |
| Systolic FPGA HNN | 2001 | — | Sign function in each systolic cell | https://ieeexplore.ieee.org/document/939022 |
| HNN via Simultaneous Perturbation | 2004 | — | Digital; details limited | https://ieeexplore.ieee.org/document/1324147 |
| Pulse Density FPGA HNN | 2007 | — | Pulse integration (mixed) | https://ieeexplore.ieee.org/iel5/4370890/4370891/04371042.pdf |
| Hikawa serial FPGA HNN | 2003–10 | 16–64 | Single MAC unit + comparator, cyclic addressing | https://ieeexplore.ieee.org/document/5650469/ |
| Mansour parallel FPGA HNN | 2011 | ~64 | Multiplierless, O(log N) additions + comparator | https://www.hindawi.com/journals/aans/2011/189368/ |
| Architecture Analysis FPGA HNN | ~2010 | param. | Comparator on accumulated sum; multipliers + adders + ROM | https://www.academia.edu/33481965/ |
| Fault-tolerant FPGA HNN (UCM) | 2016 | small | Comparator + triple modular redundancy | https://eprints.ucm.es/39057/1/Hardware%20implementation.pdf |
| Quantitative FPGA HNN analysis | 2022 | param. | Digital datapath with comparator | https://ieeexplore.ieee.org/document/9733628/ |
| Transcendental nonlinearity FPGA HNN | 2024 | — | PWL approximation via single multiplier + block RAM | https://link.springer.com/article/10.1007/s11071-024-10052-9 |
| Analog/digital circuit simplification | 2023 | — | Simplified digital comparator (ReLU variant) | https://www.sciencedirect.com/science/article/abs/pii/S0960077923006288 |

---

## (d) Cyclic Combinational Logic

### Riedel & Bruck — DAC 2003 (Best Paper)
- **Paper:** "The Synthesis of Cyclic Combinational Circuits," DAC 2003
- **Key claim:** Boolean circuits with feedback can be combinational (memoryless) if they converge to a unique stable output for every input. Cyclic circuits can implement Boolean functions with fewer gates than any acyclic implementation.
- **Not connected to HNNs in the paper.** Framing is purely digital logic synthesis / circuit complexity.
- **PDF:** https://www.mriedel.ece.umn.edu/wiki/images/7/7a/Riedel_Cyclic_Combinational_Circuits.pdf
- **Semantic Scholar:** https://www.semanticscholar.org/paper/Cyclic-combinational-circuits-Bruck-Riedel/ce1d3fa934cd2dd3ff3f089fca039a878747e44f

### Threshold Logic Gate Surveys (VLSI TLG — not Hopfield-specific)
- **Beiu, Quintana, Avedillo (2003):** "VLSI Implementations of Threshold Logic — A Comprehensive Survey," *IEEE Trans. Neural Networks* 14. Covers all CMOS TLG topologies: capacitive (switched-cap, floating-gate), current-mode (pseudo-nMOS), differential pair, wired-inverter. Majority gate as equal-weight special case.
  - https://www.academia.edu/33640168/VLSI_implementations_of_threshold_logic_a_comprehensive_survey
- **Parhami (2020):** "Majority-Logic, Its Applications, and Atomic-Scale Embodiments," *Computers and Electrical Engineering* 83:106562. Covers QCA, NML, molecular, spin-wave — all using majority-3/5 as primitive. Device geometry IS the threshold — no comparator.
  - https://web.ece.ucsb.edu/~parhami/pubs_folder/parh20-cee-maj-logic-appl-embod-final.pdf
- **"Majority Gates vs. General Weighted Threshold Gates" (1994):** Complexity-theoretic separation results. *Computational Complexity*, Springer.
  - https://link.springer.com/article/10.1007/BF01200426

**Critical note:** No paper in the threshold logic / majority gate literature connects to Hopfield network hardware. The intersection — majority/TLG as the neuron model in a recurrent network implemented as a cyclic circuit — is unoccupied.

---

## (e) p-Bit / Probabilistic Hardware

### Camsari, Faria, Sutton, Datta — p-Bits (Physical Review X, 2017)
- **Hardware:** SPICE simulation + proposed MTJ device
- **N:** 8 p-bits (2-bit multiplier demo)
- **Activation:** mᵢ = sgn{rand(−1,1) + tanh(Iᵢ)} — stochastic; deterministic limit recovers Hopfield sign update
- **Link:** https://link.aps.org/doi/10.1103/PhysRevX.7.031014

### Camsari et al. — FPGA p-Bit (arXiv:1712.04166, 2017)
- **Hardware:** FPGA (Intel Cyclone V); tanh implemented as LUT + LFSR noise
- **Update:** Async sequential; integer factorisation and combinatorial optimisation
- **Note:** tanh LUT (not sign LUT) — stochastic, not deterministic

### Hassan et al. — FPGA BSN (DAC 2021, arXiv:2101.00147)
- **Hardware:** FPGA; Binary Stochastic Neurons with LFSR noise
- **Link:** https://arxiv.org/pdf/2101.00147

---

## (f) Memristor-Based (Emerging, 2015–2025)

| Paper | Year | N | Key detail |
|---|---|---|---|
| Nature Comms reconfigurable memristor HNN | 2015 | ~32×32 synapses | Crossbar current sum + CMOS comparator |
| Memristor HNN for recognition/sequencing | 2021 | — | Binary switching memristor + op-amp threshold |
| Threshold learning for memristive HNN | 2024 | — | Binary switching = implicit threshold |
| Hardware-aware HNN with nonlinear memristor | 2025 | ~25 neurons | Superlinear capacity; analog threshold via op-amp |
| Hardware-adaptive superlinear-capacity HNN | 2025 | 64-dim | Capacity scales as N^1.49; Nature Comms |

All memristor implementations use analog weighted sum + external comparator or rely on device physics for thresholding — not digital LUT precomputation.

---

## (g) Other Hardware Paradigms

- **Quantum HNN on IBM Q (2021):** Classical majority vote over many measurement shots used to extract output. https://www.nature.com/articles/s41598-021-02866-z
- **Optical associative memory (US Patent 5,131,055, 1992):** 2-D optical XOR gate + parallel electronic comparator
- **Spin-memristor threshold logic (arXiv:1402.2648, 2014):** Spintronic crossbar + spin-torque switching comparator; 100× energy improvement over CMOS FPGA
- **Nanostructured metallic film reconfigurable TLG (npj Unconventional Computing, 2025):** Device I-V IS the threshold; gate-level only

---

## Summary: What Exists vs. What the LUT-HNN Does

| Approach | Threshold implementation | Runtime arithmetic? | LUT as truth table? | Feedback as wires? |
|---|---|---|---|---|
| Analog VLSI (Graf, Tank) | Op-amp saturation | Yes (analog) | No | Yes (analog feedback) |
| Digital ASIC/FPGA (all) | MAC + comparator | Yes (digital) | No (weights in RAM, not truth table) | No (clocked) |
| p-Bit FPGA (Camsari) | tanh LUT + stochastic | Yes (tanh + LFSR) | Partial (tanh LUT, not threshold) | No |
| Memristor | Device physics or sense amp | Yes (crossbar current) | No | No |
| **LUT-HNN (this project)** | **Precomputed sign truth table** | **No — zero runtime arithmetic** | **Yes — complete 2^N truth table** | **Yes — FPGA routing fabric** |

The LUT-HNN eliminates runtime arithmetic entirely. The threshold function is baked into the LUT at synthesis. The FPGA feedback paths are the recurrent connections. This is the first implementation that is structurally a cyclic combinational circuit in the Riedel-Bruck sense.

---

## Open Question for the Meeting

No paper explicitly frames an HNN as a cyclic combinational circuit and implements it as one. The question for Bill: *Is this framing — HNN as cyclic combinational Boolean circuit, each neuron's truth table precomputed at synthesis — the novelty claim?* Bruck 1990 proves it converges; Riedel-Bruck 2003 provides the theoretical framework; no one has built it.
