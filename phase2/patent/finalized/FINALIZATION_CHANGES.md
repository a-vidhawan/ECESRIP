# Inventor-finalization bracket resolved

Applied to the round-2 files (`../round2/`). In the tracked file these changes
are under the author **"Finalization"**, separate from "Integration",
"Final fixes" and "Round 2". Script: `apply_finalization.py`.

The bracket is deleted, and each of its three items is resolved inside the
paragraph it belongs to, so no paragraph is renumbered and the filing
package's paragraph references stay valid.

## Where each item went

**(b) Four-phase versus two-phase signalling** is appended to **[0042]**.
- Four-phase is the discipline, as already introduced in [0042]. It is what the project's dual-rail realization used (NULL/DATA, `phase2/phase10_glitch/schemes.py`).
- The added text records the one design detail that matters: in dual-rail, the state is captured during DATA and written back only during the spacer (NULL). Writing it back mid-DATA makes a rail fall and breaks monotonicity.
- Two-phase transition signalling is kept as an alternative, and the claims are not limited to either discipline.

**(c) Power-on reset and initialization** is appended to **[0043]**, the FIG. 5 phase-latch walkthrough.
- The protocol is driven by the initialization signal from initialization/readout circuitry 112.
- While that signal is asserted:
  - node outputs are forced to the input pattern at output stage 318;
  - delay elements such as 316 are held at the loaded value, so nothing is pending;
  - DONE_1 518 and DONE_2 516 are held low;
  - phase latch 510 is held in the state that enables the first class, with EN_1 512 and EN_2 514 gated off;
  - full-pass quiescence logic 606 is cleared.
- Release is a single transition. It is based on the `init_en` override the RTL actually used: it loads the input straight into node state and holds the delay line at that value.

**(a) Matched-delay sizing and guard band** is appended to **[0044]**.
- Settling time is defined as the longest sensitizable path, plus interconnect, plus any output-path delay element.
- Stages are sized by static timing analysis at each corner, using the smallest stage count that exceeds settling at every corner, plus a guard band.
- The guard band comes from statistical timing at a chosen number of standard deviations. The text gives "in some embodiments between 10% and 50% of the settling time", with optional post-manufacture calibration.

## Verification

- **Clean file:** only [0042], [0043] and [0044] change, and the bracket paragraph is gone. All other paragraphs are identical, and the numbering runs [0001] to [0062] unchanged.
- **Tracked file, accept all:** matches the clean file for every changed paragraph.
- **Tracked file, reject "Finalization" only:** gives back exactly the round-2 file.
- **LibreOffice:** renders the insertions and the struck-through bracket correctly.

## For the inventors to confirm

- These paragraphs describe design choices, not measurements. Only the `init_en` override and the four-phase dual-rail handshake were actually built and simulated. Neither inventor may sign off on text that doesn't reflect their design, so both should read these three additions.
- **The "10% to 50%" guard-band range is a drafting choice.** It gives claim support for a range, but nothing measured it, because no target process has been chosen. Keep it or delete that one clause.
- **The filing package still lists "One remaining yellow bracket".** That line is now out of date and should be deleted from the package.
