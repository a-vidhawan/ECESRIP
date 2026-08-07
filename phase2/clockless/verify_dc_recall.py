#!/usr/bin/env python3
"""
Does don't-care minimisation preserve the network's behaviour?

Leaving the off-region as don't-care lets espresso assign it whatever is
cheapest. That is what makes the LUT small -- and it is also a correctness
risk: the minimised neuron is NOT the threshold function any more off the care
set, so it can invent fixed points, destroy basins, or reintroduce oscillation.

Term counts alone do not settle the question. This rebuilds the network from
the espresso SOPs and re-measures settling and recall against the exact
threshold network, under the same graph-coloured async schedule.
"""

import argparse, itertools, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import build_net, care_rows, write_pla, ESPRESSO
from schedule_hnn import graph_from_W, dsatur


def espresso_sop(path):
    """Return list of cubes; each cube is a tuple of (index, required_bit)."""
    out = subprocess.run([ESPRESSO, path], capture_output=True, text=True,
                         timeout=1800)
    cubes = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith(".") or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or parts[1] != "1":
            continue
        cubes.append(tuple((i, c) for i, c in enumerate(parts[0]) if c != "-"))
    return cubes


def build_sop_net(W, pats, radius, tmp):
    """Minimise every neuron with don't-cares; return per-neuron (support, cubes)."""
    N = W.shape[0]
    funcs, total = [], 0
    for i in range(N):
        sup, d, rows = care_rows(i, W, pats, radius)
        if sup is None or d == 0:
            funcs.append((None, None)); continue
        p = os.path.join(tmp, f"n{i}.pla")
        write_pla(p, sup, d, rows, dc=True)
        cubes = espresso_sop(p)
        total += len(cubes)
        funcs.append((sup, cubes))
    return funcs, total


def sop_eval(funcs, i, s01):
    """Evaluate neuron i's minimised SOP on the 0/1 state vector."""
    sup, cubes = funcs[i]
    if sup is None:
        return s01[i]
    proj = s01[sup]
    for cube in cubes:
        if all(proj[j] == int(b) for j, b in cube):
            return 1
    return 0


def simulate(s01, W, delays, funcs=None, max_t=None):
    """Schedule-driven settling. funcs=None uses the exact threshold function."""
    d = np.asarray(delays)
    max_t = max_t or 40 * int(d.max())
    s = s01.copy()
    for t in range(1, max_t + 1):
        fire = np.nonzero(t % d == 0)[0]
        if fire.size == 0:
            continue
        if funcs is None:
            bip = 2.0 * s - 1.0
            nxt = (np.where(W[fire] @ bip >= 0, 1, 0)).astype(s.dtype)
        else:
            nxt = np.array([sop_eval(funcs, i, s) for i in fire], dtype=s.dtype)
        if np.array_equal(nxt, s[fire]):
            continue
        s[fire] = nxt
    # settled iff a full re-evaluation changes nothing
    if funcs is None:
        bip = 2.0 * s - 1.0
        stable = np.array_equal(np.where(W @ bip >= 0, 1, 0).astype(s.dtype), s)
    else:
        stable = np.array_equal(
            np.array([sop_eval(funcs, i, s) for i in range(len(s))], dtype=s.dtype), s)
    return s, bool(stable)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=256)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    pats, W, kept = build_net(args.N, args.M, args.degree, args.seed)
    print(f"N={args.N} M={args.M} fan-in={args.degree} radius={args.radius}  "
          f"exact-net fixed points {kept}/{args.M}")

    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]          # linear pool, distinct
    print(f"coupling graph: {len(edges)} edges, chi={chi}, delays 1..{chi}")

    tmp = tempfile.mkdtemp()
    funcs, total = build_sop_net(W, pats, args.radius, tmp)
    print(f"espresso SOPs: {total} product terms across {args.N} neurons "
          f"({total/args.N:.1f} avg)")
    print()

    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(args.seed + 1)

    print(f"{'test':>26}{'exact settled':>15}{'exact ok':>10}"
          f"{'SOP settled':>13}{'SOP ok':>9}{'agree':>8}")
    print("-" * 81)
    for hd in (0, 1, 3, 5):
        es = eo = ss = so = ag = 0
        for _ in range(args.trials):
            m = rng.integers(args.M)
            s = P01[m].copy()
            if hd:
                s[rng.choice(args.N, size=hd, replace=False)] ^= 1
            a, oka = simulate(s.copy(), W, delays, None)
            b, okb = simulate(s.copy(), W, delays, funcs)
            es += oka; eo += oka and np.array_equal(a, P01[m])
            ss += okb; so += okb and np.array_equal(b, P01[m])
            ag += np.array_equal(a, b)
        t = args.trials
        print(f"{'HD='+str(hd)+' from a pattern':>26}{es/t*100:>14.0f}%{eo/t*100:>9.0f}%"
              f"{ss/t*100:>12.0f}%{so/t*100:>8.0f}%{ag/t*100:>7.0f}%")

    # OUTSIDE the care set: espresso is free there, so this is where it can break
    es = eo = ss = so = ag = 0
    for _ in range(args.trials):
        s = rng.integers(0, 2, size=args.N).astype(np.int8)
        a, oka = simulate(s.copy(), W, delays, None)
        b, okb = simulate(s.copy(), W, delays, funcs)
        es += oka; ss += okb; ag += np.array_equal(a, b)
    t = args.trials
    print(f"{'uniform random (off-region)':>26}{es/t*100:>14.0f}%{'-':>9}"
          f"{ss/t*100:>12.0f}%{'-':>8}{ag/t*100:>7.0f}%")
    print()
    print("'agree' = minimised network reached the same state as the exact one.")
    print("Disagreement inside the operating region would be a real failure;")
    print("disagreement outside it is expected -- that region was declared free.")


if __name__ == "__main__":
    main()
