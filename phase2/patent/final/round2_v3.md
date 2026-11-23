# Application 1 — final changes to the 8 November files

**Apply every change in Parts A to D, and nothing else.** Apply them to the
8 November files:

- `patent_app_integrated_clean.docx`
- `patent_app_integrated_tracked.docx`
- `patent_filing_package_hopfield_clean.docx`
- `patent_filing_package_hopfield_tracked.docx`

Make each change in both the clean and the tracked version. In the tracked
versions, record each Part under its own author: "Round 2" (Part A),
"Finalization" (Part B), "Claims and summary" (Part C) and "Filing package"
(Part D). Keep the earlier "Integration" and "Final fixes" revisions as they
are. Paragraph numbering stays [0001]–[0062]; only the claims grow, from 24 to
27.

Locate every passage by its content. Where this file quotes text to replace,
it is the exact 8 November wording. If a quoted passage is not found exactly,
stop on that item and report it rather than improvising.

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

   Keep the "between 10% and 50%" clause as written. It is an "in some embodiments" range that gives claim support; it is not presented as a measurement.

---

## Part C — Operating-region don't-cares in the Summary and the claims

Why: the don't-care synthesis is one of the three points that survived the
prior-art review. Before this Part, it was described only in [0051] and the
Example. It was missing from the Summary, and no claim covered it.
Disclosed-but-unclaimed subject matter is generally dedicated to the public
on publication. Claim 1 also said "according to a Boolean threshold function",
which a don't-care node satisfies only within the operating region.

8. **[0010] (Summary).** Immediately after "substantially reducing the logic cost of each node circuit." insert:

   > In other embodiments each threshold function is realized as a two-level sum-of-products network obtained by minimizing an incompletely specified Boolean function, the function being specified only on the combinations of node inputs arising within an operating region of the network, such as the network states within a bounded Hamming distance of a stored pattern, and left unspecified elsewhere, the care set being enumerated directly by complementing up to that distance of the input bits in the projection of each stored pattern onto the node inputs rather than by sampling network states, whereby the coupling weights are consumed at design time and no arithmetic is performed during operation.

9. **Claim 1.** Replace "according to a Boolean threshold function of a plurality of binary inputs;" with:

   > according to a Boolean threshold function of a plurality of binary inputs, at least for combinations of the binary inputs arising within an operating region of the integrated circuit;

10. **Claim 18.** Replace "combinational logic implementing a Boolean threshold function defined by the retrained coupling weights and threshold of that node;" with:

    > combinational logic implementing, at least for combinations of node inputs arising within an operating region of the network, a Boolean threshold function defined by the retrained coupling weights and threshold of that node;

11. **New claims 25 to 27.** Add them after claim 24 and before the ABSTRACT heading, each as its own paragraph formatted like claim 24:

    > 25. The integrated circuit of claim 1, wherein the operating region comprises states of the node circuits within a bounded Hamming distance of at least one stored pattern, and wherein at least one node circuit comprises a two-level sum-of-products network minimized from an incompletely specified Boolean function that is specified, for the combinations of the binary inputs of that node circuit arising within the operating region, to agree with the Boolean threshold function of that node circuit, and is unspecified for other combinations.

    > 26. The method of claim 18, wherein the operating region comprises states of the network within a bounded Hamming distance of at least one stored pattern, and wherein synthesizing comprises, for each node: determining a care set consisting of the combinations of node inputs arising within the operating region; specifying the Boolean threshold function of that node only on the care set, all other combinations of node inputs being left unspecified; and minimizing the resulting incompletely specified Boolean function to a two-level sum-of-products network.

    > 27. The method of claim 26, wherein determining the care set comprises enumerating, for each stored pattern, the projection of that stored pattern onto the inputs of the node with every combination of at most the bounded Hamming distance of those inputs complemented, whereby the care set is determined without sampling states of the network.

    Support in the description: [0010] (item 8), [0051] (item 4) and [0058]. Totals become 27 claims and 3 independent (1, 14, 18), with no multiple dependencies. That is within the Track One limits of 30 / 4.

---

## Part D — Filing package

12. **Delete** the sentence that begins "One remaining yellow bracket: the inventor-finalization items in the completion-detection…" (in the "Application contents" part), up to the end of that sentence. The bracket no longer exists after item 7.

13. **Update the claim count everywhere it appears:**
    - "24 claims (3 independent)" → "27 claims (3 independent)"
    - "Claim count: 24 total claims, 3 independent claims" → "Claim count: 27 total claims, 3 independent claims"
    - "24 total claims = 4 claims over 20" → "27 total claims = 7 claims over 20"

    Leave the per-claim fee amounts as they are. Search the package for any other "24" that refers to the number of claims, and update it the same way.

14. **Leave** the reference-numeral check, sheet list and Example summary as they are: Parts A to C add no drawing numerals and no figures.

---

## Verification (report each)

- **Clean application:** compared with 8 November, exactly these change: [0010], [0042], [0043], [0044], [0051], [0057], [0058], [0060], claim 1, claim 18, and the new claims 25–27. The INVENTOR FINALIZATION paragraph is gone, and every other paragraph is unchanged.
- **Tracked application:** accepting all changes reproduces the clean application. Rejecting one Part's author restores the previous state.
- **Claims:** they run 1–27 in order. Claims 25, 26 and 27 depend on 1, 18 and 26 respectively.
- **Filing package:** compared with 8 November, only the items in Part D change.
- **Reference numerals:** the 37 C.F.R. 1.84(p)(5) cross-check still finds every drawing numeral in the description and vice versa.

Report back with the before and after text of every change.
