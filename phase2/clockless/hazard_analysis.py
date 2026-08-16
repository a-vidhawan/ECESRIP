#!/usr/bin/env python3
"""
PHASE 7 -- do logic hazards break settling?

Raised by the advisor, and correctly framed: the differentiated delays exist to
prevent OSCILLATION (two coupled neurons committing together). Hazards are a
separate problem. A hazard is a transient glitch on a neuron's combinational
output caused by unequal arrival times through the SOP, and it can be latched
even though the steady-state value is correct.

Every result in this project so far assumes hazards away. The generated RTL is
`assign s_next[i] = (cube)|(cube)|...` -- zero-delay combinational logic -- so a
glitch has zero width in simulation and can never reach the state element. Both
Python simulators do the same. So the honest position is that we have never
tested this.

Two arguments, and they point opposite ways:

  benign   -- this is an attractor system; a transient wrong value is just a
              perturbation, and if the state stays inside the basin the dynamics
              pull it back. Basins are wide (>=90% recall at 19% corruption at
              N=256), so there is a lot of slack to absorb.
  harmful  -- the convergence guarantee assumes each commit is a CORRECT
              evaluation of the neuron's function. A glitched commit breaks the
              monotonic energy descent the whole scheduling result rests on, and
              propagates to neighbours from a state that never legitimately
              existed.

This is the cheap test that decides whether the expensive gate-level study is
needed: inject spurious commits at a controlled rate and see whether recall
degrades gracefully or falls off a cliff. It does NOT estimate the real glitch
rate -- only the sensitivity to one.
"""

import argparse, heapq, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from scale_study import make_support
from improve_capacity import train_margin_auto, n_fixed
from schedule_hnn import graph_from_W, dsatur


def settle_with_glitches(s0, W, delays, glitch_p=0.0, rng=None, t_max=None):
    """Event-driven settling in which a commit may latch the WRONG value.

    Same inertial-delay model as pvt_analysis.settle_event_driven -- all events
    at one timestamp commit together from a shared snapshot -- with one addition:
    with probability glitch_p a commit latches the inverse of the computed value.
    The neuron re-evaluates afterwards, so a glitch is self-correcting in the
    sense that a correction gets scheduled; the question is whether the network
    has already moved somewhere else by then.
    """
    n = len(s0)
    d = np.asarray(delays, dtype=float)
    t_max = t_max or 400.0 * d.max()
    s = s0.astype(np.int8).copy()
    rng = rng or np.random.default_rng(0)
    bip = lambda x: 2.0 * x - 1.0

    pending, q, seq, t = {}, [], 0, 0.0

    def targets():
        return (W @ bip(s) >= 0).astype(np.int8)

    tgt = targets()
    for i in np.nonzero(tgt != s)[0]:
        seq += 1
        pending[i] = (t + d[i], tgt[i])
        heapq.heappush(q, (t + d[i], seq, i))

    EPS = 1e-12
    glitches = commits = 0
    while q:
        ft = q[0][0]
        if ft > t_max:
            return s, False, glitches, commits
        t = ft
        batch = []
        while q and q[0][0] <= ft + EPS:
            _, _, i = heapq.heappop(q)
            if i in pending and abs(pending[i][0] - ft) <= EPS:
                batch.append(i)
        if not batch:
            continue
        for i in batch:
            val = pending.pop(i)[1]
            commits += 1
            if glitch_p and rng.random() < glitch_p:
                val = np.int8(1 - val)       # latched a transient wrong value
                glitches += 1
            s[i] = val
        tgt = targets()
        for j in np.nonzero(tgt != s)[0]:
            if j not in pending:
                seq += 1
                pending[j] = (t + d[j], tgt[j])
                heapq.heappush(q, (t + d[j], seq, j))
        for j in list(pending):
            if tgt[j] == s[j]:
                del pending[j]
    return s, True, glitches, commits


def run(N, M, hd, glitch_ps, trials, seed):
    d = min(N - 1, max(16, 4 * M))
    pats = np.random.default_rng(seed + M).choice([-1, 1], size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    W, kappa = train_margin_auto(pats, mask, seed=seed)
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)

    out = []
    for p in glitch_ps:
        rng = np.random.default_rng(seed + 500)
        ok = settled = gl = com = 0
        for _ in range(trials):
            m = int(rng.integers(M))
            s = P01[m].copy()
            s[rng.choice(N, size=hd, replace=False)] ^= 1
            res, st, g, cm = settle_with_glitches(s, W, delays, p, rng)
            settled += st
            gl += g
            com += cm
            ok += st and np.array_equal(res, P01[m])
        out.append(dict(N=N, M=M, hd=hd, kappa=kappa, glitch_p=p,
                        recall=ok / trials, settled=settled / trials,
                        mean_glitches=gl / trials, mean_commits=com / trials))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=["64:8", "128:16", "256:32"])
    ap.add_argument("--hd", type=int, default=0,
                    help="absolute HD; 0 means use 10%% of N so that "
                         "settling takes many commits")
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    # p must go high enough to actually stress the system: settling takes only a
    # handful of commits, so a low p injects well under one glitch per trial and
    # measures nothing. mean_commits is reported so the stress level is visible.
    ps = [0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70]
    rows = []
    print("Spurious-commit sensitivity (HD = 10% of N unless overridden).")
    print("glitch_p = probability that any single commit latches the wrong value.\n")
    for case in args.cases:
        N, M = (int(x) for x in case.split(":"))
        hd = args.hd or max(3, N // 10)
        r = run(N, M, hd, ps, args.trials, args.seed)
        rows += r
        print(f"N={N} M={M} (kappa={r[0]['kappa']}, HD={hd})")
        print("  glitch_p: " + "".join(f"{x['glitch_p']:>8.3f}" for x in r))
        print("    recall: " + "".join(f"{100*x['recall']:>7.0f}%" for x in r))
        print("   settled: " + "".join(f"{100*x['settled']:>7.0f}%" for x in r))
        print("  commits/: " + "".join(f"{x['mean_commits']:>8.1f}" for x in r))
        print("  glitches: " + "".join(f"{x['mean_glitches']:>8.1f}" for x in r),
              flush=True)
        print()
    dest = os.path.join(HERE, "results", "hazard_sensitivity.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
