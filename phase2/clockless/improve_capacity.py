#!/usr/bin/env python3
"""
Raise the pattern capacity of a fan-in-limited Hopfield network.

Capacity here is not a property of the network so much as of the TRAINING rule.
The existing trainer (`retrain_pseudoinverse_masked`) solves an exact
least-squares fit per neuron and then symmetrises, and symmetrisation destroys
the fit -- which is why fan-in has to be roughly 3M before all patterns survive
as fixed points. Fan-in is the dominant area cost, so this is expensive.

A margin-maximising rule does better, because it never relies on an exact fit:
it enforces xi_i^mu * h_i^mu >= kappa for every pattern and neuron, maintains
symmetry throughout rather than at the end, and only stops when the constraints
hold. This is the masked, symmetric form of the classical perceptron/minover
learning rule for associative memory.

Reports the largest M storable at each fan-in, for both rules, plus recall.
"""

import argparse, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from phase1.pruning import retrain_pseudoinverse_masked
from scale_study import make_support
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


def train_margin(pats, mask, kappa=1.0, iters=4000, lr=0.05, seed=0):
    """Masked, symmetric, margin-maximising learning.

    Symmetry is restored after every sweep rather than once at the end, so the
    solution the rule converges to already satisfies the constraint it will be
    deployed under -- unlike a least-squares fit that is symmetrised afterwards.
    """
    M, N = pats.shape
    rng = np.random.default_rng(seed)
    W = np.zeros((N, N))
    mask = (mask > 0).astype(float)
    np.fill_diagonal(mask, 0.0)

    # scale so an unnormalised Hebbian start is on the right order
    W = (pats.T @ pats) / N
    np.fill_diagonal(W, 0.0)
    W *= mask
    W = (W + W.T) / 2.0 * mask

    for it in range(iters):
        H = pats @ W.T                      # (M,N) local fields
        marg = H * pats                     # margin per (pattern, neuron)
        viol = marg < kappa
        if not viol.any():
            break
        # gradient step only on violated constraints, restricted to the mask
        upd = np.zeros_like(W)
        for m in range(M):
            bad = np.nonzero(viol[m])[0]
            if bad.size == 0:
                continue
            upd[bad, :] += lr * np.outer(pats[m][bad], pats[m])
        upd *= mask
        W += upd
        W = (W + W.T) / 2.0                 # keep symmetric at every step
        W *= mask
        np.fill_diagonal(W, 0.0)
        n = np.abs(W).max()
        if n > 0:
            W /= n                          # renormalise; margin is scale-free
    return W


def n_fixed(W, pats):
    return sum(np.array_equal(np.where(W @ pats[m] >= 0, 1, -1), pats[m])
               for m in range(len(pats)))


def recall_rate(W, pats, hd, trials, rng):
    """Recall under the graph-coloured clockless schedule."""
    N = W.shape[0]
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    ok = 0
    for _ in range(trials):
        m = int(rng.integers(len(pats)))
        s = P01[m].copy()
        if hd:
            s[rng.choice(N, size=hd, replace=False)] ^= 1
        out, settled = settle_event_driven(s, W, delays)
        ok += settled and np.array_equal(out, P01[m])
    return ok / trials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--fanins", type=int, nargs="+", default=[8, 12, 16, 24, 32])
    ap.add_argument("--Ms", type=int, nargs="+",
                    default=[2, 4, 6, 8, 12, 16, 20, 24, 32])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--hd", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    N = args.N
    rng = np.random.default_rng(args.seed)
    print(f"N={N}: largest M with ALL patterns stored as fixed points")
    print(f"{'fan-in':>8}{'lstsq+sym':>12}{'margin':>9}{'gain':>7}"
          f"{'  recall@HD=' + str(args.hd) + ' (margin, at its M_max)':>40}")
    print("-" * 76)
    rows = []
    for d in args.fanins:
        best_old = best_new = 0
        rec = float("nan")
        for M in args.Ms:
            if M > N // 2:
                break
            pats = np.random.default_rng(args.seed + M).choice(
                [-1, 1], size=(M, N)).astype(float)
            mask = make_support(N, d, "regular", np.random.default_rng(args.seed))
            Wo = retrain_pseudoinverse_masked(pats, mask)
            if n_fixed(Wo, pats) == M:
                best_old = M
            Wn = train_margin(pats, mask, seed=args.seed)
            if n_fixed(Wn, pats) == M:
                best_new = M
                rec = recall_rate(Wn, pats, args.hd, args.trials,
                                  np.random.default_rng(args.seed + 1))
        gain = f"{best_new/best_old:.1f}x" if best_old else "--"
        print(f"{d:>8}{best_old:>12}{best_new:>9}{gain:>7}{100*rec:>38.0f}%")
        rows.append(dict(fan_in=d, m_lstsq=best_old, m_margin=best_new,
                         recall=rec))
    print("-" * 76)
    import json
    dest = os.path.join(HERE, "results", "capacity_improved.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
