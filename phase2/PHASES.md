# Project Phases

Written after the fact, so the work has a spine rather than a chronology. Commit
subjects use the `phaseN:` prefix from phase 5 onward; earlier commits predate
the scheme and are mapped here by content.

Each phase lists what it established, the code that produces it, and — where it
matters — what a later phase overturned.

---

## Phase 1 — Clockless settling and stress testing

Build a Hopfield network whose neurons are lookup tables, settle it without a
clock using per-neuron NBA delays, and stress the result.

- **Code:** `gen_clockless_sv.py`, `run_clockless_stress.py`,
  `run_stress_round3.py` … `run_stress_round5.py`
- **Established:** 60.2% of all 2^16 states cycle under synchronous updates
  (exhaustive); asynchronous settling is what breaks them.
- **Superseded:** the `noise` delay mode was never a third condition — it emits
  delays byte-identical to `depth`. Every "noise" row in rounds 1–5 duplicates
  `depth`. See `paper/CLAIMS_AUDIT.md` R2.

## Phase 2 — The scheduling rule

Why `even_odd` still oscillated, and what the general rule is.

- **Code:** `analyze_coupling.py`, `run_stress_round6.py`, `run_stress_round7.py`,
  `schedule_hnn.py`
- **Established:** index parity leaves 19/43 (44%) of coupled pairs committing
  simultaneously. The rule is that **coupled neurons must differ in delay
  VALUE** — necessary and sufficient, 18 schemes at 100%, both controls at 0%.
  χ stays ~6 even at N=4096.
- **Superseded:** the "T_ODD/T_EVEN symmetry crisis" is the degenerate case of
  this rule, not an integer-ratio effect. Incommensurability is irrelevant.

## Phase 3 — Scaling and don't-care synthesis

- **Code:** `scale_study.py`, `gen_dc_pla.py`, `verify_dc_recall.py`
- **Established:** specifying only the operating region collapses LUT cost —
  fan-in 32 needs 5–27 product terms against a 4.3×10⁹-row table. Care-set size
  is `M·Σ_{j≤h} C(d,j)`, polynomial in fan-in. Behaviourally identical in-region,
  2% agreement outside.
- **Superseded:** phase 3's own earlier conclusion that the LUT hits an
  exponential wall — that was an artifact of fully specifying the functions.

## Phase 4 — Verification and baselines

Move claims from estimate to measurement.

- **Code:** `rtl_n256.py`, `synth_compare.py`, `pvt_analysis.py`,
  `cam_baseline.py`, `msweep_cam.py`
- **Established:** full flow verified in RTL at N=256 (240/240 inputs match the
  simulator); area synthesised with yosys; PVT-robust to ±348% delay spread, and
  variation *rescues* a degenerate schedule.
- **Overturned two of our own claims:** the estimated area advantage
  (2.4–2.8× smaller) became 1.52× on ASIC and 1.19× *larger* on FPGA; and a
  nearest-match CAM beats this design on both area and function at small M.

## Phase 5 — Capacity and the training rule

- **Code:** `improve_capacity.py`, `nm_scaling.py`, `hd_sweep.py`
- **Established:** capacity is a property of the training rule, not the
  architecture. A masked symmetric margin rule (perceptron/minover) stores
  1.5–3× more patterns than least-squares-plus-symmetrise at the same fan-in.
  Storage and ≥95% recall hold to α≈0.5. Recall degrades with HD/N, not absolute
  HD: N=256 holds ≥90% recall at 19% corruption.
- **Superseded:** the fixed κ=1 default. The apparent capacity cliff at N=256,
  α=0.5 was the κ=1 feasibility boundary — κ=0.7 stores all 128.
  `train_margin_auto` now takes the largest feasible κ.

## Phase 6 — Adjoint / implicit differentiation

Optimise basin size directly instead of using margin as a proxy.

- **Code:** `adjoint_train.py`
- **Status:** partial. First implementation was **wrong** — the undamped forward
  map `tanh(βWs)` is a synchronous update and oscillated, converging only 15–50%
  of the time, so most gradients were taken at non-equilibria. Damped to γ=0.7
  (100% convergence), margin term retained to pin the fixed points, per-step
  renormalisation removed.
- **Result so far:** at N=64, M=16, fan-in 32 — stored 14/16 → 15/16, recall@HD3
  42% → 52%. One configuration on a deliberately fan-in-starved network. Not yet
  established across the regimes where the margin rule is already strong.

## Phase 7 — Hazards

- **Code:** `hazard_analysis.py`
- **Established:** spurious commits do not break settling. At N=256, 86 glitches
  against 123 commits still gives 98% recall; settling stays 100% at every rate.
  Targeted glitching of the deepest-logic quarter of neurons holds to p=0.8.
- **Consequence:** hazard-free synthesis and Muller C-elements are probably
  unnecessary — which matters, because both cost area this design cannot spare,
  and hazard-free two-level synthesis would require retaining exactly the
  redundant terms that phase 3 removes.
- **Open:** gate-level simulation with annotated delays is the definitive test.
  The injection model is conservative in one way (a latched wrong value is worse
  than a narrow pulse) and optimistic in another (independent rather than
  correlated with input transitions).

---

## Where the evidence stands

See `paper/CLAIMS_AUDIT.md` for per-claim evidence tiers. Summary:

| tier | meaning | scope |
|---|---|---|
| T1 | RTL measured (iverilog) | N ≤ 256 |
| T2 | Tool measured (espresso, yosys) | synthesis and area |
| T3 | Simulator, validated against T1 at N=16 and N=256 | N > 256, capacity, hazards |
| T4 | Analytical estimate | superseded by T2 for area |
