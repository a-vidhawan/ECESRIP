#!/usr/bin/env python3
"""
Round 5 stress tests -- capacity limits and robustness analysis.

Motivated by R4 findings. Probes:
  S. Capacity: store 1, 2, 3, 4 patterns, measure cross-talk and recall
  T. HD-5 isolation: for all states within HD=5 of patterns, full exhaustive SV test
  U. T_EVEN sweep: fix T_ODD=24, sweep T_EVEN 1..30
  V. Single-bit basin: for each bit position, find all states where flipping that
     bit drives the state to a stored pattern (reveals critical recall bits)
  W. Attractor stability: start from attractor, add single-bit flip, measure recall
     (tests local basin curvature at each fixed point)
"""

import os, sys, time, math, random
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from run_clockless_stress import (
    generate_rtl, run_batch, corrupt,
    PATTERNS_BIN, PATTERNS_INT, ALL_FPS, SPURIOUS_FPS,
    hamming, N, DEFAULT_TERMS, RES, TMP, RTL, LUT_SV,
    write_testbench, compile_and_run, parse_output, classify
)
from gen_clockless_sv import compute_depths, _header, gen_even_odd_sv

W_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                      "phase1", "results", "truth_tables",
                      "pseudo_s_maxprune", "W_pruned.npy")


# ════════════════════════════════════════════════════════════════════════════
# EXP T: EXHAUSTIVE HD<=5 BASIN TEST (SV simulation)
# All states within Hamming distance 5 of any stored pattern
# This is the claimed "basin of attraction" -- verify exhaustively
# ════════════════════════════════════════════════════════════════════════════

