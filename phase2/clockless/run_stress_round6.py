#!/usr/bin/env python3
"""
Round 6: does scheduling by the coupling graph beat scheduling by index parity?

even_odd assigns delays by i%2, which is blind to the LUT coupling graph and
leaves 44% of coupled pairs latching at the same sim time. Here we build delay
classes that are proper colourings of that graph and compare them head-to-head
on the hardest state sets from earlier rounds.

Schemes
  parity    -- baseline even_odd (T_EVEN=10, T_ODD=24)
  colour6   -- proper colouring of the coupling graph, prime delays
  dist2     -- colouring of the graph SQUARE (no 2-hop pair shares a class)
  distinct  -- all 16 neurons on distinct primes (maximal desynchronisation)

Scheme colour6/dist2/distinct all use prime delays so no two classes are
commensurate -- they never lock into a fixed phase relationship.
"""

import os, sys, json, itertools
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_clockless_sv import gen_coloring_sv, gen_even_odd_sv, PRIME_DELAYS
from run_clockless_stress import (
    N, PATTERNS_BIN, PATTERNS_INT, RTL, RES as RESULTS,
    lut_update, hamming, nearest_pat, corrupt, flip_k, run_batch,
)
from analyze_coupling import build_graph, conflicts, greedy_colour

SEED = 606


# ─── delay-class schemes ─────────────────────────────────────────────────────

def build_schemes():
    supports, terms, edges = build_graph()
    deg = {i: 0 for i in range(N)}
    for i, j in edges:
        deg[i] += 1
        deg[j] += 1
    order = sorted(range(N), key=lambda v: -deg[v])

    # proper colouring of G
    col6 = greedy_colour(edges, order)

    # colouring of G^2: also forbid two neurons sharing a common neighbour,
    # so no 2-hop-correlated pair fires together either
    adj = {i: set() for i in range(N)}
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    sq_edges = set(edges)
    for v in range(N):
        for a, b in itertools.combinations(sorted(adj[v]), 2):
            sq_edges.add((min(a, b), max(a, b)))
    sq_edges = sorted(sq_edges)
    deg2 = {i: 0 for i in range(N)}
    for i, j in sq_edges:
        deg2[i] += 1
        deg2[j] += 1
    col_d2 = greedy_colour(sq_edges, sorted(range(N), key=lambda v: -deg2[v]))

    distinct = {i: i for i in range(N)}
    parity = {i: i % 2 for i in range(N)}

    schemes = {
        "parity":   parity,
        "colour6":  col6,
        "dist2":    col_d2,
        "distinct": distinct,
    }
    stats = {}
    for name, cls in schemes.items():
        stats[name] = {
            "n_classes": max(cls.values()) + 1,
            "conflicts_G": len(conflicts(edges, cls)),
            "conflicts_G2": len(conflicts(sq_edges, cls)),
        }
    return schemes, stats, edges, sq_edges


def generate(name, classes):
    """Emit RTL for a scheme; parity keeps the original even_odd module."""
    if name == "parity":
        sv, max_d = gen_even_odd_sv(N, 10, 24)
        path = os.path.join(RTL, "clockless_even_odd.sv")
        with open(path, "w") as f:
            f.write(sv)
        return "even_odd", path, max_d
    sv, max_d, delays = gen_coloring_sv(
        N, classes, note=f"scheme={name}")
    path = os.path.join(RTL, f"clockless_col_{name}.sv")
    with open(path, "w") as f:
        f.write(sv)
    return "coloring", path, max_d


# ─── test sets ───────────────────────────────────────────────────────────────

def load_universal_oscillators():
    """States that oscillated in BOTH depth and even_odd (round 3, EXP E)."""
    p = os.path.join(RESULTS, "stress_r3_universal_osc.csv")
    if not os.path.exists(p):
        return []
    df = pd.read_csv(p)
    col = "init_state"
    return sorted({int(str(v), 16) for v in df[col].dropna().unique()})


