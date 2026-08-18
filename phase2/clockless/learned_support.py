#!/usr/bin/env python3
"""
Does choosing the sparse support WITH KNOWLEDGE of the patterns buy capacity?

Everywhere else in phase2 the support is imposed BEFORE training:
`make_support(N, d, "regular", rng)` builds a random d-regular graph that never
looks at the patterns, and `train_margin_auto` then fits weights inside that
fixed mask (it can never add an edge). Fan-in d is the dominant hardware cost --
a neuron with d inputs needs a 2^d LUT -- so the obvious question is whether a
pattern-aware support stores more patterns at the SAME d. If it did, capacity
would be free area-wise.

Five support strategies are compared at matched fan-in:

  regular      random d-regular, pattern-blind          (the incumbent baseline)
  correlation  keep the d edges per neuron with the largest |sum_mu xi_i xi_j|
  projection   keep the d largest |P_ij| of the DENSE pseudoinverse projector
               P = X^T (X X^T)^-1 X, i.e. sparsify the ideal unconstrained
               solution rather than the raw second moment        (my 5th idea)
  greedy       grow the support in 4 rounds; each round re-scores every candidate
               edge by a hinge-weighted correlation that only counts (pattern,
               neuron) constraints whose margin is currently violated, so edges
               are added where the margin deficit actually is
  ring         circulant nearest-neighbour support -- a KNOWN-BAD control,
               included to prove the comparison can detect a bad support

All five go through the same degree-constrained selector so every strategy is
exactly (or near-exactly) d-regular; achieved mean/max degree is printed and
stored so a fan-in advantage cannot masquerade as a capacity win. Every strategy
gets the identical trainer, the identical kappa ladder, and the identical seeds.

FINDING (see results/learned_support.json, and the report printed at the end):
pattern-aware support does NOT beat the pattern-blind random d-regular baseline.
Across N in {64,128} and d in {16,32}, correlation/projection/greedy tie with or
lose to `regular` on max storable M, and are no better on recall at HD = 5%/10%.
The ring control DOES lose clearly, which shows the measurement is sensitive
enough to see a bad support -- so the null result is not an artefact of a blunt
instrument. The interpretation: for random unbiased patterns the empirical
correlations carry no reusable structure (all |sum_mu xi_i xi_j| are O(sqrt(M))
noise), so "pattern-aware" selection is just a different random graph, while the
margin trainer is what actually does the work. Pattern-aware support would only
be expected to pay off for structured/correlated pattern sets.

Run:  python3 learned_support.py            (~15 min)
      python3 learned_support.py --quick    (smaller sweep)
"""

import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from scale_study import make_support
from improve_capacity import train_margin_auto, n_fixed, recall_rate

# One kappa ladder for every strategy. Shorter than improve_capacity's default
# (7 values) purely for runtime; it is the SAME ladder for all five strategies,
# so no strategy is tuned harder than another.
KAPPAS = (1.0, 0.5, 0.3, 0.1)


# ── degree-constrained symmetric edge selection ─────────────────────────────

def select_dregular(score, d, rng):
    """Pick a symmetric, zero-diagonal mask of per-row degree ~d, taking the
    highest-scoring edges subject to a hard degree cap of d on both endpoints.

    Greedy b-matching on the sorted candidate list, then a repair pass that
    pairs up any leftover deficit nodes (best-scoring admissible pair first) so
    the achieved degree matches the pattern-blind baselines. Ties are broken by
    a tiny deterministic jitter so a degenerate score matrix does not collapse
    onto a structured (e.g. banded) graph.
    """
    N = score.shape[0]
    sc = np.array(score, dtype=float)
    sc = sc + rng.random(sc.shape) * 1e-9
    sc = (sc + sc.T) / 2.0
    iu = np.triu_indices(N, 1)
    vals = sc[iu]
    order = np.argsort(-vals)
    adj = [set() for _ in range(N)]
    for idx in order:
        i, j = int(iu[0][idx]), int(iu[1][idx])
        if len(adj[i]) < d and len(adj[j]) < d:
            adj[i].add(j); adj[j].add(i)
    # repair: connect deficit nodes to each other, best score first
    for _ in range(4 * N):
        need = [i for i in range(N) if len(adj[i]) < d]
        if len(need) < 2:
            break
        best, bs = None, -np.inf
        for a in range(len(need)):
            for b in range(a + 1, len(need)):
                i, j = need[a], need[b]
                if j in adj[i]:
                    continue
                if sc[i, j] > bs:
                    bs, best = sc[i, j], (i, j)
        if best is None:
            break
        i, j = best
        adj[i].add(j); adj[j].add(i)
    mask = np.zeros((N, N))
    for i in range(N):
        for j in adj[i]:
            mask[i, j] = mask[j, i] = 1.0
    np.fill_diagonal(mask, 0.0)
    return mask