def exp_exhaustive_basin():
    print("\n=== EXP T: EXHAUSTIVE HD≤5 BASIN (SV simulation) ===")
    # Generate all states within HD=k of each pattern for k=0..5
    all_inits = []
    all_pats = []
    all_hds = []
    seen = set()

    for p_idx in range(4):
        pat_int = PATTERNS_INT[p_idx]
        for hd in range(6):  # 0..5
            for bits in itertools.combinations(range(N), hd):
                s_int = pat_int
                for b in bits:
                    s_int ^= (1 << b)
                if s_int not in seen:
                    seen.add(s_int)
                    all_inits.append(s_int)
                    all_pats.append(p_idx)
                    all_hds.append(hd)

    all_etas = [hd / N for hd in all_hds]
    print(f"  Testing {len(all_inits)} unique states within HD≤5 of any pattern")

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        df = run_batch(f"basin_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            by_hd = df.groupby("hamming_in").apply(
                lambda x: pd.Series({
                    "correct": (x.outcome == "correct").mean(),
                    "settled": (x.outcome != "oscillated").mean(),
                    "n": len(x),
                })
            )
            print(f"\n  [{mode}] Recall by HD:")
            for hd, row in by_hd.iterrows():
                print(f"    HD={hd}: correct={row.correct:.1%}  settled={row.settled:.1%}  n={int(row.n)}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP U: T_EVEN SWEEP (fix T_ODD=24, sweep T_EVEN=1..30)
# Complement to the T_ODD sweep: what happens as even neurons get faster/slower?
# ════════════════════════════════════════════════════════════════════════════

def exp_t_even_sweep():
    print("\n=== EXP U: T_EVEN SWEEP (T_ODD=24 fixed) ===")
    T_ODD = 24
    t_even_vals = list(range(1, 35))
    rng = np.random.default_rng(55555)
    eta_grid = [0.0, 0.15, 0.30]
    n_trials = 80

    all_inits, all_pats, all_etas, all_hds = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                all_inits.append(s); all_pats.append(p_idx)
                all_etas.append(eta); all_hds.append(hamming(s, PATTERNS_INT[p_idx]))

    dfs = []
    for t_even in t_even_vals:
        sv, max_d = gen_even_odd_sv(N, t_even, T_ODD)
        tag = f"_teven{t_even}"
        sv_path = os.path.join(RTL, f"clockless_teven{tag}.sv")
        with open(sv_path, "w") as f:
            f.write(sv)
        df = run_batch("t_even", "even_odd", all_inits, all_pats, all_etas, all_hds,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["t_even"] = t_even
            df["t_odd"] = T_ODD
            df["ratio"] = T_ODD / t_even
            settled = (df.outcome != "oscillated").mean()
            correct = (df.outcome == "correct").mean()
            print(f"  t_even={t_even:3d} (ratio={T_ODD/t_even:.2f}): correct={correct:.1%}  settled={settled:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP V: ATTRACTOR LOCAL STABILITY (single-bit perturbation of attractors)
# Start from each of the 20 fixed points, flip each bit, test recall
# Measures the local "steepness" of the basin around each attractor
# ════════════════════════════════════════════════════════════════════════════

def exp_attractor_stability():
    print("\n=== EXP V: ATTRACTOR LOCAL STABILITY ===")
    all_fps = list(ALL_FPS)
    pat_set = set(PATTERNS_INT)

    all_inits, all_pats, all_etas, all_hds = [], [], [], []
    flip_bits_list, fp_list = [], []

    for fp in all_fps:
        nearest = min(range(4), key=lambda p: hamming(fp, PATTERNS_INT[p]))
        for bit in range(N):
            perturbed = fp ^ (1 << bit)
            hd = hamming(perturbed, PATTERNS_INT[nearest])
            all_inits.append(perturbed)
            all_pats.append(nearest)
            all_etas.append(hd / N)
            all_hds.append(hd)
            flip_bits_list.append(bit)
            fp_list.append(f"{fp:04x}")

    print(f"  Testing {len(all_inits)} perturbed attractor states")

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        df = run_batch(f"attstab_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            df["source_fp"] = fp_list[:len(df)]
            df["flip_bit"] = flip_bits_list[:len(df)]
            df["is_stored"] = df["source_fp"].apply(
                lambda x: int(x, 16) in pat_set)

            # Summary: for stored vs spurious attractors, how stable are 1-bit neighbors?
            for is_stored in [True, False]:
                sub = df[df["is_stored"] == is_stored]
                if sub.empty: continue
                label = "stored" if is_stored else "spurious"
                # What fraction of 1-bit neighbors return to the original FP?
                return_same = sub.apply(
                    lambda row: row["result_state"] == row["source_fp"], axis=1).mean()
                correct = (sub.outcome == "correct").mean()
                print(f"  [{mode}/{label}] return_to_same_fp={return_same:.1%}  correct_recall={correct:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP W: MULTI-STEP PERTURBATION RECOVERY
# Start from a stored pattern, apply k sequential single-bit flips,
# check if network recovers after each flip series
# ════════════════════════════════════════════════════════════════════════════

def exp_sequential_perturbation():
    print("\n=== EXP W: SEQUENTIAL PERTURBATION RECOVERY ===")
    rng = np.random.default_rng(66666)
    n_trials = 100
    k_flips = list(range(1, 10))  # 1..9 sequential flips

    all_inits, all_pats, all_etas, all_hds, all_k_vals = [], [], [], [], []

    for k in k_flips:
        for p_idx in range(4):
            pat_int = PATTERNS_INT[p_idx]
            for _ in range(n_trials):
                # Apply k sequential random bit flips to the pattern
                s = pat_int
                for _ in range(k):
                    bit = int(rng.integers(0, N))
                    s ^= (1 << bit)
                # Note: with k random flips, expected HD from pattern is k*(1 - 2*hd_current/N)
                # but actual HD could be less if same bit flipped twice
                hd = hamming(s, pat_int)
                all_inits.append(s)
                all_pats.append(p_idx)
                all_etas.append(hd / N)
                all_hds.append(hd)
                all_k_vals.append(k)

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        df = run_batch(f"seqpert_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            df["k_flips"] = all_k_vals[:len(df)]
            by_k = df.groupby("k_flips").apply(
                lambda x: pd.Series({
                    "correct": (x.outcome == "correct").mean(),
                    "settled": (x.outcome != "oscillated").mean(),
                    "mean_hd": x["hamming_in"].mean(),
                })
            )
            print(f"\n  [{mode}] By number of sequential flips:")
            for k, row in by_k.iterrows():
                print(f"    k={k}: correct={row.correct:.1%}  settled={row.settled:.1%}  mean_HD={row.mean_hd:.1f}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

import itertools

def main():
    t0 = time.time()
    all_dfs = []

    steps = [
        ("exhaustive_basin", exp_exhaustive_basin),
        ("t_even_sweep",     exp_t_even_sweep),
        ("att_stability",    exp_attractor_stability),
        ("seq_perturb",      exp_sequential_perturbation),
    ]

    for name, fn in steps:
        t_exp = time.time()
        try:
            df = fn()
            if df is not None and not df.empty:
                out = os.path.join(RES, f"stress_r5_{name}.csv")
                df.to_csv(out, index=False)
                all_dfs.append(df)
                print(f"  → {out}  ({len(df)} rows)")
        except Exception as exc:
            import traceback
            print(f"  [ERROR] {name}: {exc}")
            traceback.print_exc()
        print(f"  [wall] {name}: {time.time()-t_exp:.1f}s")

    print(f"\n══ Round 5 DONE in {time.time()-t0:.1f}s ══")


if __name__ == "__main__":
    main()
