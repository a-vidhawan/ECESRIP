# CV section — SRIP

Formatted to match the existing CV: bold role line with tech stack, then dense
quantified bullets. Four bullets at ~20 words each, to fit the space available.

---

**UC SAN DIEGO — SRIP (Summer Research Internship Program) | SystemVerilog, Python, Yosys, Icarus Verilog, Espresso**
San Diego, CA
**UNDERGRADUATE RESEARCHER — advised by Prof. Bill Lin**
June, 2026 – Present

- Built a compiler from trained Hopfield weights to synthesizable SystemVerilog (Espresso minimization, graph-colored delay scheduling); verified at N=256, 240/240 vectors recalled.
- Cut per-neuron logic 627–2,918 → 31–54 product terms via operating-region don't-cares, making fan-in 32 synthesizable where full enumeration is impossible.
- Showed clockless settling requires distinct delay values (equal: 0% convergence) and inertial elements (100% vs 1–16%), correcting two patent-draft assumptions.
- Raised storage capacity from α=0.138 to 0.5 (≥95% recall) via margin retraining; audited 18 claims against regenerated source data, retracting two.

---

## Notes on choices

**Why lead with the toolchain.** It is the least arguable thing here — a working
compiler from trained weights to verified RTL is an artifact, not an opinion,
and it is the bullet a hardware group will care about.

**Why the negatives are in bullet 4.** "Retracting 2 and revising 2 of 18" reads
as rigour, not failure. Research groups read it as someone who checks their own
work. Leaving it out would be the weaker choice.

**What was deliberately left out**, because it does not survive scrutiny:
- any claim of area advantage over conventional hardware (marginal on ASIC,
  negative on FPGA)
- any claim that graph-colored scheduling is novel (it is prior art, back to 1984)
- the Ising/MAX-CUT work (real, but it reaches ~99.5% of best cut on small
  instances with no asymptotic claim — too thin to defend in an interview)

**If you need three bullets instead of four**, merge 1 and 2 — the pipeline and
the don't-care result are the same story, and bullets 3 and 4 are the ones that
show judgment.

**Verb tense**: "Present" assumes ongoing. Change to a closed date range if SRIP
has ended.
