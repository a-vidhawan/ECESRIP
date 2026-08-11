#!/usr/bin/env python3
"""
How far can corruption go before recall fails?

Everything so far has quoted recall at HD<=3, which says nothing about where the
basin boundary actually is. This sweeps the corruption level from 1 flipped bit
upward, for several (N, M), under the graph-coloured clockless schedule.

Fan-in is min(N-1, 4M), matching nm_scaling.py, so these numbers are directly
comparable to the capacity frontier rather than to the fan-in-starved runs used
for the adjoint comparison.

Note HD is reported in absolute bits AND as a fraction of N: 6 flipped bits is a
mild perturbation at N=256 and a severe one at N=64, so absolute HD alone is
misleading when comparing sizes.
"""

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from scale_study import make_support
from improve_capacity import train_margin, n_fixed
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


def build(N, M, seed):
    d = min(N - 1, max(16, 4 * M))
    pats = np.random.default_rng(seed + M).choice([-1, 1],
                                                  size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    W = train_margin(pats, mask, seed=seed)
    return pats, W, d, n_fixed(W, pats)


def sweep(N, M, hds, trials, seed):
    pats, W, d, stored = build(N, M, seed)
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(seed + 99)
    out = []
    for hd in hds:
        if hd >= N:
            break
        ok = settled = 0
        for _ in range(trials):
            m = int(rng.integers(M))
            s = P01[m].copy()
            s[rng.choice(N, size=hd, replace=False)] ^= 1
            res, st = settle_event_driven(s, W, delays)
            settled += st
            ok += st and np.array_equal(res, P01[m])
        out.append(dict(N=N, M=M, fan_in=d, stored=stored, hd=hd,
                        hd_frac=hd / N, recall=ok / trials,
                        settled=settled / trials))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=str, nargs="+",
                    default=["64:8", "64:16", "64:32", "128:16", "128:32",
                             "256:16", "256:32"])
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    rows = []
    for case in args.cases:
        N, M = (int(x) for x in case.split(":"))
        hds = [h for h in (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48)
               if h < N]
        r = sweep(N, M, hds, args.trials, args.seed)
        rows += r
        st = r[0]["stored"]
        print(f"\nN={N} M={M} (fan-in {r[0]['fan_in']}, stored {st}/{M})")
        print("   HD:  " + "".join(f"{x['hd']:>6}" for x in r))
        print("  HD/N: " + "".join(f"{100*x['hd_frac']:>5.0f}%" for x in r))
        print("recall: " + "".join(f"{100*x['recall']:>5.0f}%" for x in r),
              flush=True)
    dest = os.path.join(HERE, "results", "hd_sweep.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
