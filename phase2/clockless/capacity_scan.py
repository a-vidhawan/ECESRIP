#!/usr/bin/env python3
"""
How much of the recall gap is loading (alpha = M/N) rather than scheduling?

Round 6/7 show scheduling drives oscillation down to ~2% but leaves ~76% of
random states landing on SPURIOUS attractors. That is an attractor-structure
problem, not a timing one. This scans pseudoinverse Hopfield nets across N and
M to find the loading at which basins are large enough for near-perfect recall.

Pure Python/numpy synchronous + random-async simulation -- no SV needed.
"""

import argparse, json
import numpy as np


def pseudoinverse_W(P):
    """Projection rule: W = P (P^T P)^-1 P^T, zero diagonal. P is (N, M) bipolar."""
    W = P @ np.linalg.pinv(P.T @ P) @ P.T
    np.fill_diagonal(W, 0.0)
    return W


def step_sync(s, W):
    h = W @ s
    out = np.where(h >= 0, 1, -1)
    return out


def settle_async(s, W, rng, max_sweeps=60):
    """Random-order asynchronous updates -- the idealised limit of a schedule
    where no two coupled neurons ever fire together."""
    n = len(s)
    s = s.copy()
    for _ in range(max_sweeps):
        changed = False
        for i in rng.permutation(n):
            h = W[i] @ s
            v = 1 if h >= 0 else -1
            if v != s[i]:
                s[i] = v
                changed = True
        if not changed:
            return s, True
    return s, False


def scan(N, M, n_trials, hd, rng):
    P = rng.choice([-1, 1], size=(N, M)).astype(float)
    W = pseudoinverse_W(P)

    # confirm the patterns are fixed points at all
    stored_ok = sum(np.array_equal(step_sync(P[:, m], W), P[:, m]) for m in range(M))

    correct = settled = 0
    for _ in range(n_trials):
        m = rng.integers(M)
        s = P[:, m].copy()
        flip = rng.choice(N, size=hd, replace=False)
        s[flip] *= -1
        out, ok = settle_async(s, W, rng)
        settled += ok
        if ok and np.array_equal(out, P[:, m]):
            correct += 1
    return {
        "N": N, "M": M, "alpha": M / N, "hd": hd,
        "stored_fixed": stored_ok, "stored_frac": stored_ok / M,
        "settled": settled / n_trials,
        "correct": correct / n_trials,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--reps", type=int, default=5, help="independent nets per cell")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = np.random.default_rng(31337)
    rows = []
    print(f"{'N':>4} {'M':>3} {'alpha':>6} {'hd':>3} "
          f"{'stored_fp':>9} {'settled':>8} {'correct':>8}")
    print("-" * 50)
    for N in (16, 24, 32, 48, 64):
        for M in (2, 3, 4, 6, 8):
            if M / N > 0.6:
                continue
            for hd in (1, 3):
                acc = [scan(N, M, args.trials // args.reps, hd, rng)
                       for _ in range(args.reps)]
                r = {k: float(np.mean([a[k] for a in acc])) for k in acc[0]}
                rows.append(r)
                print(f"{N:>4} {M:>3} {r['alpha']:>6.3f} {hd:>3} "
                      f"{r['stored_frac']*100:>8.1f}% {r['settled']*100:>7.1f}% "
                      f"{r['correct']*100:>7.1f}%")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