# ── strategies ──────────────────────────────────────────────────────────────

def support_correlation(pats, d, rng):
    C = np.abs(pats.T @ pats)
    np.fill_diagonal(C, -np.inf)
    return select_dregular(C, d, rng)


def support_projection(pats, d, rng):
    """|P_ij| of the dense pseudoinverse projector -- the unconstrained ideal
    weight matrix. Sparsifying the ideal solution is a strictly stronger use of
    the patterns than the raw second moment."""
    X = np.asarray(pats, float)
    G = X @ X.T
    P = X.T @ np.linalg.pinv(G) @ X
    S = np.abs(P)
    np.fill_diagonal(S, -np.inf)
    return select_dregular(S, d, rng)


def support_greedy(pats, d, rng, rounds=4, kappa=1.0):
    """Grow the support in `rounds` stages. At each stage a Hebbian weight
    matrix restricted to the current mask gives local fields; the hinge
    violation v_i^mu = max(0, kappa - marg_i^mu / scale_i) says where margin is
    still missing, and every candidate edge is scored by

        s_ij = | sum_mu (v_i^mu + v_j^mu) * xi_i^mu * xi_j^mu |

    i.e. the correlation reweighted towards the constraints that are currently
    violated. That is the cheap surrogate for 'the edge that most reduces total
    margin violation': it is the magnitude of the first-order change in the
    violated margins from switching edge (i,j) on with its best sign.
    Round 1 (empty mask, all v = 1) reduces to plain correlation; later rounds
    diverge from it.
    """
    M, N = pats.shape
    mask = np.zeros((N, N))
    for r in range(1, rounds + 1):
        cap = int(round(d * r / rounds))
        if mask.any():
            W = (pats.T @ pats) / N * mask
            np.fill_diagonal(W, 0.0)
            W = (W + W.T) / 2.0 * mask
            H = pats @ W.T
            scale = np.abs(H).mean(axis=0)
            scale[scale <= 0] = 1.0
            marg = (H * pats) / scale
            v = np.maximum(0.0, kappa - marg)
        else:
            v = np.ones((M, N))
        # s_ij = |sum_mu (v_i + v_j) xi_i xi_j| = |(v*X)^T X + X^T (v*X)|_ij
        A = (v * pats).T @ pats
        S = np.abs(A + A.T)
        np.fill_diagonal(S, -np.inf)
        # keep already-chosen edges by scoring them at the top
        S = np.where(mask > 0, S.max() + 1.0, S)
        mask = select_dregular(S, cap, rng)
    return mask


def build_support(kind, N, d, pats, seed):
    rng = np.random.default_rng(seed)
    if kind == "regular":
        return make_support(N, d, "regular", rng)
    if kind == "ring":
        return make_support(N, d, "ring", rng)
    if kind == "correlation":
        return support_correlation(pats, d, rng)
    if kind == "projection":
        return support_projection(pats, d, rng)
    if kind == "greedy":
        return support_greedy(pats, d, rng)
    raise ValueError(kind)


STRATEGIES = ["regular", "correlation", "projection", "greedy", "ring"]


# ── sweep ───────────────────────────────────────────────────────────────────

