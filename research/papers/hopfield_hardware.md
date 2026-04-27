# Hopfield Network Hardware — Paper References

Papers on FPGA and hardware implementations of Hopfield neural networks, directly relevant to the project.

---

## [1] Architecture Analysis of an FPGA-Based Hopfield Network

**Link:** https://ieeexplore.ieee.org/document/ *(skim reference in notes)*

**Relevance:** HIGH — closest prior work to this project.

**Key points:**
- Implements Hopfield network as asynchronous logic circuit on FPGA
- Uses a "weight unit" — NO MULTIPLIERS (uses MUXes instead of multipliers, saves a lot of slices)
- Section 3.3 analyzes constant-weight-value implementation — directly relevant
- Per-neuron update logic block diagram is shown
- **No mention of hazard-free logic or glitch analysis** — this is an open question for our work
- Takeaway: M = 0.14N capacity constraint is a real hardware design constraint (limits fan-in)

**Notes:**
- MUXs instead of MULTs → significant LUT savings
- Good reference for building the update control path
- Does NOT use truth table enumeration — uses arithmetic units

---

## [2] Hardware Implementation of Hopfield-like Neural Networks: Quantitative Analysis of FPGA Approach

**Link:** https://ieeexplore.ieee.org/document/ *(IEEE Conference Publication, IEEE Xplore)*

**Relevance:** HIGH — long paper with useful references and related work.

**Key points:**
- Quantitative resource analysis: Inputs RAM, Weights RAM, Outputs RAM, Control (CNT)
- Memory formulas:
  - `M_inputs = M_outputs = N × b` (b = word length in bits)
  - `M_weights = 2 × N² × b`
  - `M_cnt = ⌈log₂(3 × N)⌉`
  - `M_total = b × (2 × N² + 2 × N) + ⌈log₂(3 × N)⌉`
- Interconnection logic for big networks is where most LEs go — FPGAs are not well-designed for this at scale
- Proposes a new family of reconfigurable circuits with more resources for NN connections and less arithmetic/register resources
- Two interconnected FPGA circuits as a potential solution

**Notes:**
- Highlights the routing/interconnect bottleneck — key motivation for our truth table approach (no routing, just LUTs)
- Weight storage at N² scaling is the memory bottleneck for large N

---

## [3] Hardware Implementation of a Fault-Tolerant Hopfield Neural Network on FPGAs

**Link:** https://www.sciencedirect.com/science/article/

**Relevance:** MEDIUM — covers SEU/SET fault tolerance.

**Key points:**
- Focuses on Single Event Upsets (SEUs) and Single Event Transients (SETs) in VLSI
- SEU: soft error from cosmic rays/alpha particles flipping stored bits in SRAM/flip-flops
- `Qcrit ≈ 2 × VDD × C` — lower supply voltages increase susceptibility
- Investigates fault-tolerant design for HNN on FPGA

**Notes:**
- Are timing issues/glitches in asynchronous Hopfield logic related to SEUs? This connects to our hazard-free logic question.
- Valuable reference for the reliability/metastability angle of asynchronous circuits

---

## Open Questions from These Papers

1. **Hazard-free logic**: None of these papers address hazards in asynchronous Hopfield update loops. If neurons fire asynchronously and their outputs feed back as inputs to other neurons, glitches on intermediate signals could cause incorrect state transitions. Espresso `-dhazard` flag inserts redundant consensus terms to prevent this.

2. **Multiplierless design**: All prior work uses arithmetic units (MUXes or adders). Our approach eliminates arithmetic entirely — the truth table IS the computation.

3. **N scaling**: Prior work hits the N² weight storage wall. Our approach hits the 2^N truth table wall. At large N both approaches require sparse connectivity; ours maps directly to FPGA K-LUTs (K ≤ 6 for most devices).
