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

Six supports are compared at matched fan-in d:

  regular      random d-regular, pattern-blind          (the incumbent baseline)
  correlation  keep the d edges per neuron with the largest |sum_mu xi_i xi_j|
  projection   keep the d largest |P_ij| of the DENSE pseudoinverse projector
               P = X^T (X X^T)^-1 X, i.e. sparsify the ideal unconstrained
               solution rather than the raw second moment        (my 5th idea)
  greedy       grow the support in 4 rounds; each round re-scores every candidate
               edge by a hinge-weighted correlation that only counts (pattern,
               neuron) constraints whose margin is currently violated, so edges
               are added where the margin deficit actually is
  decoy        CONTROL. The correlation selector run on a FRESH, INDEPENDENT
               pattern set -- the same machinery pointed at the wrong patterns.
               Isolates "the selector builds a better graph" from "the selector
               knows the patterns".
  ring         circulant nearest-neighbour support -- a KNOWN-BAD control,
               included to prove the comparison can detect a bad support

All six go through the same degree-constrained selector (greedy b-matching under
a hard degree cap of d, plus a deficit-repair pass), so every strategy is
exactly or near-exactly d-regular; the achieved mean/max/min degree is printed
and stored so a fan-in advantage cannot masquerade as a capacity win. Every
strategy gets the identical trainer (train_margin_auto), the identical kappa
ladder, the identical M grid, the identical seeds, and the identical recall
protocol (DSATUR colouring, delays = colour+1, settle_event_driven).

FINDING -- pattern-aware support DOES beat random d-regular, by a lot.
At matched fan-in the correlation/projection/greedy supports store roughly
1.8-2x the patterns the random d-regular baseline can, and at matched load
(everyone trained on the baseline's own max M) they recall ~80-100% at HD=5%/10%
where the baseline recalls ~5%. The two controls behave exactly as they must for
this to be believable: `ring` is no better than `regular` (the instrument can see
a bad support), and `decoy` -- the identical selector fed independent patterns --
lands on the baseline, not on the pattern-aware group. So the gain is
attributable to pattern knowledge, not to the selector producing a
structurally nicer graph. Numbers, per cell, in results/learned_support.json.

CAVEATS. (1) The support is now pattern-specific: the routing is only valid for
the pattern set it was derived from, so a stored-set change means a re-route,
not just a re-train. The baseline graph is equally fixed, but it is
pattern-agnostic, which is a real deployment difference. (2) Only 2 replicates
per cell and one pattern draw per M, so max-M is resolved to the M grid, not
finely. (3) Patterns are i.i.d. random +/-1; a correlation-based selector on
i.i.d. patterns is picking up sampling noise in sum_mu xi_i xi_j, which is
exactly the "structure" the trainer then exploits -- the effect should be
expected to change (probably grow) for genuinely correlated pattern sets, and
this experiment does not measure that.

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


def support_decoy(pats, d, rng, seed):
    """CONTROL. Identical selector, identical score function, but computed on a
    FRESH independent pattern set of the same shape -- i.e. the right machinery
    pointed at the wrong patterns. If `correlation` beats `regular` because it
    knows the patterns, this must NOT beat `regular`; if it does, the advantage
    came from the selector's graph structure and not from pattern knowledge."""
    M, N = pats.shape
    fake = np.random.default_rng(seed + 90210).choice(
        [-1, 1], size=(M, N)).astype(float)
    return support_correlation(fake, d, rng)


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
    if kind == "decoy":
        return support_decoy(pats, d, rng, seed)
    raise ValueError(kind)


STRATEGIES = ["regular", "correlation", "projection", "greedy",
              "decoy", "ring"]


# ── sweep ───────────────────────────────────────────────────────────────────

def m_grid(d, N):
    """M values swept upward, as multiples of the fan-in d. Runs to 2.5d
    because the pattern-aware supports turn out to keep working well past the
    ~0.8d where the random-regular baseline dies. Coarse on purpose: the grid is
    the same for every strategy, so it costs resolution, not fairness."""
    fr = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5]
    out = sorted({max(2, int(round(d * f))) for f in fr})
    return [m for m in out if m <= N]


def train_at(N, d, kind, pats, seed):
    mask = build_support(kind, N, d, pats, seed)
    W, kap = train_margin_auto(pats, mask, kappas=KAPPAS, seed=seed)
    return W, kap, mask


