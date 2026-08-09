# Paper Preparation

Everything needed to write up the clockless LUT Hopfield work. **Nothing here is
hand-copied** — the numbers are regenerated from the result files by script, so a
value that drifts shows up here rather than in review.

## Read in this order

| File | What it is |
|---|---|
| `CLAIMS_AUDIT.md` | Every claim, its evidence tier, and what is verified / revised / **retracted**. Read first. |
| `TALKING_POINTS.md` | Positioning, prior-art risk, pros and cons, anticipated referee objections. |
| `PAPER_OUTLINES.md` | Three distinct theses with structure, evidence, and risk. Ends with a recommendation. |
| `RESULTS_TABLES.md` | Canonical numbers with Wilson 95% CIs. Generated. |
| `figures/` | Six figures, PDF (vector, for the paper) and PNG (preview). Generated. |

## Regenerating

```bash
python3 audit_claims.py --json data/claims_audit.json   # verify every claim
python3 make_tables.py                                  # RESULTS_TABLES.md
python3 make_figures.py                                 # figures/*.pdf|png
```

`audit_claims.py` is the gate: run it before any submission. It recomputes each
headline number from source and flags anything missing.

## Figures

| Figure | Shows | Tier |
|---|---|---|
| `fig1_coupling_graph` | Why index parity fails: 19/43 coupled pairs collide, vs 0 under colouring | T1 |
| `fig2_scheduling_rule` | The 2×2 — separation is necessary and sufficient | T1 |
| `fig3_scaling` | χ stays ~6 to N=4096; settling and recall hold | T3 |
| `fig4_dontcare` | Term count falls with fan-in; area comparison inverts | T2 / T4 |
| `fig5_two_levers` | Failures are spurious attractors, not oscillation | T1 |
| `fig6_capacity` | Recall is set by loading α, not by the schedule | T3 |

## Evidence tiers

- **T1** RTL measured (iverilog) — everything at N=16
- **T2** Tool measured (Berkeley espresso) — don't-care term counts
- **T3** Python simulator, validated against T1 at N=16 only — all scaling above N=16
- **T4** First-order analytical estimate — all area comparisons

The boundary that matters: **every scaling number above N=16 is T3**, and every
area number is T4. Word them accordingly.

## Headline results

1. **Don't-care synthesis** — fan-in 32 needs 5–27 product terms where the truth
   table has 4.3×10⁹ rows. Term count *falls* as fan-in grows. Behaviourally
   identical to the exact network inside the operating region.
2. **The scheduling rule** — coupled neurons must differ in delay *value*;
   necessary and sufficient; 18 schemes at 100%, both controls at 0%.
3. **Two levers** — scheduling fixes settling, loading fixes correctness. They
   are orthogonal and are often conflated.
