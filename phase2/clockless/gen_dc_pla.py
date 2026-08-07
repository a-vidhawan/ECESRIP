#!/usr/bin/env python3
"""
Emit per-neuron PLAs that specify ONLY the care set, and minimise with espresso.

The existing pipeline emits fully-specified truth tables: all 2^d rows, every
one a care condition. That is the worst case for two-level minimisation, and it
is also more than an associative memory needs -- it only has to behave correctly
on states it actually visits.

Here the care set is the projection of the operating region (states within
Hamming radius h of a stored pattern) onto each neuron's support. Its size is
M * sum_{j<=h} C(d,j), which is POLYNOMIAL in fan-in, while the full table is
exponential. Everything else is emitted as a don't-care via `.type fr`, which
lists the ON-set and OFF-set and leaves the remainder free for espresso.

Usage:
    python3 gen_dc_pla.py --N 256 --M 4 --degree 16 --radius 3 --full-compare
"""

import argparse, itertools, os, subprocess, sys, tempfile, time
from math import comb
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from phase1.pruning import retrain_pseudoinverse_masked
from scale_study import make_support

ESPRESSO = os.environ.get("ESPRESSO", "espresso")


def build_net(N, M, d, seed):
    rng = np.random.default_rng(seed)
    pats = rng.choice([-1, 1], size=(M, N)).astype(float)
    mask = make_support(N, d, "regular", rng)
    W = retrain_pseudoinverse_masked(pats, mask)
    kept = sum(np.array_equal(np.where(W @ pats[m] >= 0, 1, -1), pats[m])
               for m in range(M))
    return pats, W, kept


def care_rows(i, W, pats, radius):
    """Distinct (input projection -> output) pairs over the operating region.

    Enumerated directly rather than by sweeping states: the projection of a
    corrupted pattern onto neuron i's support is just the pattern's projection
    with <=radius of THOSE bits flipped, so this is M*sum C(d,j) work, not
    O(N^radius).
    """
    sup = np.nonzero(np.abs(W[i]) > 1e-12)[0]
    d = len(sup)
    if d == 0:
        return None, 0, {}
    w = W[i, sup]
    rows = {}
    for m in range(len(pats)):
        base = pats[m][sup].copy()
        rest = float(W[i] @ pats[m] - w @ base)   # contribution outside support
        for j in range(radius + 1):
            for flip in itertools.combinations(range(d), j):
                v = base.copy()
                for b in flip:
                    v[b] *= -1
                key = tuple(int((x + 1) // 2) for x in v)
                rows[key] = 1 if (w @ v + rest) >= 0 else 0
    return sup, d, rows


def full_rows(i, W, pats):
    """Every one of the 2^d input combinations -- the current pipeline's output."""
    sup = np.nonzero(np.abs(W[i]) > 1e-12)[0]
    d = len(sup)
    w = W[i, sup]
    rows = {}
    for bits in itertools.product((0, 1), repeat=d):
        v = np.array([2 * b - 1 for b in bits], dtype=float)
        rows[bits] = 1 if (w @ v) >= 0 else 0
    return sup, d, rows


def write_pla(path, sup, d, rows, dc=True):
    with open(path, "w") as f:
        f.write(f".i {d}\n.o 1\n")
        f.write(".ilb " + " ".join(f"b_{j}" for j in sup) + "\n")
        f.write(".ob f\n")
        # fr: ON-set and OFF-set are both listed; anything absent is a don't-care
        f.write(".type fr\n" if dc else ".type f\n")
        f.write(f".p {len(rows)}\n")
        for k, v in rows.items():
            f.write("".join(str(b) for b in k) + f" {v}\n")
        f.write(".e\n")


def run_espresso(path):
    t0 = time.time()
    try:
        out = subprocess.run([ESPRESSO, path], capture_output=True, text=True,
                             timeout=1800)
    except subprocess.TimeoutExpired:
        return None, 1800.0, "timeout"
    if out.returncode != 0:
        return None, time.time() - t0, out.stderr.strip()[:80]
    terms = None
    for line in out.stdout.splitlines():
        if line.startswith(".p "):
            terms = int(line.split()[1])
    return terms, time.time() - t0, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=256)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, required=True)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--neurons", type=int, default=6, help="how many to minimise")
    ap.add_argument("--full-compare", action="store_true",
                    help="also minimise the fully-specified table (feasible <=16)")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    d = args.degree
    pats, W, kept = build_net(args.N, args.M, d, args.seed)
    bound = args.M * sum(comb(d, j) for j in range(args.radius + 1))
    print(f"N={args.N} M={args.M} fan-in={d} radius={args.radius}  "
          f"fixed points kept {kept}/{args.M}")
    print(f"full table 2^{d} = {2**d:,} rows | care-set bound "
          f"M*sum C(d,j) = {bound:,} ({100*bound/2**d:.4f}%)")
    print()
    hdr = f"{'neuron':>7}{'care rows':>11}{'DC terms':>10}{'DC sec':>8}"
    if args.full_compare:
        hdr += f"{'full rows':>11}{'full terms':>11}{'full sec':>9}{'saving':>8}"
    print(hdr); print("-" * len(hdr))

    tmp = tempfile.mkdtemp()
    dc_tot = full_tot = 0
    for i in range(min(args.neurons, args.N)):
        sup, dd, rows = care_rows(i, W, pats, args.radius)
        if sup is None or dd == 0:
            continue
        p = os.path.join(tmp, f"dc_{i}.pla")
        write_pla(p, sup, dd, rows, dc=True)
        t, sec, err = run_espresso(p)
        line = f"{i:>7}{len(rows):>11,}{(t if t is not None else -1):>10,}{sec:>8.2f}"
        dc_tot += t or 0
        if args.full_compare:
            sup2, dd2, rows2 = full_rows(i, W, pats)
            p2 = os.path.join(tmp, f"full_{i}.pla")
            write_pla(p2, sup2, dd2, rows2, dc=False)
            t2, sec2, err2 = run_espresso(p2)
            full_tot += t2 or 0
            sv = (t2 / t) if (t and t2) else float("nan")
            line += f"{len(rows2):>11,}{(t2 if t2 is not None else -1):>11,}{sec2:>9.2f}{sv:>7.1f}x"
        if err:
            line += f"  [{err}]"
        print(line)
    print("-" * len(hdr))
    print(f"total DC terms: {dc_tot:,}" +
          (f"   total full terms: {full_tot:,}   overall saving: "
           f"{full_tot/dc_tot:.1f}x" if args.full_compare and dc_tot else ""))


if __name__ == "__main__":
    main()
