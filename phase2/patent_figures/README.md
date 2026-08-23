# Patent figures — revised set

Eleven sheets, `out/patent_figures_v2.pdf`. Regenerate with
`python3 figs_1_5.py && python3 figs_6_11.py`.

Drawn to 37 CFR 1.84: black line art, no colour, no greyscale fill, vector PDF.
Distinctions that would normally be carried by colour (which class a node
belongs to) are carried by hatching and by an explicit roman-numeral label,
because colour drawings need a petition.

## FIGS. 1–5 — the inventor's originals, corrected

Reference numerals are unchanged so the specification does not need
renumbering. Numerals 310 and 516 are new.

| | what was wrong | what changed |
|---|---|---|
| 1 | signal lines crossed each other and passed through boxes; the node array showed five unlabelled nodes with arbitrary edges and no delay elements, so the figure did not depict the invention | orthogonal routing, no crossings; the control path is drawn as the closed loop it is; the array now shows the class partition and per-class delay values |
| 2 | two unrelated curves plus a third "trajectory" arrow on one pair of axes | one relationship, three annotated regions, schedule direction shown separately as 204 |
| 3 | the delay taps ran to the pulse filter while the multiplexer output looped backwards into it — not a circuit | taps go to the multiplexer, multiplexer feeds the filter, filter drives the output; the filter is now inside the element boundary; adds a waveform inset showing what the rejection window does |
| 4 | same tap-routing problem; no sizing constraint | routing fixed; the constraint that makes the block correct is stated on the sheet |
| 5 | no decision node, so the restart edge had no origin; the loop-back would have reset the margin every pass | proper flowchart shapes, explicit convergence test, `no` branch returns to the evaluate step rather than to the step that sets the margin low |

## FIGS. 6–11 — new

The original set draws the annealing embodiment in detail and the sequencing
mechanism not at all, which is backwards: the sequencing mechanism is what the
independent claims recite.

- **6** coupling graph → proper colouring → distinct delay values, with the
  constraint stated on values rather than labels
- **7** timing diagrams for a coupled pair, equal versus different delay
  values, with the measured 2×2
- **8** node circuit and the two-part delay sizing rule
- **9** delay-insensitive alternative embodiment (dual-rail, C-element
  completion detection), including why it does *not* replace the partitioning
- **10** operating-region don't-care synthesis flow
- **11** measured care-set size and product-term counts versus fan-in

## Which sheets carry measured values

**FIG. 7** (the 2×2) and **FIG. 11** (both panels) only. Both are labelled
MEASURED and state their conditions on the sheet. Everything else is
structural or states a relationship without asserting magnitudes — FIG. 2
carries "relationship shown; axes are not to scale" for that reason.

FIG. 2 is worth revisiting before filing. It asserts that the escaping-
transition rate falls monotonically with the timing margin, and **that
relationship has not been measured**. Adjacent things have been (glitch
injection rate versus recall; settling versus delay ratio), but not that curve.
It is drawn as a relationship rather than as data, which is permissible, but a
measured version would be better and the harness in `../phase10_glitch` can
produce one.

## Note for counsel

FIG. 6, FIG. 7 and FIG. 8 depict subject matter that `../paper/PRIOR_ART_REVIEW.md`
concludes is not adequately recited in the present independent claims, and
FIG. 10 depicts a family that is not claimed at all. Figures cannot cure that;
the claims have to.
