# LUT-HNN — a clockless Hopfield network compiled to logic

Compiling a trained Hopfield associative memory into synthesizable hardware in
which every neuron is a two-level Boolean function and the network settles
**without a clock**, update order being enforced by per-neuron delay values
derived from a graph colouring of the coupling matrix.

UC San Diego, Summer Research Internship Program (SRIP), 2026.
Aarav Vidhawan, advised by Prof. Bill Lin.

---

## What this is

A Hopfield network updates each neuron as `s_i = sign(Σ_j W_ij s_j)`. The usual
hardware realisation is a multiply-accumulate and a comparator. This project
instead **enumerates each neuron's update function as a Boolean function and
minimises it into logic** — no multipliers, no adders — and then removes the
clock, letting the network settle as a purely combinational feedback circuit.

Removing the clock creates the problem the project is actually about. If
mutually coupled neurons commit at the same instant, each acts on the other's
stale value and the network oscillates instead of converging. The fix is to
colour the coupling graph and give each colour class a **different delay value**,
so coupled neurons can never commit together.

**End to end, the pipeline is:**

```
trained weights W  →  per-neuron care set (operating region)
                   →  incompletely-specified PLA
                   →  espresso two-level minimisation
                   →  SystemVerilog SOP + graph-coloured delay schedule
                   →  iverilog simulation / yosys gate-level netlist
```

Run at N = 256 neurons, verified against its own behavioural model.

---

## Honest summary of what was and was not achieved

This is a research prototype. It does not beat production hardware, and several
of its early conclusions were overturned by later measurement — by design, since
every headline number is regenerated from source by
[`phase2/paper/audit_claims.py`](phase2/paper/audit_claims.py).

**Claim status after audit: 14 verified, 2 revised, 2 retracted.**
Full detail in [`CLAIMS_AUDIT.md`](phase2/paper/CLAIMS_AUDIT.md).

### What holds up

| result | number | evidence |
|---|---|---|
| Operating-region don't-care synthesis | care set 2,768 rows vs 65,536 for the full table at fan-in 16; **31–54 product terms vs 627–2,918** | measured, espresso |
| …and it dissolves the exponential wall | at fan-in 32 the full table is 4.29×10⁹ rows and cannot be enumerated; the care set is 21,956 | measured |
| Full-network RTL verification | N=256, 12,357 product terms, **240/240 test vectors settle to the intended pattern** | iverilog |
| Storage capacity under margin training | **α = M/N up to 0.5** with ≥95% recall, against 0.138 for the classical rule | measured |
| The scheduling invariant is on delay **values** | a *valid* graph colouring with all delays equal settles **0%** of the time | measured |
| The delay element must be **inertial** | cancelling superseded transitions: **100%** convergence, vs **1–16%** for transport delay | measured |
| Tolerance to delay variation | 100% settling out to **±348%** delay spread (3σ) | simulated |

### What did not

- **Area advantage is marginal or negative.** An early estimate claimed 2.4–2.8×
  smaller; synthesis says 1.52× smaller on an ASIC proxy and **1.19× larger on
  FPGA**. Do not lead with area.
- **A CAM beats this at small M.** At N=64, M=4 a nearest-match CAM is 2,858
  gates to our 7,020 and recalls 100% at every Hamming distance where we manage
  ~57%. We fail on storage before we fail on area.
- **Graph-colouring for update order is prior art**, extensively — traced back to
  Geman & Geman (1984), and stated as hardware by Aadit et al. (2022). See
  [`COLOR_UPDATE_ORDER_ART.md`](phase2/paper/COLOR_UPDATE_ORDER_ART.md).
- **Two published claims were retracted outright** — "32 oscillators never
  converge" (false; they were parity artifacts) and "noise is a third delay mode"
  (the noise RTL emitted byte-identical delays to depth mode).
- **No silicon, no PDK timing.** Area figures are yosys cell counts after
  technology-independent mapping.

---

## Repository map

```
phase1/          truth-table generation, pruning, retraining
  pruning.py       masked pseudoinverse retraining
  results/         per-configuration truth tables and sweeps

phase2/          logic minimisation, RTL, and everything after
  clockless/       the core pipeline
    gen_dc_pla.py        operating-region care sets  →  PLA
    schedule_hnn.py      coupling graph  →  DSATUR colouring  →  delays
    rtl_n256.py          end-to-end N=256 run
    improve_capacity.py  margin (Krauth–Mertens) training
    pvt_analysis.py      event-driven settling model
    gate_level_hazard.py yosys  →  primitive gates  →  iverilog
  phase9_ising/    MAX-CUT / Ising adaptation
  phase10_glitch/  inertial vs transport; C-element embodiment
  paper/           claims audit, figures, tables, prior-art review
  patent_figures/  USPTO-style figure set
  patent/          patent draft revisions

research/        literature notes
meetings/        advisor meeting materials, by date
sim/             early Python training and benchmarking
hardware/        FPGA project files
```

Start with [`phase2/PHASES.md`](phase2/PHASES.md) — written after the fact so the
work reads as a spine rather than a chronology, and it records where a later
phase overturned an earlier one.

---

## Reproducing

Requires `python3` (numpy, matplotlib), `iverilog`, `yosys`, and Berkeley
`espresso` on `PATH`.

```bash
# regenerate every headline number from source
python3 phase2/paper/audit_claims.py

# end-to-end N=256: care sets → espresso → SystemVerilog → iverilog
python3 phase2/clockless/rtl_n256.py --N 256 --M 4 --degree 16 --radius 3

# the scheduling result: colouring vs parity, distinct vs identical delays
python3 phase2/clockless/analyze_coupling.py

# inertial vs transport delay semantics
python3 phase2/phase10_glitch/inertial_required.py
```

---

## Key documents

| | |
|---|---|
| [`phase2/PHASES.md`](phase2/PHASES.md) | what each phase established, and what later overturned it |
| [`phase2/paper/CLAIMS_AUDIT.md`](phase2/paper/CLAIMS_AUDIT.md) | every claim, its evidence tier, and the retractions |
| [`phase2/paper/RESULTS_TABLES.md`](phase2/paper/RESULTS_TABLES.md) | results with Wilson confidence intervals |
| [`phase2/paper/PRIOR_ART_FINDINGS_READ.md`](phase2/paper/PRIOR_ART_FINDINGS_READ.md) | prior-art review from full-text sources |
| [`METHODS.md`](METHODS.md) | every training, pruning and retraining method used |

---

## A note on method

Results are tagged by evidence tier: **T1** measured in RTL, **T2** measured by a
tool, **T3** from the event-driven simulator, **T4** analytical estimate. The
audit script exists because three of the project's own conclusions were
overturned by later measurement, and the intent was that the record should show
that rather than hide it.
