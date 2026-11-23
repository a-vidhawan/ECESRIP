# Application 1 — changes since the 8 November version

This file records every change made to the 8 November application
(`patent_app_integrated_clean.docx` / `_tracked.docx`). The edits are already
applied in `phase2/patent/finalized/`. Use this file as the record, or give it
to an agent to apply the same changes to another copy. In that case: apply
these changes and nothing else.

In the tracked file the edits appear under two authors: **"Round 2"**
(items 1–6) and **"Finalization"** (item 7). Paragraph numbering is unchanged
([0001]–[0062]).

---

## Part A — Round 2 corrections

1. **[0057]** The N = 16 sweep excluded the stored patterns. Its initial states were all states at Hamming distance one, two or three from each of the four stored patterns (696 per pattern), not de-duplicated across patterns (`phase2/clockless/run_stress_round6.py`).

   Replace "all 2,784 initial states within Hamming distance three of a stored pattern" with:

   > "all of the 2,784 initial states at a Hamming distance of one to three from each of the four stored patterns (4 × 696)"

   Keep the rest of the sentence and its result unchanged.

2. **[0056]** No change. The N = 16 network was trained with the pseudoinverse rule on four random patterns and magnitude-pruned to the sparsest level at which all four patterns remain fixed points, with no retraining (`phase1/results/truth_tables/pseudo_s_maxprune/pipeline_meta.json`).

3. **[0060]** The N = 1,024, 2,048 and 4,096 networks were each built on a random connectivity support of degree 24 with four random stored patterns. The weights were fitted by masked least squares on that support and then symmetrized (`phase2/clockless/results/scale_final.json`).

   Replace "each storing M = 4 patterns with a degree bound of 24 and retrained on that support" with:

   > "each constructed with a random connectivity support of degree twenty-four and four random stored patterns, the weights being fitted by masked least squares on that support and then symmetrized"

   The paragraph already says these were software-model results, so no "in simulation" change is needed. Note that N = 256 used degree 16, while N = 1,024, 2,048 and 4,096 used degree 24.

