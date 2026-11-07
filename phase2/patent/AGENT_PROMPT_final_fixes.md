# Prompt for the patent agent — final fixes to Application 1

Paste everything below the line into the agent session that holds the current
draft. Supply with it: the replacement FIG. 5 and FIG. 6A images, and the
revised node-circuit figure with DELAY SELECT 322 (FIX 5).

---

You are revising a US patent application draft (Application 1: "Self-timed
recurrent threshold-logic network with clockless sequencing of graph-colored
node partitions"; inventors Bill Lin and Aarav Vidhawan). Apply the fixes below
to the current draft, and to the filing-package description that accompanies
it. Make ONLY the changes listed. Do not rephrase, reformat or renumber anything
else. If something cannot be applied as written (the passage no longer exists,
or reads differently than described), stop on that item and report it instead
of improvising.

Paragraph numbers below are the ones in your previous report. Locate each
passage by its CONTENT, not its number, because numbering may have shifted.

The architecture and technical content of the application are frozen. These
fixes correct facts, references and drawings. They do not change what is
disclosed or claimed.

GROUND RULES
- Every numeric result must come from the facts given in this prompt. Never
  state power, energy, silicon, place-and-route or PDK-timing results: none were
  measured.
- Results are simulation results. The node logic was synthesized from minimized
  covers. The delay elements were modeled behaviorally (Verilog delays), which
  synthesis strips.
- Graph coloring for update ordering is prior art. Add no language presenting
  coloring itself as new.
- Do not alter claims.

=====================================================================
FIX 1 — Dangling annealing reference
=====================================================================
In the delay-differentiated paragraph about programmable / calibrated delay
elements (formerly [0038]), delete the trailing clause "as discussed below in
connection with annealing". Annealing is the subject of a separate application.
Fix the punctuation so the sentence ends cleanly, e.g. "...in which occasional
ordering violations are tolerable as stochastic perturbations." Then search the
whole document for "anneal". Report every other occurrence with its location;
do not change those.

=====================================================================
FIX 2 — Obsolete drawings note
=====================================================================
Delete the yellow-highlighted bracketed note asking the patent agent to prepare
formal drawings from the figure descriptions. Delete the whole note, including
its highlighting. Add no replacement.

=====================================================================
FIX 3 — Care-set numbers in the Experimental Example
=====================================================================
Verified facts (phase2/paper/data/dc_terms.json; phase2/clockless/gen_dc_pla.py,
N=256, M=4, radius 3, seed 11, recomputed for all 256 node circuits):

- 256 node circuits. 248 have 16 inputs and 8 have 15 (maximum fan-in 16).
  Four stored patterns.
- Operating region: all states within Hamming distance 3 of a stored pattern.
- Care-set size is per node circuit: the number of distinct input combinations
  in the union of the four projected radius-3 neighbourhoods. For a 16-input
  node each neighbourhood has 1 + 16 + 120 + 560 = 697 combinations, so the
  maximum is 4 × 697 = 2,788. The actual size is smaller where neighbourhoods
  overlap, i.e. where two projected patterns lie within distance 6 of each
  other.
- Across all 256 node circuits: 2,224 to 2,788 combinations. The most common
  size is 2,768 (95 of 256). NO node circuit has 2,784.
- Complete truth table of a 16-input node circuit: 65,536 rows.
- Product terms: six node circuits were minimized both ways. With
  operating-region don't-cares they needed 31 to 54 terms; with the complete
  truth table, 627 to 2,918. The whole network needed 12,357 terms with
  don't-cares.
- Fan-in 32 (a separate 1,024-node network, same M and radius): care set
  21,956, against 4,294,967,296 (about 4.29 × 10^9) for the complete table.

Edits:
(a) Replace the Example statement "2,784 states within Hamming distance three
of four 16-bit patterns" (formerly [0057]) with:
"For each node circuit, the care set comprised the combinations of neighbor
outputs lying within a Hamming distance of three of the projection of any
stored pattern onto that node circuit's inputs. For a node circuit of sixteen
inputs this is at most 4 × 697 = 2,788 combinations, and fewer where the
projections of two stored patterns lie within a distance of six of one another.
Across the 256 node circuits the care sets ranged from 2,224 to 2,788
combinations, the most common size being 2,768, against 65,536 for the complete
truth table of a sixteen-input node circuit."
(b) Make the product-term statement say it was measured on six node circuits:
"For six node circuits minimized both ways, minimization with operating-region
don't-cares yielded 31 to 54 product terms, against 627 to 2,918 when the
complete truth table was specified."
(c) Search the WHOLE document, including the don't-care synthesis figure's
description and the node-circuit paragraphs, for "2,784", "2,768" and "2,788".
Make every occurrence consistent with the facts above. A bare "2,768" must be
presented as the most common per-node size, never as THE care-set size.
(d) Where the Example says "fan-in 16", change it to "maximum fan-in 16".

=====================================================================
FIX 4 — Accuracy of the Example's setup and delay elements
=====================================================================
Verified facts (phase2/clockless/rtl_n256.py, phase1/pruning.py,
phase2/clockless/results/rtl_n256_inertial.json):
- Connectivity: a random support of degree 16. It was NOT pruned from a trained
  network.
- Stored patterns: four random patterns.
- Weights: fitted per node by masked least squares (a constrained
  pseudo-inverse) on that support, then symmetrized, with zero diagonal.
- Coloring: DSATUR, four update classes, no coupled pair sharing a delay value.
- Delay values: 1, 2, 3 and 4 time units (class index + 1).
- Node logic: zero propagation delay in simulation.
- Delay elements: INERTIAL. Each was modeled as a delay that cancels a pending
  output change if the node function reverts before the delay elapses (a
  Verilog continuous assignment with delay).
- Test: 240 vectors, 60 each at Hamming distance 0, 1, 3 and 5 from a stored
  pattern. All 240 reached a fixed point, every fixed point was the intended
  stored pattern, and the register-transfer results matched the behavioral
  simulator on all 240.

Edits:
(a) If the Example says the network was "produced by the method of FIG. 7", or
implies it was sparsified from a trained network, replace that with:
"A network was constructed with a random connectivity support of degree sixteen
and four random stored patterns, the weights of each node circuit being fitted
to the stored patterns by masked least squares on that support and the weight
matrix then symmetrized; the coloring, care-set derivation, minimization and
netlist steps of FIG. 7 were then applied."
Use the FIG. 7 step numerals as they actually appear in the document.
(b) Add to the Example:
"The four update classes were assigned delay values of one, two, three and four
time units, and the node logic was modeled with zero propagation delay, so that
the delay value associated with each class exceeded the settling time of the
class preceding it in that order."
(c) Add to the Example:
"Each delay element was modeled as an inertial delay element, a pending
transition at its output being cancelled when the value of the node function
reverted before the delay interval elapsed."
(d) The Example must not mention transport delay elements.

=====================================================================
FIX 5 — Show the programmable delay in the drawings
=====================================================================
Claim 3 recites programmable delay elements calibrated after manufacture. The
revised node-circuit figure supplied with this prompt adds a dashed control
input "DELAY SELECT (PROGRAMMABLE, OPTIONAL)", reference numeral 322, entering
delay element 316. Replace the node-circuit figure with the supplied version.
(a) In that figure's Brief Description paragraph, add "and, optionally, a
delay-select input by which the delay of the delay element is programmed".
(b) In the programmable-delay paragraph (the one edited in FIX 1), add after
its first sentence:
"In such embodiments the delay element 316 of each node circuit comprises a
delay-select input 322, illustrated in FIG. 3, by which its delay value is set,
for example from a configuration register or by the calibration procedure."
Use the node-circuit figure's actual number if it is not FIG. 3.
(c) Do not change claim 3.

=====================================================================
FIX 6 — Replacement images for FIG. 5 and FIG. 6A
=====================================================================
Replace the FIG. 5 and FIG. 6A images with the supplied exports. Place each at
full page width without resampling it down.
- FIG. 6A labels the completion-signal input "DONE_1, DONE_2 (FROM 506, 508)"
  with reference numeral 610. Make sure the convergence-detection paragraph
  names it. Where that paragraph describes sampling on each class's completion,
  add "the completion signals 610" so that it reads, for example, "...sampled
  on the completion signals 610 of the update classes, received from
  completion detection circuits 506, 508...". Make no other change to that
  paragraph.
- Check that FIG. 5 and FIG. 6A use the same names for the completion signals
  (DONE_1 / DONE_2, not DONE_A / DONE_B). If they differ, report it; do not
  edit images.
- Report each image's pixel dimensions and its effective resolution as placed
  on the page. Flag any below 300 dpi.

=====================================================================
FIX 7 — Filing package
=====================================================================
Rebuild the filing-package description from the document as it now stands. Do
not just patch in the numbers from your report.
(a) Count the drawing sheets and list every figure and sub-figure (FIG. 1 ...
FIG. 8, including lettered sub-figures such as 6A), with the sheet each is on.
State the total number of sheets.
(b) State the reference-numeral series actually used (100 to 800). Run a 37
C.F.R. 1.84(p)(5) check: list every numeral that appears in the drawings but
not in the description, and every numeral used in the description that appears
on no drawing. This includes 322 (FIX 5) and 610 (FIX 6). Report mismatches; do
not resolve them by deleting text.
(c) Confirm the Brief Description has exactly one paragraph per figure or
sub-figure, and that its numbering matches the drawings.
(d) State that the application includes one Experimental Example, and summarize
it in one line.
(e) Replace every old "7 sheets / numerals 100 to 700" statement.

=====================================================================
DO NOT CHANGE
=====================================================================
- The claims.
- Any text not named in this prompt.

=====================================================================
REPORT BACK
=====================================================================
1. For each fix, the exact before and after text, with paragraph locations.
2. Every occurrence found by the searches in FIX 1 and FIX 3(c), and what you
   did with each.
3. The full 1.84(p)(5) numeral cross-check from FIX 7(b).
4. Image dimensions and effective dpi from FIX 6.
5. Anything you could not apply, and why.
6. Any new inconsistency you notice, numbered by importance. List them; do not
   fix them.
