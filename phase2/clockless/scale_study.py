#!/usr/bin/env python3
"""
How far does the graph-coloured async schedule scale?

Uses the real Phase-1 pipeline (prune_pseudoinverse) so the networks are the
same kind the RTL is generated from, then for each N:

  1. train + max-prune  -> W_pruned (all M patterns exact fixed points)
  2. coupling graph     -> DSATUR colouring -> power-of-2 delay ladder
  3. simulate the schedule and measure settling + recall
  4. record the LUT cost, which is what actually caps N

The hard scaling limit is NOT the schedule -- it is the per-neuron LUT. A
neuron with k inputs needs a 2^k-entry truth table, so max_degree is the
binding constraint on synthesisable N.

`--validate` first checks the schedule simulator against the round-6/7 SV
measurements at N=16 before any large-N number is reported.
"""

import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from phase1.pruning import prune_pseudoinverse, retrain_pseudoinverse_masked
from schedule_hnn import graph_from_W, dsatur, verify, POW2


# ─── schedule simulator ──────────────────────────────────────────────────────

def simulate(s0, W, delays, max_t=None):
    """Model the RTL delay schedule: neuron i re-latches at multiples of its
    delay d_i. Neurons firing at the same t update from a common snapshot of s,
    which is exactly the synchronous-update hazard the colouring exists to
    prevent between coupled neurons.

    Returns (final_state, settled).
    """
    n = len(s0)
    d = np.asarray(delays)
    period = int(np.lcm.reduce(d))
    if max_t is None:
        max_t = 64 * int(d.max())
    s = s0.copy()
    stable_for = 0
    for t in range(1, max_t + 1):
        fire = np.nonzero(t % d == 0)[0]
        if fire.size == 0:
            continue
        h = W[fire] @ s
        nxt = np.where(h >= 0, 1, -1)
        if np.array_equal(nxt, s[fire]):
            stable_for += 1
            # a full schedule period with no change == fixed point
            if stable_for >= period:
                return s, True
        else:
            stable_for = 0
            s[fire] = nxt
    # final check: is it a fixed point under a full sweep?
    h = W @ s
    return s, bool(np.array_equal(np.where(h >= 0, 1, -1), s))


def make_pool(k, mode="pow2"):
    """k distinct delay values. The rule only requires that coupled neurons
    differ, so any distinct set is legal -- but the SPREAD affects settling, so
    the modes are compared empirically rather than assumed."""
    if mode == "pow2":
        return [2 ** (i + 1) for i in range(k)]        # doubles; max delay 2^k
    if mode == "linear":
        return [i + 1 for i in range(k)]               # 1..k; max delay k
    if mode == "linear2":
        return [2 * (i + 1) for i in range(k)]         # 2,4,..2k
    if mode == "primes":
        out, c = [], 2
        while len(out) < k:
            if all(c % d for d in range(2, int(c ** 0.5) + 1)):
                out.append(c)
            c += 1
        return out
    raise ValueError(mode)


def build_sched(W, pool=None, mode="pow2"):
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    k = max(colour.values()) + 1
    pool = list(pool) if pool else make_pool(k, mode)
    delays = [pool[colour[i]] for i in range(n)]
    return edges, colour, k, delays


# ─── validation against the SV measurements ──────────────────────────────────

def validate(rng):
    """The simulator must reproduce the qualitative SV result at N=16:
    pow2 ladder ~100% settled, all-equal delays far worse."""
    W = np.load(os.path.join(ROOT, "phase1", "results", "truth_tables",
                             "pseudo_s_maxprune", "W_pruned.npy"))
    n = W.shape[0]
    edges, colour, k, delays = build_sched(W)
    print(f"validation net: N={n} edges={len(edges)} classes={k} delays={delays[:6]}")

    P = np.load(os.path.join(ROOT, "phase1", "results", "truth_tables",
                             "pseudo_s_maxprune", "W_pruned.npy"))
    # rebuild the stored patterns the same way phase2 does
    rng0 = np.random.default_rng(42)
    pats = rng0.choice([-1, 1], size=(4, n)).astype(float)

    for label, dl in (("pow2 (coloured)", delays),
                      ("all_equal (degenerate)", [20] * n)):
        nconf = len(verify(dl, edges))
        settled = correct = tot = 0
        for m in range(len(pats)):
            for _ in range(120):
                s = pats[m].copy()
                s[rng.choice(n, size=rng.integers(1, 4), replace=False)] *= -1
                out, ok = simulate(s, W, dl, max_t=64 * max(dl))
                settled += ok
                correct += ok and np.array_equal(out, pats[m])
                tot += 1
        print(f"  {label:24s} value-conflicts={nconf:3d}  "
              f"settled={settled/tot*100:5.1f}%  correct={correct/tot*100:5.1f}%")


# ─── scaling scan ────────────────────────────────────────────────────────────

