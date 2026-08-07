#!/usr/bin/env python3
"""
LUT-per-neuron clockless HNN vs the conventional threshold-gate HNN.

Benchmark ("industry best") = the standard digital Hopfield neuron: a cascaded
adder tree over w_i*s_i plus a sign comparison, clocked. Because s_i is binary,
no multipliers are needed -- w_i*s_i is a conditional negate -- so the adder
tree is the honest, optimised version of that design, not a strawman.

Compared per-neuron (area/delay vs fan-in) and per-network (settling latency,
convergence, clocking). Cost models are first-order gate-equivalent estimates,
NOT synthesis results; they are labelled as such and the crossover is reported
as a range, since the exact point depends on the standard-cell library.

Measured espresso term counts from phase2/pla_min/pseudo_maxprune anchor the
LUT model at fan-in 3..11; beyond that the threshold-function bound C(d, d/2)
is used, which our own data tracks closely (neuron 7 hits it exactly).
"""

import json, os
from math import comb, log2, ceil

HERE = os.path.dirname(os.path.abspath(__file__))

# fan-in -> espresso product terms, measured from the real minimised PLAs
MEASURED = {3: 3, 4: 3, 5: 7, 6: 13, 7: 19, 9: 126, 11: 386}

WEIGHT_BITS = 8          # weight precision for the adder-tree design
GE_PER_ADDER_BIT = 5     # gate-equivalents per full-adder bit (typical)
GE_PER_LITERAL = 1.0     # gate-equivalents per SOP literal (AND plane)


def lut_terms(d):
    """Product terms after minimisation. Threshold functions have inherently
    exponential 2-level complexity ~ C(d, d/2); espresso gets close to it."""
    if d in MEASURED:
        return MEASURED[d], "measured"
    return comb(d, d // 2), "C(d,d/2) bound"


def lut_cost(d):
    """Two-level SOP: AND plane + OR plane."""
    t, src = lut_terms(d)
    literals = t * (d / 2.0)                 # avg cube specifies ~half its inputs
    ge = literals * GE_PER_LITERAL + t       # AND plane + OR tree
    # delay: fan-in trees over d literals then over t terms
    depth = ceil(log2(max(d, 2))) + ceil(log2(max(t, 2)))
    return ge, depth, t, src


def threshold_cost(d):
    """Conditional-negate + adder tree + sign bit."""
    width = WEIGHT_BITS + ceil(log2(max(d, 2)))   # accumulator growth
    ge = (d - 1) * width * GE_PER_ADDER_BIT + d * WEIGHT_BITS  # adders + negates
    depth = ceil(log2(max(d, 2))) * ceil(log2(width))          # CSA tree stages
    return ge, depth, width


def per_neuron_table():
    print("=" * 92)
    print("PER-NEURON COST vs FAN-IN   (first-order gate-equivalent estimates)")
    print("=" * 92)
    print(f"{'fan-in':>7}{'LUT terms':>11}{'src':>16}{'LUT GE':>12}{'LUT depth':>11}"
          f"{'Thresh GE':>11}{'Thr depth':>10}{'winner':>10}")
    print("-" * 92)
    cross = None
    for d in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 24):
        lge, ldep, t, src = lut_cost(d)
        tge, tdep, _ = threshold_cost(d)
        win = "LUT" if lge < tge else "thresh"
        if cross is None and lge >= tge:
            cross = d
        print(f"{d:>7}{t:>11,}{src:>16}{lge:>12,.0f}{ldep:>11}{tge:>11,.0f}"
              f"{tdep:>10}{win:>10}")
    print("-" * 92)
    print(f"AREA CROSSOVER: LUT is smaller below fan-in ~{cross}, larger above.")
    return cross


def latency_table():
    """Network-level settling. All three converge to a fixed point EXCEPT
    synchronous parallel, which oscillates -- measured at 60.2% of all 2^16
    states cycling under synchronous dynamics on our N=16 network."""
    print()
    print("=" * 92)
    print("NETWORK-LEVEL SETTLING  (updates needed for one full relaxation sweep)")
    print("=" * 92)
    print(f"{'N':>7}{'chi':>6}{'sync par':>11}{'seq async':>12}{'ours (chi)':>12}"
          f"{'speedup vs seq':>16}{'converges?':>14}")
    print("-" * 92)
    for N, chi in ((16, 6), (64, 10), (256, 9), (1024, 5), (4096, 6)):
        print(f"{N:>7}{chi:>6}{1:>11}{N:>12}{chi:>12}{N/chi:>15.0f}x"
              f"{'yes (~100%)':>14}")
    print("-" * 92)
    print("sync parallel needs 1 update slot but does NOT converge:")
    print("  measured 60.2% of all 65,536 states cycle under synchronous dynamics.")
    print("seq async converges but serialises to N slots per sweep.")
    print("colour schedule converges AND runs chi slots -- chi stays ~6 as N grows.")


def qualitative():
    print()
    print("=" * 92)
    print("QUALITATIVE METRICS")
    print("=" * 92)
    rows = [
        ("clock tree", "none (clockless)", "required",
         "OURS: no clock distribution power/skew budget"),
        ("update latency", "1-2 logic levels", "log2(d) adder stages",
         "OURS at low fan-in"),
        ("area vs fan-in", "exponential ~C(d,d/2)", "linear O(d*w)",
         "THEIRS above the crossover"),
        ("area vs N", "O(N) neurons", "O(N) neurons",
         "tie (both linear in N at fixed fan-in)"),
        ("scaling in M", "fan-in >~6M -> exponential", "fan-in >~6M -> linear",
         "THEIRS"),
        ("weight precision", "none (absorbed in LUT)", "w bits/weight, affects area",
         "OURS: no quantisation error"),
        ("convergence", "~100% w/ colour schedule", "guaranteed if sequential",
         "tie; OURS keeps it while staying parallel"),
        ("determinism", "delay-ratio dependent", "clock-exact",
         "THEIRS: easier timing closure"),
        ("timing closure", "needs delay-ratio control", "standard STA",
         "THEIRS"),
        ("fault tolerance", "10% LUT corruption -> ~10% recall loss", "bit-flip in "
         "adder is catastrophic", "OURS (measured)"),
        ("don't-care exploit", "care set O(M*d^h), polynomial", "n/a",
         "OURS: this is the lever that rescues large fan-in"),
    ]
    print(f"{'metric':>20}  {'LUT clockless (ours)':<30}{'threshold clocked':<30}")
    print("-" * 92)
    for m, a, b, w in rows:
        print(f"{m:>20}  {a:<30}{b:<30}")
        print(f"{'':>20}  -> {w}")


if __name__ == "__main__":
    per_neuron_table()
    latency_table()
    qualitative()