4. **[0051]** (operating-region don't-cares at step 714) Replace "synthesizing the threshold functions to a gate-level netlist 714;" with:

   > "synthesizing the threshold functions to a gate-level netlist 714, in some embodiments each threshold function being specified only over the input combinations arising within an operating region of the network, the remaining combinations being left unspecified, and minimized as an incompletely specified Boolean function to two-level sum-of-products logic;"

   The wording follows [0058], which is the only other place in the application where the don't-care embodiment is described.

5. **[0058]** Delete the duplicate statement of the degree-16 support. Replace "The connectivity support was restricted to a degree bound of 16, so that each node circuit had a maximum fan-in of 16, …" with:

   > "Each node circuit had a maximum fan-in of 16, compared with 255 for a fully connected network."

   The degree-16 support is still stated once, in the paragraph's first sentence.

6. **[0036]** No change. Numeral 322 need not appear there.

---

## Part B — Inventor-finalization bracket resolved

7. **Delete** the bracketed paragraph beginning "[INVENTOR FINALIZATION — remaining selections for the phase-control embodiment: …]", together with its highlighting. Resolve its three items by appending text to the end of the paragraph each belongs to. No paragraph is added, so nothing is renumbered.

   **(b) Four-phase vs two-phase signalling.** Append to the end of **[0042]**:

   > In some embodiments the handshake operates under the four-phase discipline. In dual-rail embodiments, successive evaluations are separated by a spacer phase in which both rails of every node output are deasserted, so that each evaluation proceeds monotonically from the spacer; the node state is captured while the outputs of the evaluated class are valid and is written back to the node outputs only during the following spacer phase, because writing the state back while the outputs are valid would cause a rail to fall during evaluation and defeat the monotonicity on which completion detection relies. In other embodiments the handshake operates under a two-phase, transition-signaling discipline, in which each transition of a completion signal, in either direction, denotes completion and the phase element toggles in response, halving the number of signal transitions per cycle at the cost of completion detection that responds to transitions rather than to levels. The claims are not limited to either discipline.

   **(c) Power-on reset and initialization.** Append to the end of **[0043]**:

   > Initialization/readout circuitry 112 provides an initialization signal, which is asserted at power-on, for example by a power-on reset circuit, until the supply has stabilized, and whenever a new input pattern is to be loaded. While the initialization signal is asserted, (i) each node output is forced to the corresponding bit of the input pattern by an override at the output stage 318 of the node circuit, bypassing the node function; (ii) each delay element in the output path of a node circuit, such as the inertial delay element 316, is held at the loaded value, so that no transition is pending upon release; (iii) the completion signals DONE_1 518 and DONE_2 516 are held deasserted; (iv) the phase latch 510 is held in the state in which the phase signal P 520 enables the first update class, the enable signals EN_1 512 and EN_2 514 both being gated off for the duration of initialization; and (v) the full-pass quiescence logic 606 of FIG. 6A is cleared, so that the convergence signal cannot be asserted until at least one complete pass through all update classes has occurred after release. Release of the initialization signal is a single transition. In handshake-sequenced embodiments it enables the first update class, and evaluation proceeds through the cyclic order; in delay-differentiated embodiments it releases every node circuit at once, and the ordering emerges from the delay values. The node outputs constitute the result when the convergence signal is asserted.

   **(a) Matched-delay sizing and guard band.** Append to the end of **[0044]**:

   > The matched delay line of each update class is sized so that, at each characterized operating corner, its delay exceeds the worst-case settling time of that class by a guard band, the settling time comprising the delay of the longest sensitizable path through any node circuit of the class, the interconnect delay to the node circuits that receive its outputs, and the delay of any delay element in the node output path. In some embodiments the worst-case settling time of each class and the delay of one stage of the matched delay line are determined at each corner by static timing analysis, the number of stages is selected as the smallest number whose delay exceeds the settling time at every corner, and that number is increased by the guard band, which covers local variation not tracked by the matching. In some embodiments the guard band is determined from a statistical timing analysis of the target process at a selected number of standard deviations, and in some embodiments it is between 10% and 50% of the settling time. In further embodiments the matched delay line is programmable and is calibrated after manufacture in the manner described above for delay-differentiated embodiments.

   These are design statements. Only the `init_en` loading override and the four-phase dual-rail handshake were built and simulated. The "between 10% and 50%" range is a drafting choice, not a measurement; keep or delete that one clause.

---

## Part C — Operating-region don't-cares: what they are, and what is still open

**Mechanism.**
- Each node is a threshold function of its d neighbours. Written out in full, its truth table has 2^d rows: 65,536 at fan-in 16, and 4.29 × 10⁹ at fan-in 32.
- The network only operates near stored patterns. So the node is specified only on its *care set*: the input combinations that can arise while the network state lies within Hamming distance h of a stored pattern.
- The care set is derived in closed form, not sampled. Take each pattern's projection onto the node's inputs and flip up to h of those bits. That gives at most M · Σ_{k≤h} C(d,k) rows, which is polynomial in d.
- Every other row is a don't-care. The minimizer (espresso) uses that freedom to produce a small two-level sum-of-products cover.
- The weights are used only at design time, so no arithmetic remains in the circuit.

**Measured** (all already in [0058]):
- **Rows to specify at fan-in 16:** 2,224 to 2,788 per node, most often 2,768, against 65,536 for the full table.
- **Product terms:** 31 to 54 per node with don't-cares, against 627 to 2,918 with the full table (six nodes minimized both ways).
- **Rows to specify at fan-in 32:** 21,956, against about 4.29 × 10⁹.
- **Full N = 256 design:** 12,357 product terms, and correct recall on 240 of 240 inputs, out to Hamming distance 5.

**Limit.** Outside the operating region the circuit need not agree with the exact threshold network. On uniformly random states it agreed 2.5% of the time. It is designed for recall, not for arbitrary inputs.

**Why it matters.**
- It is what lets the compiled-logic approach scale past fan-in of about 16.
- It is one of the three points that survived the prior-art review. LUT-based neural-network work (NullaNet, LogicNets, PolyLUT) derives don't-cares by *sampling* activations, and only for feed-forward networks. Here the care set is derived in closed form from a stated region, for a recurrent network.

**Open — for Prof. Lin and the patent agent (not changed here):**
1. The don't-care embodiment is now described only in [0058] (the Example) and [0051] (step 714). It is not in the Summary and not in any claim. Disclosed-but-unclaimed subject matter is generally treated as dedicated to the public once the application publishes, unless it is claimed here or in a continuation. Consider a Summary sentence and at least one dependent claim.
2. Claim 1 says each node produces its output "according to a Boolean threshold function". A don't-care node agrees with that function only within the operating region, so check that the claim wording covers the embodiment actually built.
3. The filing package still lists "One remaining yellow bracket". That line is out of date now that item 7 has been applied.

---

## Verification of the applied files

- **Round 2:** only [0051], [0057], [0058] and [0060] changed. Rejecting "Round 2" restores the 8 November file exactly.
- **Finalization:** only [0042], [0043] and [0044] changed, and the bracket paragraph was removed. Rejecting "Finalization" restores the round-2 file exactly.
- **Accept all:** accepting every tracked change reproduces the clean file.
- **Numbering:** [0001]–[0062], unchanged.
