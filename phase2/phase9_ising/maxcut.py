#!/usr/bin/env python3
"""
PHASE 9 -- can the settling hardware solve MAX-CUT?

Everything before this treats the network as a MEMORY: patterns are trained in,
corrupted versions are recalled. Optimisation is a different use of the same
machine. A MAX-CUT instance maps onto an Ising model directly -- put s_i = +/-1
for which side of the cut vertex i is on, set W_ij = -w_ij for each graph edge,
and the Hopfield energy E = -1/2 s^T W s is (up to a constant) the negative cut
weight. Settling to a low-energy state IS finding a large cut.

Why this is worth testing rather than assuming:

  the case FOR   -- our scheduling result gives convergence to a fixed point in a
                    constant number of time slots (chi ~ 6) regardless of network
                    size. An Ising solver needs exactly that, and it needs it
                    without a clock. The coupling graph here is the problem graph,
                    so chi is the graph's chromatic number rather than something
                    we choose.
  the case AGAINST -- settling reliably means reaching *a* local minimum. Measured
                    on the memory side, ~90-95% of random starts reach a fixed
                    point that is not a stored pattern. For a memory that is a
                    failure mode; for optimisation it is the entire difficulty,
                    because a local minimum of the Ising energy is just a
                    locally-optimal cut.

So the question is NOT "does it converge" -- we know it does. It is "how good is
the cut it converges to, and is one-shot descent competitive with anything?"
Baselines are therefore essential: a random cut (floor), greedy, and simulated
annealing (what anyone would actually use).

No claim is made here about NP-hardness or asymptotic advantage. This measures
solution quality on small instances, which is the honest first step.
"""

import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CLK = os.path.join(os.path.dirname(HERE), "clockless")
sys.path.insert(0, ROOT); sys.path.insert(0, CLK)

from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


# ─── instances ───────────────────────────────────────────────────────────────

def random_graph(n, p, rng, weighted=False):
    """Erdos-Renyi G(n,p). Returns a symmetric weight matrix."""
    A = (rng.random((n, n)) < p).astype(float)
    A = np.triu(A, 1)
    if weighted:
        A = A * rng.integers(1, 11, size=A.shape)
    return A + A.T


def cut_weight(A, s):
    """Total weight of edges crossing the cut defined by s in {-1,+1}^n."""
    return float(np.sum(A * (1 - np.outer(s, s))) / 4.0)


# ─── solvers ─────────────────────────────────────────────────────────────────

def solve_random(A, rng, restarts):
    return max(cut_weight(A, rng.choice([-1, 1], size=len(A))) for _ in range(restarts))


def solve_greedy(A, rng, restarts):
    """Assign vertices in random order to whichever side cuts more weight."""
    n = len(A)
    best = 0.0
    for _ in range(restarts):
        s = np.zeros(n)
        for v in rng.permutation(n):
            # placing v opposite its already-placed neighbours gains their weight
            gain = float(A[v] @ s)
            s[v] = -1.0 if gain > 0 else 1.0
        best = max(best, cut_weight(A, s))
    return best


def solve_anneal(A, rng, restarts, sweeps=300):
    """Single-flip simulated annealing -- the honest baseline."""
    n = len(A)
    best = 0.0
    for _ in range(restarts):
        s = rng.choice([-1.0, 1.0], size=n)
        T0, T1 = float(np.abs(A).sum()) / max(n, 1), 1e-3
        for k in range(sweeps):
            T = T0 * (T1 / T0) ** (k / max(1, sweeps - 1))
            for v in rng.permutation(n):
                # flipping v changes the cut by 2 * s_v * (A_v . s) / 2
                delta = float(s[v] * (A[v] @ s))
                if delta > 0 or rng.random() < np.exp(delta / max(T, 1e-9)):
                    s[v] = -s[v]
        best = max(best, cut_weight(A, s))
    return best


def solve_settle(A, rng, restarts):
    """Our clockless settling, run as an Ising solver.

    W = -A makes the Hopfield energy the negative cut weight, so descending the
    energy is maximising the cut. Delays come from a DSATUR colouring of the
    PROBLEM graph -- for optimisation the coupling graph is given by the instance
    rather than chosen by us, so chi is a property of the input.
    """
    W = -A
    n, edges = graph_from_W(W)
    if not edges:
        return 0.0, 1, 0.0
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]
    best, settled = 0.0, 0
    for _ in range(restarts):
        s0 = rng.integers(0, 2, size=n).astype(np.int8)
        out, ok = settle_event_driven(s0, W, delays)
        settled += ok
        best = max(best, cut_weight(A, 2.0 * out.astype(float) - 1.0))
    return best, chi, settled / restarts


# ─── experiment ──────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[20, 40, 60])
    ap.add_argument("--p", type=float, default=0.3)
    ap.add_argument("--instances", type=int, default=5)
    ap.add_argument("--restarts", type=int, default=20)
    ap.add_argument("--weighted", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print(f"MAX-CUT on G(n,{args.p}){' weighted' if args.weighted else ''}, "
          f"{args.instances} instances x {args.restarts} restarts each.")
    print("Cut weights normalised to the best value any method found on that")
    print("instance, then averaged -- 1.000 means it was never beaten.\n")
    print(f"{'n':>5}{'chi':>6}{'settled':>9}{'random':>9}{'greedy':>9}"
          f"{'anneal':>9}{'settle':>9}{'anneal_s':>10}{'settle_s':>10}{'speedup':>10}")
    print("-" * 86)

    rows = []
    for n in args.sizes:
        acc = {k: [] for k in ("random", "greedy", "anneal", "settle")}
        chis, setrates, secs = [], [], []
        for inst in range(args.instances):
            rng = np.random.default_rng(args.seed + 1000 * n + inst)
            A = random_graph(n, args.p, rng, args.weighted)
            # time every method, not just ours -- annealing does 300 sweeps per
            # restart against our single descent, so a quality tie at much lower
            # cost is the interesting outcome and an untimed comparison hides it
            res, tm = {}, {}
            for name, fn in (("random", solve_random), ("greedy", solve_greedy),
                             ("anneal", solve_anneal)):
                t0 = time.time(); res[name] = fn(A, rng, args.restarts)
                tm[name] = time.time() - t0
            t0 = time.time()
            res["settle"], chi, sr = solve_settle(A, rng, args.restarts)
            tm["settle"] = time.time() - t0
            secs.append(tm)
            chis.append(chi); setrates.append(sr)
            best = max(res.values()) or 1.0
            for k, v in res.items():
                acc[k].append(v / best)
        m = {k: float(np.mean(v)) for k, v in acc.items()}
        tmean = {k: float(np.mean([d[k] for d in secs])) for k in secs[0]}
        rows.append(dict(n=n, p=args.p, weighted=args.weighted,
                         chi=float(np.mean(chis)),
                         settle_rate=float(np.mean(setrates)),
                         seconds=tmean, **m))
        print(f"{n:>5}{np.mean(chis):>6.1f}{100*np.mean(setrates):>8.0f}%"
              f"{m['random']:>9.3f}{m['greedy']:>9.3f}{m['anneal']:>9.3f}"
              f"{m['settle']:>9.3f}{tmean['anneal']:>10.2f}{tmean['settle']:>10.3f}"
              f"{tmean['anneal']/max(tmean['settle'],1e-9):>9.0f}x", flush=True)

    print("-" * 86)
    print("random = floor, anneal = what you would actually use.")
    print("settle beating greedy would be interesting; beating anneal would be")
    print("surprising and should be checked before it is believed.")
    dest = os.path.join(HERE, "results", "maxcut.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
