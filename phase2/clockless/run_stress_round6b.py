#!/usr/bin/env python3
"""
Round 6b: why does colouring settle LESS often than parity on ordinary states?

Round 6 found colouring cracks all 32 universal oscillators (parity: 0% settled,
colouring: 100%) but drops settled-rate on hd3/heavy/random from ~99% to ~95%.
This isolates that regression set and asks whether it is a timeout artifact
(longer schedules need longer to converge) or genuinely new oscillators.
"""

import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_clockless_stress import RTL, RES as RESULTS, run_batch, nearest_pat

SCHEME_RTL = {
    "colour6":  ("coloring", os.path.join(RTL, "clockless_col_colour6.sv"), 29),
    "dist2":    ("coloring", os.path.join(RTL, "clockless_col_dist2.sv"), 53),
    "distinct": ("coloring", os.path.join(RTL, "clockless_col_distinct.sv"), 71),
}


def main():
    src = os.path.join(RESULTS, "stress_r6_scheduling.csv")
    df = pd.read_csv(src)

    # settled status per (testset, init_state, scheme)
    piv = df.pivot_table(index=["testset", "init_state"], columns="scheme",
                         values="settled", aggfunc="first")
    piv = piv.dropna()

    print("=" * 70)
    print("REGRESSION ANALYSIS: settled under parity, oscillating under colouring")
    print("=" * 70)

    frames = []
    for scheme in ["colour6", "dist2", "distinct"]:
        if scheme not in piv.columns:
            continue
        reg = piv[(piv["parity"] == True) & (piv[scheme] == False)]
        gain = piv[(piv["parity"] == False) & (piv[scheme] == True)]
        print(f"\n{scheme}: {len(reg)} states regressed, {len(gain)} states rescued")

        if not len(reg):
            continue
        states = sorted({int(str(s), 16) for _, s in reg.index})
        print(f"  re-running {len(states)} regressed states at 1x / 4x / 16x timeout")

        mode, path, base_d = SCHEME_RTL[scheme]
        pidx = [nearest_pat(v)[0] for v in states]
        hds  = [nearest_pat(v)[1] for v in states]
        for mult in (1, 4, 16):
            d = base_d * mult
            r = run_batch(f"r6b_{scheme}_x{mult}", mode, states, pidx,
                          [-1.0] * len(states), hds, path, d,
                          variant_tag=f"_{scheme}_x{mult}")
            if len(r):
                r["scheme"] = scheme
                r["timeout_mult"] = mult
                frames.append(r)
                print(f"    x{mult:<2d} (TIMEOUT={64*d+100:6d}ns): "
                      f"settled={r['settled'].mean()*100:5.1f}%  "
                      f"correct={r['correct'].mean()*100:5.1f}%")

    if frames:
        out = pd.concat(frames, ignore_index=True)
        dest = os.path.join(RESULTS, "stress_r6b_regression.csv")
        out.to_csv(dest, index=False)
        print("\n" + "=" * 70)
        print(out.pivot_table(index="scheme", columns="timeout_mult",
                              values="settled", aggfunc="mean").round(3).to_string())
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
