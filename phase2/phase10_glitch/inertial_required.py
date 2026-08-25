#!/usr/bin/env python3
"""
PHASE 10c -- is the inertial behaviour part of the MECHANISM, not a mitigation?

The commensurability test came back 100% for every delay pool, so realignment is
not what made the N=32 reference settle 50%. That leaves one difference between
the Python model and the RTL, and it is not a small one.

  Python model   a pending commit is CANCELLED if the node's target reverts
                 before the commit fires.  That is inertial delay.
  RTL            `s_settle[i] <= #(d_i) s_next[i]` queues every event and
                 delivers all of them.  That is transport delay.

They are different machines. This runs the same networks, the same schedules and
the same initial states through both and reports how often each reaches a fixed
point.

If transport loses, then the inertial behaviour is not a hazard mitigation that
can be bolted on or left off -- it is a requirement of the scheduling scheme,
and it belongs in the claims. It would also sharpen the distinction over
phase-shifted-clock implementations, because a clocked node SAMPLES its input at
an edge; it has no notion of cancelling a superseded transition.
"""

import argparse, heapq, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLK = os.path.join(os.path.dirname(HERE), "clockless")
sys.path.insert(0, CLK)

from improve_capacity import train_margin_auto
from scale_study import make_support
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


def settle_transport(s0, W, delays, t_max=None):
    """Same schedule, transport semantics: nothing is ever cancelled.

    Deliberately a copy of settle_event_driven with the cancellation removed and
    the one-pending-commit-per-node restriction lifted, so the only difference
    between the two functions is the thing under test.
    """
    n = len(s0)
    d = np.asarray(delays, dtype=float)
    t_max = t_max or 400.0 * d.max()
    s = s0.astype(np.int8).copy()
    bip = lambda x: 2.0 * x - 1.0
    q, seq, t = [], 0, 0.0

    def targets():
        return (W @ bip(s) >= 0).astype(np.int8)

    for i in np.nonzero(targets() != s)[0]:
        seq += 1
        heapq.heappush(q, (d[i], seq, i, int(targets()[i])))
    EPS = 1e-12
    while q:
        ft = q[0][0]
        if ft > t_max:
            return s, False
        t = ft
        batch = []
        while q and q[0][0] <= ft + EPS:
            _, _, i, v = heapq.heappop(q)
            batch.append((i, v))
        changed = False
        for i, v in batch:
            if s[i] != v:
                s[i] = v; changed = True
        if not changed:
            continue
        tgt = targets()
        for j in np.nonzero(tgt != s)[0]:
            seq += 1
            heapq.heappush(q, (t + d[j], seq, j, int(tgt[j])))
    return s, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, nargs="+", default=[16, 32, 64, 128, 256])
    ap.add_argument("--M", type=int, default=8)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--nets", type=int, default=3)
    args = ap.parse_args()

    print("Fraction of random initial states reaching a fixed point.")
    print("Identical networks, identical schedules, identical starting states.\n")
    hdr = (f"{'N':>6}{'chi':>5}{'edges':>7}{'INERTIAL (cancels)':>21}"
           f"{'TRANSPORT (queues all)':>25}")
    print(hdr); print("-" * len(hdr))
    rows = []
    for N in args.N:
        ine, tra, chis, eds = [], [], [], []
        for k in range(args.nets):
            rng = np.random.default_rng(11 + k)
            pats = rng.choice([-1, 1], size=(args.M, N)).astype(float)
            mask = make_support(N, min(N - 1, args.degree), "regular",
                                np.random.default_rng(11 + k))
            W, _ = train_margin_auto(pats, mask, seed=11 + k)
            n, edges = graph_from_W(W)
            col = dsatur(n, edges)
            chi = max(col.values()) + 1
            d = [(col[i] + 1) * 10 for i in range(N)]
            starts = [rng.integers(0, 2, size=N).astype(np.int8)
                      for _ in range(args.trials)]
            ine.append(np.mean([settle_event_driven(s.copy(), W, d)[1]
                                for s in starts]))
            tra.append(np.mean([settle_transport(s.copy(), W, d)[1]
                                for s in starts]))
            chis.append(chi); eds.append(len(edges))
        rows.append(dict(N=N, chi=float(np.mean(chis)), edges=float(np.mean(eds)),
                         inertial=float(np.mean(ine)),
                         transport=float(np.mean(tra))))
        print(f"{N:>6}{np.mean(chis):>5.0f}{np.mean(eds):>7.0f}"
              f"{100*np.mean(ine):>20.0f}%{100*np.mean(tra):>24.0f}%", flush=True)
    print("-" * len(hdr))
    dest = os.path.join(HERE, "results", "inertial_required.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
