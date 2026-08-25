#!/usr/bin/env python3
"""
PHASE 10b -- do the DELAY VALUES have to be non-commensurate?

The draft, and FIG. 6, say the constraint is only that coupled nodes hold
DIFFERENT delay values, and that the particular values are otherwise immaterial.
The N=32 gate-level run casts doubt on that. Its delays were consecutive
multiples of one scale factor -- 120, 240, ... 840 -- and the zero-delay
reference settled 50% of the time, which is impossible if the schedule is doing
its job.

The suspected mechanism is realignment. Nodes re-evaluate continuously rather
than once per sweep, so a node commits, its neighbours re-evaluate, and THEIR
commits are scheduled one delay later. Commit times are therefore sums of delay
values. If every delay is a multiple of some g, every commit time is a multiple
of g and coupled nodes can land on the same instant despite holding distinct
delays. Distinctness is preserved; simultaneity is not prevented.

If that is right, the invariant needs restating: coupled nodes must not COMMIT
SIMULTANEOUSLY, and holding distinct delay values is sufficient only for the
first commit. This matters for the claims -- it is a different limitation from
the one presently drafted.

Uses the event-driven model rather than iverilog so that many delay pools can be
swept; that model was validated against the RTL at N=16 and N=256.
"""

import argparse, itertools, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLK = os.path.join(os.path.dirname(HERE), "clockless")
sys.path.insert(0, CLK)

from improve_capacity import train_margin_auto
from scale_study import make_support
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]


def pools(chi, scale):
    """Delay pools that all satisfy `coupled nodes hold distinct values`."""
    return {
        # every value a multiple of `scale` -> every commit time is too
        "consecutive  k*s": [scale * (c + 1) for c in range(chi)],
        # still commensurate: gcd is `scale`
        "powers of two": [scale * 2 ** c for c in range(chi)],
        # gcd is `scale` again, but sums coincide far less often
        "primes * s": [scale * PRIMES[c] for c in range(chi)],
        # gcd 1: sums of these coincide only rarely
        "primes, coprime": [PRIMES[c] * scale + c + 1 for c in range(chi)],
        # irrational ratios cannot realign at all
        "incommensurate": [scale * (1.0 + c * 0.61803398875) for c in range(chi)],
    }


def run(N, M, degree, seed, trials, scale):
    rng = np.random.default_rng(seed)
    pats = rng.choice([-1, 1], size=(M, N)).astype(float)
    mask = make_support(N, min(N - 1, degree), "regular",
                        np.random.default_rng(seed))
    W, _ = train_margin_auto(pats, mask, seed=seed)
    n, edges = graph_from_W(W)
    col = dsatur(n, edges)
    chi = max(col.values()) + 1
    starts = [rng.integers(0, 2, size=N).astype(np.int8) for _ in range(trials)]
    out = {}
    for name, vals in pools(chi, scale).items():
        d = [vals[col[i]] for i in range(N)]
        ok = sum(settle_event_driven(s0.copy(), W, d)[1] for s0 in starts)
        out[name] = ok / trials
    return chi, len(edges), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, nargs="+", default=[16, 32, 64, 128])
    ap.add_argument("--M", type=int, default=8)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--scale", type=int, default=10)
    ap.add_argument("--nets", type=int, default=3)
    args = ap.parse_args()

    names = list(pools(4, 10))
    print(f"Fraction of random initial states reaching a fixed point.\n"
          f"Every pool below is a VALID schedule: coupled nodes always hold "
          f"distinct delay values.\n")
    hdr = f"{'N':>5}{'chi':>5}{'edges':>7}" + "".join(f"{n:>18}" for n in names)
    print(hdr); print("-" * len(hdr))
    rows = []
    for N in args.N:
        acc = {k: [] for k in names}
        chis, eds = [], []
        for k in range(args.nets):
            chi, ed, res = run(N, args.M, args.degree, 11 + k, args.trials,
                               args.scale)
            chis.append(chi); eds.append(ed)
            for kk, v in res.items():
                acc[kk].append(v)
        m = {k: float(np.mean(v)) for k, v in acc.items()}
        rows.append(dict(N=N, chi=float(np.mean(chis)), edges=float(np.mean(eds)),
                         **m))
        print(f"{N:>5}{np.mean(chis):>5.0f}{np.mean(eds):>7.0f}" +
              "".join(f"{100*m[n]:>17.0f}%" for n in names), flush=True)
    print("-" * len(hdr))
    print("If the left columns lose to the right ones, distinctness of the delay")
    print("VALUES is not sufficient -- what matters is that commit times, which")
    print("are sums of delays, do not coincide on a coupled pair.")
    dest = os.path.join(HERE, "results", "commensurate.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