def build_testsets(rng):
    sets = {}

    # 1. exhaustive HD<=3 around every stored pattern -- the basin edge
    hd3 = []
    for pi, pb in enumerate(PATTERNS_BIN):
        base = PATTERNS_INT[pi]
        for k in range(1, 4):
            for bits in itertools.combinations(range(N), k):
                v = base
                for b in bits:
                    v ^= (1 << b)
                hd3.append((v, pi, float(k) / N, k))
    sets["hd3"] = hd3

    # 2. heavy corruption -- eta 0.35..0.50
    heavy = []
    for pi, pb in enumerate(PATTERNS_BIN):
        for eta in (0.35, 0.40, 0.45, 0.50):
            for _ in range(150):
                v = corrupt(pb, eta, rng)
                heavy.append((v, pi, eta, hamming(v, PATTERNS_INT[pi])))
    sets["heavy"] = heavy

    # 3. universal oscillators -- the states nothing has cracked
    uosc = load_universal_oscillators()
    sets["uosc"] = [(v, nearest_pat(v)[0], -1.0, nearest_pat(v)[1]) for v in uosc]

    # 4. uniform random over the whole state space
    rs = rng.choice(65536, size=3000, replace=False)
    sets["random"] = [(int(v), nearest_pat(int(v))[0], -1.0,
                       nearest_pat(int(v))[1]) for v in rs]

    return sets


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(SEED)
    schemes, stats, edges, sq_edges = build_schemes()

    print("=" * 74)
    print("DELAY-CLASS SCHEMES vs COUPLING GRAPH")
    print(f"  |E(G)|={len(edges)}  |E(G^2)|={len(sq_edges)}")
    for name, st in stats.items():
        print(f"  {name:9s} classes={st['n_classes']:2d}  "
              f"simultaneous coupled pairs: G={st['conflicts_G']:3d}  "
              f"G^2={st['conflicts_G2']:3d}")
    print("=" * 74)

    rtl = {}
    for name, cls in schemes.items():
        mode, path, max_d = generate(name, cls)
        rtl[name] = (mode, path, max_d)
        print(f"  {name:9s} -> {os.path.basename(path)} (max_delay={max_d})")

    testsets = build_testsets(rng)
    print("\ntest sets: " + ", ".join(f"{k}={len(v)}" for k, v in testsets.items()))

    frames = []
    for set_name, items in testsets.items():
        if not items:
            print(f"  [skip] {set_name} empty")
            continue
        inits = [it[0] for it in items]
        pidx  = [it[1] for it in items]
        etas  = [it[2] for it in items]
        hds   = [it[3] for it in items]
        print(f"\n--- test set: {set_name} ({len(inits)} states)")
        for name in schemes:
            mode, path, max_d = rtl[name]
            df = run_batch(f"r6_{set_name}", mode, inits, pidx, etas, hds,
                           path, max_d, variant_tag=f"_{name}")
            if len(df):
                df["scheme"] = name
                df["testset"] = set_name
                df["n_classes"] = stats[name]["n_classes"]
                df["conflicts_G"] = stats[name]["conflicts_G"]
                frames.append(df)

    if not frames:
        print("no results")
        return

    alldf = pd.concat(frames, ignore_index=True)
    dest = os.path.join(RESULTS, "stress_r6_scheduling.csv")
    alldf.to_csv(dest, index=False)

    print("\n" + "=" * 74)
    print("SUMMARY  (correct% / settled%)")
    print("=" * 74)
    piv_c = alldf.pivot_table(index="scheme", columns="testset",
                              values="correct", aggfunc="mean") * 100
    piv_s = alldf.pivot_table(
        index="scheme", columns="testset", values="settled", aggfunc="mean") * 100
    order = [s for s in ["parity", "colour6", "dist2", "distinct"]
             if s in piv_c.index]
    print("\ncorrect %:\n", piv_c.reindex(order).round(1).to_string())
    print("\nsettled %:\n", piv_s.reindex(order).round(1).to_string())

    with open(os.path.join(RESULTS, "r6_schemes.json"), "w") as f:
        json.dump({"stats": stats,
                   "classes": {k: {str(i): c for i, c in v.items()}
                               for k, v in schemes.items()}}, f, indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
