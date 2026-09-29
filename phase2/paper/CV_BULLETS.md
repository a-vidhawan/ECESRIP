# CV section — SRIP

Formatted to match the existing CV: bold role line with tech stack, then dense
quantified bullets. Four bullets, consistent with the longer project entries.

---

**UC SAN DIEGO — SRIP (Summer Research Internship Program) | SystemVerilog, Python, Yosys, Icarus Verilog, Espresso**
San Diego, CA
**UNDERGRADUATE RESEARCHER — advised by Prof. Bill Lin**
June, 2026 – Present

- Built an end-to-end toolchain compiling a trained Hopfield associative memory into synthesizable RTL — per-neuron Boolean minimization via Berkeley Espresso, graph-colored delay scheduling, and SystemVerilog emission — verified at N=256 neurons and 12,357 product terms, with 240/240 test vectors settling to the intended stored pattern under Icarus Verilog.
- Cut per-neuron logic from 627–2,918 product terms to 31–54 by specifying each neuron's function only over a bounded operating region and leaving the rest as don't-cares, reducing the specification from 65,536 rows to 2,768 at fan-in 16 and making fan-in 32 synthesizable where the full 4.3×10⁹-row table cannot be enumerated.
- Established the correctness conditions for clockless settling through RTL and gate-level experiments: coupled neurons must hold distinct delay *values* (a valid graph coloring with equal delays converges 0% of the time), and delay elements must be inertial rather than transport (100% vs 1–16% convergence), results that corrected two design assumptions carried in the project's patent draft.
- Raised storage capacity from the classical α=0.138 to α=0.5 (≥95% recall) via margin-based retraining under a sparsity mask; audited all project claims against regenerated source data, retracting 2 and revising 2 of 18.

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
