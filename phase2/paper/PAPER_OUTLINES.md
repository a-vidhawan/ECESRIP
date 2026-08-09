# Three Paper Outlines

Three genuinely different theses, not one paper aimed at three venues. Each
lists what it claims, what evidence it stands on, and what would sink it.

**Recommendation up front: Outline B is the most likely to be accepted; Outline A
is the best paper if we can get synthesis numbers; Outline C should only be
attempted as a workshop paper.** _Updated: the N=256 end-to-end RTL run (C13)
closes A's second-biggest gap — only synthesis remains._ Reasoning at the end.

Evidence tiers (T1 RTL / T2 tool-measured / T3 simulator / T4 estimate) are from
`CLAIMS_AUDIT.md`. A claim's tier determines how strongly it may be worded.

---

# Outline A — The systems paper

### "A Clockless Lookup-Table Hopfield Associative Memory"

**Thesis.** LUT-per-neuron associative memory is practical, not a toy: the
apparent exponential wall is an artifact of fully specifying functions, and
clockless settling can be made convergent by construction.

**Venues.** FCCM, FPL, DATE, ASP-DAC; journal version TCAS-I.

**Audience.** Hardware architects who default to adder trees.

### Structure

1. **Introduction** — Digital Hopfield implementations universally use
   multiply/accumulate + comparator. Two reasons LUTs are dismissed: threshold
   functions have exponential two-level complexity, and asynchronous timing is
   assumed to need a clock for determinism. We show both are avoidable.
2. **Background** — Hopfield dynamics; sequential convergence vs synchronous
   oscillation; two-level minimisation; the threshold-function complexity bound.
   *Cite Gonzalez et al. and multicolour Gauss-Seidel here, not later.*
3. **Architecture** — LUT neuron; clockless NBA settling; per-neuron delay.
   *Fig. 1.*
4. **Scheduling** — the energy cross-term argument; the colouring; the
   value-distinctness rule. *Fig. 1, Fig. 2, Table 1, Table 2.* [T1]
5. **Synthesis** — operating-region don't-cares; closed-form care set;
   espresso results. *Fig. 4, Table 4.* [T2]
6. **Verification** — behavioural equivalence in-region, divergence outside.
   *Table 5.* [T2/T3]
7. **Scaling and limits** — χ vs N; the α ceiling on recall. *Fig. 3, Fig. 5,
   Fig. 6, Table 3, Table 7.* [T1 at N≤256 via the end-to-end RTL run; T3 above]
8. **Comparison** — vs threshold-gate HNN across area, latency, clocking,
   quantisation, fault tolerance. Area is now synthesised [T2]: 1.52× smaller
   (ASIC proxy) but 1.19× larger (FPGA proxy). **Do not lead with area** — lead
   with latency and the absence of a clock tree.
9. **Limitations** — no silicon, no PVT, N=16 RTL ceiling, off-region behaviour.
10. **Conclusion.**

### Risk
Both original blockers are closed: scaling is measured in RTL at N=256 (Table 7)
and area is synthesised (C14). But synthesis **weakened** the story rather than
confirming it — the LUT is larger on an FPGA target. This outline now needs an
honest reframing around latency and clocklessness, with area reported as a wash.
A version that still claims an area win will not survive review.

---

# Outline B — The synthesis paper  ← recommended

### "Operating-Region Don't-Cares for Lookup-Table Associative Memories"

**Thesis.** For an attractor network the don't-care set is not empirical, it is
*derivable*: correctness is only required on the operating region, whose
projection onto each neuron's support has closed-form size
`M · Σ_{j≤h} C(d,j)` — polynomial in fan-in where the truth table is
exponential. This collapses LUT cost by orders of magnitude, and the resulting
network is behaviourally identical where it is specified.

**Venues.** DAC, ICCAD, DATE; journal version TCAD.

**Audience.** Logic synthesis and EDA.

### Structure

1. **Introduction** — LUT-mapped neurons (NullaNet, LogicNets, PolyLUT) use
   don't-cares harvested from training-set activations. For associative memory
   the care set can instead be *derived and bounded a priori*.
2. **The obstruction** — each neuron is a threshold function; threshold
   functions have exponential two-level complexity. Empirically our
   fully-specified PLAs track `C(d, d/2)`, with neuron 7 hitting `C(9,4)=126`
   exactly. *Table: measured terms vs bound.* [T2] This is the reason the field
   uses adder trees, and it is the thing we remove.
3. **Operating-region don't-cares** — definition; the closed form; why it is
   polynomial; the recurrence hazard (a wrong off-region output can create a new
   fixed point, unlike in a feedforward net).