def run_cell(N, d, kind, seed, hds, trials, verbose=True):
    """Sweep M upward for one (N, d, strategy, seed); return the largest M with
    ALL patterns stored, the achieved degrees, and recall at that M."""
    out = dict(N=N, d=d, strategy=kind, seed=seed, max_M=0, kappa=None,
               mean_degree=None, max_degree=None, min_degree=None,
               n_edges=None, recall_at_maxM={})
    keep = None
    fails = 0
    for M in m_grid(d, N):
        pats = np.random.default_rng(seed * 1000 + M).choice(
            [-1, 1], size=(M, N)).astype(float)
        W, kap, mask = train_at(N, d, kind, pats, seed)
        deg = mask.sum(axis=1)
        nf = n_fixed(W, pats)
        if verbose:
            print(f"    M={M:<3} deg {deg.mean():.2f}/{int(deg.max())}/"
                  f"{int(deg.min())} kappa={kap} fixed={nf}/{M}", flush=True)
        if nf == M:
            fails = 0
            out.update(max_M=M, kappa=kap, mean_degree=float(deg.mean()),
                       max_degree=int(deg.max()), min_degree=int(deg.min()),
                       n_edges=int(deg.sum() // 2))
            keep = (W, pats)
        else:
            fails += 1
            if fails >= 1:      # failure is sharp and monotone in M here;
                break           # stopping at the first one, for every strategy
                                # alike, roughly halves the runtime
    if keep is not None:
        W, pats = keep
        for hd in hds:
            out["recall_at_maxM"][f"hd{hd}"] = recall_rate(
                W, pats, hd, trials, np.random.default_rng(seed + 7))
    return out


def matched_recall(N, d, kind, M_ref, seed, hds, trials):
    """Recall for every strategy at the SAME load M_ref (the baseline's max M),
    so strategies are not compared at different pattern counts."""
    pats = np.random.default_rng(seed * 1000 + M_ref).choice(
        [-1, 1], size=(M_ref, N)).astype(float)
    W, kap, mask = train_at(N, d, kind, pats, seed)
    nf = n_fixed(W, pats)
    r = dict(M_ref=M_ref, kappa=kap, n_fixed=nf, all_stored=bool(nf == M_ref),
             mean_degree=float(mask.sum(axis=1).mean()))
    for hd in hds:
        r[f"hd{hd}"] = recall_rate(W, pats, hd, trials,
                                   np.random.default_rng(seed + 7))
    return r


def reps_for(N, d):
    """Replicates (independent pattern draws + independent support seeds) per
    cell. Uniform across cells and strategies."""
    return 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns", type=int, nargs="+", default=[64, 128])
    ap.add_argument("--ds", type=int, nargs="+", default=[16, 32])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--reps", type=int, default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results",
                                                  "learned_support.json"))
    args = ap.parse_args()
    if args.quick:
        args.Ns, args.ds, args.trials, args.reps = [64], [16], 20, 1

    t0 = time.time()
    rows, matched = [], []
    for N in args.Ns:
        hds = [max(1, int(round(f * N))) for f in (0.05, 0.10)]
        for d in args.ds:
            R = args.reps or reps_for(N, d)
            print(f"\n=== N={N} d={d}  HD={hds}  reps={R} ===", flush=True)
            for kind in STRATEGIES:
                for rep in range(R):
                    sd = args.seed + 137 * rep
                    print(f"  [{kind}] rep {rep} (seed {sd})", flush=True)
                    rows.append(run_cell(N, d, kind, sd, hds, args.trials))
            # matched-load recall at the baseline's median max M
            base = sorted(r["max_M"] for r in rows
                          if r["N"] == N and r["d"] == d
                          and r["strategy"] == "regular")
            M_ref = base[len(base) // 2] if base else 0
            if M_ref:
                print(f"  -- matched-load recall at M_ref={M_ref} --", flush=True)
                for kind in STRATEGIES:
                    for rep in range(R):
                        sd = args.seed + 137 * rep
                        m = matched_recall(N, d, kind, M_ref, sd, hds,
                                           args.trials)
                        m.update(N=N, d=d, strategy=kind, seed=sd)
                        matched.append(m)

    # ── report ──
    def agg(vals):
        v = sorted(vals)
        return v[len(v) // 2], min(v), max(v)

    print("\n" + "=" * 104)
    print(f"MAX M WITH ALL PATTERNS STORED  (median [min-max] over reps), "
          f"recall at each strategy's own max M, {args.trials} trials/point")
    print("=" * 104)
    hdr = (f"{'N':>4}{'d':>4}  {'strategy':<12}{'maxM med':>10}{'range':>10}"
           f"{'vs reg':>8}{'deg mean':>10}{'deg max':>9}{'deg min':>9}"
           f"{'rec@5%':>9}{'rec@10%':>9}")
    print(hdr); print("-" * len(hdr))
    summary = []
    for N in args.Ns:
        hds = [max(1, int(round(f * N))) for f in (0.05, 0.10)]
        for d in args.ds:
            cell = [r for r in rows if r["N"] == N and r["d"] == d]
            if not cell:
                continue
            bm, _, _ = agg([r["max_M"] for r in cell
                            if r["strategy"] == "regular"])
            for kind in STRATEGIES:
                rr = [r for r in cell if r["strategy"] == kind]
                if not rr:
                    continue
                med, lo, hi = agg([r["max_M"] for r in rr])
                dm = [r["mean_degree"] for r in rr if r["mean_degree"]]
                dmx = [r["max_degree"] for r in rr if r["max_degree"]]
                dmn = [r["min_degree"] for r in rr if r["min_degree"]]
                rec = []
                for hd in hds:
                    vs = [r["recall_at_maxM"].get(f"hd{hd}") for r in rr
                          if r["recall_at_maxM"]]
                    rec.append(float(np.mean(vs)) if vs else float("nan"))
                srow = dict(N=N, d=d, strategy=kind, maxM_median=med,
                            maxM_min=lo, maxM_max=hi, vs_regular=med - bm,
                            ratio=(med / bm if bm else None),
                            deg_mean=float(np.mean(dm)) if dm else None,
                            deg_max=int(max(dmx)) if dmx else None,
                            deg_min=int(min(dmn)) if dmn else None,
                            recall_own_maxM=dict(zip([f"hd{h}" for h in hds],
                                                     rec)))
                summary.append(srow)
                print(f"{N:>4}{d:>4}  {kind:<12}{med:>10}"
                      f"{f'{lo}-{hi}':>10}{med-bm:>+8}"
                      f"{(srow['deg_mean'] or 0):>10.2f}"
                      f"{(srow['deg_max'] or 0):>9}{(srow['deg_min'] or 0):>9}"
                      f"{100*rec[0]:>8.0f}%{100*rec[1]:>8.0f}%")
            print()

    if matched:
        print("=" * 104)
        print("RECALL AT MATCHED LOAD (all strategies at the baseline's max M) "
              f"-- {args.trials} trials/point, mean over reps")
        print("=" * 104)
        h2 = (f"{'N':>4}{'d':>4}  {'strategy':<12}{'M_ref':>7}{'stored':>9}"
              f"{'rec@5%':>9}{'rec@10%':>9}")
        print(h2); print("-" * len(h2))
        for N in args.Ns:
            hds = [max(1, int(round(f * N))) for f in (0.05, 0.10)]
            for d in args.ds:
                for kind in STRATEGIES:
                    mm = [m for m in matched if m["N"] == N and m["d"] == d
                          and m["strategy"] == kind]
                    if not mm:
                        continue
                    st = np.mean([m["all_stored"] for m in mm])
                    r5 = np.mean([m[f"hd{hds[0]}"] for m in mm])
                    r10 = np.mean([m[f"hd{hds[1]}"] for m in mm])
                    print(f"{N:>4}{d:>4}  {kind:<12}{mm[0]['M_ref']:>7}"
                          f"{100*st:>8.0f}%{100*r5:>8.0f}%{100*r10:>8.0f}%")
                print()

    # ── honest verdict ──
    wins = losses = ties = 0
    for s_ in summary:
        if s_["strategy"] not in ("correlation", "projection", "greedy"):
            continue
        wins += s_["vs_regular"] > 0
        losses += s_["vs_regular"] < 0
        ties += s_["vs_regular"] == 0
    dec = [s_ for s_ in summary if s_["strategy"] == "decoy"]
    dec_wins = sum(s_["vs_regular"] > 0 for s_ in dec)
    print("-" * 104)
    print(f"pattern-aware vs random-regular on max-M: {wins} win / {ties} tie /"
          f" {losses} loss of {wins+ties+losses} cells")
    print(f"DECOY control (same selector, wrong patterns) beats regular in "
          f"{dec_wins}/{len(dec)} cells")
    if wins == 0:
        print("VERDICT: pattern-aware support does NOT beat random d-regular.")
    elif dec_wins >= wins:
        print("VERDICT: the gain is NOT from pattern knowledge -- the decoy "
              "control gains as much, so it is the selector/graph structure.")
    else:
        print("VERDICT: pattern-aware support beats random d-regular, and the "
              "decoy control does not reproduce the gain, so the gain is "
              "attributable to pattern knowledge.")
    print(f"total runtime {time.time()-t0:.0f}s")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dict(config=dict(Ns=args.Ns, ds=args.ds, trials=args.trials,
                                   seed=args.seed, kappas=list(KAPPAS),
                                   strategies=STRATEGIES,
                                   reps={f"N{N}_d{d}": (args.reps or reps_for(N, d))
                                         for N in args.Ns for d in args.ds}),
                       summary=summary, runs=rows, matched_load=matched),
                  f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
