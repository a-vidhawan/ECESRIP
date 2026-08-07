#!/usr/bin/env python3
"""
Round 7: is the colouring win a design rule or numerology?

Round 6 showed a proper colouring of the coupling graph with prime delays
cracks all 32 universal oscillators. Two properties could be responsible:

  (A) COLOURING       -- no two coupled neurons share a delay class
  (B) INCOMMENSURABLE -- no two class delays are integer multiples

This runs the 2x2 to separate them, plus 12 random permutations of the same
primes over the same classes to test robustness. If permuting the primes moves
the result, the win is luck, not a rule.

  colouring + incommensurate : perm00..perm11, primes_{small,large,spread}
  colouring + commensurate   : commens_{6x,10x,pow2}
  colouring + no separation  : all_equal   (delays identical -> synchronous)
  parity    + incommensurate : parity_primes
"""

import os, sys, json, random, itertools
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_clockless_sv import gen_coloring_sv
from run_clockless_stress import (
    N, PATTERNS_BIN, PATTERNS_INT, RTL, RES as RESULTS,
    hamming, nearest_pat, corrupt, run_batch,
)
from analyze_coupling import build_graph, conflicts, greedy_colour

SEED = 707
BASE_PRIMES = [11, 13, 17, 19, 23, 29]


def build_scheme_list():
    supports, terms, edges = build_graph()
    deg = {i: 0 for i in range(N)}
    for i, j in edges:
        deg[i] += 1
        deg[j] += 1
    col6 = greedy_colour(edges, sorted(range(N), key=lambda v: -deg[v]))
    parity = {i: i % 2 for i in range(N)}

    rng = random.Random(SEED)
    perms = set()
    while len(perms) < 12:
        perms.add(tuple(rng.sample(BASE_PRIMES, 6)))

    schemes = []
    for k, p in enumerate(sorted(perms)):
        schemes.append((f"perm{k:02d}", col6, list(p), "colour+incommens"))
    schemes += [
        ("primes_small",  col6, [2, 3, 5, 7, 11, 13],        "colour+incommens"),
        ("primes_large",  col6, [101, 103, 107, 109, 113, 127], "colour+incommens"),
        ("primes_spread", col6, [11, 29, 53, 79, 101, 127],  "colour+incommens"),
        # proper colouring, but every delay is a multiple of the smallest
        ("commens_6x",    col6, [6, 12, 18, 24, 30, 36],     "colour+commens"),
        ("commens_10x",   col6, [10, 20, 30, 40, 50, 60],    "colour+commens"),
        ("commens_pow2",  col6, [2, 4, 8, 16, 32, 64],       "colour+commens"),
        # colouring present but delays identical -> fully synchronous
        ("all_equal",     col6, [20] * 6,                    "colour+nosep"),
        # incommensurate delays but NO colouring
        ("parity_primes", parity, [11, 29],                  "parity+incommens"),
    ]
    return schemes, edges


def build_testsets(rng):
    sets = {}
    hd3 = []
    for pi in range(len(PATTERNS_BIN)):
        base = PATTERNS_INT[pi]
        for k in range(1, 4):
            for bits in itertools.combinations(range(N), k):
                v = base
                for b in bits:
                    v ^= (1 << b)
                hd3.append((v, pi, float(k) / N, k))
    sets["hd3"] = hd3

    p = os.path.join(RESULTS, "stress_r3_universal_osc.csv")
    if os.path.exists(p):
        uo = sorted({int(str(v), 16)
                     for v in pd.read_csv(p)["init_state"].dropna().unique()})
        sets["uosc"] = [(v, nearest_pat(v)[0], -1.0, nearest_pat(v)[1]) for v in uo]

    rs = rng.choice(65536, size=1500, replace=False)
    sets["random"] = [(int(v), nearest_pat(int(v))[0], -1.0,
                       nearest_pat(int(v))[1]) for v in rs]
    return sets


def main():
    rng = np.random.default_rng(SEED)
    schemes, edges = build_scheme_list()
    testsets = build_testsets(rng)
    print(f"{len(schemes)} schemes x {sum(len(v) for v in testsets.values())} states")

    frames = []
    for name, classes, delays, category in schemes:
        k = max(classes.values()) + 1
        sv, max_d, per_neuron = gen_coloring_sv(
            N, classes, delays[:k], note=f"scheme={name} cat={category}")
        path = os.path.join(RTL, f"clockless_r7_{name}.sv")
        with open(path, "w") as f:
            f.write(sv)
        nconf = len(conflicts(edges, classes))
        print(f"\n[{name}] {category}  delays={delays[:k]}  conflicts={nconf}")
        for set_name, items in testsets.items():
            if not items:
                continue
            df = run_batch(f"r7_{set_name}", "coloring",
                           [it[0] for it in items], [it[1] for it in items],
                           [it[2] for it in items], [it[3] for it in items],
                           path, max_d, variant_tag=f"_{name}")
            if len(df):
                df["scheme"] = name
                df["category"] = category
                df["testset"] = set_name
                df["delays"] = str(delays[:k])
                df["conflicts_G"] = nconf
                frames.append(df)

    if not frames:
        print("no results")
        return
    alldf = pd.concat(frames, ignore_index=True)
    dest = os.path.join(RESULTS, "stress_r7_permutation.csv")
    alldf.to_csv(dest, index=False)

    print("\n" + "=" * 78)
    print("SETTLED % by scheme x testset")
    print("=" * 78)
    ps = alldf.pivot_table(index=["category", "scheme"], columns="testset",
                           values="settled", aggfunc="mean") * 100
    print(ps.round(1).to_string())

    print("\n" + "=" * 78)
    print("CORRECT % by scheme x testset")
    print("=" * 78)
    pc = alldf.pivot_table(index=["category", "scheme"], columns="testset",
                           values="correct", aggfunc="mean") * 100
    print(pc.round(1).to_string())

    print("\n" + "=" * 78)
    print("ROBUSTNESS across the 12 prime permutations (same classes)")
    print("=" * 78)
    perm = alldf[alldf["scheme"].str.startswith("perm")]
    for set_name in sorted(perm["testset"].unique()):
        sub = perm[perm["testset"] == set_name].groupby("scheme")["settled"].mean() * 100
        c = perm[perm["testset"] == set_name].groupby("scheme")["correct"].mean() * 100
        print(f"  {set_name:8s} settled: mean={sub.mean():5.1f}% "
              f"sd={sub.std():4.2f} min={sub.min():5.1f} max={sub.max():5.1f} | "
              f"correct: mean={c.mean():5.1f}% sd={c.std():4.2f}")

    print("\n" + "=" * 78)
    print("CATEGORY MEANS")
    print("=" * 78)
    print((alldf.pivot_table(index="category", columns="testset",
                             values="settled", aggfunc="mean") * 100).round(1).to_string())
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