4. **Method** — care-set enumeration directly in projection space (avoiding
   `O(N^h)` state sweeps); `.type fr` emission; espresso.
5. **Results** — *Fig. 4, Table 4.* fan-in 16: 31–54 terms vs 1,000–2,900
   fully specified (34.5×) and 100× faster to minimise; fan-in 24: 10–58 terms
   where the table is 16.7M rows; fan-in 32: 5–27 terms. Term count **falls**
   with fan-in. [T2]
6. **Correctness** — *Table 5, Table 7.* Rebuild the network from the SOPs;
   100% agreement in-region including beyond the care radius; 2% outside
   [T2/T3]. The same SOPs, emitted as SystemVerilog, settle and recall
   identically under iverilog at N=256 [T1] — so the minimisation is verified as
   hardware, not only as a Python model.
7. **Cost model** — inverted area comparison vs adder trees. [T4 — present as an
   estimate, explicitly]
8. **Limitations** — off-region unspecified; espresso runtime caps fan-in ≈32;
   one network family; h unswept.
9. **Related work** — NullaNet/LogicNets/PolyLUT/NeuraLUT; classical
   don't-care-based minimisation; threshold logic synthesis.

### Why this one
Narrowest scope, strongest evidence, least prior-art exposure, and the
contribution is stated as a bound that a reader can check without trusting our
hardware. It needs **no new experiments** to be submittable — everything in
sections 2–6 is already measured. Scheduling appears only as "we use a known
chromatic schedule," which removes the entire novelty argument in §2 of
`TALKING_POINTS.md`.

### Risk
"This is NullaNet with a different care set." Rebuttal must be crisp and early:
their care set is sampled and unbounded, ours is closed-form and provably
polynomial; and the recurrent setting makes correctness non-trivial in a way the
feedforward setting does not.

---

# Outline C — The timing paper

### "Delay Assignment for Convergent Clockless Attractor Networks"

**Thesis.** Chromatic scheduling is known, but its translation to
continuous-time hardware is not free: colour classes must be realised as
*distinct delay values*, and the natural engineering intuition about that
realisation is wrong.

**Venues.** ASYNC (the async circuits community), a DATE special session, or a
workshop. **Not** a theory venue.

### Structure

1. **Introduction** — clockless settling; why synchronous update oscillates
   (60.2% of the state space, exhaustively). [T1]
2. **Known result** — colouring ⇒ parallel-safe updates (Gauss-Seidel, Chromatic
   Gibbs). Conceded up front as prior art.
3. **The translation gap** — in a round-based sampler the colour class *is* the
   schedule; a clockless circuit has no rounds. Classes must become delays.
4. **The rule** — coupled neurons must differ in delay **value**. The 2×2:
   colouring with identical delays settles 0% despite being a valid colouring;
   distinct delays without colouring settle 0%. *Fig. 2, Table 1.* [T1]
5. **Two negative results** — (i) incommensurability is irrelevant; powers of two
   settle best, contradicting the re-alignment intuition and our own earlier
   ratio-sweep conclusion. (ii) The "symmetry crisis" at T_ODD=T_EVEN is not a
   timing resonance but the degenerate case of the rule. [T1]
6. **Robustness** — 12 permutations, sd = 0.00. *Table 2.* [T1]
7. **Scaling** — χ stays ~6 to N=4096. *Fig. 3.* [T3]
8. **Limitations** — no PVT analysis (the central one for async), N=16 RTL only.

### Risk
Thin. After conceding §2, the contribution is one rule and two negative results.
Honest, useful, and probably a workshop paper. The missing PVT analysis is fatal
at ASYNC specifically — that community will ask about corners immediately.
**Would become a real paper with Monte-Carlo delay-variation results**, which is
maybe a week of work and would make this the most novel of the three.

---

# Recommendation

- **Submit B.** It is complete now, evidentially strongest, and has the cleanest
  novelty story.
- **Build toward A.** With synthesis numbers and one N=256 RTL run, A becomes the
  better paper and subsumes B as a section. Without them, A's central comparison
  is unsupported.
- **Hold C** unless we do the corner analysis. Then it becomes genuinely novel
  and should be split out rather than folded into A.

**Do not** write one paper containing all three. The scheduling material invites
a prior-art fight that the don't-care result does not need, and mixing them means
the strongest contribution is defended on the weakest ground.

### Sequencing
1. Draft B now from existing results.
2. In parallel: N=256 RTL run, then synthesis. Those unlock A.
3. If corner analysis happens, C follows independently.
