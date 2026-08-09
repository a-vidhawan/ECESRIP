# Claims Audit

_Companion to `audit_claims.py`, which recomputes every number below from its
source file. Run it before any submission: `python3 audit_claims.py`._

**Status: 10 verified, 1 revised, 2 retracted.**

Two claims currently stated as fact in `clockless/STRESS_TEST_FINDINGS.md` are
false, and one is misattributed. They were produced by earlier rounds and
contradicted by later ones; the findings document was appended to rather than
reconciled. **These must be fixed before any of that text is reused.**

---

## 1. Evidence tiers

Not all results here carry the same weight, and a paper must not present them as
though they do. Every claim is tagged with the strongest evidence supporting it.

| Tier | Meaning | What it covers |
|---|---|---|
| **T1 — RTL measured** | iverilog simulation of generated SystemVerilog | Everything at N=16: rounds 1–7, the 2×2 scheduling rule, oscillator sets |
| **T2 — Tool measured** | Real Berkeley espresso runs | Don't-care term counts at fan-in 16/24/32; full-table term counts |
| **T3 — Simulator** | Python schedule model, validated against T1 at N=16 **and N=256** | Scaling results N > 256; capacity scan |
| **T4 — Analytical estimate** | First-order gate-equivalent models | All area comparisons vs threshold gates |

**The tier boundary that matters most: N ≤ 256 is measured; above that is
simulated.** The simulator models the delay schedule as periodic firing rather
than event-driven NBA semantics, so it needed independent confirmation. It now
has two anchor points: N=16 (qualitative, both directions) and **N=256, where
the full flow — don't-care SOPs → SystemVerilog → iverilog — agrees with the
simulator on 240/240 inputs**. Claims at N=256 and below are measured. A claim
of the form "this works at N=4096" is still a simulator claim.

---

## 2. Retracted

### R1 — "32 universal oscillators never converge under any configuration"

Stated in finding #4. **False.** Every graph-coloured schedule settles all 32,
across 18 independent schemes. They were artifacts of parity collisions, not
intrinsic limit cycles. The original claim generalised from having tried only
even_odd variants.

Source: `stress_r6_scheduling.csv`, `stress_r7_permutation.csv`.

### R2 — "noise is a third delay mode"

The canonical noise configuration (seed 99, scale 0.5) emits delays
**byte-identical** to depth mode, because `round(d + U(-0.5, 0.5))` almost always
returns `d`. Every "noise" row in rounds 1–5 duplicates depth mode under a
different label.

**Consequence:** the three-way mode comparison throughout findings #2, #5–#13 is
really two-way, and any statement of the form "all three modes agree" is
circular. Noise *sweeps* at scale ≥ 2.0 are genuine and unaffected.

Source: `rtl/clockless_depth.sv` vs `rtl/clockless_noise.sv`.

---

## 3. Revised

### V1 — the "T_ODD/T_EVEN symmetry crisis"

Finding #3 concluded "avoid integer ratios; use 2.4×, 3×, or any non-integer."
That framing is wrong. Ratio = 1.0 means T_ODD = T_EVEN, i.e. *every neuron
shares one delay value* — which is exactly the `all_equal` control that settles
0% on hard states. The crisis is an instance of the value-collision rule, not a
separate timing phenomenon.

Round 7 then showed commensurate delays settle perfectly well (100% on the
oscillator set, 3 schemes) provided the values **differ**. So integer ratios per
se are harmless; only equality is fatal. The residual dip at ratio 2.0 is
unexplained and is too small to build an argument on — **do not put it in a
paper without re-running it.**

Source: `stress_add_ratio_sweep.csv` (ratio 1.0: 64.3% vs 97.6% elsewhere),
`stress_r7_permutation.csv`.

---

## 4. Verified

| ID | Claim | Tier | Key number |
|---|---|---|---|
| C1 | Synchronous updates cycle on most of the state space | T1 | 39,436/65,536 = 60.2% cycle; 9.55% reach a stored pattern |
| C2 | Index parity collides coupled neurons | T1 | 19/43 = 44.2%; hub neuron 14 collides with 6 of 11 neighbours |
| C3 | Coupled neurons must differ in delay **value** — necessary and sufficient | T1 | colour+distinct 100% (18 schemes); both controls 0% |
| C7 | The schedule scales; χ stays small | **T3** | χ = 6 at N = 4096; settling and recall 100% |
| C13 | Full flow runs in RTL at N=256 and matches the simulator | **T1** | 240/240 inputs identical; 100% settled and recalled; 12,357 terms, χ=4 |
| C8 | Don't-cares keep term count flat in fan-in | T2 | fan-in 32: 5–27 terms vs 4.3×10⁹ table rows |
| C9 | Minimised network is behaviourally identical in-region | T2/T3 | 100% agreement HD≤5; 2% agreement off-region |
| C10 | Recall is governed by α = M/N, not by the schedule | T3 | α=0.25 → 79%; α=0.125 → 100% |
| C11 | Residual failures are spurious attractors, not oscillation | T1 | random states: 75.8% spurious vs 1.7% oscillated |
| C12 | On full tables espresso tracks the C(d,d/2) threshold bound | T2 | 5/16 neurons hit it exactly (neuron 7: 126 = C(9,4)) |

---

## 5. Gaps — claimed nowhere, but a referee will ask

These are not errors; they are missing work. Listed in the order I would close
them.

1. ~~**No RTL above N=16.**~~ **CLOSED.** `rtl_n256.py` runs the full flow at
   N=256 under iverilog and matches the simulator on 240/240 inputs (C13). The
   remaining exposure is N > 256, which is still T3.
2. **No synthesis.** Every area and delay comparison is T4. Without at least a
   standard-cell or FPGA synthesis run, the LUT-vs-threshold comparison is an
   argument, not a measurement.
3. **No PVT / corner analysis.** A clockless design lives or dies on whether the
   delay *ordering* survives process, voltage and temperature variation. The rule
   requires only that coupled neurons differ, which is encouraging — ordering is
   more robust than absolute values — but this is untested and is the most
   likely reviewer attack on the whole approach.
4. **Care radius `h` never swept.** It is now the principal design knob (it sets
   both LUT size and the size of the guaranteed-correct region) and we have a
   single value, h=3.
5. **One network family.** Random bipolar patterns, pseudoinverse, one pruning
   method. No structured or real-world patterns, which have correlations that
   could change basin geometry substantially.
6. **M is barely varied.** Almost everything is M=4. The capacity claims lean on
   a T3 scan over unpruned networks.
7. **Trial counts are small in places.** Scaling rows are 25–30 trials; the
   oscillator set is n=32. See the Wilson intervals in `RESULTS_TABLES.md` —
   "100%" at n=32 has a lower bound near 89%.
8. **Espresso runtime bounds fan-in at ~32.** Not a term-count limit, but it
   caps what we can demonstrate.

---

## 6. Required edits to `STRESS_TEST_FINDINGS.md`

- Finding #3: rewrite per V1. Delete the "avoid integer ratios" rule.
- Finding #4: delete the universal-oscillator claim; replace with R1.
- Findings #2, #5–#13: add a note that the `noise` column duplicates `depth`.
- Finding #16: already superseded by #17; make the supersession explicit at the
  top of #16 rather than leaving the reader to reconcile them.
