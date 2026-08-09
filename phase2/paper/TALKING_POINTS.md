# Talking Points, Positioning, and Honest Assessment

_Read `CLAIMS_AUDIT.md` first for what is and is not established._

---

## 1. The blunt version

We have **three results**. One is strong and probably novel. One is a solid
engineering contribution whose core idea is textbook. One is a framing device.
Ordering the paper by how impressive the work felt would put them in exactly the
wrong order.

| # | Result | Strength | Novelty risk |
|---|---|---|---|
| **A** | Don't-care synthesis collapses LUT cost for associative memory | **Strongest.** Measured, dramatic (2.7M predicted → 27 actual), behaviourally verified | **Moderate** — same *technique* as NullaNet/LogicNets, different *argument* |
| **B** | Chromatic delay scheduling for clockless settling | Clean theory + a decisive 2×2 experiment | **High** — the colouring idea is a standard result |
| **C** | Settling and correctness are orthogonal levers | Useful diagnostic framing | Not a contribution on its own |

**Lead with A.** It is the result that survives the hardest scrutiny.

---

## 2. The prior-art problem with B — read this before writing anything

Chromatic scheduling of parallel updates is **not new**. It is a standard result
in parallel algorithms: for any fixed-length Gauss-Seidel schedule there exists
an equivalent parallel execution derived from a colouring of the dependency
graph. It is the basis of multicolour Gauss-Seidel, and Gonzalez et al. (AISTATS
2011) built the Chromatic Gibbs sampler on exactly this argument for Markov
random fields — same graph, same colouring, same "same-colour vertices are
independent so update them together" reasoning. GraphLab ships it.

A referee in this area **will** know this. If the paper presents graph colouring
as its contribution, it gets desk-rejected or savaged.

**What is actually left after conceding all of that:**

1. **Colour classes are not a schedule in hardware.** In Gauss-Seidel or Gibbs,
   the colour class *is* the round — you execute class 1, then class 2. A
   clockless circuit has no rounds. Classes must be *realised* as physical delay
   values, and that realisation can fail while the colouring is still valid.
   Our `all_equal` control is precisely this: a correct 6-colouring in which all
   six classes were given delay 20, which settles **0%**. That failure mode does
   not exist in the round-based setting and is invisible to the standard theory.
2. **The invariant is on values, not on class membership.** This is the
   hardware-specific restatement of the rule, and it is the thing a designer
   actually needs. Our own verifier had this bug — it checked class labels and
   would have passed the 0% schedule.
3. **Incommensurability is irrelevant.** A natural hardware intuition (and our
   own earlier conclusion, from the T_ODD/T_EVEN ratio sweep) is that delays
   should be non-commensurate to avoid re-alignment. Measured: false. Powers of
   two — maximally commensurate — settle best. That is a genuinely
   counter-intuitive, hardware-specific negative result.

**Honest framing for B:** "we apply a known scheduling result to continuous-time
clockless hardware, and show that the translation is not free." That is
publishable as part of a systems paper. It is not publishable as a theory paper.

---

## 3. Why A is the stronger contribution

NullaNet and LogicNets already map neurons to Boolean functions and already use
don't-cares from observed activations. So the *technique* is known. What is
different here:

- **Their care set is empirical; ours has a closed form.** They record which
  input patterns occur on training data. For an associative memory the care set
  is *derivable*: it is the operating region — a union of M Hamming balls of
  radius h — projected onto each neuron's support, of size exactly
  `M · Σ_{j≤h} C(d,j)`. That is **polynomial in fan-in**, against a table that is
  exponential. You can state the size before running anything.
- **It inverts an apparently fundamental limit.** Each neuron computes a
  threshold function, and threshold functions have provably exponential two-level
  complexity — our own fully-specified PLAs track the `C(d, d/2)` bound, with
  neuron 7 hitting `C(9,4) = 126` exactly. That looks like a hard wall for LUT
  implementations, and it is the reason the field defaults to adder trees.
  Don't-cares dissolve it: 5–27 terms at fan-in 32.
- **Recurrence makes it non-obvious.** In a feedforward net, a wrong output on an
  unseen input is one wrong answer. In a recurrent attractor network it can
  create a *new fixed point* or a limit cycle and corrupt behaviour on inputs
  that were in the care set. That the minimised network is behaviourally
  identical in-region is a result, not a formality — and it is why we measured
  it rather than assuming it.

---

## 4. Pros — what to argue

- **Measured, not simulated, at the point that matters.** The don't-care result
  is real Berkeley espresso on real PLAs, not a cost model.
- **The negative results are load-bearing.** Incommensurability doesn't matter;
  ring/local supports fail; magnitude pruning cannot select a support at low
  rank. Each rules out an approach a reader would otherwise propose.