def m_grid(d, N):
    base = [d // 4, d // 3, d // 2, int(d * 0.65), int(d * 0.8), d,
            int(d * 1.25), int(d * 1.5)]
    out = sorted({max(2, m) for m in base if m <= N // 2})
    return out


def run_cell(N, d, kind, seed, trials, hds, verbose=True):
    """Sweep M upward for one (N, d, strategy); return the largest M with all
    patterns stored, plus recall at that M."""
    best = dict(N=N, d=d, strategy=kind, max_M=0, kappa=None,
                mean_degree=None, max_degree=None, min_degree=None,
                recall={}, support_s=0.0, train_s=0.0)
    fails = 0
    for M in m_grid(d, N):
        pats = np.random.default_rng(seed * 1000 + M).choice(
            [-1, 1], size=(M, N)).astype(float)
        t0 = time.time()
        mask = build_support(kind, N, d, pats, seed)
        ts = time.time() - t0
        deg = mask.sum(axis=1)
        t0 = time.time()
        W, kap = train_margin_auto(pats, mask, kappas=KAPPAS, seed=seed)
        tt = time.time() - t0
        nf = n_fixed(W, pats)
        if verbose:
            print(f"    M={M:<3} deg mean/max/min={deg.mean():.1f}/"
                  f"{int(deg.max())}/{int(deg.min())} kappa={kap} "
                  f"fixed={nf}/{M} ({ts:.1f}s+{tt:.1f}s)", flush=True)
        if nf == M:
            fails = 0
            best.update(max_M=M, kappa=kap,
                        mean_degree=float(deg.mean()),
                        max_degree=int(deg.max()),
                        min_degree=int(deg.min()),
                        support_s=round(ts, 2), train_s=round(tt, 2))
            best["_W"], best["_pats"] = W, pats
        else:
            fails += 1
            if fails >= 2:
                break
    if "_W" in best:
        W, pats = best.pop("_W"), best.pop("_pats")
        for hd in hds:
            r = recall_rate(W, pats, hd, trials, np.random.default_rng(seed + 7))
            best["recall"][f"hd{hd}"] = r
    best.pop("_W", None); best.pop("_pats", None)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns", type=int, nargs="+", default=[64, 128])
    ap.add_argument("--ds", type=int, nargs="+", default=[16, 32])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results",
                                                  "learned_support.json"))
    args = ap.parse_args()
    if args.quick:
        args.Ns, args.ds, args.trials = [64], [16], 20

    t_start = time.time()
    rows = []
    for N in args.Ns:
        hds = [max(1, int(round(f * N))) for f in (0.05, 0.10)]
        for d in args.ds:
            print(f"\n=== N={N} d={d}  (HD = {hds[0]}, {hds[1]}) ===", flush=True)
            for kind in STRATEGIES:
                print(f"  [{kind}]", flush=True)
                r = run_cell(N, d, kind, args.seed, args.trials, hds)
                rows.append(r)

    # ── report ──
    print("\n" + "=" * 92)
    print("MAX M WITH ALL PATTERNS STORED, and recall at HD=5%/10% of N "
          f"({args.trials} trials, seed {args.seed})")
    print("=" * 92)
    hdr = (f"{'N':>4}{'d':>4}  {'strategy':<12}{'maxM':>6}{'vs reg':>8}"
           f"{'kappa':>7}{'deg mean':>10}{'deg max':>9}{'deg min':>9}"
           f"{'rec@5%':>9}{'rec@10%':>9}")
    print(hdr); print("-" * len(hdr))
    for N in args.Ns:
        for d in args.ds:
            cell = [r for r in rows if r["N"] == N and r["d"] == d]
            if not cell:
                continue
            base = next((r["max_M"] for r in cell
                         if r["strategy"] == "regular"), 0)
            for r in cell:
                rec = r["recall"]
                ks = sorted(rec.keys(), key=lambda s: int(s[2:]))
                v = [rec[k] for k in ks] + [float("nan")] * 2
                delta = (f"{r['max_M']-base:+d}" if base else "--")
                print(f"{r['N']:>4}{r['d']:>4}  {r['strategy']:<12}"
                      f"{r['max_M']:>6}{delta:>8}{str(r['kappa']):>7}"
                      f"{(r['mean_degree'] or 0):>10.1f}"
                      f"{(r['max_degree'] or 0):>9}{(r['min_degree'] or 0):>9}"
                      f"{100*v[0]:>8.0f}%{100*v[1]:>8.0f}%")
            print()

    # honest verdict
    wins = losses = ties = 0
    for N in args.Ns:
        for d in args.ds:
            cell = {r["strategy"]: r for r in rows
                    if r["N"] == N and r["d"] == d}
            if "regular" not in cell:
                continue
            b = cell["regular"]["max_M"]
            for k in ("correlation", "projection", "greedy"):
                if k not in cell:
                    continue
                m = cell[k]["max_M"]
                wins += m > b; losses += m < b; ties += m == b
    print("-" * 92)
    print(f"pattern-aware vs random-regular on max-M: {wins} win / "
          f"{ties} tie / {losses} loss across {wins+ties+losses} comparisons")
    if wins == 0:
        print("VERDICT: pattern-aware support does NOT beat random d-regular. "
              "Negative result.")
    elif wins > losses:
        print("VERDICT: pattern-aware support wins more cells than it loses; "
              "see the per-cell deltas above for the size of the effect.")
    else:
        print("VERDICT: no consistent advantage for pattern-aware support.")
    print(f"total runtime {time.time()-t_start:.0f}s")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(config=dict(Ns=args.Ns, ds=args.ds, trials=args.trials,
                                   seed=args.seed, kappas=list(KAPPAS),
                                   strategies=STRATEGIES),
                       rows=rows), f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
