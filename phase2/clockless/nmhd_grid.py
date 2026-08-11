#!/usr/bin/env python3
"""
Recall as a function of all three knobs at once: N, M and corruption level.

Earlier sweeps varied one thing at a time, which hid the interaction: the
tolerable corruption depends on the LOADING alpha = M/N, not on M alone, and the
whole surface shifts with N. M is therefore scaled as a fraction of N here so
the comparison across sizes is meaningful.

Corruption is likewise expressed as a fraction of N. HD=8 is a mild perturbation
at N=256 and a severe one at N=64, so plotting against absolute HD makes bigger
networks look better than they are for the wrong reason.

Output feeds the heatmaps in paper/make_nmhd_figure.py.
"""

import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from scale_study import make_support
from improve_capacity import train_margin, n_fixed
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


def run_cell(N, M, hd_fracs, trials, seed):
    d = min(N - 1, max(16, 4 * M))
    pats = np.random.default_rng(seed + M).choice([-1, 1],
                                                  size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    t0 = time.time()
    W = train_margin(pats, mask, seed=seed)
    stored = n_fixed(W, pats)

    n, edges = graph_from_W(W)
    if not edges:
        return []
    colour = dsatur(n, edges)
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(seed + 99)

    out = []
    for hf in hd_fracs:
        hd = max(1, int(round(hf * N)))
        if hd >= N:
            continue
        ok = 0
        for _ in range(trials):
            m = int(rng.integers(M))
            s = P01[m].copy()
            s[rng.choice(N, size=hd, replace=False)] ^= 1
            res, st = settle_event_driven(s, W, delays)
            ok += st and np.array_equal(res, P01[m])
        out.append(dict(N=N, M=M, alpha=M / N, fan_in=d, stored=stored,
                        hd=hd, hd_frac=hd / N, recall=ok / trials))
    print(f"  N={N:>4} M={M:>3} (alpha={M/N:.3f}) stored={stored}/{M} "
          f"[{time.time()-t0:.0f}s]  " +
          " ".join(f"{100*r['recall']:.0f}%" for r in out), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns", type=int, nargs="+", default=[64, 128, 256])
    ap.add_argument("--alphas", type=float, nargs="+",
                    default=[0.0625, 0.125, 0.25, 0.375, 0.5])
    ap.add_argument("--hdfracs", type=float, nargs="+",
                    default=[0.01, 0.02, 0.03, 0.05, 0.08, 0.12,
                             0.16, 0.20, 0.25, 0.30, 0.40])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    print("corruption levels (as % of N): " +
          " ".join(f"{100*h:.0f}%" for h in args.hdfracs))
    rows = []
    for N in args.Ns:
        for a in args.alphas:
            M = max(2, int(round(a * N)))
            try:
                rows += run_cell(N, M, args.hdfracs, args.trials, args.seed)
            except Exception as e:
                print(f"  N={N} M={M} FAILED: {type(e).__name__}: {e}", flush=True)
    dest = os.path.join(HERE, "results", "nmhd_grid.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