- **Falsification was built in.** The 2×2 has both controls, and both fail. The
  12-permutation robustness check exists specifically to kill the "you got lucky
  with those numbers" objection (sd = 0.00).
- **Two real bugs were found by the analysis and fixed** — `_prune_to_degree`
  silently no-opping on tied weights, and a verifier checking labels instead of
  values. Both are worth a sentence; they show the methodology has teeth.
- **Clockless is a genuine differentiator** where it applies: no clock tree, no
  distribution power, no skew budget, no weight quantisation.

## 5. Cons — what we must concede first, before a referee says it

- **Area is a weak argument, and we now know it.** Synthesis (yosys, N=64)
  gives LUT 1.52× smaller on an ASIC proxy but 1.19× *larger* on an FPGA proxy.
  The estimate that said 2.4–2.8× smaller was wrong. Lead with latency and
  clocklessness instead.
- **No silicon and no corner analysis.** For a *clockless* design the missing
  PVT analysis is the most serious gap: the entire approach rests on delay relationships holding
  across corners. (Mitigating argument: the rule requires only that coupled
  delays *differ*, and ordering is far more robust than absolute values. This is
  an argument, not evidence.)
- **RTL verification stops at N=256.** The full flow is measured there and
  matches the simulator on 240/240 inputs, but the N=4096 headline is still a
  Python simulator result. Quote N=256 as measured and N=4096 as projected —
  never blur them.
- **Don't-cares buy area with unspecified behaviour.** Off the care set the
  minimised network agrees with the exact one **2%** of the time. For associative
  recall that is fine. For anything adversarial, or any system that can present
  arbitrary states, it is not. Report this in the abstract, not the appendix — if
  a referee finds it themselves, the paper reads as evasive.
- **Toy scale and toy data.** M=4, random bipolar patterns, one training rule.
- **Small n in places.** "100% settled" on the oscillator set is 32/32 → Wilson
  95% CI [89.3, 100]. Pooling across schemes is what makes it convincing.

---

## 6. Anticipated referee objections, and the answer

**"Graph colouring for parallel updates is textbook (Gonzalez et al. 2011)."**
Concede immediately and cite it in the introduction, not the related-work
footnotes. Our contribution is the hardware realisation: colour classes must
become distinct *delay values*, a valid colouring with equal delays settles 0%,
and the commensurability intuition is wrong.

**"Your don't-care trick just moves the error somewhere you don't measure."**
Correct, and we measure it: Table 5 reports 2% off-region agreement explicitly.
The claim is scoped to the operating region and the region is a stated design
parameter (h), not an accident.

**"Threshold gates are smaller, simpler, and well understood. Why LUTs?"**
**Answer revised after synthesis — do not use the old estimate.** Measured with
yosys on the same N=64 network: LUT 7,020 gates vs threshold 10,659 (LUT 1.52×
smaller on a generic standard-cell mapping), but 1,728 vs 1,458 6-LUTs — the
**LUT design is 1.19× LARGER on an FPGA target**. The earlier T4 estimate
(2.4–2.8× smaller) was wrong on two counts: 4-bit weights preserve all patterns
where the estimate assumed 8, and 6-LUT packing suits the adder tree.

So **do not lead with area.** It is a modest, target-dependent win at best. The
defensible LUT advantages are single-level latency, no clock tree, no weight
quantisation, and graceful degradation under corruption.

**"Why is this a Hopfield network rather than a hash table / CAM?"**
A fair and dangerous question at M=4, N=16. The answer must be the graceful
degradation and Hamming-ball completion that a CAM does not give — and it should
be demonstrated against a CAM baseline, which we do not currently have. **This
is the most under-defended part of the whole project.**

**"α = 0.25 is above the classical capacity limit; of course it fails."**
Agreed — and that is our finding, not our oversight. It is exactly why we
separate the scheduling lever from the loading lever.

---

## 7. What would most improve the paper, in order

1. ~~**One end-to-end RTL run at N=256.**~~ **DONE** — 240/240 inputs match the
   simulator (C13). The scaling claim is measured at N≤256.
2. ~~**Synthesis numbers.**~~ **DONE** — and it corrected us: see C14. Next step
   is a real PDK with timing, to get delay as well as area.
3. **A baseline.** CAM, or a conventional clocked threshold-gate HNN, built and
   measured the same way. Without one, every comparison is against a model.
4. **Sweep the care radius h.** It is the design knob; we have one value.
5. **Corner/Monte-Carlo analysis on delay ratios.** Directly addresses the
   biggest structural objection to clockless.
6. **Structured patterns** (correlated, not random bipolar) to show basin
   geometry results are not an artifact of orthogonality.
