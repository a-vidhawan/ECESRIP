# Round 2 — changes applied to the application

Applied to the 8 November files (`patent_app_integrated_clean.docx` and
`patent_app_integrated_tracked.docx`), per `../AGENT_REPLY_round2.md`. In the
tracked file the changes are under the author **"Round 2"**, kept separate
from "Integration" (5 Nov) and "Final fixes" (8 Nov). The filing package is
unchanged: none of the edited wording appears in it.

Script: `apply_round2.py` (reproducible from the 8 November inputs).

## Changes

**[0051]**, step 714. Added after "...to a gate-level netlist 714":
> ", in some embodiments each threshold function being specified only over the input combinations arising within an operating region of the network, the remaining combinations being left unspecified, and minimized as an incompletely specified Boolean function to two-level sum-of-products logic"

The wording follows [0058], which is the only other place the don't-care
embodiment is described (see note 1 below).

**[0057]**
- Before: "...settled from all 2,784 initial states within Hamming distance three of a stored pattern, with no oscillation."
- After: "...settled from all of the 2,784 initial states at a Hamming distance of one to three from each of the four stored patterns (4 × 696), with no oscillation."

Source: `phase2/clockless/run_stress_round6.py` enumerates distances 1 to 3
(`range(1, 4)`) from each pattern, with no de-duplication.

**[0058]**, removing the duplicate statement of the degree-16 support.
- Before: "The connectivity support was restricted to a degree bound of 16, so that each node circuit had a maximum fan-in of 16, compared with 255 for a fully connected network."
- After: "Each node circuit had a maximum fan-in of 16, compared with 255 for a fully connected network."

The degree-16 support is still stated once, in the first sentence.

**[0060]**
- Before: "...each storing M = 4 patterns with a degree bound of 24 and retrained on that support, were evaluated..."
- After: "...each constructed with a random connectivity support of degree twenty-four and four random stored patterns, the weights being fitted by masked least squares on that support and then symmetrized, were evaluated..."

The paragraph already says "software model", so it needed no "in simulation"
change. Its counts (5, 6, 6 classes; all settled and recalled) match
`phase2/clockless/results/scale_final.json`.

**[0056]** and **[0036]**: no change, as instructed.

## Verification

- **Changed paragraphs:** clean output against clean input differs in exactly [0051], [0057], [0058] and [0060], with the same paragraph count.
- **Tracked file, accept all:** against the input with the same procedure, the only differences are those four paragraphs, and each matches the clean output.
- **Tracked file, reject "Round 2" only:** the result is identical to the 8 November input.
- **Revision marks:** "Round 2" adds 4 deletions and 4 insertions, and all revision ids are unique.
- **LibreOffice:** both files open, and the tracked markup renders as separate rounds.

## Notes for you (not changed)

1. **The don't-care embodiment appears only in the Example.** Neither the Summary, the detailed description outside [0051]/[0058], nor the claims describe operating-region don't-care synthesis. The earlier drafts had it in the Summary. That embodiment is novelty point (c), and with this text it is disclosed but claimed nowhere. Whether to add a Summary sentence and a dependent claim is a decision for Prof. Lin.
2. **The filing package still lists one yellow bracket:** the inventor-finalization items in the completion-detection section. It is still in the application, unresolved.