def make_support(N, d, kind, rng):
    """Structural fan-in-d support, chosen BEFORE training.

    Magnitude pruning cannot pick a support here: a rank-M pseudoinverse W has
    essentially one off-diagonal magnitude, so every candidate edge ties and the
    choice is arbitrary. Fixing the support first and retraining on it makes the
    stored patterns exact fixed points whenever d >= M, independent of N.
    """
    mask = np.zeros((N, N))
    if kind == "ring":
        # circulant: neuron i reads its d nearest neighbours (hardware-local)
        for i in range(N):
            for k in range(1, d // 2 + 1):
                for j in ((i + k) % N, (i - k) % N):
                    mask[i, j] = mask[j, i] = 1.0
    elif kind == "regular":
        # exactly d-regular: start from the ring, then randomise with
        # double-edge swaps, which preserve every degree
        adj = {i: set() for i in range(N)}
        for i in range(N):
            for k in range(1, d // 2 + 1):
                for j in ((i + k) % N, (i - k) % N):
                    adj[i].add(j); adj[j].add(i)
        edges = [(a, b) for a in range(N) for b in adj[a] if a < b]
        for _ in range(20 * len(edges)):
            i1, i2 = rng.integers(len(edges), size=2)
            if i1 == i2:
                continue
            a, b = edges[i1]; c, e = edges[i2]
            if len({a, b, c, e}) < 4:
                continue
            if e in adj[a] or b in adj[c]:
                continue
            adj[a].discard(b); adj[b].discard(a)
            adj[c].discard(e); adj[e].discard(c)
            adj[a].add(e); adj[e].add(a)
            adj[c].add(b); adj[b].add(c)
            edges[i1] = (min(a, e), max(a, e))
            edges[i2] = (min(c, b), max(c, b))
        for i in range(N):
            for j in adj[i]:
                mask[i, j] = mask[j, i] = 1.0
    elif kind == "random":
        for i in range(N):
            cand = [j for j in range(N) if j != i]
            for j in rng.choice(cand, size=min(d, len(cand)), replace=False):
                mask[i, j] = mask[j, i] = 1.0
    else:
        raise ValueError(kind)
    np.fill_diagonal(mask, 0.0)
    return mask


def run_N(N, alpha, rng, trials, hd_list, target_degree=None, fixed_M=None,
          pool_mode='pow2', support=None):
    M = fixed_M if fixed_M else max(2, int(round(alpha * N)))
    pats = rng.choice([-1, 1], size=(M, N)).astype(float)
    t0 = time.time()
    if support:
        mask = make_support(N, target_degree or 12, support, rng)
        W = retrain_pseudoinverse_masked(pats, mask)
    else:
        _, W, rep = prune_pseudoinverse(pats, s=0.5, target_degree=target_degree)
    train_s = time.time() - t0

    deg = (np.abs(W) > 1e-12).sum(axis=1)
    edges, colour, k, delays = build_sched(W, mode=pool_mode)
    nconf = len(verify(delays, edges))

    # are the patterns still fixed points after pruning?
    fixed = sum(np.array_equal(np.where(W @ pats[m] >= 0, 1, -1), pats[m])
                for m in range(M))

    out = {
        "N": N, "M": M, "alpha": M / N,
        "fixed_points_kept": f"{fixed}/{M}",
        "mean_degree": float(deg.mean()), "max_degree": int(deg.max()),
        "n_edges": len(edges), "chromatic": k,
        "value_conflicts": nconf,
        "max_lut_entries": 2 ** int(deg.max()),
        "total_lut_entries": int(sum(2 ** int(d) for d in deg)),
        "max_delay": max(delays), "train_s": round(train_s, 2),
    }

    for hd in hd_list:
        settled = correct = 0
        for _ in range(trials):
            m = rng.integers(M)
            s = pats[m].copy()
            s[rng.choice(N, size=hd, replace=False)] *= -1
            res, ok = simulate(s, W, delays, max_t=32 * max(delays))
            settled += ok
            correct += ok and np.array_equal(res, pats[m])
        out[f"settled_hd{hd}"] = settled / trials
        out[f"correct_hd{hd}"] = correct / trials
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.125)
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--Ns", type=int, nargs="+",
                    default=[16, 32, 64, 128, 256, 512])
    ap.add_argument("--support", default=None,
                    choices=["ring", "random", "regular"],
                    help="fix a structural support and retrain on it")
    ap.add_argument("--pool", default="pow2",
                    choices=["pow2", "linear", "linear2", "primes"])
    ap.add_argument("--M", type=int, default=None,
                    help="fix the pattern count instead of deriving it from alpha")
    ap.add_argument("--degree", type=int, default=None,
                    help="cap per-neuron fan-in; LUT is 2^degree entries")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = np.random.default_rng(2718)
    if args.validate:
        print("=" * 78)
        print("SIMULATOR VALIDATION vs SV (N=16)")
        print("=" * 78)
        validate(rng)
        print()

    print("=" * 100)
    print(f"SCALING SCAN  {'M='+str(args.M) if args.M else 'alpha='+str(args.alpha)}"
          f"  degree_cap={args.degree}  "
          f"({args.trials} trials/point)")
    print("=" * 100)
    hdr = (f"{'N':>5}{'M':>4}{'deg~':>6}{'degmax':>7}{'chi':>5}{'conf':>5}"
           f"{'maxLUT':>12}{'set@1':>7}{'ok@1':>7}{'set@3':>7}{'ok@3':>7}{'t(s)':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for N in args.Ns:
        try:
            r = run_N(N, args.alpha, rng, args.trials, (1, 3), args.degree, args.M,
                      args.pool, args.support)
        except Exception as e:
            print(f"{N:>5}  FAILED: {type(e).__name__}: {e}")
            continue
        rows.append(r)
        print(f"{r['N']:>5}{r['M']:>4}{r['mean_degree']:>6.1f}{r['max_degree']:>7}"
              f"{r['chromatic']:>5}{r['value_conflicts']:>5}"
              f"{r['max_lut_entries']:>12,}"
              f"{r['settled_hd1']*100:>6.0f}%{r['correct_hd1']*100:>6.0f}%"
              f"{r['settled_hd3']*100:>6.0f}%{r['correct_hd3']*100:>6.0f}%"
              f"{r['train_s']:>7.1f}")
    if args.out and rows:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
