#!/usr/bin/env python3
"""
N x M scaling under ADAPTIVE margin -- the phase-8 re-run of nm_scaling.py.

Identical in every respect to `clockless/nm_scaling.py` except that the weights
come from `train_margin_auto` (largest FEASIBLE kappa) rather than
`train_margin` (fixed kappa=1), and the chosen kappa is recorded per point.

Why this matters: the "capacity cliff at alpha ~ 0.6" in the original sweep is
a property of kappa=1, not of the architecture. At N=256, alpha=0.5 the kappa=1
constraint system is infeasible and stores 0/128 patterns; kappa=0.7 stores
128/128. The original sweep therefore measured where kappa=1 becomes infeasible,
not where the memory actually saturates.

Two questions, kept separate as before:

  STORAGE  -- are all M patterns fixed points? A yes/no property of training.
  RECALL   -- does a corrupted pattern settle back onto the right one?

Fan-in is chosen generously (min(N-1, max(16, 4M))) so storage is not fan-in
limited; the point is to isolate the loading alpha = M/N.

The sweep is expensive at high alpha: an INFEASIBLE kappa runs the full 4000
iterations before being rejected, and train_margin_auto tries up to 7 values.
Use --Ns to split the grid across processes.
"""

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLOCKLESS = os.path.join(os.path.dirname(HERE), "clockless")
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, CLOCKLESS)

from scale_study import make_support
from improve_capacity import train_margin_auto, n_fixed
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven

# loading values swept at every N; M = round(alpha*N), de-duplicated
ALPHAS = (0.0625, 0.125, 0.1875, 0.25, 0.3125, 0.375, 0.4375, 0.5,
          0.5625, 0.625, 0.6875, 0.75, 0.875, 1.0)


def measure(N, M, seed, trials, hds):
    d = min(N - 1, max(16, 4 * M))
    pats = np.random.default_rng(seed + M).choice([-1, 1],
                                                  size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    W, kappa = train_margin_auto(pats, mask, seed=seed)
    stored = n_fixed(W, pats)

    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(seed + 99)

    out = dict(N=N, M=M, alpha=M / N, fan_in=d, stored=stored, chi=chi,
               kappa=kappa)
    for hd in hds:
        ok = settled = 0
        for _ in range(trials):
            m = int(rng.integers(M))
            s = P01[m].copy()
            if hd:
                s[rng.choice(N, size=hd, replace=False)] ^= 1
            res, st = settle_event_driven(s, W, delays)
            settled += st
            ok += st and np.array_equal(res, P01[m])
        out[f"recall_hd{hd}"] = ok / trials
        out[f"settled_hd{hd}"] = settled / trials
    return out


def m_grid(N):
    ms = sorted({max(2, int(round(a * N))) for a in ALPHAS})
    return [m for m in ms if m <= N]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns", type=int, nargs="+", default=[32, 64, 128, 256])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--hds", type=int, nargs="+", default=[1, 3])
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = []
    print(f"{'N':>6}{'M':>5}{'alpha':>8}{'fan-in':>8}{'kappa':>7}{'stored':>10}"
          f"{'chi':>5}" + "".join(f"{'rec@'+str(h):>9}" for h in args.hds))
    print("-" * (49 + 9 * len(args.hds)))
    for N in args.Ns:
        for M in m_grid(N):
            try:
                r = measure(N, M, args.seed, args.trials, args.hds)
            except Exception as e:
                print(f"{N:>6}{M:>5}  failed: {type(e).__name__}: {e}")
                continue
            rows.append(r)
            print(f"{r['N']:>6}{r['M']:>5}{r['alpha']:>8.3f}{r['fan_in']:>8}"
                  f"{r['kappa']:>7.2f}{r['stored']:>7}/{r['M']:<2}{r['chi']:>5}"
                  + "".join(f"{100*r['recall_hd'+str(h)]:>8.0f}%"
                            for h in args.hds), flush=True)
        print()
    dest = args.out or os.path.join(HERE, "results",
                                    "nm_scaling_autokappa.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
