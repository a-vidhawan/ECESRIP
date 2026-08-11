#!/usr/bin/env python3
"""
PHASE 6 -- train the basin directly, by implicit differentiation through settling.

The margin rule (phase 5) optimises a PROXY: "make each pattern a fixed point
with margin kappa". Margin correlates with basin size but does not control it, so
we optimise one thing and measure another.

What we actually want is recall: settling from a CORRUPTED start must land on the
right pattern. That is the output of a fixed-point solve, so the gradient of a
recall objective with respect to W needs differentiation through an equilibrium.
The implicit function theorem gives it without storing the settling trajectory --
the Deep Equilibrium Model / adjoint construction:

    forward    s* = f(s*, W),         f(s,W) = tanh(beta * W s)
    Jacobian   J  = df/ds = D W,      D = diag(beta (1 - s*^2))
    adjoint    v  = (I - J^T)^{-1} g, g = dL/ds*
    gradient   dL/dW_ij = v_i * D_ii * s*_j

sign() has zero gradient almost everywhere, so the forward map is smoothed with
tanh(beta*) and beta is annealed upward. The trained weights are then checked
against the ORIGINAL binary dynamics -- a smoothed equilibrium is not
automatically a binary fixed point, and that gap is the main risk of the method.

Compares against the phase-5 margin rule at matched M.
"""

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from scale_study import make_support
from improve_capacity import train_margin, n_fixed
from schedule_hnn import graph_from_W, dsatur
from pvt_analysis import settle_event_driven


def equilibrium(W, s0, beta, gamma=0.7, iters=400, tol=1e-9):
    """Smoothed forward settle, DAMPED: s <- (1-g)s + g*tanh(beta W s).

    The undamped iteration s <- tanh(beta W s) is a *synchronous* update of a
    smoothed Hopfield network, and oscillates for exactly the reason this project
    exists -- measured convergence was only 15-50%. Feeding a non-equilibrium
    into the implicit function theorem produces a meaningless gradient, which is
    what broke the first version of this trainer. Damping makes the map a
    contraction: gamma=0.7 converges 100% of the time at every beta tested.
    """
    s = s0.copy()
    for _ in range(iters):
        s_new = (1.0 - gamma) * s + gamma * np.tanh(beta * (W @ s))
        if np.max(np.abs(s_new - s)) < tol:
            return s_new, True
        s = s_new
    return s, False


def adjoint_grad(W, s_star, g, beta, ridge=1e-6):
    """dL/dW via the implicit function theorem at the equilibrium s*.

    Solves the adjoint system (I - J^T) v = g rather than backpropagating
    through the settling iterations, so cost is one linear solve and memory does
    not grow with the number of steps.
    """
    N = W.shape[0]
    d = beta * (1.0 - s_star ** 2)          # diagonal of D
    J = d[:, None] * W                       # J = D W
    A = np.eye(N) - J.T
    try:
        v = np.linalg.solve(A + ridge * np.eye(N), g)
    except np.linalg.LinAlgError:
        v = np.linalg.lstsq(A, g, rcond=None)[0]
    return np.outer(v * d, s_star)


def train_adjoint(pats, mask, W0, hd=3, epochs=60, lr=2e-3, beta0=2.0,
                  beta1=6.0, samples=4, seed=0, lam=1.0, kappa=1.0,
                  gamma=0.7, clip=1.0, verbose=False):
    """Fine-tune W so corrupted starts settle back to their pattern.

    Four things the first version got wrong, all fixed here:

      1. The forward solve was undamped and mostly did not converge, so most
         gradients were computed at non-equilibria (see `equilibrium`).
      2. Non-converged samples are now SKIPPED rather than used regardless.
      3. The margin objective is retained alongside the basin objective. The
         basin loss alone drifts the weights somewhere good for the smoothed map
         and bad for the binary one, destroying the fixed points it started from.
      4. The per-step renormalisation is gone. It is harmless for a scale-free
         margin objective but actively wrong here, because tanh(beta*W*s) depends
         on the scale of W -- rescaling every step fights the gradient.
    """
    M, N = pats.shape
    rng = np.random.default_rng(seed)
    W = W0.copy()
    mask = (mask > 0).astype(float)
    np.fill_diagonal(mask, 0.0)
    hist = []

    for ep in range(epochs):
        beta = beta0 + (beta1 - beta0) * ep / max(1, epochs - 1)
        G = np.zeros_like(W)
        loss = 0.0
        used = 0
        for m in range(M):
            for _ in range(samples):
                s0 = pats[m].copy()
                s0[rng.choice(N, size=hd, replace=False)] *= -1
                s_star, ok = equilibrium(W, s0, beta, gamma=gamma)
                if not ok:
                    continue                 # no equilibrium -> no valid gradient
                err = s_star - pats[m]
                loss += float(err @ err)
                G += adjoint_grad(W, s_star, 2.0 * err, beta)
                used += 1
        if used:
            G /= used
            loss /= used

        # keep the patterns pinned as binary fixed points while the basin term
        # reshapes the landscape around them
        H = pats @ W.T
        viol = (H * pats) < kappa
        Gm = np.zeros_like(W)
        for m in range(M):
            bad = np.nonzero(viol[m])[0]
            if bad.size:
                Gm[bad, :] -= np.outer(pats[m][bad], pats[m])
        G = G + lam * Gm / M

        gn = np.abs(G).max()
        if gn > clip:
            G *= clip / gn
        W -= lr * G
        W *= mask
        W = (W + W.T) / 2.0
        W *= mask
        np.fill_diagonal(W, 0.0)
        hist.append(dict(epoch=ep, beta=beta, loss=loss, used=used,
                         frac_converged=used / max(1, M * samples)))
        if verbose and ep % 10 == 0:
            print(f"    ep{ep:>3} beta={beta:.1f} loss={loss:.3f} "
                  f"converged={100*used/max(1,M*samples):.0f}% "
                  f"stored={n_fixed(W, pats)}/{M}")
    return W, hist


