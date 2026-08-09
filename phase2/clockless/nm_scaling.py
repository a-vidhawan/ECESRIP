#!/usr/bin/env python3
"""
N x M scaling: how many patterns can be stored, and how accurately recalled?

Two different questions that are easy to conflate:

  STORAGE  -- are all M patterns fixed points? A yes/no property of training.
  RECALL   -- starting from a corrupted pattern, does the network settle back
              onto the right one? A property of basin geometry.

Storage saturates abruptly; recall degrades smoothly and much earlier. The
useful capacity is set by recall, not storage, so both are reported.

Fan-in is chosen generously (min(N-1, max(16, 4M))) so that storage is not the
binding constraint -- the point here is to isolate how recall scales with the
loading alpha = M/N, not to re-measure the fan-in limit.
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


def measure(N, M, seed, trials, hds):
    d = min(N - 1, max(16, 4 * M))
    pats = np.random.default_rng(seed + M).choice([-1, 1],
                                                  size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    W = train_margin(pats, mask, seed=seed)
    stored = n_fixed(W, pats)

    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(seed + 99)

    out = dict(N=N, M=M, alpha=M / N, fan_in=d, stored=stored, chi=chi)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns", type=int, nargs="+", default=[32, 64, 128, 256])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--hds", type=int, nargs="+", default=[1, 3])
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = []
    print(f"{'N':>6}{'M':>5}{'alpha':>8}{'fan-in':>8}{'stored':>10}{'chi':>5}"
          + "".join(f"{'rec@'+str(h):>9}" for h in args.hds))
    print("-" * (42 + 9 * len(args.hds)))
    for N in args.Ns:
        for M in (8, 16, 24, 32, 40, 48, 56, 64, 80, 96):
            if M > N:
                break
            try:
                r = measure(N, M, args.seed, args.trials, args.hds)
            except Exception as e:
                print(f"{N:>6}{M:>5}  failed: {type(e).__name__}: {e}")
                continue
            rows.append(r)
            print(f"{r['N']:>6}{r['M']:>5}{r['alpha']:>8.3f}{r['fan_in']:>8}"
                  f"{r['stored']:>7}/{r['M']:<2}{r['chi']:>5}"
                  + "".join(f"{100*r['recall_hd'+str(h)]:>8.0f}%"
                            for h in args.hds), flush=True)
        print()
    dest = args.out or os.path.join(HERE, "results", "nm_scaling.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
