#!/usr/bin/env python3
"""
PHASE 9b -- is "compile-time" annealing noise actually annealing?

Lin's objection, restated: if the noise is baked into the logic functions and
those functions are only reprogrammed once per temperature step, then every
update round inside that step sees the SAME perturbation, whereas a real
annealer draws fresh noise every round.

That is a claim about dynamics, so it is measurable. This compares four ways of
supplying the noise, holding EVERYTHING else fixed (same instances, same
colour-parallel update order, same temperature schedule, same round budget):

  fresh    eta redrawn every round                    -- the p-bit / SA reference
  frozen   eta redrawn once per temperature step      -- the compile-time idea
  frozen_r frozen, but the state is re-randomised at  -- frozen + restarts, i.e.
           the start of each step                        one sample per redraw
  chaotic  eta_i is a deterministic parity hash of the -- costs no RNG and no
           current state, scaled by T                     reprogramming at all

Two numbers decide the argument:

  1. DWELL -- inside a frozen temperature step, how many rounds pass before the
     state stops moving? If the answer is small then the remaining rounds are
     doing no work and the round budget is a fiction; the true sample rate is
     the REPROGRAMMING rate, which is Lin's point sharpened.

  2. QUALITY per redraw -- if frozen matches fresh at equal numbers of noise
     redraws, the idea is sound and only the reprogramming mechanism is wrong
     (an engineering problem). If it loses at equal redraws too, the idea is
     wrong at the level of dynamics.

Cut weights are normalised per instance to the best value any method found, so
1.000 means "never beaten on this instance".
"""

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLK = os.path.join(os.path.dirname(HERE), "clockless")
sys.path.insert(0, CLK)

from schedule_hnn import graph_from_W, dsatur
from maxcut import random_graph, cut_weight, solve_anneal


def colour_classes(W):
    """Colour-parallel update order -- the same schedule the hardware runs."""
    n, edges = graph_from_W(W)
    col = dsatur(n, edges)
    chi = max(col.values()) + 1
    return [np.array([i for i in range(n) if col[i] == c]) for c in range(chi)]


def parity_hash(B, s):
    """eta direction as an XOR tree over the current state.

    This is the only noise source here that costs neither an RNG nor a
    reprogramming event: B is a fixed sparse +-1 support, so eta_i is the parity
    of a fixed subset of spins -- a handful of XOR gates per neuron, decided at
    synthesis time, yet producing a different perturbation every round because
    the state moved. Deterministic, but decorrelated from the local field.
    """
    return np.where((B @ ((s + 1) // 2)) % 2 == 0, 1.0, -1.0)


def run(A, mode, steps, rounds, rng, T0=None, T1=1e-3, track_dwell=False):
    """Anneal one instance. Returns (best cut, redraw count, dwell samples)."""
    W = -A
    n = len(A)
    classes = colour_classes(W)
    T0 = T0 if T0 is not None else float(np.abs(A).sum()) / max(n, 1)
    B = (rng.random((n, n)) < 3.0 / n).astype(np.int64)   # sparse XOR support
    s = rng.choice([-1.0, 1.0], size=n)
    best, redraws, dwell = cut_weight(A, s), 0, []

    for k in range(steps):
        T = T0 * (T1 / T0) ** (k / max(1, steps - 1))
        if mode in ("frozen", "frozen_r"):
            eta = T * rng.standard_normal(n)      # one reprogramming event
            redraws += 1
            if mode == "frozen_r":
                s = rng.choice([-1.0, 1.0], size=n)
        stuck = None
        for r in range(rounds):
            if mode == "fresh":
                eta = T * rng.standard_normal(n)  # a redraw every round
                redraws += 1
            prev = s.copy()
            for cls in classes:
                if mode == "chaotic":
                    eta = T * parity_hash(B, s)
                # every neuron in a colour class sees the same state, which is
                # exactly what committing them on a shared delay value does
                h = W[cls] @ s + eta[cls]
                s[cls] = np.where(h >= 0, 1.0, -1.0)
            best = max(best, cut_weight(A, s))
            if stuck is None and np.array_equal(s, prev):
                stuck = r + 1
        if track_dwell and mode == "frozen":
            dwell.append(stuck if stuck is not None else rounds + 1)
    return best, redraws, dwell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--p", type=float, default=0.3)
    ap.add_argument("--instances", type=int, default=12)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    MODES = ("fresh", "frozen", "frozen_r", "chaotic")
    print(f"MAX-CUT on G({args.n},{args.p}), {args.instances} instances")
    print(f"{args.steps} temperature steps x {args.rounds} rounds per step\n")

    acc = {m: [] for m in MODES}
    redraw = {m: [] for m in MODES}
    dwells = []
    for inst in range(args.instances):
        rng0 = np.random.default_rng(args.seed + inst)
        A = random_graph(args.n, args.p, rng0)
        res = {}
        for m in MODES:
            rng = np.random.default_rng(args.seed + 1000 + inst)
            cut, rd, dw = run(A, m, args.steps, args.rounds, rng,
                              track_dwell=(m == "frozen"))
            res[m] = cut; redraw[m].append(rd); dwells += dw
        # a proper SA baseline so "fresh" is not being graded on its own curve
        res["sa"] = solve_anneal(A, np.random.default_rng(args.seed + inst), 1,
                                 sweeps=args.steps * args.rounds)
        best = max(res.values()) or 1.0
        for m in MODES:
            acc[m].append(res[m] / best)
        acc.setdefault("sa", []).append(res["sa"] / best)

    print(f"{'mode':<10}{'cut / best':>12}{'noise redraws':>16}"
          f"{'  (= reprogramming events)'}")
    print("-" * 64)
    for m in MODES + ("sa",):
        rd = f"{np.mean(redraw[m]):.0f}" if m in redraw else "-"
        print(f"{m:<10}{np.mean(acc[m]):>12.4f}{rd:>16}")
    print("-" * 64)

    d = np.array(dwells, dtype=float)
    print(f"\nDWELL inside a frozen temperature step ({len(d)} steps observed):")
    print(f"  state stops changing after a median of {np.median(d):.0f} rounds "
          f"(mean {d.mean():.1f}) out of {args.rounds}")
    frac = float((d <= args.rounds).mean())
    print(f"  {100*frac:.0f}% of steps reach a fixed point before the budget "
          f"is spent -- those rounds do no work")
    print(f"  useful fraction of the round budget: "
          f"{np.mean(np.minimum(d, args.rounds)) / args.rounds:.2f}")

    dest = os.path.join(HERE, "results", "frozen_noise.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(dict(n=args.n, p=args.p, instances=args.instances,
                   steps=args.steps, rounds=args.rounds,
                   quality={m: float(np.mean(acc[m])) for m in acc},
                   redraws={m: float(np.mean(redraw[m])) for m in redraw},
                   dwell_median=float(np.median(d)), dwell_mean=float(d.mean()),
                   dwell_useful_fraction=float(
                       np.mean(np.minimum(d, args.rounds)) / args.rounds)),
              open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