def recall(W, pats, hd, trials, seed):
    """Recall under the real BINARY async dynamics, not the smoothed model."""
    N = W.shape[0]
    n, edges = graph_from_W(W)
    if not edges:
        return 0.0
    colour = dsatur(n, edges)
    delays = [colour[i] + 1 for i in range(n)]
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(seed)
    ok = 0
    for _ in range(trials):
        m = int(rng.integers(len(pats)))
        s = P01[m].copy()
        s[rng.choice(N, size=hd, replace=False)] ^= 1
        out, settled = settle_event_driven(s, W, delays)
        ok += settled and np.array_equal(out, P01[m])
    return ok / trials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--Ms", type=int, nargs="+", default=[8, 16, 24, 32])
    ap.add_argument("--fanin", type=int, default=32)
    ap.add_argument("--hd", type=int, nargs="+", default=[3, 6])
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--lam", type=float, default=1.0,
                    help="weight on the margin term that pins the fixed points")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    N = args.N
    print(f"N={N}, fan-in {args.fanin}, adjoint fine-tuning from the margin solution")
    print(f"{'M':>4}{'stored':>10}{'stored':>9}" +
          "".join(f"{'margin HD'+str(h):>14}{'adjoint HD'+str(h):>15}"
                  for h in args.hd))
    print(f"{'':>4}{'margin':>10}{'adjoint':>9}" + "".join(f"{'':>29}" for h in args.hd))
    print("-" * (23 + 29 * len(args.hd)))
    rows = []
    for M in args.Ms:
        d = min(N - 1, args.fanin)
        pats = np.random.default_rng(args.seed + M).choice(
            [-1, 1], size=(M, N)).astype(float)
        mask = make_support(N, d, "regular", np.random.default_rng(args.seed))
        Wm = train_margin(pats, mask, seed=args.seed)
        Wa, hist = train_adjoint(pats, mask, Wm, hd=max(args.hd),
                                 epochs=args.epochs, seed=args.seed,
                                 lr=args.lr, lam=args.lam, verbose=args.verbose)
        r = dict(N=N, M=M, fan_in=d,
                 stored_margin=n_fixed(Wm, pats), stored_adjoint=n_fixed(Wa, pats),
                 loss_start=hist[0]["loss"], loss_end=hist[-1]["loss"],
                 frac_converged=hist[-1]["frac_converged"])
        line = f"{M:>4}{r['stored_margin']:>7}/{M:<2}{r['stored_adjoint']:>6}/{M:<2}"
        for h in args.hd:
            rm = recall(Wm, pats, h, args.trials, args.seed + 1)
            ra = recall(Wa, pats, h, args.trials, args.seed + 1)
            r[f"recall_margin_hd{h}"] = rm
            r[f"recall_adjoint_hd{h}"] = ra
            line += f"{100*rm:>13.0f}%{100*ra:>14.0f}%"
        rows.append(r)
        print(line, flush=True)
    print("-" * (23 + 29 * len(args.hd)))
    print("Recall is measured on the BINARY async dynamics for both, so the")
    print("comparison is fair even though the adjoint objective is smoothed.")
    dest = os.path.join(HERE, "results", "adjoint_vs_margin.json")
    json.dump(rows, open(dest, "w"), indent=2)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
