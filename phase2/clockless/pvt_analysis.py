#!/usr/bin/env python3
"""
Does the schedule survive process/voltage/temperature variation?

This is the central objection to any clockless design: it rests on delay
relationships, and delays move with PVT. The scheduling rule says coupled
neurons must differ in delay VALUE, which suggests robustness (an ordering is
harder to break than an absolute value), but that has been an argument, not
evidence.

Two things are tested:

  1. ROBUSTNESS -- perturb every neuron's delay by a lognormal factor and sweep
     the spread. If settling degrades, the approach is fragile.
  2. MECHANISM  -- apply the same perturbation to the DEGENERATE schedule (a
     valid colouring with every delay equal, which settles 0%). Continuous
     variation almost surely makes all delays distinct, so if the rule is really
     about value distinctness, variation should RESCUE that design. If it does
     not, our explanation of the mechanism is wrong.

The simulator here is event-driven with real-valued delays -- an inertial-delay
model of the SystemVerilog `s <= #(d) s_next` semantics -- rather than the
periodic-firing approximation used elsewhere, because PVT makes delays
non-integer and the periodic model cannot represent that.
"""

import argparse, heapq, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import build_net
from schedule_hnn import graph_from_W, dsatur


def settle_event_driven(s0, W, delays, t_max=None):
    """Inertial-delay model of `s_settle[i] <= #(d_i) s_next[i]`.

    Each neuron continuously evaluates its function. When its target value
    differs from its current output it schedules a commit d_i later; if the
    target reverts before the commit fires, the pending commit is cancelled --
    which is what an inertial delay does, and what the NBA schedule does when
    s_next changes back.
    """
    n = len(s0)
    d = np.asarray(delays, dtype=float)
    t_max = t_max or 400.0 * d.max()
    s = s0.astype(np.int8).copy()
    bip = lambda x: 2.0 * x - 1.0

    pending = {}                      # neuron -> (fire_time, value)
    q = []                            # heap of (time, seq, neuron)
    seq = 0
    t = 0.0

    def targets():
        return (W @ bip(s) >= 0).astype(np.int8)

    tgt = targets()
    for i in np.nonzero(tgt != s)[0]:
        seq += 1
        pending[i] = (t + d[i], tgt[i])
        heapq.heappush(q, (t + d[i], seq, i))

    EPS = 1e-12
    while q:
        ft = q[0][0]
        if ft > t_max:
            return s, False
        t = ft
        # Commit EVERY event at this timestamp together, from one snapshot.
        # Popping them one at a time would serialise simultaneous commits and
        # silently turn any schedule into sequential async, which always
        # converges -- that would hide the very hazard being measured.
        batch = []
        while q and q[0][0] <= ft + EPS:
            _, _, i = heapq.heappop(q)
            if i in pending and abs(pending[i][0] - ft) <= EPS:
                batch.append(i)
        if not batch:
            continue
        for i in batch:
            s[i] = pending.pop(i)[1]
        tgt = targets()
        for j in np.nonzero(tgt != s)[0]:
            if j not in pending:
                seq += 1
                pending[j] = (t + d[j], tgt[j])
                heapq.heappush(q, (t + d[j], seq, j))
        for j in list(pending):       # cancel commits whose target reverted
            if tgt[j] == s[j]:
                del pending[j]
    return s, True


def run(W, pats, delays, rng, trials, hd, sigma):
    P01 = ((pats + 1) // 2).astype(np.int8)
    N = W.shape[0]
    settled = correct = 0
    for _ in range(trials):
        # independent variation draw per trial: each die is different
        dv = np.asarray(delays, float) * np.exp(rng.normal(0, sigma, size=N))
        m = int(rng.integers(len(pats)))
        s = P01[m].copy()
        if hd:
            s[rng.choice(N, size=hd, replace=False)] ^= 1
        out, ok = settle_event_driven(s, W, dv)
        settled += ok
        correct += ok and np.array_equal(out, P01[m])
    return settled / trials, correct / trials


def load_n16():
    """The max-prune N=16 network. Used because it is the one where the
    degenerate schedule demonstrably FAILS (63.6% settled, matching RTL), so the
    hazard being tested is actually present. Larger, lightly-loaded networks
    converge even under fully synchronous update and cannot exercise it."""
    W = np.load(os.path.join(ROOT, "phase1", "results", "truth_tables",
                             "pseudo_s_maxprune", "W_pruned.npy"))
    pats = np.random.default_rng(42).choice([-1, 1], size=(4, 16)).astype(float)
    return pats, W, 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--hd", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--n16", action="store_true",
                    help="use the max-prune N=16 network (the one where the "
                         "degenerate schedule actually fails)")
    args = ap.parse_args()

    if args.n16:
        pats, W, kept = load_n16()
        args.N, args.M = 16, 4
    else:
        pats, W, kept = build_net(args.N, args.M, args.degree, args.seed)
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    coloured = [colour[i] + 1 for i in range(n)]
    degenerate = [20] * n             # every delay equal: the failing case
    print(f"N={args.N} M={args.M} fan-in={args.degree} chi={chi} "
          f"fixed points {kept}/{args.M}")
    print(f"event-driven inertial-delay model, HD={args.hd}, "
          f"{args.trials} trials/point, fresh variation draw per trial")
    print()

    rng = np.random.default_rng(args.seed + 3)
    sigmas = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50]
    print(f"{'sigma':>8}{'spread(3s)':>12} | "
          f"{'coloured settled':>17}{'recall':>9} | "
          f"{'degenerate settled':>19}{'recall':>9}")
    print("-" * 80)
    for sg in sigmas:
        cs, cc = run(W, pats, coloured, np.random.default_rng(args.seed + 100),
                     args.trials, args.hd, sg)
        ds, dc = run(W, pats, degenerate, np.random.default_rng(args.seed + 100),
                     args.trials, args.hd, sg)
        spread = f"+/-{100*(np.exp(3*sg)-1):.0f}%" if sg else "none"
        print(f"{sg:>8.2f}{spread:>12} | {100*cs:>16.0f}%{100*cc:>8.0f}% | "
              f"{100*ds:>18.0f}%{100*dc:>8.0f}%")
    print("-" * 80)
    print()
    print("Column 3-4: does the coloured schedule survive PVT?")
    print("Column 5-6: does variation RESCUE the degenerate schedule? Continuous")
    print("            variation makes equal delays distinct with probability 1,")
    print("            so if the rule is about value distinctness it should.")


if __name__ == "__main__":
    main()
